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

from omochae import engine_bundle as eb, hypotheses, loop, making_log, records, talk_log, trial_video  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"  # 御来迎（slider_fan）と虎（pivot_counterweight）
NOW_SET = TEMPLATES["slider_fan"].SHEET_SET
# 連絡先の形の見本は、ここで組み立てる（ファイルに番号の形を置かない）
PHONE = "-".join(("090", "1234", "5678"))
WHO1, WHO2 = "abcd1234", "wxyz5678"

# エンジンの入口（paper-to-toy の omochae.engine_loop）の一覧。片方を変える時は、両方を変える。
ENGINE_TOP = {"schema", "exported_at", "from", "dropped_pii", "current_sets", "groups"}
ENGINE_GROUP = {"template", "sheet_set", "paper", "reports", "results", "moved_word", "not_moved_word", "stuck_steps", "quit_steps", "craft_steps",
                "minutes", "measures", "record_ids", "texts"}
ENGINE_TEXT = {"kind", "step", "text", "count"}
ENGINE_KINDS = {"stuck", "fix", "idea", "impression", "question", "explain", "think", "craft", "keep", "review"}
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
# 前の札（少し動いた）で残った記録を持つ玩具。今の札に読み替えて数える事を見る（#146）
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
SPOKEN = {"think": "筒を押すと、扇が上に出て開くと思う", "craft3a": "足を先に全部折ってから扇を畳んだ", "craft3b": "折る前に定規で線をなぞった", "craft3c": "折った後に指でしごいた",
          "craft5": "つまみは最後に付けた", "keep": "薄い紙に替えたら開きやすかった", "keep_old": "台が載せにくかった", "gone": "取り下げる記録に残した話",
          "think_old": "柄で押すと、台ごと上がると思った", "hidden": "作る側が読んで隠した話"}
assert talk_log.add(G, "think", SPOKEN["think"], hypothesis_id="H-A", who=WHO1)[1] == []
assert talk_log.add(G, "craft", SPOKEN["craft3a"], hypothesis_id="H-A", sheet_version=1, step=3, who=WHO1, via="voice")[1] == []
assert talk_log.add(G, "craft", SPOKEN["craft3b"], hypothesis_id="H-A", sheet_version=1, step=3, who=WHO2)[1] == []
assert talk_log.add(G, "craft", SPOKEN["craft3c"], hypothesis_id="H-A", sheet_version=1, step=3, who=WHO1)[1] == []  # 同じ人が同じ手順で 2 回話した。人の数は増えない
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
(making_log.folder() / "talk-20261105-1201-orphan00.json").write_text(json.dumps({**hand_talk, "scene": "keep", "step": None, "record_id": "R-7777", "share": True, "text": "消えた記録に結んだ話"}, ensure_ascii=False), encoding="utf-8")
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
# 前の札の記録は今の札で数える。エンジンは今の札の言葉で数を引くので、前の札のままだと数から落ちる
pull = groups[("string_pull", "")]
assert pull["results"] == {"動いた": 1} and (pull["moved_word"], pull["not_moved_word"]) == ("動いた", "動かない"), pull

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
assert now["craft_steps"] == {"3": {"talks": 3, "people": 2}, "5": {"talks": 1, "people": 0}}, now["craft_steps"]
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

