"""作った人の報告の入口（Issue #22）。手元の画面で受け付け、受付箱に置き、人が確かめて受け入れた物だけを集計に回す。

制作者の決定（2026-11-05）: 報告の入口もエンジン（paper-to-toy）の側に作る。
提出物の持ち寄りの受付（受付箱 → 人の確認 → 公開）と同じ流れにした。判断の芯:
- 画面は手元の機械（127.0.0.1）でだけ開く。外へ開く入口（認証・荒らし・保管の運用が要る）は、この Issue では作らない。
- 送られた報告は omochae.feedback の check を通し、通った物だけを受付箱に置く。落ちた物は置かず、床の名と理由だけを見せる。
  値を見せ返さないのは、個人の情報の形を含む中身を画面にも記録にも残さないため。IP や端末の情報も残さない。
- 受付箱も受け入れた物も local/ の下（git の外）に置く。作った人の文を repo に入れない。
- 受け入れは、端末に全文を出してから、人が ID を打たないと進まない（AI や自動の処理だけで受け入れない補助。完全な保証ではない）。
- 却下は中身を消し、ID と確認の記録だけを残す。ID は使い回さない。
- 写真は受け付けない（権利と人の写り込みの確認が要るため）。
終了: 0 = できた / 3 = 落ちた・断った / 4 = できない。
"""
import datetime
import html
import json
import os
import pathlib
import re
import secrets
import unicodedata
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from .__main__ import Parser
from .compose import TEMPLATES
from .feedback import FINISH, KINDS, MOVED, check

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = ROOT / "local" / "reports"
MAX_PROBLEMS = 3
MAX_BODY = 20_000  # 送られる文の上限（バイト）。長すぎる物は読まずに断る
# 返す全部の頁に付ける守りの見出し。画面は手元の機械だけで開くが、ほかのサイトの枠に入れて押させる形（clickjacking）を止める
SECURITY_HEADERS = {"X-Frame-Options": "DENY", "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                    "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}


def visible(text):
    """端末に出す前に、見えない文字と制御の文字を \\uXXXX の形にして見えるようにする。人が全文を読む事が最後の止めなので、
    字の並びをごまかせる文字（Unicode の Cf。文の向きを変える U+202E など）と、端末を動かせる制御の文字（Cc。C1 の U+009B CSI など。
    JSON は U+0020 より下しか escape しないので、C1 と DEL は報告の JSON に生で残る）と、行と段落の区切り（U+2028・U+2029）を
    そのまま出さない。改行とタブは読むのに要るので残す（セキュリティの点検 2026-11-07・見直しの指摘）。"""
    return "".join(f"\\u{ord(ch):04x}" if (unicodedata.category(ch) in ("Cf", "Cc", "Zl", "Zp") and ch not in "\n\t") else ch for ch in text)


ID_FORM = re.compile(r"B-\d{8}-\d{6}-[0-9a-f]{8}")  # 受付の ID の形。形でない物は扱わない（../ で受付箱の外を消せた）
CONSENTS = {"no_pii": "名前・連絡先・ほかの人の事を書いていない", "age": "18 歳以上か、保護者の同意がある"}
MOVED_JA = {"moved": "動いた", "partly": "少し動いた", "not": "動かない"}
TZ = datetime.timezone(datetime.timedelta(hours=9))


def dirs(base=BASE):
    d = {k: pathlib.Path(base) / k for k in ("inbox", "accepted", "log")}
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return d


def new_id(now=None):
    now = now or datetime.datetime.now(TZ)
    return f"B-{now:%Y%m%d-%H%M%S}-{secrets.token_hex(4)}"


