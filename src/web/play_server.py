"""使い手の入口: 手元で動くブラウザの画面（本人の決定、J-024）。依存を増やさず標準の http.server で作る。

判断の芯: コマンドの輪と同じ線を画面でも守る。仮説に順位を出さない（J-013）、
試した後の紙は記録を残すまで渡さない（J-013）、結果は人が入れる値で、成績にしない（philosophy.md）。
鍵なしで輪の前半（型紙 → 試す → 記録 → 人の説明）が回る。Claude を呼ぶ所（手帖の質問・読み・観察）は鍵がある時だけ動く。
既定は持ち寄りの画面（contrib_server.py）と同じく 127.0.0.1 にだけ開く。外に開く責任を週内に持てないため。
家の網に開く切り替え（--lan、U-36）と、デモの一周を外の機器から開く合言葉の門（--public-key-file、11-04 の本人の決定 A）は
本人の決定で足した。後者は口を 127.0.0.1 のままにし、外からはトンネル（run-demo.sh）だけが入る。
"""
import collections
import hmac
import html
import ipaddress
import json
import os
import pathlib
import re
import secrets
import sys
import threading
import time
import urllib.parse
from concurrent.futures import Future
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from omochae import hypotheses, loop, making_log, media_review, records, store
from omochae.compose import TEMPLATES
from omochae.hypotheses import ROOT
from omochae.store import SID

from . import failure_log
from . import skin as skinmod
from . import wording
from .contrib_server import STYLE

# 見た目はルックブックの様式（本人の指定、J-024）。絵が主役で、文字は添え。見開きのように絵と短い文を左右に置き、玩具ごとに左右を入れ替える。
# 参照の X の投稿の実物は 11-04 に見た（research/19）。入口の見た目は looks.py にあり、この塊は玩具の頁の見た目だけを持つ。
LOOK = STYLE + """
body{background:#efe8d8;padding:0}main{max-width:none;margin:0}
.wrap{max-width:1180px;margin:auto;padding:0 20px 64px}
.cap{font-size:max(12px,.78em);color:#6b604f;margin-top:8px}
.side h1,.side h2{font-size:clamp(28px,4vw,52px);font-weight:400;letter-spacing:.15em;margin:0 0 12px}
.side .no{font-size:.8em;letter-spacing:.3em;color:#7a3b1d}
.side a.open{display:inline-block;margin-top:18px;border-bottom:1px solid #7a3b1d;text-decoration:none}
.song{writing-mode:vertical-rl;font-size:1.25em;line-height:2;height:16em;margin:8px 0 0 auto}
.plates{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:20px}
.plate{background:#fffdf7;border:1px solid #c9bda3;padding:18px}.plate .letter{font-size:56px;line-height:1;color:#7a3b1d}
.plate h3{font-weight:400;margin:6px 0}.plate p{font-size:.9em}
.wrap > form,.wrap > article{max-width:640px}
@media (max-width:760px){.song{writing-mode:horizontal-tb;height:auto}}
"""

MAX_FORM = 64 * 1024
# トンネルの一時の名前の形（run-demo.sh の cloudflared）。本物の名前は repo に書かない（push の門の決まり）ので、形だけをここに 1 か所置く。
TUNNEL_HOST = r"[a-z0-9-]+\.trycloudflare\.com"


def uploaded(rid):
    """動画の受け口の記録か。上げた人に「頁に出さない」と約束した記録なので、置き場を共有していてもサイトの口から触らせない。"""
    rec = store.read_json_or_skip(records.folder() / f"{rid}.json")
    return bool(rec and rec.get("via") == records.UPLOADED)


def byte_range(header, size):
    """Range の要求を (始め, 終わり) にする。読めない形は None（全体を 200 で返す）、範囲の外は False（416）。

    なぜ要るか: iOS の Safari は動画を部分取得で読み、答えないサーバの動画は再生されない事が知られている（#152）。
    複数の範囲は受けず全体を返す。動画の再生では使われず、全体を返しても決まりの内で、組み立ての形を持たずに済むため。
    """
    m = re.fullmatch(r"bytes=([0-9]*)-([0-9]*)", (header or "").strip())
    if not m or not (m.group(1) or m.group(2)):
        return None
    first, last = m.groups()
    if not first:  # 末尾から last バイト。ファイルより長ければ全体
        return (max(size - int(last), 0), size - 1) if int(last) and size else False
    if last and int(last) < int(first):
        return None
    if int(first) >= size:
        return False
    return int(first), min(int(last), size - 1) if last else size - 1


def out_dir(sid):
    """刷った紙の置き場。"""
    return hypotheses.play_dir(sid)


def sources():
    return sorted(p.stem for p in (ROOT / "data/hypotheses").glob("NDL-*.json"))


def source(sid):
    return json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))


def esc(s):
    return html.escape(str(s if s is not None else ""))


def page(title, body, extra_style="", body_class="", description=""):
    cls = f' class="{body_class}"' if body_class else ""
    return (f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>{skinmod.meta_head(title, description)}'
            f'<style>{LOOK}{BOOK}{skinmod.TAP_FLOOR}{extra_style}</style><body{cls}><main>{body}</main></body></html>')


# 玩具の頁の頭に置く見開きの紙（図と、名前と縦組みの歌）。入口の冊子をめくる仕組みは、
# 本人が見開き型と冊子型を残さないと決めたので外した（2026-11-04、J-024）。この紙の形だけを玩具の頁に残す。
BOOK = """
.booklet{max-width:1180px;margin:24px auto 8px;padding:0 20px}
.sheet{display:grid;grid-template-columns:1fr 1fr;background:#fffdf7;box-shadow:0 2px 0 #c9bda3,0 18px 40px rgba(60,40,20,.12);position:relative;min-height:min(80vh,820px);margin-bottom:32px}
.sheet::after{content:"";position:absolute;left:calc(50% - 9px);top:18px;bottom:18px;width:18px;
 background:radial-gradient(circle at 50% 50%,#8a7a62 0 4px,transparent 5px) 0 0/18px 34px repeat-y}
.pg{padding:40px 44px;display:flex;flex-direction:column;justify-content:flex-end;min-width:0}
.pg.l{border-right:1px solid #e3d9c4}
.pg.full{padding:24px}.pg.full img{width:100%;height:100%;max-height:76vh;object-fit:contain}
.pg h2{font-size:clamp(28px,4vw,52px);font-weight:400;letter-spacing:.15em;margin:0 0 12px}
@media (max-width:760px){.sheet{grid-template-columns:1fr}.sheet::after{display:none}.pg.l{border-right:0;border-bottom:1px solid #e3d9c4}.pg{padding:24px}}
"""


# 画面で変えてよい寸法と、その呼び名。変えてよい寸法そのものは台帳の決まり（metrics.ALLOWED）に従う。
PARAM_NAMES = {"fold_count": "折りの数", "fold_width": "折りの幅（mm）", "fold_height": "扇の高さ（mm）", "tube_side": "外筒の一辺（mm）",
               "pusher_side": "内筒の一辺（mm）", "push_amount": "押し上げる量（mm）", "pivot_above_rim": "扇の中心の高さ（mm）",
               "paper_thickness": "紙の厚さ（mm）", "weight_g": "重りの重さ（g）", "weight_below_axle": "重りの軸からの下がり（mm）",
               "weight_behind": "重りの後ろへのずれ（mm）", "ear_length": "耳の長さ（mm）", "neck_length": "首の長さ（mm）",
               "opening": "胴の口の幅（mm）", "head_w": "頭の幅（mm）", "head_h": "頭の高さ（mm）", "paper_gsm": "紙の重さ（g/m²）"}


# 仮説の印の形（紙を返す口 /sheet/... の形と同じ）。フォームから来る値は、この形の物だけを刷った紙の探しに使う。
HID_FORM = re.compile(r"H-[A-Z0-9]+|OWN-\d+")


def printed_versions(sid, hid):
    """刷ってある版の番号（小さい順）。無ければ空。版 1 を決め打ちしない: 報告から直した版 2 以降を、次に作る人が最初に刷る事があるため。"""
    # 印の形でない値は探さずに空を返す。hid はフォーム（talk・record-json・ask）から検査なしで来るので、
    # glob の形にそのまま入れると、「..」や「**」で置き場の外まで広く探させられ、合言葉なしの場でもサーバを詰まらせられた（セキュリティの点検 U16）。
    if not isinstance(hid, str) or not HID_FORM.fullmatch(hid):
        return []
    # 自分の仮説は、型紙なしの紙（_free）も刷った紙に数える。作りながら見る頁と話す口が、その紙に付くように（ループ1、#335）。
    free = "(?:_free)?" if str(hid).startswith("OWN-") else ""
    return sorted({int(m.group(1)) for p in out_dir(sid).glob(f"{hid}_v*.pdf") if (m := re.fullmatch(rf"{re.escape(hid)}_v(\d+){free}\.pdf", p.name))}) if out_dir(sid).exists() else []


def ensure_after(sid, hid, version):
    """記録のある案と版の試した後の紙が無ければ、開く時に作る（#320）。場で配られた紙で作った人は「型紙を見る」を押さないので、置き場に紙が無い。
    記録の時でなく開く時に作るのは、前に残した記録と、置き場が空になった後の記録も同じ道で開くため。記録の POST も重くならない。
    記録の無い案と版では作らない（S-03）。作るのは試した後の紙だけで、型紙の確定（f09）も増やさない: 人が刷ると選んだ操作でないので、刷った案に数えない。
    途中で落ちても半端な紙を残さない。作れない時は紙が無いだけにする（頁ごと落とさない）。"""
    if not any(r["hypothesis_id"] == hid and r.get("sheet_version", 1) == version for r in records.all_records(sid)):
        return
    if (out_dir(sid) / f"{hid}_v{version}_after.pdf").exists():
        return
    try:
        loop.print_after(sid, hid, version, out_dir(sid))
    except Exception as e:
        failure_log.request_failed("GET", f"/sheet/{sid}/{hid}_v{version}_after", e)


def sheet_version_of(sid, hid, form):
    """この報告・質問・札が、どの版の紙への物か。画面が言った版（刷ってある物だけ）を使い、言わなければ一番新しい版。
    なぜ画面から受けるか: 版 1 で作っている間に、別の人の報告で版 2 が刷られる事がある。一番新しい版を決め打ちすると、版 1 の動きが版 2 の記録になり、
    改善の輪の根拠（どの版がどう動いたか）が崩れる（検品の指摘）。"""
    vs = printed_versions(sid, hid)
    try:
        v = int(form.get("sheet_version", ""))
    except ValueError:
        v = None
    return v if v in vs else (vs[-1] if vs else 1)


def toy_page(sid, errors=(), msg="", asked=None, look=skinmod.DEFAULT, **kw):
    """玩具の頁。中身は toy.py（順路と皮は docs/process/site-requirements.md）。ここは古い呼び口を残す薄い包み。"""
    from . import toy

    return toy.toy_page(sid, look, errors, msg, asked, **kw)


def next_form(r, back=""):
    """次の版を作る口。中身は toy.py。手帖（techo_site）がこの名前で呼ぶので残す。"""
    from . import toy

    return toy.next_form(r, back)


def _ban(sid, v):
    """刷った後の知らせの版の字。玩具の頁の窓の札・刷り直しの釦と同じ組の番号の呼び方にする（窓口の決定 11-07・#513 の (a)）。
    知らせだけ「版 2」のままだと、同じ画面の札「版 14（直し 2）」と別の版に読めるため。"""
    return hypotheses.label_of(hypotheses.current_set(hypotheses.load(sid)), int(v))

def _num(v):
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return v  # 数でない物は記録の検査に落とさせ、理由を画面に返す


def without_notes(page):
    """頁の style と script の注釈を外す。作る側の控え（決定や Issue の番号、内部の名前）なので、合言葉なしで開いた場には送らない（J-028）。
    script は行の頭の // と、文の後ろの // だけを外す。字の中の // や URL を切らないため。"""
    def clean(m):
        tag, attrs, part = m.groups()
        if tag == "style":
            part = re.sub(r"/\*.*?\*/", "", part, flags=re.S)
        else:
            part = re.sub(r"(?m)^[ \t]*//[^\n]*\n?", "", part)
            part = re.sub(r"(?m)(?<=[;{}])[ \t]*//[^\n'\"`]*$", "", part)
        return f"<{tag}{attrs}>{part}</{tag}>"

    return re.sub(r"<(style|script)\b([^>]*)>(.*?)</\1>", clean, page, flags=re.S)


