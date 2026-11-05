"""記録を残したら、その場限りの印（who）を作り直す（Issue #279 の続き。11-07 の場は機械を共用するかもしれない）。

なぜ: 印はタブごとに持つので、同じタブを次の人が使うと、前の人と同じ印のままになる。話した字は印で読むので（talk_log.bind・talk_log.texts の who）、
次の人の紙や記録に、前の人の字が混ざりうる。止まった手順の人の数も、1 回の作りごとに数えられない（Issue #275 の「who は 1 回の作りの印」）。

見る線:
- 玩具の頁の記録の欄: 残せた時だけ、戻る先に印を作り直す合図（fresh）が付く。通らなかった時は付かない（話した字が、記録に結ばれなくなるため）。
- 手帖: 記録の番号が返った後に、印を作り直す。通らなかった時は作り直さない。
- 作り直した後に話した字は、前の記録に入らず、次の記録に入る。その画面の字を読む口にも、前の印の字が混ざらない。
- 頁の script の動きは、入っている Chrome で測る（./run.sh はブラウザなしで動く決まりなので、Chrome が無い機械と時間切れは、測れないと出して通す）。

限り: 記録を残さずに席を替わった時と、記録の後に前の人が続けて話した字は、同じタブの中では見分けられない。場の進め方で避ける（次の人の前にタブを開き直す）。
"""
import json
import os
import re
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from measure_tap import chrome  # noqa: E402
from omochae import talk_log  # noqa: E402
from web import play_server, skin  # noqa: E402

G = "NDL-1187053-R0000005-L"
A, B = "abcdefghij", "klmnopqrst"  # 前の人の印と、作り直した後の印


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)
get_page, send_page = play_server.Handler.do_GET, play_server.Handler._send
# Chrome で測る時の親の頁。同じ出所の iframe は sessionStorage を親と分け合うので、タブの中を順に移る形を測れる
WRAP = """<!doctype html><body><pre id="measured"></pre><iframe id="f" width="390" height="844"></iframe><script>
sessionStorage.setItem('utsushi-who','aaaaaaaaaa');
const f=document.getElementById('f'),out=[];
const read=()=>{const d=f.contentWindow;out.push({who:sessionStorage.getItem('utsushi-who'),search:d.location.search,hash:d.location.hash,field:(d.document.querySelector('input[name=who]')||{}).value})};
const go=(src,next)=>{f.onload=()=>setTimeout(()=>{read();next()},300);f.src=src};
const toy='/toy/%s';
go(toy,()=>go(toy+'?msg=x&at=R-0001&fresh=1#R-0001',()=>go(toy,()=>{f.contentWindow.utsushiNewWho();read();
 document.getElementById('measured').textContent=JSON.stringify(out)})));
</script>""" % G


def do_get(self):
    if self.path == "/__wrap":
        return send_page(self, 200, WRAP)
    return get_page(self)


play_server.Handler.do_GET = do_get
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def post(path, data):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    try:
        r = opener.open(req)
        return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)


def talk(text, who):
    code, body, _ = post(f"/toy/{G}/talk", {"json": "1", "scene": "craft", "hypothesis": "H-A", "sheet_version": "1", "step": "1", "text": text, "who": who})
    assert code == 200 and json.loads(body)["kept"] is True, body


assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303

# ---- 玩具の頁の記録の欄: 残せた時だけ、戻る先に合図が付く。通らなかった時と、ほかの送り先には付かない
talk("前の人の工夫", A)
code, _, head = post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた", "who": A})
assert code == 303 and re.search(r"[?&]fresh=1(&|#)", head["Location"]), head
assert [k["text"] for k in talk_log.kufu(G, "R-0001")] == ["前の人の工夫"], "印は、結んだ後に作り直す"
code, _, head = post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "成功", "who": A})
assert code == 422 and "Location" not in head
code, _, head = post(f"/toy/{G}/print", {"hypothesis": "H-A"})
assert code == 303 and "fresh" not in head["Location"], head

# ---- 作り直した後: 次の人の字は次の記録に入り、前の記録と前の印の字に混ざらない
talk("次の人の工夫", B)
assert {t["text"] for t in talk_log.texts(G, who=B)} == {"次の人の工夫"} and {t["text"] for t in talk_log.texts(G, who=A)} == {"前の人の工夫"}
code, body, _ = post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "who": B})
assert code == 201 and json.loads(body)["id"] == "R-0002", body
assert [k["text"] for k in talk_log.kufu(G, "R-0002")] == ["次の人の工夫"] and [k["text"] for k in talk_log.kufu(G, "R-0001")] == ["前の人の工夫"]

# ---- 頁の script（字で見る）: 印の形は今のまま。作り直す口は 1 つ。手帖は、記録の番号が返った後にだけ呼ぶ
assert "/^[a-z0-9]{10}$/" in skin.WHO_SCRIPT and "utsushiNewWho" in skin.WHO_SCRIPT and "searchParams.has('fresh')" in skin.WHO_SCRIPT
techo = urllib.request.urlopen(f"{base}/toy/{G}/techo").read().decode()
up = techo[techo.index("const save"):]  # 手帖の残す所（1 手 1 画面の頁、#87）
assert up.index("if (!j.id)") < up.index("utsushiNewWho()") < up.index("form.reset()"), "記録が残らなかった時は、印を作り直さない"

# ---- 頁の script（Chrome で測る）
exe = chrome()
if not exe:
    print("ok（字で見た。Chrome が無いので、動きは測れない）")
    server.shutdown()
    raise SystemExit(0)
try:
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=800,900",
                              "--virtual-time-budget=8000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=120).stdout
except subprocess.TimeoutExpired:
    out = ""
server.shutdown()
found = re.search(r'<pre id="measured">(\[.*?\])</pre>', out, re.S)
if not found:
    print("ok（字で見た。Chrome が時間内に答えなかったので、動きは測れない）")
    raise SystemExit(0)
first, fresh, again, called = json.loads(found.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
# 合図の無い頁: 印はそのまま、フォームにも同じ印が入る
assert first["who"] == "aaaaaaaaaa" and first["field"] == "aaaaaaaaaa", first
# 合図のある頁: 印が新しくなり、フォームにも新しい印が入る。合図は住所から消す（読み直しで、また作り直さないように）。錨と返事の欄は残す
assert re.fullmatch(r"[a-z0-9]{10}", fresh["who"]) and fresh["who"] != "aaaaaaaaaa" and fresh["field"] == fresh["who"], fresh
assert "fresh" not in fresh["search"] and "at=R-0001" in fresh["search"] and fresh["hash"] == "#R-0001", fresh
# 次の頁でも同じ印が続く
assert again["who"] == fresh["who"] and again["field"] == fresh["who"], again
# 手帖が呼ぶ口: 印が新しくなり、開いている頁のフォームの印もそろう
assert called["who"] != fresh["who"] and re.fullmatch(r"[a-z0-9]{10}", called["who"]) and called["field"] == called["who"], called
print("ok（字で見て、Chrome でも動きを測った）")
