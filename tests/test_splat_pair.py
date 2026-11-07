"""作った実物の立体とエンジンの 3D を並べて一緒に回す部品（本人の決定 11-07・窓口の決め 125156）の試験。絵は試験の中で作る。

見る事:
1. 絵の一覧（frames.json）が無い・人が確かめた印が無い・絵が足りない・置き場の外を指す時は、頁も絵も出さない（404）
2. 確かめた絵があれば、/toy/<印>/splat に 2 つの窓（エンジンの 3D の止まった形・作った実物）と札の字と回す口が 1 つずつ
3. エンジンの側は kumitate.still の見る向きの rotateY に、回す角（--sp-turn）が足されている（kumitate の作りが替わったら、ここで気づく）
4. 回す口の幅は一覧の角の端から端・最初は 0（前）。実物の絵の最初は角 0 の絵
5. 絵の道は一覧の数の中だけ 200 の JPEG。外は 404
6. 頁は外の部品（script の src・WebGL）を読まない
7. 合言葉なしの場でも同じ
8. 札にそれぞれの型紙の版: エンジンは今の組（v14）、実物は絵の一覧の版（v13。本人の言葉 11-07「最終版の一個前」）。一覧に版が無ければ実物の版は書かない。実物に v14 を書かない
9. 回す口を動かすと、実物の絵（角に近い絵）とエンジンの向き（--sp-turn）が一緒に替わる（Chrome で頁の JS を動かす）
"""
import json
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from PIL import Image  # noqa: E402

from web import kumitate, splat_pair as sp  # noqa: E402
from web.play_server import serve  # noqa: E402

SID = "NDL-1187053-R0000005-L"  # 御来迎（組み立ての 3D がある玩具）
assert kumitate.available(SID)
base = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "splat" / SID
ANGLES = [-20.0 + 5 * i for i in range(14)]


def get(srv, path):
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}{path}", timeout=120)
        return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, "", b""


