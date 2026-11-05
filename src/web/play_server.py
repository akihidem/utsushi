"""使い手の入口: 手元で動くブラウザの画面（本人の決定、J-024）。依存を増やさず標準の http.server で作る。

判断の芯: コマンドの輪と同じ線を画面でも守る。予想が先（F9.prediction）、仮説に順位を出さない（J-013）、
試した後の紙は記録を残すまで渡さない（J-013）、結果は人が入れる値で、成績にしない（philosophy.md）。
鍵なしで輪の前半（予想 → 型紙 → 試す → 記録 → 人の説明）が回る。Claude を呼ぶ所（手帖の質問・読み・観察）は鍵がある時だけ動く。
既定は持ち寄りの画面（contrib_server.py）と同じく 127.0.0.1 にだけ開く。外に開く責任を週内に持てないため。
家の網に開く切り替え（--lan、U-36）と、デモの一周を外の機器から開く合言葉の門（--public-key-file、11-04 の本人の決定 A）は
本人の決定で足した。後者は口を 127.0.0.1 のままにし、外からはトンネル（run-demo.sh）だけが入る。
"""
import hmac
import html
import json
import os
import pathlib
import re
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from omochae import hypotheses, loop, making_log, records
from omochae.compose import TEMPLATES
from omochae.hypotheses import ROOT
from omochae.store import SID

from . import failure_log
from . import skin as skinmod
from .contrib_server import STYLE

# 見た目はルックブックの様式（本人の指定、J-024）。絵が主役で、文字は添え。見開きのように絵と短い文を左右に置き、玩具ごとに左右を入れ替える。
# 参照の X の投稿の実物は 11-04 に見た（research/19）。入口の再現は looks.py の A にあり、この塊は玩具の頁の見た目だけを持つ。
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
    """刷った紙の置き場。試験で本物の置き場を汚さないよう、記録と同じ環境変数に従う。"""
    base = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "play" if os.environ.get("OMOCHAE_DATA") else ROOT / "out/play"
    return base / sid


def sources():
    return sorted(p.stem for p in (ROOT / "data/hypotheses").glob("NDL-*.json"))


def source(sid):
    return json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))


def esc(s):
    return html.escape(str(s if s is not None else ""))


