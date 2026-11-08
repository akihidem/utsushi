"""もちよるの頁（/gallery）の、頭の並べた写真 1 枚と、みんながつくったおもちゃ・つくっている様子の敷き詰めと、職人の言葉の節（本人の言葉 11-08）。

本人の言葉: 「もちよる、ワークショップの様子、として作っている様子をあげるのと、できたおもちゃはギャラリーの形で並べる。感想も見れるように」
「職人の言葉、はもちよるに移動」「冒頭におもちゃが並べてある写真一枚。みんながつくったおもちゃに、おもちゃの単体の写真。つくっている様子に、ワークショップの様子。日付毎にしなくていい。」。
見る線:
- 写真の分けの表（data/workshop_photo_kinds.json）は、各日の review.md の「写っている物」の字のままで、43 枚から p28 だけを外した 42 枚
- 様子の節は作っている途中の写真だけ、できたおもちゃの節はできた物の写真だけ。同じ写真を 2 つの節に出さない
- 玩具の札の写真は、写真 → 玩具の表（data/workshop_photos.json）でその玩具に結ばれた、できた物の写真。札の感想は声の担当の札（workshop_for）のまま
- 頁の並び: 様子 → できたおもちゃ → 他の人が作った物 → 職人の言葉。前の「他の人が作った物」の中の写真の札（workshop.gallery）は出さない
- 合言葉なしの場でも 2 つの節は出る（公開の決めが済んだ写真）
- 職人の言葉の節は もちよる にあり、序の頁には無い。寄せられた声は序の頁のまま
- 新しい字 4 つは英語の表とやさしい日本語の表にある
"""
import json
import os
import pathlib
import re
import sys
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from omochae import hypotheses  # noqa: E402
from web import about, demo_samples, i18n, techo_site, workshop  # noqa: E402
from web.play_server import sources  # noqa: E402

SIDS = list(sources())

# 写真の分けの表
kinds = json.loads(workshop.KINDS.read_text(encoding="utf-8"))["photos"]
seen = {}
for day in ("20261104", "20261106"):
    for ln in (ROOT / "docs/process/trials/photos" / day / "review.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| (p\d{2}\.jpg) \| ([^|]+?) \|", ln)
        if m:
            seen[f"{day}/{m.group(1)}"] = m.group(2).strip()
assert len(seen) == 43 and len(kinds) == 42, (len(seen), len(kinds))
assert {r["file"] for r in kinds} == set(seen) - {"20261106/p28.jpg"}, "p28 だけを外す（他社の AI の対話の画面が写る・統括の決め 11-08）"
# 分けは本人の言葉（11-08）の 3 つ（並べた・単体・様子）と、どれにも入らない物
# body は 11-08 本人の言葉「ワークショップの様子は、みんなの手元の写真だけで良い。」で、手元のほかに人の体が大きく写る写真（出さない）
assert all(r["kind"] in ("lineup", "single", "making", "none", "body") and r["seen"] == seen[r["file"]] for r in kinds), "写っている物の字のまま・分けは 3 つと none と body"
body = [r["file"] for r in kinds if r["kind"] == "body"]
assert body and all(r.get("why") for r in kinds if r["kind"] == "body"), "体が写る写真は、どこが写るかを書いて外す"
# 人が 1 枚ずつ見て「手元のほかに体が大きく写る」と決めた 11 枚（11-08・#666 の 9 枚に、別の目の照らしと統括の決めで 3 枚を足し、
# ほぼ手元の 20261106/p24 を戻した）。決めを変えずに様子の節へ戻さない・外さないための見張り（替えるなら、表と一緒にここも直す）
BODY = {"20261104/p02.jpg", "20261104/p03.jpg", "20261104/p05.jpg", "20261104/p08.jpg", "20261106/p02.jpg", "20261106/p03.jpg",
        "20261106/p04.jpg", "20261106/p14.jpg", "20261106/p17.jpg", "20261106/p18.jpg", "20261106/p29.jpg"}
assert set(body) == BODY, ("体が写ると決めた写真と表が合わない", sorted(set(body) ^ BODY))
none = [r["file"] for r in kinds if r["kind"] == "none"]
lineup = [r["file"] for r in kinds if r["kind"] == "lineup"]
assert all((workshop.PHOTOS / r["file"]).exists() for r in kinds)

# 様子の節
scene = workshop.scene()
shown = re.findall(r'src="/workshop/([^"]+)/small"', scene)
assert scene.count('id="yousu"') == 1 and f'<h2 class="mark">{workshop.SCENE_HEAD}</h2>' in scene
assert shown and all(workshop.kind_of(f) == "making" for f in shown) and len(shown) == sum(r["kind"] == "making" for r in kinds), shown
assert scene.count(f'alt="{workshop.SCENE_ALT}"') == len(shown)

