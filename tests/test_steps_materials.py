"""手順に出る道具と材料が「用意する物」にある（#294）。用意する物を見てそろえれば、手順の途中で足りなくならない。

なぜ要るか: 手順の文は雛形に書いた決まった文で、用意する物は部品表から出る。別々に書くので、片方を直しても
もう片方は黙って食い違う。全部の案を刷って照らした時に、8 種 16 案で抜けていた。

何を見るか: 全部の玩具の全部の案で、手順の字と遊び方の字に出る語が、同じ案の用意する物の字にある事。語の一覧は手順の文を
全部読んで決めた（手順に新しい道具を書く時は NAMES に足す）。遊び方は手順のすぐ下に刷るので、字が違うと同じ紙に 2 つの字が並ぶ。紙一枚の印の案は、手順にも ways のほかの材料の語が
出ない事（札の字と手順を合わせる）。

必須 2 種の今の組で抜けている案は、組の名前を条件に FROZEN に書く。組を上げると例外が外れてこの試験が落ちるので、
次の組で直し忘れない。抜けを直した時も、例外が古いと言って落ちる。
"""
import json
import re
from types import SimpleNamespace

from omochae import ways
from omochae.compose import TEMPLATES
from omochae.hypotheses import ROOT

GORAIGO, TORA = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
KOMA = "NDL-1187053-R0000026-L-3"
KITES = {f"NDL-1187053-R0000024-L{s}" for s in ("", "-2", "-3")}
# 手順の語 → 用意する物にこの字のどれかがあればよい。手順は用意する物と同じ字で書く。紐と玉は、呼び名として許すと
# 用意する物の「糸」「ビーズ」と別の物に読めるので、同じ字の時だけ通す。
# 本は「1 本」の数え方と分けるため、載せる所の形で見る。
NAMES = {
    "竹串": ("竹串",), "竹ひご": ("竹ひご",), "楊枝": ("楊枝",), "つまようじ": ("つまようじ",), "割り箸": ("割り箸",),
    "カッター": ("カッター",), "はさみ": ("はさみ",), "のり": ("のり",), "定規": ("定規",), "テープ": ("テープ",),
    "糸": ("糸",), "紐": ("紐",), "粘土": ("粘土",), "ビーズ": ("ビーズ",), "玉": ("玉",), "厚紙": ("厚紙",),
    "輪ゴム": ("輪ゴム",), "割りピン": ("割りピン", "割ピン"), "ストロー": ("ストロー",), "鈴": ("鈴",), "盆": ("盆",),
    "豆": ("豆",), "本に": ("本",), "目打ち": ("目打ち",), "下敷き": ("下敷き",), "鉛筆": ("鉛筆",), "ニッパー": ("ニッパー",),
    "紙やすり": ("紙やすり",), "硬貨": ("硬貨",), "千枚通し": ("千枚通し",), "ホチキス": ("ホチキス",), "接着剤": ("接着剤",),
}
# 物の名前でない字。糸の穴は腕木の穴の呼び名（押して動かす形は糸を使わない）で、玉結びは結び方の名前。
NOT_TOOL = re.compile(r"糸の穴|玉結び")
# 必須 2 種の今の組で直さない案。虎 A はたたき台で、紙の指紋を変えない（凍結の床）ので、次の組で足す。ほかは本人の決定
# （#332 の点 3）で今の組から刷らなくなった案で、直しても誰の手にも渡らない。記録が番号で結ばれているので仮説は残る。
# 御来迎 E は部品に穴が無いので、次の組で使うなら、竹串を足さず手順の穴あけの文を外す（下で確かめる）。
FROZEN = {
    (GORAIGO, "goraigo-v10"): {"H-B": ["竹串"], "H-C": ["竹串"], "H-D": ["竹串"], "H-E": ["竹串"]},
    (TORA, "tora-v3"): {"H-A": ["カッター"], "H-C": ["カッター"]},
    # 御来迎の次の組（goraigo-v14）でも、E は刷らないヒントの形のまま（たたき台は H-C）。手順の穴あけの文を外すと新しい字になるので、
    # E を使う時まで今の字を残す（型紙エンジンの字と同じ）
    (GORAIGO, "goraigo-v14"): {"H-E": ["竹串"]},
}

