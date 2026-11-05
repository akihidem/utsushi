"""改善の輪がサイトで回る（本人の方針 11-05 朝「作ったものの感想と動きを報告してもらったら、サイト側もループを回し、型紙の改善をする。
そうすることでより良いおもちゃの型紙を提供できる」）。本物の API は呼ばない。

見る線: 報告に感想の欄がある → 説明 → 寸法を 1 つ変えて次の版 → 次に刷る人は直した版を受け取る → 玩具の頁と /loop に、どの報告がどの版を変えたかが出る。
成績に見える言葉と数は出さない（J-025）。感想にも連絡先の形を残さない（F3）。
"""
import json
import os
import pathlib
import re
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA

from omochae.marks import without_premise  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def get(path):
    try:
        r = opener.open(base + path)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def post(path, data):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    try:
        r = opener.open(req)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303
page = get(f"/toy/{G}")[1]
# 報告の欄に感想がある。輪の節は、報告が無い時もその旨を出す
assert 'name="impression"' in page and 'id="kaizen"' in page and "報告はまだありません" in page
# 感想にも連絡先の形は残さない
code, body = post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動かない", "impression": "電話は 090-1234-5678 です"})
assert code == 422, code
# 報告: 動き（結果）と感想
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動かない", "opener": "紙の力", "stuck": "3 枚目の折り目", "impression": "折るのは楽しかったが、扇が半分で止まった"})[0] == 303
rec = json.loads((pathlib.Path(DATA) / "records/R-0001.json").read_text(encoding="utf-8"))
assert rec["impression"] == "折るのは楽しかったが、扇が半分で止まった" and rec["sheet_version"] == 1
page = get(f"/toy/{G}")[1]
assert "感想: 折るのは楽しかったが、扇が半分で止まった" in page and 'id="R-0001"' in page
# 説明の前は「説明を待つ報告」。説明の後は「次の版を待つ報告」
assert "説明を待つ報告 1 件" in page and "次の版を待つ報告" not in page
assert post("/record/R-0001/explain", {"text": "折りが固くて戻る力が足りない", "next_idea": "折りを減らす", "by": "作った人"})[0] in (200, 303)
page = get(f"/toy/{G}")[1]
assert "次の版を待つ報告 1 件" in page and "報告から直した版はまだありません" in page
# 輪を回す: 寸法を 1 つ変えて次の版
code, body = post("/record/R-0001/next", {"interpretation": "折りが固い", "param": "fold_count", "to": "24", "why": "開きを見る", "by": "サイトの係"})
assert code in (200, 303), body[:300]
page = get(f"/toy/{G}")[1]
kz = page.split('id="kaizen"')[1]
assert "仮説 A 版 2" in kz and "折りの数" in kz and "R-0001" in kz and "次の版を待つ報告" not in kz
assert "サイトの係" not in kz, "採った人の名前は学ぶ人の頁に出さない（自由な文で、名前を書かない線）"
# 次に作る人: 刷ると直した版（版 2）が出る。窓も最新の版
out = pathlib.Path(DATA) / "play" / G
(out / "H-A_v2.pdf").unlink()
(out / "H-A_v2.png").unlink()
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303
assert (out / "H-A_v2.pdf").exists(), "刷るのは一番新しい版"
page = get(f"/toy/{G}")[1]
assert f'<img src="/sheet/{G}/H-A_v2.png"' in page and "<b>版 2</b>" in page
# その版への報告は、版 2 への返事として残る
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた", "impression": "前より開いた"})[0] == 303
assert json.loads((pathlib.Path(DATA) / "records/R-0002.json").read_text(encoding="utf-8"))["sheet_version"] == 2
# サイト側の一覧: 報告のある玩具・版・待っている報告
code, lp = get("/loop")
assert code == 200 and "改善の輪" in lp and "御来迎" in lp and f'href="/toy/{G}#kaizen"' in lp
for w in ("成功", "失敗", "正解", "順位", "点数"):
    assert w not in without_premise(lp) and w not in without_premise(kz), w
