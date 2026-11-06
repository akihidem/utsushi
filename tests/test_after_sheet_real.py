"""本物の記録（data/records）の札から、その記録の案と版の試した後の紙が窓に出る（#320）。

なぜ: 必須 2 種はたたき台だけを刷るので（#332）、前の試行の R-0002（H-C）の紙の組は作れない。窓が札の案を出せないと、黙ってたたき台の紙が出て、
札の PDF は 404 になった。作り物の記録の試験では見えなかったので、本物の記録で札から窓までをたどる。
本物の置き場には書かない（記録と説明を試験の置き場へコピーする）。
"""
import json
import os
import pathlib
import re
import shutil
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_DATA"] = str(DATA)
os.environ["OMOCHAE_USAGE_LEDGER"] = str(DATA / "api-usage.jsonl")
(DATA / "records").mkdir()
(DATA / "loop").mkdir()
real = sorted((ROOT / "data/records").glob("R-*.json"))
assert real, "本物の記録が無い"
for p in real:
    shutil.copy(p, DATA / "records")
for p in (ROOT / "data/loop").glob("explanation-R-*.json"):
    shutil.copy(p, DATA / "loop")

from omochae import hypotheses, loop  # noqa: E402
from web.play_server import printed_versions, serve  # noqa: E402

server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    try:
        with urllib.request.urlopen(base + path, timeout=180) as x:
            return x.status, x.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def window(page):
    return page[page.index('id="win"'):page.index('id="tsukuru"')]


seen = set()
for p in real:
    rec = json.loads(p.read_text(encoding="utf-8"))
    sid, hid, ver = rec["source_id"], rec["hypothesis_id"], rec.get("sheet_version", 1)
    seen.add(hid)
    h = next(x for x in hypotheses.load(sid)["hypotheses"] if x["id"] == hid)
    code, body = get(f"/toy/{sid}")
    assert code == 200, code
    # 札のリンクは頁から読む
    link = re.search(rf'<a href="(/toy/{sid}\?see={hid}&kind=after&v={ver})#win">試した後の紙</a>', body.decode())
    assert link, ("札に字のリンクが無い", rec["id"])
    code, body = get(link.group(1))
    shown = window(body.decode())
    # 窓の紙の番号が、記録の案と版と同じ。ほかの案の紙が黙って出ない
    assert code == 200 and f"/sheet/{sid}/{hid}_v{ver}_after.png" in shown, ("窓の紙の番号が記録と違う", rec["id"])
    assert set(re.findall(r"/sheet/[^/]+/(H-[A-Z0-9]+)_v", shown)) == {hid}, ("ほかの案の紙が出ている", rec["id"], shown[:200])
    assert f"仮説 {hypotheses.letter(h)}「{h['name']}」の試した後の紙" in shown, ("見出しが記録の案でない", rec["id"])
    # 札の PDF も開く
    code, body = get(f"/sheet/{sid}/{hid}_v{ver}_after.pdf")
    assert code == 200 and body[:4] == b"%PDF", ("札の PDF", rec["id"], code)
    # 開いても刷った案にならず、型紙の確定も増えない
    assert printed_versions(sid, hid) == [], ("刷った案になった", rec["id"])
    assert loop.sheet_confirmations(sid) == [], ("確定が増えた", rec["id"])
assert "H-C" in seen, "前の試行の H-C の記録が無い（この試験の芯）"

server.shutdown()
print("ok: 本物の記録", len(real), "件の札から、記録の案と版の紙が窓に出る")
