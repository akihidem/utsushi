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
    # 11-06 から試した後の紙は刷らない（本人の決まり「文章のプリントは廃止」）。札に紙への道は出さない
    assert "kind=after" not in body.decode() and f"{hid}_v{ver}_after" not in body.decode(), ("札に試した後の紙への道がある", rec["id"])
    # 前の札のリンクで窓へ来ても、ほかの案の試した後の紙が黙って出ない（窓は型紙だけ）
    code, body = get(f"/toy/{sid}?see={hid}&kind=after&v={ver}")
    shown = window(body.decode())
    assert code == 200 and "_after" not in shown, ("窓に試した後の紙が出ている", rec["id"])
    # 前に配ったリンクのために残した /sheet の道は、記録の案と版の紙を開く
    code, body = get(f"/sheet/{sid}/{hid}_v{ver}_after.pdf")
    assert code == 200 and body[:4] == b"%PDF", ("札の PDF", rec["id"], code)
    # 開いても刷った案にならず、型紙の確定も増えない
    assert printed_versions(sid, hid) == [], ("刷った案になった", rec["id"])
    assert loop.sheet_confirmations(sid) == [], ("確定が増えた", rec["id"])
assert "H-C" in seen, "前の試行の H-C の記録が無い（この試験の芯）"

server.shutdown()
print("ok: 本物の記録", len(real), "件の札に試した後の紙への道は出ず、残した道は記録の案と版の紙を開く")