# 学ぶ人の頁からは道を置かない（集計は学ぶ人の画面に出さない線。道を知っている作る側が開く）
for path in ("/about", "/toys", "/", f"/toy/{G}"):
    assert 'href="/loop' not in get(path)[1], path

# 検品の指摘の再発の見張り: 窓は刷ってある版だけを出し、版を言わなければ一番新しい版
page = get(f"/toy/{G}")[1]
assert 'see=H-A&kind=sheet&v=2#win" aria-current' in page and 'see=H-A&kind=sheet&v=1#win" aria-current' not in page, "仮説の札は一番新しい版へ"
(out / "H-A_v1.pdf").unlink()
(out / "H-A_v1.png").unlink()
only2 = get(f"/toy/{G}")[1]
assert f"/sheet/{G}/H-A_v1.png" not in only2 and "<b>版 2</b>" in only2 and ">版 1<" not in only2.split('id="win"')[1].split('id="tsukuru"')[0], "刷っていない版を出さない"
assert get(f"/toy/{G}?see=H-A&kind=sheet&v=1")[0] == 200 and f'<img src="/sheet/{G}/H-A_v2.png"' in get(f"/toy/{G}?see=H-A&kind=sheet&v=1")[1], "無い版を言われても一番新しい版へ"
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303  # 元に戻す（版 2 を刷り直す。版 1 は無いまま）
# 報告の版: 版が 2 つある時は、どの版の紙かを聞き、言われた版の報告として残す（版 1 で作っていた人の報告が版 2 の記録にならない）
# 御来迎の今の組で刷れるのは、たたき台の H-A だけ（本人の決定 11-05、J-032）。頁の札の直しは後の PR で、今は刷る所で断る。
assert post(f"/toy/{G}/print", {"hypothesis": "H-B"})[0] == 422
from omochae import hypotheses  # noqa: E402

hypotheses.print_sheet(G, "H-A", str(out / "H-A_v1"), 1)
page = get(f"/toy/{G}")[1]
assert 'name="sheet_version"' in page.split('id="record"')[1].split("</form>")[0]
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "sheet_version": "1", "result": "動かない", "impression": "版 1 で作っていた"})[0] == 303
assert json.loads((pathlib.Path(DATA) / "records/R-0003.json").read_text(encoding="utf-8"))["sheet_version"] == 1
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "sheet_version": "9", "result": "動いた"})[0] == 303
assert json.loads((pathlib.Path(DATA) / "records/R-0004.json").read_text(encoding="utf-8"))["sheet_version"] == 2, "刷っていない版を言われたら一番新しい版"
# 一番新しい版が検査に落ちる時は、1 つ前の版を刷る（その仮説の紙が誰にも刷れなくならない）
real = hypotheses.print_sheet
hypotheses.print_sheet = lambda s, h, o, v=1: 3 if v == 2 else real(s, h, o, v)
(out / "H-A_v1.pdf").unlink()
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303 and (out / "H-A_v1.pdf").exists()
hypotheses.print_sheet = real
# 新しく作られた版の型紙の歩み（本人の希望 11-06: その前の履歴・どこが良くなったか・どういう知見で良くなったか・共通化している知見・どのループで走ったか）。
# 別の台帳を作らず、今ある記録だけを読む（J-026）。読むエンジンの台帳は、試しの場所へ向ける
from omochae import loop, records, talk_log  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402
from web import kaizen_versions as kv  # noqa: E402