# 部品に穴があるのに、手順にあけ方の文が無い案。台の穴に竹串を通す形で、文を足すと新しい字になるので、今は足さない。
NO_POKE_WORDS = {("NDL-1187053-R0000007-L", "H-A"), ("NDL-1187053-R0000007-L", "H-B")}


def steps_text(tpl, p):
    return NOT_TOOL.sub("", " ".join(tpl.steps(p)))


def missing(tpl, p):
    """手順に出るのに、用意する物の字に無い語。"""
    listed, steps = " ".join(str(m) for m in tpl.materials(p)), steps_text(tpl, p)
    return sorted(w for w, names in NAMES.items() if w in steps and not any(n in listed for n in names))


def how_missing(how, tpl, p):
    """遊び方に出るのに、用意する物の字に無い語。"""
    return missing(SimpleNamespace(steps=lambda _: [how], materials=tpl.materials), p)


def says_missing_hole(tpl, p):
    """部品に穴が無いのに、手順に穴の字がある。無い穴を探させ、要らない物をそろえさせる。"""
    return "穴" in " ".join(tpl.steps(p)) and not any(q.holes for q in tpl.parts(p))


def lacks_poke_words(tpl, p):
    """部品に穴があるのに、手順に穴のあけ方の文が無い。穴の字だけを見ると、穴に糸を通す文が残る案（兜巾）で見逃す。"""
    return any(q.holes for q in tpl.parts(p)) and "の先であける" not in " ".join(tpl.steps(p))


def cases():
    """全部の案を (玩具の id, 案の id, 雛形の id, 雛形, 寸法) で返す。"""
    for path in sorted((ROOT / "data/hypotheses").glob("*.json")):
        # 記録を直接読む。hypotheses.load は人が採った新しい仮説を data/loop から重ねるので、機械ごとに案の数が変わる。
        data = json.loads(path.read_text(encoding="utf-8"))
        for h in data["hypotheses"]:
            if h.get("params") is None:
                continue
            tid = h.get("template", data.get("template", "slider_fan"))
            tpl = TEMPLATES[tid]
            yield path.stem, h["id"], tid, tpl, {**tpl.DEFAULTS, **h["params"]}


def allowed(sid, hid, tpl):
    return FROZEN.get((sid, tpl.SHEET_SET), {}).get(hid, [])


def check():
    """手順と用意する物の食い違いを (玩具の id, 案の id, 無い語, 例外に書いた語) で返す。"""
    return [(sid, hid, missing(tpl, p), allowed(sid, hid, tpl)) for sid, hid, _, tpl, p in cases() if missing(tpl, p) != allowed(sid, hid, tpl)]


# 1. 全部の案で、手順に出る語が用意する物にある。例外は書いた分だけで、全部の雛形を通る
all_cases = list(cases())
assert len(all_cases) > 100 and {tid for _, _, tid, _, _ in all_cases} == set(TEMPLATES), "通っていない雛形がある"
wrong = check()
assert not wrong, ("手順に出る語が用意する物に無い、または例外が古い", wrong)

# 遊び方も同じ。今の組の例外は要らない（必須 2 種の遊び方に抜けは無い）
how_of = {(path.stem, h["id"]): h["how_it_moves"] for path in sorted((ROOT / "data/hypotheses").glob("*.json"))
          for h in json.loads(path.read_text(encoding="utf-8"))["hypotheses"]}
wrong = [(sid, hid, how_missing(how_of[sid, hid], tpl, p)) for sid, hid, _, tpl, p in all_cases if how_missing(how_of[sid, hid], tpl, p)]
assert not wrong, ("遊び方に出る語が用意する物に無い", wrong)

