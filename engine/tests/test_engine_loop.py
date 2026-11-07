"""エンジンごとの改善の輪（omochae.engine_loop・#63）を確かめる。束の入口 → 案 → 人の採否 → 次の版 → 版ごとの数の並び。
話した事（考え・工夫・できた後の話。#65）も束で受け、手順の番号つきの工夫から案が起きる事を見る。
前の組の紙の記録から起きた案に、今の刷った組が並ぶ事を見る（#68）。
束を受けたら、人の操作なしに案と Issue の下書きが置き場に出る事を見る（#72。立てるのは人のまま）。
人が受け入れた報告（omochae.intake の accepted）も集計され、手順の番号が紙（形）ごとに分かれる事を見る（#79）。"""
import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import engine_loop as el  # noqa: E402

SAMPLE = json.loads((ROOT / "examples/bundles/sample_made_up.json").read_text(encoding="utf-8"))
# 連絡先の形の見本は、ここで組み立てる（ファイルに番号やアドレスの形を置かない）
PHONE = "-".join(("090", "1234", "5678"))
MAIL = "yamada" + "@" + "example" + ".jp"
tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")


def cli(*args):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([sys.executable, "-m", "omochae.engine_loop", *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)


def variant(change):
    b = copy.deepcopy(SAMPLE)
    change(b)
    return b


def put(name, b):
    path = tmp / name
    path.write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
    return str(path)


# 1. 見本の束は通る。見本は束の欄を全部使う（サイトの側の試験が、同じ欄の一覧と照らすため）
assert el.check_bundle(SAMPLE) == [], [f.line() for f in el.check_bundle(SAMPLE)]
assert set(SAMPLE) == el.TOP_KEYS
assert set().union(*(set(g) for g in SAMPLE["groups"])) == el.GROUP_KEYS
assert set().union(*(set(t) for g in SAMPLE["groups"] for t in g["texts"])) == el.TEXT_KEYS
assert cli("check", "examples/bundles/sample_made_up.json").returncode == 0
# 話した事（#65）: 文の種類 3 つと、群の craft_steps。前の形の束（どちらも無い）も、そのまま通る
assert set(el.TEXT_KINDS) >= {"think", "craft", "keep"} and "craft_steps" in el.GROUP_KEYS
assert {"think", "craft", "keep"} <= {t["kind"] for g in SAMPLE["groups"] for t in g["texts"]}
TALK = ("think", "craft", "keep", "review")


def old_shape(b):
    b.pop("current_sets", None)
    for g in b["groups"]:
        g.pop("craft_steps", None)
        g["texts"] = [t for t in g["texts"] if t["kind"] not in TALK]


OLD = variant(old_shape)
assert el.check_bundle(OLD) == [] and not any("craft_steps" in g for g in OLD["groups"])
# 今の刷った組（#68）: 束の上の段の、無くてもよい欄。雛形の id ごとの組の名
assert "current_sets" in el.TOP_KEYS and "current_sets" not in OLD and SAMPLE["current_sets"]["slider_fan"] == "goraigo-v10"

# 2. 決まりの外の欄・形は、束ごと断る（rc 3・F13.bundle）。何も置かない。知らせの文に、束の値を出さない
bads = [variant(lambda b: b.update(name="山田")), variant(lambda b: b["groups"][0].update(who="abc12345")),
        variant(lambda b: b["groups"][0]["texts"][0].update(by="山田")), variant(lambda b: b.update(exported_at="2026-11-05T15:00:30+09:00")),
        variant(lambda b: b["groups"][0]["stuck_steps"].update({"99": {"taps": 1, "people": 1}})),
        variant(lambda b: b["groups"][0].update(reports=9012345678)), variant(lambda b: b["groups"][0]["texts"][0].update(text="あ" * (el.MAX_TEXT + 1))),
        variant(lambda b: b["groups"][0]["texts"][0].update(kind="name")), variant(lambda b: b["groups"][0].update(minutes=[30, 20, 3])),
        variant(lambda b: b["groups"][0]["results"].update({"山田さんの家の電話で聞いた長い長い文をここへ": 1})),
        variant(lambda b: b["groups"].append(copy.deepcopy(b["groups"][0]))), variant(lambda b: b.update(schema="other/1")), ["束でない"],
        variant(lambda b: b["groups"][0]["craft_steps"].update({"3": {"talks": 2, "people": 2, "who": ["abc12345"]}})),
        variant(lambda b: b["groups"][0]["craft_steps"].update({"41": {"talks": 1, "people": 1}})),
        variant(lambda b: b["groups"][0].update(craft_steps=["山田"])), variant(lambda b: b["groups"][0]["texts"][0].update(kind="talk")),
        variant(lambda b: b.update(current_sets={"slider_fan": "山田さんの家で刷った組"})), variant(lambda b: b.update(current_sets=["goraigo-v10"])),
        variant(lambda b: b.update(current_sets={"slider fan": "goraigo-v10"}))]
for bad in bads:
    fails = el.check_bundle(bad)
    assert fails and all(f.floor == "F13.bundle" for f in fails), bad
    assert el.take(bad)[0] is None
    assert not any("山田" in f.line() or "9012345678" in f.line() for f in fails)
assert not list((tmp / "local").glob("bundles/*.json"))
r = cli("take", put("bad.json", bads[0]))
assert r.returncode == 3 and "F13.bundle" in r.stderr and "山田" not in r.stdout + r.stderr
assert cli("take", str(tmp / "no_such.json")).returncode == 4

# 3. 連絡先の形のある文: check は F13.pii で名指しし、take はその文を落として数だけ残す。落とした文は置き場にも画面にも出ない
for text in (f"電話は {PHONE}", MAIL, "０９０１２３４５６７８ まで", "〒" + "123" + "-" + "4567", "メールで知らせて", "https://x.example/a"):
    assert el.has_contact(text), text
for fine in ("折り線の向きが分からなかった", "手順 3 で 20 分かかった", "カットラインが細い", "扇が 90 度まで開いた"):
    assert not el.has_contact(fine), fine
dirty = variant(lambda b: b["groups"][0]["texts"].append({"kind": "impression", "step": None, "text": f"連絡は {PHONE} へ", "count": 1}))
assert [f.floor for f in el.check_bundle(dirty)] == ["F13.pii"]
assert PHONE not in el.check_bundle(dirty)[0].line()
assert cli("check", put("dirty.json", dirty)).returncode == 3
r = cli("take", put("dirty.json", dirty))
assert r.returncode == 0 and "落とした文 1 件" in r.stdout and PHONE not in r.stdout + r.stderr, r.stdout + r.stderr
placed = list((tmp / "local/bundles").glob("B-*.json"))
assert len(placed) == 1 and PHONE not in placed[0].read_text(encoding="utf-8")
kept = json.loads(placed[0].read_text(encoding="utf-8"))
assert kept["dropped_pii"] == 1 and len(kept["groups"][0]["texts"]) == len(SAMPLE["groups"][0]["texts"])
# 束を受けたら、続けて案が起き、Issue の下書きが置き場に出る（#72）。人が打ったのは take の 1 回だけ。propose も adopt も打っていない
ISSUES = tmp / "local/issues"
auto = el.proposals()
assert len(auto) >= 6 and all(p["status"] == "draft" for p in auto)
assert sorted(f.stem for f in ISSUES.glob("EP-*.md")) == sorted(p["id"] for p in auto)
for p in auto:
    md = (ISSUES / f"{p['id']}.md").read_text(encoding="utf-8")
    assert all(h in md for h in ("## 目的", "## なぜか（根拠）", "## どうしたらいいか", "## ゴールの要件")), p["id"]
    assert "まだ採っていない案" in md.split("## 目的")[0] and "立てるのは人" in md.split("## 目的")[0] and PHONE not in md
    assert "`PYTHONPATH=src .venv/bin/python -m omochae.engine_loop release`" in md, "下書きの命令は README と同じ字（python の名前が無い機械でも打てる）"
assert f"新しい案 {len(auto)} 件" in r.stdout and "Issue の下書き" in r.stdout and all(p["id"] in r.stdout for p in auto)
# この道具は、外へ何も送らない（Issue を立てるのは人）。網や外の命令を使う呼び出しを持たない
code = (ROOT / "src/omochae/engine_loop.py").read_text(encoding="utf-8")
for word in ("import subprocess", "import urllib", "import socket", "import http", "import requests", "os.system", "gh issue"):
    assert word not in code, word
# 話した事（声から字にした物）も同じ床で落ちる。話した数（craft_steps）は数なので残る
spoken = variant(lambda b: b["groups"][0]["texts"].append({"kind": "craft", "step": 3, "text": f"分からなければ {PHONE} に聞いて", "count": 1}))
assert [f.floor for f in el.check_bundle(spoken)] == ["F13.pii"] and PHONE not in el.check_bundle(spoken)[0].line()

# 4. 同じ出し元の束は、新しい物だけを数える（束はその時までの全部なので、2 つ数えると 2 重になる）
newer = variant(lambda b: b.update(exported_at="2026-11-05T16:00+09:00"))
assert el.take(newer)[0] is not None
assert len(el.bundles()) == 1 and el.bundles()[0]["exported_at"] == "2026-11-05T16:00+09:00"
gs = el.groups(el.bundles())
assert gs[("slider_fan", "goraigo-v10", "")]["reports"] == 5

# 5. 案: 雛形・部品（共有の所）・生成の決まり の 3 種が出る。案は数と文だけで、新しい寸法の値を持たない。2 度起こさない
assert el.propose() == ([], [])  # 束の中身が同じなら、新しい案も、新しくする案も無い
made = el.proposals()
kinds = {p["target"]["kind"] for p in made}
assert kinds == {"template", "part", "rule"}, kinds
by_key = {p["key"]: p for p in made}
stuck = by_key["stuck:slider_fan:goraigo-v10:3"]
assert stuck["numbers"] == {"stuck_taps": 4, "stuck_people": 2, "quit_people": 1, "craft_talks": 2, "craft_people": 2, "reports": 5}
# 止まった段の案には、その段で話された工夫も付く（止まった所を、別の人がどう越えたかが並ぶ）
assert {t["kind"] for t in stuck["evidence"]} == {"stuck", "question", "craft"} and all(t["step"] == 3 for t in stuck["evidence"])
assert "stuck:slider_fan:goraigo-v10:5" not in by_key  # 1 人だけの段は案にしない
assert "stuck:pivot_counterweight:tora-v3:2" in by_key  # 印の無い記録だけの時は、札 3 回から
assert by_key["craft:slider_fan:goraigo-v10"]["numbers"] == {"fixes": 1, "ideas": 0, "craft_talks": 5, "keeps": 1, "reports": 5}
assert {t["kind"] for t in by_key["craft:slider_fan:goraigo-v10"]["evidence"]} == {"fix", "craft", "keep"}
assert by_key["craft:pivot_counterweight:tora-v3"]["numbers"] == {"fixes": 0, "ideas": 1, "craft_talks": 3, "keeps": 0, "reports": 2}  # 思いつきだけでも、工夫の言葉として案にする
assert by_key["motion:slider_fan:goraigo-v10"]["numbers"] == {"not_moved": 2, "moved": 2, "reports": 5}
# 作る前の考えは、動かない側の札が重なった時の案に付く。考えだけでは案にならない
assert {"explain", "think"} <= {t["kind"] for t in by_key["motion:slider_fan:goraigo-v10"]["evidence"]}
only_think = variant(lambda b: b.update(groups=[{"template": "slider_fan", "sheet_set": "goraigo-v10", "reports": 0,
                                                 "texts": [{"kind": "think", "step": None, "text": "扇は糸で引くと開くと思う", "count": 3}]}]))
assert el.check_bundle(only_think) == [] and el.drafts(el.groups([only_think])) == []
# 手順の番号つきの工夫: 止まったの札が重なっていない段でも、話した人が 2 人から案になる。1 人の段は案にしない。
# 止まった段の案が起きる段では、工夫はその案に付けるので、別の案を起こさない。印の無い記録だけの時は 3 件から
talk6 = by_key["talk:slider_fan:goraigo-v10:6"]
assert talk6["target"] == {"kind": "template", "name": "slider_fan"} and talk6["step"] == 6
assert talk6["numbers"] == {"craft_talks": 2, "craft_people": 2, "stuck_taps": 0, "stuck_people": 0, "reports": 5}
assert [(t["kind"], t["step"]) for t in talk6["evidence"]] == [("craft", 6)]
assert "talk:slider_fan:goraigo-v10:5" not in by_key and "talk:slider_fan:goraigo-v10:3" not in by_key
assert by_key["talk:pivot_counterweight:tora-v3:4"]["numbers"]["craft_talks"] == 3
few = el.groups([variant(lambda b: b["groups"][1]["craft_steps"].update({"4": {"talks": 2, "people": 0}}))])
assert not any(d["key"].startswith("talk:pivot_counterweight") for d in el.drafts(few))
# 前の形の束からは、前と同じ鍵の案だけが起きる（話した事の案は起きない）
assert {d["key"] for d in el.drafts(el.groups([OLD]))} == {k for k in by_key if not k.startswith(("talk:", "review:"))}
# 作る前の型紙のレビュー（経験者が、作らずに型紙を読んだ指摘）: 人が確かめた字だけが束に来るので、1 件から案にする。作っていないので、
# 止まった段にも工夫の数にも、報告の数にも入れない
rv = by_key["review:slider_fan:goraigo-v10"]
assert rv["target"] == {"kind": "template", "name": "slider_fan"} and rv["numbers"] == {"reviews": 1, "reports": 5} and "レビュー" in rv["title"]
assert [(t["kind"], t["step"], t["text"]) for t in rv["evidence"]] == [("review", 8, "このつまみの幅だと、大人の指では押しにくそう")]
assert not [k for k in by_key if k.endswith(":8") and k.startswith(("stuck:", "talk:"))]
assert "review" not in {t["kind"] for t in by_key["craft:slider_fan:goraigo-v10"]["evidence"]}
assert "作る前のレビュー（手順 8）" in el.issue_draft({**rv, "id": "EP-0000"}).split("---")[1]
only_review = variant(lambda b: b.update(groups=[{"template": "slider_fan", "sheet_set": "goraigo-v10", "reports": 0,
                                                  "texts": [{"kind": "review", "step": None, "text": "外筒の糊代が細く見える", "count": 1}]}]))
assert el.check_bundle(only_review) == [] and [d["key"] for d in el.drafts(el.groups([only_review]))] == ["review:slider_fan:goraigo-v10"]
assert "motion:pivot_counterweight:tora-v3" not in by_key
fold = by_key["shared:fold:pivot_counterweight+slider_fan"]
assert fold["target"]["kind"] == "part" and fold["numbers"]["templates"] == 2
# 今の組と同じ組の群から起きた案には、組の並びを足さない。雛形の id が要る案は、今の組を持つ
assert stuck["current_set"] == "goraigo-v10" and all("今の組" not in p["why"] for p in made)
allowed = {"id", "status", "key", "target", "template", "sheet_set", "current_set", "paper", "step", "title", "numbers", "why", "evidence", "record_ids", "in_engine", "made_at"}
for p in made:
    assert set(p) == allowed and p["status"] == "draft", set(p) ^ allowed
    assert all(isinstance(v, int) and not isinstance(v, bool) for v in p["numbers"].values())  # 数は件数だけ（寸法の値でない）
    assert not {"params", "to", "value", "from"} & set(p["target"])
assert el.propose() == ([], [])
# 前の組の紙の記録（#68）: 案は今までどおり起きる（機械が「もう直った」と決めない）。「なぜか」に、今の組と、前の組の紙の物である事が並ぶ。
# 組の分からない記録には、分からない事が並ぶ。束が今の組を持たない時は、何も足さない
def add_old(b):
    fix = {"kind": "fix", "step": None, "text": "柄 / 先に土台を足した / 台が載せやすくなった", "count": 1}
    b["groups"].append({"template": "slider_fan", "sheet_set": "goraigo-v7", "reports": 2, "texts": [fix]})
    b["groups"].append({"template": "slider_fan", "sheet_set": "", "reports": 1, "texts": [fix]})


with_old = variant(add_old)
assert el.check_bundle(with_old) == []
old = {d["key"]: d for d in el.drafts(el.groups([with_old]))}
v7, unknown = old["craft:slider_fan:goraigo-v7"], old["craft:slider_fan:"]
assert v7["current_set"] == "goraigo-v10" and "今の組は goraigo-v10" in v7["why"] and "前の組の紙の物" in v7["why"] and "先に見る" in v7["why"]
assert "今の組は goraigo-v10" in unknown["why"] and "どの組の紙の物か分からない" in unknown["why"] and "前の組" not in unknown["why"]
assert "今の組" not in old["craft:slider_fan:goraigo-v10"]["why"]
assert "今の組は goraigo-v10" in el.issue_draft({**v7, "id": "EP-0000"}).split("---")[0]
no_cur = {d["key"]: d for d in el.drafts(el.groups([variant(lambda b: (add_old(b), b.pop("current_sets")))]))}
assert set(no_cur) == set(old) and all(no_cur[k]["numbers"] == old[k]["numbers"] for k in old)  # 鍵と数は変わらない
assert all("今の組" not in d["why"] and not d["current_set"] for d in no_cur.values())
# この repo に無い雛形の群も数える（サイトの側の雛形）。案には、無い事を書く。出し元が違う束の同じ群は、足して数える
only_site = variant(lambda b: (b.update({"from": "other-site", "groups": [b["groups"][2]]}), b["groups"][0]["stuck_steps"].update({"4": {"taps": 2, "people": 2}})))
assert el.take(only_site)[0] is not None
assert el.groups(el.bundles())[("den_den", "den_den-v1", "sample-toy.H-A")]["reports"] == 2
extra = {p["key"]: p for p in el.propose()[0]}
assert (ISSUES / f"{extra['stuck:den_den:den_den-v1:sample-toy.H-A:4']['id']}.md").exists()  # 手で propose を打った時も、下書きが出る
assert extra["stuck:den_den:den_den-v1:sample-toy.H-A:4"]["in_engine"] is False
assert "今の組は den_den-v2" in extra["stuck:den_den:den_den-v1:sample-toy.H-A:4"]["why"]
assert "一覧に無い" in el.issue_draft(extra["stuck:den_den:den_den-v1:sample-toy.H-A:4"])

# 6. 採否は人が決める。名前が無いと rc 3。採った案だけが次の版の予定に入り、Issue の下書き（4 つの見出し）が出る
sid, fid, mid = stuck["id"], by_key["craft:slider_fan:goraigo-v10"]["id"], by_key["motion:slider_fan:goraigo-v10"]["id"]
r = cli("adopt", sid)
assert r.returncode == 3 and "F13.human" in r.stderr
assert cli("adopt", "EP-9999", "--by", "作る人").returncode == 3
assert cli("adopt", "../x", "--by", "作る人").returncode == 3
assert "まだ採っていない案" in (ISSUES / f"{sid}.md").read_text(encoding="utf-8") and (ISSUES / f"{fid}.md").exists()
assert cli("adopt", sid, "--by", "作る人").returncode == 0
assert cli("reject", fid, "--by", "作る人", "--note", "次の試行を待つ").returncode == 0
led = el.ledger()
assert [p["id"] for p in led["next"]] == [sid] and led["versions"] == []
ledger_text = (tmp / "versions.json").read_text(encoding="utf-8")
# 台帳は git に入る物。作った人の文も、決めた人の名前も入れない
assert "折り線の向きが分からなかった" not in ledger_text and "作る人" not in ledger_text and "evidence" not in ledger_text
draft = (tmp / "local/issues" / f"{sid}.md").read_text(encoding="utf-8")
assert all(h in draft for h in ("## 目的", "## なぜか（根拠）", "## どうしたらいいか", "## ゴールの要件")) and "足は山折りですか" in draft
assert "採った案" in draft.split("## 目的")[0] and "まだ採っていない案" not in draft
assert "止まったの札 4" in draft and "stuck_taps" not in draft  # 数は呼び方を付けて出す
assert "話した工夫（手順 3）: 「折る前に、定規で折り線をなぞった」" in draft and "craft_talks" not in draft
assert "話した工夫（手順 6）" in el.issue_draft(talk6) and "組み方の文" in el.issue_draft(talk6)
# 作った人の言葉は、4 つの見出しの外の「手元の材料」にだけ出る（Issue にそのまま写さない物として分ける）
head, _, material = draft.partition("---")
assert el.MATERIAL in material and "写さない" in material and "## " not in material
assert all(t["text"] in material and t["text"] not in head for t in stuck["evidence"]) and len(stuck["evidence"]) >= 4
assert set(el.NUMBER_JA) >= {k for p in made for k in p["numbers"]}
assert not (tmp / "local/issues" / f"{fid}.md").exists()  # 採らないと決めた案の下書きは、置き場から消える（立てる物と間違えないため）
listed = cli("list").stdout
assert f"{sid} adopted" in listed and "下書きあり" in [ln for ln in listed.splitlines() if ln.startswith(sid)][0]
assert "下書きあり" not in [ln for ln in listed.splitlines() if ln.startswith(fid)][0]
assert "（刷った組 goraigo-v10）" in [ln for ln in listed.splitlines() if ln.startswith(sid)][0]  # 同じ雛形の案を、組で見分ける
assert cli("adopt", sid, "--by", "作る人").returncode == 3  # 決め直しはしない
assert cli("adopt", fid, "--by", "作る人").returncode == 3

# 7. 次の版: commit と人が要る。刻むと、版の番号・採った案・commit が台帳に残り、予定は空になる。同じ案を 2 度刻めない
assert cli("release", "--by", "作る人").returncode == 3
assert cli("release", "--commit", "abc1234").returncode == 3
assert cli("release", "--commit", "abc1234", "--by", "作る人", "--sheet-set", "slider_fan").returncode == 3
r = cli("release", "--commit", "abc1234", "--by", "作る人", "--sheet-set", "slider_fan=goraigo-v11")
assert r.returncode == 0 and "版 1" in r.stdout, r.stdout + r.stderr
led = el.ledger()
assert led["next"] == [] and [(v["version"], v["commit"], [p["id"] for p in v["proposals"]]) for v in led["versions"]] == [(1, "abc1234", [sid])]
assert led["versions"][0]["sheet_sets"] == {"slider_fan": "goraigo-v11"}
assert json.loads((tmp / "local/proposals" / f"{sid}.json").read_text(encoding="utf-8"))["status"] == "released"
assert cli("release", "--commit", "abc1234", "--by", "作る人").returncode == 3  # 採った案が無いまま刻まない
assert cli("adopt", mid, "--by", "作る人").returncode == 0 and cli("release", "--commit", "def5678", "--by", "作る人").returncode == 0
assert [v["version"] for v in el.ledger()["versions"]] == [1, 2]
broken = el.ledger()
broken["next"].append({"id": sid, "target": {}, "title": "", "numbers": {}})
(tmp / "versions.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
assert cli("version").returncode == 4  # 同じ案が 2 度ある台帳は、読めない物として止める
broken["next"].pop()
(tmp / "versions.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")

# 7b. 束が増えて数や文が変わったら、まだ決まっていない案と下書きを新しくする（番号は同じ）。人が決めた案は書き換えない（#72）
def more(b):
    b.update(exported_at="2026-11-05T17:00+09:00")
    g = b["groups"][0]
    g["stuck_steps"]["3"] = {"taps": 9, "people": 5}  # 採って版に刻んだ案（sid）の段
    g["craft_steps"]["6"] = {"talks": 3, "people": 3}  # まだ決まっていない案（talk6）の段
    g["texts"].append({"kind": "craft", "step": 6, "text": "貼る前に、内筒を一度抜いて確かめた", "count": 1})
    g["texts"].append({"kind": "fix", "step": None, "text": "外筒 / 角を少し削った / 引っかからなくなった", "count": 1})  # 採らないと決めた案（fid）の材料


before = {p["id"]: p for p in el.proposals()}
r = cli("take", put("more.json", variant(more)))
assert r.returncode == 0 and "新しくした案 1 件" in r.stdout and talk6["id"] in r.stdout, r.stdout + r.stderr
now = {p["id"]: p for p in el.proposals()}
assert set(now) == set(before)  # 番号は増えない
t6 = now[talk6["id"]]
assert t6["status"] == "draft" and t6["numbers"]["craft_talks"] == 3 and t6["numbers"]["craft_people"] == 3 and t6["made_at"] == talk6["made_at"] and t6["renewed_at"]
md6 = (ISSUES / f"{talk6['id']}.md").read_text(encoding="utf-8")
assert "話した工夫 3" in md6 and "貼る前に、内筒を一度抜いて確かめた" in md6 and "まだ採っていない案" in md6
for pid in (sid, fid, mid):  # 採った・採らない・版に刻んだ案は、決めた時に見た数のまま
    assert now[pid] == before[pid], pid
assert "止まったの札 4" in (ISSUES / f"{sid}.md").read_text(encoding="utf-8") and not (ISSUES / f"{fid}.md").exists()
assert "新しくした案 0 件" in cli("propose").stdout  # 同じ束でもう一度打っても、何も変わらない

# 8. 並べる: 次の版の紙の束が来たら、刷った組ごとに数が並ぶ。判定の語も割合も出さない。組は名の数の順（v9 → v10 → v11）
after = variant(lambda b: (b.update(exported_at="2026-11-06T10:00+09:00"), b["current_sets"].update(slider_fan="goraigo-v11"),
                           b["groups"].append({**copy.deepcopy(b["groups"][0]), "sheet_set": "goraigo-v9", "reports": 1}),
                           b["groups"].append({"template": "slider_fan", "sheet_set": "goraigo-v11", "reports": 3, "results": {"動いた": 3},
                                               "moved_word": "動いた", "not_moved_word": "動かない", "stuck_steps": {"3": {"taps": 1, "people": 1}},
                                               "quit_steps": {}, "minutes": [10, 25, 3], "measures": {}, "record_ids": [],
                                               "texts": [{"kind": "craft", "step": 3, "text": "足の向きは、絵を見て合わせた", "count": 1}]})))
assert el.take(after)[0] is not None
r = cli("compare")
assert r.returncode == 0, r.stderr
out = r.stdout
rows = [ln for ln in out.splitlines() if ln.startswith("| goraigo-")]
# 今の組の行に印が付く。今の組は、新しい束の値で読む（前の束では v10 が今の組だった）
assert [ln.split("|")[1].strip() for ln in rows] == ["goraigo-v9", "goraigo-v10", "goraigo-v11（今の組）"], rows
assert "| goraigo-v10 | — | — | 5 件 | 動いた 2・動かない 2・わからない 1 | 手順 3: 4 回・2 人、手順 5: 1 回・1 人 | 手順 3: 1 | 20〜40（3 件） | 考え 1・工夫 5・できた後 1・レビュー 1 |" in out, out
assert f"| goraigo-v11（今の組） | — | 版 1（{sid}） | 3 件 | 動いた 3 | 手順 3: 1 回・1 人 | — | 10〜25（3 件） | 工夫 1 |" in out, out
assert "| tora-v3（今の組） |" in out
assert "| den_den-v1 | sample-toy.H-A | — | 2 件 | 鳴った 2 | 手順 4: 2 回・2 人 | — | — | — |" in out, out  # 紙の名がある群は、紙ごとの行になる
assert "判定はしない" in out and "den_den（この repo の雛形の一覧に無い）" in out
for word in ("効いた", "改善し", "良くな", "悪くな", "増えた", "減った", "上がっ", "下がっ", "%", "％", "↑", "↓", "平均"):
    assert word not in out, word

# 9. repo の台帳（git に入る物）は読めて、作った人の文の欄を持たない。知見の 1 行（finding）は採る人が自分の言葉で書いた物なので
# 欄として持ってよいが、連絡先の形が無く、長さの上限の中にある
os.environ.pop("OMOCHAE_ENGINE_LEDGER")
real = el.ledger()
assert real["versions"] and real["versions"][0]["version"] == 1
entries = [p for v in real["versions"] for p in v["proposals"]] + real["next"]
assert all(set(p) <= {"id", "target", "title", "numbers", "adopted_at", "finding"} for p in entries)
assert all(not el.has_contact(p["finding"]) and len(p["finding"]) <= el.MAX_TEXT for p in entries if "finding" in p)

# 10. 呼び方の誤り（引数なし・知らない命令・要る引数が無い・知らない印）は rc 4。1 と 2 は使わない（終了の番号の決まり。#71）。--help は rc 0
for wrong in ((), ("no_such_command",), ("take",), ("adopt",), ("release", "--no-such-flag"), ("compare", "extra")):
    r = cli(*wrong)
    assert r.returncode == 4, (wrong, r.returncode, r.stderr[-200:])
assert cli("--help").returncode == 0 and cli("take", "--help").returncode == 0

# 11. 紙（形）ごとの手順（#79）: 同じ雛形・同じ刷った組でも、紙が違えば手順の番号の意味が違う。手順ごとの案は紙ごとに起こす。
# paper の無い束は、今までどおり（上の 1〜8 がそのまま通っている）。paper は名の形だけ（自由な文を運ばせない）
def by_paper(b):
    g = copy.deepcopy(b["groups"][0])
    b["groups"] = [{**copy.deepcopy(g), "paper": "tab", "stuck_steps": {"3": {"taps": 1, "people": 1}}, "quit_steps": {}, "craft_steps": {}, "texts": []},
                   {**copy.deepcopy(g), "paper": "stick", "stuck_steps": {"3": {"taps": 1, "people": 1}, "4": {"taps": 2, "people": 2}}, "quit_steps": {"4": 1},
                    "craft_steps": {}, "texts": [{"kind": "stuck", "step": 4, "text": "柄の先の差し込みがきつい", "count": 1}]}]


papers = variant(by_paper)
assert "paper" in el.GROUP_KEYS and el.check_bundle(papers) == []
assert el.check_bundle(variant(lambda b: b["groups"][0].update(paper="山田さんの紙"))) != []
assert el.check_bundle(variant(lambda b: (by_paper(b), b["groups"][1].update(paper="tab")))) != []  # 同じ雛形・組・紙の群が 2 つ
pk = {d["key"]: d for d in el.drafts(el.groups([papers]))}
# 違う紙の「手順 3」に 1 人ずつ: 足して 2 人にしない（案にならない）。同じ紙の手順 4 に 2 人: その紙の案になる
assert not [k for k in pk if k.startswith("stuck:") and k.endswith(":3")], sorted(pk)
s4 = pk["stuck:slider_fan:goraigo-v10:stick:4"]
assert s4["paper"] == "stick" and s4["step"] == 4 and s4["numbers"]["stuck_people"] == 2 and s4["numbers"]["quit_people"] == 1
assert "stick" in s4["title"] and [t["text"] for t in s4["evidence"]] == ["柄の先の差し込みがきつい"]
# 動きの札と報告の数も紙ごと（玩具 = 雛形 + 形。別の玩具の札を足して案にしない）
assert el.groups([papers])[("slider_fan", "goraigo-v10", "stick")]["reports"] == 5 and pk["motion:slider_fan:goraigo-v10:stick"]["numbers"]["not_moved"] == 2
assert pk["motion:slider_fan:goraigo-v10:tab"]["numbers"]["not_moved"] == 2 and "motion:slider_fan:goraigo-v10" not in pk


def row_of(out, paper):
    """版ごとの数の表の、その紙の行。"""
    return next(x for x in out.splitlines() if f"| {paper} |" in x or f"| {paper}（" in x)


listed = el.compare(el.groups([papers]), {"versions": [], "next": []})
assert "手順 4: 2 回・2 人" in row_of(listed, "stick") and "手順 4" not in row_of(listed, "tab")

# 12. 人が受け入れた報告も集計する（#79）。入口（omochae.intake）の accepted だけを読み、受付箱（inbox）は読まない。
# 報告は形（form）を持つので、紙 = 形。サービスの困り事（案内・聞く口・サイトの流れ）は、エンジンの案にしない
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local2")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions2.json")
os.environ["OMOCHAE_REPORTS"] = str(tmp / "reports")
for sub in ("accepted", "inbox"):
    (tmp / "reports" / sub).mkdir(parents=True)


def report(name, where="accepted", **kw):
    r = {"template": "slider_fan", "form": "tab", "built": True, "moved": "not", "finish": 3, "reported_at": "2026-11-05T10:00:00+09:00", **kw}
    (tmp / "reports" / where / f"{name}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")


report("a1", stuck_step=3, minutes=40, motion_notes="押しても扇が出てこない",
       problems=[{"kind": "fold", "step": 3, "note": "足をどちらへ折るのかが分からない"}, {"kind": "guide", "step": 3, "note": "画面の説明の字が小さい"}])
report("a2", stuck_step=3, gave_up=True, minutes=25, finish=2)
report("b1", form="stick", moved="moved", stuck_step=3, finish=4)  # 別の形の手順 3
report("c1", template="spinner", form="pinwheel", moved="partly", problems=[{"kind": "fold", "step": 2, "note": "羽の折る向きが分かりにくい"}])
report("in1", where="inbox", stuck_step=5)
report("in2", where="inbox", stuck_step=5)  # 受付箱にあるだけの報告は、人が確かめる前なので数えない
report("bad", stuck_step=7, motion_notes=f"分からない時は {PHONE} へ")  # 受け入れた後に手で書き換えられた形。報告の検査に落ちる物は数えない
rg = el.groups(el.sources())
fan = rg[("slider_fan", "", "tab")]
assert fan["reports"] == 2 and fan["results"] == {"動かない": 2} and fan["minutes"] == [25, 40, 2], fan
assert fan["measures"]["finish"] == [2, 3, 2] and (fan["moved_word"], fan["not_moved_word"]) == ("動いた", "動かない")
assert rg[("slider_fan", "", "stick")]["results"] == {"動いた": 1}
rk = {d["key"]: d for d in el.drafts(rg)}
st = rk["stuck:slider_fan::tab:3"]
assert st["numbers"]["stuck_people"] == 2 and st["numbers"]["stuck_taps"] == 3 and st["numbers"]["quit_people"] == 1 and st["paper"] == "tab"
assert "足をどちらへ折るのかが分からない" in [t["text"] for t in st["evidence"]]
assert "stuck:slider_fan::stick:3" not in rk and not [k for k in rk if ":5" in k or ":7" in k], sorted(rk)
assert rk["motion:slider_fan::tab"]["numbers"] == {"not_moved": 2, "moved": 0, "reports": 2} and "（紙 tab）" in rk["motion:slider_fan::tab"]["title"]
# 困り事の種類が同じ物が 2 つ以上の雛形で出たら、共有の所の案（文の語でなく、報告の種類で束ねる）
fold = rk["shared:fold:slider_fan+spinner"]
assert fold["numbers"] == {"templates": 2, "texts": 2}
text_all = json.dumps(list(rk.values()), ensure_ascii=False)
assert "画面の説明の字が小さい" not in text_all and PHONE not in text_all  # サービスの困り事と、検査に落ちる報告の文は案に出ない
# 命令: propose を打つと、束が 1 つも無くても、受け入れた報告から案と Issue の下書きが出る
r = cli("propose")
assert r.returncode == 0 and "新しい案" in r.stdout and PHONE not in r.stdout + r.stderr, r.stdout + r.stderr
made2 = {p["key"]: p for p in el.proposals()}
assert set(made2) == set(rk)
md = (tmp / "local2/issues" / f"{made2['stuck:slider_fan::tab:3']['id']}.md").read_text(encoding="utf-8")
assert "まだ採っていない案" in md and "## ゴールの要件" in md and "tab" in md and "足をどちらへ折るのかが分からない" in md.split("---")[1]
out = cli("compare").stdout
# 札の数は、書かれた数（a1 は止まった手順の欄と、困り事の手順で 2 回。サービスの困り事は数えない）。人の数は報告の数
assert "手順 3: 3 回・2 人" in row_of(out, "tab") and "手順 3: 1 回・1 人" in row_of(out, "stick") and "| 不明 |" in out, out
for word in ("効いた", "改善し", "良くな", "悪くな", "%", "％", "平均"):
    assert word not in out, word

# 13. 玩具ごとの案と版（玩具 = 雛形 + 形。制作者の決定 11-05「型紙は玩具ごとに 1 枚」）。工夫・レビュー・動きの床の案も紙で分ける。
# 紙の名の無い前の形の束は、前の鍵のまま（上の 1〜8 がそのまま通っている）
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local3")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions3.json")
os.environ["OMOCHAE_REPORTS"] = str(tmp / "no-reports")


