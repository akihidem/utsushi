"""もちよる（/gallery）の玩具ごとの錨と札（本人の言葉 11-08 477「…復元の記録などはすべてもちよるに統合する。…」と、本人の言葉 11-08「みんなが作った
おもちゃの方は、おもちゃの名前と写真が合っていない。ワークショップで作られたものの方は写真と名前が一致しているので、こちらの組み合わせと表示を採用して、
みんなが作ったおもちゃの方に置く。」）。「みんながつくったおもちゃ」の札は作例の記録の札（名と写真が結ばれた本人の写真）で、玩具ごとの最初の札が
錨 id="toy-<印>" を持つ。玩具の頁にだけあった事例の写真（改善ループの例・3 バージョン）も、その玩具の札として並ぶ。

見る事:
1. 錨は玩具ごとに頁に 1 つで、みんながつくったおもちゃ のその玩具の最初の札 → 無ければ 他の人が作った物 の最初の札 に付く（作例の節は錨を持たない）。
   どれも無い玩具と 83 の外の玩具には無い。techo_site.toy_place が同じ線で道を返す（無ければ None）
2. 作例の写真・事例の写真・感想と言葉は、その玩具の札の中。試行の写真の表の組（名と写真が合っていなかった）は札に出さない
3. もちよるの頁の全体で、同じ写真の道が 2 度出ない
4. 作例の節には顔の写真と工夫だけが残る。83 の外の玩具の作例の札は みんながつくったおもちゃ の後ろに、棚卸しの名で道なし。札の字と錨に記録の番号を出さない
5. 合言葉なしの公開の場でも同じ。写真を出さない前の開いた場の形（photos=False）は、事例と作例の写真を出さない
6. 記録の札の玩具の名の道は、玩具の頁の記録（#R-…）でなく、もちよるの中のその玩具の錨（#toy-<印>）へ向く
"""
import io
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import hypotheses, media_review, records  # noqa: E402
from web import demo_samples, made, sakurei, techo_site, toy, workshop  # noqa: E402
from web.play_server import sources  # noqa: E402

tmp = tempfile.mkdtemp()
G, T, KAZA = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R", "NDL-1187053-R0000020-R"
DEN = "NDL-1187053-R0000007-R"  # 作例だけがある玩具（試行の写真も感想も無い）
REC = "NDL-1187053-R0000009-L"  # 人の記録だけがある玩具
CAT = "NDL-1187053-R0000025-R"  # 83 の外の玩具（猫と鼠の箱）


def photo(name, n):
    path = os.path.join(tmp, name)
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (n * 20 % 255, 80, 160)).save(buf, "JPEG")
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return path


def add(sid, n, kind=None, sheet_set=None, shows="object"):
    (rid, name, _), = sakurei.add([photo(f"p{n}.jpg", n)], sid, "2026-11-07", sheet_set=sheet_set, kind=kind)[0]
    assert media_review.record(rid, name, shows, "確認者") == []
    return f"/record/{rid}/media/{name}/small"


made_g = add(G, 1, sheet_set="goraigo-v10")
made_t = add(T, 2)
versions_t = add(T, 3, kind="versions")
loop_g = add(G, 4, kind="loop")
versions_g = add(G, 10, kind="versions")
made_den = add(DEN, 5)
made_cat = add(CAT, 6)
kufu_cat = add(CAT, 7, kind="kufu")
face = add(records.WORKSHOP_ALL, 8)
people = add(T, 9, shows="people")  # 人が入る写真は出ない
rid, fails = records.add({"source_id": REC, "hypothesis_id": hypotheses.sheet_of(REC)["id"], "sheet_version": 1, "result": records.UNSURE,
                          "impression": "筒の口が開いた"})
assert rid and not fails, fails
CASES = {G: [loop_g, versions_g], T: [versions_t]}


def name_of(sid):
    t = hypotheses.load(sid)["toy"]
    return t if isinstance(t, str) else t["name"]


def esc(t):
    return techo_site.esc(t)


def section(page, sec_id):
    return page.split(f'id="{sec_id}"', 1)[1].split("</section>", 1)[0] if f'id="{sec_id}"' in page else ""


def cards_of(page, sid):
    """みんながつくったおもちゃ の、その玩具の札（figure.workshop・玩具の頁への道を持つ物）の中身を全部つないだ物。"""
    dk = section(page, "dekita")
    return "".join(m for m in re.findall(r'<figure class="workshop"(?: id="toy-[^"]+")?>((?:(?!</figure>).)*?)</figure>', dk, re.S)
                   if f'<a href="/toy/{sid}">' in m)


def first_card(page, sid):
    head = f'<figure class="workshop" id="toy-{sid}">'
    return page.split(head, 1)[1].split("</figure>", 1)[0] if head in page else None