def report_from_fields(f):
    """画面の欄（parse_qs の形）から報告の dict を作る。空の困り事の行は入れない。同意の欄は報告に入れない。"""
    one = lambda k: (f.get(k) or [""])[0].strip()
    # yes・no の欄は、決まりの 2 つの値だけを真偽にする。ほかの値（欠けた・細工した）は文のまま残し、check で落とす。
    # 「yes でなければ false」にすると、壊れた送信が「組み上がらなかった」という正しい報告として集計に入った
    yes_no = lambda v: {"yes": True, "no": False}.get(v, v)
    r = {"template": one("template"), "form": one("form"), "built": yes_no(one("built")), "moved": one("moved"),
         "motion_notes": one("motion_notes"), "finish_notes": one("finish_notes"),
         "reported_at": datetime.datetime.now(TZ).isoformat(timespec="seconds")}
    try:
        r["finish"] = int(one("finish"))
    except ValueError:
        r["finish"] = None
    # 作る様子（#23）。空なら欄を入れない（書かなかったのと、0 と書いたのを分ける）
    for key in ("stuck_step", "minutes"):
        v = one(key)
        if v:
            # 半角の数字だけを数にする。isdigit は ² や ① も真で、int() が落ちた
            r[key] = int(v) if re.fullmatch(r"[0-9]{1,4}", v) else v
    if one("gave_up"):
        r["gave_up"] = yes_no(one("gave_up"))
    probs = []
    for i in range(MAX_PROBLEMS):
        kind, note, step = one(f"p{i}_kind"), one(f"p{i}_note"), one(f"p{i}_step")
        if not kind:
            continue
        pr = {"kind": kind, "note": note, "step": None}
        if step:
            pr["step"] = int(step) if re.fullmatch(r"[0-9]{1,4}", step) else step
        probs.append(pr)
    r["problems"] = probs
    return r


def submit(fields, base=BASE):
    """送られた欄を受け付ける。Returns (受付の ID か None, 知らせの list)。通らなければ何も置かない。"""
    missing = [txt for k, txt in CONSENTS.items() if (fields.get(k) or [""])[0] != "yes"]
    if missing:
        return None, [f"同意が要る: {m}" for m in missing]
    r = report_from_fields(fields)
    fails = check(r)
    if fails:
        return None, [f.line() for f in fails]
    rid = new_id()
    d = dirs(base)
    # 排他的に作る。接続ごとの糸で同じ秒に 2 件来ても、先の報告を黙って上書きしない
    with open(d["inbox"] / f"{rid}.json", "x", encoding="utf-8") as fh:
        fh.write(json.dumps(r, ensure_ascii=False, indent=1))
    return rid, []


def _log(base, line):
    with open(dirs(base)["log"] / "review.log", "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.datetime.now(TZ).isoformat(timespec='seconds')}\t{line}\n")


def accept(rid, base=BASE, confirm=None, shown=None):
    """受付箱の報告を受け入れる。confirm は人が打った ID。合わなければ断る。受け入れる前にもう一度 check を通す。
    shown は人に見せた全文。渡された時は、今のファイルがそれと同じ時だけ受け入れる
    （見せてから ID を打つ間に書き換えられると、人が読んでいない報告を受け入れられた）。"""
    if not isinstance(rid, str) or not ID_FORM.fullmatch(rid):
        return False, "受付の ID の形でない"
    d = dirs(base)
    src = d["inbox"] / f"{rid}.json"
    if not src.exists():
        return False, "受付箱に無い"
    if confirm != rid:
        return False, "確かめの ID が合わない（人が端末で打つ）"
    text = src.read_text(encoding="utf-8")
    if shown is not None and text != shown:
        return False, "見せた後に報告が変わった（受け入れない。もう一度 review accept で読み直す）"
    r = json.loads(text)
    if check(r):
        return False, "報告が検査に通らない（受け入れない。review reject で却下する）"
    r["reviewed_at"] = datetime.datetime.now(TZ).isoformat(timespec="seconds")
    (d["accepted"] / src.name).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    src.unlink()
    _log(base, f"accept\t{rid}")
    return True, "受け入れた"


def reject(rid, base=BASE, reason=""):
    """却下する。中身を消し、ID と確認の記録だけを残す。理由は決まった語だけ（文を残さない）。"""
    if not isinstance(rid, str) or not ID_FORM.fullmatch(rid):
        return False, "受付の ID の形でない"
    src = dirs(base)["inbox"] / f"{rid}.json"
    if not src.exists():
        return False, "受付箱に無い"
    src.unlink()
    _log(base, f"reject\t{rid}\t{reason if reason in ('pii', 'spam', 'off_topic', 'other') else 'other'}")
    return True, "却下した（中身は消した）"


def _options(values, labels=None):
    return "".join(f'<option value="{html.escape(str(v))}">{html.escape(str((labels or {}).get(v, v)))}</option>' for v in values)