# 書き込みの口（話す口・記録の口・説明の口・聞く口）の、同じ相手からの短い間の数の上限（公開の前の点検の 9、統括の頼み 11-06）。
# 聞く口も 1 回ごとに置き場へファイルを書くので数える（統括の足し 11-06）。段の口は別の数で数える（STEP_LIMIT）。
# 合言葉付きの場で 5 人が同じ網（同じ番地）から同時に一周しても止まらない数: 1 人の一周の書き込みは 6〜12 回（話す回数による）で、
# 作る間の数分にわたる。5 人が 1 分に 12 回ずつ書いても通り、それを超える速さだけを止める。
WRITE_LIMIT, WRITE_WINDOW = 60, 60.0
# 段の口（作りながら見る頁の札）の数。書き込みの口と別に数え、手順を押す数で記録や話す口を断らない（統括の決め 11-06）。
# 5 人が同じ網から、手順を全部同じ 1 分で押しても（1 人 13〜20 回）断らない数。超えても頁は止めず、段を置き場へ書かないだけ。
STEP_LIMIT = 120
# 写真と動画の口の数（セキュリティの点検 U1）。この口はフォームを読む前に本体のまま受けるので、書き込みの数（WRITE_PATHS）が届かず、上限が無かった。
# 1 つ 20MB まで。1 つの網（学校の網など、トンネル越しの番地が 1 つ）から同じ 1 分に、20 人が 3 つずつ（のこす時の上限 MAX_PER_RECORD）
# 上げても断らない数（窓口の決め 11-07・案 b。前は 20 で、7 人目から断りが出えた）。機械を埋めない守りは、公開の場の合計の上限
# （PUBLIC_MEDIA_TOTAL）と、写した動画の大きさの上限（techo_site.VIDEO_ROOM）の方で効く。
MEDIA_LIMIT = 60
# 区切りの見出しの値と型の組（声とカメラの設計 3 版の 3 節）。声は音の型（iPhone の Safari は audio/mp4・Chrome は audio/webm）、
# カメラは絵の型だけを受ける。組に無い物は 422（名乗った型と中身の頭のバイトが合うかは voice_text が見る）
CLIP_TYPES = {("t", "audio/webm"): "webm", ("t", "audio/mp4"): "mp4", ("k", "video/webm"): "webm", ("k", "video/mp4"): "mp4"}
# しおりの開く道（押した順を送る・とじる）も書き込みの数に入れる。台帳の止め 3 つの前に、同じ相手の短い間の数でも抑えるため（開く道の設計 7.2）
# 話した考えから紙を作る口（think-sheet・think-ok）も入れる。Claude を呼ぶ口と、紙を刷る口なのに、前は数の上限が無かった（設計 2 版の 4 節・別の目の止め 2）
WRITE_PATHS = re.compile(rf"/toy/{SID}/(?:talk|record|record-json|ask|ask-json|think-sheet|think-ok)|/record/R-\d{{4,}}/explain|/close|/s/[A-Za-z0-9_-]{{22}}|/s/close")
# 紙を刷る口（刷る・刷り直す・英語の頁から刷る）の数（セキュリティの点検 U17）。1 回ごとに描画と PDF の別の処理が走り、刷った記録に
# 1 件足す重い口なのに、前は数の上限が無く、合言葉なしの場で玩具を変えながら送り続けると CPU が詰まった。書き込みの口と別に数える。
# 相手ごと: 1 つの網（学校の網など、トンネル越しの番地が 1 つ）から、同じ 1 分に 30 人が刷っても通る数（窓口の決め 11-07・案 b）。
# 機械の重さは全体の同時の数（PRINT_SLOTS）の方で守るので、相手ごとの数は、1 つの相手が空きを独り占めしない程度でよい。
PRINT_LIMIT = 30
# 型紙としおりを一緒に返す道（sheet-shiori）も刷る道として数える（しおりの頁を描いて合わせる重さがある・設計 2.1 版）
PRINT_PATHS = re.compile(rf"/toy/{SID}/(?:print|reprint|sheet-shiori)|/en/toy/{SID}/print")
# 全体: 同時に刷るのは 2 本まで。番地を替えて送られても、描画の処理が機械を埋めないため。空きは少し待ち、待っても空かなければ断る。
PRINT_SLOTS, PRINT_WAIT = 2, 20.0
_print_slots = threading.BoundedSemaphore(PRINT_SLOTS)


class PrintBusy(Exception):
    """刷る空きを待っても取れなかった。受けた口で、書き込みが多すぎる時と同じ断り（429）を返す。"""


def _printing(make):
    """全体の刷る空きを 1 つ取ってから make を動かす。同じ案を同時に頼んだ人は _one_at_a_time で待つので、空きを取るのは作る人だけ。"""
    if not _print_slots.acquire(timeout=PRINT_WAIT):
        raise PrintBusy
    try:
        return make()
    finally:
        _print_slots.release()
BUSY = "受け付けられませんでした。少し待って、もう一度送ってください。"
# 頼まれた仮説が無い時の断り（刷る・記録を残す・考えを話す）。前は「仮説 {hid} は無い」で、内部の番号（H-A など）をそのまま出していた。
# 印（A・C）と番号を学ぶ人に出さない決め（本人の答え 11-08「そろえる。」）に外れるので、統括の決め（11-08）の向きの字にした。新しい字は本人の確かめ待ち
NO_HYPOTHESIS = "その仮説は見つかりません。頁を開き直してください。"
# 押し方の違う紙の記録から次の版を作ろうとした時の断り（loop.next_target が None）。前は「次の版はたたき台（H-C）にだけ足す」で、
# たたき台の内部の番号を出していた（別の目の気づき・統括の決め 11-08）。新しい字は本人の確かめ待ち
NEXT_SHEET_ONLY = "次の版は、今のたたき台の型紙にだけ足せます。"


def writer(peer, headers):
    """書き込みを数える相手の番地。None は数えない（手元から直に来た物。試験と手元の確かめ）。
    外からはトンネル（cloudflared）越しにしか入らず、どの人も手元の番地から来るので、トンネルが付ける見出しの番地を使う。
    見出しを信じるのは手元から来た時だけ: 家の網から直に来る機器（--lan）が、見出しを変えて数を逃れないため。"""
    try:
        local = ipaddress.ip_address(peer).is_loopback
    except ValueError:
        local = False
    if not local:
        return peer
    return (headers.get("Cf-Connecting-Ip") or (headers.get("X-Forwarded-For") or "").split(",")[0]).strip() or None


class WriteLimit:
    """同じ相手からの、短い間の書き込みの数。持つのは相手の番地と時刻だけで、送られた字は持たない。"""

    def __init__(self, limit=WRITE_LIMIT, window=WRITE_WINDOW, keys=4096):
        self.limit, self.window, self.keys = limit, window, keys
        self.times, self.lock = {}, threading.Lock()

    def wait(self, who, now=None):
        """この相手が今書いてよければ 0、まだなら待つ秒数。"""
        now = time.monotonic() if now is None else now
        with self.lock:
            if len(self.times) > self.keys:  # 覚える相手の数を限る。間が過ぎた相手から忘れる
                self.times = {k: q for k, q in self.times.items() if q and now - q[-1] < self.window}
            q = self.times.setdefault(who, collections.deque())
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return max(1, int(self.window - (now - q[0])) + 1)
            q.append(now)
            return 0


UP_COOKIE = "utsushi_up"  # 確認の前の写真を、上げた本人の画面にだけ出すための鍵（media_review.shown_to）
SHIORI_PENDING = "utsushi_sp"  # 型紙と一緒に刷ったしおりの待ちの印（記録に結ぶ前・omochae.shiori の pending）
REC_COOKIE = "utsushi_rec"  # 記録の札の説明と字を足す口を、記録を残した本人の画面にだけ開くための鍵（records.mine）


# 応答の守りの頭（公開の前の点検 U18・U20。本人の決め 11-07「(a) を出す」）。
# - 途中で溜め置かせない: トンネルの先（Cloudflare）は写真や PDF の拡張子を既定で溜めうる。溜めると、上げた人にだけ出す確かめる前の
#   写真や、その人だけの紙が、同じ URL を開いた別の人に返る。private は共有の溜め置きを止め、頁と JSON は人ごとに替わるので
#   no-store も付ける。絵と紙は同じ人の端末では溜めてよい（private だけ）ので、読み込みは遅くしない
# - ほかのサイトの枠に入れさせない（クリックジャッキングの備え）。同じ origin の枠は開く（SAMEORIGIN・'self'）: 試験は手帖を同じ origin の
#   親の頁の iframe で開いて本物の順で押す（test_photo_attach_walk ほか）ので、DENY・'none' にするとその枠が開かず止まった（別の目の指摘）
# - Referrer-Policy は same-origin にする。no-referrer にすると、ブラウザは同じ頁からのフォームの POST に Origin: null を付け、
#   書き込みの口の Origin の照らし（同じ頁から来た物だけを受ける）が全部断る形になるため
def guard_headers(ctype):
    dynamic = ctype.startswith("text/html") or ctype.startswith("application/json")
    return (("Cache-Control", "private, no-store" if dynamic else "private"),
            ("X-Frame-Options", "SAMEORIGIN"),
            ("Content-Security-Policy", "frame-ancestors 'self'"),
            ("Referrer-Policy", "same-origin"))


