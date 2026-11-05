"""輪の前提を試験で見る。本人の言葉（2026-11-05）:
「これをオフラインで作った後のループの動きにする。型紙が正解ではなくて、とりあえずAIが考えた仮説であるということを明示する。システム側もそれを認識した上でループを回す」

見る事:
- 輪を回す Claude の担当（仮説・読み・案・観察）の全部に、同じ前提の文が渡る。1 つでも抜けると「システム側も認識」が崩れる。
- 紙は、試作の玩具と必須 2 種の次の版に新しい文が刷られ、必須 2 種の今の版の文は変わらない（凍結の床）。
- 使い手が自分で立てた仮説の紙には「AI が考えた」と刷らない。人の仮説を AI の案と書かないため。
- カメラの担当は人の出来を書かない（本人の言葉 11-05「カメラで見るのはそういうとこだよ」）。
"""
import inspect
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from api import generate, loop_agents, observe  # noqa: E402
from omochae import hypotheses  # noqa: E402
from omochae.marks import AI_HYPOTHESIS, HYPOTHESIS, LOOP_PREMISE, PREMISE_PAGE, mark_lines  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"

for name, system in (("generate", generate.SYSTEM), ("interpret", loop_agents.INTERPRET_SYSTEM), ("propose", loop_agents.PROPOSE_SYSTEM), ("observe", observe.SYSTEM)):
    assert LOOP_PREMISE in system, f"{name} の担当に前提が渡っていない"
assert "人の出来は書きません" in observe.SYSTEM and "工夫" in observe.SYSTEM

assert "正解では" in PREMISE_PAGE and "AI が考えた仮説" in PREMISE_PAGE
assert "正解では" in AI_HYPOTHESIS and "AI が考えた仮説" in AI_HYPOTHESIS

# 紙の印の選び方。必須 2 種の版 1 だけは今の文（凍結の床）。
assert hypotheses.hypothesis_mark(G, 1) is None and hypotheses.hypothesis_mark(T, 1) is None
assert hypotheses.hypothesis_mark(G, 2) == AI_HYPOTHESIS and hypotheses.hypothesis_mark(T, 2) == AI_HYPOTHESIS
trial = next(p.stem for p in sorted((ROOT / "data/hypotheses").glob("*.json")) if hypotheses.stage(p.stem) == "試作")
assert hypotheses.hypothesis_mark(trial, 1) == AI_HYPOTHESIS
src = {"holding": "所蔵", "modification_note": "改変", "source_id": G}
assert HYPOTHESIS in mark_lines(src) and AI_HYPOTHESIS not in mark_lines(src)
assert AI_HYPOTHESIS in mark_lines({**src, "hypothesis_mark": AI_HYPOTHESIS})
# 自分の仮説の紙は印の選び方を通さない
assert "hypothesis_mark" not in inspect.getsource(hypotheses.print_own)

# 試作の玩具を実際に刷って、新しい文が紙に載り、紙の床（長くなった文で組みが崩れない）を通る事を見る。
with tempfile.TemporaryDirectory() as tmp:
    data = hypotheses.load(trial)
    hid = data["hypotheses"][0]["id"]
    assert hypotheses.print_sheet(trial, hid, f"{tmp}/{hid}_v1", 1) == 0
    for name in (f"{hid}_v1.pdf", f"{hid}_v1_tejun.pdf"):
        flat = "".join(subprocess.run(["pdftotext", f"{tmp}/{name}", "-"], capture_output=True, text=True, check=True).stdout.split())
        assert "".join(AI_HYPOTHESIS.split()) in flat, f"{name} に新しい印が載っていない"
print("ok")
