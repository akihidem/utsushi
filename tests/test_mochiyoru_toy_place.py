"""もちよる（/gallery）の玩具ごとの錨（本人の言葉 11-08 477「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などはすべてもちよるに統合する。…」）。
つくるの作り直しの枝 2（声の担当）。玩具の頁から外す中身（頭の「これまでの記録」の畳み・「これまでの復元」・原画の横の作ってみた実物の写真・
感想と型紙レビューの言葉）は、もちよるの今の札にもうある（感想は みんながつくったおもちゃ の札の 感想を見る・作例の写真は作例の節の札・
人の記録は 他の人が作った物）。新しい置き場は足さず、今の札に錨 id="toy-<印>" を 1 つ付ける（統括の決め 11-08）。玩具の頁にだけあった
事例の写真（改善ループの例・本人の言葉 193 と、3 バージョン）は、その玩具の みんながつくったおもちゃ の札に寄せる。玩具の頁から外すのは枝 1（修正の担当 d）。

見る事:
1. 錨は玩具ごとに頁に 1 つで、みんながつくったおもちゃ の札 → 無ければ作例の節の最初の札 → 無ければ 他の人が作った物 の最初の札 に付く。
   どれも無い玩具と 83 の外の玩具には無い。techo_site.toy_place が同じ線で道を返す（無ければ None）
2. 玩具の頁の「これまでの復元」と頭の畳みと原画の横に出ていた写真・感想・言葉が、もちよるに全部ある（枝 1 が玩具の頁から外しても消えない）。
   事例の写真（改善ループの例・3 バージョン）はその玩具の みんながつくったおもちゃ の札の中
3. もちよるの頁の全体で、同じ写真の道が 2 度出ない
4. 作例の節は今のまま（83 の玩具の札・83 の外の玩具の札・顔の写真・工夫）。札の中に記録の番号の字を出さない
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


def card(page, sid):
    """錨の付いた札（みんながつくったおもちゃ の figure）の中身。"""
    head = f'<figure class="workshop" id="toy-{sid}">'
    return page.split(head, 1)[1].split("</figure>", 1)[0] if head in page else None


for public in (False, True):
    page = techo_site.gallery_page(sources(), public=public)
    dekita, sak, ageta = section(page, "dekita"), section(page, "sakurei"), section(page, "ageta")
    # 1. 錨は今の札に 1 つ・付く所の順・toy_place
    for sid in sources():
        n = page.count(f'id="toy-{sid}"')
        where = ("dekita" if f'id="toy-{sid}"' in dekita else "sakurei" if f'id="toy-{sid}"' in sak else "ageta" if f'id="toy-{sid}"' in ageta else None)
        if workshop.has_card(sid):
            want = "dekita"
        elif any(e["sid"] == sid for e in sakurei.examples()):
            want = "sakurei"
        elif sid == REC and not public:  # 公開の場では、人が確かめていない字の記録の札は出ない
            want = "ageta"
        else:
            want = None
        assert (n, where) == ((1, want) if want else (0, None)), (sid, public, n, where, want)
        assert techo_site.toy_place(sid, public=public) == (f"/gallery#toy-{sid}" if want else None), (sid, public)
    assert f'id="toy-{CAT}"' not in page, "83 の外の玩具は玩具の頁が無いので錨を持たない"
    # 2. 玩具の頁に出ていた物が、もちよるに全部ある
    for sid in (G, T, DEN, KAZA):
        tp = toy.toy_page(sid)
        minna = tp.split('id="minna"', 1)[1].split("</section>", 1)[0]
        hero = tp.split('<section class="hero">', 1)[1].split("</section>", 1)[0]
        urls = re.findall(r'src="(/(?:workshop|record)/[^"]+)"', minna + hero)
        assert urls, (sid, "玩具の頁に写真がある前提")
        for url in urls:
            assert f'src="{url}"' in page, (sid, url, "玩具の頁の写真が、もちよるに無い")
        assert made.photo(sid) is None or f'src="{made.photo(sid)}"' in page, (sid, "原画の横の実物の写真")
        name = name_of(sid)
        texts = [t for v in demo_samples.VOICES if demo_samples.VOICE_TOYS.get(v["toy"]) == sid for _, t in v["fields"]]
        texts += [s["text"] for s in demo_samples.SPOKEN if s["toy"] == name]
        c = card(page, sid)
        assert all(esc(t) in (c or "") for t in texts), (sid, "感想と言葉は みんながつくったおもちゃ の札の中")
        for url in CASES.get(sid, []):
            assert c is not None and f'src="{url}"' in c, (sid, url, "事例の写真はその玩具の みんながつくったおもちゃ の札の中")
    assert people not in page, "人が入る写真は出ない"
    # 3. 同じ写真の道が 2 度出ない
    srcs = re.findall(r'src="(/(?:workshop|record)/[^"]+)"', page)
    dup = sorted({u for u in srcs if srcs.count(u) > 1})
    assert not dup, (public, dup[:5], "同じ写真を 2 度出さない")
    # 4. 作例の節は今のまま。札の字に記録の番号を出さない。錨と道に記録の番号を入れない
    assert all(f'src="{u}"' in sak for u in (made_g, made_t, made_den, made_cat, kufu_cat, face)), "作例の節の札・83 の外・工夫・顔の写真は今のまま"
    assert not any(f'src="{u}"' in sak for u in (loop_g, versions_g, versions_t)), "事例の写真は玩具の札へ（作例の節に 2 度出さない）"
    assert not re.search(r"R-\d{4}", re.sub(r"<[^>]+>", " ", dekita + sak)), "札の字に記録の番号を出さない"
    assert not re.search(r'id="toy-R-', page), "錨に記録の番号を入れない"
    # 記録の札の玩具の名の道は、玩具の頁の記録（#R-…・玩具の頁から無くなる）でなく、もちよるの中のその玩具の錨へ（統括の決め 11-08）
    assert not re.search(r'href="/toy/[^"#]+#R-\d', page), "無くなる玩具の頁の記録の札へ向けない"
    if not public:
        assert f'href="#toy-{REC}"' in ageta and f'id="toy-{REC}"' in ageta, "記録だけの玩具の札は、その玩具の錨（この札）へ向く"
# 5 の続き: 写真を出さない前の開いた場の形（photos=False）
old = techo_site.gallery_page(sources(), photos=False)
assert "/record/" not in old, "photos=False の場は事例と作例の写真を出さない"
assert f'id="toy-{G}"' in old and f'id="toy-{DEN}"' not in old, "試行の写真か感想の玩具は札と錨を持ち、作例だけの玩具は持たない"
print("ok もちよるの玩具ごとの錨: 今の札に 1 つ・玩具の頁の写真と感想は全部もちよるに・事例の写真は玩具の札へ・同じ写真を 2 度出さない・作例の節は今のまま・公開の場も同じ")