def page(title, body, extra_style="", body_class=""):
    cls = f' class="{body_class}"' if body_class else ""
    return (f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>'
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


def printed_versions(sid, hid):
    """刷ってある版の番号（小さい順）。無ければ空。版 1 を決め打ちしない: 報告から直した版 2 以降を、次に作る人が最初に刷る事があるため。"""
    return sorted({int(m.group(1)) for p in out_dir(sid).glob(f"{hid}_v*.pdf") if (m := re.fullmatch(rf"{re.escape(hid)}_v(\d+)\.pdf", p.name))}) if out_dir(sid).exists() else []


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


def _num(v):
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return v  # 数でない物は記録の検査に落とさせ、理由を画面に返す


class Handler(BaseHTTPRequestHandler):
    timeout = 20

    def log_message(self, *a):  # 予想や記録の文を記録に残さない
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8", headers=()):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _refuse(self, code, reason, title="開けません", **kw):
        """断りの頁を出す。_look は要求の始めに決まるが、そこで落ちた時も頁を出せるように既定を持つ（#136）。"""
        self._send(code, skinmod.notice(title, reason, getattr(self, "_look", skinmod.DEFAULT), **kw))

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
        jar = {}
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            jar[k] = v
        if hmac.compare_digest(jar.get("utsushi_k", "").encode(), key.encode()):
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

    def _toy(self, sid, **kw):
        return toy_page(sid, look=self._look, **kw)

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
        except Exception as e:
            failure_log.request_failed("POST", self.path, e)
            self._refuse(500, "受け付けられませんでした。少し待って、もう一度送ってください。", "送れませんでした")

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
            return self._send(200, PAGES[look]())
        m = re.fullmatch(r"/look/([a-z]+)", path)
        if m and m.group(1) == look:
            return self._send(200, PAGES[look]())
        if path == "/about":
            from . import about
            return self._send(200, about.page(look, path))
        # 作る側の頁は、合言葉なしで開いたデモには出さない: 聞いた言葉と感想の文がそのまま読める頁で、名前は機械では落とせないため（J-027・J-028）。
        if path.startswith("/loop") and getattr(self.server, "public_open", False):
            return self._send(404, "見つかりません")
        if path == "/loop":
            # 改善の輪の一覧（本人の方針 11-05）。サイト側が輪を回す所で、学ぶ人の順路の帯には入れない。
            from . import kaizen
            return self._send(200, kaizen.page(look, path))
        m = re.fullmatch(rf"/loop/({SID})", path)
        if m and m.group(1) in sources():
            # その玩具の工作の様子（聞かれた事・止まった所・感想・動きの札）。作る側が読む集計で、学ぶ人の頁には出さない。
            from . import kaizen
            return self._send(200, kaizen.toy_page(m.group(1), look, path))
        if path == "/toys":
            from . import toys
            return self._send(200, toys.page(look, path))
        if path == "/gallery":
            from . import techo_site
            from .demo_samples import STYLE as SAMPLE_STYLE
            return self._send(200, skinmod.shell("上げた物と職人の言葉", techo_site.gallery_page(sources()), look, "/gallery", path, techo_site.STYLE + SAMPLE_STYLE, "techo"))
        # 図鑑（f15）。文の印の床（F6.label）と予想が先の線は zukan.py が持つ。床に落ちれば例外で 500 になり、頁を出さない。
        m = re.fullmatch(rf"/zukan(?:/({SID}))?", path)
        if m and (m.group(1) is None or m.group(1) in sources()):
            from . import zukan
            return self._send(200, zukan.toy_zukan(m.group(1), look) if m.group(1) else zukan.index_page(sources(), look))
        # くずし字を読む（f14）。書く前の頁は確かめた読みを出さない。予想が先の線と印の床は kuzushi.py が持つ。
        m = re.fullmatch(rf"/zukan/({SID})/yomi", path)
        if m and m.group(1) in sources():
            from . import kuzushi
            return self._send(200, kuzushi.page(m.group(1), look=look))
        m = re.fullmatch(rf"/toy/({SID})/kazasu", path)
        if m and m.group(1) in sources():
            # かざして選ぶ（試作、本人の案 11-05）。内カメラの映像に原図を重ね、札のタップで予想を選ぶ。映像は端末の外へ出さない（kazasu.py）。
            from . import kazasu
            return self._send(200, kazasu.page(m.group(1), look))
        m = re.fullmatch(rf"/toy/({SID})/tsukuru", path)
        if m and m.group(1) in sources():
            # 作りながら見る（観察 A の試作、本人の案 11-05）。机の端に立てた端末に手本と返事を出し、鏡は端末の中だけ（tsukuru.py）。
            # 予想の前と、刷った紙が無い時は開かない（手帖と同じ扱い。仮説の中身を先に見せないため）。
            sid = m.group(1)
            if hypotheses.need_prediction(sid):
                return self._send(200, self._toy(sid, errors=["先に予想を書くと、作りながら見る頁が開きます"]))
            printed = [h["id"] for h in hypotheses.load(sid)["hypotheses"] if printed_versions(sid, h["id"])]
            hid = qs.get("h", [""])[0] or (printed[0] if printed else "")
            if hid not in printed:
                return self._send(200, self._toy(sid, errors=["先に紙を刷ると、作りながら見る頁が開きます"]))
            from . import tsukuru
            try:
                n = int(qs.get("n", ["1"])[0])
            except ValueError:
                n = 1
            # 版は開いた時に決めて URL で持つ（作っている途中で別の人の版が刷られても、手順の文が変わらないように）。
            v = int(qs["v"][0]) if qs.get("v", [""])[0].isdigit() else None
            return self._send(200, tsukuru.page(sid, hid, look, step=n, event=qs.get("ev", [""])[0], version=v))
        m = re.fullmatch(rf"/toy/({SID})/techo", path)
        if m and m.group(1) in sources():
            # 手帖は入口のサイトの中の一続きの頁（本人の方向転換、11-04）。予想の前は仮説の字も出さない（F9.prediction）。
            sid = m.group(1)
            if hypotheses.need_prediction(sid):
                # 頁の頭に戻すと理由が画面の外になるので、予想の欄へ送る（#121）。
                return self._send(303, "", headers=[("Location", f"/toy/{sid}?msg={urllib.parse.quote('先に予想を書くと、手帖が開きます')}&at=yosou#yosou")])
            printed = [h["id"] for h in hypotheses.load(sid)["hypotheses"] if printed_versions(sid, h["id"])]
            pic = f"/picture/{sid}" if (ROOT / "out/sources" / f"{sid}.jpg").exists() else ""
            from . import techo_site
            return self._send(200, skinmod.shell("手帖", techo_site.page(sid, printed, pic, msg=qs.get("msg", [""])[0], uploads=not getattr(self.server, "public_open", False)), look, "", path, techo_site.STYLE, "techo"))
        m = re.fullmatch(r"/record/(R-\d{4,})/media/(m\d+\.(?:jpg|png|mp4|mov))", path)
        if m and not getattr(self.server, "public_open", False):  # 開いたデモでは、置き場に写真が在っても出さない
            from . import techo_site
            f = techo_site.media_dir(m.group(1)) / m.group(2)
            if f.exists():
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
            return self._send(200, self._toy(m.group(1), msg=qs.get("msg", [""])[0], at=qs.get("at", [""])[0], see=qs.get("see", [None])[0], kind=kind, v=v, path=path))
        m = re.fullmatch(rf"/picture/({SID})", path)
        if m and (ROOT / "out/sources" / f"{m.group(1)}.jpg").exists():
            return self._send(200, (ROOT / "out/sources" / f"{m.group(1)}.jpg").read_bytes(), "image/jpeg")
        # 刷った紙。PDF（刷る）のほかに PNG と SVG（画面で見る、要件の S-01）。試した後の紙はどの形でも記録の前は渡さない。
        m = re.fullmatch(rf"/sheet/({SID})/((?:H-[A-Z0-9]+|OWN-\d+)_v\d+(?:_tejun|_after|_free)?)\.(pdf|svg|png)", path)
        if m and m.group(1) in sources():
            sid, stem, ext = m.groups()
            hid = re.split(r"_v\d+", stem)[0]
            if stem.endswith("_after") and hid not in {r["hypothesis_id"] for r in records.all_records(sid)}:
                return self._refuse(403, "試した記録を残してから開きます。", links=((f"/toy/{sid}#kiroku", "記録の欄へ"),))
            f = out_dir(sid) / f"{stem}.{ext}"
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

    def _done(self, sid, msg, back="", see=None, anchor="kiroku"):
        # 手帖から送った物は手帖へ戻す（本人「アップロードも手帖から。フィードバックも手帖」、11-04）。玩具の頁へ戻す時は、刷った紙の窓か記録の所へ。
        if back == "techo":
            return self._send(303, "", headers=[("Location", f"/toy/{sid}/techo?msg={urllib.parse.quote(msg)}#mine")])
        extra = f"&see={see}&kind=sheet" if see else ""
        self._send(303, "", headers=[("Location", f"/toy/{sid}?msg={urllib.parse.quote(msg)}&at={anchor}{extra}#{anchor}")])

    def _post(self):
        if not self._host_ok():
            # 手元の名前でない Host には、その名前へ戻るリンクを出さない
            return self._refuse(403, "受け付けられません", links=(), bare=True)
        m = re.fullmatch(r"/record/(R-\d{4,})/media", self.path)
        if m:
            # 写真と動画はフォームでなく本体そのままで受ける。別のサイトから送らせないため、同じ出所だけを受ける。
            from . import techo_site
            if not self._origin_ok():
                return self._send(403, "受け付けられない送り方です")
            # 合言葉なしで開いたデモでは、写真と動画を受けない: 誰でも上げられると、確かめていない写真（顔・他人の物）がそのまま
            # 皆に見える。持ち寄りは同意と権利を確かめてから載せる線（J-021）と、子どもの写真を扱わない線を、開いた場でも守るため。
            if getattr(self.server, "public_open", False):
                return self._send(403, "公開のデモでは、写真と動画は上げられません", "text/plain; charset=utf-8")
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return self._send(411, "大きさが分かりません")
            if not 0 < length <= techo_site.MAX_MEDIA:
                return self._send(413, "1 つ 20MB まで")
            name, why = techo_site.save_media(m.group(1), self.headers.get("Content-Type", "").split(";")[0], self.rfile.read(length))
            return self._send(201 if name else 422, name or why, "text/plain; charset=utf-8")
        form = self._form()
        if form is None:
            return self._refuse(403, "受け付けられない送り方です。頁を開き直して、もう一度送ってください。")
        m = re.fullmatch(rf"/toy/({SID})/reprint", self.path)
        if m and m.group(1) in sources():
            return self._reprint(m.group(1), form)
        m = re.fullmatch(rf"/toy/({SID})/(ask-json|record-json)", self.path)
        if m and m.group(1) in sources():
            return self._json_post(m.group(1), m.group(2), form)
        m = re.fullmatch(rf"/toy/({SID})/step", self.path)
        if m and m.group(1) in sources():
            return self._step_post(m.group(1), form)
        m = re.fullmatch(rf"/toy/({SID})/predict-choice", self.path)
        if m and m.group(1) in sources():
            # かざして選ぶ頁の候補（U-44、Issue #118）。受けるのは押した候補の印だけ（動く所の候補。仮説の印ではない）。
            # 選んだ事を予想として残し、仮説の所へ戻す。どの仮説も選んでいないので、窓に出す仮説（see）は付けない。
            from . import kazasu
            sid = m.group(1)
            cand, why = kazasu.choose(sid, form.get("choice", ""))
            if cand is None:
                return self._send(422, kazasu.page(sid, self._look, error="；".join(why)))
            # 頁の段の進み: かざして選んだ予想も「予想を書いた」に数える（U-45 の段取り 2。文字の予想と同じ段）。
            making_log.add_stage(sid, "predict", form.get("who", ""))
            return self._send(303, "", headers=[("Location", f"/toy/{sid}?msg={urllib.parse.quote(kazasu.SENT)}#kasetsu")])
        m = re.fullmatch(rf"/toy/({SID})/(predict|own|print|print-own|record|ask)", self.path)
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
        m = re.fullmatch(r"/record/(R-\d{4,})/(ai-interpret|ai-observe)", self.path)
        if m:
            return self._ai_reply(m.group(1), m.group(2), form)
        m = re.fullmatch(r"/record/(R-\d{4,})/next", self.path)
        if m:
            return self._next_version(m.group(1), form)
        m = re.fullmatch(r"/record/(R-\d{4,})/explain", self.path)
        if m:
            rid = m.group(1)
            rec = loop.record(rid)
            failures = loop.save_explanation(rid, form.get("by", ""), form.get("text", ""), form.get("next_idea", ""))
            if failures:
                return self._send(422, self._toy(rec["source_id"], errors=[f.message for f in failures], at=rid, filled=("explain", form)))
            return self._done(rec["source_id"], "説明を残しました", form.get("back", ""), anchor=rid)
        self._refuse(404, "リンクが古いか、道が違うようです。", "見つかりません")

    def _ai_reply(self, rid, act, form):
        """手帖で AI の返事を受ける口（J-013 の決める点 2: 子どもも AI から直接返事をもらってよい。紙 → 人の説明 → AI の順）。
        人の説明が先に無い記録には呼ばない。鍵が無い時は、鍵が置かれると答える事を伝えて止める（J-023）。"""
        from api import ask
        from api.budget import BudgetStop

        rec = loop.record(rid)
        sid = rec["source_id"]
        if loop.explanation(rid) is None:
            return self._send(422, self._toy(sid, errors=["先に何が起きたと思うかを書く"], at=rid))
        if not ask._key_present():
            return self._done(sid, "鍵が置かれると、Claude が答えます", form.get("back", ""), anchor=rid)
        try:
            from api.agent import default_client

            if act == "ai-interpret":
                from api.loop_agents import draft_interpretation

                _, failures = draft_interpretation(rid, client=default_client("interpret"))
                msg = "Claude の読みを出しました" if not failures else failures[0].message
            else:
                from api import observe

                from . import techo_site
                videos = [f for f in techo_site.media_of(rid) if f.endswith(("mp4", "mov"))]
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
        if (hypotheses.need_prediction(sid) or hid not in {h["id"] for h in hypotheses.load(sid)["hypotheses"]}
                or not (v.isascii() and v.isdigit() and int(v) in loop.adopted_versions(sid, hid))):
            return self._send(422, self._toy(sid, errors=["その版は採られていません"], at="win"))
        if loop.print_version(sid, hid, int(v), out_dir(sid)) != 0:
            return self._send(422, self._toy(sid, errors=[f"版 {v} を刷れませんでした（検査に落ちた）"], at="win"))
        loop.confirm_sheet(sid, hid, int(v), "画面の使い手", TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].SHEET_SET)
        return self._done(sid, f"版 {v} を刷りました。100% で印刷します", see=hid, anchor="win")

    def _next_version(self, rid, form):
        """人の解釈の確定 → 人が書いた変更の案 → 人が採る → 次の版を刷る。どこかで床に落ちたら、その理由を出して止め、何も残さない（#158）。"""
        rec = loop.record(rid)
        sid, hid = rec["source_id"], rec["hypothesis_id"]
        if loop.explanation(rid) is None:
            return self._send(422, self._toy(sid, errors=["先に説明を書く"], at=rid))
        to = _num(form.get("to"))
        if not isinstance(to, float):
            return self._send(422, self._toy(sid, errors=["新しい値は数で書く"], at=f"next-{rid}", filled=("next", form)))
        # 折りの数のような整数の寸法は、整数で渡す（範囲の検査が小数の折り数を落とすため）。
        to = int(to) if to.is_integer() else to
        source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
        change = {"param": form.get("param"), "to": to, "why": form.get("why", "")}
        v, failures = loop.next_version(rid, form.get("by", ""), form.get("interpretation", "").strip() or None, change, source, out_dir(sid))
        if failures:
            from . import toy

            return self._send(422, self._toy(sid, errors=toy.next_reasons(failures, sid, hid, change["param"]), at=f"next-{rid}", filled=("next", form)))
        return self._done(sid, f"版 {v} を刷りました。100% で印刷します", form.get("back", ""), see=hid, anchor="win")

    def _step_post(self, sid, form):
        """作りながら見る頁の札（次の手順へ・戻る・止まった・できた）と、頁を開いた事。残すのは手順の番号と出来事だけ（making_log.add_step）。
        決まりの外（予想の前・刷っていない紙・数でない番号・手順の数の外・知らない出来事）は 422。映像や写真はこの口では受けない（form の欄だけ）。"""
        from . import tsukuru

        as_json = form.get("json") == "1"
        bad = lambda why: self._send(422, json.dumps({"error": why}, ensure_ascii=False) if as_json else why,
                                     "application/json; charset=utf-8" if as_json else "text/plain; charset=utf-8")
        if hypotheses.need_prediction(sid):
            return bad("先に予想を書く")
        hid, event = form.get("hypothesis", ""), form.get("event", "")
        if hid not in {h["id"] for h in hypotheses.load(sid)["hypotheses"]} or not printed_versions(sid, hid):
            return bad("刷った紙をえらぶ")
        if event not in making_log.EVENTS:
            return bad("その札は無い")
        total = tsukuru.count(sid, hid, sheet_version_of(sid, hid, form))
        try:
            step = int(form.get("step", ""))
        except ValueError:
            return bad("手順の番号は数で")
        if not 1 <= step <= max(total, 1):
            return bad("その手順は無い")
        # 最後の手順の「次の手順へ」は動かないので残さない（残すと、途中でやめた段の数えで、無い手順が出る）。
        if not (event == "next" and step >= total):
            making_log.add_step(sid, hid, sheet_version_of(sid, hid, form), step, event, who=form.get("who", ""))
        if event == "start":
            making_log.add_stage(sid, "make", form.get("who", ""))  # 頁の段の進み: 作る頁を開いた（U-45 の段取り 2）
        # 次に見せる手順: 進む・戻るは 1 つ動かし、止まった・できた・開いたは同じ手順のまま。
        nxt = min(step + 1, max(total, 1)) if event == "next" else max(step - 1, 1) if event == "back" else step
        if as_json:
            return self._send(200, json.dumps({"ok": True, "step": nxt}), "application/json; charset=utf-8")
        ev = f"&ev={event}" if event in ("stuck", "done") else ""
        return self._send(303, "", headers=[("Location", f"/toy/{sid}/tsukuru?h={urllib.parse.quote(hid)}&v={sheet_version_of(sid, hid, form)}&n={nxt}{ev}")])

    def _ask(self, sid, hid, question):
        """手順の質問を Claude へ。失敗は理由を作る側の記録に残し、投げ直す（画面の文は呼ぶ側が決める）。"""
        from api import ask

        try:
            return ask.answer(sid, hid, question)
        except Exception as e:
            failure_log.claude_failed("ask", "POST", self.path, e, private=(question,))
            raise

    def _json_post(self, sid, act, form):
        """手帖の頁から呼ぶ口。頁を作り直さず、答えか記録の番号だけを返す。"""
        out = lambda code, obj: self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")
        if hypotheses.need_prediction(sid):
            return out(422, {"error": "先に予想を書く"})
        hid = form.get("hypothesis", "")
        if not printed_versions(sid, hid):
            return out(422, {"error": "刷った紙をえらぶ"})
        if act == "ask-json":
            from api.budget import BudgetStop

            try:
                text, how = self._ask(sid, hid, form.get("question", ""))
            except BudgetStop as e:
                text, how = f"今は AI に聞けません（{e.note}）", "stop"
            except Exception:
                text, how = "今は AI に聞けません。組み方の紙を見てください", "error"
            # 質問の文だけを工作の様子として残す（本人の決定 11-05 朝。連絡先の形は落とす。答えの文・声・誰が聞いたかは残さない）。
            making_log.add_ask(sid, hid, sheet_version_of(sid, hid, form), form.get("question", ""), how, step=form.get("step"), who=form.get("who", ""))
            return out(200, {"text": text, "from": how})
        rid, failures = records.add({"source_id": sid, "hypothesis_id": hid, "sheet_version": sheet_version_of(sid, hid, form), "result": form.get("result"),
                                     "note": form.get("note", ""), "impression": form.get("impression", ""), "fixes": [], "via": "techo"})
        if rid:
            making_log.add_stage(sid, "record", form.get("who", ""))  # 頁の段の進み: 記録を残した（手帖から）
        return out(201, {"id": rid}) if rid else out(422, {"error": "；".join(f.message for f in failures)})

    def _toy_post(self, sid, act, form):
        see = None  # 刷った時だけ、戻り先を型紙の窓にする
        anchor = "kiroku"  # 予想と自分の仮説は次の段へ戻す（要件 L-04）。試した記録の欄へ戻すのは記録だけ
        if act == "ask":
            # 手順の質問は、試した記録（仮説への返事）には入れず、その場で答えを頁に出す。順（紙 → 記録と説明 → AI）には入らない。
            # 質問の文だけは工作の様子（omochae.making_log）に残す: 何で止まるかを、案内と答えを直す材料にする（本人の決定 11-05 朝）。
            from api import ask
            from api.budget import BudgetStop

            hid = form.get("hypothesis", "")
            if hypotheses.need_prediction(sid) or not printed_versions(sid, hid):
                return self._send(422, self._toy(sid, errors=["刷った紙について聞けます。先に予想を書いて、紙を刷ってください"], at="ask", filled=("ask", form)))
            try:
                text, how = self._ask(sid, hid, form.get("question", ""))
            except BudgetStop as e:  # 額の入った例外の文は出さず、止めた線だけを言う
                text, how = f"今は AI に聞けません（{e.note}）", "stop"
            except Exception:
                text, how = "今は AI に聞けません。型紙の凡例と手順の紙の絵を見てください", "error"
            making_log.add_ask(sid, hid, sheet_version_of(sid, hid, form), form.get("question", ""), how, step=form.get("step"), who=form.get("who", ""))
            return self._send(200, self._toy(sid, asked=(form.get("question", ""), text)))
        if act == "predict":
            _, failures = hypotheses.save_prediction(sid, form.get("text", ""))
            msg = "予想を残しました"
            anchor = "kasetsu"
        elif act == "own":
            own, failures = hypotheses.save_own(sid, form.get("name", ""), form.get("how", ""), form.get("evidence", ""))
            msg = "仮説を残しました。「紙を刷る」で、身の回りの紙と紐で作る型紙なしの紙が刷れます"
            anchor = f"own-{own['id']}" if own else anchor
        elif act == "print-own":
            oid = form.get("id", "")
            if oid not in {h["id"] for h in hypotheses.own_hypotheses(sid)}:
                return self._send(422, self._toy(sid, errors=[f"仮説 {oid} は無い"], at="yosou"))
            out_dir(sid).mkdir(parents=True, exist_ok=True)
            if hypotheses.print_own(sid, oid, str(out_dir(sid) / f"{oid}_v1")) != 0:
                return self._send(422, self._toy(sid, errors=["紙を刷れませんでした（検査に落ちた）"], at=f"own-{oid}"))
            failures, msg = [], "刷りました。100% で印刷します"
        elif act == "print":
            failures = hypotheses.need_prediction(sid)
            hid = form.get("hypothesis", "")
            if not failures and hid not in {h["id"] for h in hypotheses.load(sid)["hypotheses"]}:
                return self._send(422, self._toy(sid, errors=[f"仮説 {hid} は無い"], at="kasetsu"))
            if not failures:
                out_dir(sid).mkdir(parents=True, exist_ok=True)
                # 刷るのは一番新しい版（報告から直した版）。次に作る人に改善した型紙を渡すため（本人の方針 11-05「報告を型紙の改善に回し、
                # より良い型紙を提供する」）。版 1 しか無ければ版 1。
                v = loop.latest_version(sid, hid)
                # 一番新しい版が刷れない時は、1 つ前の版へ戻る: 採った版が検査に落ちたまま残ると、その仮説の紙が誰にも刷れなくなるため。
                while hypotheses.print_sheet(sid, hid, str(out_dir(sid) / f"{hid}_v{v}"), v) != 0:
                    if v <= 1:
                        return self._send(422, self._toy(sid, errors=["型紙を刷れませんでした（検査に落ちた）"], at="kasetsu"))
                    v -= 1
                # 刷ると選んだ事が型紙の確定（f09）。名前の欄は画面に無いので、使い手として残す。
                loop.confirm_sheet(sid, hid, v, "画面の使い手", TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].SHEET_SET)
            msg = "刷りました。下の窓で絵を見て、PDF を 100% で印刷します"
            see = hid
        else:
            if hypotheses.need_prediction(sid):
                failures = hypotheses.need_prediction(sid)
            else:
                hid = form.get("hypothesis", "")
                # 版は刷ってある一番新しい物（報告はその版への返事）。感想は本人の方針（11-05）「感想と動きの報告」の欄。
                rec = {"source_id": sid, "hypothesis_id": hid, "sheet_version": sheet_version_of(sid, hid, form), "result": form.get("result"),
                       "impression": form.get("impression", "").strip(),
                       "opened_deg": _num(form.get("opened_deg")), "opener": form.get("opener") or None, "power": form.get("power") or None,
                       "minutes_to_try": _num(form.get("minutes_to_try")), "fixes": [], "note": form.get("note", ""),
                       "answers": {k: form[k] for k in ("first_moved", "stuck", "what_if") if form.get(k, "").strip()},
                       "ideas": [form["idea"]] if form.get("idea", "").strip() else []}
                rid, failures = records.add(rec)
                anchor = rid or anchor  # 今残した記録の札に着く。欄に戻ると、押す前と同じ画面に見える（#121）
            msg = "記録を残しました。試した後の紙が開けます"
        if failures:
            at = {"predict": "yosou", "own": "yosou", "print": "kasetsu"}.get(act, "kiroku")
            return self._send(422, self._toy(sid, errors=[f.message for f in failures], at=at, filled=(act, form)))
        # 頁の段の進み（予想を書いた・刷った・記録を残した）を工作の様子に残す（U-45 の段取り 2）。何を書いたかは写さない。
        # 人の印は画面が送った時だけ。書けなくても例外は出ないので、この口は止まらない。
        if act in ("predict", "print", "record"):
            making_log.add_stage(sid, act, form.get("who", ""))
        self._done(sid, msg, see=see, anchor="win" if see else anchor)


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
    # 開いた場では写真と動画を受けず、出しもしない（上の受け口と、下の /record/…/media の道）。
    if public_open and public_key:
        raise ValueError("合言葉付きと合言葉なしは同時に使えない")
    if public_open:
        # 鍵のある場所では開かない: 誰でも聞く口から費用のかかる呼び出しができてしまうため（J-028）。
        from api import ask
        if ask._key_present():
            raise ValueError("鍵（.env）がある所では、合言葉なしで開けない")
    server.public_open = bool(public_open)
    server.look = look
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