T = "NDL-1187053-R0000014-R"  # 首振り虎
OTHER = "NDL-1187053-R0000005-R"  # 版の記録の無い玩具
engine = pathlib.Path(DATA) / "engine-repo"
os.environ["OMOCHAE_ENGINE_REPO"] = str(engine)  # 台帳がまだ無い
named = lambda sid: {e["name"]: e for e in kv.entries(sid)}
code, lp = get("/loop")
sec = lp.split('id="versions"')[1]
assert code == 200 and sec.index("新しく作られた版の型紙") < sec.index("その前の履歴") < sec.index("どこが良くなったか") < sec.index("どういう知見で良くなったか") < sec.index("共通化している知見"), "見出しは本人の言葉と順のまま"
assert all(f"ループ {n}" in sec.split("<article")[0] for n in (1, 2, 3, 4)) and "エンジンの台帳が手元にありません" in sec
# その前の履歴: 人が書いた版の表を読む。玩具ごとに分かれ、組み合わせの行は両方に入る。見比べる紙の行（玩具でない）は出ない
goraigo, tora = named(G), named(T)
assert list(goraigo)[:3] == ["goraigo-v1", "goraigo-v2", "goraigo-v3"] and [n for n in goraigo if n.startswith("goraigo")][-1] == "goraigo-v10" and list(tora)[:3] == ["tora-v1", "tora-v2", "tora-v3"]
# 版の名前を変えない例外の行は、新しい版にせず、その版の中身に足す
assert "goraigo-v10 の H-E（例外）" not in goraigo and any(x.startswith("goraigo-v10 の H-E（例外）: ") for x in goraigo["goraigo-v10"]["changed"])
assert goraigo["goraigo-v10"]["changed"][0] == tora["tora-v3"]["changed"][0] and len(tora["tora-v3"]["changed"]) == 1 and kv.entries(OTHER) == [] and "compare-v1" not in sec and f'href="/loop/{OTHER}"' not in sec
assert goraigo["goraigo-v3"]["found"] == "台の形では扇が 180° までしか開けない" and "手元の複写を基準に寸法を直した" in goraigo["goraigo-v3"]["changed"][0]
assert goraigo["goraigo-v1"]["commit"] == "a76c29f" and goraigo["goraigo-v8"]["commit"] == ""  # 番号でない欄は commit と読まない
# 作業の番号と線の名は頁に出さない。リンクの印も字にする
assert not re.search(r"103912|(?:hack|sub)-[a-z]|lane/[a-z]|\]\(|`", sec), re.search(r"103912|(?:hack|sub)-[a-z]|lane/[a-z]|\]\(|`", sec)
assert kv._plain("[research/1](x.md)の`形`（カード 123・456）") == "research/1の形"
# 表の「記録」は、その記録の題まで読む（どういう知見で）。人が書いた題で、機械の要約を作らない
title = (ROOT / "docs/process/research/03-mechanism-dimensions.md").read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# 03").strip()
assert f"記録 research/03: {title}" in goraigo["goraigo-v1"]["learned"] and title in sec
assert not any(x.startswith("記録 J-020: J-020") for e in goraigo.values() for x in e["learned"]), "題の頭の番号を呼び名と重ねない"
# どのループ: 記録に結ばれていない直しは、ループに入れて見せない
assert goraigo["goraigo-v9"]["loops"] == [] and "ループの外" in sec
# 雛形の直し（T-番号）: エンジンの側を直した物なので ループ 3。材料の記録が通ったループも並べる。人の説明が知見に並ぶ。採った人の名前とカードの番号は出さない
assert loop.save_template_change(["R-0001"], "goraigo-v8", "9e590cd", ["つまみの溝は下の端からはさみで切り込む"], "サイトの係", "カード 20261104-103912")[1] == []
v8 = named(G)["goraigo-v8"]
assert v8["loops"] == [3] and v8["material"] == [2] and v8["changed"] == ["つまみの溝は下の端からはさみで切り込む"] and v8["commit"] == "9e590cd"
assert any("折りが固くて戻る力が足りない" in x for x in v8["learned"]) and any("折りを減らす" in x for x in v8["learned"])
assert kv.tag(v8) == "ループ 3（材料はループ 2）"
# 表に無い組の雛形の直しも出る
assert loop.save_template_change(["R-0001"], "goraigo-v99", "abc1234", ["表にまだ無い直し"], "サイトの係")[1] == []
assert named(G)["goraigo-v99"]["loops"] == [3]
# 寸法の版: 根拠の記録で決める。話の無い記録は ループ 2。変えた寸法・理由・読み・説明が並び、その版の型紙へ行ける
v2 = named(G)["仮説 A 版 2"]
assert v2["loops"] == [2] and v2["material"] == [] and any("折りの数" in x and "24" in x for x in v2["changed"])
assert any("開きを見る" in x for x in v2["learned"]) and any("折りが固い" in x for x in v2["learned"]) and any("折りが固くて戻る力が足りない" in x for x in v2["learned"])
assert v2["link"] == f"/toy/{G}?see=H-A&kind=sheet&v=2#win"
code, lp = get("/loop")
sec = lp.split('id="versions"')[1]
assert f'/toy/{G}?see=H-A&amp;kind=sheet&amp;v=2#win' in sec and "サイトの係" not in lp and "20261104" not in lp and "103912" not in lp
for w in ("成功", "失敗", "正解", "順位", "点数"):
    assert w not in without_premise(lp), w