# 頭の 1 枚（おもちゃが並べてある写真）
top = workshop.top()
assert workshop.TOP in lineup and re.findall(r'src="/workshop/([^"]+)/small"', top) == [workshop.TOP] and f'alt="{workshop.TOP_ALT}"' in top
# みんながつくったおもちゃの節（おもちゃの単体の写真）
made = workshop.made(SIDS)
pics = re.findall(r'src="/workshop/([^"]+)/small"', made)
assert made.count('id="dekita"') == 1 and f'<h2 class="mark">{workshop.MADE_HEAD}</h2>' in made
# 本人の言葉 11-08「みんなが作ったおもちゃの方は、おもちゃの名前と写真が合っていない。ワークショップで作られたものの方は写真と名前が一致しているので、こちらの組み合わせと表示を採用して、みんなが作ったおもちゃの方に置く。」
# 試行の写真の表の単体の写真を玩具に結んだ組（名と写真が合っていなかった）は使わない。札は作例の記録の札（この試験の場には作例が無い）
assert not pics, ("みんながつくったおもちゃに、試行の写真の表の組を出さない", pics)
# 様子の写真（making）は全部、つくっている様子に 1 回ずつ出る。並べた写真は頭の 1 枚だけで、どれにも入らない写真と体が写る写真は出さない
assert sorted(shown) == sorted(r["file"] for r in kinds if r["kind"] == "making") and len(shown) == len(set(shown)), "様子の写真で、どこにも出ない写真か 2 回出る写真がある"
assert not (set(none) | set(body)) & set(shown) and not (set(lineup) - {workshop.TOP}) & set(shown)
assert not any(workshop.known(f) for f in none) and not workshop.known("20261106/p28.jpg"), "出さない写真は道でも返さない"
by_toy = {r["file"]: r["toy"] for r in workshop.rows()}
order = []
for sid in SIDS:
    name = hypotheses.load(sid)["toy"]
    # 玩具ごとの札は錨 id="toy-<印>" を持つ（本人の言葉 11-08 477・つくるの作り直しの枝 2）。錨の有無で札の見分けを替えない
    card = re.search(r'<figure class="workshop"(?: id="toy-[^"]+")?>((?:(?!</figure>).)*?<a href="/toy/' + re.escape(sid) + r'">.*?)</figure>', made, re.S)
    voices = demo_samples.workshop_for(sid, name)
    if not voices:  # この試験の場には作例が無いので、札は感想か言葉のある玩具だけ
        assert not card, ("札の要らない玩具に札", sid)
        continue
    assert card, ("札が無い", sid)
    order.append(made.index(f'<a href="/toy/{sid}">'))
    body = card.group(1)
    got = re.findall(r'src="/workshop/([^"]+)/small"', body)
    assert got == [], (sid, got, "試行の写真の表の組を札に出さない")
    if voices:
        assert f"<summary>{workshop.OPEN_VOICES}</summary>{voices}</details>" in body, ("感想は声の担当の札のまま", sid)
    else:
        assert "<details" not in body, sid
assert order == sorted(order), "玩具の札は頁の玩具の並びの順"
# 名前や記録の番号を出さない（感想は回答のまま・名前なし。本人の決め 11-07「寄せられた声…名前や番号なし」）
assert not re.search(r"R-\d{4}", made)

# 頁の並びと、前の写真の札が残っていない事
g = techo_site.gallery_page(SIDS)
# 並び: 頭の 1 枚 → みんながつくったおもちゃ → つくっている様子 → 他の人が作った物 → 職人の言葉（本人の言葉 11-08 の順）
ORDER = ("narabe", "dekita", "yousu", "ageta", "shokunin")
at = [g.index(f'id="{x}"') for x in ORDER]
assert at == sorted(at) and all(g.count(f'id="{x}"') == 1 for x in ORDER), at
ageta = g[g.index('id="ageta"'):g.index('id="shokunin"')]
assert "/workshop/" not in ageta, "他の人が作った物の中に、前の写真の札（workshop.gallery）が残っている"
# 合言葉なしの場でも 2 つの節は出る
pub = techo_site.gallery_page(SIDS, photos=False, public=True)
assert 'id="yousu"' in pub and 'id="dekita"' in pub and 'id="narabe"' in pub

# 職人の言葉は もちよる、寄せられた声は序の頁
yomu = about.page("tenji")
assert 'id="shokunin"' not in yomu and 'id="yose"' in yomu
assert '<h2 class="mark">職人の言葉</h2>' in g and demo_samples.craft_html() in g, "職人の言葉の節の中身は craft_html のまま"

# 新しい字の英語とやさしい日本語
en, easy = i18n.table("en"), i18n.table("easy")
for t in (workshop.SCENE_HEAD, workshop.MADE_HEAD, workshop.SCENE_ALT, workshop.TOP_ALT, workshop.OPEN_VOICES):
    assert t in en and t in easy, t
    assert not re.findall(r"[一-龥々]", i18n.RUBY.sub("", easy[t])), ("ルビの無い漢字", t)
print(f"ok もちよる: 様子 {len(shown)} 枚・できたおもちゃ {made.count('<figure')} 枚の札・職人の言葉は もちよる")
