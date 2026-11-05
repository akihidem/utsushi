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

from omochae import hypotheses, loop, records
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
.cap{font-size:.78em;color:#6b604f;margin-top:8px}
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
            f'<style>{LOOK}{BOOK}{extra_style}</style><body{cls}><main>{body}</main></body></html>')


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
.switch{max-width:1180px;margin:0 auto;padding:14px 20px;font-size:.85em;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
@media (max-width:760px){.sheet{grid-template-columns:1fr}.sheet::after{display:none}.pg.l{border-right:0;border-bottom:1px solid #e3d9c4}.pg{padding:24px}}
"""


# 画面で変えてよい寸法と、その呼び名。変えてよい寸法そのものは台帳の決まり（metrics.ALLOWED）に従う。
PARAM_NAMES = {"fold_count": "折りの数", "fold_width": "折りの幅（mm）", "fold_height": "扇の高さ（mm）", "tube_side": "外筒の一辺（mm）",
               "pusher_side": "内筒の一辺（mm）", "push_amount": "押し上げる量（mm）", "pivot_above_rim": "扇の中心の高さ（mm）",
               "paper_thickness": "紙の厚さ（mm）", "weight_g": "重りの重さ（g）", "weight_below_axle": "重りの軸からの下がり（mm）",
               "weight_behind": "重りの後ろへのずれ（mm）", "ear_length": "耳の長さ（mm）", "neck_length": "首の長さ（mm）",
               "opening": "胴の口の幅（mm）", "head_w": "頭の幅（mm）", "head_h": "頭の高さ（mm）", "paper_gsm": "紙の重さ（g/m²）"}


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
        # 皮（白の展示・黒のジン）を選んだ時だけ cookie を書く。合言葉の cookie（_gate）とは別の名前。
        for k, v in getattr(self, "_cookie", ()):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _host_ok(self):
        # DNS rebinding で外のサイトから手元の記録を読み書きさせないため、手元の名前だけを受ける。
        port = self.server.server_address[1]
        # 家の網に開いた時（--lan）は、この機械の網の中の番地と名前だけを足す。ほかの名前は今までどおり断る。
        extra = getattr(self.server, "lan_hosts", ())
        host = self.headers.get("Host", "")
        # デモの一周を外の機器から開く時（public_key あり）は、トンネルの名前を足す。名前は毎回変わるので形で受け、合言葉の門（_gate）で絞る。
        if getattr(self.server, "public_key", None) and re.fullmatch(TUNNEL_HOST, host):
            return True
        return host in (f"127.0.0.1:{port}", f"localhost:{port}", *(f"{h}:{port}" for h in extra))

    def _origin_ok(self):
        # トンネルの先は https、手元は http。どちらも同じ Host の頁から来た物だけを受ける（別のサイトから送らせない）。
        host = self.headers.get("Host", "")
        ok = {f"http://{host}"} | ({f"https://{host}"} if getattr(self.server, "public_key", None) else set())
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
        self._send(403, "合言葉付きのリンクから開いてください")
        return False

    def _pick_look(self):
        """この要求の皮。?look= が先、次に cookie、無ければ既定（skin.DEFAULT）。?look= の時は cookie に移して全部の頁に続ける。"""
        _, _, query = self.path.partition("?")
        self._look, want = skinmod.pick(self.headers.get("Cookie", ""), query)
        self._cookie = [skinmod.cookie_header(want)] if want else []

    def _toy(self, sid, **kw):
        return toy_page(sid, look=self._look, **kw)

    def do_GET(self):
        try:
            self._pick_look()
            if self._gate():
                self._get()
        except Exception as e:
            failure_log.request_failed("GET", self.path, e)
            self._send(500, "うまく表示できませんでした")

    def do_POST(self):
        try:
            self._pick_look()
            if self._gate():
                self._post()
        except Exception as e:
            failure_log.request_failed("POST", self.path, e)
            self._send(500, "受け付けられませんでした")

    def _get(self):
        if not self._host_ok():
            return self._send(403, "受け付けられません")
        path, _, query = self.path.partition("?")
        qs = urllib.parse.parse_qs(query)
        look = self._look
        from .looks import PAGES

        # 入口は皮の入口（A′ 白の展示が既定、黒のジンは cookie か ?look=zine）。A はルックブックの再現として /look/taiban に残す（カード 011452 の Q1・Q2）。
        if path == "/":
            return self._send(200, PAGES["zine" if look == "zine" else "tenji"]())
        m = re.fullmatch(r"/look/([a-z]+)", path)
        if m:
            if m.group(1) in PAGES:
                if m.group(1) in skinmod.SKINS:
                    # 入口で皮が決まり、以後の頁に続く（要件の L-01）。
                    self._look, self._cookie = m.group(1), [skinmod.cookie_header(m.group(1))]
                return self._send(200, PAGES[m.group(1)]())
        if path == "/about":
            from . import about
            return self._send(200, about.page(look, path))
        if path == "/toys":
            from . import toys
            return self._send(200, toys.page(look, path))
        if path == "/gallery":
            from . import techo_site
            from .demo_samples import STYLE as SAMPLE_STYLE
            return self._send(200, skinmod.shell("上げた物と、職人の言葉", techo_site.gallery_page(sources()), look, "/gallery", path, techo_site.STYLE + SAMPLE_STYLE, "techo"))
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
        m = re.fullmatch(rf"/toy/({SID})/techo", path)
        if m and m.group(1) in sources():
            # 手帖は入口のサイトの中の一続きの頁（本人の方向転換、11-04）。予想の前は仮説の字も出さない（F9.prediction）。
            sid = m.group(1)
            if hypotheses.need_prediction(sid):
                return self._send(200, self._toy(sid, errors=["先に予想を書くと、手帖が開きます"]))
            printed = [h["id"] for h in hypotheses.load(sid)["hypotheses"] if (out_dir(sid) / f"{h['id']}_v1.pdf").exists()]
            pic = f"/picture/{sid}" if (ROOT / "out/sources" / f"{sid}.jpg").exists() else ""
            from . import techo_site
            return self._send(200, skinmod.shell("手帖", techo_site.page(sid, printed, pic), look, "", path, techo_site.STYLE, "techo"))
        m = re.fullmatch(r"/record/(R-\d{4,})/media/(m\d+\.(?:jpg|png|mp4|mov))", path)
        if m:
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
            try:
                v = int(qs.get("v", ["1"])[0])
            except ValueError:
                v = 1
            return self._send(200, self._toy(m.group(1), msg=qs.get("msg", [""])[0], see=qs.get("see", [None])[0], kind=kind, v=v, path=path))
        m = re.fullmatch(rf"/picture/({SID})", path)
        if m and (ROOT / "out/sources" / f"{m.group(1)}.jpg").exists():
            return self._send(200, (ROOT / "out/sources" / f"{m.group(1)}.jpg").read_bytes(), "image/jpeg")
        # 刷った紙。PDF（刷る）のほかに PNG と SVG（画面で見る、要件の S-01）。試した後の紙はどの形でも記録の前は渡さない。
        m = re.fullmatch(rf"/sheet/({SID})/((?:H-[A-Z0-9]+|OWN-\d+)_v\d+(?:_tejun|_after|_free)?)\.(pdf|svg|png)", path)
        if m and m.group(1) in sources():
            sid, stem, ext = m.groups()
            hid = re.split(r"_v\d+", stem)[0]
            if stem.endswith("_after") and hid not in {r["hypothesis_id"] for r in records.all_records(sid)}:
                return self._send(403, "試した記録を残してから開きます")
            f = out_dir(sid) / f"{stem}.{ext}"
            if f.exists():
                return self._send(200, f.read_bytes(), {"pdf": "application/pdf", "svg": "image/svg+xml", "png": "image/png"}[ext])
        self._send(404, "見つかりません")

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
        self._send(303, "", headers=[("Location", f"/toy/{sid}?msg={urllib.parse.quote(msg)}{extra}#{anchor}")])

    def _post(self):
        if not self._host_ok():
            return self._send(403, "受け付けられません")
        m = re.fullmatch(r"/record/(R-\d{4,})/media", self.path)
        if m:
            # 写真と動画はフォームでなく本体そのままで受ける。別のサイトから送らせないため、同じ出所だけを受ける。
            from . import techo_site
            if not self._origin_ok():
                return self._send(403, "受け付けられない送り方です")
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
            return self._send(403, "受け付けられない送り方です")
        m = re.fullmatch(rf"/toy/({SID})/(ask-json|record-json)", self.path)
        if m and m.group(1) in sources():
            return self._json_post(m.group(1), m.group(2), form)
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
                return self._send(422, self._toy(rec["source_id"], errors=[f.message for f in failures]))
            return self._done(rec["source_id"], "説明を残しました", form.get("back", ""))
        self._send(404, "見つかりません")

    def _ai_reply(self, rid, act, form):
        """手帖で AI の返事を受ける口（J-013 の決める点 2: 子どもも AI から直接返事をもらってよい。紙 → 人の説明 → AI の順）。
        人の説明が先に無い記録には呼ばない。鍵が無い時は、鍵が置かれると答える事を伝えて止める（J-023）。"""
        from api import ask
        from api.budget import BudgetStop

        rec = loop.record(rid)
        sid = rec["source_id"]
        if loop.explanation(rid) is None:
            return self._send(422, self._toy(sid, errors=["先に何が起きたと思うかを書く"]))
        if not ask._key_present():
            return self._done(sid, "鍵が置かれると、Claude が答えます", form.get("back", ""))
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
                    return self._done(sid, "動画を上げると、Claude が見えた事を返します", form.get("back", ""))
                _, why = observe.observe(rid, techo_site.media_dir(rid) / videos[0], default_client("observe"))
                msg = "Claude が見えた事を出しました" if not why else why
        except BudgetStop as e:  # 今日の上限か累計の停止線かを言う（待てば聞けるのかが分かるように）
            failure_log.claude_failed(act.removeprefix("ai-"), "POST", self.path, e)
            msg = f"今は AI に聞けません（{e.note}）"
        except Exception as e:  # 画面の文は変えない。理由は作る側の記録に残す
            failure_log.claude_failed(act.removeprefix("ai-"), "POST", self.path, e)
            msg = "今は AI に聞けません"
        return self._done(sid, msg, form.get("back", ""))

    def _next_version(self, rid, form):
        """人の解釈の確定 → 人が書いた変更の案 → 人が採る → 次の版を刷る。どこかで床に落ちたら、その理由を出して止める。"""
        rec = loop.record(rid)
        sid, hid = rec["source_id"], rec["hypothesis_id"]
        if loop.explanation(rid) is None:
            return self._send(422, self._toy(sid, errors=["先に説明を書く"]))
        by = form.get("by", "")
        failures = loop.confirm_interpretation(rid, by, form.get("interpretation", "").strip() or None)
        if failures:
            return self._send(422, self._toy(sid, errors=[f.message for f in failures]))
        to = _num(form.get("to"))
        if not isinstance(to, float):
            return self._send(422, self._toy(sid, errors=["新しい値は数で書く"]))
        # 折りの数のような整数の寸法は、整数で渡す（範囲の検査が小数の折り数を落とすため）。
        to = int(to) if to.is_integer() else to
        source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
        pid, failures = loop.save_proposal({"record_ids": [rid], "hypothesis_id": hid, "changes": [{"param": form.get("param"), "to": to, "why": form.get("why", "")}]}, source, "human")
        if failures:
            return self._send(422, self._toy(sid, errors=[f.message for f in failures]))
        made, failures = loop.adopt(pid, by, accept_params=[form.get("param")], source=source)
        if failures or "version" not in made:
            return self._send(422, self._toy(sid, errors=[f.message for f in failures] or ["次の版ができませんでした"]))
        v = made["version"]
        out_dir(sid).mkdir(parents=True, exist_ok=True)
        if hypotheses.print_sheet(sid, hid, str(out_dir(sid) / f"{hid}_v{v}"), v) != 0:
            return self._send(422, self._toy(sid, errors=[f"版 {v} を刷れませんでした（検査に落ちた）"]))
        loop.confirm_sheet(sid, hid, v, by, TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].SHEET_SET)
        return self._done(sid, f"版 {v} を刷りました。100% で印刷します", form.get("back", ""), see=hid, anchor="win")

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
        if not (out_dir(sid) / f"{hid}_v1.pdf").exists():
            return out(422, {"error": "刷った紙をえらぶ"})
        if act == "ask-json":
            from api.budget import BudgetStop

            try:
                text, how = self._ask(sid, hid, form.get("question", ""))
            except BudgetStop as e:
                text, how = f"今は AI に聞けません（{e.note}）", "stop"
            except Exception:
                text, how = "今は AI に聞けません。組み方の紙を見てください", "error"
            return out(200, {"text": text, "from": how})
        rid, failures = records.add({"source_id": sid, "hypothesis_id": hid, "sheet_version": 1, "result": form.get("result"),
                                     "note": form.get("note", ""), "fixes": [], "via": "techo"})
        return out(201, {"id": rid}) if rid else out(422, {"error": "；".join(f.message for f in failures)})

    def _toy_post(self, sid, act, form):
        see = None  # 刷った時だけ、戻り先を型紙の窓にする
        anchor = "kiroku"  # 予想と自分の仮説は次の段へ戻す（要件 L-04）。試した記録の欄へ戻すのは記録だけ
        if act == "ask":
            # 手順の質問は記録に残さず、その場で答えを頁に出す。仮説への返事の順（紙 → 記録と説明 → AI）には入らない。
            from api.budget import BudgetStop

            hid = form.get("hypothesis", "")
            if hypotheses.need_prediction(sid) or not (out_dir(sid) / f"{hid}_v1.pdf").exists():
                return self._send(422, self._toy(sid, errors=["刷った紙について聞けます。先に予想を書いて、紙を刷ってください"]))
            try:
                text, _ = self._ask(sid, hid, form.get("question", ""))
            except BudgetStop as e:  # 額の入った例外の文は出さず、止めた線だけを言う
                text = f"今は AI に聞けません（{e.note}）"
            except Exception:
                text = "今は AI に聞けません。型紙の凡例と手順の紙の絵を見てください"
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
                return self._send(422, self._toy(sid, errors=[f"仮説 {oid} は無い"]))
            out_dir(sid).mkdir(parents=True, exist_ok=True)
            if hypotheses.print_own(sid, oid, str(out_dir(sid) / f"{oid}_v1")) != 0:
                return self._send(422, self._toy(sid, errors=["紙を刷れませんでした（検査に落ちた）"]))
            failures, msg = [], "刷りました。100% で印刷します"
        elif act == "print":
            failures = hypotheses.need_prediction(sid)
            hid = form.get("hypothesis", "")
            if not failures and hid not in {h["id"] for h in hypotheses.load(sid)["hypotheses"]}:
                return self._send(422, self._toy(sid, errors=[f"仮説 {hid} は無い"]))
            if not failures:
                out_dir(sid).mkdir(parents=True, exist_ok=True)
                if hypotheses.print_sheet(sid, hid, str(out_dir(sid) / f"{hid}_v1")) != 0:
                    return self._send(422, self._toy(sid, errors=["型紙を刷れませんでした（検査に落ちた）"]))
                # 刷ると選んだ事が型紙の確定（f09）。名前の欄は画面に無いので、使い手として残す。
                loop.confirm_sheet(sid, hid, 1, "画面の使い手", TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].SHEET_SET)
            msg = "刷りました。下の窓で絵を見て、PDF を 100% で印刷します"
            see = hid
        else:
            if hypotheses.need_prediction(sid):
                failures = hypotheses.need_prediction(sid)
            else:
                rec = {"source_id": sid, "hypothesis_id": form.get("hypothesis"), "sheet_version": 1, "result": form.get("result"),
                       "opened_deg": _num(form.get("opened_deg")), "opener": form.get("opener") or None, "power": form.get("power") or None,
                       "minutes_to_try": _num(form.get("minutes_to_try")), "fixes": [], "note": form.get("note", ""),
                       "answers": {k: form[k] for k in ("first_moved", "stuck", "what_if") if form.get(k, "").strip()},
                       "ideas": [form["idea"]] if form.get("idea", "").strip() else []}
                _, failures = records.add(rec)
            msg = "記録を残しました。試した後の紙が開けます"
        if failures:
            return self._send(422, self._toy(sid, errors=[f.message for f in failures]))
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


def serve(port=8766, lan=False, public_key=None):
    """lan=True は本人の決定（11-04、U-36）で、家の網から iPhone で手帖を開くための切り替え。既定は今までどおり手元だけ。
    public_key はデモの一周をパソコン・iPad・iPhone から開く時（本人の決定 A、11-04）。短すぎる合言葉は断る（当てられないため）。"""
    if public_key is not None and len(public_key) < 16:
        raise ValueError("合言葉が短すぎる（16 字以上）")
    server = ThreadingHTTPServer(("0.0.0.0" if lan else "127.0.0.1", port), Handler)
    server.lan_hosts = tuple(lan_addresses()) if lan else ()
    server.public_key = public_key
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
        args = [a for a in argv if a != "--lan"]
        lan = "--lan" in argv
        port = int(args[0]) if args else 8766
        server = serve(port, lan=lan, public_key=key)
    except (ValueError, OSError, OverflowError, IndexError) as e:
        print(f"検査できない: 開けない: {e}", file=sys.stderr)
        sys.exit(4)
    print(f"http://127.0.0.1:{port}/")
    for h in server.lan_hosts:
        print(f"家の網から: http://{h}:{port}/  （同じ網の iPhone で開く。音声認識は https でないので使えない見込みで、字の入力と読み上げは使える）")
    server.serve_forever()
