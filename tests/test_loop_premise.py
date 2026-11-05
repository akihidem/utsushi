"""輪の前提を試験で見る。本人の言葉（2026-11-05）:
「これをオフラインで作った後のループの動きにする。型紙が正解ではなくて、とりあえずAIが考えた仮説であるということを明示する。システム側もそれを認識した上でループを回す」

見る事:
- 輪を回す Claude の担当（仮説・読み・案・観察）の全部に、同じ前提の文が渡る。1 つでも抜けると「システム側も認識」が崩れる。
- 使い手が自分で立てた仮説の紙には「AI が考えた」と刷らない。人の仮説を AI の案と書かないため。
- カメラの担当は人の出来を書かない（本人の言葉 11-05「カメラで見るのはそういうとこだよ」）。
"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from api import generate, loop_agents, observe  # noqa: E402
from omochae import hypotheses  # noqa: E402
from omochae.marks import HYPOTHESIS, LOOP_PREMISE, OWN_HYPOTHESIS, PREMISE_PAGE, mark_lines  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"

for name, system in (("generate", generate.SYSTEM), ("interpret", loop_agents.INTERPRET_SYSTEM), ("propose", loop_agents.PROPOSE_SYSTEM), ("observe", observe.SYSTEM)):
    assert LOOP_PREMISE in system, f"{name} の担当に前提が渡っていない"
assert "人の出来は書きません" in observe.SYSTEM and "工夫" in observe.SYSTEM

assert "正しい答えではありません" in PREMISE_PAGE and "ためしの案（仮説）" in PREMISE_PAGE  # やさしい言葉の文（#318）

# 紙の文は本人の決定の文（#258）。使い手が自分で立てた仮説の紙だけ「自分で立てた」と刷る
assert "AI が考えた" in HYPOTHESIS and "AI が考えた" not in OWN_HYPOTHESIS and "正しい答えではありません" in OWN_HYPOTHESIS
src = {"holding": "所蔵", "modification_note": "改変", "source_id": G}
# G は必須 2 種なので、今の組は前の文（凍結の床・#318）。試作の玩具は新しい文
from omochae.marks import HYPOTHESIS_FROZEN  # noqa: E402
assert HYPOTHESIS_FROZEN in mark_lines(src) and HYPOTHESIS in mark_lines({**src, "source_id": "NDL-試作"})
assert OWN_HYPOTHESIS in mark_lines({**src, "hypothesis_mark": OWN_HYPOTHESIS}) and HYPOTHESIS not in mark_lines({**src, "hypothesis_mark": OWN_HYPOTHESIS})

# 自分の仮説の紙を実際に刷って見る。AI の仮説の紙は tests/test_hypothesis_label.py が見る
with tempfile.TemporaryDirectory() as tmp:
    os.environ["OMOCHAE_DATA"] = tmp
    rec, failures = hypotheses.save_own(G, "糸で引く", "糸を引くと扇が開く", "筒の線")
    assert not failures
    assert hypotheses.print_own(G, rec["id"], f"{tmp}/own") == 0
    flat = "".join(subprocess.run(["pdftotext", f"{tmp}/own_free.pdf", "-"], capture_output=True, text=True, check=True).stdout.split())
    assert "".join(OWN_HYPOTHESIS.split()) in flat, "自分の仮説の紙に AI の案の文が刷られている"
    assert "AIが考えた" not in flat
print("ok")