# 8. 呼び方の誤り（引数なし・知らない命令・知らない印）は rc 4。1 と 2 は使わない（Issue 313）。--help は rc 0
for wrong in ([], ["no_such_command"], ["export", "--nope"]):
    r = subprocess.run([sys.executable, "-m", "omochae.engine_bundle", *wrong], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 4, (wrong, r.returncode)
assert subprocess.run([sys.executable, "-m", "omochae.engine_bundle", "--help"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120).returncode == 0

# 9. 手で置いた記録の形が決まりの外でも、束は出る（Issue 313）。型の外の欄は読み飛ばし、その記録の動きの札は数える。
# 文字の欄を 1 字ずつの文にしない。辞書でない記録と、番号の形でない記録の番号は、束に入れない
odd = {"source_id": T, "hypothesis_id": "H-A", "sheet_version": 1, "result": "揺れた", "answers": "首の向きで止まった", "ideas": "粘土を増やす",
       "fixes": "軸を短くした", "impression": ["首が揺れて楽しかった"], "id": "R-0097", "by": "human", "recorded_at": "2026-11-05T12:30:00+09:00"}
(records.folder() / "R-0097.json").write_text(json.dumps(odd, ensure_ascii=False), encoding="utf-8")
(records.folder() / "R-0096.json").write_text(json.dumps(["記録でない"], ensure_ascii=False), encoding="utf-8")
(records.folder() / "R-0095.json").write_text(json.dumps({**odd, "id": "山田の記録", "answers": {"stuck": ["文でない"]}, "ideas": ["軸を太くしたい", 3], "fixes": [], "impression": ""}, ensure_ascii=False), encoding="utf-8")
b2 = eb.build()
text2 = json.dumps(b2, ensure_ascii=False)
tora2 = {(g["template"], g["sheet_set"]): g for g in b2["groups"]}[("pivot_counterweight", "")]
assert tora2["results"]["揺れた"] == tora["results"]["揺れた"] + 2 and tora2["reports"] == tora["reports"] + 2
assert "R-0097" in tora2["record_ids"] and "山田の記録" not in text2 and "記録でない" not in text2
assert not [t for g in b2["groups"] for t in g["texts"] if len(t["text"]) == 1], "1 字ずつの文が束に入った"
for skipped in ("首の向きで止まった", "粘土を増やす", "軸を短くした", "楽しかった", "文でない"):
    assert skipped not in text2, skipped
assert ("idea", "軸を太くしたい") in {(t["kind"], t["text"]) for t in tora2["texts"]}  # 型の合う欄は、今までどおり読む
r = subprocess.run([sys.executable, "-m", "omochae.engine_bundle", "export", "--out", str(pathlib.Path(DATA) / "bundle2.json")], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
assert r.returncode == 0, r.stderr

# 10. 刷り直しの前後（Issue 313）: 記録の紙の組は、記録の時刻までに刷った確定のうち、一番新しい物。後で刷り直しても、前の記録は前の組のまま。
# 確定より前の記録と、時刻の読めない記録は、不明の群（今の組にも、後の組にも数えない）。確定の並びの順でなく、時刻で見る
confirm = {"source_id": T, "hypothesis_id": "H-B", "version": 1, "confirmations": [
    {"by": "画面の使い手", "sheet_set": "tora-v3", "at": "2026-11-05T12:00:00+09:00"},
    {"by": "画面の使い手", "sheet_set": "tora-v2", "at": "2026-11-05T10:00:00+09:00"},
    {"by": "画面の使い手", "sheet_set": "tora-v9", "at": "読めない時刻"}]}
(loop.folder() / f"sheet-confirm-{T}-H-B-v1.json").write_text(json.dumps(confirm, ensure_ascii=False), encoding="utf-8")
for rid, at in (("R-0094", "2026-11-05T11:00:00+09:00"), ("R-0093", "2026-11-05T13:00:00+09:00"), ("R-0092", "2026-11-05T09:00:00+09:00"),
                ("R-0091", "読めない時刻"), ("R-0090", "2026-11-05T11:30+09:00")):
    rec = {"source_id": T, "hypothesis_id": "H-B", "sheet_version": 1, "result": "揺れた", "fixes": [], "id": rid, "by": "human", "recorded_at": at}
    (records.folder() / f"{rid}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
where = {rid: g["sheet_set"] for g in eb.build()["groups"] for rid in g["record_ids"]}
assert (where["R-0094"], where["R-0093"], where["R-0092"], where["R-0091"], where["R-0090"]) == ("tora-v2", "tora-v3", "", "", "tora-v2"), where

# 11. 群 1 つの文の上限（エンジンの入口は 2000 件を超えると束ごと断る）。話した字は一番数が増えるので、束の側で持つ。
# 上限を超えた時は、どの種類も残るように順に取る（並びのまま切ると、後ろの種類が丸ごと消える）。超えなければ何も変えない
few = [{"kind": "stuck", "step": None, "text": f"文{i}", "count": 1} for i in range(3)]
assert eb._cap_texts(few) == few and eb.MAX_TEXTS == 2000
many = [{"kind": k, "step": None, "text": f"{k}{i}", "count": 1} for k in ("stuck", "craft") for i in range(1500)] + [{"kind": "keep", "step": None, "text": "1 件だけの種類", "count": 1}]
capped = eb._cap_texts(many)
assert len(capped) == eb.MAX_TEXTS and {t["kind"] for t in capped} == {"stuck", "craft", "keep"}
assert [t for t in many if t in capped] == capped  # 並びは元のまま

# 13. 動画の札（試行の動画の入口 trial_video）: 札は事前の人の確かめなしで束に入る（本人の方針 11-06「こういう確認は不用です。版管理してるから」）。
# 人が外した札と、意味を付けていない機械の候補は入らない。動画の受け口の記録（学ぶ人の頁に出さない約束の記録）も、札があれば群に数える。動いたかは聞いていないので、動きの札には数えない。人の数は数えない（1 人が何本上げるか分からない）
def mark(mid, step, kind, note, ok=True, dropped=False):
    return {"id": mid, "video": "v1.mp4", "at": 12.0, "step": step, "kind": kind, "note": note, "read_by": "読んだ山田", "confirmed_by": "確かめた田中" if ok else None, "rejected_by": "外した佐藤" if dropped else None}


def video_up(rid, sheet_set, marks, note="上げた人の文で、札に書いていない話", result="わからない"):
    rec = {"source_id": T, "hypothesis_id": "H-C", "sheet_version": 1, "result": result, "sheet_set": sheet_set, "fixes": [], "note": note, "via": records.UPLOADED,
           "id": rid, "by": "human", "recorded_at": "2026-11-05T18:00:00+09:00"}
    (records.folder() / f"{rid}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    trial_video._save(rid, {"record_id": rid, "source_id": T, "hypothesis_id": "H-C", "sheet_version": 1, "sheet_set": sheet_set, "videos": [{"file": "v1.mp4", "duration": 70.0, "still": [], "attached_at": "", "checked_by": None}], "marks": marks})


video_up("R-0080", "tora-v8", [mark("M1", 2, "fold", "首の帯の折り線が見えない"), mark("M2", 2, "fold", "折る前に裏から透かして見た"), mark("M3", 4, trial_video.KUFU, "粘土を少しずつ足して揺れを見た"),
                               mark("M4", 2, "cut", "案のままの札", ok=False), mark("M5", 2, "cut", "人が外した札", ok=False, dropped=True), mark("M6", 3, "site", "画面の字が小さい札"), mark("M7", None, "other", "手順の分からない札"),
                               mark("M8", 2, "fold", f"分からない時は {PHONE} へ")])
video_up("R-0081", "tora-v8", [mark("M1", 2, "fold", "首の帯をどちらへ折るのか迷った")])
video_up("R-0082", "tora-v8", [mark("M1", 5, "fold", "案のままの札 2", ok=False)])  # 確かめの印の無い札だけの記録も数える
video_up("R-0088", "tora-v8", [mark("M1", 5, "fold", "外した札だけ", ok=False, dropped=True)])  # 外した札だけの記録は、数えない
video_up("R-0083", "tora-v7", [mark("M1", 1, "cut", "切る線が細い")], result="揺れた")  # 上げた人が結果を選んだ記録は、動きの札に数える
# 機械が作った札の案（止まった候補。意味を付けていない）は、確かめなしでは束に入らない
video_up("R-0084", "tora-v6", [{**mark("M1", None, "other", "動きの少ない区間 25〜49 秒（機械が拾った候補。意味はまだ付けていない）", ok=False), "read_by": "機械（止まった候補）"}], result="揺れた")
# 手で結んだ記録（本人の動画など。via が video）の札も同じに扱う。記録は今までどおり数えるので、2 重に数えない
hand_rid, _ = records.add({"source_id": T, "hypothesis_id": "H-B", "sheet_version": 1, "result": "揺れた", "sheet_set": "tora-v9", "fixes": []})
trial_video._save(hand_rid, {"record_id": hand_rid, "source_id": T, "hypothesis_id": "H-B", "sheet_version": 1, "sheet_set": "tora-v9", "videos": [], "marks": [mark("M1", 7, "glue", "糊がはみ出した")]})
b3 = eb.build()
text3 = json.dumps(b3, ensure_ascii=False)
g3 = {(g["template"], g["sheet_set"]): g for g in b3["groups"]}
up = g3[("pivot_counterweight", "tora-v8")]
assert up["reports"] == 3 and up["record_ids"] == ["R-0080", "R-0081", "R-0082"], up  # R-0088 は外した札だけなので数えない
assert up["results"] == {}, up["results"]  # 動いたかを聞いていない記録を、動きの札に数えない
assert up["stuck_steps"] == {"2": {"taps": 4, "people": 0}, "5": {"taps": 1, "people": 0}}, up["stuck_steps"]  # 外した札と番号の形の札は入らない。人は 0
assert up["craft_steps"] == {"4": {"talks": 1, "people": 0}}, up["craft_steps"]  # 人の工夫の札は、止まった段に数えず、工夫へ
assert {(t["kind"], t["step"], t["text"]) for t in up["texts"]} == {("stuck", 2, "首の帯の折り線が見えない"), ("stuck", 2, "折る前に裏から透かして見た"), ("stuck", 2, "首の帯をどちらへ折るのか迷った"),
                                                                    ("stuck", 2, "案のままの札"), ("stuck", 5, "案のままの札 2"),
                                                                    ("craft", 4, "粘土を少しずつ足して揺れを見た"), ("stuck", None, "手順の分からない札")}, up["texts"]
for hidden in ("外した札だけ", "人が外した札", "画面の字が小さい札", "上げた人の文", "読んだ山田", "確かめた田中", "外した佐藤", "v1.mp4", '"at"', PHONE):
    assert hidden not in text3, hidden
chose = g3[("pivot_counterweight", "tora-v7")]
assert chose["results"] == {"揺れた": 1} and (chose["moved_word"], chose["not_moved_word"]) == ("揺れた", "揺れない"), chose
assert ("pivot_counterweight", "tora-v6") not in g3 and "動きの少ない区間" not in text3
hg = g3[("pivot_counterweight", "tora-v9")]
assert hg["record_ids"] == [hand_rid] and hg["reports"] == 1 and hg["results"] == {"揺れた": 1} and hg["stuck_steps"] == {"7": {"taps": 1, "people": 0}}, hg
# 受け口の記録の、札の無い分は、今までどおり束に出ない。取り下げると、札のファイルごと消えるので束からも落ちる
assert not [g for g in b3["groups"] if "R-0088" in g["record_ids"]]
assert records.withdraw("R-0081")[1] == []
gone = {(g["template"], g["sheet_set"]): g for g in eb.build()["groups"]}[("pivot_counterweight", "tora-v8")]
assert gone["record_ids"] == ["R-0080", "R-0082"] and gone["stuck_steps"] == {"2": {"taps": 3, "people": 0}, "5": {"taps": 1, "people": 0}} and "首の帯をどちらへ折るのか迷った" not in json.dumps(gone, ensure_ascii=False)
r = subprocess.run([sys.executable, "-m", "omochae.engine_bundle", "export", "--out", str(pathlib.Path(DATA) / "bundle3.json")], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
assert r.returncode == 0, r.stderr

# 14. 作る前の型紙のレビューの動画（本人の指示 11-05 20:35）: 作っていないので、札は止まった段にも工夫の数にも入れず、種類 review の文にする。
# 報告の数にも入れない（作った人の数と混ぜない）。字の全文は記録の置き場にあるが、束には入れない
def review_up(rid, sheet_set, marks):
    video_up(rid, sheet_set, marks)
    path = records.folder() / f"{rid}.json"
    path.write_text(json.dumps({**json.loads(path.read_text(encoding="utf-8")), "video_kind": "review"}, ensure_ascii=False), encoding="utf-8")


review_up("R-0085", "tora-v5", [mark("M1", 8, "fit", "軸の穴が紙の厚みに比べて小さく見える"), mark("M2", None, trial_video.KUFU, "竹ひごの太さで揺れの速さが変わるはず"), mark("M3", 2, "fold", "案のままの指摘", ok=False), mark("M4", 3, "site", "画面の字の指摘"), mark("M5", 2, "fold", "わたしの名前は山田です、と話していた"), mark("M6", None, "guide", "題の言葉の意味が分かりづらい")])
media = records.folder() / "media" / "R-0085"
media.mkdir(parents=True, exist_ok=True)
(media / "transcript.txt").write_text("わたしは山田です。字の全文です", encoding="utf-8")
r5 = {(g["template"], g["sheet_set"]): g for g in eb.build()["groups"]}[("pivot_counterweight", "tora-v5")]
assert r5["reports"] == 0 and r5["record_ids"] == ["R-0085"] and r5["results"] == {} and r5["stuck_steps"] == {} and r5["craft_steps"] == {}, r5
# 読んでいるのは紙なので、案内の札（題や組み方の文の読みにくさ）も、紙への指摘として入れる。サイトの札は入れない
assert {(t["kind"], t["step"], t["text"]) for t in r5["texts"]} == {("review", 8, "軸の穴が紙の厚みに比べて小さく見える"), ("review", None, "竹ひごの太さで揺れの速さが変わるはず"), ("review", None, "題の言葉の意味が分かりづらい"),
                                                                    ("review", 2, "案のままの指摘")}, r5["texts"]
assert "字の全文" not in json.dumps(eb.build(), ensure_ascii=False) and "案のままの指摘" in json.dumps(r5, ensure_ascii=False) and "山田です" not in json.dumps(r5, ensure_ascii=False)  # 名乗りの形の札は入れない

# 15. 映っている紙が、受付で選ばれた玩具の紙と違う時（1 本目がそうだった。エンジンの repo の雛形の紙を読んでいた）: 人が決めて札の置き場に書いた紙に数える。
# 形の外の値は読まない（自由な文をこの欄で運ばせない）。元の玩具の群には数えない
review_up("R-0086", "tora-v4", [mark("M1", None, "mark", "折り線の表記が無く、曲げる所が読めない")])
sheet = {**trial_video.load("R-0086"), "engine_sheet": {"template": "spinner", "paper": "pinwheel", "by": "決めた本人"}}
trial_video._save("R-0086", sheet)
review_up("R-0087", "tora-v33", [mark("M1", None, "mark", "形の外の紙の欄の記録の札")])
trial_video._save("R-0087", {**trial_video.load("R-0087"), "engine_sheet": {"template": "山田さんの紙", "paper": "pinwheel"}})
b6 = eb.build()
g6 = {(g["template"], g["sheet_set"], g["paper"]): g for g in b6["groups"]}
over = g6[("spinner", "", "pinwheel")]
assert over["record_ids"] == ["R-0086"] and over["reports"] == 0 and [t["text"] for t in over["texts"]] == ["折り線の表記が無く、曲げる所が読めない"], over
assert not [k for k in g6 if k[0] == "pivot_counterweight" and k[1] == "tora-v4"] and "決めた本人" not in json.dumps(b6, ensure_ascii=False)
assert [g["record_ids"] for k, g in g6.items() if "R-0087" in g["record_ids"]] == [["R-0087"]] and [k for k, g in g6.items() if "R-0087" in g["record_ids"]][0][:2] == ("pivot_counterweight", "tora-v33")
assert "山田さんの紙" not in json.dumps(b6, ensure_ascii=False)
# 束の出し元の名（エンジンは同じ出し元の束を新しい 1 つだけ数えるので、置き場が違う束は名を分ける）。形の外は rc 4
r = subprocess.run([sys.executable, "-m", "omochae.engine_bundle", "export", "--from", "utsushi-review", "--out", str(pathlib.Path(DATA) / "bundle4.json")], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
assert r.returncode == 0 and json.loads((pathlib.Path(DATA) / "bundle4.json").read_text(encoding="utf-8"))["from"] == "utsushi-review", r.stderr
r = subprocess.run([sys.executable, "-m", "omochae.engine_bundle", "export", "--from", "山田の束", "--out", str(pathlib.Path(DATA) / "bundle5.json")], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
assert r.returncode == 4 and not (pathlib.Path(DATA) / "bundle5.json").exists(), r.stderr
assert eb.build()["from"] == "utsushi"
# 札の置き場は人が手で触るファイル。記録の番号が決まりの外の形でも、束ごと止めない（読み飛ばす。#313 の線）
before = eb.build()["groups"]
for i, odd in enumerate((["R-0086"], {"a": 1}, 86, None)):
    (pathlib.Path(DATA) / "loop" / f"video-R-08{i:02d}.json").write_text(json.dumps({"record_id": odd, "marks": [{"id": "M1", "kind": "mark", "note": "形の外の札の字", "confirmed_by": "人"}]}, ensure_ascii=False), encoding="utf-8")
assert eb.build()["groups"] == before, "形の外の札の置き場は読み飛ばす"
for i in range(4):
    (pathlib.Path(DATA) / "loop" / f"video-R-08{i:02d}.json").unlink()

# 12. 紙ごとの群（Issue 334）: 同じ雛形・同じ刷った組でも、紙（玩具と仮説と版）が違えば、手順の番号の意味が違う。違う紙の「手順 3」を足さない。
# 雛形の組み方の手順の数は、紙で違う（御来迎の 5 枚は 12・11・11・11・9 手順）
tpl = TEMPLATES["slider_fan"]
counts = [len(tpl.steps({**tpl.DEFAULTS, **h.get("params", {})})) for h in hypotheses.load(G)["hypotheses"]]
assert len(set(counts)) > 1, counts
for who, hid in ((WHO1, "H-B"), (WHO2, "H-C")):
    assert making_log.add_step(G, hid, 1, 3, "stuck", who=who) is not None
b4 = eb.build()
assert {g["paper"] for g in b4["groups"] if g["template"] == "slider_fan" and g["sheet_set"] == NOW_SET} == {f"{G}.H-A", f"{G}.H-B", f"{G}.H-C"}
p4 = {g["paper"]: g for g in b4["groups"] if g["template"] == "slider_fan" and g["sheet_set"] == NOW_SET}
assert p4[f"{G}.H-B"]["stuck_steps"] == {"3": {"taps": 1, "people": 1}} and p4[f"{G}.H-C"]["stuck_steps"] == {"3": {"taps": 1, "people": 1}}
assert p4[f"{G}.H-A"]["stuck_steps"]["3"] == {"taps": 3, "people": 2}
# 動きの札と報告の数は、紙で分けても、雛形と組で足すと同じ数になる（エンジンの側は雛形と組で足す。分けるのは手順ごとの数と文だけ）
before = [g for g in b4["groups"] if g["template"] == "slider_fan" and g["sheet_set"] == NOW_SET]
extra, fails = records.add({"source_id": G, "hypothesis_id": "H-B", "sheet_version": 1, "result": "動かない", "sheet_set": NOW_SET, "fixes": []})
assert fails == [], [f.line() for f in fails]
after_rec = [g for g in eb.build()["groups"] if g["template"] == "slider_fan" and g["sheet_set"] == NOW_SET]
assert sum(g["reports"] for g in after_rec) == sum(g["reports"] for g in before) + 1
assert sum(g["results"].get("動かない", 0) for g in after_rec) == sum(g["results"].get("動かない", 0) for g in before) + 1
assert {g["paper"]: g["reports"] for g in after_rec}[f"{G}.H-B"] == 1
# 版が違えば別の紙。紙の名は決まった形だけで、人を辿れる物でない。雛形と組と紙の組は 1 つの群だけ
v2 = [making_log.add_step(G, "H-D", 2, 4, "stuck", who=WHO1)]
assert v2[0] is not None
b5 = eb.build()
assert f"{G}.H-D.v2" in {g["paper"] for g in b5["groups"]}
keys = [(g["template"], g["sheet_set"], g["paper"]) for g in b5["groups"]]
assert len(keys) == len(set(keys)) and all(eb.NAME.fullmatch(g["paper"]) or g["paper"] == "" for g in b5["groups"])
assert all(not re.search(r"[0-9]{2}:[0-9]{2}|" + WHO1 + "|" + WHO2, g["paper"]) for g in b5["groups"])
# 動画の札の記録と、結んだ話も、その記録の紙の群に入る
assert {g["paper"] for g in b5["groups"] if g["sheet_set"] == "tora-v8"} == {f"{T}.H-C"}
assert {g["paper"] for g in b5["groups"] if ("think", SPOKEN["think_old"]) in {(t["kind"], t["text"]) for t in g["texts"]}} == {f"{G}.H-B"}

print("OK test_engine_bundle")