def toys(b):
    g = {**copy.deepcopy(b["groups"][0]), "template": "spinner", "sheet_set": "spin-v1", "stuck_steps": {}, "quit_steps": {}, "craft_steps": {}, "record_ids": []}
    say = lambda paper: [{"kind": "fix", "step": None, "text": f"{paper} の羽を少し細くした", "count": 1}, {"kind": "review", "step": None, "text": f"{paper} の軸の穴が小さく見える", "count": 1}]
    b["current_sets"] = {}
    b["groups"] = [{**copy.deepcopy(g), "paper": "pinwheel", "texts": say("pinwheel")}, {**copy.deepcopy(g), "paper": "top", "texts": say("top")},
                   {**copy.deepcopy(g), "template": "slider_fan", "sheet_set": "goraigo-v10", "paper": "tube", "texts": say("tube")},
                   {**copy.deepcopy(g), "template": "slider_fan", "sheet_set": "goraigo-v10", "paper": "tab", "texts": say("tab")},
                   {**copy.deepcopy(g), "template": "slider_fan", "sheet_set": "goraigo-v12", "paper": "rise", "texts": say("rise")}]


(tmp / "toys.json").write_text(json.dumps(variant(toys), ensure_ascii=False), encoding="utf-8")
assert cli("take", str(tmp / "toys.json")).returncode == 0
toy = {p["key"]: p for p in el.proposals()}
for kind in ("craft", "review", "motion"):
    # 別の玩具の声を 1 つの案に混ぜない
    assert f"{kind}:spinner:spin-v1" not in toy and {f"{kind}:spinner:spin-v1:pinwheel", f"{kind}:spinner:spin-v1:top"} <= set(toy), sorted(toy)
    assert "（紙 pinwheel）" in toy[f"{kind}:spinner:spin-v1:pinwheel"]["title"] and "（紙 pinwheel）" in toy[f"{kind}:spinner:spin-v1:pinwheel"]["why"]
    assert toy[f"{kind}:spinner:spin-v1:pinwheel"]["paper"] == "pinwheel"
