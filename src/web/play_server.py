"""使い手の入口: 手元で動くブラウザの画面（本人の決定、J-024）。依存を増やさず標準の http.server で作る。

判断の芯: コマンドの輪と同じ線を画面でも守る。予想が先（F9.prediction）、仮説に順位を出さない（J-013）、
試した後の紙は記録を残すまで渡さない（J-013）、結果は人が入れる値で、成績にしない（philosophy.md）。
Claude を呼ぶ所は置かない。鍵なしで輪の前半（予想 → 型紙 → 試す → 記録 → 人の説明）が回る。
持ち寄りの画面（contrib_server.py）と同じく 127.0.0.1 にだけ開く。外に開く責任を週内に持てないため。
"""
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

from .contrib_server import STYLE

# 見た目はルックブックの様式（本人の指定、J-024）。絵が主役で、文字は添え。見開きのように絵と短い文を左右に置き、玩具ごとに左右を入れ替える。
# 本人が参照した X の記事の実物はまだ届いていないので、様式だけを写す。届いたら、この塊と下の 2 つの頁の組み方だけを替える。
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
SID = r"NDL-\d+-R\d+-[LR]"


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


def song(src, short=False):
    """歌は人が確かめた読みだけを、原文の引用として出す。採らなかった読みは出さない（labels.source_lines と同じ線）。

    本の頁のように縦に組む。引用の印（誰が確かめたか）は短くしても消さない。図鑑の文の印（J-016）を画面でも守るため。
    """
    lines = [e for e in src.get("transcription", {}).get("entries", []) if not e.get("rejected_by") and e.get("checked_by")]
    return "".join(f'<p class="song">{esc(e["text"])}</p><p class="cap">原文の引用。確かめた人: {esc(e["checked_by"])}</p>' for e in lines)


def sheets(sid, hid, recorded):
    """刷った紙へのリンク。試した後の紙は、その仮説の記録が 1 件でもある時だけ出す（試す前に渡さない）。"""
    links = []
    for suffix, label in (("", "型紙"), ("_tejun", "手順の紙"), ("_after", "試した後の紙")):
        name = f"{hid}_v1{suffix}.pdf"
        if (out_dir(sid) / name).exists() and (suffix != "_after" or recorded):
            links.append(f'<a href="/sheet/{sid}/{name}">{label}</a>')
    return "・".join(links)


