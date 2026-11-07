"""デモ用の見本（本人の指示、11-04）。ギャラリーに上げた物と職人の言葉（フォームの情報提供）の見本が、作り物と分かる札付きで出る。
寄せられた声は 11-07 夜から見本でなく、ワークショップの参加者の実際の感想（18 件のうち本人が見送ると決めた 1 件を除く 17 件・1 件 1 枚の札）。
本物の記録の置き場には書かない。OMOCHAE_SAMPLES=0 で消える。"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import records  # noqa: E402
from web import demo_samples, techo_site  # noqa: E402
from web.play_server import sources  # noqa: E402
# ワークショップの試行の写真（web.workshop・repo に在る）は、ここが見る「本物の記録が無い時」の形を変えるので、この試験では表を空にする
# （写真が出る形は tests/test_workshop_gallery.py が見る。本人の見直し 11-07 夜の ②⑦）
from web import workshop as _workshop  # noqa: E402

_workshop.TABLE = _workshop.TABLE.with_name("no-such-workshop-photos.json")

# 上げた物の見本はギャラリーに、職人の言葉と寄せられた声の見本は序の頁の節（voices_sections）に出る
# （職人の言葉と寄せる話の入口を序の頁へ移した。本人のサイト体験レビュー 11-07 の言葉 6、直しの設計の D）
gallery, voices = techo_site.gallery_page(sources()), techo_site.voices_sections()
assert gallery.count('class="item is-sample"') == 0, "上げた物の見本（作り物）は外した（本人の言葉 11-08「見本の記録をワークショップのデータで作成して欲しい。」）"
assert voices.count('class="item is-sample"') == len(demo_samples.CONTRIBUTIONS), "職人の言葉の見本が序の頁の節に出る"
html = gallery + voices
assert html.count('class="item is-sample"') == len(demo_samples.CONTRIBUTIONS), "見本は職人の言葉だけ"
# 寄せられた声は見本でなく、11 月のワークショップの参加者の実際の感想（本人の言葉 11-07 夜「とりあえず感想は全て反映させたい」）。
# 1 件 1 枚の札で、見本の札は付けない。字は回答のまま。名前・番号・回（A/B）は出さない。抜き出した事と名前を外した事の一文が先頭
yose = voices[voices.index('id="yose"'):voices.index('id="shokunin"')]
assert len(demo_samples.VOICES) == 17 and all(v["toy"] and v["fields"] for v in demo_samples.VOICES)
assert '<span class="sample">見本</span>' not in yose and demo_samples.VOICES_NOTE in yose, "寄せられた声は見本の札でなく、抜き出した一文"
assert yose.count('<div class="item">') == len(demo_samples.VOICES) + len(demo_samples.SPOKEN), "感想 1 件 1 枚と、話された言葉 1 か所 1 枚"
import html as _h  # noqa: E402
for v in demo_samples.VOICES:
    assert all(_h.escape(t) in yose for _, t in v["fields"]), v["toy"]
    assert all(t not in ("", "なし", "特になし") for _, t in v["fields"]), "空や「なし」の欄は出さない"
assert demo_samples.VOICES_WHO in yose and not any(x in yose for x in ("回: A", "回: B", "（A）", "（B）")), "名前・回を出さない"
# 話された言葉（本人の言葉 11-07 夜: 62 分の音源の言葉は「載せてよい」、レビューは「話した人に了承を得ているので大丈夫です」）。
# 1 か所 1 枚の札で、字は話したまま。話し手の名は出さず、出所の札だけを付ける（本人の言葉 11-08「全てがワークショップです。」で札は 1 つ）
from omochae import contrib  # noqa: E402
assert {s["where"] for s in demo_samples.SPOKEN} == {"workshop", "review"} and len(demo_samples.SPOKEN) == 30, len(demo_samples.SPOKEN)
assert sum(s["where"] == "workshop" for s in demo_samples.SPOKEN) == 8 and sum(s["where"] == "review" for s in demo_samples.SPOKEN) == 22
assert demo_samples.SPOKEN_NOTE in yose and yose.count(demo_samples.SPOKEN_WHO) == len(demo_samples.SPOKEN), "30 枚とも同じ出所の札（本人の言葉「全てがワークショップです。」）と、抜き出した事の一文"
assert "レビューで話された言葉" not in yose, "レビューを別の札にしない"
for s in demo_samples.SPOKEN:
    assert s["text"].strip() and _h.escape(s["text"]) in yose, s["text"][:20]
    assert s["toy"] is None or _h.escape(s["toy"]) in yose
    # 名乗り・連絡先の形が無い（持ち寄りの入口と同じ見張り）。話し手の名は字に入れない
    assert not contrib.check_pii({"body": s["text"]}), s["text"][:20]
assert '<span class="sample">見本</span>' not in yose, "話された言葉も見本の札でない"
# 作り物である事の一文（NOTE）は、上げた物の見本と一緒に外した。残る職人の言葉の見本は、札ごとに見本の札と（架空）の名で見分ける
assert all(demo_samples.esc(c["who"]) in html for c in demo_samples.CONTRIBUTIONS if c.get("slot")), "職人の言葉の見本は、名に（架空）を付けて出す"
# どの見本の枠にも札がある（本物と取り違えない）
for chunk in html.split('class="item is-sample"')[1:]:
    assert chunk.split("</div>")[0].count('<span class="sample">見本</span>') == 1, chunk[:80]
assert "まだ作った物の記録はありません" in html, "本物が無い事は見本があっても隠さない"
assert "（準備中）" not in html, "職人の言葉の 3 枠に見本が入る"
assert all("架空" in c["who"] for c in demo_samples.CONTRIBUTIONS), "職人の言葉の見本の人の名前は架空と書く"
for sid in sources():
    assert records.all_records(sid) == [], "見本を記録の置き場に書かない"

os.environ["OMOCHAE_SAMPLES"] = "0"
off = techo_site.gallery_page(sources()) + techo_site.voices_sections()
assert "is-sample" not in off and off.count("（準備中）") == 3, "本番では見本を消せる"
assert demo_samples.VOICES_NOTE in off, "寄せられた声は見本でないので、見本を消しても出る"
print("ok")
