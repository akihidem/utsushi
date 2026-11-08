"""寄せられた声と職人の言葉（序の頁の節）。見本（作り物）は 11-08 に全部外した（上げた物の見本・職人の言葉の見本）。
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

# 見本は全部外した（上げた物の見本: 本人の言葉 11-08「見本の記録をワークショップのデータで作成して欲しい。」。
# 職人の言葉の見本: 本人の言葉 11-08「改善のために撮影し上た型紙レビュー10本は職人の言葉です。見本と取り替えて、もちよる、に掲載してください。」）
gallery, voices = techo_site.gallery_page(sources()), techo_site.voices_sections()
html = gallery + voices
assert 'class="item is-sample"' not in html and '<span class="sample">見本</span>' not in html and demo_samples.NOTE not in html, "見本と作り物の一文は出ない"
assert not hasattr(demo_samples, "CONTRIBUTIONS") and not hasattr(demo_samples, "UPLOADS"), "作り物を残さない"
# 寄せられた声は、11 月のワークショップの参加者の実際の感想（本人の言葉 11-07 夜「とりあえず感想は全て反映させたい」）と、ワークショップの場で話された言葉。
# 1 件 1 枚の札で、見本の札は付けない。字は回答のまま。名前・番号・回（A/B）は出さない。抜き出した事と名前を外した事の一文が先頭
yose = voices[voices.index('id="yose"'):voices.index('id="shokunin"')]
craft = voices[voices.index('id="shokunin"'):]
assert len(demo_samples.VOICES) == 17 and all(v["toy"] and v["fields"] for v in demo_samples.VOICES)
assert demo_samples.VOICES_NOTE in yose, "寄せられた声は抜き出した一文が先頭"
workshop = [s for s in demo_samples.SPOKEN if s["where"] == "workshop"]
review = [s for s in demo_samples.SPOKEN if s["where"] == "review"]
assert len(demo_samples.SPOKEN) == 30 and len(workshop) == 8 and len(review) == 22, len(demo_samples.SPOKEN)
assert yose.count('<div class="item">') == len(demo_samples.VOICES) + len(workshop), "感想 1 件 1 枚と、ワークショップの場の言葉 1 か所 1 枚"
import html as _h  # noqa: E402
for v in demo_samples.VOICES:
    assert all(_h.escape(t) in yose for _, t in v["fields"]), v["toy"]
    assert all(t not in ("", "なし", "特になし") for _, t in v["fields"]), "空や「なし」の欄は出さない"
assert demo_samples.VOICES_WHO in yose and not any(x in yose for x in ("回: A", "回: B", "（A）", "（B）")), "名前・回を出さない"
# 話された言葉（本人の言葉 11-07 夜: 62 分の音源の言葉は「載せてよい」、レビューは「話した人に了承を得ているので大丈夫です」）。字は話したまま。話し手の名は出さない
from omochae import contrib  # noqa: E402
assert demo_samples.SPOKEN_NOTE in yose and yose.count(demo_samples.SPOKEN_WHO) == len(workshop), "ワークショップの場の言葉は出所の札 1 つ"
for s in workshop:
    assert _h.escape(s["text"]) in yose and _h.escape(s["text"]) not in craft, s["text"][:20]
# 型紙レビュー 10 本の言葉は職人の言葉の節にだけ出す（同じ言葉を 2 か所に出さない）。レビュー 1 本に 1 枚の札
assert craft.count('<div class="item">') == 10 and demo_samples.SPOKEN_NOTE in craft, "職人の言葉はレビュー 1 本に 1 枚"
# 本人の答え（11-08）「字だけ出す。」: レビューの録画は 10 本のうち 5 本に顔が入るので、動画は出さない
assert "<video" not in craft and "<iframe" not in craft, "職人の言葉は字だけで、動画を出さない"
for s in review:
    assert _h.escape(s["text"]) in craft and _h.escape(s["text"]) not in yose, s["text"][:20]
    assert _h.escape(s["toy"]) in craft
for s in demo_samples.SPOKEN:
    assert s["text"].strip()
    # 名乗り・連絡先の形が無い（持ち寄りの入口と同じ見張り）。話し手の名は字に入れない
    assert not contrib.check_pii({"body": s["text"]}), s["text"][:20]
assert "（準備中）" not in craft, "職人の言葉の節に本物が入る"
assert "まだ作った物の記録はありません" in html, "本物が無い事を隠さない"
for sid in sources():
    assert records.all_records(sid) == [], "記録の置き場に書かない"

os.environ["OMOCHAE_SAMPLES"] = "0"
off = techo_site.gallery_page(sources()) + techo_site.voices_sections()
assert demo_samples.VOICES_NOTE in off and all(_h.escape(s["text"]) in off for s in review), "寄せられた声も職人の言葉も本物なので、見本を消す設定でも出る"
print("ok")