def form_page(messages=(), done_id=None):
    forms = {tid: list(map(str, t.FORMS)) for tid, t in TEMPLATES.items()}
    msg = ""
    if done_id:
        msg = f'<p class="ok">受け付けました（{html.escape(done_id)}）。人が確かめてから、型紙の直しの材料にします。</p>'
    if messages:
        msg = '<ul class="ng">' + "".join(f"<li>{html.escape(m)}</li>" for m in messages) + "</ul>"
    rows = "".join(f"""<fieldset><legend>困り事 {i + 1}（無ければ空のまま）</legend>
<label>種類 <select name="p{i}_kind"><option value="">—</option>{_options(KINDS)}</select></label>
<label>手順の番号 <input name="p{i}_step" size="3" inputmode="numeric"></label>
<label>どうだったか <input name="p{i}_note" size="40" maxlength="300"></label></fieldset>""" for i in range(MAX_PROBLEMS))
    consents = "".join(f'<label><input type="checkbox" name="{k}" value="yes"> {html.escape(t)}</label><br>' for k, t in CONSENTS.items())
    return f"""<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>型紙の報告</title><style>body{{font-family:sans-serif;max-width:40rem;margin:1rem auto;padding:0 1rem}}
fieldset{{margin:.6rem 0}}.ok{{color:#185}}.ng{{color:#a22}}label{{display:inline-block;margin:.2rem .6rem .2rem 0}}</style>
<h1>型紙で作った物の報告</h1>
<p>組み上がりの感想と、動いた様子、どこで止まったかを教えてください。型紙と、案内・サイトを直す材料にします。名前・連絡先・ほかの人の事は書かないでください。写真は受け付けていません。</p>
{msg}<form method="post" action="/report">
<label>雛形 <select name="template" id="t">{_options(forms)}</select></label>
<label>形 <select name="form" id="f"></select></label><br>
<label>組み上がった <select name="built"><option value="yes">はい</option><option value="no">いいえ</option></select></label>
<label>動いた <select name="moved">{_options(MOVED, MOVED_JA)}</select></label>
<label>仕上がり（1 悪い〜5 良い） <select name="finish">{_options(FINISH)}</select></label><br>
<label>止まった手順の番号（止まらなければ空） <input name="stuck_step" size="3" inputmode="numeric"></label>
<label>途中でやめた <select name="gave_up"><option value="">—</option><option value="no">いいえ</option><option value="yes">はい</option></select></label>
<label>かかった時間（分・およそ） <input name="minutes" size="4" inputmode="numeric"></label><br>
<label>動きの感想<br><textarea name="motion_notes" rows="3" cols="50" maxlength="600"></textarea></label><br>
<label>仕上がり・見た目の感想<br><textarea name="finish_notes" rows="3" cols="50" maxlength="600"></textarea></label>
{rows}{consents}<input type="hidden" name="token" value="{html.escape(Handler.token)}"><button>送る</button></form>
<script>const F={json.dumps(forms, ensure_ascii=False)};const t=document.getElementById('t'),f=document.getElementById('f');
function fill(){{f.innerHTML='';for(const v of F[t.value]){{const o=document.createElement('option');o.value=o.textContent=v;f.appendChild(o)}}}}
t.onchange=fill;fill();</script></html>"""


class Handler(BaseHTTPRequestHandler):
    base = BASE
    # 画面に埋めて、送る時に返させる合言葉。ほかのサイトが手元のブラウザーから送り込むのを止める（Host と Origin も見る）
    token = secrets.token_urlsafe(16)
    port = 0
    timeout = 10  # 1 つの接続の読み込みの待ち（秒）

    def _same_site(self):
        host = self.headers.get("Host", "")
        ok_hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        origin = self.headers.get("Origin")
        return host in ok_hosts and (origin is None or origin in {f"http://{h}" for h in ok_hosts})

    def _send(self, code, body):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        # ほかのページの枠に入れさせない・形を読み替えさせない・送り元の URL を出さない（セキュリティの点検 2026-11-07）
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, form_page()) if self.path in ("/", "/report") else self._send(404, "無い")

    def do_POST(self):
        if self.path != "/report":
            return self._send(404, "無い")
        if not self._same_site():
            return self._send(403, "断った（手元の画面からだけ受け付ける）")
        cl = self.headers.get("Content-Length", "")
        if not re.fullmatch(r"[0-9]{1,6}", cl):
            return self._send(400, "断った（長さが読めない）")
        n = int(cl)
        if n > MAX_BODY:
            return self._send(413, form_page(["長すぎる"]))
        try:
            fields = parse_qs(self.rfile.read(n).decode("utf-8", "replace"))
            if (fields.get("token") or [""])[0] != self.token:
                return self._send(403, "断った（画面を開き直して送る）")
            rid, msgs = submit(fields, self.base)
        except Exception:  # 想定外でも、送られた値や送った人の IP を記録に出さない（handle_error の traceback を出さない）
            return self._send(400, form_page(["受け付けられなかった（画面を開き直して送る）"]))
        self._send(200 if rid else 400, form_page(msgs, rid))

    def log_message(self, *a):
        pass  # 送った人の IP や時刻の記録を残さない


