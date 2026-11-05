"""型紙の版の歩み（本人の希望 11-06）。前の履歴・どこを良くしたか・どの知見から・共通の知見・どのループかが、裏側の改善ループの頁で見える事を見る。

統括の決め（11-06）: どのループかは記録から決める。手で足した欄は使わない。答えは repo の中の data だけで決まり、置き場（OMOCHAE_DATA）を別にしても、
隣の repo（paper-to-toy）が無くても変わらない。本物の API は呼ばない。
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

data_dir = tempfile.mkdtemp()
no_engine = tempfile.mkdtemp()  # 台帳の無い場所
os.environ["OMOCHAE_DATA"] = data_dir
os.environ["OMOCHAE_ENGINE_REPO"] = no_engine

from api import words  # noqa: E402
from omochae import hypotheses, loop, records, talk_log  # noqa: E402
from omochae.marks import without_premise  # noqa: E402
from web import ayumi, kaizen, kaizen_versions as kv, play_server  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"  # 御来迎・首振り虎
ROOT = pathlib.Path(__file__).resolve().parents[1]
LOOP = pathlib.Path(data_dir) / "loop"
LOOP.mkdir(parents=True, exist_ok=True)
RECS = pathlib.Path(data_dir) / "records"
RECS.mkdir(parents=True, exist_ok=True)
OUT = {"loops": [], "material": [], "review": False}
V8 = {"loops": [3], "material": [2], "review": False}


def article(page, anchor):
    """頁の中の、その札（id の付いた article）の字。"""
    return page.split(f'id="{anchor}"')[1].split("</article>")[0]


def item_of(html, word):
    """その字のある札。"""
    return next(x for x in html.split("<article")[1:] if word in x).split("</article>")[0]


# 1. 今の main の data での答え。OMOCHAE_DATA を別にした場でも、隣の repo が無くても、同じ答えになる。別のプロセスで、この repo の data を読む
PROBE = """
import json
from web import ayumi, kaizen_versions as kv
out = {"v8": kv.set_verdict(["goraigo-v8"]), "v9": kv.set_verdict(["goraigo-v9"]), "v10": kv.set_verdict(["goraigo-v10"]), "tora3": kv.set_verdict(["tora-v3"]),
       "tag8": kv.tag(kv.set_verdict(["goraigo-v8"])), "tag9": kv.tag(kv.set_verdict(["goraigo-v9"])), "words": kv.change_words([t for t in kv.template_changes() if t.get("sheet_set") == "goraigo-v8"]),
       "ledger": kv.engine_ledger(), "page": ayumi.page()}
