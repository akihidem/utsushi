"""連絡先の検査が長い文で遅くならず、上限を越えた文は検査に入る前に断る事を見る（#161）。

なぜ時間を測るか: 式が文の長さの 2 乗で遅くなると、貼り付け 1 回で送った人の画面が長く戻らない。式の字面では見張れない。
時間は機械の混み具合で揺れるので、3 回の一番速い値で比べ、上限より長い文でも見る（遅い式は長いほど差が開く）。
"""
import os
import pathlib
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api import words  # noqa: E402
from omochae import contrib, loop, records  # noqa: E402

LIMIT = contrib.MAX_BODY


def best(text):
    times = []
    for _ in range(3):
        start = time.perf_counter()
        assert contrib.check_pii({"body": text}) == [], text[:40]
        times.append(time.perf_counter() - start)
    return min(times)


# 1. 上限いっぱいの文で 0.1 秒の中。上限の 8 倍でも 1 秒の中（前の式は 8 倍の英字で 12 秒かかった）
shapes = {"英字": "a", "数字": "1a", "点": "a.", "空白": "a ", "記号": "+-", "at": "a at ", "下線": "a_"}
for name, unit in shapes.items():
    text = unit * (LIMIT // len(unit))
    assert best(text) < 0.1, (name, best(text))
    assert best(text * 8) < 1.0, (name, best(text * 8))
digits = "1" * LIMIT  # 数字だけの並びは電話番号の桁を越えるので、連絡先とは読まない
assert best(digits) < 0.1 and best(digits * 8) < 1.0
for name, text in (("at の後の空白", "x at y" + " " * LIMIT), ("@ の前の空白", "x" + " " * LIMIT), ("丸括弧の at", "x(at)" * (LIMIT // 5))):
    assert best(text) < 0.1 and best(text * 8) < 1.0, name

# 2. 長くても、終わりの方の連絡先を拾う（速くするために見る範囲を狭めていない）
assert contrib.check_pii({"body": "a" * LIMIT + " a.b@example.com"})
assert contrib.check_pii({"body": "a " * (LIMIT // 2) + "a at example dot com"})
assert contrib.check_pii({"body": "a" * LIMIT + "@example.com"}), "連絡先の頭が長くても拾う"
assert contrib.check_pii({"body": "x-" * 100 + "a@example.com"}), "記号でつながった頭でも拾う"

# 3. 上限を越えた記録は、検査に入る前に理由つきで断る
SID = "NDL-1187053-R0000005-L"
BASE = {"source_id": SID, "hypothesis_id": "H-A", "result": records.results_for(SID)[0]}
seen = []
real = records.check_pii
records.check_pii = lambda c: seen.append(c) or real(c)
try:
    for over in ({"note": "a" * (LIMIT + 1)}, {"answers": {"q": "a" * (LIMIT + 1)}}, {"ideas": ["a" * (LIMIT + 1)]},
                 {"fixes": [{"part": "扇", "change": "a" * (LIMIT + 1), "outcome": "x"}]}):
        fails = records.check({**BASE, **over})
        assert any(str(LIMIT) in f.message and "超える" in f.message for f in fails), (over.keys(), fails)
    assert seen == [], "上限を越えた文を検査に回した"
    # ちょうど上限なら断らず、検査に回す
    assert records.check({**BASE, "note": "あ" * LIMIT}) == [] and len(seen) == 1
finally:
    records.check_pii = real

# 4. 説明の口と、言葉の仮説の口も同じ。文が空の時に「空」と言う決まりは前のまま
real_record = loop.record
loop.record = lambda r: {}
try:
    fails = loop.save_explanation("R-0001", "確認者", "a" * (LIMIT + 1), "次")
    assert fails and "超える" in fails[0].message, fails
    fails = loop.save_explanation("R-0001", "確認者", "説明", "a" * (LIMIT + 1))
    assert fails and "超える" in fails[0].message, fails
    assert not list(loop.folder().glob("explanation-*")) if loop.folder().exists() else True
finally:
    loop.record = real_record
never = object()  # Claude を呼ぶ前に断るので、client には触らない
gs = {"source_id": SID}
fails = words.draft_words(gs, "a" * (LIMIT + 1), "案", "図の棒", "大人", never)[1]
assert fails and "超える" in fails[0].message, fails
assert {f.floor for f in words.draft_words(gs, "", "案", "図の棒", "大人", never)[1]} == {"F9.own"}
assert {f.floor for f in words.draft_words(gs, "連絡先 a@example.com", "案", "図の棒", "大人", never)[1]} == {"F10.pii"}
print(f"ok 上限 {LIMIT} 字。{len(shapes) + 4} 通りの文で速さを見た")
