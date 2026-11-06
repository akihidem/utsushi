"""御来迎の次の組 goraigo-v14（#115）。前の組 goraigo-v10 の紙と指紋は変えない（tests/test_floor_pin.py が見る）。

なぜ次の組か: 本人の決定（2026-11-06）「筒を外す形（lift）はやめる。下から押し上げるバージョンを作る。側面のつまみのバージョンは廃止。
内筒を付ける。」と「糸なしでやります」。型紙エンジン paper-to-toy の #122（形 rise）と #117（実物の写真と照らした色と札）と同じ形と字。
たたき台は H-C（柄を下から押し上げる。割り箸の形と字が合うので。統括の決め 11-06）で、寸法はエンジンの見本 examples/goraigo_v14.json の値（雛形の既定では検査に落ちる。#127 の割り箸の形・#132 の扇をまるごと倍と内筒の隙間）。

見る線（この試験はまだ途中。手順の紙が A4 に収まらない所は、刷る物を型紙だけにするサイトの PR を待つ。統括の決め 11-06）:
- たたき台と寸法は組ごと: 次の組は H-C の rise の寸法、前の組は H-A のつまみ
- 考えの節（ループ 1）は、たたき台の寸法が全部読める呼び名を持つ時だけ出る。次の組の寸法の 4 つの呼び名（筒の高さ・台の一辺・像の幅・
  像の高さ）は窓口が本人の委任で選んだ案 A（11-06）
"""
import json

from omochae import hypotheses
from omochae.compose import TEMPLATES
from omochae.hypotheses import ROOT
from web import think_sheet

G = "NDL-1187053-R0000005-L"
FAN = TEMPLATES["slider_fan"]
V14 = {"push_part": "rise", "tube_side": 26, "tube_height": 130, "pusher_side": 24.5, "pusher_height": 57.5, "push_amount": 60,
       "base_side": 24.0, "fold_count": 44, "fold_width": 4, "fold_height": 57.2, "figure_w": 10.4, "figure_h": 27.7}


class old_set:
    """前の組の紙を組む（雛形は SHEET_SET で組を見分ける）。"""

    def __enter__(self):
        self.keep = FAN.SHEET_SET
        FAN.SHEET_SET = FAN.FROZEN_SET

    def __exit__(self, *_):
        FAN.SHEET_SET = self.keep


# 1. 組の名前と、組ごとのたたき台と寸法
assert (FAN.SHEET_SET, FAN.FROZEN_SET) == ("goraigo-v14", "goraigo-v10")
raw = json.loads((ROOT / "data/hypotheses" / f"{G}.json").read_text(encoding="utf-8"))
assert raw["sheet"] == "H-A" and raw["sheet_by_set"] == {"goraigo-v14": "H-C"}
h = hypotheses.sheet_of(G)
assert h["id"] == "H-C" and h["params"] == V14 and h["name"] == "柄を下から押し上げる", (h["id"], h["params"])
with old_set():
    h0 = hypotheses.sheet_of(G)
    assert h0["id"] == "H-A" and h0["params"]["push_part"] == "tab", (h0["id"], h0["params"])
assert not FAN.check_range({**FAN.DEFAULTS, **V14}) and not FAN.check_physics({**FAN.DEFAULTS, **V14})

# 2. 考えの節: 次の組のたたき台の寸法が全部読めるので節が出る。4 つの呼び名は案 A の字
assert think_sheet.ready(G), [k for k, v in V14.items() if not think_sheet.readable("slider_fan", k, v)]
assert {k: think_sheet.NAMES[k] for k in ("tube_height", "base_side", "figure_w", "figure_h")} == {
    "tube_height": "筒の高さ（mm）", "base_side": "台の一辺（mm）", "figure_w": "像の幅（mm）", "figure_h": "像の高さ（mm）"}
assert think_sheet.VALUES["rise"] == think_sheet.VALUES["stick"] == "柄", "押す所の呼び名は、押す部品（割り箸の柄）の今の字（新しい字にしない）"
assert 'id="think"' in think_sheet.section(G)

# 3. 玩具ごとの共通の字のうち、糸の前提の 5 つは v14 の組では出さない（窓口が本人の委任で選んだ案 A 11-06・字は変えず外すだけ）。
# 前の組 v10 は今のまま出す。頁（玩具の頁）と試した後の紙の両方で見る
FIVE = {"questions": ["何の力で扇が開くのか（紙の力・糸・手）"],
        "after_try.contrasts": ["紙の力だけの時と、糸で引いた時を比べる"],
        "after_try.card": ["戻る力が、こすれる力や糸の重さより小さいと、途中で止まります。"],
        "analogy.related": ["てこ: 糸で引く時は、糸を結ぶ所が扇の要から遠いほど、小さな力で開く（要が支点）",
                            "止まる角度: 扇の中心が筒の口より上にあるほど、口の角に当たる前に大きく開ける"]}
assert raw["hide_by_set"] == {"goraigo-v14": FIVE}
texts = [t for v in FIVE.values() for t in v]


def shown(data):
    """記録の共通の字の、出す物の全部（比べる事は change の字）。"""
    return set(data["questions"]) | {c["change"] for c in data["after_try"]["contrasts"]} | set(data["after_try"]["card"]) | set(data["analogy"]["related"])


from omochae.instructions import compose_after  # noqa: E402
from web import toy  # noqa: E402

src = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))


def after_words(data):
    return "".join("".join(t.text for t in compose_after(src, data["toy"], data["after_try"], sheet_set=FAN.SHEET_SET)[0]["texts"] if t.text).split())


now = hypotheses.load(G)
assert not set(texts) & shown(now), set(texts) & shown(now)
assert len(shown(now)) == len(shown(raw)) - len(texts), "外すのは 5 つだけ"
page = toy.toy_page(G)
assert not any(t in page for t in texts), [t for t in texts if t in page]
assert not any("".join(t.split()) in after_words(now) for t in FIVE["after_try.contrasts"] + FIVE["after_try.card"])
with old_set():
    then = hypotheses.load(G)
    assert set(texts) <= shown(then), "前の組の字が外れた"
    assert all("".join(t.split()) in after_words(then) for t in FIVE["after_try.contrasts"] + FIVE["after_try.card"])
    assert all(t in toy.toy_page(G) for t in FIVE["analogy.related"]), "前の組の頁のたとえが外れた"

# 4. 押し方の違う紙の記録からは次の版を作らない（窓口が本人の委任で決めた案 A 11-06）。11-04 の R-0002 は goraigo-v7 の H-C（柄を差す形）の紙。
# 今の組の H-C は割り箸で押し上げる形なので、向く先が無い。今の組の記録・組を持たない記録・前の組で同じ形の記録は今までどおり
from omochae import loop  # noqa: E402

assert loop.next_target(G, "H-C", "goraigo-v7") is None and loop.next_target(G, "H-A", "goraigo-v7") is None
assert loop.next_target(G, "H-C", "goraigo-v14") == "H-C" and loop.next_target(G, "H-C") == "H-C"
with old_set():
    assert loop.next_target(G, "H-A", "goraigo-v7") == "H-A", "前の組では 11-04 の H-A の記録から次の版に進める（前と同じ）"
    assert loop.next_target(G, "H-C", "goraigo-v7") is None

print("ok 御来迎の次の組 goraigo-v14。組ごとのたたき台と寸法・考えの節の呼び名・糸の前提の字 5 つを v14 で出さない・押し方の違う記録から次の版を作らない")