print(json.dumps(out, ensure_ascii=False))
"""


def probe(**env):
    base = {k: v for k, v in os.environ.items() if k not in ("OMOCHAE_DATA", "OMOCHAE_ENGINE_REPO")}
    r = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env={**base, "PYTHONPATH": str(ROOT / "src"), **env}, capture_output=True, text=True, timeout=240)
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


seen = {"今の main の data": probe(OMOCHAE_ENGINE_REPO=no_engine), "置き場が別": probe(OMOCHAE_ENGINE_REPO=no_engine, OMOCHAE_DATA=tempfile.mkdtemp())}
for where, got in seen.items():
    assert got["ledger"] is None, where
    assert got["v8"] == V8 and got["tag8"] == "ループ 3（材料はループ 2）", (where, got["v8"])
    assert got["v9"] == OUT and got["v10"] == OUT and got["tora3"] == OUT and got["tag9"] == "ループの外", (where, got["v9"], got["v10"])
    assert any("くり抜く側面の穴を切るのが大変" in x and x.startswith("人の説明 R-0001") for x in got["words"]), (where, got["words"])
    page = got["page"]
    assert "ループ 3（材料はループ 2）" in article(page, "goraigo-v8") and "人の説明 R-0001" in article(page, "goraigo-v8") and "人の説明 R-0002" in article(page, "goraigo-v8"), where
    for anchor in ("goraigo-v9", "goraigo-v10", "tora-v2"):
        assert "ループの外" in article(page, anchor) and "人の説明" not in article(page, anchor), (where, anchor)
    assert "読めません" in page and "雛形の分からない直し" not in page, where

# 2. 版の表: 全部の行に知見がある。ループの欄は無い（手で足した欄で答えを決めない）。新しい版が上で、前の履歴まで並ぶ。玩具でない見比べる紙は出ない
rows = ayumi.sheet_rows()
assert len(rows) >= 15 and all(r["知見"] for r in rows) and "ループ" not in rows[0], rows[0]
assert "ループ" not in ayumi.shared_rows()[0] and "版" in ayumi.shared_rows()[0]
go = [r["版"] for r in ayumi.rows_for("goraigo")]
assert go[0].startswith("goraigo-v10") and go[-1] == "goraigo-v1" and "goraigo-v8" in go, go
assert [r["版"] for r in ayumi.rows_for("tora")] == ["goraigo-v10・tora-v3", "tora-v2", "tora-v1"]
assert not ayumi.rows_for("stand_figure")
assert ayumi._plain("[research/1](x.md)の`形`（カード 123・456）") == "research/1の形"

# 3. 頁: 見本の見出しと並び。知見の字。判定しない事を頭に書く。作業の番号と線の名は出さない
page = ayumi.page()
order = ("4 つのループ", "共通にしている知見", "御来迎", "張子の首振り虎", "ほかの", "エンジンの版")
at = [page.index(f"<h2>{w}") for w in order]
assert at == sorted(at), at
for word in ("どこを良くしたか", "どの知見から", "その後に分かった事", "ループ 1", "ループ 2", "ループ 3", "ループ 4", "ループの外", "今の数"):
    assert word in page, word
assert "くり抜く側面の穴を切るのが大変" in page and "見た目のクオリティが低く見える" in page
assert 'id="goraigo-v9"' in page and f'id="{G}"' in page and f'id="{T}"' in page and page.count('id="goraigo-v10"') == 1 and page.count('id="tora-v3"') == 1
assert "本当に良くなったかは機械では決めません" in page, "判定しない事を頭に書く"
assert "ループの外: 作った人の記録に結ばれていない直しです" in page, "札の字の意味を頭に書く"
assert not re.search(r"103912|(?:hack|sub)-[a-z]|lane/[a-z]|\]\(|`", page), re.search(r"103912|(?:hack|sub)-[a-z]|lane/[a-z]|\]\(|`", page)
for bad in ("点", "％", "順位", "ランキング"):
    assert f">{bad}<" not in page
for w in ("成功", "失敗", "正解", "順位", "点数"):
    assert w not in without_premise(page), w

# 4. 共通の知見: 入っている型は雛形のコードから数える。全部の型・一部の型・これからが分かれる。ループは「版」の欄の版の記録から決める
shared = ayumi.shared_block()
assert "全部の型" in shared and "虎の型" in shared and "まだ紙に入っていません" in shared
assert ayumi._has("hide_folds", "slider_fan") and not ayumi._has("hide_folds", "pivot_counterweight")
assert not ayumi._has("no_cuts", "pivot_counterweight") and ayumi._has("no_cuts", "slider_fan")
try:
    ayumi._has("知らない", "slider_fan")
    raise AssertionError("知らない見分け方を通した")
except ValueError:
    pass
assert list(ayumi.KINDS)[:2] == ["slider_fan", "pivot_counterweight"], "型の並びは表の順で、数の多い順にしない（J-025）"
for name in ("凡例に、谷折りと山折りの向きを言葉で添える", "はさみで切れる形にする（くり抜かない）"):
    assert "ループ 3（材料はループ 2）" in item_of(shared, name), name
for name in ("見える面の折り線を刷らず、絵の色の境で折る", "図を貼らず、色と線を描き直す", "最初に物差しを確かめてから切る", "色のある見える面は外を向くように折る", "手順で使う道具は、用意する物にも書く"):
    assert "ループの外" in item_of(shared, name), name
for name in ("色のある見える面は外を向くように折る", "手順で使う道具は、用意する物にも書く"):  # 型紙エンジンに入った直し。サイトの紙にはまだ入っていない
    assert "まだ紙に入っていません" in item_of(shared, name) and "paper-to-toy" in item_of(shared, name), name

# 5. 置き場に同じ番号の記録があっても、repo の直しの根拠は repo から読む。版の知見は、その版の根拠の記録の字だけ
base = {"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "わからない", "by": "human"}


def put(rid, **kw):
    (RECS / f"{rid}.json").write_text(json.dumps({**base, "id": rid, "recorded_at": "2026-11-06T01:00:00+09:00", **kw}, ensure_ascii=False), encoding="utf-8")


put("R-0001")
assert not loop.save_explanation("R-0001", "サイトの係", "置き場の同じ番号の字", "わからない")
assert kv.set_verdict(["goraigo-v8"]) == V8
item8 = ayumi._set_item(next(r for r in rows if r["版"] == "goraigo-v8"))
assert "人の説明 R-0001" in item8 and "くり抜く側面の穴を切るのが大変" in item8 and "置き場の同じ番号の字" not in item8
assert "人の説明" not in ayumi._set_item(next(r for r in rows if r["版"] == "goraigo-v9"))
put("R-0011", answers={"stuck": "止まった所の字"}, fixes=[{"part": "外筒", "change": "幅を広げた", "outcome": "入った"}])
put("R-0012")
assert not loop.save_explanation("R-0011", "サイトの係", "根拠の記録の説明の字", "次の思いつきの字")
assert not loop.save_explanation("R-0012", "サイトの係", "根拠でない記録の説明の字", "わからない")


def put_version(sid, hid, n, record_ids, param="fold_count", at="2026-11-06T02:00:00+09:00"):
    (LOOP / f"version-{sid}-{hid}-{n}.json").write_text(json.dumps({"source_id": sid, "hypothesis_id": hid, "version": n, "params": {}, "changes": [{"param": param, "from": 70, "to": 72, "why": "変更の理由の字"}],
                                                                    "record_ids": record_ids, "proposal": "P-0001", "adopted_by": "サイトの係", "adopted_at": at}, ensure_ascii=False), encoding="utf-8")


put_version(G, "H-A", 2, ["R-0011"])
block = ayumi.toy_block(G, hypotheses.load(G))
v2 = item_of(block, "仮説 A 版 2")
assert "折りの数 70→72" in v2 and "変更の理由の字" in v2 and "根拠の記録の説明の字" in v2 and "ループ 2" in v2
assert "止まった所 R-0011: 止まった所の字" in v2 and "人の工夫 R-0011: 外筒 / 幅を広げた / 入った" in v2 and "次の思いつきの字" in v2
assert "根拠でない記録の説明の字" not in block, "版の知見は版の根拠の記録から。組の知見は組の直しの根拠の記録から"
assert "サイトの係" not in block, "採った人と説明した人の名前は出さない"
assert block.index("仮説 A 版 2") < block.index("goraigo-v10"), "新しい版が上"

# 6. 表に行の無い雛形の直しを黙って消さない。根拠の記録の玩具の札に出す。組の名が雛形に当たらなくても出す。番号が repo と重なっても、repo の直しを消さない
_, fails = loop.save_template_change(["R-0011"], "goraigo-v99", "abc1234", ["表にまだ無い直し <b>字</b>"], "サイトの係", "カード 20261104-103912")
assert fails == [], fails
_, fails = loop.save_template_change(["R-0011"], "x-v1", "abc1234", ["組の名が雛形に当たらない直し"], "サイトの係")
assert fails == [], fails
assert kv.set_verdict(["goraigo-v8"]) == V8 and kv.set_verdict(["goraigo-v99"]) == V8 and kv.set_verdict(["x-v1"]) == V8
block = ayumi.toy_block(G, hypotheses.load(G))
assert "goraigo-v99" in block and "表にまだ無い直し" in block and "<b>字</b>" not in block and "x-v1" in block and "組の名が雛形に当たらない直し" in block
assert max(block.index("x-v1"), block.index("goraigo-v99"), block.index("仮説 A 版 2")) < block.index("goraigo-v10"), "日付のある版は、版の表より上"
assert "組の名が雛形に当たらない直し" not in ayumi.toy_block(T, hypotheses.load(T)), "根拠の玩具の札にだけ出す"
assert "根拠の記録の説明の字" in item_of(block, "x-v1") and "根拠でない記録の説明の字" not in block
# 根拠から玩具が分からない直しは、別の節に出す
(LOOP / "template-change-0090.json").write_text(json.dumps({"id": "T-0090", "kind": "template_change", "record_ids": ["R-9999"], "sheet_set": "y-v1", "commit": "abc1234", "changes": ["玩具の分からない直し"], "adopted_by": "サイトの係", "at": "2026-11-06T02:00:00+09:00"}, ensure_ascii=False), encoding="utf-8")
sids = play_server.sources()
assert "雛形の分からない直し" in ayumi.unknown_block(sids) and "玩具の分からない直し" in ayumi.unknown_block(sids) and "組の名が雛形に当たらない直し" not in ayumi.unknown_block(sids)
page = ayumi.page()
assert page.index('id="unknown"') < page.index('id="others"') and "玩具の分からない直し" in page
assert f"雛形の直し {len(kv.template_changes())}、" in ayumi.loop_summary(sids)["3"] and len(kv.template_changes()) == 4, "数えた直しは全部、頁に出る"
(LOOP / "template-change-0090.json").unlink()
assert ayumi.unknown_block(sids) == "" and 'id="unknown"' not in ayumi.page()

# 7. 呼び名の無い寸法は、内部の名前を出さない。呼び名のある寸法はその名で出す
assert kaizen._param_name(G, "no_such_param") == "寸法" and kaizen._param_name(G, "fold_count") == "折りの数"
put_version(T, "H-A", 2, ["R-9999"], param="no_such_param")
tiger = ayumi.toy_block(T, hypotheses.load(T))
assert "寸法 70→72" in tiger and "no_such_param" not in tiger
# 玩具の頁の窓の札も同じ（刷ってある版の札。紙そのものは見ない）
play = pathlib.Path(data_dir) / "play" / T
play.mkdir(parents=True, exist_ok=True)
for name in ("H-A_v2.pdf", "H-A_v2.png"):
    (play / name).write_bytes(b"x")
win = play_server.serve(0)
threading.Thread(target=win.serve_forever, daemon=True).start()
with urllib.request.urlopen(f"http://127.0.0.1:{win.server_address[1]}/toy/{T}?see=H-A&kind=sheet&v=2", timeout=120) as res:
    shown = res.read().decode()
win.shutdown()
assert "変えた所: 寸法 70→72" in shown and "no_such_param" not in shown, re.findall(r"変えた所[^<]{0,40}", shown)
# 根拠の記録が読めない寸法の版も、頁を止めず ループ 2 と見る（版は記録からしか作れない）
assert "ループ 2" in item_of(tiger, "仮説 A 版 2")
(LOOP / f"version-{T}-H-A-2.json").unlink()
assert kv.record_loops("R-9999") == ([], False) and kv.record_loops("../x") == ([], False) and kv.record_words("R-9999") == []
assert kv.record_loops("../loop/explanation-R-0001", True) == ([], False) and kv.record_words("../loop/explanation-R-0001", True) == [], "repo の外や別の置き場を番号で読まない"

# 8. ループの札は通った道で決まる。話の無い記録はループ 2
WHO = "ayumitest01"
put("R-0021")
put("R-0022")
assert kv.record_loops("R-0021") == ([2], False)
assert talk_log.add(G, "craft", "糊代を少し広くした", hypothesis_id="H-A", sheet_version=1, step=3, who=WHO)[1] == []
talk_log.bind(G, "H-A", 1, WHO, "R-0021")
assert kv.record_loops("R-0021") == ([2], False)
assert talk_log.add(G, "keep", "できた後に、扇の向きを変えた", record_id="R-0021")[1] == []
assert kv.record_loops("R-0021") == ([2, 4], False), "作りながらの話と上げた後の話"
assert talk_log.add(G, "keep", "上げた後の話だけ", record_id="R-0022")[1] == []
assert kv.record_loops("R-0022") == ([4], False)
# 置き場の同じ番号に話した字があっても、repo の記録の答えと知見には混ぜない
assert talk_log.add(G, "keep", "置き場の同じ番号に話した字", record_id="R-0001")[1] == []
assert kv.set_verdict(["goraigo-v8"]) == V8 and not any("置き場の同じ番号に話した字" in x for x in kv.record_words("R-0001", True))
put("R-0101", via=records.UPLOADED)
assert kv.record_loops("R-0101") == ([4], False), "上げる口から来た記録"
put("R-0102", via=records.UPLOADED, video_kind="review")
assert kv.record_loops("R-0102") == ([], True), "作る前のレビューは 4 つのどれにも数えない"
put("R-0103", hypothesis_id="OWN-1")
assert kv.record_loops("R-0103") == ([2], False), "話した考えから作った紙でなければ ループ 1 を付けない"
(LOOP / "words-W-0001.json").write_text(json.dumps({"source_id": G, "typed_by": words.THINK_BY, "own_id": "OWN-1"}, ensure_ascii=False), encoding="utf-8")
assert kv.record_loops("R-0103") == ([1, 2], False)
assert kv.version_verdict({"record_ids": ["R-0021"]}) == {"loops": [2, 4], "material": [], "review": False}
assert kv.version_verdict({"record_ids": ["R-0102"]}) == {"loops": [], "material": [], "review": True} and kv.tag(kv.version_verdict({"record_ids": ["R-0102"]})) == "ループの外（材料は作る前のレビュー）"
assert kv.version_verdict({"record_ids": ["無い記録"]})["loops"] == [2]
assert kv.change_verdict([]) == OUT and kv.tag(OUT) == "ループの外"
assert kv.tag({"loops": [1, 2], "material": [], "review": False}) == "ループ 1・2"
put_version(G, "H-A", 3, ["R-0022"], at="2026-11-06T03:00:00+09:00")
summary = ayumi.loop_summary(sids)
assert "寸法の版 1" in summary["2"] and "上げた後の字も材料にした版 1" in summary["4"], summary
assert "ループ 4" in item_of(ayumi.toy_block(G, hypotheses.load(G)), "仮説 A 版 3")
assert ayumi.toy_block(G, hypotheses.load(G)).index("仮説 A 版 3") < ayumi.toy_block(G, hypotheses.load(G)).index("仮説 A 版 2"), "日の新しい版が上"
(LOOP / f"version-{G}-H-A-3.json").unlink()

# 9. 知見の字: 話した工夫は並ぶ。隠した字と案のままの読みは出ない。人が確かめた読みは出る。床に当たる字は、手で置いた記録でも出さない。人の字は符号にする
assert "手順 3 で話した工夫 R-0021: 糊代を少し広くした" in kv.record_words("R-0021") and "上げた後の話 R-0021: できた後に、扇の向きを変えた" in kv.record_words("R-0021")
talk_log.set_share(G, "R-0021", False)
assert kv.record_words("R-0021") == []
talk_log.set_share(G, "R-0021", True)
loop.save_interpretation_draft("R-0022", {"observed": ["案の見た事の字"], "causes": [{"text": "案の原因の字", "confidence": "低い"}], "unknown": []})
assert not any("案の見た事の字" in x or "案の原因の字" in x for x in kv.record_words("R-0022"))
assert loop.confirm_interpretation("R-0022", "サイトの係") == []
assert "読み R-0022: 案の見た事の字" in kv.record_words("R-0022") and "読み R-0022: 案の原因の字" in kv.record_words("R-0022")
put("R-0023")
assert loop.confirm_interpretation("R-0023", "サイトの係", "人が書いた読みの字") == [] and "読み R-0023: 人が書いた読みの字" in kv.record_words("R-0023")
PHONE = "090-1234-5678"
put("R-0024", answers={"stuck": f"電話は {PHONE} です"}, fixes=[{"part": "外筒", "change": f"電話は {PHONE}", "outcome": "入った"}])
(LOOP / "explanation-R-0024.json").write_text(json.dumps({"record_id": "R-0024", "text": f"電話は {PHONE} です", "next_idea": "わからない", "by": "x"}, ensure_ascii=False), encoding="utf-8")
assert kv.record_words("R-0024") == [], kv.record_words("R-0024")
assert not loop.save_explanation("R-0012", "サイトの係", "<script>alert(1)</script>の形", "わからない")
put_version(G, "H-A", 3, ["R-0012"])
block = ayumi.toy_block(G, hypotheses.load(G))
assert "<script>alert(1)" not in block and "&lt;script&gt;alert(1)" in block
(LOOP / f"version-{G}-H-A-3.json").unlink()

# 10. エンジンの版: 読めない時は読めないと言い、頁は止めない。案から刻んだ版はループ 3 で、材料は案の数で読む。案の無い版はループの外
assert kv.engine_ledger() is None and "読めません" in ayumi.engine_block() and "読めません" in ayumi.loop_summary([G])["3"]
root = pathlib.Path(no_engine) / "data/engine"
root.mkdir(parents=True)
ledger = {"next": [{"id": "EP-0009", "target": {"kind": "part", "name": "まだ版に入っていない部品"}, "title": "次の版の予定の題", "numbers": {}, "finding": "まだ版に入っていない知見"}],
          "versions": [{"version": 1, "at": "2026-11-05", "proposals": [], "sheet_sets": {}, "note": "輪を足す前からの形"},
                       {"version": 2, "at": "2026-11-06", "note": "足の絵を直した", "sheet_sets": {"slider_fan.tab": "goraigo-v101"},
                        "proposals": [{"id": "EP-0001", "target": {"kind": "template", "name": "slider_fan"}, "title": "slider_fan（紙 tab）: 手順 3", "numbers": {"stuck_people": 2, "keeps": 1, "not_moved": 7}, "finding": "足の向きは絵で見せる <i>"}]},
                       {"version": 3, "at": "2026-11-06", "note": "", "sheet_sets": {"spinner": "spin-v2"},
                        "proposals": [{"id": "EP-0002", "target": {"kind": "template", "name": "spinner"}, "title": "spinner: レビュー", "numbers": {"reviews": 3}, "finding": f"電話は {PHONE}"}]},
                       {"version": 4, "at": "2026-11-06", "note": "折り線の刷り方を直した", "sheet_sets": {},
                        "proposals": [{"id": "EP-0003", "target": {"kind": "part", "name": "折り線の刷り方と凡例（render）"}, "title": "共有の所の題", "numbers": {"templates": 2, "keeps": 1}, "finding": "折る向きは言葉で書く <u>"},
                                      {"id": "EP-0004", "target": {"kind": "rule", "name": "slider_fan の動きの床と既定の寸法"}, "title": "slider_fan: 動きの床の題", "numbers": {"not_moved": 2}},
                                      {"id": "EP-0005", "target": {"kind": "template", "name": "spinner"}, "title": "雛形だけの案の題", "numbers": {}}]}]}
(root / "versions.json").write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
versions_ = ledger["versions"]
assert kv.engine_verdict(versions_[0]) == OUT and kv.engine_verdict(versions_[1]) == {"loops": [3], "material": [2, 4], "review": False}
assert kv.tag(kv.engine_verdict(versions_[2])) == "ループ 3（材料は作る前のレビュー）"
block = ayumi.engine_block()
assert block.index("エンジンの版 4") < block.index("エンジンの版 2") < block.index("エンジンの版 1") and "spin-v2" in block and "案 1 件から" in block and "足の絵を直した" in block
assert "足の向きは絵で見せる &lt;i&gt;（案 EP-0001）" in block and "<i>" not in block and PHONE not in block, "採る人の 1 行。連絡先の形は出さない"
assert "ループの外" in item_of(block, "エンジンの版 1") and "ループ 3（材料はループ 2・4）" in item_of(block, "エンジンの版 2")
assert "not_moved" not in block and "動かない" not in block and ">7<" not in block, "動きの札の数は出さない（J-025）"
assert "3 版" in ayumi.loop_summary([G])["3"]
shared = ayumi.shared_block()
assert "折る向きは言葉で書く &lt;u&gt;" in shared and "<u>" not in shared and "全部の型" in item_of(shared, "折る向きは言葉で書く") and "エンジンの版 4・案 EP-0003" in shared
assert "slider_fan: 動きの床の題" in shared and "雛形だけの案の題" not in shared and "まだ版に入っていない" not in shared, "版に入った部品と決まりの案だけ"
assert "ループ 3（材料はループ 4）" in item_of(shared, "折る向きは言葉で書く")
(root / "versions.json").write_text("{壊れた", encoding="utf-8")
assert kv.engine_ledger() is None and "読めません" in ayumi.page()
# 環境の値が無い時は、隣の repo の main の中身を git から読む（隣の木は作業の途中の枝のことがある）。読めなければ木の中のファイル。隣の repo が無くても止まらない
del os.environ["OMOCHAE_ENGINE_REPO"]
sibling = pathlib.Path(data_dir) / "sib" / "paper-to-toy"
real_root, kv.ROOT = kv.ROOT, sibling.parent / "utsushi"
try:
    assert kv.engine_ledger() is None, "隣の repo が無い"
    (sibling / "data/engine").mkdir(parents=True)
    git = lambda *a: subprocess.run(["git", "-C", str(sibling), "-c", "user.name=t", "-c", "user.email=t@example.com", *a], check=True, capture_output=True)
    git("init", "-q")
    (sibling / "data/engine/versions.json").write_text(json.dumps({"versions": [{"version": 7}]}), encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "ledger")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    (sibling / "data/engine/versions.json").write_text(json.dumps({"versions": [{"version": 8}]}), encoding="utf-8")
    assert kv.engine_ledger()["versions"][0]["version"] == 7, "隣の木が途中の枝でも main の台帳を読む"
    git("update-ref", "-d", "refs/remotes/origin/main")
    assert kv.engine_ledger()["versions"][0]["version"] == 8, "main が読めない時は木の中のファイル"
finally:
    kv.ROOT = real_root
    os.environ["OMOCHAE_ENGINE_REPO"] = no_engine

# 11. 表の形が崩れたら黙って飛ばさない
keep = ayumi.LEDGER
broken = pathlib.Path(tempfile.mkdtemp()) / "x.md"
broken.write_text("| 版 | 知見 |\n|---|---|\n| a | b | c |\n", encoding="utf-8")
ayumi.LEDGER = broken
try:
    ayumi.sheet_rows()
    raise AssertionError("欄の数が合わない表を通した")
except ValueError:
    pass
ayumi.LEDGER = keep

# 12. 道: 一覧と工作の様子から行ける。学ぶ人の頁には道を置かない。合言葉なしで開いたデモでは出さない
assert '<a href="/loop/ayumi">' in kaizen.page() and f'<a href="/loop/ayumi#{G}">' in kaizen.toy_page(G)
for public, want in ((False, 200), (True, 404)):
    srv = play_server.serve(0, public_open=public)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/loop/ayumi", timeout=120) as res:
            status, body = res.status, res.read().decode()
    except urllib.error.HTTPError as e:
        status, body = e.code, ""
    srv.shutdown()
    assert status == want, (public, status)
    assert public or "型紙の版の歩み" in body
own = play_server.serve(0)
threading.Thread(target=own.serve_forever, daemon=True).start()
for path in ("/about", "/toys", "/", f"/toy/{G}"):
    with urllib.request.urlopen(f"http://127.0.0.1:{own.server_address[1]}{path}", timeout=120) as res:
        body = res.read().decode()
    assert "/loop/ayumi" not in body and "どの知見から" not in body and "ループの外" not in body, path
own.shutdown()
print("ok: 型紙の版の歩み")
