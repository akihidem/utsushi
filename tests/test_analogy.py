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
# 順路: たとえは型紙の窓のすぐ前に、畳まずに出す。本人の言葉 11-08「つくるのページ、これまでの復元、仮説、組み立てを立体で見る、たとえと関連する事柄、
# 型紙の順で」（前は本人の答え 11-07 夕の Q4「型紙の窓の近くへ戻す」で窓のすぐ後。型紙の近くは変わらない）。前は頁の足の畳み（段 0）
# 本人の言葉 11-08（477）「原図をみて、狂歌を読んで、仮説、たとえ、3D をみたあとに型紙の印刷にすすむ。」で 仮説 → たとえ → 立体 → 型紙の窓 の順になった
# （前は 394 の これまでの復元 → 立体 → 仮説 → たとえ → 型紙。これまでの復元 は もちよる へ移り頁に無い）
assert after.index('id="kasetsu-fuda"') < after.index('id="tatoe"') < after.index('id="kasetsu"') < after.index('id="win"') and 'id="minna"' not in after
assert '<section class="sec" id="tatoe"><h2>たとえと、関連する事柄</h2>' in after, "畳まずに出す"
for w in BAD:
    assert w not in after.split('id="tatoe"')[1].split("</section>")[0], w
print("ok: たとえ", len(sids))