# 2. 穴あけの字は、部品に穴がある案だけに出す（穴の無い案に、要らない物をそろえさせない）。手順の穴の字も同じで、御来迎 E だけ今の組の例外
for sid, hid, _, tpl, p in all_cases:
    if any("穴あけ" in str(m) for m in tpl.materials(p)):
        assert any(q.holes for q in tpl.parts(p)), ("穴の無い案に穴あけの字がある", sid, hid)
    if says_missing_hole(tpl, p):
        assert (sid, hid) == (GORAIGO, "H-E") and tpl.SHEET_SET in ("goraigo-v10", "goraigo-v14"), ("穴の無い案の手順に穴の字がある", sid, hid)
# 反対の向き: 部品に穴がある案は、あけ方の文を消さない
named = {(sid, hid) for sid, hid, _, tpl, p in all_cases if lacks_poke_words(tpl, p)}
assert named == NO_POKE_WORDS, ("穴があるのにあけ方の文が無い、または例外が古い", named ^ NO_POKE_WORDS)

# 3. 紙一枚の印の案の手順に、ほかの材料の語が出ない。御来迎 E の竹串は今の組の例外で、穴が無いので印は外さない
for sid, hid, tid, tpl, p in all_cases:
    if ways.details(tid, p)["one_sheet"]:
        found = ways.OTHER.findall(steps_text(tpl, p))
        assert found == FROZEN.get((sid, tpl.SHEET_SET), {}).get(hid, []), ("紙一枚の札と手順が合わない", sid, hid, found)
fan = TEMPLATES["slider_fan"]
e = next(p for sid, hid, _, _, p in all_cases if (sid, hid) == (GORAIGO, "H-E"))
assert ways.details("slider_fan", e)["one_sheet"] is True and not any(q.holes for q in fan.parts(e)), "御来迎 E の読みが変わった"


# 4. 負の対照: 照らす形が抜けを拾う事を確かめる（拾わない検査は、同じと言っても意味が無い）
class Stub:
    def __init__(self, steps, materials, parts=()):
        self.steps, self.materials, self.parts = (lambda p: steps), (lambda p: materials), (lambda p: parts)


assert missing(Stub(["穴は竹串の先であける"], ["のり、はさみ"]), {}) == ["竹串"]
assert missing(Stub(["穴は竹串の先であける"], ["竹串（穴あけ）"]), {}) == []
assert missing(Stub(["腕木の糸の穴に留める"], ["竹串"]), {}) == []  # 穴の呼び名は物の名前でない
assert missing(Stub(["糸を腕木の糸の穴に結ぶ"], ["竹串"]), {}) == ["糸"]  # 本物の糸は隠さない
assert missing(Stub(["内側で玉結びにする"], ["糸"]), {}) == [] and missing(Stub(["玉を通す"], ["糸"]), {}) == ["玉"]
assert missing(Stub(["玉を通す"], ["ビーズ（穴に芯が通る物）"]), {}) == ["玉"] and missing(Stub(["ビーズを通す"], ["ビーズ（穴に芯が通る物）"]), {}) == []
assert missing(Stub(["紐を巻く"], ["糸（長さ約 30cm）"]), {}) == ["紐"] and missing(Stub(["糸を巻く"], ["糸（長さ約 30cm）"]), {}) == []
assert missing(Stub(["紐を巻く"], ["木綿の糸か細い紐（80cm ほど）"]), {}) == [] and missing(Stub(["紐を巻く"], ["のり"]), {}) == ["紐"]
assert missing(Stub(["2 本の先を結ぶ"], ["のり"]), {}) == [] and missing(Stub(["端を本に載せる"], ["のり"]), {}) == ["本に"]
assert how_missing("紐を引く", Stub([], ["糸（長さ約 30cm）"]), {}) == ["紐"] and how_missing("糸を引く", Stub([], ["糸（長さ約 30cm）"]), {}) == []
assert says_missing_hole(Stub(["穴は竹串の先であける"], [], [SimpleNamespace(holes=[])]), {})
assert not says_missing_hole(Stub(["穴は竹串の先であける"], [], [SimpleNamespace(holes=[(1, 1, 1)])]), {})
assert not says_missing_hole(Stub(["部品を実線で切る"], [], [SimpleNamespace(holes=[])]), {})
assert lacks_poke_words(Stub(["2 つの穴に糸を通す"], [], [SimpleNamespace(holes=[(1, 1, 1)])]), {})  # 穴に通す文だけでは足りない
assert not lacks_poke_words(Stub(["穴は竹串の先であける"], [], [SimpleNamespace(holes=[(1, 1, 1)])]), {})
assert not lacks_poke_words(Stub(["部品を実線で切る"], [], [SimpleNamespace(holes=[])]), {})

