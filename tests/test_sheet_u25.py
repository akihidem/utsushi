"""U-25（学習プリントを本人の 4 つの着目で考え直す、案 1〜4）と research/22 の候補 1・4 が紙に入っている事を見る。

受け入れの条件は LANE-NOTES.md（lane/print-u25）に先に凍結した物。紙の上の文字と絵の部品で確かめる。
刷った PDF の印（check_pdf）と画像の数は、print-teacher の命令を通して見る。
"""
import json
import pathlib
import subprocess
import sys
import tempfile

from omochae.compose import compose
from omochae.instructions import (AFTER_QUESTION, COMPARE_QUESTIONS, QUESTIONS, RESULT_HEAD, STUCK, TEACHER_FOCUS,
                                  compose_after, compose_compare, compose_free, compose_sheet, compose_teacher)
from omochae.templates import pivot_counterweight, slider_fan

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"


def src(sid):
    return json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))


def words(layout):
    return [t.text for t in layout["texts"] if t.text]


def flat(layout):
    return "".join(words(layout))


fan = {"tab": {**slider_fan.DEFAULTS, "push_part": "tab", "hub": "axle", "pusher_height": 15},
       "stick": {**slider_fan.DEFAULTS, "push_part": "stick", "hub": "axle", "pusher_height": 84},
       "tube": {**slider_fan.DEFAULTS, "push_part": "tube", "hub": "rim", "push_amount": 36, "pusher_height": 84, "fold_count": 18, "fold_width": 8}}
pic = ROOT / "out/sources" / f"{G}.jpg"
sheets = {k: compose_sheet("slider_fan", p, src(G), f"御来迎 {k} 版 1", "筒を持ち、押す", picture=pic if pic.exists() else None) for k, p in fan.items()}
sheets["tora"] = compose_sheet("pivot_counterweight", pivot_counterweight.DEFAULTS, src(T), "虎 版 1", "頭に触れる")
# 「物差し」は紙の物差しの注記で見る。組み方の 1 番「刷った物差しに定規を当て」は型紙の物差しの話で、残す。
NO_MEASURE = ("（度）", "角度", "回数", "作り始めて", "10cm の物差し")

# S と A: どの手順の紙も検査を通り、測る欄と物差しが無い
for k, (layout, failures) in sheets.items():
    assert failures == [], (k, [f.line() for f in failures])
    text = flat(layout)
    assert not any(w in text for w in NO_MEASURE), (k, [w for w in NO_MEASURE if w in text])
    assert layout["ruler"] is None
    ws = words(layout)
    # A1 予想は動き方を言葉か絵で、描ける広さの枠
    ask = "頭はどう動くと思いますか（言葉か絵で）" if k == "tora" else "押すと、どこがどう動くと思いますか（言葉か絵で）"
    assert ask in ws, k
    assert any(s.get("tag") == "predict_box" and s["h"] >= 15 for s in layout["shapes"]), k
    # A3 丸の欄は同じ大きさ
    assert RESULT_HEAD in ws
    boxes = [s for s in layout["shapes"] if s["kind"] == "rect" and s["w"] == 30]
    assert len({(b["w"], b["h"]) for b in boxes}) == 1 and len(boxes) == len((pivot_counterweight if k == "tora" else slider_fan).RESULTS)
    # A4 4 問がこの順。折り返しても順は崩れない
    pos = [text.index(q) for q in QUESTIONS]
    assert pos == sorted(pos), k
    # A5 つまずいた所と直した点
    assert STUCK in ws and "直した点（部品・変えた事・結果）" in ws
assert QUESTIONS == ("一番おもしろかったのはどの時ですか", "どうしたら、もっと楽しくなりますか",
                     "なぜそう動くのか、自分の言葉か絵で（まだ分からない所も書く）", "作っている途中で思いついた事は何ですか")

# F1 折る向きの矢印は手順の紙の絵にだけ。谷は塗り、山は白抜き
for k in fan:
    layout = sheets[k][0]
    heads = [s["fill"] for s in layout["shapes"] if s.get("tag") == "arrowhead"]
    assert "black" in heads and "white" in heads, k
    assert any("谷折り" in w for w in words(layout)) and any("山折り" in w for w in words(layout))
    _, tpl_layout, _ = compose("slider_fan", fan[k], src(G))
    assert "shapes" not in tpl_layout, "型紙には矢印を足さない"