def toy_page(sid, errors=(), msg=""):
    data, src = hypotheses.load(sid), source(sid)
    note = "".join(f'<p id="msg">{esc(e)}</p>' for e in errors) + (f'<p id="msg">{esc(msg)}</p>' if msg else "")
    # 頁の頭は見開き: 大きな図と、名前と縦組みの歌。操作の欄はその下に置く。
    # 入口の冊子と同じ見開きの紙。玩具の頁ではめくらず、この 1 枚の下に操作の欄を置く。
    has_pic = (ROOT / "out/sources" / f"{sid}.jpg").exists()
    pic = f'<img src="/picture/{sid}" alt="{esc(data["toy"])}の図">' if has_pic else f'<a href="{esc(src["image_url"])}">図を見る（国立国会図書館）</a>'
    hero = (f'<div class="booklet"><section class="sheet"><div class="pg l full">{pic}<p class="cap">{esc(src.get("holding", ""))}</p></div>'
            f'<div class="pg r"><p class="cap"><a href="/">← 玩具の一覧</a></p><h2>{esc(data["toy"])}</h2>{song(src)}</div></section></div>')
    preds = hypotheses.predictions(sid)
    latest = json.loads(preds[-1].read_text(encoding="utf-8"))["text"] if preds else None
    form_pred = f'<form method="post" action="/toy/{sid}/predict"><label>どう動くと思いますか（先に書きます）<textarea name="text" required></textarea></label><button>予想を残す</button></form>'
    form_own = (f'<form method="post" action="/toy/{sid}/own"><h3>自分の仮説を立てる</h3><label>名前<input type="text" name="name" required></label>'
                f'<label>動かし方<textarea name="how" required></textarea></label><label>図のどこを見たか<input type="text" name="evidence" required></label><button>仮説を残す</button></form>')
    if hypotheses.need_prediction(sid):
        # 予想の前は仮説を見せない。答えを先に見せないため（F9.prediction）。
        return page(data["toy"], hero + f'<div class="wrap">{note}{form_pred}{form_own}</div>')
    recs = records.all_records(sid)
    recorded = {r["hypothesis_id"] for r in recs}
    own = hypotheses.own_hypotheses(sid)
    body = note
    body += (f"<article><h2>あなたの予想</h2><p>{esc(latest)}</p></article>" if latest else "") + form_pred
    for h in own:
        # 寸法の無い自分の仮説には、型紙なしの紙（身の回りの紙と紐で作る紙）を返す。本人の決定。
        free = f'{h["id"]}_v1_free.pdf'
        link = f'<a href="/sheet/{sid}/{free}">型紙なしの紙</a>' if (out_dir(sid) / free).exists() else ""
        body += (f'<article><h3>あなたの仮説 {esc(h["id"])} {esc(h["name"])}</h3><p>{esc(h["how_it_moves"])}</p><p class="meta">根拠: {esc(h["evidence"])}</p>'
                 f'<form method="post" action="/toy/{sid}/print-own"><input type="hidden" name="id" value="{esc(h["id"])}"><button>紙を刷る</button></form><p>{link}</p></article>')
    body += form_own + f'<h2>仮説</h2><p class="meta">{esc(data["note"])}</p><div class="plates">'
    # 並びは記録の順位でなく、元の記録の並び。順位は学ぶ人の画面に出さない（J-013）。
    for h in data["hypotheses"]:
        ev = "".join(f'<li>〔{esc(e["certainty"])}〕{esc(e["what"])}（{esc(e["where"])}）</li>' for e in h["evidence"])
        printed = sheets(sid, h["id"], h["id"] in recorded)
        # 仮説は図版の 1 枚のように並べる。大きな字は仮説の名札で、順位ではない（並びは元の記録の順）。
        body += (f'<div class="plate"><div class="letter">{esc(hypotheses.letter(h))}</div><h3>仮説 {esc(hypotheses.letter(h))}「{esc(h["name"])}」</h3><p>{esc(h["how_it_moves"])}</p><ul>{ev}</ul>'
                 f'<p class="meta">試して見る事: {esc(h["to_measure"])}</p>'
                 f'<form method="post" action="/toy/{sid}/print"><input type="hidden" name="hypothesis" value="{esc(h["id"])}"><button>型紙と手順の紙を刷る</button></form>'
                 f'<p>{printed}</p></div>')
    body += "</div>" + record_form(sid, data, own) + records_list(recs)
    return page(data["toy"], hero + f'<div class="wrap">{body}</div>')