for kind, word in (("craft", "羽"), ("review", "穴")):
    assert [t["text"] for t in toy[f"{kind}:spinner:spin-v1:pinwheel"]["evidence"]] == [f"pinwheel の{'羽を少し細くした' if word == '羽' else '軸の穴が小さく見える'}"]
assert toy["review:spinner:spin-v1:pinwheel"]["numbers"]["reviews"] == 1 and toy["motion:spinner:spin-v1:top"]["numbers"]["not_moved"] == 2
# 別の読みの形（ヒント）の声も案にする。機械は捨てず、型紙でない事と型紙の形を並べて、人が決める。
# 御来迎の型紙は rise（制作者の決定 2026-11-06）。前の型紙 tab で刷った紙（goraigo-v10）の声も、別の読みとして今の型紙の形を並べる
reading = toy["craft:slider_fan:goraigo-v10:tube"]
assert "別の読み" in reading["why"] and "型紙は rise" in reading["why"], reading["why"]
assert "型紙は rise" in toy["craft:slider_fan:goraigo-v10:tab"]["why"], toy["craft:slider_fan:goraigo-v10:tab"]["why"]
assert "別の読み" not in toy["craft:slider_fan:goraigo-v12:rise"]["why"] and "別の読み" not in toy["craft:spinner:spin-v1:top"]["why"]
out = cli("compare").stdout
assert "別の読み" in row_of(out, "tube") and "型紙は rise" in row_of(out, "tube") and "別の読み" not in row_of(out, "rise"), out
# 採る時に人が書く知見の 1 行は、台帳に入る（頁が読む）。書かなければ欄が無い。連絡先の形と長すぎる文は断る。採らない案には書けない
pin, top = toy["review:spinner:spin-v1:pinwheel"]["id"], toy["review:spinner:spin-v1:top"]["id"]
assert cli("adopt", pin, "--by", "作る人", "--finding", f"穴の大きさは {PHONE} へ").returncode == 3
assert cli("adopt", pin, "--by", "作る人", "--finding", "あ" * (el.MAX_TEXT + 1)).returncode == 3
assert el.ledger()["next"] == [] and json.loads((tmp / "local3/proposals" / f"{pin}.json").read_text(encoding="utf-8"))["status"] == "draft"
assert cli("reject", top, "--by", "作る人", "--finding", "書けない").returncode == 4
assert cli("adopt", pin, "--by", "作る人", "--finding", "軸の穴は、羽の幅に合わせて大きめに取る").returncode == 0
assert cli("adopt", top, "--by", "作る人").returncode == 0
next_up = {p["id"]: p for p in el.ledger()["next"]}
assert next_up[pin]["finding"] == "軸の穴は、羽の幅に合わせて大きめに取る" and "finding" not in next_up[top]
# 版は玩具ごとにも刻める（雛形 id.形）。刻むと、当たる玩具の出典が台帳に残り、版ごとの数はその紙の行にだけ版が並ぶ
r = cli("release", "--commit", "abc1234", "--by", "作る人", "--sheet-set", "spinner.pinwheel=spin-v1", "--sheet-set", "slider_fan=goraigo-v10", "--sheet-set", "no_such=x")
assert r.returncode == 0, r.stderr
ver = el.ledger()["versions"][-1]
assert ver["sources"]["spinner.pinwheel"] == ["NDL-1187053-R0000014-L-spinner"] and ver["sources"]["slider_fan"] == ["NDL-1187053-R0000005-L"] and ver["sources"]["no_such"] == []
assert ver["proposals"][0]["finding"] == "軸の穴は、羽の幅に合わせて大きめに取る"
out = cli("compare").stdout
assert "版 1" in row_of(out, "pinwheel") and "版 1" not in row_of(out, "top") and "版 1" in row_of(out, "tab") and "版 1" in row_of(out, "tube"), out