class QuietServer(ThreadingHTTPServer):
    # 接続ごとに糸を分け、読み込みの待ちに上限を置く。1 本の糸だと、何も送らない接続 1 本で入口が止まった
    daemon_threads = True
    def handle_error(self, request, client_address):
        pass  # 既定は送った人の IP と traceback（送られた値を含みうる）を stderr に出すので、出さない


def make_server(port):
    """127.0.0.1 だけで開く。port 0 なら空いている番号。Handler.port を実際の番号にする（Host を確かめるため）。"""
    srv = QuietServer(("127.0.0.1", port), Handler)
    Handler.port = srv.server_address[1]
    return srv


def main(argv=None):
    ap = Parser(prog="omochae.intake", description="作った人の報告の入口。終了: 0 できた / 3 落ちた・断った / 4 できない")
    ap.add_argument("--base", default=str(BASE), help="置き場（既定 local/reports。git の外）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sv = sub.add_parser("serve", help="手元の機械（127.0.0.1）で報告の画面を開く")
    sv.add_argument("--port", type=int, default=8765)
    rv = sub.add_parser("review", help="受付箱を見て、受け入れるか却下する")
    rv.add_argument("action", choices=("list", "show", "accept", "reject"))
    rv.add_argument("id", nargs="?")
    rv.add_argument("--reason", default="other", help="却下の理由（pii・spam・off_topic・other）")
    args = ap.parse_args(argv)
    base = pathlib.Path(args.base)
    if args.cmd == "serve":
        Handler.base = base
        dirs(base)
        srv = make_server(args.port)
        print(f"http://127.0.0.1:{Handler.port}/ で開いた（手元の機械だけ）。止めるのは Ctrl-C", file=sys.stderr)
        srv.serve_forever()
        return 0
    d = dirs(base)
    if args.action == "list":
        for p in sorted(d["inbox"].glob("*.json")):
            print(p.stem)
        return 0
    if not args.id:
        print("ID が要る", file=sys.stderr)
        return 4
    if not ID_FORM.fullmatch(args.id):
        print("受付の ID の形でない", file=sys.stderr)
        return 3
    if args.action == "show":
        p = d["inbox"] / f"{args.id}.json"
        if not p.exists():
            print("受付箱に無い", file=sys.stderr)
            return 3
        print(visible(p.read_text(encoding="utf-8")))
        return 0
    if args.action == "reject":
        ok, msg = reject(args.id, base, args.reason)
    else:
        if not sys.stdin.isatty():
            print("断った: 受け入れは端末で人が ID を打つ（入力が端末でない）", file=sys.stderr)
            return 3
        # 受け入れの前に、全文を必ず端末に出す。式は名前・住所を見分けられないので、人が全文を読む事が最後の止め。
        # show を別に打つ形だと、読まずに ID だけ打って受け入れられた
        p = d["inbox"] / f"{args.id}.json"
        if not p.exists():
            print("受付箱に無い", file=sys.stderr)
            return 3
        shown = p.read_text(encoding="utf-8")
        print(visible(shown))
        print("上の全文に、名前・住所・連絡先・ほかの人の事が無いかを読んでから、ID を打つ（あれば review reject --reason pii）")
        typed = input(f"受け入れる報告の ID を打つ（{args.id}）: ").strip()
        ok, msg = accept(args.id, base, typed, shown=shown)
    print(msg, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