# 一番新しい版が札の頭（日付のある版の日の順で、表の行より後）。その前の版は履歴に入る
card = sec.split(f'id="ver-{G}"')[1].split("</article>")[0]
assert card.index("goraigo-v99") < card.index("その前の履歴") < card.index("仮説 A 版 2") < card.index("goraigo-v8") and "表にまだ無い直し" in card.split("どこが良くなったか")[1]
# 根拠の記録が読めない寸法の版も、頁を止めず ループ 2 と見る（版は記録からしか作れない）
(pathlib.Path(DATA) / "loop" / f"version-{T}-H-A-2.json").write_text(json.dumps({"source_id": T, "hypothesis_id": "H-A", "version": 2, "params": {}, "changes": [], "record_ids": ["R-9999"], "adopted_at": "2026-11-06T00:00:00+09:00"}, ensure_ascii=False), encoding="utf-8")
assert named(T)["仮説 A 版 2"]["loops"] == [2]
(pathlib.Path(DATA) / "loop" / f"version-{T}-H-A-2.json").unlink()
# ループの札は通った道で決まる
WHO = "kaizentest01"
rid = lambda n: f"R-{n:04d}"
assert kv.record_loops(rid(2)) == ([2], False)  # 話の無い記録
assert talk_log.add(G, "craft", "糊代を少し広くした", hypothesis_id="H-A", sheet_version=2, step=3, who=WHO)[1] == []
talk_log.bind(G, "H-A", 2, WHO, rid(2))
assert kv.record_loops(rid(2)) == ([2], False)  # 作りながらの話
assert talk_log.add(G, "keep", "できた後に、扇の向きを変えた", record_id=rid(2))[1] == []
assert kv.record_loops(rid(2)) == ([2, 4], False)  # 上げた後の話もある
assert talk_log.add(G, "keep", "上げた後の話だけ", record_id=rid(3))[1] == []
assert kv.record_loops(rid(3)) == ([4], False)
recs = pathlib.Path(DATA) / "records"
extra = {"source_id": G, "hypothesis_id": "H-A", "sheet_version": 2, "result": "わからない", "recorded_at": "2026-11-06T01:00:00+09:00", "by": "human"}
(recs / "R-0101.json").write_text(json.dumps({**extra, "id": "R-0101", "via": records.UPLOADED}, ensure_ascii=False), encoding="utf-8")
assert kv.record_loops("R-0101") == ([4], False)  # 上げる口から来た記録
(recs / "R-0102.json").write_text(json.dumps({**extra, "id": "R-0102", "via": records.UPLOADED, "video_kind": "review"}, ensure_ascii=False), encoding="utf-8")
assert kv.record_loops("R-0102") == ([], True)  # 作る前のレビューは作っていないので、4 つのどれにも数えず、レビューと出す
(recs / "R-0103.json").write_text(json.dumps({**extra, "id": "R-0103", "hypothesis_id": "OWN-1"}, ensure_ascii=False), encoding="utf-8")
assert kv.record_loops("R-0103") == ([2], False)  # 話した考えから作った紙でなければ ループ 1 を付けない
(pathlib.Path(DATA) / "loop" / "words-W-0001.json").write_text(json.dumps({"source_id": G, "typed_by": kv.words.THINK_BY, "own_id": "OWN-1"}, ensure_ascii=False), encoding="utf-8")
assert kv.record_loops("R-0103") == ([1, 2], False)
assert kv.record_loops("R-9999") == ([], False)  # 読めない記録で頁を止めない
# 話した工夫は知見に並ぶ。作る側が隠した字は出さない。人の字は頁で符号にする
assert any("糊代を少し広くした" in x for x in kv.record_words(rid(2))) and any("できた後に、扇の向きを変えた" in x for x in kv.record_words(rid(2)))
talk_log.set_share(G, rid(2), False)
assert kv.record_words(rid(2)) == []
talk_log.set_share(G, rid(2), True)
# 読みは、人が確かめた物だけ。案のままの読みは出さない
loop.save_interpretation_draft(rid(3), {"observed": ["案の見た事の字"], "causes": [{"text": "案の原因の字", "confidence": "低い"}], "unknown": []})
assert not any("案の見た事の字" in x or "案の原因の字" in x for x in kv.record_words(rid(3)))
assert loop.confirm_interpretation(rid(3), "サイトの係") == []
assert any("案の見た事の字" in x for x in kv.record_words(rid(3))) and any("案の原因の字" in x for x in kv.record_words(rid(3)))
assert not loop.save_explanation(rid(4), "作った人", "<script>alert(1)</script>の形", "わからない")
assert loop.save_template_change([rid(4)], "goraigo-v100", "abc1234", ["<b>字</b>の形"], "サイトの係")[1] == []
code, lp = get("/loop")
assert "<script>alert(1)</script>" not in lp and "&lt;script&gt;alert(1)" in lp and "<b>字</b>" not in lp
# エンジンの版: ループ 3。材料は案の数で読む。版は当たる玩具にだけ付く。採る人が書いた知見と版の文が並ぶ。動きの札の数は出さない（J-025）
(engine / "data/engine").mkdir(parents=True)
ledger = {"next": [{"id": "EP-0009", "target": {"kind": "part", "name": "まだ版に入っていない部品"}, "title": "次の版の予定", "numbers": {}, "finding": "まだ版に入っていない知見"}],
          "versions": [{"version": 1, "commit": "c932e58", "at": "2026-11-05", "proposals": [], "sheet_sets": {}, "note": "輪を足す前からの形"},
                       {"version": 2, "commit": "abc1234def", "at": "2026-11-06", "note": "足の絵を直した", "sheet_sets": {"slider_fan.tab": "goraigo-v101"}, "sources": {"slider_fan.tab": ["NDL-1187053-R0000005-L"]},
                        "proposals": [{"id": "EP-0001", "target": {"kind": "template", "name": "slider_fan"}, "title": "slider_fan（紙 tab）: 手順 3 の文と、その段の部品の形を見直す",
                                       "numbers": {"stuck_taps": 3, "stuck_people": 2, "craft_talks": 1, "keeps": 1, "not_moved": 7}, "finding": "足の向きは絵で見せる <i>"}]},
                       {"version": 3, "commit": "bcd2345", "at": "2026-11-06", "note": "羽の穴を直した", "sheet_sets": {"spinner.pinwheel": "spin-v2"}, "sources": {"spinner.pinwheel": ["NDL-1187053-R0000014-L-spinner"]},
                        "proposals": [{"id": "EP-0002", "target": {"kind": "template", "name": "spinner"}, "title": "spinner（紙 pinwheel）: 作る前のレビューの指摘を、雛形に入れるか見る", "numbers": {"reviews": 3}, "finding": "穴は大きめに"}]},
                       {"version": 4, "commit": "cde3456", "at": "2026-11-06", "note": "折り線の刷り方を直した", "sheet_sets": {"stand_figure": "stand_figure-v2"}, "sources": {},
                        "proposals": [{"id": "EP-0003", "target": {"kind": "part", "name": "折り線の刷り方と凡例（render）"}, "title": "共有の所: 折り線の刷り方と凡例（render）を見直す", "numbers": {"templates": 2, "texts": 3}, "finding": "折る向きは凡例に言葉で書く"},
                                      {"id": "EP-0004", "target": {"kind": "rule", "name": "slider_fan の動きの床と既定の寸法"}, "title": "slider_fan（紙 tab）: 動きの床の式と既定の寸法を見直す", "numbers": {"not_moved": 2}}]},
                       {"version": 5, "commit": "def4567", "at": "2026-11-06", "note": "刷った組を結ばずに刻んだ版", "sheet_sets": {},
                        "proposals": [{"id": "EP-0005", "target": {"kind": "template", "name": "pivot_counterweight"}, "title": "pivot_counterweight: 作った人の工夫を、雛形に入れるか見る", "numbers": {"fixes": 1}}]}]}