assert not any(s.get("tag") == "arrowhead" for s in sheets["tora"][0]["shapes"])

# F4 折る順は 3〜5 コマで、押し方で中身が変わり、順を変える余白を刷る
for k in fan:
    layout = sheets[k][0]
    n = sum(1 for s in layout["shapes"] if s.get("tag") == "order_panel")
    assert 3 <= n <= 5, (k, n)
    assert "折る順（目安）" in words(layout) and "やりやすい順に変えてよい" in flat(layout)
assert "土台" in flat(sheets["stick"][0]) and "割り箸を差す" in flat(sheets["stick"][0])
assert "竹串を通す" in flat(sheets["tab"][0])

# 色: 最初の一歩の平らな筒は v9 の 2 つの地の色を交互に塗り、面の境に破線を引かない
for k in fan:
    faces = [s for s in sheets[k][0]["shapes"] if s.get("tag") == "tube_face"]
    assert [f["fill"] for f in faces] == [slider_fan.PAPER, slider_fan.PAPER_ALT] * 2, k
    x0, y0 = faces[0]["pts"][0]
    x4, y1 = faces[-1]["pts"][2]
    inside = [s for s in sheets[k][0]["shapes"] if s["kind"] == "line" and s.get("dash")
              and x0 < s["x1"] < x4 and y0 <= s["y1"] <= y1]
    assert inside == [], "平らな筒の面の境に破線を引かない"

# B 試した後の紙: 物差しを刷らず、納得の問いは札の側（折り線より下）にある
hyp = json.loads((ROOT / "data/hypotheses" / f"{G}.json").read_text(encoding="utf-8"))
after, failures = compose_after(src(G), "御来迎 H-A 版 1", hyp["after_try"], sheet_set="goraigo-v9")
assert failures == [] and after["ruler"] is None
fold = next(s["y1"] for s in after["shapes"] if s.get("dash") == "1.5,1.5")
q = next(t for t in after["texts"] if t.text == AFTER_QUESTION)
assert q.y > fold
assert all(c["change"] in flat(after) for c in hyp["after_try"]["contrasts"]), "次に変える条件は残す"
# 札が長くて帯が取れない時は、今までどおり刷らない
_, failures = compose_after(src(G), "x", {**hyp["after_try"], "card": ["札の文がとても長い" * 40] * 12})
assert "F5.fold" in {f.floor for f in failures}

# C 見比べる紙: 角度の表と物差しを刷らず、どちらが良いかを決める欄が無い
ha, hb = hyp["hypotheses"][0], hyp["hypotheses"][1]
comp, failures = compose_compare(src(G), "御来迎", ha, hb, ("A", "B"))
assert failures == [] and comp["ruler"] is None
assert "回目" not in flat(comp) and "（度）" not in flat(comp)
assert all(q in words(comp) for q in COMPARE_QUESTIONS)
assert [w for w in words(comp) if "どちら" in w and "思いますか" not in w and "証明" not in w] == []

# D 先生の見る紙: 4 つの着目、つぶやきの欄。点も名前の欄も無い
teacher, failures = compose_teacher(src(G), "御来迎", sheet_set="goraigo-v9")
assert failures == [] and teacher["ruler"] is None
tw = words(teacher)
assert [f for f, _ in TEACHER_FOCUS] == ["おもちゃとして動いたか", "どうしたらもっと楽しいか", "仕組みは納得できるか", "哲学に沿った効果があったか"]
assert all(f"{i}. {f}" in tw for i, (f, _) in enumerate(TEACHER_FOCUS, 1))
assert any("つぶやき" in w for w in tw) and "点は付けない" in flat(teacher)
assert not any(w in flat(teacher) for w in ("点数", "評価", "◎", "名前の欄", "氏名"))

# 型紙なしの紙も同じ 4 問と丸の見出し（記録を同じ形で残す）
free, failures = compose_free(src(G), "自分の仮説", "押す", "筒", slider_fan.RESULTS)
assert failures == [] and all(q in flat(free) for q in QUESTIONS) and RESULT_HEAD in words(free)

# D の命令: 予想が無くても刷れ（答えも仮説も載らない紙）、印の検査と画像 0 枚を通る
with tempfile.TemporaryDirectory() as tmp:
    r = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "--source", G, "print-teacher", "--out", f"{tmp}/t"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert pathlib.Path(f"{tmp}/t.pdf").exists()
print("ok")