class Handler(BaseHTTPRequestHandler):
    timeout = 20
    # Server の見出しに Python の版を出さない（公開の前の点検）。
    server_version = "utsushi"
    sys_version = ""

    def log_message(self, *a):  # 記録の文を記録に残さない
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8", headers=()):
        if isinstance(body, str) and ctype.startswith("text/html") and getattr(self.server, "public_open", False):
            body = without_notes(body)
        if isinstance(body, str) and ctype.startswith("text/html") and getattr(self, "_lang", "ja") == "en" and not re.match(r"/en(?:[/?#]|$)", self.path):
            from . import i18n  # 全頁の英語（窓口の決め 130735 の案 B）。作る側は日本語のまま作り、出口で表を引いて替える

            body = i18n.page_en(body)
        elif isinstance(body, str) and ctype.startswith("text/html") and getattr(self, "_lang", "ja") == "easy" and not re.match(r"/en(?:[/?#]|$)", self.path):
            from . import i18n  # やさしい日本語（3 つ目の言葉・web.i18n の頭の注）。表に無い字は元の日本語のまま

            body = i18n.page_easy(body)
        if getattr(self, "_lang_cookie", None):
            headers = (*headers, self._lang_cookie)
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        given = {k.lower() for k, _ in headers}
        for k, v in guard_headers(ctype):
            if k.lower() not in given:  # 口が自分で決めた頭（動画の口の no-store など）を上書きしない
                self.send_header(k, v)
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _refuse(self, code, reason, title="開けません", **kw):
        """断りの頁を出す。_look は要求の始めに決まるが、そこで落ちた時も頁を出せるように既定を持つ（#136）。"""
        self._send(code, skinmod.notice(title, reason, getattr(self, "_look", skinmod.DEFAULT), **kw))

    def _busy(self, wait, form):
        """書き込みが多すぎる時の断り（429）。字は全体の受け皿と同じ物で、新しい字を足さない。JSON で受ける口には、その口の形で返す。"""
        headers = [("Retry-After", str(wait))]
        if self.path.endswith("/record-json"):
            return self._send(429, json.dumps({"error": BUSY}, ensure_ascii=False), "application/json; charset=utf-8", headers)
        if self.path.endswith("/talk") and form.get("json") == "1":
            return self._send(429, json.dumps({"kept": False, "why": BUSY}, ensure_ascii=False), "application/json; charset=utf-8", headers)
        if self.path.endswith("/ask-json"):  # 手帖と作りながら見る頁は、答えの欄に text を出す
            return self._send(429, json.dumps({"text": BUSY, "from": "busy"}, ensure_ascii=False), "application/json; charset=utf-8", headers)
        return self._send(429, skinmod.notice("送れませんでした", BUSY, getattr(self, "_look", skinmod.DEFAULT)), headers=headers)

    def _host_ok(self):
        # DNS rebinding で外のサイトから手元の記録を読み書きさせないため、手元の名前だけを受ける。
        port = self.server.server_address[1]
        # 家の網に開いた時（--lan）は、この機械の網の中の番地と名前だけを足す。ほかの名前は今までどおり断る。
        extra = getattr(self.server, "lan_hosts", ())
        host = self.headers.get("Host", "")
        # デモの一周を外の機器から開く時（public_key あり）は、トンネルの名前を足す。名前は毎回変わるので形で受け、合言葉の門（_gate）で絞る。
        # 合言葉なしで開くデモ（public_open、本人の許可 11-05「デモサイト 2 つを他の人でも見れるように公開していいよ」）でも、トンネルの名前を受ける。
        if (getattr(self.server, "public_key", None) or getattr(self.server, "public_open", False)) and re.fullmatch(TUNNEL_HOST, host):
            return True
        return host in (f"127.0.0.1:{port}", f"localhost:{port}", *(f"{h}:{port}" for h in extra))

    def _origin_ok(self):
        # トンネルの先は https、手元は http。どちらも同じ Host の頁から来た物だけを受ける（別のサイトから送らせない）。
        host = self.headers.get("Host", "")
        ok = {f"http://{host}"} | ({f"https://{host}"} if getattr(self.server, "public_key", None) or getattr(self.server, "public_open", False) else set())
        return self.headers.get("Origin") in ok

    def _gate(self):
        """合言葉の門。public_key がある時だけ働く。URL を知っただけの人に記録と写真を見せないため。通れば True、断った時は返事を送って False。
        合言葉は最初の 1 回だけ ?k= で受け、Cookie に移して URL から消す（履歴や画面に長く残さない）。"""
        key = getattr(self.server, "public_key", None)
        if not key:
            return True
        from . import shiori_open

        # しおりの開く道（GET と POST /s/<22 字> の 2 つだけ）は門の外（統括の決め 11-08）。絵の順が鍵なので、合言葉を知らない人も絵の頁までは来る。
        # 見分けは ? より前の道の fullmatch。startswith にしない（% の入った字・末の /・/s/close・//s/… は門の中に残す）
        if self.command in ("GET", "POST") and shiori_open.PATH.fullmatch(self.path.partition("?")[0]):
            return True
        jar = {}
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            jar[k] = v
        if hmac.compare_digest(jar.get("utsushi_k", "").encode(), key.encode()):
            return True
        # しおりで開いた画面（開いた画面の印・20 分の内）も門を通す。合言葉の値そのものは端末に渡さない（別の目の止め S1 の代わりの形）。
        # 使えなくした・止めた・とじた・開き直したしおりの画面は、台帳が通さない。最後に使った時刻の書き直しは台帳が 1 分に 1 回に絞る
        from omochae import shiori

        if jar.get(shiori_open.COOKIE) and shiori.fresh(jar[shiori_open.COOKIE]):
            shiori.touch(jar[shiori_open.COOKIE])
            return True
        path, _, query = self.path.partition("?")
        given = urllib.parse.parse_qs(query).get("k", [""])[0]
        if self.command == "GET" and given and hmac.compare_digest(given.encode(), key.encode()):
            rest = urllib.parse.urlencode([(a, b) for a, b in urllib.parse.parse_qsl(query) if a != "k"])
            self._send(303, "", headers=[("Location", path + (f"?{rest}" if rest else "")),
                                         ("Set-Cookie", f"utsushi_k={key}; Max-Age=604800; Path=/; HttpOnly; Secure; SameSite=Lax")])
            return False
        # 合言葉を落とした人が最初に見る頁。帯もリンクも出さず、頁の中身と玩具の名前を見せない
        self._refuse(403, "合言葉付きのリンクから開いてください。リンクを渡した人に聞いてください。", "合言葉が要ります", links=(), bare=True)
        return False

    def _pick_look(self):
        """この要求の皮。サーバを立てた時に 1 つに決める（serve の look、命令の --look）。
        なぜ切り替えないか: 本人の決定（11-05 朝）「日本画かジンで行く。それぞれのデザインのサイトを 2 つ作る」。1 つのサイトの中で
        見た目を切り替える形ではなく、皮ごとに 1 サイト。cookie も ?look= も見ない（前の形の名残を受け付けると 2 サイトの線が崩れる）。"""
        self._look = getattr(self.server, "look", skinmod.DEFAULT)
        self._pick_lang()

    def _kiroku(self, sid, msg="", errors=(), err_at="", filled=None, look=None, path=None, at=""):
        """手帖の記録の頁（/toy/<印>/techo/kiroku）。記録の札の説明と次の版が通らなかった時（422）も、この頁を理由の文と書いた字つきで返す:
        つくるの頁から記録の札を外した（本人の言葉 11-08「復元の記録などはすべてもちよるに統合する。」）ので、前の玩具の頁の札の返事の代わり"""
        from . import nokosu, techo_site, techo_step, think_sheet

        sheet = hypotheses.sheet_of(sid)["id"]
        # 記入の節の紙は手帖と同じ決め方（たたき台か、この画面の案の紙・techo_step.paper_of）。刷った紙が無い時は記入の節を出さず、紙を作る道
        paper = techo_step.paper_of(sid, [sheet] if printed_versions(sid, sheet) else [], think_sheet.latest_mine(self, sid))
        from omochae import shiori

        body = techo_site.records_page(sid, msg=msg, at=at, up_key=self._up_key(), rec_key=self._rec_key(), public=getattr(self.server, "public_open", False), paper=paper,
                                       shiori_wait=shiori.pending_fresh(self._key_of(SHIORI_PENDING)),
                                       errors=errors, err_at=err_at, filled=filled)
        return skinmod.shell("手帖", body, look or self._look, "", path or f"/toy/{sid}/techo/kiroku", techo_site.STYLE + nokosu.STYLE, "techo")

    def _toy(self, sid, **kw):
        # 合言葉なしで開いた場では写真と動画を出さない（受け口が断るので、壊れた絵にしない。J-028）。
        # 話した本人の案（think_sheet.mine）は、玩具の頁の記録の欄が選ぶ口に使っていた。欄はのこすへ寄せたので渡さない（本人の答え Q3）
        return toy_page(sid, look=self._look, photos=not getattr(self.server, "public_open", False), up_key=self._up_key(), rec_key=self._rec_key(), **kw)

    def _pick_lang(self):
        """頁の言語（全頁の英語。web.i18n・窓口の決め 130735 の案 B）。?lang=en か ?lang=ja で選び、ブラウザを閉じれば消える cookie に持つ。道は日本語の頁と同じ。
        前からの英語の頁（/en と /en/toy/<印>）は別の作りで、ここでは替えない（もう英語なので）。"""
        _, _, query = self.path.partition("?")
        pick = urllib.parse.parse_qs(query).get("lang", [""])[0]
        self._lang_cookie = None
        if pick in ("en", "ja", "easy"):
            self._lang = pick
            # 期限（Max-Age）を付けない: ブラウザを閉じれば消え、新しく開いた入口はいつも日本語から始まる（本人の言葉 11-08「サイトトップのデフォルトの表示は日本語で。」）。
            # 前は 1 年の期限で、一度 English を押した端末は次の日も英語の入口が出た。開いている間は cookie が残るので、頁をたどっても選んだ言葉のまま
            self._lang_cookie = ("Set-Cookie", f"utsushi_lang={pick}; Path=/; SameSite=Lax")
            return
        self._lang = "ja"
        for part in self.headers.get("Cookie", "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == "utsushi_lang" and value in ("en", "easy"):
                self._lang = value

    def do_GET(self):
        try:
            self._pick_look()
            if self._gate():
                self._get()
        except Exception as e:
            failure_log.request_failed("GET", self.path, e)
            self._refuse(500, "うまく表示できませんでした。少し待って、もう一度開いてください。")

    def do_POST(self):
        try:
            self._pick_look()
            if self._gate():
                self._post()
        except PrintBusy:
            self._busy(int(PRINT_WAIT), {})
        except Exception as e:
            failure_log.request_failed("POST", self.path, e)
            self._refuse(500, BUSY, "送れませんでした")

    def _get(self):
        if not self._host_ok():
            # 手元の名前でない Host には、その名前へ戻るリンクを出さない
            return self._refuse(403, "受け付けられません", links=(), bare=True)
        path, _, query = self.path.partition("?")
        qs = urllib.parse.parse_qs(query)
        look = self._look
        from .looks import PAGES

        # 入口はこのサイトの皮の入口（白の展示か黒のジン、--look）。別の皮の入口はこのサイトには無い（404）。
        # 大判（A）と外した 3 案は出さない（本人の決定 11-05 朝「日本画かジンで行くから、他のデザインは要らない」）。
        if path == "/":
            return self._send(200, PAGES[look](photos=not getattr(self.server, "public_open", False)))
        m = re.fullmatch(r"/s/([A-Za-z0-9_-]{22})", path)
        if m:
            return self._shiori_get(m.group(1))
        m = re.fullmatch(r"/look/([a-z]+)", path)
        if m and m.group(1) == look:
            return self._send(200, PAGES[look](photos=not getattr(self.server, "public_open", False)))
        if path == "/kaizen":
            # 審査用の頁「良くするための一周 ♻︎」（本人の言葉 11-07・題は 11-08）。記録済みの 1 周を段ごとに見せる。合言葉なしの場でも開く（repo の中の記録だけを出す）
            from . import kaizen_judge
            return self._send(200, kaizen_judge.page(look, path))
        m = re.fullmatch(r"/kaizen/video/([^/]+)", path)
        if m:
            # 審査用の頁の動画（御来迎が開く所。公開の場のデータの置き場の、確かめた印のある物だけ。web/kaizen_kata.py）。iPhone の Safari のために Range を受ける
            from . import kaizen_kata
            data = kaizen_kata.video_bytes(urllib.parse.unquote(m.group(1)))
            if data is None:
                return self._send(404, "無い")
            plain = (("Accept-Ranges", "bytes"),)
            span = byte_range(self.headers.get("Range"), len(data))
            if span is False:
                return self._send(416, b"", "video/mp4", plain + (("Content-Range", f"bytes */{len(data)}"),))
            if span:
                return self._send(206, data[span[0]:span[1] + 1], "video/mp4", plain + (("Content-Range", f"bytes {span[0]}-{span[1]}/{len(data)}"),))
            return self._send(200, data, "video/mp4", plain)
        m = re.fullmatch(r"/kaizen/photo/(\d{1,2})/([^/]+)", path)
        if m:
            # 審査用の頁のワークショップの写真（サーバの記録の置き場の、人が確かめた物だけ。web/kaizen_ws.py）。出さない物はどれも 404
            from . import kaizen_ws
            data = kaizen_ws.photo_bytes(int(m.group(1)), urllib.parse.unquote(m.group(2)))
            return self._send(200, data, "image/jpeg") if data else self._send(404, "無い")
        m = re.fullmatch(r"/about/loop-figure/([^/]+)", path)
        if m:
            # 説明の頁の学びの輪の生成の絵（本人の言葉 11-07「qwen2.1 でもっと綺麗な絵を」・公開の場のデータの置き場の確かめた物だけ。web/loop_figure.py）
            from . import loop_figure
            data = loop_figure.image_bytes(urllib.parse.unquote(m.group(1)))
            return self._send(200, data, "image/jpeg") if data else self._send(404, "無い")
        if path == "/about":
            from . import about
            return self._send(200, about.page(look, path))
        if path == "/otona":
            from . import otona
            return self._send(200, otona.page(look, path))
        # 作る側の頁は、合言葉なしで開いたデモには出さない: 聞いた言葉と感想の文がそのまま読める頁で、名前は機械では落とせないため（J-027・J-028）。
        if path.startswith("/loop") and getattr(self.server, "public_open", False):
            return self._send(404, "見つかりません")
        if path == "/loop":
            # 改善の輪の一覧（本人の方針 11-05）。サイト側が輪を回す所で、学ぶ人の順路の帯には入れない。
            from . import kaizen
            return self._send(200, kaizen.page(look, path))
        if path == "/loop/ayumi":
            # 型紙の版の歩み（本人の希望 11-06）。前の履歴・良くした所・知見・共通の知見・どのループか。
            from . import ayumi
            return self._send(200, ayumi.page(look, path))
        m = re.fullmatch(rf"/loop/({SID})", path)
        if m and m.group(1) in sources():
            # その玩具の工作の様子（聞かれた事・止まった所・感想・動きの札）。作る側が読む集計で、学ぶ人の頁には出さない。
            from . import kaizen
            return self._send(200, kaizen.toy_page(m.group(1), look, path))
        if path == "/toys":
            # 入口を えらぶ にした（本人のサイト体験レビュー 11-07 の 4「入口と選ぶは分けない」）ので、えらぶ の頁は入口へ送る。
            # 紙 1 枚の絞り込み（本人の言葉 11-05 の口）は、絞った並びの頁として残す（入口に同じ絞り込みは置かない）
            if qs.get("paper", [""])[0] != "1":
                return self._send(302, "", headers=[("Location", "/")])
            from . import toys
            return self._send(200, toys.page(look, path, paper=True))
        if path == "/gallery":
            from . import techo_site
            # のこした後はここに着く（窓口の決定 11-06 夜・案 A）。今残した 1 つは、記録を残した画面の鍵（記録の鍵）で見分けて頭に出す。返事の文は ?msg= で受ける
            # 今残した 1 つの札（記録の番号と感想の字）は、合言葉なしの場では出さない（J-028）。場の見分けを photos の引数に頼らず、
            # 記録の鍵を渡さない形で閉じる: 公開の場の見分けを別の引数に替える直しと合わせても、札が出ないように。
            opened = getattr(self.server, "public_open", False)
            return self._send(200, skinmod.shell("作った物", techo_site.gallery_page(sources(), public=opened, msg=qs.get("msg", [""])[0], rec_key=None if opened else self._rec_key()), look, "/gallery", path, techo_site.GALLERY_STYLE, description=techo_site.GALLERY_LEAD))
        # 図鑑の本の頁（本人の決定 11-06。玩具の絵がある頁を 1 コマずつ）。頁の全体の絵は ingest が git の外に取る
        m = re.fullmatch(r"/zukan/hon/(\d{1,2})", path)
        if m:
            from . import zukan_hon
            if int(m.group(1)) in zukan_hon.frames():
                return self._send(200, zukan_hon.page(int(m.group(1)), look, path))
        m = re.fullmatch(r"/zukan/hon/R(\d{7})-([LR])\.jpg", path)
        if m:
            from omochae import ingest
            from . import zukan_hon
            face = (int(m.group(1)), m.group(2))
            if face in ingest.book_faces() and zukan_hon.face_file(*face).exists():
                return self._send(200, zukan_hon.face_file(*face).read_bytes(), "image/jpeg")
        # 図鑑の目次（/zukan）と玩具ごとの図鑑の頁（/zukan/<印>）は外した（本人の言葉 11-08「図鑑のページ要らない」）。道は無い（断りの 404）。
        # 図鑑の本の頁（上の /zukan/hon）と、くずし字を読む（下の /zukan/<印>/yomi・道の名はそのまま）は残す
        # くずし字を読む（f14）。書く前の頁は確かめた読みを出さない。読みが先の線と印の床は kuzushi.py が持つ。
        if path == "/en":
            # 英語の入口と玩具の頁（J-030 の段 1）。
            from . import en
            return self._send(200, en.index_page(look, path))
        m = re.fullmatch(rf"/en/toy/({SID})", path)
        if m and m.group(1) in sources():
            from . import en
            return self._send(200, en.toy_page(m.group(1), look, path, printed=qs.get("printed", [""])[0] == "1"))
        m = re.fullmatch(rf"/zukan/({SID})/yomi", path)
        if m and m.group(1) in sources():
            from . import kuzushi
            return self._send(200, kuzushi.page(m.group(1), look=look))
        m = re.fullmatch(rf"/toy/({SID})/splat(?:/(\d{{1,2}})\.jpg)?", path)
        if m and m.group(1) in sources():
            # 作った実物の立体とエンジンの 3D を並べて一緒に回す頁と、実物の絵（本人の決定 11-07・web/splat_pair.py）。
            # 絵は人が確かめた物だけ（サーバの記録の置き場）。無い玩具・確かめていない玩具は 404
            from . import splat_pair
            if m.group(2) is not None:
                data = splat_pair.frame_bytes(m.group(1), int(m.group(2)))
                return self._send(200, data, "image/jpeg") if data else self._send(404, "無い")
            body = splat_pair.page(m.group(1), look, path)
            return self._send(200, body) if body else self._send(404, "無い")
        m = re.fullmatch(rf"/toy/({SID})/kumitate", path)
        if m:
            # 手順どおりに組み立てる様子を立体で見る頁（本人の決定 11-05、#331）。
            from . import kumitate
            # 立体の無い玩具も、組み方の文と絵の頁として開く（本人の決まり 11-06: 全種の組み立て頁に寄せる）
            if m.group(1) not in sources() or not kumitate.has(m.group(1)):
                return self._send(404, "無い")
            return self._send(200, kumitate.page(m.group(1), look, path))
        # 作業の頁に重ねる形（本人の指示 11-07「HMD か iPhone カメラでオーバーレイする形での作業を前提に、作業ページを作ろう。」）。
        # 下地は試作の枝 try/hmd の頁（hmd.py）。/toy/<玩具>/kasane は後ろのカメラの映像に重ねる形、/toy/<玩具>/kasane/hmd は透けて見える画面の形。
        # 組み立ての書き方がある玩具だけ。手帖からの道は、口の字が決まってから足す（新しい字は本人の確かめ）
        m = re.fullmatch(rf"/toy/({SID})/kasane(/hmd)?", path)
        if m:
            from . import hmd
            if m.group(1) not in sources() or not hmd.available(m.group(1)):
                return self._send(404, "見つかりません")
            return self._send(200, hmd.page(m.group(1), look, cam=not m.group(2)))
        m = re.fullmatch(rf"/toy/({SID})/tsukuru", path)
        if m and m.group(1) in sources():
            # 作りながら見る（観察 A の試作、本人の案 11-05）。机の端に立てた端末に手本と返事を出し、鏡は端末の中だけ（tsukuru.py）。
            # 刷った紙が無い時は開かない（手順は刷った版の物なので）。
            sid = m.group(1)
            from . import think_sheet
            # 話した考えから作った案は、作った本人の画面にだけ開く。工夫がその紙に付くように（本人の描く一周の順。ループ1、#335）。
            printed = [h["id"] for h in hypotheses.load(sid)["hypotheses"] if printed_versions(sid, h["id"])] + [o for o in think_sheet.mine(self, sid) if printed_versions(sid, o)]
            # 紙の印が無ければ、本人の案、無ければたたき台の 1 枚を開く（J-032）。刷った物の先頭を開くと、ほかの仮説だけを刷った置き場でその紙が開く。
            hid = qs.get("h", [""])[0] or think_sheet.latest_mine(self, sid) or hypotheses.sheet_of(sid)["id"]
            if hid not in printed:
                # 文が頁の頭より 1 画面下に出ないよう、#121 の手帖と同じく節へ送る（#289）
                msg = urllib.parse.quote("先に紙を作ると、作りながら見る頁が開きます")
                return self._send(303, "", headers=[("Location", f"/toy/{sid}?msg={msg}&at=kasetsu#kasetsu")])
            from api import ask

            from . import tsukuru
            try:
                n = int(qs.get("n", ["1"])[0])
            except ValueError:
                n = 1
            # 版は開いた時に決めて URL で持つ（作っている途中で別の人の版が刷られても、手順の文が変わらないように）。
            v = int(qs["v"][0]) if qs.get("v", [""])[0].isdigit() else None
            return self._send(200, tsukuru.page(sid, hid, look, step=n, event=qs.get("ev", [""])[0], version=v, ai=ask._key_present() and not getattr(self.server, "public_open", False)))
        m = re.fullmatch(rf"/toy/({SID})/techo", path)
        if m and m.group(1) in sources():
            # 手帖は入口のサイトの中の一続きの頁（本人の方向転換、11-04）。1 手 1 画面で、頭の帯を置かない（本人の決定 11-05、#87。techo_step.py）。
            sid = m.group(1)
            sheet = hypotheses.sheet_of(sid)["id"]
            printed = [sheet] if printed_versions(sid, sheet) else []  # 手帖の紙もたたき台の 1 枚だけ（J-032）
            from . import techo_step, think_sheet
            # この画面が話した考えから作った本人の紙があれば、それを作る（一番新しい物。ほかの人の案は出さない。#335 ループ1）。
            own = think_sheet.latest_mine(self, sid)
            try:
                n = int(qs.get("n", ["1"])[0])
            except ValueError:
                n = 1
            # 版は開いた時に決めて URL で持つ（作りながら見る頁と同じ）。
            v = int(qs["v"][0]) if qs.get("v", [""])[0].isdigit() else None
            return self._send(200, techo_step.page(sid, printed, look, step=n, version=v, own=own, public=getattr(self.server, "public_open", False)))
        m = re.fullmatch(rf"/toy/({SID})/techo/kiroku", path)
        if m and m.group(1) in sources():
            # 手帖の記録の頁（上げた物とフィードバック）。作る頁から分けた（#87）。組み方は _kiroku（記録の札の 422 の返事と同じ頁）
            return self._send(200, self._kiroku(m.group(1), msg=qs.get("msg", [""])[0], at=qs.get("at", [""])[0], look=look, path=path))
        # 作った物の写真の小さい写し（web.made。入口の札と玩具の頁の頭は、上げた元の写真 3.7MB ほどを読まない。1 枚 100KB 以下の線）。
        # 見せてよいかは元の写真と同じ線（media_review.shown_to）で決める
        m = re.fullmatch(r"/record/(R-\d{4,})/media/(m\d+\.(?:jpg|png))/small", path)
        if m:
            from . import made, techo_site
            f = techo_site.media_dir(m.group(1)) / m.group(2)
            if f.exists() and media_review.shown_to(m.group(1), [m.group(2)], self._up_key()):
                small = made.small_photo(f)
                if small:
                    return self._send(200, small, "image/jpeg")
            return self._refuse(404, "リンクが古いか、道が違うようです。", "見つかりません")
        m = re.fullmatch(r"/record/(R-\d{4,})/media/(m\d+\.(?:jpg|png|mp4|mov))", path)
        if m:
            from . import techo_site
            f = techo_site.media_dir(m.group(1)) / m.group(2)
            # 人や声が入ると確かめた物は、どの頁からも返さない（本人の決定 11-05、#314）。確認の前の物は、上げた本人の画面にだけ返す。
            # 合言葉なしで開いたデモも同じ線（本人の決定 11-06「公開の場で上げた写真は、公開の場のギャラリーにも出します」）。
            if f.exists() and media_review.shown_to(m.group(1), [m.group(2)], self._up_key()):
                kind = {"jpg": "image/jpeg", "png": "image/png", "mp4": "video/mp4", "mov": "video/quicktime"}[f.suffix[1:]]
                data, plain = f.read_bytes(), (("Accept-Ranges", "bytes"),)
                span = byte_range(self.headers.get("Range"), len(data))
                if span is False:
                    return self._send(416, b"", kind, plain + (("Content-Range", f"bytes */{len(data)}"),))
                if span:
                    return self._send(206, data[span[0]:span[1] + 1], kind, plain + (("Content-Range", f"bytes {span[0]}-{span[1]}/{len(data)}"),))
                return self._send(200, data, kind, plain)
        m = re.fullmatch(rf"/toy/({SID})", path)
        if m and m.group(1) in sources():
            # 型紙の窓の選び（仮説・紙の種類・版）は URL で持つ。JS なしで切り替えられ、戻るで前の紙に戻れる。
            kind = {"sheet": "", "tejun": "_tejun", "after": "_after"}.get(qs.get("kind", ["sheet"])[0], "")
            # 版を言わなければ一番新しい版（0 は「無指定」で、窓が最新に直す）。次の版を刷った後に開く時に、古い版が先に出ないため。
            try:
                v = int(qs.get("v", ["0"])[0])
            except ValueError:
                v = 0
            see = qs.get("see", [None])[0]
            # 窓は型紙だけを出す（本人の決まり 11-06「文章のプリントは廃止」）。前は kind=after で試した後の紙をここで作って窓に出した（#320）。
            # 前に配ったリンクのために /sheet/…_after の道は残し、紙はそこで開く時にだけ作る（ensure_after）
            from . import think_sheet
            return self._send(200, self._toy(m.group(1), msg=qs.get("msg", [""])[0], at=think_sheet.allowed_at(self, m.group(1), qs.get("at", [""])[0]), see=see, kind=kind, v=v, path=path))
        # 型紙の版の歩みの額の絵（エンジンが組ごとに出した、刷った紙の 1 枚目を縮めた物。生成物なので repo の外の out/history に置く）。
        # 組の名の形だけを受け、置き場の外のファイルを開かない（ban_ayumi.picture_file）。合言葉なしの場でも出す（刷った型紙で、人の写真ではない）
        m = re.fullmatch(r"/history/sheets/([a-z]+-v[0-9]{1,3})\.png", path)
        if m:
            from . import ban_ayumi
            f = ban_ayumi.picture_file(m.group(1))
            return self._send(200, f.read_bytes(), "image/png") if f else self._send(404, "無い")
        m = re.fullmatch(r"/hokusai/([A-Za-z0-9-]+)\.jpg", path)
        if m:
            # 北斎漫画の絵（国立国会図書館・PDM）。記録にある名前だけを出す。玩具の絵の道とは分ける（取り違えないため）。
            from omochae import hokusai as hk
            if m.group(1) in hk.names() and hk.has(m.group(1)):
                return self._send(200, hk.path_of(m.group(1)).read_bytes(), "image/jpeg")
            return self._send(404, "無い")
        # ワークショップで作られた物の写真の小さい写し（web.workshop。表に載った物だけ・合言葉なしの場でも返す。本人の言葉 11-07 夜）
        m = re.fullmatch(r"/workshop/(\d{8}/p\d{2}\.jpg)/small", path)
        if m:
            from . import workshop
            small = workshop.small(m.group(1))
            if small:
                return self._send(200, small, "image/jpeg")
            return self._refuse(404, "リンクが古いか、道が違うようです。", "見つかりません")
        # 玩具が載る頁の全体（原画と歌。本人の指示 11-06）。合言葉なしの場でも出す（公開の古い本の絵で、人の写真ではない）
        m = re.fullmatch(rf"/picture/({SID})/page", path)
        if m and m.group(1) in sources():
            from . import genga
            page = genga.page_file(source(m.group(1)))
            if page.exists():
                return self._send(200, page.read_bytes(), "image/jpeg")
        # えらぶ の敷き詰めの小さい写し（toys.small_picture。幅 1600px の切り抜きを 83 枚読まないため）
        # 浮かぶ玩具の試作の輪郭の絵（web.ukabu・out/ukabu の生成物）
        m = re.fullmatch(rf"/ukabu/({SID})\.webp", path)
        if m and (ROOT / "out/ukabu" / f"{m.group(1)}.webp").exists():
            return self._send(200, (ROOT / "out/ukabu" / f"{m.group(1)}.webp").read_bytes(), "image/webp")
        m = re.fullmatch(rf"/picture/({SID})/(small|mid)", path)
        if m:
            from . import toys
            small = toys.small_picture(m.group(1), m.group(2))
            if small:
                return self._send(200, small, "image/jpeg")
        m = re.fullmatch(rf"/picture/({SID})", path)
        if m and (ROOT / "out/sources" / f"{m.group(1)}.jpg").exists():
            return self._send(200, (ROOT / "out/sources" / f"{m.group(1)}.jpg").read_bytes(), "image/jpeg")
        # 刷った紙。PDF（刷る）のほかに PNG と SVG（画面で見る、要件の S-01）。試した後の紙はどの形でも記録の前は渡さない。
        m = re.fullmatch(rf"/sheet/({SID})/((?:H-[A-Z0-9]+|OWN-\d+)_v\d{{1,6}}(?:_tejun|_after|_free)?)\.(pdf|svg|png)", path)  # 版は 6 桁まで: 桁の多い手作りの URL を、int の上限の 500 でなく 404 にする
        if m and m.group(1) in sources():
            sid, stem, ext = m.groups()
            hid = re.split(r"_v\d+", stem)[0]
            if hid.startswith("OWN-"):
                # 話した字が刷られた紙は、作った本人の画面からだけ。合言葉なしの場では OWN-n の紙を開かない（J-028）。在るかどうかも言わない（下と同じ 404）。
                from . import think_sheet
                if not think_sheet.opens(self, sid, hid, after=stem.endswith("_after")):
                    return self._refuse(404, "リンクが古いか、道が違うようです。", "見つかりません")
            if stem.endswith("_after") and hid not in {r["hypothesis_id"] for r in records.all_records(sid)}:
                # 道の行き先は記録の頁（のこす）。玩具の頁の記録の欄は本人の答え 11-07 夕の Q3 で のこす へ寄せたので、#kiroku に着いても欄が無い
                # （道 1 本だけ）。1 回で着くよう直接向ける（字は替えない。別の目の指摘 11-07）
                return self._refuse(403, "試した記録を残してから開きます。", links=((f"/toy/{sid}/techo/kiroku", "記録の欄へ"),))
            f = out_dir(sid) / f"{stem}.{ext}"
            if stem.endswith("_after"):
                ensure_after(sid, hid, int(re.search(r"_v(\d+)", stem).group(1)))
            if f.exists():
                # インラインの印: ブラウザが PDF を表示できる機器では、落とさずにその場で開く（本人の指示 11-05「クリックで画面に型紙が出る形」）。
                return self._send(200, f.read_bytes(), {"pdf": "application/pdf", "svg": "image/svg+xml", "png": "image/png"}[ext],
                                  [("Content-Disposition", f'inline; filename="{stem}.{ext}"')])
        self._refuse(404, "リンクが古いか、道が違うようです。", "見つかりません")

    def _form(self):
        # 別のサイトの頁から手元の記録へ送らせないため、同じ出所のフォームだけを受ける。
        if not self._origin_ok():
            return None
        if self.headers.get("Content-Type", "").split(";")[0] != "application/x-www-form-urlencoded":
            return None
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return None
        if not 0 <= length <= MAX_FORM:
            return None
        return {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True).items()}

    def _key_of(self, cookie):
        """この画面が持つ鍵。無ければ None。who と同じ sessionStorage では絵の GET にも頁の GET にも載らないので、本人の画面の見分けは cookie に置く。"""
        for part in self.headers.get("Cookie", "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == cookie and value:
                return value
        return None

    def _key_cookie(self, cookie, key=""):
        """鍵の cookie。ブラウザを閉じれば消えるように Max-Age を付けない。key が空なら消す。外から開く場（合言葉付き）は https なので Secure を付ける。"""
        secure = "; Secure" if getattr(self.server, "public_key", None) else ""
        return ("Set-Cookie", f"{cookie}={key}; Path=/; HttpOnly; SameSite=Lax{secure}" + ("" if key else "; Max-Age=0"))

    def _up_key(self):
        """この画面が写真を上げた時に渡した鍵（media_review.claim）。"""
        return self._key_of(UP_COOKIE)

    def _up_close(self):
        """記録を残すのが交代の区切り（who を作り直すのと同じ）。同じ機械の次の人に、前の人の確認の前の写真を出さない。"""
        return [self._key_cookie(UP_COOKIE)] if self._up_key() else []

    def _rec_key(self):
        """この画面が記録を残した時に渡した鍵（records.claim）。"""
        return self._key_of(REC_COOKIE)

    def _rec_cookie(self, rid):
        """記録を残した画面へ鍵を渡す行。次の記録が残ると上書きされ、前の記録には書けなくなる（記録を残すのが交代の区切り。机の端の 1 台を順に使う場）。"""
        key = secrets.token_urlsafe(18)
        records.claim(rid, key)
        return self._key_cookie(REC_COOKIE, key)

    def _done(self, sid, msg, back="", see=None, anchor="kiroku", v=None, fresh=False, headers=()):
        # 手帖から送った物は手帖へ戻す（本人「アップロードも手帖から。フィードバックも手帖」、11-04）。玩具の頁へ戻す時は、刷った紙の窓か記録の所へ。
        if back == "techo":
            # 着く印: 既定は上げる節（#mine）。作りながら見る頁の組み上がりからは記入の節（#kinyu・頁の頭）へ着き、返事の字もそこに出す
            # （別の目の確かめ 11-08: #mine は頁の一番下で、記入の節を飛び越えた）
            at = "kinyu" if anchor == "kinyu" else "mine"
            return self._send(303, "", headers=[("Location", f"/toy/{sid}/techo/kiroku?msg={urllib.parse.quote(msg)}{'&at=kinyu' if at == 'kinyu' else ''}#{at}"), *headers])
        # 記録の札（錨が記録の番号）へ戻す時は、手帖の記録の頁の記録の並びへ: つくるの頁から記録の札を外した（本人の言葉 11-08「復元の記録などはすべて
        # もちよるに統合する。」）。fresh の合図と、写真の鍵を閉じる行（_up_close）は、玩具の頁へ戻す時と同じに付ける: 付けないと、同じ機械の次の人が
        # 前の人の写真の口を持ったままになる（別の目の試験 test_photo_owner_only・test_who_fresh が見る）
        if re.fullmatch(r"R-\d{4}", anchor or ""):
            mark = "&fresh=1" if fresh else ""
            return self._send(303, "", headers=[("Location", f"/toy/{sid}/techo/kiroku?msg={urllib.parse.quote(msg)}{mark}#mine"), *headers] + (self._up_close() if fresh else []))
        extra = (f"&see={see}&kind=sheet" + (f"&v={v}" if v else "")) if see else ""
        # fresh: 記録を残した時の合図。戻った頁で、その場限りの印を作り直す（skin.WHO_SCRIPT）。通らなかった時はここに来ない。
        extra += "&fresh=1" if fresh else ""
        self._send(303, "", headers=[("Location", f"/toy/{sid}?msg={urllib.parse.quote(msg)}&at={anchor}{extra}#{anchor}"), *headers] + (self._up_close() if fresh else []))

    def _shiori_get(self, token):
        """しおりの道の GET（web.shiori_open）。公開の場は断る（照らさず数えない）。開いた画面ならそのしおりの記録、まだなら絵の頁。"""
        from omochae import shiori

        from . import shiori_open
        if getattr(self.server, "public_open", False):
            return self._send(403, shiori_open.notice(shiori_open.PUBLIC_REFUSE, self._look))
        if shiori.status(token) != "open":
            return self._send(404, shiori_open.notice(shiori_open.CANNOT, self._look))
        screen = self._key_of(shiori_open.COOKIE)
        if screen and shiori.token_of(screen) == token and shiori.fresh(screen):
            return self._send(200, shiori_open.opened_page(screen, self._look))
        return self._send(200, shiori_open.picture_page(token, self._look))

    def _shiori_post(self, token, form):
        """押した順を照らす（止めは台帳の中で、当たりの前に効く）。当たった時だけ、開いた画面の印の cookie を渡す。合言葉の cookie は渡さない。"""
        from omochae import shiori

        from . import shiori_open
        nonce = secrets.token_urlsafe(16)
        got = shiori.check(token, shiori_open.order_of(form), writer(self.client_address[0], self.headers) or "local", screen=nonce)
        if got == "ok":
            secure = bool(getattr(self.server, "public_key", None))
            return self._send(303, "", headers=[("Location", f"/s/{token}"), shiori_open.cookie_line(f"{token}.{nonce}", secure)])
        if got == "wrong":
            return self._send(422, shiori_open.picture_page(token, self._look, shiori_open.WRONG))
        if got == "busy":
            return self._send(429, shiori_open.picture_page(token, self._look, shiori_open.WAIT), headers=[("Retry-After", "60")])
        return self._send(404, shiori_open.notice(shiori_open.CANNOT, self._look))

    def _sheet_shiori(self, sid, form):
        """型紙の PDF の後ろに、その場で作ったしおりの 1 頁（表と裏を同じ面に並べる・本人「しおりは同じ面に刷る。」）を足して返す（本人 11-08「しおりは型紙の PDF に一緒に刷る。」・設計 grove の
        state/shiori-in-sheet-20261108.md の 2.1 版）。合わせた物はどこにも書き出さない（台帳は印そのものを持たない決まり）。
        - 合言葉なしの場（公開デモ）は台帳を作らずに断る（頁の釦も出さない・受け口でも 2 重に・しおりはワークショップの場でだけ開くため）。
        - 決まった番地が無い場は、しおりを作らずに型紙だけを返す（替わる番地を刷らない・shiori.NoBase）。
        - 待ち: who と作り始めの回の印が届いた時だけ作る（台本の無い画面は送れないので作らない。結ぶのは開いた画面から）。待ちの印は cookie で渡し、
          押すたびに替わる（結べるのは一番新しく刷った 1 枚だけ）。
        - 返し方は今の /sheet/ と同じ inline（iPhone・iPad の Safari で別のタブに開いて刷れる）。no-store（鍵の入った物を残さない）。"""
        from omochae import shiori

        if getattr(self.server, "public_open", False):
            return self._send(403, "公開のデモでは使えません")
        stem = form.get("name", "")
        m = re.fullmatch(r"(H-[A-Z0-9]+)_v(\d+)", stem)
        # 刷れるのは頁に出すたたき台の紙だけ（J-032）。話した字の紙（OWN-n）と試した後の紙には、しおりを付けない
        if not m or m.group(1) != hypotheses.sheet_of(sid)["id"] or not (out_dir(sid) / f"{stem}.pdf").exists():
            return self._refuse(404, "リンクが古いか、道が違うようです。", "見つかりません")
        sheet = out_dir(sid) / f"{stem}.pdf"
        inline = [("Content-Disposition", f'inline; filename="{stem}.pdf"'), ("Cache-Control", "no-store")]
        who, run = form.get("who", ""), form.get("run", "")
        nonce = secrets.token_urlsafe(18) if re.fullmatch(r"[a-z0-9]{10}", who) and re.fullmatch(r"[a-z0-9]{6,40}", run) else ""
        try:
            made = shiori.make(pending={"nonce": nonce, "who": who, "run": run} if nonce else None)
        except shiori.NoBase:
            return self._send(200, sheet.read_bytes(), "application/pdf", inline)
        from omochae import shiori_card

        def build():
            card = shiori_card.pages(sid, made["token"], made["order"], int(m.group(2)), time.time(), shiori.base_url())
            return shiori_card.merge(sheet, card)
        try:
            pdf = _printing(build)
        except PrintBusy:
            shiori.revoke(made["token"])  # 返せなかったしおりは、紙にならないので使えなくする
            return self._send(429, "少し待ってから、もう一度押してください。", "text/plain; charset=utf-8", [("Retry-After", "30")])
        except Exception:
            shiori.revoke(made["token"])
            raise
        # 待ちの印は Max-Age なし（ブラウザを閉じれば消える）・HttpOnly（台本から読ませない）
        sp = [self._key_cookie(SHIORI_PENDING, nonce)] if nonce else []
        return self._send(200, pdf, "application/pdf", inline + sp)

    def _shiori_bind(self, rid, form):
        """記録を、型紙と一緒に刷ったしおりの待ちに結ぶ。確かめの画面で「外す」を押さなかった時（shiori=1）だけ。結んでも結ばなくても待ちの
        cookie は消す（結べるのは 1 回だけ）。返すのは足す見出しの並び。"""
        from omochae import shiori

        nonce = self._key_of(SHIORI_PENDING)
        if not nonce:
            return []
        if form.get("shiori") == "1":
            shiori.bind_pending(nonce, form.get("who", ""), form.get("run", ""), rid)
        return [self._key_cookie(SHIORI_PENDING)]

    def _shiori_add(self, rid):
        """しおりで開いた画面が残した記録を、そのしおりの並びに足す（開いていない画面では何もしない）。"""
        from omochae import shiori

        from . import shiori_open
        screen = self._key_of(shiori_open.COOKIE)
        if screen:
            shiori.add_record(screen, rid)

    def _post(self):
        if not self._host_ok():
            # 手元の名前でない Host には、その名前へ戻るリンクを出さない
            return self._refuse(403, "受け付けられません", links=(), bare=True)
        if getattr(self.server, "public_open", False) and re.fullmatch(r"/s/[A-Za-z0-9_-]{22}", self.path):
            # 公開の場ではしおりを開かない。フォームを読む前・書き込みの数の前に断り、照らさず数えない（開く道の設計 7.2 の 1）
            from . import shiori_open
            return self._send(403, shiori_open.notice(shiori_open.PUBLIC_REFUSE, self._look))
        m = re.fullmatch(r"/record/(R-\d{4,})/.*", self.path)
        if m and uploaded(m.group(1)):
            return self._refuse(404, "見つかりません")
        m = re.fullmatch(r"/record/(R-\d{4,})/media", self.path)
        if m:
            # 写真と動画はフォームでなく本体そのままで受ける。別のサイトから送らせないため、同じ出所だけを受ける。
            from . import techo_site
            if not self._origin_ok():
                return self._send(403, "受け付けられない送り方です")
            # 記録を残した画面からだけ受ける（記録の鍵）。番号は札に出る連番なので、番号だけで受けると、別の人の記録に写真を足せる。
            if not records.mine(m.group(1), self._rec_key()):
                return self._send(403, "受け付けられない送り方です")
            if (who := writer(self.client_address[0], self.headers)) and (wait := self.server.media_limit.wait(who)):
                return self._busy(wait, {})
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return self._send(411, "大きさが分かりません")
            if not 0 < length <= techo_site.MAX_MEDIA:
                return self._send(413, "1 つ 20MB まで")
            # 合言葉なしで開いたデモでも受ける（本人の決定 11-06「公開のデモでも写真と動画を上げられるようにしてください」）。前は 403 で断っていた。
            # 誰でも上げられる場なので、置き場の合計に上限を置く。断る時は本文を空にし、手帖は今ある字（写真か動画を上げられませんでした）を出す。
            # 確かめていない写真が皆に見える形にはしない線（J-021）は、出す側で守る（確かめる前は上げた本人の画面だけ。合言葉付きの場と同じ shown_to）。
            # 同時に送られた分は数え合わないので、合計は送られた数 × 20MB まで上限を越えうる（止めるより、機械を埋めない事が目的）。
            if getattr(self.server, "public_open", False) and techo_site.media_bytes() + length > techo_site.PUBLIC_MEDIA_TOTAL:
                return self._send(507, b"", "text/plain; charset=utf-8")
            # 声とカメラの区切り（声とカメラの設計 3 版の 3 節・統括の決め (3)）: 見出し X-Utsushi-Clip で渡す。上の照らし（Origin・記録の鍵・
            # 書き込みの止め・大きさ・公開の場の合計）は全部通した後で、save_media（m<n>）と claim の前で分ける。区切りは人に見せる物でないので
            # 確かめる前の並び（claim）に入れず、頁にもギャラリーにも出ない（voice/ の下・voice_text が置く）
            clip = self.headers.get("X-Utsushi-Clip")
            if clip is not None:
                return self._clip_post(m.group(1), clip, self.rfile.read(length))
            name, why = techo_site.save_media(m.group(1), self.headers.get("Content-Type", "").split(";")[0], self.rfile.read(length),
                                              keep_voice=getattr(self.server, "voice_tool", False))
            if not name:
                return self._send(422, why, "text/plain; charset=utf-8")
            from omochae import voice_text

            # 写した声は、返事の後に作業列で字にする（字にするのに数十秒かかり、上げた人を待たせないため）
            if (voice := voice_text.voice_dir(m.group(1)) / f"{pathlib.Path(name).stem}.mka").exists() and getattr(self.server, "voice_jobs", None):
                self.server.voice_jobs.jobs.put(voice)
            key = self._up_key() or secrets.token_urlsafe(18)
            media_review.claim(m.group(1), name, key)
            return self._send(201, name, "text/plain; charset=utf-8", [self._key_cookie(UP_COOKIE, key)])
        form = self._form()
        if form is None:
            # しおりの道（門の外）への断りは、当たる前の頁と同じ帯なしの形にする（頭の帯の道しるべから門の中へ行けると見せない・#631 の別の目の気づき）
            from . import shiori_open
            if shiori_open.PATH.fullmatch(self.path.partition("?")[0]):  # 門の外の見分けと同じく ? より前の道で見る（問い付きでも同じ形にそろえる）
                return self._send(403, shiori_open.notice("受け付けられない送り方です。頁を開き直して、もう一度送ってください。", getattr(self, "_look", skinmod.DEFAULT)))
            return self._refuse(403, "受け付けられない送り方です。頁を開き直して、もう一度送ってください。")
        if WRITE_PATHS.fullmatch(self.path) and (who := writer(self.client_address[0], self.headers)):
            wait = self.server.write_limit.wait(who)
            if wait:
                return self._busy(wait, form)
        if PRINT_PATHS.fullmatch(self.path) and (who := writer(self.client_address[0], self.headers)):
            wait = self.server.print_limit.wait(who)
            if wait:
                return self._busy(wait, form)
        m = re.fullmatch(r"/s/([A-Za-z0-9_-]{22})", self.path)
        if m:
            return self._shiori_post(m.group(1), form)
        if self.path == "/s/close":
            # とじる: 台帳の開いた画面の印も消す（cookie を消すだけだと、写した値が 20 分の切れまで生きる・止め S2）
            from omochae import shiori

            from . import shiori_open
            shiori.close(self._key_of(shiori_open.COOKIE) or "")
            return self._send(303, "", headers=[("Location", "/"), shiori_open.cookie_line("", bool(getattr(self.server, "public_key", None)))])
        if self.path == "/close":
            # のこした後の「この画面をとじる」（techo_site.close_form）。この画面の写真の鍵と記録の鍵を消し、その場限りの印も作り直させる（fresh）。
            # 鍵が無くても同じ返事にする（とじる事は誰にでもできてよく、鍵の有り無しを外へ見せない）。フォームなので _form の Origin の照らしが先に効く
            from . import techo_site
            return self._send(303, "", headers=[("Location", f"/gallery?msg={urllib.parse.quote(techo_site.CLOSED)}&fresh=1#ageta"),
                                                self._key_cookie(UP_COOKIE), self._key_cookie(REC_COOKIE)])
        m = re.fullmatch(rf"/toy/({SID})/reprint", self.path)
        if m and m.group(1) in sources():
            return self._reprint(m.group(1), form)
        m = re.fullmatch(rf"/toy/({SID})/sheet-shiori", self.path)
        if m and m.group(1) in sources():
            return self._sheet_shiori(m.group(1), form)
        m = re.fullmatch(rf"/toy/({SID})/(ask-json|record-json)", self.path)
        if m and m.group(1) in sources():
            return self._json_post(m.group(1), m.group(2), form)
        m = re.fullmatch(rf"/toy/({SID})/step", self.path)
        if m and m.group(1) in sources():
            return self._step_post(m.group(1), form)
        m = re.fullmatch(rf"/toy/({SID})/talk", self.path)
        if m and m.group(1) in sources():
            # 話す口（一周の声の部分、Issue #279）。ここに届くのは字のフォームだけ（上の _form が、音のファイルなど、ほかの形の本体を断る）。
            from . import hanasu
            return hanasu.post(self, m.group(1), form)
        m = re.fullmatch(rf"/toy/({SID})/(think-sheet|think-ok)", self.path)
        if m and m.group(1) in sources():  # 話した考えから紙を作り直す（ループ1、Issue #335。中身は think_sheet.py）
            if getattr(self.server, "public_open", False):  # 合言葉なしの場では開かない（J-028）
                return self._send(403, "公開のデモでは使えません")
            from . import think_sheet
            if not think_sheet.ready(m.group(1)):  # 節を出さない玩具には、受け口も無い
                return self._refuse(404, "リンクが古いか、道が違うようです。", "見つかりません")
            return think_sheet.post(self, m.group(1), m.group(2), form)
        m = re.fullmatch(rf"/en/toy/({SID})/print", self.path)
        if m and m.group(1) in sources():
            # 英語の頁から刷る（J-030 の段 1）。紙は同じ物で日本語のまま。聞く口と記録の口は英語の頁に置かない。
            sid, hid = m.group(1), form.get("hypothesis", "")
            if hid != hypotheses.sheet_of(sid)["id"]:  # 刷れるのは頁に出すたたき台だけ（J-032）
                return self._send(422, "That idea does not exist.", "text/plain; charset=utf-8")
            if print_latest(sid, hid) is None:
                return self._send(422, "This template could not be printed.", "text/plain; charset=utf-8")
            making_log.add_stage(sid, "print", form.get("who", ""))
            return self._send(303, "", headers=[("Location", f"/en/toy/{sid}?printed=1#ideas")])
        m = re.fullmatch(rf"/toy/({SID})/(print|record|ask)", self.path)
        if m and m.group(1) in sources():
            sid, act = m.groups()
            return self._toy_post(sid, act, form)
        m = re.fullmatch(rf"/zukan/({SID})/yomi", self.path)
        if m and m.group(1) in sources():
            # 書いた読みは応答に映すだけで、どこにも書かない（保存の形は本人が決めていない、research/25）。
            from . import kuzushi
            mine = form.get("mine", "").strip()[:kuzushi.MAX_READING]
            if not mine:
                return self._send(422, kuzushi.page(m.group(1), msg="先に、読めた所だけでも書いてください", look=self._look))
            return self._send(200, kuzushi.page(m.group(1), mine, look=self._look))
        # 合言葉なしで開いたデモでは、次の版を採る口と AI の口を閉じる: 誰でも型紙の版を変えられる形にしない。費用のかかる呼び出しもさせない（J-028）。
        if getattr(self.server, "public_open", False) and re.fullmatch(r"/record/R-\d{4,}/(next|ai-interpret|ai-observe)", self.path):
            return self._send(403, "公開のデモでは使えません")
        m = re.fullmatch(r"/record/(R-\d{4,})/(?:explain|next|ai-interpret|ai-observe)", self.path)
        if m and not (records.folder() / f"{m.group(1)}.json").exists():
            # 無い記録の番号（打ち間違いや、取り下げた後の古い頁）は 404 にする。記録を読む所で落ちて、送り直しを勧める 500 を返さないため
            return self._refuse(404, "リンクが古いか、道が違うようです。", "見つかりません")
        m = re.fullmatch(r"/record/(R-\d{4,})/(ai-interpret|ai-observe)", self.path)
        if m:
            return self._ai_reply(m.group(1), m.group(2), form)
        m = re.fullmatch(r"/record/(R-\d{4,})/next", self.path)
        if m:
            return self._next_version(m.group(1), form)
        m = re.fullmatch(r"/record/(R-\d{4,})/media/withdraw", self.path)
        if m:
            # 合言葉なしの場の、上げた画面からの取り下げ（窓口の決定 11-06 夜・案 A）。公開の場には進行者がいないので、上げた人が自分で消す。
            # 見分けは写真の鍵（上げた画面・期限 2 時間）で、釦を出す手帖の記録の頁と同じ条件。消すのは記録の写真と動画だけ（records.withdraw の
            # media_only。置き場ごと消すので、確かめの控えも残らず、ギャラリーからも消える）。合言葉付きの場は進行者に番号を伝える形のまま
            from . import techo_site
            rid = m.group(1)
            rec = loop.record(rid)
            if not (getattr(self.server, "public_open", False) and rec and media_review.uploaded_here(rid, techo_site.media_of(rid), self._up_key())):
                return self._refuse(403, "受け付けられません")
            _, failures = records.withdraw(rid, media_only=True)
            if failures:
                return self._refuse(422, failures[0].message)
            return self._send(303, "", headers=[("Location", f"/toy/{rec['source_id']}/techo/kiroku#mine")])
        m = re.fullmatch(r"/record/(R-\d{4,})/explain", self.path)
        if m:
            rid = m.group(1)
            rec = loop.record(rid)
            if not records.mine(rid, self._rec_key()):  # 説明は記録を残した画面からだけ。1 回限りなので、別の人が書くと本人の欄が閉じる
                return self._refuse(403, "受け付けられません")
            failures = loop.save_explanation(rid, form.get("by", ""), form.get("text", ""), form.get("next_idea", ""))
            if failures:
                # 記録の札の説明と次の版が通らない時は、手帖の記録の頁で、その札の頭に理由を出し、書いた字を戻す（つくるの頁から記録の札を外した 11-08。_kiroku）
                return self._send(422, self._kiroku(rec["source_id"], errors=[f.message for f in failures], err_at=rid, filled=("explain", form)))
            return self._done(rec["source_id"], "説明を残しました", form.get("back", ""), anchor=rid)
        self._refuse(404, "リンクが古いか、道が違うようです。", "見つかりません")

    def _clip_post(self, rid, clip, data):
        """区切りを 1 つ受ける。t は声（音だけを .mka に写して、この機械の中で字にしてから消す）、k はカメラ（押した後の 10 秒・音なし）。
        k は付帯情報（手順・釦）を控え、合言葉付きの場では人の操作（のこすの承認で届いた）の後に 1 回だけ読みを走らせる（api.clip_read）。
        公開の場は学ぶ人の操作では読まない（J-028）。進め役が media_review で確かめた時に読む。"""
        from omochae import voice_text

        kind = CLIP_TYPES.get((clip, self.headers.get("Content-Type", "").split(";")[0].strip()))
        if kind is None:
            return self._send(422, "受け付けられない区切りです", "text/plain; charset=utf-8")
        put = voice_text.put_voice_clip if clip == "t" else voice_text.put_cam_clip
        # 空いた番号を選んで置くまでを錠の中で（同時に 2 つ届いても同じ番号に上書きしない・別の目の気づき）。錠は別のプロセスとも取り合う
        with store.locked(loop.folder()):
            name, why = put(rid, data, kind)
        if not name:
            return self._send(422, why, "text/plain; charset=utf-8")
        if clip == "k":
            from api import clip_read

            step = self.headers.get("X-Utsushi-Step", "")
            # 数は 0〜9 の 1〜3 字だけ（isdigit は上付きの「²」なども通し、int で落ちて 500 になった・別の目の止め 2）
            clip_read.save_meta(rid, name, int(step) if re.fullmatch(r"[0-9]{1,3}", step) else None,
                                "stuck" if self.headers.get("X-Utsushi-Button") == "stuck" else None)
            if not getattr(self.server, "public_open", False):
                from api.agent import default_client

                clip_read.read_later(rid, name, lambda: default_client("observe"))
        return self._send(201, name, "text/plain; charset=utf-8")

    def _ai_reply(self, rid, act, form):
        """手帖で AI の返事を受ける口（J-013 の決める点 2: 子どもも AI から直接返事をもらってよい。紙 → 人の説明 → AI の順）。
        人の説明が先に無い記録には呼ばない。鍵が無い時は、鍵が置かれると答える事を伝えて止める（J-023）。"""
        from api import ask
        from api.budget import BudgetStop

        rec = loop.record(rid)
        sid = rec["source_id"]
        from . import techo_site

        is_video = lambda f: f.endswith(("mp4", "mov"))
        files = techo_site.media_of(rid)
        videos = [f for f in media_review.shown_to(rid, files, self._up_key()) if is_video(f)]  # 人や声が入ると確かめた動画は渡さない（#314）
        # 確認の前の動画を、上げた本人でない画面から Claude に渡さない。頁に釦は出ないが、開いたままの古い頁から届く。
        if act == "ai-observe" and not videos and any(is_video(f) for f in media_review.visible(rid, files)):
            return self._refuse(403, "受け付けられません")
        if not loop.explained(rid):  # 取り下げで字が空になった説明も、説明が無いと読む（J-013）
            return self._send(422, self._kiroku(sid, errors=["先に何が起きたと思うかを書く"], err_at=rid))
        if not ask._key_present():
            return self._done(sid, wording.plain("鍵が置かれると、Claude が答えます"), form.get("back", ""), anchor=rid)
        try:
            from api.agent import default_client

            if act == "ai-interpret":
                from api.loop_agents import draft_interpretation

                _, failures = draft_interpretation(rid, client=default_client("interpret"))
                msg = "Claude の読みを出しました" if not failures else failures[0].message
            else:
                from api import observe

                if not videos:
                    return self._done(sid, "動画を上げると、Claude が見えた事を返します", form.get("back", ""), anchor=rid)
                _, why = observe.observe(rid, techo_site.media_dir(rid) / videos[0], default_client("observe"))
                msg = "Claude が見えた事を出しました" if not why else why
        except BudgetStop as e:  # 今日の上限か累計の停止線かを言う（待てば聞けるのかが分かるように）
            failure_log.claude_failed(act.removeprefix("ai-"), "POST", self.path, e)
            msg = f"今は AI に聞けません（{e.note}）"
        except Exception as e:  # 画面の文は変えない。理由は作る側の記録に残す
            failure_log.claude_failed(act.removeprefix("ai-"), "POST", self.path, e)
            msg = "今は AI に聞けません"
        return self._done(sid, msg, form.get("back", ""), anchor=rid)

    def _reprint(self, sid, form):
        """版の記録があって紙が無い版を刷り直す（#158）。「次の版を作る」は、同じ値では前の版と変わらないので通らない。"""
        hid, v = form.get("hypothesis", ""), form.get("version", "")
        if (hid not in {h["id"] for h in hypotheses.load(sid)["hypotheses"]}
                or not (v.isascii() and v.isdigit() and int(v) in loop.adopted_versions(sid, hid))):
            return self._send(422, self._toy(sid, errors=["その版は採られていません"], at="win"))
        if _printing(lambda: loop.print_version(sid, hid, int(v), out_dir(sid))) != 0:
            return self._send(422, self._toy(sid, errors=[f"{_ban(sid, v)} の紙を作れませんでした（検査に落ちた）"], at="win"))
        loop.confirm_sheet(sid, hid, int(v), "画面の使い手", TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].SHEET_SET)
        return self._done(sid, f"{_ban(sid, v)} の紙を作りました。印刷する時は、PDF の大きさを 100% にしてください。", see=hid, anchor="win")

    def _next_version(self, rid, form):
        """人の解釈の確定 → 人が書いた変更の案 → 人が採る → 次の版を刷る。どこかで床に落ちたら、その理由を出して止め、何も残さない（#158）。"""
        rec = loop.record(rid)
        sid, hid = rec["source_id"], loop.next_target(rec["source_id"], rec["hypothesis_id"], rec.get("sheet_set"))  # 自分の紙の記録からの次の版は、たたき台へ向ける
        if hid is None:  # 今のたたき台と押し方の違う紙の記録（loop.next_target）。断りは床の今の字のまま
            return self._send(422, self._kiroku(sid, errors=[NEXT_SHEET_ONLY], err_at=rid))
        if hid != hypotheses.sheet_of(sid)["id"]:  # 次の版はたたき台の記録からだけ（J-032。欄も toy.next_form が出さない）
            return self._send(422, self._kiroku(sid, errors=[NO_HYPOTHESIS], err_at=rid))
        if loop.explanation(rid) is None:
            return self._send(422, self._kiroku(sid, errors=["先に説明を書く"], err_at=rid))
        to = _num(form.get("to"))
        if not isinstance(to, float):
            return self._send(422, self._kiroku(sid, errors=["新しい値は数で書く"], err_at=f"next-{rid}", filled=("next", form)))
        # 折りの数のような整数の寸法は、整数で渡す（範囲の検査が小数の折り数を落とすため）。
        to = int(to) if to.is_integer() else to
        source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
        change = {"param": form.get("param"), "to": to, "why": form.get("why", "")}
        v, failures = loop.next_version(rid, form.get("by", ""), form.get("interpretation", "").strip() or None, change, source, out_dir(sid))
        if failures:
            from . import toy

            return self._send(422, self._kiroku(sid, errors=toy.next_reasons(failures, sid, hid, change["param"], to), err_at=f"next-{rid}", filled=("next", form)))
        return self._done(sid, f"{_ban(sid, v)} の紙を作りました。印刷する時は、PDF の大きさを 100% にしてください。", form.get("back", ""), see=hid, anchor="win")

    def _step_post(self, sid, form):
        """作りながら見る頁の札（次の手順へ・戻る・止まった・できた）と、頁を開いた事。残すのは手順の番号と出来事だけ（making_log.add_step）。
        決まりの外（刷っていない紙・数でない番号・手順の数の外・知らない出来事・途中の手順の組み上がり）は 422。映像や写真はこの口では受けない（form の欄だけ）。"""
        from . import tsukuru

        as_json = form.get("json") == "1"
        bad = lambda why: self._send(422, json.dumps({"error": why}, ensure_ascii=False) if as_json else why,
                                     "application/json; charset=utf-8" if as_json else "text/plain; charset=utf-8")
        hid, event = form.get("hypothesis", ""), form.get("event", "")
        from . import think_sheet

        known = hid in {h["id"] for h in hypotheses.load(sid)["hypotheses"]} or hid in think_sheet.mine(self, sid)  # 本人の案は、作った本人の画面からだけ
        if not known or not printed_versions(sid, hid):
            return bad("作った紙をえらぶ")
        if event not in making_log.EVENTS:
            return bad("その札は無い")
        total = tsukuru.count(sid, hid, sheet_version_of(sid, hid, form))
        try:
            step = int(form.get("step", ""))
        except ValueError:
            return bad("手順の番号は数で")
        if not 1 <= step <= max(total, 1):
            return bad("その手順は無い")
        # 組み上がりは最後の手順だけで受ける。途中の札は頁に出さないが、開いたままの古い頁からは届く。残すと作る様子の集計がずれる（#321）。
        if event == "done" and step < total:
            return bad("その札は無い")
        # 次に見せる手順: 進む・戻るは 1 つ動かし、止まった・できた・開いたは同じ手順のまま。
        nxt = min(step + 1, max(total, 1)) if event == "next" else max(step - 1, 1) if event == "back" else step
        # 同じ相手からの段の数の上限（STEP_LIMIT。書き込みの口と別に数える）。超えたら置き場へ書かない。頁は止めない:
        # 頁を読み直さない札（JS）は返事の step で進むので、断りにも次の手順を添える。フォーム（JS の無い頁と、組み上がりの札）は、
        # 断りの頁で止めず、書かずに成功の時と同じ行き先へ返す。
        busy = (who := writer(self.client_address[0], self.headers)) and self.server.step_limit.wait(who)
        if busy and as_json:
            return self._send(429, json.dumps({"error": BUSY, "step": nxt}, ensure_ascii=False), "application/json; charset=utf-8", [("Retry-After", str(busy))])
        if not busy:
            # 最後の手順の「次の手順へ」は頁に出さないが、開いたままの古い頁からは届く。動かないので残さない（残すと、途中でやめた段の数えで、無い手順が出る）。
            if not (event == "next" and step >= total):
                making_log.add_step(sid, hid, sheet_version_of(sid, hid, form), step, event, who=form.get("who", ""))
            if event == "start":
                making_log.add_stage(sid, "make", form.get("who", ""))  # 頁の段の進み: 作る頁を開いた（U-45 の段取り 2）
        if as_json:
            return self._send(200, json.dumps({"ok": True, "step": nxt}), "application/json; charset=utf-8")
        if event == "done":  # 組み上がりを残した後、のこすの頁（手帖の記録の頁 /toy/<印>/techo/kiroku）へ直に送る（本人の答え 11-08「B。」・統括の決め (a)）。
            # 前はどの紙かを渡して玩具の頁の記録の欄へ送り、そこから のこす へもう 1 押し要った。組み上がりの記録（making_log.add_step）は上で今と同じに残す
            return self._done(sid, tsukuru.DONE_NOTE, back="techo", anchor="kinyu")
        ev = f"&ev={event}" if event == "stuck" else ""
        return self._send(303, "", headers=[("Location", f"/toy/{sid}/tsukuru?h={urllib.parse.quote(hid)}&v={sheet_version_of(sid, hid, form)}&n={nxt}{ev}")])

    def _ask(self, sid, hid, question):
        """手順の質問を Claude へ。失敗は理由を作る側の記録に残し、投げ直す（画面の文は呼ぶ側が決める）。
        話す口と同じ入口の床を先に当てる（#87）。手帖は 1 回押した後は聞き続けるので、名乗りや連絡先の形の話し声も字になって届く。
        当たった字は Claude へ送らず、返す字は採られた文にする。残す時は add_ask が字を落として数だけ残す。"""
        from api import ask
        from omochae import talk_log

        if talk_log.blocked(question or ""):
            return making_log.ASK_NAME_VOICE, "floor"
        try:
            return ask.answer(sid, hid, question)
        except Exception as e:
            failure_log.claude_failed("ask", "POST", self.path, e, private=(question,))
            raise

    def _photo_target(self, sid, form):
        """写真を足す先: この画面が、写真の口の無い所（玩具の頁の記録の欄）で残した、同じ玩具の、写真の無い記録の番号（無ければ None）。
        そこで残した後に手帖で写真を上げる人の記録を、1 つのままにするために引く。照らすのは記録の鍵だけ（records.mine）。
        手帖の欄に新しい中身（字・別の見た事）がある時は足さない: 足すと、書いた事が残らないため。その時は今までどおり新しい記録になる。
        別の紙や版を選んでいる時も足さない（見た事を選んでいなくても）: 別の紙の作りの写真を、前の紙の記録に付けないため。紙は頁で最初から 1 つ
        選ばれているので、頁は、紙を選び直した時と見た事を選んだ時だけ紙を送る。紙が来ない時は、紙と版を見ない。
        手帖で残した記録には足さない: 写真の口のある所で「記録だけ」を選んだ物で、机の端の 1 台を順に使う場では、次の人の写真が前の人の記録に付くため。"""
        key = self._rec_key()
        if not key or getattr(self.server, "public_open", False):
            return None
        from . import techo_site

        r = next((r for r in reversed(records.all_records(sid)) if records.mine(r["id"], key)), None)
        if r is None or r.get("via") or techo_site.media_of(r["id"]):
            return None
        if any(form.get(k, "").strip() for k in ("note", "impression", "fix_part", "fix_change", "fix_outcome")):
            return None
        hid = form.get("hypothesis", "")
        if hid and (hid != r["hypothesis_id"] or sheet_version_of(sid, hid, form) != r.get("sheet_version", 1)):
            return None
        if form.get("result") and (not hid or form["result"] != records.result_word(r)):
            return None
        return r["id"]

    def _json_post(self, sid, act, form):
        """手帖の頁から呼ぶ口。頁を作り直さず、答えか記録の番号だけを返す。"""
        out = lambda code, obj, headers=(): self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8", headers)
        hid = form.get("hypothesis", "")
        from . import think_sheet

        if act == "record-json" and form.get("attach") == "1":
            # 「写真あり」の合図（1 回の作りが 2 つの記録に割れる所の直し）: この画面が残した、写真の無い記録に足せる時は、新しい記録を作らずに
            # その番号を返す。頁から番号は受けない（番号は札に出る連番なので、別の人が送れる）。鍵は作り直さない（期限の数え方がそのまま続く）。
            rid = self._photo_target(sid, form)
            return out(200, {"id": rid, "attached": True} if rid else {"attached": False})
        if not printed_versions(sid, hid) or not think_sheet.usable(self, sid, hid):
            return out(422, {"error": "作った紙をえらぶ"})
        if act == "ask-json":
            from api.budget import BudgetStop

            try:
                text, how = self._ask(sid, hid, form.get("question", ""))
            except BudgetStop as e:
                text, how = f"今は AI に聞けません（{e.note}）", "stop"
            except Exception:
                text, how = "今は AI に聞けません。組み方の絵を見てください", "error"  # 呼び名は「組み方の絵」にそろえる（11-06 の決定。紙は刷らなくなった）
            # 質問の文だけを工作の様子として残す（本人の決定 11-05 朝。連絡先の形は落とす。答えの文・声・誰が聞いたかは残さない）。
            making_log.add_ask(sid, hid, sheet_version_of(sid, hid, form), form.get("question", ""), how, step=form.get("step"), who=form.get("who", ""))
            return out(200, {"text": text, "from": how})
        rid, failures = records.add({"source_id": sid, "hypothesis_id": hid, "sheet_version": sheet_version_of(sid, hid, form), "result": form.get("result"),
                                     "note": form.get("note", ""), "impression": form.get("impression", ""), "fixes": fixes_of(form), "via": "techo"})
        if rid:
            making_log.add_stage(sid, "record", form.get("who", ""))  # 頁の段の進み: 記録を残した（手帖から）
            # 作りながら話した工夫と、仮説を見て話した考えを、この記録に結ぶ（Issue #279）。結んだ数を返す（頁はまだ読まない。知らせる文は本人の確認の後）。
            from omochae import talk_log
            kufu, kangae = talk_log.bind(sid, hid, sheet_version_of(sid, hid, form), form.get("who", ""), rid)
            self._shiori_add(rid)  # しおりで開いた画面なら、その並びに足す（続きの記録を足す・2‴ の 3）
            sp = self._shiori_bind(rid, form)  # 型紙と一緒に刷ったしおりの待ちに結ぶ（確かめの画面で外さなかった時だけ・設計 2.1 版の 2 節）
            return out(201, {"id": rid} | ({"kufu": kufu} if kufu else {}) | ({"kangae": kangae} if kangae else {}), [*self._up_close(), self._rec_cookie(rid), *sp])
        return out(422, {"error": "；".join(f.message for f in failures)})

    def _toy_post(self, sid, act, form):
        see = None  # 刷った時だけ、戻り先を型紙の窓にする
        anchor = "kiroku"  # 試した記録の欄へ戻すのは記録だけ
        claim = ()  # 記録が残った時だけ、残した画面へ印を渡す
        if act == "ask":
            # 手順の質問は、試した記録（仮説への返事）には入れず、その場で答えを頁に出す。順（紙 → 記録と説明 → AI）には入らない。
            # 質問の文だけは工作の様子（omochae.making_log）に残す: 何で止まるかを、案内と答えを直す材料にする（本人の決定 11-05 朝）。
            from api import ask
            from api.budget import BudgetStop

            hid = form.get("hypothesis", "")
            from . import think_sheet

            if not printed_versions(sid, hid) or not think_sheet.usable(self, sid, hid):
                return self._send(422, self._toy(sid, errors=["作った紙について聞けます。先に紙を作ってください"], at="ask", filled=("ask", form)))
            try:
                text, how = self._ask(sid, hid, form.get("question", ""))
            except BudgetStop as e:  # 額の入った例外の文は出さず、止めた線だけを言う
                text, how = f"今は AI に聞けません（{e.note}）", "stop"
            except Exception:
                text, how = "今は AI に聞けません。型紙の凡例と、組み方の絵を見てください", "error"  # 呼び名は ask.NO_KEY とそろえる（組み方の絵）
            making_log.add_ask(sid, hid, sheet_version_of(sid, hid, form), form.get("question", ""), how, step=form.get("step"), who=form.get("who", ""))
            return self._send(200, self._toy(sid, asked=(form.get("question", ""), text)))
        if act == "print":
            failures = []
            hid = form.get("hypothesis", "")
            at = "win" if form.get("at") == "win" else "kasetsu"  # 窓の札から押した時は、通らない理由も窓で読む（#127）
            if hid != hypotheses.sheet_of(sid)["id"]:  # 刷れるのは頁に出すたたき台だけ（J-032）
                return self._send(422, self._toy(sid, errors=[NO_HYPOTHESIS], at=at))
            if print_latest(sid, hid) is None:
                return self._send(422, self._toy(sid, errors=["型紙を作れませんでした（検査に落ちた）"], at=at))
            msg = "紙を作りました。下の窓で絵を見てください。印刷する時は、PDF の大きさを 100% にしてください。"
            see = hid
        else:
            hid = form.get("hypothesis", "")
            from . import think_sheet

            # 話した考えから作った案の記録は、作った本人の画面からだけ。無い仮説は受け口で先に断る（前は records.add の床の字
            # 「仮説 H-ZZ は実在しない」が内部の番号のまま、3 つの言葉とも訳されずに出た。別の目の気づき・統括の決め 11-08）
            if not think_sheet.usable(self, sid, hid) or not records.known_hypothesis(sid, hid):
                return self._send(422, self._toy(sid, errors=[NO_HYPOTHESIS], at="kiroku", filled=(act, form)))
            # 版は刷ってある一番新しい物（報告はその版への返事）。感想は本人の方針（11-05）「感想と動きの報告」の欄。
            rec = {"source_id": sid, "hypothesis_id": hid, "sheet_version": sheet_version_of(sid, hid, form), "result": form.get("result"),
                   "impression": form.get("impression", "").strip(),
                   "opened_deg": _num(form.get("opened_deg")), "opener": form.get("opener") or None, "power": form.get("power") or None,
                   "minutes_to_try": _num(form.get("minutes_to_try")), "fixes": fixes_of(form), "note": form.get("note", ""),
                   "answers": {k: form[k] for k in ("first_moved", "stuck", "what_if") if form.get(k, "").strip()},
                   "ideas": [form["idea"]] if form.get("idea", "").strip() else []}
            rid, failures = records.add(rec)
            if rid:
                # 作りながら話した工夫と、仮説を見て話した考えを、この記録に結ぶ（Issue #279。手帖の記録を残す口と同じ）。
                from omochae import talk_log
                talk_log.bind(sid, hid, rec["sheet_version"], form.get("who", ""), rid)
                claim = (self._rec_cookie(rid),)
                self._shiori_add(rid)  # しおりで開いた画面なら、その並びに足す（続きの記録を足す・2‴ の 3）
            # 試した後の紙は刷らなくなった（本人の決まり 11-06）ので、後ろの「試した後の紙が開けます」を外した（字は足していない）
            msg = "記録を残しました。"
            # 残した札へ戻す。次の段（試した後の紙・説明）がそこにあるため。
            anchor = rid or anchor
        if failures:
            return self._send(422, self._toy(sid, errors=[f.message for f in failures], at="kiroku", filled=(act, form)))
        # 頁の段の進み（刷った・記録を残した）を工作の様子に残す（U-45 の段取り 2）。何を書いたかは写さない。
        # 人の印は画面が送った時だけ。書けなくても例外は出ないので、この口は止まらない。
        if act in ("print", "record"):
            making_log.add_stage(sid, act, form.get("who", ""))
        # 台本の無い画面の のこす（web.nokosu の素のフォーム）は back=techo を送り、記録の頁の #mine へ戻る（_done は techo の時だけ替え、ほかの値は無視する）
        self._done(sid, msg, back=form.get("back", ""), see=see, anchor="win" if see else anchor, fresh=act == "record", headers=claim)


