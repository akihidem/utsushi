"""型紙は正しい答えでなく AI が考えた仮説だと、紙と頁に出す（#258、本人の決定）。
文はやさしい言葉の文（#318、本人の決定 11-05）。必須 2 種の今の組（凍結の床）だけは前の文（marks.HYPOTHESIS_FROZEN）のまま刷る。"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from omochae import hypotheses, marks  # noqa: E402
from omochae.compose import compose  # noqa: E402
from omochae.instructions import compose_after, compose_sheet  # noqa: E402
from web.play_server import serve  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORDS = "仮説（ためしの案）: AI が考えた、ためしに作るための案の 1 つです。正しい答えではありません。作って、動くか見て、直していきます。"
REQUIRED = {"NDL-1187053-R0000005-L": "H-A", "NDL-1187053-R0000014-R": "H-A"}
assert marks.HYPOTHESIS == WORDS
# 語の見張りで外すのは打ち消しの文だけ。文から「正解」を外したら、もう残っていない
assert "正解" not in WORDS.replace("正解ではありません", "")
# 前の文を刷るのは、雛形の今の組が凍結の組の玩具だけ。組を上げて FROZEN_SETS を直し忘れると、ここで落ちる
from omochae.compose import TEMPLATES  # noqa: E402
for sid, sheet_set in marks.FROZEN_SETS.items():
    assert TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].SHEET_SET == sheet_set, (sid, sheet_set)


def flat(s):
    return "".join(s.split())


def printed(layout):
    return flat("".join(t.text or "" for t in layout["texts"]))


# 必須 2 種と試作の全部で、型紙・手順の紙・試した後の紙に同じ文が刷られる
paths = sorted((ROOT / "data/hypotheses").glob("*.json"))
assert len(paths) >= 80, len(paths)
for p in paths:
    sid = p.stem
    data = hypotheses.load(sid)
    source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    template = data.get("template", "slider_fan")
    h = next(x for x in data["hypotheses"] if x.get("params") is not None)
    _, layout, failures = compose(h.get("template", template), h["params"], source)
    assert not failures, (sid, [f.line() for f in failures])
    sheet, failures = compose_sheet(h.get("template", template), h["params"], source, h["name"], h.get("how_it_moves", ""))
    assert not failures, (sid, [f.line() for f in failures])
    after, failures = compose_after(source, h["name"], data["after_try"])
    assert not failures, (sid, [f.line() for f in failures])
    for name, lay in (("型紙", layout), ("手順の紙", sheet), ("試した後の紙", after)):
        want = marks.HYPOTHESIS_FROZEN if sid in marks.FROZEN_SETS else WORDS
        assert flat(want) in printed(lay), (sid, name)

# 刷った PDF から読み直せる（必須 2 種）
for sid, hid in REQUIRED.items():
    r = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "--source", sid, "print", hid, "--out", f"{tmp}/{sid}"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for pdf in (f"{tmp}/{sid}.pdf", f"{tmp}/{sid}_tejun.pdf"):
        text = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True, check=True).stdout
        # 前の文で刷るのは、今の組が凍結の組の玩具（marks.FROZEN_SETS。今は御来迎だけ。虎は次の組 tora-v4 に上げた）
        want = marks.HYPOTHESIS_FROZEN if sid in marks.FROZEN_SETS else WORDS
        assert flat(want) in flat(text), pdf

# 頁の型紙の窓に同じ文が出る
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
G = "NDL-1187053-R0000005-L"
req = urllib.request.Request(f"{base}/toy/{G}/print", urllib.parse.urlencode({"hypothesis": "H-A"}).encode(), headers={"Origin": base})
urllib.request.urlopen(req).read()
with urllib.request.urlopen(f"{base}/toy/{G}?see=H-A") as r:
    assert WORDS in r.read().decode()
server.shutdown()

print("ok")