def record_form(sid, data, own):
    template = data.get("template", "slider_fan")
    hyps = [(h["id"], f'仮説 {hypotheses.letter(h)}「{h["name"]}」') for h in data["hypotheses"]] + [(h["id"], f'あなたの仮説「{h["name"]}」') for h in own]
    opts = "".join(f'<option value="{esc(i)}">{esc(n)}</option>' for i, n in hyps)
    results = "".join(f'<label class="check"><input type="radio" name="result" value="{esc(r)}" required>{esc(r)}</label>' for r in TEMPLATES[template].RESULTS)
    if template == "pivot_counterweight":
        extra = '<label>動かした物<select name="power"><option value="">—</option><option>手</option><option>息</option><option>団扇</option><option>風</option></select></label>'
    else:
        extra = ('<label>開いた角度（度。測った時だけ）<input type="text" name="opened_deg" inputmode="decimal"></label>'
                 '<label>開いた力<select name="opener"><option value="">—</option><option>紙の力</option><option>糸</option><option>手</option></select></label>')
    return (f'<form method="post" action="/toy/{sid}/record"><h2>試した記録</h2><p class="meta">見た事を残します。動かなかった記録も、そのまま紙の返事です。</p>'
            f'<label>どの仮説の紙か<select name="hypothesis">{opts}</select></label><fieldset><legend>見た事</legend>{results}</fieldset>{extra}'
            '<label>最初に動いたのはどこか<input type="text" name="first_moved"></label><label>引っかかった所<input type="text" name="stuck"></label>'
            '<label>何を変えると違いが出そうか<input type="text" name="what_if"></label><label>作っている途中で思いついた事<input type="text" name="idea"></label>'
            '<label>作り始めて最初に動かすまで（分）<input type="text" name="minutes_to_try" inputmode="decimal"></label><label>メモ<textarea name="note"></textarea></label>'
            '<button>記録を残す</button></form>')