_making = {}  # 作っている最中の紙。（玩具, 案）→ その結果
_making_guard = threading.Lock()


def _one_at_a_time(key, make):
    """同じ案の紙を同時に作らない（#301）。作っている人がいれば作り直さず、その結果を待って同じ物を返す。
    順に作り直すと、同じ釦に人が集まる場（#332）で、最後の人が人数分待つ。作る人が落ちたら、待っている人も同じ失敗を受け取る。"""
    with _making_guard:
        running = _making.get(key)
        if running is None:
            mine = _making[key] = Future()
    if running is not None:
        return running.result()
    try:
        result = make()
    except BaseException as e:
        mine.set_exception(e)
        raise
    else:
        mine.set_result(result)
        return result
    finally:
        with _making_guard:
            del _making[key]


def print_latest(sid, hid):
    """仮説の一番新しい版を刷る。日本語の頁と英語の頁で同じ物を使う（紙は同じ。J-030）。刷った版を返し、刷れなければ None。
    刷るのは一番新しい版（報告から直した版）。次に作る人に改善した型紙を渡すため（本人の方針 11-05「報告を型紙の改善に回し、より良い型紙を提供する」）。
    一番新しい版が刷れない時は 1 つ前の版へ戻る: 採った版が検査に落ちたまま残ると、その仮説の紙が誰にも刷れなくなるため。"""

    def make():
        v = loop.latest_version(sid, hid)
        while loop.print_version(sid, hid, v, out_dir(sid)) != 0:
            if v <= 1:
                return None
            v -= 1
        # 刷ると選んだ事が型紙の確定（f09）。名前の欄は画面に無いので、使い手として残す。
        loop.confirm_sheet(sid, hid, v, "画面の使い手", TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].SHEET_SET)
        return v

    return _one_at_a_time((sid, hid), lambda: _printing(make))


