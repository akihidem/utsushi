"""全部の玩具に「たとえと、関連する事柄」がある（本人の頼み 11-05）。通信はしない。

なぜ: 本人が御来迎の扇を開く話を気に入り、同じ形で身近な物へのたとえと関連する事柄を全部の玩具に求めた。
文は作る側の言葉なので、印（作る側のたとえ）と「答えではない」の断りを付ける。
成績の言葉（成功・失敗・正解・順位）は入れない（J-025、philosophy.md）。仮説の名前の丸写しもしない（たとえは仕組みの手がかりで、仮説の言い換えではない）。
"""
import json
import os
import pathlib
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402
from web import toy  # noqa: E402

BAD = ("成功", "失敗", "正解", "不正解", "順位", "点数", "答えは")
sids = sorted(p.stem for p in (ROOT / "data/hypotheses").glob("NDL-*.json"))
assert len(sids) >= 3
missing = []
for sid in sids:
    d = json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8"))
    a = d.get("analogy")
    if not a:
        missing.append(sid)
        continue
    like, rel, by = a["like"], a["related"], a["written_by"]
    assert isinstance(like, str) and 30 <= len(like) <= 220, (sid, len(like))
    assert isinstance(rel, list) and 2 <= len(rel) <= 5 and all(isinstance(x, str) and 8 <= len(x) <= 120 for x in rel), (sid, rel)
    assert "人の確認はまだ" in by, (sid, by)
    text = like + "".join(rel)
    for w in BAD:
        assert w not in text, (sid, w)
    assert "\n" not in text, sid
assert not missing, ("たとえが無い玩具", len(missing), missing[:10])

# 頁: 印と断り付きで出る
sid = "NDL-1187053-R0000005-L"
after = toy.toy_page(sid)
a = json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8"))["analogy"]
assert "作る側のたとえ" in after and "答えではありません" in after and a["like"] in after and a["related"][0] in after
# 順路: 仮説 → たとえ → 型紙の窓
assert after.index('id="kasetsu"') < after.index('id="tatoe"') < after.index('id="win"')
for w in BAD:
    assert w not in after.split('id="tatoe"')[1].split('id="win"')[0], w
print("ok: たとえ", len(sids))