def records_list(recs):
    out = "<h2>これまでの記録</h2>" if recs else ""
    for r in reversed(recs):
        told = loop.explanation(r["id"])
        deg = f'・{r["opened_deg"]:g}°' if r.get("opened_deg") is not None else ""
        if told:
            tail = f'<p>説明: {esc(told["text"])}</p><p>次の思いつき: {esc(told["next_idea"])}</p>'
        else:
            # 人の説明が先。Claude の解釈はこの後の段で、画面からは呼ばない。
            tail = (f'<form method="post" action="/record/{esc(r["id"])}/explain"><label>何が起きたと思いますか（わからない、でもよい）<textarea name="text" required></textarea></label>'
                    '<label>次に試したい事<input type="text" name="next_idea" required></label><label>書いた人<input type="text" name="by" required></label><button>説明を残す</button></form>')
        out += f'<article><h3>{esc(r["id"])} {esc(r["hypothesis_id"])}: {esc(r["result"])}{esc(deg)}</h3><p class="meta">{esc(r["recorded_at"])}</p>{tail}</article>'
    return out


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

    def _host_ok(self):
        # DNS rebinding で外のサイトから手元の記録を読み書きさせないため、手元の名前だけを受ける。
        port = self.server.server_address[1]
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def do_GET(self):
        try:
            self._get()
        except Exception as e:
            print(f"GET の失敗: {type(e).__name__}: {e}", file=sys.stderr)
            self._send(500, "うまく表示できませんでした")

    def do_POST(self):
        try:
            self._post()
        except Exception as e:
            print(f"POST の失敗: {type(e).__name__}: {e}", file=sys.stderr)
            self._send(500, "受け付けられませんでした")

    def _get(self):
        if not self._host_ok():
            return self._send(403, "受け付けられません")
        path, _, query = self.path.partition("?")
        # 入口は本人が残した A 大判写真集（2026-11-04、J-024）。/look/ の下には残した 2 案だけがある。
        if path == "/":
            from .looks import taiban

            return self._send(200, taiban())
        m = re.fullmatch(r"/look/([a-z]+)", path)
        if m:
            from .looks import PAGES

            if m.group(1) in PAGES:
                return self._send(200, PAGES[m.group(1)]())
        m = re.fullmatch(rf"/toy/({SID})", path)
        if m and m.group(1) in sources():
            return self._send(200, toy_page(m.group(1), msg=urllib.parse.parse_qs(query).get("msg", [""])[0]))
        m = re.fullmatch(rf"/picture/({SID})", path)
        if m and (ROOT / "out/sources" / f"{m.group(1)}.jpg").exists():
            return self._send(200, (ROOT / "out/sources" / f"{m.group(1)}.jpg").read_bytes(), "image/jpeg")
        m = re.fullmatch(rf"/sheet/({SID})/((?:H-[A-Z0-9]+|OWN-\d+)_v1(?:_tejun|_after|_free)?\.pdf)", path)
        if m and m.group(1) in sources():
            sid, name = m.groups()
            hid = name.split("_v1")[0]
            # 試した後の紙は、URL を知っていても記録の前は渡さない。
            if name.endswith("_after.pdf") and hid not in {r["hypothesis_id"] for r in records.all_records(sid)}:
                return self._send(403, "試した記録を残してから開きます")
            f = out_dir(sid) / name
            if f.exists():
                return self._send(200, f.read_bytes(), "application/pdf")
        self._send(404, "見つかりません")

    def _form(self):
        # 別のサイトの頁から手元の記録へ送らせないため、同じ出所のフォームだけを受ける。
        if self.headers.get("Origin") != f"http://{self.headers.get('Host', '')}":
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

    def _done(self, sid, msg):
        self._send(303, "", headers=[("Location", f"/toy/{sid}?msg={urllib.parse.quote(msg)}")])

    def _post(self):
        if not self._host_ok():
            return self._send(403, "受け付けられません")
        form = self._form()
        if form is None:
            return self._send(403, "受け付けられない送り方です")
        m = re.fullmatch(rf"/toy/({SID})/(predict|own|print|print-own|record)", self.path)
        if m and m.group(1) in sources():
            sid, act = m.groups()
            return self._toy_post(sid, act, form)
        m = re.fullmatch(r"/record/(R-\d{4,})/explain", self.path)
        if m:
            rid = m.group(1)
            rec = loop.record(rid)
            failures = loop.save_explanation(rid, form.get("by", ""), form.get("text", ""), form.get("next_idea", ""))
            if failures:
                return self._send(422, toy_page(rec["source_id"], [f.message for f in failures]))
            return self._done(rec["source_id"], "説明を残しました")
        self._send(404, "見つかりません")

    def _toy_post(self, sid, act, form):
        if act == "predict":
            _, failures = hypotheses.save_prediction(sid, form.get("text", ""))
            msg = "予想を残しました"
        elif act == "own":
            _, failures = hypotheses.save_own(sid, form.get("name", ""), form.get("how", ""), form.get("evidence", ""))
            msg = "仮説を残しました。「紙を刷る」で、身の回りの紙と紐で作る型紙なしの紙が刷れます"
        elif act == "print-own":
            oid = form.get("id", "")
            if oid not in {h["id"] for h in hypotheses.own_hypotheses(sid)}:
                return self._send(422, toy_page(sid, [f"仮説 {oid} は無い"]))
            out_dir(sid).mkdir(parents=True, exist_ok=True)
            if hypotheses.print_own(sid, oid, str(out_dir(sid) / f"{oid}_v1")) != 0:
                return self._send(422, toy_page(sid, ["紙を刷れませんでした（検査に落ちた）"]))
            failures, msg = [], "刷りました。100% で印刷します"
        elif act == "print":
            failures = hypotheses.need_prediction(sid)
            hid = form.get("hypothesis", "")
            if not failures and hid not in {h["id"] for h in hypotheses.load(sid)["hypotheses"]}:
                return self._send(422, toy_page(sid, [f"仮説 {hid} は無い"]))
            if not failures:
                out_dir(sid).mkdir(parents=True, exist_ok=True)
                if hypotheses.print_sheet(sid, hid, str(out_dir(sid) / f"{hid}_v1")) != 0:
                    return self._send(422, toy_page(sid, ["型紙を刷れませんでした（検査に落ちた）"]))
            msg = "刷りました。100% で印刷します"
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
            return self._send(422, toy_page(sid, [f.message for f in failures]))
        self._done(sid, msg)


def serve(port=8766):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    try:
        port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
        server = serve(port)
    except (ValueError, OSError, OverflowError) as e:
        print(f"検査できない: 開けない: {e}", file=sys.stderr)
        sys.exit(4)
    print(f"http://127.0.0.1:{port}/")
    server.serve_forever()