def print_own(sid, oid):
    """自分の仮説の紙を刷る。刷れたら 0。順番と置き換えは print_latest と同じ。"""
    return _one_at_a_time((sid, oid), lambda: loop.print_own(sid, oid, out_dir(sid)))


def fixes_of(form):
    """記録の欄の「工夫した所」を記録の形にする。本人の言葉（11-05）「それを人間が工夫で乗り切る過程をAIにフィードバックして型紙が改善される」の、輪の材料の口。
    何も書かなければ空。「あれば」の欄なので、一部だけ書いても記録ごと落とさない（落とすと書いた全部が消える）。
    欠けた欄は「書かれていない」と残す: 3 欄の床（F3.result）を通し、読む人が欠けと分かるようにするため。"""
    part, change, outcome = (form.get(k, "").strip() for k in ("fix_part", "fix_change", "fix_outcome"))
    if not (part or change or outcome):
        return []
    blank = records.FIX_BLANK
    return [{"part": part or blank, "change": change or blank, "outcome": outcome or blank}]


def lan_addresses():
    """この機械の網の中の番地（192.168.x.x などの私的な番地だけ）と、.local の名前。"""
    import ipaddress
    import socket

    names = set()
    try:
        # 外へ繋がる番地を知るため、送らない UDP の口で経路だけを引く（実際には何も送らない）。
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))
            names.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        names.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    ips = sorted(a for a in names if ipaddress.ip_address(a).is_private and not ipaddress.ip_address(a).is_loopback)
    return ips + [f"{socket.gethostname().split('.')[0]}.local"]