def put(meta, n=len(ANGLES)):
    base.mkdir(parents=True, exist_ok=True)
    for f in base.glob("t*.jpg"):
        f.unlink()
    for i in range(n):
        Image.new("RGB", (480, 540), (240, 230 - i, 200)).save(base / f"t{i:02d}.jpg")
    (base / "frames.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


# ---- 1 出さない時
assert sp.section(SID) == "" and sp.page(SID) == "", "一覧が無い"
put({"angles": ANGLES})
assert sp.frames(SID) is None, "確かめた印が無い"
put({"angles": ANGLES, "checked_by": "確かめた人"}, n=10)
assert sp.frames(SID) is None, "絵が足りない"
put({"angles": ANGLES, "checked_by": "確かめた人"})
outside = pathlib.Path(tempfile.mkdtemp()) / "x.jpg"
Image.new("RGB", (10, 10)).save(outside)
(base / "t03.jpg").unlink(); (base / "t03.jpg").symlink_to(outside)
assert sp.frames(SID) is None, "置き場の外を指す印"
put({"angles": ANGLES, "checked_by": "確かめた人"})
assert sp.frames(SID)["files"][0] == "t00.jpg" and sp.frames(SID)["version"] == "", "一覧に版が無ければ、実物の版は書かない"
assert "型紙の版" not in re.search(r'<figure class="sp-made">.*?</figure>', sp.section(SID), re.S).group(0)
put({"angles": ANGLES, "checked_by": "確かめた人", "sheet_set": "goraigo-v13"})

for opened in (False, True):
    srv = serve(0, public_open=opened)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    code, _, body = get(srv, f"/toy/{SID}/splat")
    page = body.decode()
    assert code == 200, (code, opened)
    # ---- 2 2 つの窓と札と回す口
    assert page.count('class="sp-ai"') == 1 and page.count('class="sp-made"') == 1 and page.count('class="sp-turn"') == 1
    assert sp.AI in page and sp.MADE in page and f'aria-label="{sp.TURN}"' in page
    # ---- 3 エンジンの向きに回す角を足した
    scene = re.search(r'class="rt-scene" style="transform:([^"]*)"', page).group(1)
    assert re.search(r"rotateY\(calc\(-?[\d.]+deg \+ var\(--sp-turn,0deg\)\)\)", scene), scene
    # ---- 4 回す口と最初の絵
    assert f'min="{ANGLES[0]:g}" max="{ANGLES[-1]:g}"' in page and 'value="0"' in page
    assert f'src="/toy/{SID}/splat/{ANGLES.index(0.0)}.jpg"' in page, "最初は前（角 0）の絵"
    # ---- 8 札の版: エンジンは今の組、実物は絵の一覧の版（v13）。実物に今の組の版（v14）を書かない（本人の言葉 11-07）
    ai = re.search(r'<figure class="sp-ai">.*?<figcaption>(.*?)</figcaption>', page, re.S).group(1)
    made = re.search(r'<figure class="sp-made">.*?<figcaption>(.*?)</figcaption>', page, re.S).group(1)
    assert "型紙の版 v14" in ai and "型紙の版 v13" in made and "v14" not in made, (ai, made)
    # ---- 6 外の部品を読まない
    assert not re.search(r"<script[^>]+src=", page) and "webgl" not in page.lower()
    # ---- 5 絵の道
    code, ctype, data = get(srv, f"/toy/{SID}/splat/0.jpg")
    assert code == 200 and ctype == "image/jpeg" and data[:2] == b"\xff\xd8"
    for path in (f"/toy/{SID}/splat/14.jpg", f"/toy/{SID}/splat/99.jpg", f"/toy/{SID}/splat/-1.jpg", f"/toy/{SID}/splat/a.jpg",
                 "/toy/NDL-1187053-R0000099-L/splat", f"/toy/{SID}/splat/..%2F..%2Fx.jpg"):
        assert get(srv, path)[0] == 404, path
    srv.shutdown()

# ---- 9 回す口を動かすと、実物の絵とエンジンの向きが一緒に替わる（頁の JS を Chrome で動かして見る。Chrome が無い機械では測れないと書いて進む）
import subprocess  # noqa: E402
import sys  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from measure_tap import chrome  # noqa: E402
from web import play_server  # noqa: E402

WALK = ("<script>setTimeout(()=>{const r=document.querySelector('.sp-turn'),o={};for(const v of [-20,0,45]){r.value=v;r.dispatchEvent(new Event('input'));"
        "o[v]={img:document.querySelector('.sp-made img').getAttribute('src'),turn:document.querySelector('.sp-ai .rt-scene').style.getPropertyValue('--sp-turn')}}"
        "const p=document.createElement('pre');p.id='measured';p.textContent=JSON.stringify(o);document.body.appendChild(p)},300)</script>")
exe = chrome()
if exe:
    send = play_server.Handler._send

    def walked(self, code, body, ctype="text/html; charset=utf-8", headers=()):
        if isinstance(body, str) and "/splat" in self.path and 'class="sp"' in body:
            body = body.replace("</body>", WALK + "</body>", 1)
        return send(self, code, body, ctype, headers)

    play_server.Handler._send = walked
    srv = serve(0, public_open=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=600,900",
                                  "--virtual-time-budget=10000", "--dump-dom", f"http://127.0.0.1:{srv.server_address[1]}/toy/{SID}/splat"],
                                 capture_output=True, text=True, timeout=170).stdout
    finally:
        play_server.Handler._send = send
        srv.shutdown()
    got = json.loads(re.search(r'<pre id="measured">(.*?)</pre>', out, re.S).group(1).replace("&quot;", '"'))
    assert got["-20"] == {"img": f"/toy/{SID}/splat/0.jpg", "turn": "20deg"}, got
    assert got["0"] == {"img": f"/toy/{SID}/splat/{ANGLES.index(0.0)}.jpg", "turn": "0deg"}, got
    assert got["45"] == {"img": f"/toy/{SID}/splat/{len(ANGLES) - 1}.jpg", "turn": "-45deg"}, got
else:
    print("測れない: Chrome が無いので、回す口の JS は動かしていない")

# ---- 1 の続き: 確かめた印を外すと頁も絵も 404
put({"angles": ANGLES})
srv = serve(0, public_open=True)
threading.Thread(target=srv.serve_forever, daemon=True).start()
assert get(srv, f"/toy/{SID}/splat")[0] == 404 and get(srv, f"/toy/{SID}/splat/0.jpg")[0] == 404
srv.shutdown()

print("ok 実物の立体とエンジンの 3D: 確かめた絵がある時だけ、2 つの窓と回す口 1 つで、同じ角だけ回る。絵の道は一覧の中だけ")
