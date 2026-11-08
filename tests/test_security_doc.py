"""SECURITY.md の「分かっている限りの今の事実」が、今のコードの値と食い違わない。

なぜ: 2026-11-08 の安全の点検の事項 8〜13 は作りを替えずに、今の事実と次の手を SECURITY.md に書いた（本人の指示 11-08「先ほどの点検の事項に、
対応してください。…見た目と挙動は変えず、安全の事項だけ直す」と統括の割り振り）。数や期限をコードが替えた時に、文書が黙って古くならないよう、
文書に書いた数をコードの値と照らす。字の言い回しは見ない（数と、書くと決めた項目があるかだけ）。
見る事:
- 直接の依存の数が requirements.txt の固定の行の数と同じ
- 保存期間の数（声の写し 72 時間・確かめ前の物を出す 2 時間・話した字の鍵 2 時間・しおりの待ち 3 時間・記録の鍵 15 分）と、しおりの順の数（504 通り・外れ 20 回）がコードの値と同じ
- 「fsync はしていない」と書いてある間は、store.write_atomic が fsync を呼ばない（呼ぶ形にしたら文書も直す）
- 事項 8〜13 の項目が「していない事」にある。書きかけの印（〈 〉）が残っていない
- SECURITY.md に名を書いた試験のファイル（tests/test_*.py）が、どれも在る（守りを書いた所が、在る試験を指す・直しの PR より先に字だけが入らない）
"""
import inspect
import itertools
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api import words  # noqa: E402
from omochae import media_review, records, shiori, store, voice_text  # noqa: E402

doc = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
pins = [l for l in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines() if re.match(r"[A-Za-z0-9_.-]+==", l.strip())]
assert f"直接の依存 {len(pins)} つ" in doc, ("直接の依存の数", len(pins))

assert voice_text.LIMIT == 72 * 3600 and "72 時間で消す" in doc
assert media_review.OWNER_HOURS == 2 and words.KEY_HOURS == 2 and "確かめ前の物を出す長さ（2 時間）" in doc and "話した字の紙を開く鍵（2 時間）" in doc
assert shiori.PENDING == 3 * 3600 and "しおりの待ち（3 時間）" in doc
assert records.OWNER_MINUTES == 15 and "記録の鍵 15 分・写真の鍵 2 時間" in doc
ways = len(list(itertools.permutations(range(shiori.PICTURES), shiori.ORDER)))
assert f"{ways} 通り" in doc and f"外れ {shiori.TOTAL_FAILS} 回で止める" in doc, (ways, shiori.TOTAL_FAILS)

if "`fsync` はしていない" in doc:
    assert "fsync" not in inspect.getsource(store.write_atomic), "write_atomic が fsync を呼ぶなら、SECURITY.md の事項 8 を直す"

not_done = doc[doc.index("## していない事"):doc.index("## エンジン（engine/）")]
for n in (8, 9, 10, 11, 12, 13):
    assert f"（事項 {n}）" in not_done, ("していない事に事項の項目が無い", n)
assert "〈" not in doc and "〉" not in doc, "書きかけの印が残っている"
# engine/tests/ の試験（エンジンの節）は engine/ の中で探す
named = sorted(set(m.group(0) for m in re.finditer(r"(?:engine/)?tests/test_[a-z0-9_]+\.py", doc)))
missing = [n for n in named if not (ROOT / n).exists()]
assert not missing, ("SECURITY.md が名を書いた試験が無い", missing)
print(f"ok SECURITY.md の数（直接の依存 {len(pins)}・保存期間・しおりの {ways} 通り）がコードと同じで、事項 8〜13 が していない事 にあり、名を書いた試験 {len(named)} 本が在る")
