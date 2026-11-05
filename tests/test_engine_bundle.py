"""エンジンへ渡す束（omochae.engine_bundle・Issue #278）。作る過程の記録を、雛形の id と刷った組ごとに束ねる口を確かめる。

見る線: 束の欄は決めた物だけ（エンジンの入口と同じ一覧）。名前・その場限りの印の値・秒・メモが束に無い。連絡先の形のある文は入らず、
落とした数だけが入る。数は件数と幅だけで、割合や平均が無い。直す前の組の記録を、今の組に数えない。書く先は git の外か out/ の下だけ。
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA

from omochae import engine_bundle as eb, hypotheses, loop, making_log, records, talk_log  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"  # 御来迎（slider_fan）と虎（pivot_counterweight）
NOW_SET = TEMPLATES["slider_fan"].SHEET_SET
# 連絡先の形の見本は、ここで組み立てる（ファイルに番号の形を置かない）
PHONE = "-".join(("090", "1234", "5678"))
WHO1, WHO2 = "abcd1234", "wxyz5678"

# エンジンの入口（paper-to-toy の omochae.engine_loop）の一覧。片方を変える時は、両方を変える。
ENGINE_TOP = {"schema", "exported_at", "from", "dropped_pii", "current_sets", "groups"}
ENGINE_GROUP = {"template", "sheet_set", "reports", "results", "moved_word", "not_moved_word", "stuck_steps", "quit_steps", "craft_steps",
                "minutes", "measures", "record_ids", "texts"}
ENGINE_TEXT = {"kind", "step", "text", "count"}
ENGINE_KINDS = {"stuck", "fix", "idea", "impression", "question", "explain", "think", "craft", "keep"}
# 話した事の種類は、話す口の場面の名と同じ（Issue 307）。場面の名が変わったら、ここで落ちて気づく
assert set(talk_log.SCENES) == {"think", "craft", "keep"} <= ENGINE_KINDS
ENGINE_MAX_TEXT, ENGINE_MAX_STEP = 300, 40
assert (set(eb.TOP_KEYS), set(eb.GROUP_KEYS), set(eb.TEXT_KEYS), set(eb.TEXT_KINDS)) == (ENGINE_TOP, ENGINE_GROUP, ENGINE_TEXT, ENGINE_KINDS)
assert (eb.SCHEMA, eb.MAX_TEXT, eb.MAX_STEP) == ("omochae.making-bundle/1", ENGINE_MAX_TEXT, ENGINE_MAX_STEP)

# 0. 記録が無い時も、空の束が出る（形は同じ）
empty = eb.build()
assert set(empty) == ENGINE_TOP and empty["groups"] == [] and empty["dropped_pii"] == 0 and empty["current_sets"] == {}

# 1. 見本の記録を置く。刷った時の確定（今の組）→ 試した記録 → 人の説明 → 手順の進み → 聞く口の質問
assert loop.confirm_sheet(G, "H-A", 1, "画面の使い手", NOW_SET) == []
rid1, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動かない", "minutes_to_try": 30, "opened_deg": 40,
                           "impression": "扇が開いた時にうれしかった", "note": "入れた人の覚え書き", "ideas": ["溝を広げたい"],
                           "answers": {"stuck": "扇の足の折り線の向きが分からなかった", "what_if": "筒を太くすると動きそう"},
                           "fixes": [{"part": "内筒", "change": "溝を 1mm 広げた", "outcome": "引っかからずに動いた"}]})
assert fails == [], [f.line() for f in fails]
rid2, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動かない", "minutes_to_try": 20, "fixes": [],
                       "impression": "長い感想" + "あ" * 400})
rid3, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "わからない", "fixes": [], "answers": {"stuck": "扇の足の折り線の向きが分からなかった"}})
# 直す前の組で試した記録（記録が組を持つ）と、刷った確定の無い記録（組が分からない）
rid4, _ = records.add({"source_id": G, "hypothesis_id": "H-B", "sheet_version": 1, "result": "動いた", "sheet_set": "goraigo-v7", "fixes": []})
rid5, _ = records.add({"source_id": G, "hypothesis_id": "H-C", "sheet_version": 1, "result": "動いた", "fixes": []})
rid6, _ = records.add({"source_id": T, "hypothesis_id": "H-A", "sheet_version": 1, "result": "揺れた", "ten_swings_sec": 8.5, "fixes": []})
# 間の札（少し動いた）を持つ雛形の玩具。動かない側の札を 2 番目と決めない事を見る
S = next(p.stem for p in sorted((ROOT / "data/hypotheses").glob("*.json")) if json.loads(p.read_text(encoding="utf-8")).get("template") == "string_pull")
rid7, fails = records.add({"source_id": S, "hypothesis_id": hypotheses.load(S)["hypotheses"][0]["id"], "sheet_version": 1, "result": "少し動いた", "fixes": []})
assert fails == [], [f.line() for f in fails]
assert all((rid2, rid3, rid4, rid5, rid6, rid7))
assert loop.save_explanation(rid1, "説明した山田", "内筒が外筒にきつくて、押しても扇が出なかった", "内筒を細くする") == []
# 手で置かれた記録（入口の床を通っていない）に、連絡先の形がある
hand = {"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた", "sheet_set": NOW_SET, "fixes": [],
        "impression": f"連絡は {PHONE} へ", "id": "R-0099", "by": "human", "recorded_at": "2026-11-05T12:00:00+09:00"}
(records.folder() / "R-0099.json").write_text(json.dumps(hand, ensure_ascii=False), encoding="utf-8")
# 長い文の、上限（300 字）で切れる所をまたいで番号がある。床は切る前の全文に当てる（切った端に番号の頭だけが残る形を作らない）
LONG = "い" * 295
hand_long = {"source_id": T, "hypothesis_id": "H-A", "sheet_version": 1, "result": "", "fixes": [], "impression": f"{LONG} {PHONE}",
             "id": "R-0098", "by": "human", "recorded_at": "2026-11-05T12:00:00+09:00"}
(records.folder() / "R-0098.json").write_text(json.dumps(hand_long, ensure_ascii=False), encoding="utf-8")

for who, events in ((WHO1, [(1, "start"), (2, "next"), (3, "stuck"), (3, "stuck")]), (WHO2, [(3, "stuck"), (3, "next"), (4, "done")]), ("", [(5, "stuck")])):
    for step, event in events:
        assert making_log.add_step(G, "H-A", 1, step, event, who=who) is not None
assert making_log.add_ask(G, "H-A", 1, "足は山折りですか", "words", step=3, who=WHO1) is not None
assert making_log.add_ask(G, "H-A", 1, "足は山折りですか？", "words", step=3, who=WHO2) is not None
assert making_log.add_ask(G, "H-A", 1, f"{PHONE} に電話してもいいですか", "words", step=2) is not None  # 残す時に文が落ちる

# 話した事（Issue 307。話す口 talk_log の記録）: 作る前の考え・作りながらの工夫（手順の番号つき）・できた後の話
SPOKEN = {"think": "筒を押すと、扇が上に出て開くと思う", "craft3a": "足を先に全部折ってから扇を畳んだ", "craft3b": "折る前に定規で線をなぞった",
          "craft5": "つまみは最後に付けた", "keep": "薄い紙に替えたら開きやすかった", "keep_old": "台が載せにくかった", "gone": "取り下げる記録に残した話",
          "think_old": "柄で押すと、台ごと上がると思った", "hidden": "作る側が読んで隠した話"}
assert talk_log.add(G, "think", SPOKEN["think"], hypothesis_id="H-A", who=WHO1)[1] == []
assert talk_log.add(G, "craft", SPOKEN["craft3a"], hypothesis_id="H-A", sheet_version=1, step=3, who=WHO1, via="voice")[1] == []
assert talk_log.add(G, "craft", SPOKEN["craft3b"], hypothesis_id="H-A", sheet_version=1, step=3, who=WHO2)[1] == []
assert talk_log.add(G, "craft", SPOKEN["craft5"], hypothesis_id="H-A", sheet_version=1, step=5)[1] == []  # その場限りの印が無い話
assert talk_log.add(G, "keep", SPOKEN["keep"], record_id=rid1, who=WHO1)[1] == []
assert talk_log.add(G, "keep", SPOKEN["keep_old"], record_id=rid4)[1] == []  # 直す前の組の紙の記録に結んだ話
# 入口の床で落ちた話（名乗りの形）は、文が残っていない。落とした数にだけ入る
assert talk_log.add(G, "craft", "わたしの名前は山田です", hypothesis_id="H-A", sheet_version=1, step=2)[0] is None
# 手で置かれた話（入口の床を通っていない）に、学校の名前の形がある。出す時にもう一度、話す口の床を当てる
hand_talk = {"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "template": "slider_fan", "sheet_set": NOW_SET, "scene": "craft", "step": 4,
             "record_id": None, "text": "桜台小学校の授業で作った時は糊を使った", "via": "text", "share": False, "who": "", "at": "2026-11-05T12:00+09:00"}
(making_log.folder() / "talk-20261105-1200-handmade.json").write_text(json.dumps(hand_talk, ensure_ascii=False), encoding="utf-8")
# 記録に結ばれた考え（記録を残した時に、話す口が結ぶ）。話の持つ組は残した時の今の組でも、結んだ記録の群に数える
(making_log.folder() / "talk-20261105-1202-boundold.json").write_text(json.dumps({**hand_talk, "scene": "think", "step": None, "record_id": rid4, "hypothesis_id": "H-B",
                                                                                 "share": True, "text": SPOKEN["think_old"]}, ensure_ascii=False), encoding="utf-8")
# 記録に結んだ後に、作る側が隠した字（読んで名前などに気づいた時に隠す）は、束にも入れない。記録そのものは、今までどおり数える
assert talk_log.add(T, "keep", SPOKEN["hidden"], record_id=rid6)[1] == [] and talk_log.set_share(T, rid6, False)[1] == []
# 記録の番号があるのに記録が無い話（記録が消えた後に残った物）は、束に入れない
(making_log.folder() / "talk-20261105-1201-orphan00.json").write_text(json.dumps({**hand_talk, "scene": "keep", "step": None, "record_id": "R-7777", "text": "消えた記録に結んだ話"}, ensure_ascii=False), encoding="utf-8")
# 取り下げた記録に結んだ話は、取り下げと一緒に消える（話す口の決まり）。束にも出ない
rid_gone, _ = records.add({"source_id": T, "hypothesis_id": "H-A", "sheet_version": 1, "result": "揺れた", "fixes": []})
assert talk_log.add(T, "keep", SPOKEN["gone"], record_id=rid_gone)[1] == [] and records.withdraw(rid_gone)[1] == []

b = eb.build()
text = json.dumps(b, ensure_ascii=False)

# 2. 束の欄は決めた物だけ。時刻は分まで。名前・その場限りの印の値・メモ・番号の形が、束のどこにも無い
assert set(b) == ENGINE_TOP and b["schema"] == eb.SCHEMA and b["from"] == "utsushi"
assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\+09:00", b["exported_at"]), b["exported_at"]
assert all(set(g) == ENGINE_GROUP for g in b["groups"])
assert all(set(t) == ENGINE_TEXT and t["kind"] in ENGINE_KINDS and 1 <= len(t["text"]) <= ENGINE_MAX_TEXT for g in b["groups"] for t in g["texts"])
for hidden in (WHO1, WHO2, "説明した山田", "画面の使い手", "入れた人の覚え書き", PHONE, "recorded_at", '"who"', '"by"', '"note"',
               '"share"', '"via"', '"scene"', "voice", "山田です", "桜台小学校", "消えた記録に結んだ話", SPOKEN["gone"], SPOKEN["hidden"], LONG[:20], PHONE[:4]):
    assert hidden not in text, hidden

# 3. 群は 雛形の id × 刷った組。直す前の組と、組の分からない記録を、今の組に数えない
groups = {(g["template"], g["sheet_set"]): g for g in b["groups"]}
assert set(groups) == {("slider_fan", NOW_SET), ("slider_fan", "goraigo-v7"), ("slider_fan", ""), ("pivot_counterweight", ""), ("string_pull", "")}, set(groups)
now = groups[("slider_fan", NOW_SET)]
assert now["reports"] == 4 and now["record_ids"] == [rid1, rid2, rid3, "R-0099"]
assert now["results"] == {"動かない": 2, "わからない": 1, "動いた": 1} and (now["moved_word"], now["not_moved_word"]) == ("動いた", "動かない")
assert groups[("slider_fan", "goraigo-v7")]["record_ids"] == [rid4] and groups[("slider_fan", "")]["record_ids"] == [rid5]
tora = groups[("pivot_counterweight", "")]
assert tora["results"] == {"揺れた": 1} and tora["measures"] == {"ten_swings_sec": [8.5, 8.5, 1]} and tora["not_moved_word"] == "揺れない"
# 間の札を持つ雛形は、動かない側を 2 番目と決めない（「少し動いた」を動かない側に数えない）
pull = groups[("string_pull", "")]
assert pull["results"] == {"少し動いた": 1} and (pull["moved_word"], pull["not_moved_word"]) == ("よく動いた", "動かない"), pull

# 3b. 今の刷った組（Issue 309）: 群に出てくる雛形だけ。エンジンの側が、前の組の紙の記録から起きた案を見分けるのに使う。
# 記録の無い雛形の組は入れない（読む物を増やさない）。値は雛形が持つ今の組の名で、記録の紙の組（goraigo-v7 など）ではない
assert b["current_sets"] == {t: TEMPLATES[t].SHEET_SET for t in ("slider_fan", "pivot_counterweight", "string_pull")}, b["current_sets"]
assert b["current_sets"]["slider_fan"] == NOW_SET != "goraigo-v7" and len(TEMPLATES) > len(b["current_sets"])

# 4. 数は件数と幅だけ。止まった段は札の数と人の数、やめた段は、できたを押していない人が最後に居た段
assert now["stuck_steps"] == {"3": {"taps": 3, "people": 2}, "5": {"taps": 1, "people": 0}}, now["stuck_steps"]
assert now["quit_steps"] == {"3": 1}, now["quit_steps"]
assert now["minutes"] == [20, 30, 2] and now["measures"] == {"opened_deg": [40, 40, 1]}
for g in b["groups"]:
    assert not {"rate", "percent", "mean", "average", "rank", "score"} & set(g)

# 5. 文: 止まった所・直した点・思いつき・感想・質問・人の説明。同じ文は回数にまとめる。長い感想は頭だけ。メモは入れない
texts = {(t["kind"], t["step"], t["text"]): t["count"] for t in now["texts"]}
assert texts[("stuck", None, "扇の足の折り線の向きが分からなかった")] == 2
assert texts[("fix", None, "内筒 / 溝を 1mm 広げた / 引っかからずに動いた")] == 1
assert texts[("idea", None, "溝を広げたい")] == 1 and texts[("idea", None, "筒を太くすると動きそう")] == 1 and texts[("idea", None, "内筒を細くする")] == 1
assert texts[("explain", None, "内筒が外筒にきつくて、押しても扇が出なかった")] == 1
assert texts[("question", 3, "足は山折りですか")] == 1 and texts[("question", 3, "足は山折りですか？")] == 1
long = [t for t in now["texts"] if t["text"].startswith("長い感想")]
assert len(long) == 1 and len(long[0]["text"]) == ENGINE_MAX_TEXT and long[0]["text"].endswith("…")

# 5b. 話した事: 場面が文の種類になり、工夫は手順の番号つき。同じ手順で工夫を話した数と、その場限りの印で数えた人の数が craft_steps に入る
assert texts[("think", None, SPOKEN["think"])] == 1 and texts[("keep", None, SPOKEN["keep"])] == 1
assert texts[("craft", 3, SPOKEN["craft3a"])] == 1 and texts[("craft", 3, SPOKEN["craft3b"])] == 1 and texts[("craft", 5, SPOKEN["craft5"])] == 1
assert now["craft_steps"] == {"3": {"talks": 2, "people": 2}, "5": {"talks": 1, "people": 0}}, now["craft_steps"]
# 記録に結んだ話は、その記録と同じ群に入る（直す前の組の紙の記録の話を、今の組に数えない）
old_texts = {(t["kind"], t["text"]) for t in groups[("slider_fan", "goraigo-v7")]["texts"]}
assert ("keep", SPOKEN["keep_old"]) in old_texts and ("keep", SPOKEN["keep_old"]) not in {(t["kind"], t["text"]) for t in now["texts"]}
assert ("think", SPOKEN["think_old"]) in old_texts and ("think", SPOKEN["think_old"]) not in {(t["kind"], t["text"]) for t in now["texts"]}
assert all(g["craft_steps"] == {} for k, g in groups.items() if k != ("slider_fan", NOW_SET))
assert rid_gone not in tora["record_ids"] and rid6 in tora["record_ids"] and not [t for t in tora["texts"] if t["kind"] == "keep"]

# 6. 連絡先の形のある文は入らず、落とした数だけが入る（出す時に落とした 1 件と、残す時に落ちていた質問 1 件）。
# 話した事は、入口の床で落ちた 1 件（名乗り）と、出す時に落とした 1 件（手で置いた話の学校の名前）。
# 上限で切れる所をまたぐ番号の文も、切る前の全文で見て落とす（1 件）
assert b["dropped_pii"] == 5, b["dropped_pii"]

# 7. 書く先は git の外か out/ の下だけ。repo の中の、git に入る所へは書かない（rc 4）
for bad in (ROOT / "docs" / "bundle.json", ROOT / "data" / "bundle.json", ROOT / "bundle.json"):
    try:
        eb.out_path(str(bad))
        raise AssertionError(f"断らなかった: {bad.name}")
    except ValueError:
        pass
assert eb.out_path(str(ROOT / "out" / "engine-bundle" / "x.json")).name == "x.json"
env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
r = subprocess.run([sys.executable, "-m", "omochae.engine_bundle", "export", "--out", str(ROOT / "docs" / "bundle.json")], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
assert r.returncode == 4 and not (ROOT / "docs" / "bundle.json").exists(), r.stderr
out = pathlib.Path(DATA) / "bundle.json"
r = subprocess.run([sys.executable, "-m", "omochae.engine_bundle", "export", "--out", str(out)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
assert r.returncode == 0 and "落とした文 5" in r.stdout and PHONE not in r.stdout + r.stderr, r.stdout + r.stderr
written = json.loads(out.read_text(encoding="utf-8"))
assert {**written, "exported_at": ""} == {**eb.build(), "exported_at": ""}

print("OK test_engine_bundle")
