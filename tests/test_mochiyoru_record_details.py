"""もちよるの「他の人が作った物」の記録の札に、玩具の頁の記録の札にだけあった 5 つ（型紙の版・最初に動いた所・引っかかった所・
変えると違いが出そうな所・思いついた事）を、畳み「のこした記録」（前からある字）で足す。6 つ目のメモ（ひとこと）は もちよる に出さず
（11-05 の別の目の決まり「ギャラリーに出さない」・統括の答え 11-08 の C）、手帖の記録の頁の自分の記録の札に出す。
本人の言葉 11-08 477「復元の記録などはすべてもちよるに統合する。」・統括の決め（11-08）: 玩具の頁から記録の札を外すと、この 6 つがサイトのどこにも
出なくなるので、もちよるの札に畳みで足す。公開の場は、人が確かめた字だけを出す線（#618・omochae.words_review）に乗せる。

見る事:
1. 合言葉付きの場: 記録の札に、ふだん閉じた畳み「のこした記録」があり、型紙の版と 4 つの欄が玩具の頁と同じ字で出る。書いていない欄は出さない。
   メモ（ひとこと）は もちよる のどの場にも出さない
2. 欄だけの記録（写真も感想も工夫も無い）も、札が出る（玩具の頁から外しても消えない）
3. 公開の場: 人が確かめる前は 5 つの欄の字を出さない。確かめた後は出す。確かめた後に字が替わったら、また出さない
4. 人が確かめる時に、5 つの欄の字も見える（words_review の字に入る）。連絡先の形の床に当たる字は、確かめた後でも出さない
5. 欄が無い記録の、前の確かめの指紋は替わらない（words_review の字の形が、前と同じ）
6. メモは、手帖の記録の頁で、その画面が残した自分の記録の札にだけ出る（ほかの人の画面・公開の場には出ない）
"""
import html
import json
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, records, store, words_review  # noqa: E402
from web import techo_site  # noqa: E402
from web.play_server import sources  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
SET = hypotheses.current_set(hypotheses.load(G))


def add(sid, **fields):
    rid, fails = records.add({"source_id": sid, "hypothesis_id": hypotheses.sheet_of(sid)["id"], "sheet_version": 1, "result": records.UNSURE, **fields})
    assert rid and not fails, fails
    return rid


full = add(G, impression="扇がよく開いた", answers={"first_moved": "筒の口", "stuck": "折り目が固い", "what_if": "紙を薄くする"},
           ideas=["割り箸を貼る", "糊を減らす"], note="二回目に作った")
only = add(T, answers={"first_moved": "頭が揺れた"})
plain = add(G, impression="うまく動いた")


def esc(t):
    return html.escape(t, quote=True)


MARK = {full: "筒の口", only: "頭が揺れた", plain: "うまく動いた"}  # 札を見分ける、その記録にだけある字


def item(page, rid):
    """その記録の札（他の人が作った物の .item）の中身。札の中の、その記録にだけある字で見分ける。"""
    sec = page.split('id="ageta"', 1)[1].split("</section>", 1)[0]
    return next((p for p in sec.split('<div class="item"')[1:] if esc(MARK[rid]) in p), None)


LINES = {full: ["最初に動いた所: 筒の口", "引っかかった所: 折り目が固い", "変えると違いが出そうな所: 紙を薄くする", "思いついた事: 割り箸を貼る、糊を減らす"],
         only: ["最初に動いた所: 頭が揺れた"]}

# 1・2. 合言葉付きの場
page = techo_site.gallery_page(sources())
for rid, lines in LINES.items():
    c = item(page, rid)
    assert c is not None, (rid, "札が出ない")
    assert f"<details class=\"record-more\"><summary>{esc(techo_site.DETAILS_HEAD)}</summary>" in c, (rid, "閉じた畳み「のこした記録」")
    assert all(esc(x) in c for x in lines), (rid, "5 つの欄が玩具の頁と同じ字で出る")
    assert esc(hypotheses.label_of(SET if rid == full else hypotheses.current_set(hypotheses.load(T)), 1)) in c, (rid, "型紙の版の札")
assert "引っかかった所" not in item(page, only), "書いていない欄は出さない"
assert "二回目に作った" not in page and "メモ:" not in page.split('id="ageta"', 1)[1], "メモ（ひとこと）は もちよる に出さない"
assert techo_site.DETAILS_HEAD == "のこした記録", "見出しは前からある字"
# 3. 公開の場: 確かめる前は出さない・確かめた後は出す・字が替わったら出さない
pub = techo_site.gallery_page(sources(), public=True)
assert "筒の口" not in pub and "頭が揺れた" not in pub and "二回目に作った" not in pub, "確かめる前は欄の字を出さない"
# 4. 人が確かめる字に 5 つの欄も入る
assert set(words_review.waiting()) >= {full, only}, "欄だけの記録も確かめを待つ"
assert "筒の口" in json.dumps(words_review.words_of(store.read_json_or_skip(records.folder() / f"{full}.json")), ensure_ascii=False), "確かめる人に欄の字が見える"
for rid in (full, only):
    assert words_review.record(rid, "確認者") == []
pub = techo_site.gallery_page(sources(), public=True)
assert all(esc(x) in pub for lines in LINES.values() for x in lines), "確かめた後は欄の字を出す"
path = records.folder() / f"{only}.json"
rec = store.read_json_or_skip(path)
rec["answers"]["first_moved"] = "頭が大きく揺れた"
store.write_json(path, rec)
assert "頭が大きく揺れた" not in techo_site.gallery_page(sources(), public=True), "確かめた後に字が替わったら出さない"
rec["answers"]["first_moved"] = "電話は 090-1234-5678 です"
store.write_json(path, rec)
assert words_review.record(only, "確認者") == [] and not words_review.checked(only), "連絡先の形の床に当たる字は、確かめた後でも出さない"
# 5. 欄の無い記録の字の形と指紋は前と同じ
prec = store.read_json_or_skip(records.folder() / f"{plain}.json")
assert set(words_review.words_of(prec)) == {"impression", "fixes"}, "欄の無い記録は前の字の形のまま（前の確かめが外れない）"
# 6. メモは、手帖の記録の頁の自分の記録の札にだけ
assert "二回目に作った" not in techo_site.gallery_page(sources(), public=True) and "二回目に作った" not in json.dumps(words_review.words_of(store.read_json_or_skip(records.folder() / f"{full}.json")), ensure_ascii=False), "公開の場にも確かめる字にもメモを入れない"
records.claim(full, "key-1")
assert "メモ: 二回目に作った" in techo_site.records_page(G, rec_key="key-1"), "自分の記録の札にメモが出る"
assert "二回目に作った" not in techo_site.records_page(G, rec_key="key-2") and "二回目に作った" not in techo_site.records_page(G), "ほかの人の画面には出ない"
assert "二回目に作った" not in techo_site.records_page(G, rec_key="key-1", public=True), "公開の場には出ない"
print("ok もちよるの記録の札: 畳み「のこした記録」に型紙の版と 4 つの欄・メモは自分の手帖の札だけ・欄だけの記録も出る・公開の場は人が確かめた字だけ・前の確かめは外れない")
