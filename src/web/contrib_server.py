"""持ち寄りの手元の画面。依存を増やさず標準の http.server で作る。

手元の 127.0.0.1 にだけ開く。外に開く形にしない理由は research/09: 認証・荒らし・保管の責任を週内に持てない。
だから待ち受けの場所を変える引数を置かない。公開の頁に出すのは contrib.public_list だけ。
"""
import html
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from omochae import contrib
from omochae.form_import import FORM_URL

MAX_REQUEST = 8 * 1024 * 1024
STYLE = """
body{font-family:"Noto Serif CJK JP",serif;background:#f5efe0;color:#2b2520;margin:0;padding:24px 16px;line-height:1.7}
main{max-width:640px;margin:auto}label{display:block;margin-top:14px;font-weight:bold}
input[type=text],textarea,select{width:100%;box-sizing:border-box;padding:8px;border:1px solid #8a7a62;background:#fffdf7;font:inherit}
textarea{min-height:120px}.check{font-weight:normal;display:flex;gap:8px;margin-top:8px}button{margin-top:18px;padding:10px 24px;font:inherit;background:#7a3b1d;color:#fff;border:0}
article{background:#fffdf7;border:1px solid #c9bda3;padding:14px;margin:14px 0}.meta{font-size:.85em;color:#5d5345}img{max-width:100%}#msg{margin-top:14px;font-weight:bold}
a{color:#7a3b1d}
"""
FORM = """<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>おもちゃの持ち寄り</title><style>%s</style><main>
<h1>おもちゃの持ち寄り</h1>
<p>職人、玩具店、実際に遊んだ人の話を集めています。江戸の玩具について、手元の写真、知っている事、思い出、作り方を寄せてください。確認した物だけを<a href="/public">公開の頁</a>に載せます。</p>
<form id="f">
<label>何を寄せますか<select name="kind"><option value="memory">思い出</option><option value="info">情報</option><option value="knowhow">作り方の知見</option><option value="photo">写真</option></select></label>
<label>あなたの立場<select name="role"><option value="memory">思い出を持つ人</option><option value="craftsperson">職人</option><option value="shop">玩具店・お店</option><option value="played">遊んだ人</option><option value="scholar">調べている人</option><option value="other">その他</option></select></label>
<label>どの玩具ですか<input type="text" name="toy_name" maxlength="100"></label>
<label>内容（公開されます）<textarea name="body" maxlength="2000" required></textarea></label>
<label>それは、どうして知っていますか<select name="certainty"><option>見た</option><option>持っている</option><option>聞いた</option><option>覚えている</option><option>作っている</option><option>売っている</option><option>遊んだ</option><option>推測</option></select></label>
<label>いつ頃・どのあたりの話ですか（おおよそで。公開されます）<input type="text" name="where_when" maxlength="100"></label>
<label>出所（本や人の話など。公開されます）<input type="text" name="origin" maxlength="200"></label>
<label>写真（JPEG か PNG、5MB まで。人が写っていない物）<input type="file" name="image" accept="image/jpeg,image/png"></label>
<label>写真や文の権利<select name="basis"><option value="own_work">自分で撮った・書いた</option><option value="permission">持ち主の許可がある</option><option value="public_domain">権利が切れている</option><option value="unknown">分からない（公開しません）</option></select></label>
<label>権利の持ち主の名前（写真の時は必須。公開されます）<input type="text" name="holder" maxlength="100"></label>
<label>公開の条件<select name="license"><option value="display_only">この場所での表示だけ（AI には渡しません）</option><option value="CC-BY-4.0">CC BY 4.0（出典を示せば誰でも使える。仮説づくりの参考として AI の Claude にも渡します）</option></select></label>
<label>公開する名前（空なら匿名）<input type="text" name="display_name" maxlength="50"></label>
<label>連絡先（任意。公開しません。確認や取り下げの連絡に使います）<input type="text" name="contact" maxlength="200"></label>
<label class="check"><input type="checkbox" name="agrees_terms"> 確認の後に公開される事、取り下げを申し出られる事に同意します</label>
<label class="check"><input type="checkbox" name="adult_or_guardian"> 18 歳以上か、保護者の同意があります</label>
<label class="check"><input type="checkbox" name="no_identifiable_people"> 写真に人が写っておらず、文に他の人の連絡先や私的な事を書いていません</label>
<button>寄せる</button><div id="msg" role="status"></div></form></main>
<script>
const f=document.getElementById('f'),m=document.getElementById('msg');
f.addEventListener('submit',async e=>{e.preventDefault();const d=new FormData(f);const v=k=>d.get(k);
const b={kind:v('kind'),role:v('role'),toy_name:v('toy_name'),body:v('body'),certainty:v('certainty'),where_when:v('where_when'),origin:v('origin'),display_name:v('display_name'),contact:v('contact'),
rights:{basis:v('basis'),holder:v('holder'),license:v('license')},attest:{agrees_terms:!!v('agrees_terms'),adult_or_guardian:!!v('adult_or_guardian'),no_identifiable_people:!!v('no_identifiable_people')}};
const file=f.image.files[0];if(file){b.image=await new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(r.result.split(',')[1]);r.onerror=no;r.readAsDataURL(file)})}
b.pii_confirmed=window.piiAsked===JSON.stringify([b.body,b.origin,b.where_when,b.toy_name,b.display_name,b.rights.holder]);
const r=await fetch('/api/contribute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});const j=await r.json();
if(!r.ok&&j.pii_only){window.piiAsked=JSON.stringify([b.body,b.origin,b.where_when,b.toy_name,b.display_name,b.rights.holder]);m.textContent='連絡先に見える所があります（'+j.errors.join(' / ')+'）。連絡先なら消してください。連絡先でなければ、もう一度「寄せる」を押すと、そのまま受け付けて確認の人に伝えます。';return}
m.textContent=r.ok?('受け付けました（'+j.id+'）。確認の後に公開します。'):('送れませんでした: '+j.errors.join(' / '));if(r.ok){f.reset();window.piiAsked=null}});
</script></html>""" % STYLE