(engine / "data/engine/versions.json").write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
(engine / "data/engine/shared-findings.json").write_text(json.dumps([
    {"finding": "糊代の見え方は全部の雛形でそろえる", "where": "刷り方", "reach": "all", "loops": [3], "material": [2], "from": "goraigo-v8"},
    {"finding": "<u>字</u>の形", "where": "<u>置き場</u>", "reach": "all", "loops": [], "material": [], "from": "<u>元</u>"},
    {"finding": "虎の胴だけの知見", "where": "胴", "reach": ["pivot_counterweight"], "loops": [], "material": [], "from": "tora-v3"},
    {"finding": "", "where": "形の外"}, "形の外"], ensure_ascii=False), encoding="utf-8")
gg = named(G)
assert "エンジンの版 1" not in gg and "エンジンの版 3" not in gg
ev2 = gg["エンジンの版 2（goraigo-v101）"]
assert ev2["loops"] == [3] and ev2["material"] == [2, 4] and ev2["changed"] == ["足の絵を直した"] and ev2["commit"] == "abc1234"
assert kv.tag(ev2) == "ループ 3（材料はループ 2・4）" and any("足の向きは絵で見せる" in x for x in ev2["learned"]) and not any("動かない" in x or "not_moved" in x for x in ev2["learned"])
# 形まで刻んだ版は、その形の出典の玩具にだけ付く。雛形の鍵で刻んだ版は、その雛形の玩具の全部に付き、一覧では 1 枚の札にまとまる
assert "エンジンの版 3（spin-v2）" in named("NDL-1187053-R0000014-L") and [n for n in named(T) if n.startswith("エンジンの版")] == ["エンジンの版 5"]  # 組を結ばずに刻んだ版は、案の行き先の雛形で結ぶ
assert "エンジンの版 5" not in gg
assert named("NDL-1187053-R0000014-L")["エンジンの版 3（spin-v2）"]["review"] is True and kv.tag(named("NDL-1187053-R0000014-L")["エンジンの版 3（spin-v2）"]) == "ループ 3（材料は作る前のレビュー）"
stands = [p.stem for p in (ROOT / "data/hypotheses").glob("NDL-*.json") if json.loads(p.read_text(encoding="utf-8")).get("template") == "stand_figure"]
assert all("エンジンの版 4（stand_figure-v2）" in named(sid) for sid in stands[:3])
code, lp = get("/loop")
sec = lp.split('id="versions"')[1]
assert sec.count("エンジンの版 4（stand_figure-v2）") == 1 and f"ほか {len(stands) - 1} 種" in sec, "同じ歩みの玩具は 1 枚の札にまとめる"
assert "エンジンの台帳が手元にありません" not in sec and "足の向きは絵で見せる &lt;i&gt;" in sec and "<i>" not in sec
# 共通化している知見: 版に入った部品と決まりの案と、人が書いた一覧。全部の一覧は頁の節に、玩具の札には届く物だけ。まだ版に入っていない案は出さない。形の外の行は読まない
shared = sec.split('id="shared"')[1]
for w in ("折る向きは凡例に言葉で書く", "糊代の見え方は全部の雛形でそろえる", "虎の胴だけの知見", "slider_fan の動きの床と既定の寸法"):
    assert w in shared, w