def bind_host(lan):
    return "0.0.0.0" if lan else "127.0.0.1"


def serve(port=8766, lan=False, public_key=None, look=skinmod.DEFAULT, public_open=False, bind=None):
    """lan=True は本人の決定（11-04、U-36）で、家の網から iPhone で手帖を開くための切り替え。既定は今までどおり手元だけ。
    public_key はデモの一周をパソコン・iPad・iPhone から開く時（本人の決定 A、11-04）。短すぎる合言葉は断る（当てられないため）。
    look はこのサイトの皮（tenji 白の展示・zine 黒のジン）。皮ごとに 1 サイト（本人の決定 11-05 朝）なので、2 つ立てる時は port と look を変える。"""
    if public_key is not None and len(public_key) < 16:
        raise ValueError("合言葉が短すぎる（16 字以上）")
    if look not in skinmod.SKINS:
        raise ValueError(f"皮が無い: {look}（{'・'.join(skinmod.SKINS)}）")
    # bind は試験のため。--lan の番地の許しを試す間も、全部の網に口を開かない（#169）。
    server = ThreadingHTTPServer((bind or bind_host(lan), port), Handler)
    server.lan_hosts = tuple(lan_addresses()) if lan else ()
    server.public_key = public_key
    # public_open: 合言葉なしで外から開けるデモ（本人の許可 11-05）。合言葉付き（public_key）とは同時に使わない。
    # 開いた場でも写真と動画は受ける（本人の決定 11-06）。確かめる前は上げた本人の画面にだけ、物だけと確かめた後はギャラリーにも出す（合言葉付きの場と同じ線）。
    if public_open and public_key:
        raise ValueError("合言葉付きと合言葉なしは同時に使えない")
    if public_open:
        # 鍵のある場所では開かない: 誰でも聞く口から費用のかかる呼び出しができてしまうため（J-028）。
        from api import ask
        if ask._key_present():
            raise ValueError("鍵（.env）がある所では、合言葉なしで開けない")
    server.public_open = bool(public_open)
    server.look = look
    server.write_limit = WriteLimit()
    server.step_limit = WriteLimit(limit=STEP_LIMIT)
    server.print_limit = WriteLimit(limit=PRINT_LIMIT)
    server.media_limit = WriteLimit(limit=MEDIA_LIMIT)
    # 上げた動画の声を、この機械の中で字にしてから消す（本人の言葉 11-08「全部残していいことにしたい。」・omochae.voice_text）。
    # 道具の確かめは立てる時に 1 度だけ（受けるたびに確かめると、上げるたびに数秒待たせる）。道具がある時だけ声を写す。
    # 72 時間の掃除は道具の有無に関わらず、作業列が立てた時と 1 時間ごとに回す
    from omochae import voice_text

    server.voice_tool = not voice_text.tool_missing()
    server.voice_jobs = voice_text.Worker(server.voice_tool)
    server.voice_jobs.start()
    return server


