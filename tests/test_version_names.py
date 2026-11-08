"""作る側の頁の版の札で、同じ玩具の 2 つ以上の仮説に版がある時は、仮説の名で見分ける（統括の割り振り 11-08）。

なぜ: 本人の答え（11-08）「そろえる。」で仮説の印（A・C）を外した。同じ玩具の 2 つ以上の仮説に版がある時、どれも「仮説 版 2」になって
見分けられない（別の目の気づき）。11-08 に調べた記録の置き場（手元・公開デモの白と暗い版・1 枚の型紙のデモ）には、版の記録が 1 つも無い。
無くても、版が並んだ時の形をここで固める。

見る事（改善の輪 kaizen.section と、版の歩み ayumi.toy_block の両方）:
1. 版がある仮説が 2 つの時: 札の題は「仮説「名」 版 N」で、2 つの題が違う。印（仮説 A 版 N の形）も、名の無い「仮説 版 N」も無い
2. 版がある仮説が 1 つの時: 札の題は「仮説 版 N」（名を添えない）
"""
import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, loop  # noqa: E402
from web import ayumi, kaizen  # noqa: E402

G = "NDL-1187053-R0000005-L"  # 御来迎（仮説が A〜E）
data = hypotheses.load(G)
two = [h for h in data["hypotheses"] if h.get("params")][:2]
assert len(two) == 2 and two[0]["name"] != two[1]["name"], [h["id"] for h in two]
MARK = re.compile(r"仮説 [A-Z] 版 \d")


def put(h, n=2):
    path = loop.folder() / f"version-{G}-{h['id']}-{n}.json"
    path.write_text(json.dumps({"source_id": G, "hypothesis_id": h["id"], "version": n, "params": dict(h["params"]), "changes": [], "record_ids": []},
                               ensure_ascii=False), encoding="utf-8")
    return path


def heads(html):
    text = re.sub(r"<[^>]+>", " ", html)
    return re.findall(r"仮説(?:「[^」]+」)? 版 \d", text), text


# 1. 2 つの仮説に版がある
paths = [put(h) for h in two]
for where, html in (("改善の輪", kaizen.section(G, data, [])), ("版の歩み", ayumi.toy_block(G, data))):
    got, text = heads(html)
    want = sorted(f"{hypotheses.shown_name(h)} 版 2" for h in two)
    assert sorted(got) == want, (where, got, want)
    assert not MARK.search(text) and "仮説 版 2" not in text, (where, "印か名の無い題が残る")
# 2. 1 つの仮説だけに版がある
paths[1].unlink()
for where, html in (("改善の輪", kaizen.section(G, data, [])), ("版の歩み", ayumi.toy_block(G, data))):
    got, _ = heads(html)
    assert got == ["仮説 版 2"], (where, got)
print("ok 作る側の頁の版の札: 2 つ以上の仮説に版がある時は仮説の名で分け、1 つの時は「仮説 版 N」（改善の輪・版の歩み）")