# 14. 案の番号は、置き場（git の外）だけでなく台帳（git の中）の番号とも重ねない。新しい機械や空の置き場で束を受けると、
# 番号が EP-0001 から振り直され、台帳にある案と同じ番号になって台帳が読めなくなる（README の手順の試験で見つけた）
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local4")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions4.json")
row = lambda pid: {"id": pid, "target": {"kind": "template", "name": "spinner"}, "title": "前の案", "numbers": {}}
(tmp / "versions4.json").write_text(json.dumps({"versions": [{"version": 1, "commit": "abc1234", "at": "2026-11-05", "proposals": [row("EP-0002")], "sheet_sets": {}, "note": ""}],
                                                "next": [row("EP-0005")]}, ensure_ascii=False), encoding="utf-8")
assert cli("take", str(tmp / "toys.json")).returncode == 0
fresh = sorted(p["id"] for p in el.proposals())
assert fresh and fresh[0] == "EP-0006", fresh
assert cli("adopt", fresh[0], "--by", "作る人").returncode == 0
assert [p["id"] for p in el.ledger()["next"]] == ["EP-0005", "EP-0006"]

# 15. 版に入れる案を選べる（--proposal）。直しが入った案だけを版にし、まだ直していない案は次の版の予定に残す。
# 全部を入れると、直していない案を「この版で直した」と台帳に書く事になる（11-06、虎と御来迎の直しだけが先に入った）
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local5")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions5.json")
(tmp / "versions5.json").write_text(json.dumps({"versions": [], "next": [{**row(pid), "adopted_at": "2026-11-06"} for pid in ("EP-0001", "EP-0002", "EP-0003")]}, ensure_ascii=False), encoding="utf-8")
assert cli("release", "--commit", "abc1234", "--by", "作る人", "--proposal", "EP-0009").returncode == 3, "次の版の予定に無い案は刻まない"
assert cli("release", "--commit", "abc1234", "--by", "作る人", "--proposal", "x").returncode == 3, "案の番号の形でない"
assert [p["id"] for p in el.ledger()["next"]] == ["EP-0001", "EP-0002", "EP-0003"] and not el.ledger()["versions"], "落ちた時は台帳に触らない"
r = cli("release", "--commit", "abc1234", "--by", "作る人", "--proposal", "EP-0003", "--proposal", "EP-0001", "--sheet-set", "slider_fan=goraigo-v11")
assert r.returncode == 0, r.stderr
led5 = el.ledger()
assert [p["id"] for p in led5["versions"][-1]["proposals"]] == ["EP-0001", "EP-0003"] and [p["id"] for p in led5["next"]] == ["EP-0002"]
assert cli("release", "--commit", "abc1234", "--by", "作る人").returncode == 0 and [p["id"] for p in el.ledger()["versions"][-1]["proposals"]] == ["EP-0002"], "選ばなければ全部（前と同じ）"