if __name__ == "__main__":
    try:
        argv = sys.argv[1:]
        key = None
        if "--public-key-file" in argv:
            # 合言葉は引数に書かない（ps で見える）。ファイルの中身だけを読む。
            i = argv.index("--public-key-file")
            key = pathlib.Path(argv[i + 1]).read_text(encoding="utf-8").strip()
            del argv[i:i + 2]
        look = skinmod.DEFAULT
        if "--look" in argv:
            # どの皮のサイトか（tenji か zine）。2 サイト目は port も変えて別に立てる。
            i = argv.index("--look")
            look = argv[i + 1]
            del argv[i:i + 2]
        public_open = "--public" in argv  # 合言葉なしで開く（run-demo.sh --open）
        args = [a for a in argv if a not in ("--lan", "--public")]
        lan = "--lan" in argv
        port = int(args[0]) if args else 8766
        server = serve(port, lan=lan, public_key=key, look=look, public_open=public_open)
        # 作り方の印は部品を組み立てて数えるので、初めて数える時は一覧の頁が 3 秒ほど待たされる。人が開く前に裏で数えておく
        import threading
        from omochae import ways

        threading.Thread(target=lambda: [ways.toy_labels(s) for s in sources()], daemon=True).start()
    except (ValueError, OSError, OverflowError, IndexError) as e:
        print(f"検査できない: 開けない: {e}", file=sys.stderr)
        sys.exit(4)
    print(f"http://127.0.0.1:{port}/  皮: {skinmod.SKINS[look]['name']}（{look}）")
    for h in server.lan_hosts:
        print(f"家の網から: http://{h}:{port}/  （同じ網の iPhone で開く。音声認識は https でないので使えない見込みで、字の入力と読み上げは使える）")
    server.serve_forever()
