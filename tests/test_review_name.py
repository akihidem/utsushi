"""呼び名「ワークショップの型紙レビュー」（制作者の言葉 2026-11-08「全てがワークショップです。」）。本物の API は呼ばない。

エンジンは同じ日に、経験者が作らずに型紙を読んだ指摘の呼び名を「作る前のレビュー」から替えた（engine/src/omochae/engine_loop.py）。
utsushi の側（版の歩みの表・ループの札・序の頁の輪・訳の表）も同じ字にそろえる（統括の決め 11-08）。
見る事:
1. 前の呼び名が、作り（src/）・版の歩みの表・訳の表に残っていない（記録の文書 docs/process/ と engine/ は見ない。記録は書いた時の字のまま）
2. utsushi の呼び名が、engine/ の中のエンジンの呼び名と同じ
3. 版の歩みの表の why の字（text）と changed は、呼び名を替える前と一字も同じ（替えたのは kind の呼び名と line の説明だけ。のこすの直った例を替えない）
"""
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
OLD, NEW = "作る前のレビュー", "ワークショップの型紙レビュー"
import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from web import kaizen_versions  # noqa: E402

# 1
places = [*(ROOT / "src").rglob("*.py"), ROOT / "data/history/kaizen-history.json", *(ROOT / "data/i18n").rglob("*.json")]
left = [str(p.relative_to(ROOT)) for p in places if OLD in p.read_text(encoding="utf-8")]
assert not left, ("前の呼び名が残っている", left)

# 2
engine = (ROOT / "engine/src/omochae/engine_loop.py").read_text(encoding="utf-8")
m = re.search(r'"review": "([^"]+)"', engine)
assert m and m.group(1) == NEW == kaizen_versions.REVIEW_NAME, ("エンジンの呼び名と違う", m and m.group(1), kaizen_versions.REVIEW_NAME)

# 3 呼び名を替える前の表（main 19447494）から取った印。why の text と changed を、行の順に並べた物の sha256
FROZEN = "1bb42f1b2cf9433a10130e5be88fce576571ba9a15b7908f582f636e815cb8b5"
table = json.loads((ROOT / "data/history/kaizen-history.json").read_text(encoding="utf-8"))
rows = [[t.get("template") or t.get("toy"), v.get("set") or v.get("version"), [w.get("text") for w in v.get("why", [])], v.get("changed", [])]
        for t in table["toys"] for v in t["versions"]]
got = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
assert got == FROZEN, ("版の歩みの表の why の字か changed が替わった（のこすの直った例は替えない）", got)
kinds = [w.get("kind") for t in table["toys"] for v in t["versions"] for w in v.get("why", [])]
assert kinds.count(NEW) == 2, ("表の kind の呼び名", kinds.count(NEW))
print("ok 呼び名はワークショップの型紙レビューにそろい、エンジンと同じで、版の歩みの表の why の字と changed は替わっていない")