# 16. 雛形をまたぐ困り事の種類に、穴・足りない部品・手順と説明・接着を足した（11-06 のワークショップの感想 18 件で、制作者が挙げた
# 「穴の位置と大きさ・部品・手順の少なさ・接着」が、前の語では 1 つも共有の案にならなかった）。2 つの雛形で出たら共有の案になる
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local6")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions6.json")


def survey(b):
    g = {**copy.deepcopy(b["groups"][0]), "sheet_set": "", "stuck_steps": {}, "quit_steps": {}, "craft_steps": {}, "record_ids": [], "current_set": None}
    g.pop("current_set")
    b["current_sets"] = {}
    b["groups"] = [{**copy.deepcopy(g), "template": "spinner", "paper": "pinwheel",
                    "texts": [{"kind": "idea", "step": None, "text": "軸の穴の場所がわかりにくい", "count": 1},
                              {"kind": "keep", "step": None, "text": "組み方の手順がほしい", "count": 1}]},
                   {**copy.deepcopy(g), "template": "wheel_cart", "paper": "stick",
                    "texts": [{"kind": "keep", "step": None, "text": "車の接着がむずかしい", "count": 1},
                              {"kind": "idea", "step": None, "text": "車軸の穴が大きすぎる", "count": 1}]},
                   {**copy.deepcopy(g), "template": "lever_link", "paper": "saru_take",
                    "texts": [{"kind": "keep", "step": None, "text": "パーツが足りない気がする。作る順番を知りたい", "count": 1},
                              {"kind": "idea", "step": None, "text": "腕が外れやすいので留め方を知りたい", "count": 1}]}]


(tmp / "survey.json").write_text(json.dumps(variant(survey), ensure_ascii=False), encoding="utf-8")
assert cli("take", str(tmp / "survey.json")).returncode == 0
sk = {p["key"]: p for p in el.proposals()}
assert "shared:hole:spinner+wheel_cart" in sk, sorted(sk)
assert "shared:steps:lever_link+spinner" in sk and "shared:join:lever_link+wheel_cart" in sk, sorted(sk)
assert not any(k.startswith("shared:parts:") for k in sk), "足りない部品は 1 つの雛形だけなので、共有の案にしない"
assert [t["text"] for t in sk["shared:hole:spinner+wheel_cart"]["evidence"]] == ["軸の穴の場所がわかりにくい", "車軸の穴が大きすぎる"]

print("OK test_engine_loop")