LICENSE_LABEL = {"display_only": "この場所での表示だけ", "CC-BY-4.0": "CC BY 4.0"}


def public_page():
    rows = []
    for c in contrib.public_list():
        e = html.escape
        img = "".join(f'<img src="/media/{e(n)}" alt="投稿の写真">' for n in c.get("media", []))
        rights = c.get("rights", {})
        rows.append(
            f'<article id="{e(c["id"])}"><h2>{e(c.get("toy_name") or "玩具の名は未記入")}</h2>{img}<p>{e(c["body"])}</p>'
            f'<p class="meta">{e(c["id"])}・{e(contrib.KIND_LABEL[c["kind"]])}・{e(contrib.ROLE_LABEL[c["role"]])}・確かさ: {e(c["certainty"])}'
            f'・{e(c.get("where_when") or "時と所は未記入")}<br>出所: {e(c.get("origin") or "未記入")}・寄せた人: {e(c.get("display_name") or "匿名")}'
            f'<br>権利: {e(rights.get("holder") or "未記入")}・条件: {e(LICENSE_LABEL.get(rights.get("license"), "未記入"))}</p></article>'
        )
    body = "".join(rows) or "<p>確認済みの投稿はまだありません。</p>"
    return f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>持ち寄られた事</title><style>{STYLE}</style><main><h1>持ち寄られた事</h1><p>寄せられた言葉をそのまま載せています。事実と確かめた物ではありません。<a href="{html.escape(FORM_URL)}" rel="noopener" target="_blank">持ち寄りの入口（フォーム）で寄せる</a>（手元の受付は <a href="/">こちら</a>）</p>{body}</main></html>'


class Handler(BaseHTTPRequestHandler):
    # 本文を送らない接続を待ち続けないため。
    timeout = 20

    def log_message(self, *a):  # 投稿の中身や連絡先を記録に残さない
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def _host_ok(self):
        # DNS rebinding で外のサイトから手元の受付を読み書きさせないため、手元の名前だけを受ける。
        port = self.server.server_address[1]
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def do_GET(self):
        try:
            self._get()
        except Exception as e:  # 中身を応答に出さず、1 回の失敗で接続を黙って切らない
            print(f"GET の失敗: {type(e).__name__}", file=sys.stderr)
            self._send(500, "うまく表示できませんでした")

    def do_POST(self):
        try:
            self._post()
        except Exception as e:
            print(f"POST の失敗: {type(e).__name__}", file=sys.stderr)
            self._json(500, {"errors": ["受け付けられませんでした"]})

    def _get(self):
        if not self._host_ok():
            return self._send(403, "受け付けられません")
        path = self.path.split("?")[0]
        if path == "/":
            return self._send(200, FORM)
        if path == "/public":
            return self._send(200, public_page())
        m = re.fullmatch(r"/media/(C-\d+\.(?:jpg|png))", path)
        if m:
            # 確認済みの投稿が持つ写真の名前だけを出す。受付中の写真を URL の推測で見られないように。
            names = {n for c in contrib.public_list() for n in c.get("media", [])}
            if m.group(1) in names:
                ctype = "image/png" if m.group(1).endswith(".png") else "image/jpeg"
                media = contrib.dirs()["media"] / m.group(1)
                if media.exists():
                    return self._send(200, media.read_bytes(), ctype)
        self._send(404, "見つかりません")

    def _post(self):
        if not self._host_ok():
            return self._json(403, {"errors": ["受け付けられない送り方です"]})
        if self.path != "/api/contribute":
            return self._send(404, "見つかりません")
        # 別のサイトの頁から手元の受付へ送らせないため、JSON と同じ出所だけを受ける。
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json" or origin != f"http://{host}":
            return self._json(403, {"errors": ["受け付けられない送り方です"]})
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self._json(411, {"errors": ["長さが分かりません"]})
        if length < 0 or length > MAX_REQUEST:
            return self._json(413, {"errors": ["大きすぎます"]})
        try:
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError
            image = data.pop("image", None)
            if image is not None and not isinstance(image, str):
                raise ValueError
        except (ValueError, RecursionError):
            return self._json(400, {"errors": ["読めない送り方です"]})
        cid, failures = contrib.submit(data, image)
        if failures:
            only_pii = all(f.floor == "F10.pii" for f in failures)
            return self._json(422, {"errors": [f"{f.where}: {f.message}" for f in failures], "pii_only": only_pii})
        self._json(200, {"id": cid})


def serve(port=8765):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    try:
        port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    except ValueError:
        print("検査できない: ポートは数字で指定する", file=sys.stderr)
        sys.exit(4)
    try:
        server = serve(port)
    except (OSError, OverflowError) as e:
        print(f"検査できない: ポート {port} で開けない: {e}", file=sys.stderr)
        sys.exit(4)
    print(f"http://127.0.0.1:{port}/")
    server.serve_forever()
