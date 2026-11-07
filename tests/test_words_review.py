"""公開の場のギャラリーの札は、人が確かめた後だけ、作った人の感想と工夫の行を出す（窓口の決め A・11-08。omochae.words_review）。

なぜ: 本人 11-08「…できたおもちゃはギャラリーの形で並べる。感想も見れるように」。前は公開の場では人の書いた文を出さなかった
（文の中の名前は機械で落とせない・J-028）。人の目を間に入れて出す形にしたので、両方の向きを見る: 確かめていない物は出ない／確かめた物は出る。
あわせて、確かめた後に字が替わった時・取り消した時・写真ごと取り下げた時・連絡先の形が入った時は出ない事、合言葉付きの場は今のまま出る事、
確かめの置き場に人の字そのものを持たない事、進め役の命令が端末の人の確かめ無しに進まない事を見る。
"""
import json
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, records, store, words_review  # noqa: E402
from web import techo_site  # noqa: E402

G = "NDL-1187053-R0000005-L"
data = hypotheses.load(G)
H = hypotheses.sheet_of(G)["id"]
SAY, FIX = "扇がよく開いた", {"part": "扇", "change": "紙を厚くした", "outcome": "よく開いた"}


def add(impression=SAY, fixes=(FIX,)):
    rid, fs = records.add({"source_id": G, "hypothesis_id": H, "sheet_version": 1, "result": "動いた", "impression": impression, "fixes": list(fixes)})
    assert not fs, fs
    return rid


def card(rid, public=True):
    r = store.read_json_or_skip(records.folder() / f"{rid}.json")
    return techo_site.made_item(G, data, r, public=public)


shown = lambda html: SAY in html and "工夫: 扇 / 紙を厚くした / よく開いた" in html

# 確かめていない物は、公開の場の札に出ない（前と同じ）。合言葉付きの場は確かめずに出る（今のまま）
a = add()
assert not words_review.checked(a)
assert not shown(card(a)) and SAY not in card(a), card(a)
assert shown(card(a, public=False)), "合言葉付きの場は今までどおり出す"
assert words_review.waiting() == [a], words_review.waiting()

# 人が確かめると出る。確かめの置き場は、字そのものを持たない（指紋・確かめた人・時刻だけ）
assert words_review.record(a, "進め役") == []
assert words_review.checked(a) and shown(card(a)), card(a)
kept = json.loads((records.folder() / "media" / a / "words.json").read_text(encoding="utf-8"))
assert set(kept) == {"ok", "reviewer", "digest", "at"} and SAY not in json.dumps(kept, ensure_ascii=False), kept
assert words_review.waiting() == []

# 確かめた後に字が替わると、確かめていない扱いに戻る（確かめた物と違う字を出さない）
p = records.folder() / f"{a}.json"
store.write_json(p, {**json.loads(p.read_text(encoding="utf-8")), "impression": "あとで替えた字"})
assert not words_review.checked(a) and "あとで替えた字" not in card(a)
assert words_review.waiting() == [a], "字が替わった物は、確かめを待つ物に戻る"

# 取り消すと出ない
b = add()
assert words_review.record(b, "進め役") == [] and words_review.checked(b)
assert words_review.revoke(b) == [] and not words_review.checked(b) and not shown(card(b))

# 写真ごと取り下げる（公開の場の上げた画面からの取り下げ）と、置き場ごと消えて、字の確かめも外れる（出さない方へ倒れる）
c = add()
assert words_review.record(c, "進め役") == [] and words_review.checked(c)
gone, fs = records.withdraw(c, media_only=True)
assert not fs and f"media/{c}/words.json" in gone, gone
assert not words_review.checked(c) and not shown(card(c))

# 連絡先の形の床を出す時にもう一度当てる（受ける時の床の後に入った字や、床が強くなった時のため）
d = add()
pd = records.folder() / f"{d}.json"
store.write_json(pd, {**json.loads(pd.read_text(encoding="utf-8")), "impression": "連絡は a@example.com まで"})
assert words_review.record(d, "進め役") == []
assert not words_review.checked(d) and "example.com" not in card(d)

# 字の無い記録は確かめない・待つ物にも出ない。無い番号・取り下げた番号・名前の無い確かめは断る
e = add(impression="", fixes=())
assert words_review.record(e, "進め役") and e not in words_review.waiting()
assert words_review.record("R-9999", "進め役") and words_review.record(b, " ")
assert records.withdraw(b)[1] == [] and words_review.record(b, "進め役") and not words_review.checked(b)

# 進め役の命令: 端末で人が番号を打たないと進まない（試験には端末が無い）・呼び方の誤りは 4・待つ物の一覧は 0
f = add()
assert words_review.main(["approve", f, "--reviewer", "進め役"]) == 3 and not words_review.checked(f)
assert words_review.main(["list"]) == 0 and words_review.main(["approve"]) == 4 and words_review.main(["revoke", "bad"]) == 3

# ギャラリーの頁でも同じ（公開の場は確かめた記録の字だけ）
g = add()
assert words_review.record(g, "進め役") == []
page = techo_site.gallery_page([G], public=True)
assert page.count(SAY) == 1, page.count(SAY)  # 確かめた g だけ（f は確かめていない・a は字が替わった・b は取り下げた）
print("ok: 公開の場のギャラリーの札は、人が確かめた後だけ、作った人の感想と工夫の行を出す")