assert "まだ版に入っていない" not in sec and "形の外" not in sec and "<u>" not in sec and "&lt;u&gt;置き場&lt;/u&gt;" in shared and "&lt;u&gt;元&lt;/u&gt;" in shared
fan_card, tiger_card = sec.split(f'id="ver-{G}"')[1].split("</article>")[0], sec.split(f'id="ver-{T}"')[1].split("</article>")[0]
assert "糊代の見え方は全部の雛形でそろえる" in fan_card and "虎の胴だけの知見" not in fan_card and "虎の胴だけの知見" in tiger_card
assert "slider_fan の動きの床と既定の寸法" in fan_card and "slider_fan の動きの床と既定の寸法" not in tiger_card
assert "ループ 3（材料はループ 2）" in shared and "ループの外" in shared
# 玩具ごとの様子の頁にも同じ札が、集計の前に出る。学ぶ人の頁には出さない
tp = get(f"/loop/{G}")[1]
assert tp.index('id="versions"') < tp.index('id="k1"') and "どういう知見で良くなったか" in tp and "足の向きは絵で見せる" in tp
assert f'href="/loop/{G}#k2"' in tp
assert "版の記録はまだありません" in get(f"/loop/{OTHER}")[1].split('id="k1"')[0]
for path in ("/about", "/toys", "/", f"/toy/{G}"):
    assert "どういう知見で良くなったか" not in get(path)[1] and "ループの外" not in get(path)[1], path