for public in (False, True):
    page = techo_site.gallery_page(sources(), public=public)
    dekita, sak, ageta = section(page, "dekita"), section(page, "sakurei"), section(page, "ageta")
    # 1. 錨は今の札に 1 つ・付く所の順・toy_place（作例の札は みんながつくったおもちゃ に移ったので、作例の節は錨を持たない）
    for sid in sources():
        n = page.count(f'id="toy-{sid}"')
        where = "dekita" if f'id="toy-{sid}"' in dekita else "ageta" if f'id="toy-{sid}"' in ageta else None
        if workshop.has_card(sid):
            want = "dekita"
        elif sid == REC and not public:  # 公開の場では、人が確かめていない字の記録の札は出ない
            want = "ageta"
        else:
            want = None
        assert (n, where) == ((1, want) if want else (0, None)), (sid, public, n, where, want)
        assert techo_site.toy_place(sid, public=public) == (f"/gallery#toy-{sid}" if want else None), (sid, public)
    assert f'id="toy-{CAT}"' not in page, "83 の外の玩具は玩具の頁が無いので錨を持たない"
    # 2. 作例の写真・事例の写真・感想と言葉は、その玩具の札の中（玩具の頁から外した物が もちよる に全部ある）。名と写真は作例の記録の組のまま
    for sid in (G, T, DEN, KAZA):
        mine = cards_of(page, sid)
        urls = [f"/record/{e['rid']}/media/{f}/small" for e in sakurei.examples() if e["sid"] == sid for f in e["photos"]] + CASES.get(sid, [])
        for url in urls:
            assert f'src="{url}"' in mine, (sid, url, "作例と事例の写真は、その玩具の札の中")
        assert made.photo(sid) is None or f'src="{made.photo(sid)}"' in page, (sid, "原画の横の実物の写真")
        name = name_of(sid)
        texts = [t for v in demo_samples.VOICES if demo_samples.VOICE_TOYS.get(v["toy"]) == sid for _, t in v["fields"]]
        texts += [s["text"] for s in demo_samples.SPOKEN if s["toy"] == name]
        c = first_card(page, sid)
        assert all(esc(t) in (c or "") for t in texts), (sid, "感想と言葉は、その玩具の最初の札の中")
        assert "/workshop/" not in mine, (sid, "試行の写真の表の組（名と写真が合っていなかった）を札に出さない")
    assert people not in page, "人が入る写真は出ない"
    # 3. 同じ写真の道が 2 度出ない
    srcs = re.findall(r'src="(/(?:workshop|record)/[^"]+)"', page)
    dup = sorted({u for u in srcs if srcs.count(u) > 1})
    assert not dup, (public, dup[:5], "同じ写真を 2 度出さない")
    # 4. 作例の節には顔の写真と工夫だけが残り、玩具ごとの作例の札（83 の外の玩具も）は みんながつくったおもちゃ へ移った
    assert all(f'src="{u}"' in sak for u in (kufu_cat, face)), "工夫・顔の写真は作例の節に残る"
    assert not any(f'src="{u}"' in sak for u in (made_g, made_t, made_den, made_cat, loop_g, versions_g, versions_t)), "作例と事例の札は作例の節に出さない"
    assert all(f'src="{u}"' in dekita for u in (made_g, made_t, made_den, made_cat, loop_g, versions_g, versions_t)), "作例と事例の札は みんながつくったおもちゃ"
    assert "猫と鼠の箱" in dekita and f'<a href="/toy/{CAT}">' not in page, "83 の外の玩具は棚卸しの名で、道を付けない"
    assert not re.search(r"R-\d{4}", re.sub(r"<[^>]+>", " ", dekita + sak)), "札の字に記録の番号を出さない"
    assert not re.search(r'id="toy-R-', page), "錨に記録の番号を入れない"
    # 記録の札の玩具の名の道は、玩具の頁の記録（#R-…）でなく、もちよるの中のその玩具の錨へ（統括の決め 11-08）
    assert not re.search(r'href="/toy/[^"#]+#R-\d', page), "無くなる玩具の頁の記録の札へ向けない"
    if not public:
        assert f'href="#toy-{REC}"' in ageta and f'id="toy-{REC}"' in ageta, "記録だけの玩具の札は、その玩具の錨（この札）へ向く"
    # 型紙の版の札（作例の節の札の形のまま）
    assert "型紙の版 10" in cards_of(page, G), "刷った組が分かる作例は型紙の版の札を付ける"
# 5 の続き: 写真を出さない前の開いた場の形（photos=False）
old = techo_site.gallery_page(sources(), photos=False)
assert "/record/" not in old, "photos=False の場は事例と作例の写真を出さない"
assert f'id="toy-{G}"' in old and f'id="toy-{DEN}"' not in old, "感想の玩具は札と錨を持ち、作例だけの玩具は持たない（写真を出さない場）"
print("ok もちよるの玩具ごとの錨: 今の札に 1 つ・玩具の頁の写真と感想は全部もちよるに・事例の写真は玩具の札へ・同じ写真を 2 度出さない・作例の節は今のまま・公開の場も同じ")