# 穴あけの文を全部の形で外すと、穴がある兜巾を名指しする
prop = TEMPLATES["stick_prop"]
keep = prop.steps
prop.steps = lambda p: [s.replace("。穴は竹串の先であける", "") for s in keep(p)]
try:
    named = {(sid, hid) for sid, hid, _, tpl, p in cases() if lacks_poke_words(tpl, p)}
finally:
    prop.steps = keep
assert {("NDL-1187053-R0000005-R-2", "H-A"), ("NDL-1187053-R0000005-R-2", "H-B")} <= named, named

# 用意する物から字を消すと、その案を名指しする
kite = TEMPLATES["string_pull"]
keep = kite.materials
kite.materials = lambda p: [str(m).replace("竹串（穴あけ）", "") for m in keep(p)]
try:
    named = check()
finally:
    kite.materials = keep
assert {sid for sid, _, got, _ in named if got == ["竹串"]} >= KITES, named

# 組を上げると例外が外れ、次の組で直す案を名指しする。B〜D は次の組から竹串の行が付く（雛形の materials）ので、残るのは穴の無い E だけ
# （例外の表に無い組の名に置く。前の組 goraigo-v10 に戻すと、B〜D の例外も効いて何も出ない事も見る）
now = fan.SHEET_SET
fan.SHEET_SET = "goraigo-v99"
try:
    named = check()
finally:
    fan.SHEET_SET = now
assert named == [(GORAIGO, "H-E", ["竹串"], [])], named
fan.SHEET_SET = fan.FROZEN_SET
try:
    assert check() == [], check()
finally:
    fan.SHEET_SET = now

# 例外に書いた抜けを直すと、例外が古いと言って落ちる。今の組（goraigo-v14）の例外は E だけ、前の組（goraigo-v10）は B〜E
keep = fan.materials
fan.materials = lambda p: [*keep(p), "竹串（穴あけ）"]
try:
    named = check()
    fan.SHEET_SET = fan.FROZEN_SET
    named_old = check()
finally:
    fan.materials = keep
    fan.SHEET_SET = now
assert named == [(GORAIGO, "H-E", [], ["竹串"])], named
assert named_old == [(GORAIGO, h, [], ["竹串"]) for h in ("H-B", "H-C", "H-D", "H-E")], named_old

# 5. 独楽 B は、本人が採った字（2026-11-06）を一字も変えずに出す。芯が竹ひごの長さなので手順も竹ひごと書き、
# 芯の穴をあけるつまようじを用意する物に足す。字を雛形の決まりから組むので、出来上がった字そのものを見る。
# 採った案は「手順 4」と名指ししていたので、手順は位置まで見る（前に手順が入ってずれたら、確かめ直す）。
spin = TEMPLATES["spin_toy"]
koma = next(p for sid, hid, _, _, p in all_cases if (sid, hid) == (KOMA, "H-B"))
assert spin.steps(koma)[3] == "竹ひごを穴に通し、下に 10mm 出してのりで止める", spin.steps(koma)
assert "つまようじ（穴あけ）" in spin.materials(koma), spin.materials(koma)

print(f"ok {len(all_cases)} 案で手順と遊び方と用意する物が合う（今の組の例外 {sum(len(v) for v in FROZEN.values())} 案）")