# 環境の値が無い時は、隣の repo の main の中身を git から読む（隣の木は作業の途中の枝のことがある）。読めなければ、木の中のファイル
del os.environ["OMOCHAE_ENGINE_REPO"]
sibling = pathlib.Path(DATA) / "sibling" / "paper-to-toy"
(sibling / "data/engine").mkdir(parents=True)
real_root, kv.ROOT = kv.ROOT, sibling.parent / "utsushi"
git = lambda *a: subprocess.run(["git", "-C", str(sibling), "-c", "user.name=t", "-c", "user.email=t@example.com", *a], check=True, capture_output=True)
git("init", "-q")
(sibling / "data/engine/versions.json").write_text(json.dumps({"versions": [{"version": 7, "commit": "aaa1111", "at": "2026-11-06", "note": "main の版", "sheet_sets": {"slider_fan": "goraigo-v200"}, "proposals": []}], "next": []}, ensure_ascii=False), encoding="utf-8")
git("add", "-A")
git("commit", "-qm", "ledger")
git("update-ref", "refs/remotes/origin/main", "HEAD")
(sibling / "data/engine/versions.json").write_text(json.dumps({"versions": [{"version": 8, "commit": "bbb2222", "at": "2026-11-06", "note": "作業の途中の版", "sheet_sets": {"slider_fan": "goraigo-v201"}, "proposals": []}], "next": []}, ensure_ascii=False), encoding="utf-8")
assert "エンジンの版 7（goraigo-v200）" in named(G) and "エンジンの版 8（goraigo-v201）" not in named(G)
git("update-ref", "-d", "refs/remotes/origin/main")
assert "エンジンの版 8（goraigo-v201）" in named(G), "main が読めない時は、木の中のファイル"
kv.ROOT = real_root
os.environ["OMOCHAE_ENGINE_REPO"] = str(engine)
# 台帳が壊れていても頁は止めない
(engine / "data/engine/versions.json").write_text("{壊れた", encoding="utf-8")
(engine / "data/engine/shared-findings.json").write_text("{壊れた", encoding="utf-8")
code, lp = get("/loop")
assert code == 200 and "エンジンの台帳が手元にありません" in lp
print("ok: 改善の輪")
