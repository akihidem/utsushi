"""鍵なしで 4 つのループを一周回す入口の試験（#335）。

なぜ期待を部品の有無から組むか: 話す口・ループ1・ループ2・束の話した事は別々の枝から入る。部品が入るたびにこの試験を直さなくて済むよう、
期待はその場で部品の有無から組む。部品が入ると通る段が増え、同じ試験がそのまま厚くなる。
エンジンの repo は機械によって有無が違うので、ここでは本物を呼ばず、呼び方を偽の repo で見る（本物で回した結果は関門の帳面に書く）。
"""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from unittest import mock

WATCH = tempfile.mkdtemp()  # 本物の置き場の代わりに見張る。入口はここに書かないはず
os.environ["OMOCHAE_DATA"] = WATCH
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(WATCH, "api-usage.jsonl")
os.environ["ANTHROPIC_API_KEY"] = "x"  # 鍵の値は使われないはず。入口の間は環境から外れる

from omochae import cycle, engine_bundle, hypotheses, loop, records  # noqa: E402
from omochae.model import Failure  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
NO_ENGINE = os.path.join(WATCH, "no-such-engine")
env_before = dict(os.environ)
missing = [(cycle.PARTS[p]["stage"], cycle.PARTS[p]["label"]) for p in cycle.PARTS if not cycle.has(p)]
order = [name for name, _ in cycle.STAGES]


def after(name):
    return order[order.index(name) + 1:]


# 1. 既定は、部品の無い段で名指しして止まる。止まった後ろは回さない。全部の部品があれば最後まで通り、エンジンの repo が無ければ飛ばす印を出す
res = cycle.run(engine_repo=NO_ENGINE)
got = [s.name for s in res.stages]
assert got == order[: len(got)], got
assert not [s for s in res.stages if s.status == cycle.FAILED], res.stages
assert res.stage("最初の紙").status == cycle.PASSED, res.stages
stop = min(missing, key=lambda m: order.index(m[0])) if missing else None
if stop:
    assert res.rc == 4 and res.stages[-1].status == cycle.NOT_YET and res.stages[-1].name == stop[0], (res.rc, res.stages)
    assert stop[1] in res.stages[-1].detail, res.stages[-1]
else:
    assert res.rc == 0 and res.stage("エンジンの入口と下書き").status == cycle.SKIPPED, (res.rc, res.stages)

# 2. 本物の置き場に書かない。環境の値は元に戻す
assert os.listdir(WATCH) == [], os.listdir(WATCH)
assert dict(os.environ) == env_before

# 3. 後ろの段も見る形では、部品のある段が全部通る。部品の無い段だけが印を出す
kept = pathlib.Path(tempfile.mkdtemp()) / "kept"
res = cycle.run(keep_going=True, keep=kept, engine_repo=NO_ENGINE)
assert [s.name for s in res.stages] == order, res.stages
assert res.rc == (4 if missing else 0), (res.rc, res.stages)
not_yet = {s.name for s in res.stages if s.status == cycle.NOT_YET}
assert not_yet == {m[0] for m in missing}, (not_yet, missing)
assert {s.status for s in res.stages} <= {cycle.PASSED, cycle.NOT_YET, cycle.SKIPPED}, res.stages
for name in ("最初の紙", "記録", "人の説明", "人の解釈と次の版の紙"):
    assert res.stage(name).status == cycle.PASSED, res.stages
engine = res.stage("エンジンの入口と下書き")
assert engine.status == cycle.SKIPPED and "手元に無い" in engine.detail, engine
OWN_STAGE = "自分の紙で作って記録"
assert OWN_STAGE in order, "ループ1 で作った紙で作って記録する段が無い"
OWN_NEXT = "自分の紙の記録から次の版"
assert OWN_NEXT in order, "自分の紙の記録から次の版を見る段が無い"
if cycle.has("think_sheet"):
    assert res.stage(OWN_STAGE).status == cycle.PASSED, res.stages
    assert res.stage(OWN_NEXT).status == (cycle.PASSED if cycle.has("own_next") else cycle.NOT_YET), res.stages

# 4. 次の版の紙が刷れて、次の人の型紙になる。前の版と記録は残る（本人の方針 11-05）
os.environ["OMOCHAE_DATA"] = str(kept / "data")
hid = hypotheses.sheet_id(hypotheses.load(G)) or hypotheses.load(G)["hypotheses"][0]["id"]  # たたき台は組ごと（御来迎の次の組は H-C）
# 自分の紙の記録がたたき台の版 2 を作ると、たたき台で進む人の次の版は版 3 になる
walked = res.stage(OWN_NEXT).status == cycle.PASSED
assert loop.latest_version(G, hid) == (3 if walked else 2), (walked, loop.latest_version(G, hid))
assert loop.version_params(G, hid, 1)[0] == next(h for h in hypotheses.load(G)["hypotheses"] if h["id"] == hid)["params"], "前の版が変わった"
assert (hypotheses.play_dir(G) / f"{hid}_v2.pdf").exists() and (hypotheses.play_dir(G) / f"{hid}_v1.pdf").exists(), "前の版の紙は残る"
if walked:
    made = loop.version_params(G, hid, 2)[1]
    assert made["record_ids"] == [res.context.own_rid], made
    assert (hypotheses.play_dir(G) / f"{hid}_v3.pdf").exists() and loop.version_params(G, hid, 3)[1]["record_ids"] == [res.context.rid]
    assert loop.adopted_versions(G, res.context.own_id) == [], "自分の紙に版が足された"
rid = res.context.rid
assert loop.confirmed(rid), "人の解釈が確定していない"
assert loop.explanation(rid)["by"] == cycle.BY
# ループ1 で作った紙の記録に、その紙で話した工夫と元の考えが結ばれる。たたき台の記録には混ざらない
if cycle.has("think_sheet"):
    from omochae import talk_log  # noqa: E402

    mine = [r for r in records.all_records(G) if r["hypothesis_id"].startswith("OWN-")]
    assert len(mine) == 1 and mine[0]["id"] == res.context.own_rid and mine[0]["sheet_version"] == 1, mine
    said = {t["when"]: t["text"] for t in talk_log.kufu(G, mine[0]["id"])}
    assert said.get("making") == cycle.OWN_CRAFT and said.get("idea") == cycle.OWN_THINK, said
    base_said = [t["text"] for t in talk_log.kufu(G, rid)]
    assert cycle.CRAFT in base_said and cycle.OWN_CRAFT not in base_said, base_said

# 5. 束に記録が入る。束はエンジンの入口の形（欄の一覧）を外れない
bundle = json.loads((kept / "bundle.json").read_text(encoding="utf-8"))
assert bundle["schema"] == engine_bundle.SCHEMA and set(bundle) == set(engine_bundle.TOP_KEYS), sorted(bundle)
groups = [g for g in bundle["groups"] if rid in g["record_ids"]]
assert len(groups) == 1 and {t["kind"] for t in groups[0]["texts"]} >= {"fix", "idea"} and groups[0]["sheet_set"], groups
if cycle.has("bundle_talk") and cycle.has("talk_log"):
    said = {t["text"] for t in groups[0]["texts"]}
    assert {cycle.CRAFT, cycle.KEEP} <= said, said
    if cycle.has("think_sheet"):
        assert cycle.OWN_CRAFT in {t["text"] for g in bundle["groups"] for t in g["texts"]}, "自分の紙で話した工夫が束に無い"
os.environ["OMOCHAE_DATA"] = WATCH

# 6. 話した字は床を通った物だけが輪へ渡る。声そのものは残らない。鍵を使わない（台帳が無い）
for p in kept.rglob("*"):
    if p.is_file():
        assert p.suffix.lower() not in cycle.VOICE_SUFFIXES, p.name
        data = p.read_bytes()
        assert all(x.encode() not in data for x in cycle.PROBE_MARKS), p.name
assert not list(kept.rglob("api-usage*")), "鍵なしの入口が API を呼んだ"

# 7. 必須 2 種の外の玩具でも、同じ道で次の版まで通る
other = cycle.run(toy="NDL-1187053-R0000004-L", keep_going=True, engine_repo=NO_ENGINE)
assert {s.status for s in other.stages} <= {cycle.PASSED, cycle.NOT_YET, cycle.SKIPPED}, other.stages
assert other.stage("人の解釈と次の版の紙").status == cycle.PASSED, other.stages
# 節を出さない玩具には受け口も無いので、ループ1 の 2 つの段は飛ばす印を出す（節を出す玩具では通る）
if cycle.has("think_sheet"):
    from web import think_sheet  # noqa: E402

    want = cycle.PASSED if think_sheet.ready("NDL-1187053-R0000004-L") else cycle.SKIPPED
    assert other.stage("ループ1 の紙").status == want and other.stage(OWN_STAGE).status == want and other.stage(OWN_NEXT).status == want, other.stages

# ここから後は、段の式を見る試験を何度も回す。紙を本当に刷ると 1 回ごとに数秒かかり、./run.sh の 1 本の上限（300 秒）に混んだ機械で届く。
# 紙は 3 と 7 の本物の一周が刷っているので、ここでは刷った形の空のファイルを置くだけにする。


def light_print(source_id, hid, out, version=1, pending=None):
    pathlib.Path(f"{out}.pdf").write_bytes(b"%PDF-1.4")
    return 0


light = mock.patch.multiple(hypotheses, print_sheet=light_print, print_own=light_print)
light.start()

# 8. 部品が抜けると、その段で止まる（今ある部品を 1 つずつ抜いて見る。入るたびに、ここの数が増える）
for part in [p for p in cycle.PARTS if cycle.has(p)]:
    with mock.patch.object(cycle, "has", lambda p, part=part, real=cycle.has: p != part and real(p)):
        r = cycle.run(engine_repo=NO_ENGINE)
    assert r.stages[-1].status == cycle.NOT_YET and r.rc == 4, (part, r.stages)
    first = min((cycle.PARTS[p]["stage"] for p in cycle.PARTS if p == part or not cycle.has(p)), key=order.index)
    assert r.stages[-1].name == first, (part, r.stages)
with mock.patch.object(cycle, "has", lambda p: False):
    r = cycle.run(engine_repo=NO_ENGINE)
assert [s.name for s in r.stages] == order[: order.index("話した字") + 1] and r.rc == 4, r.stages

# 頁の道が切れたら、その段で落ちる。関数だけを通すと気づけない所（自分の紙の頁が開かない形が、実際に通ってしまった）
if cycle.has("think_sheet") and cycle.has("material") and cycle.has("bundle_talk"):
    from api import words  # noqa: E402
    from omochae import making_log  # noqa: E402
    from web import toy  # noqa: E402

    real_talk, real_build = loop.maker_talk, engine_bundle.build

    def no_own_talk(rid):  # 自分の紙の記録だけ、話した字が材料に渡らない形
        return {**real_talk(rid), "items": []} if records.all_records(G)[0]["id"] == rid else real_talk(rid)

    def no_own_bundle():  # 自分の紙で話した工夫だけ、束に入らない形
        b = real_build()
        return {**b, "groups": [{**g, "texts": [t for t in g["texts"] if t["text"] != cycle.OWN_CRAFT]} for g in b["groups"]]}

    MATERIAL, BUNDLE = "ループ2 の材料", "ループ3 の束"
    cuts = (("自分の紙の頁が開かない", mock.patch.object(think_sheet, "mine", lambda handler, sid: set()), OWN_STAGE, "開かない"),
            ("ほかの人の画面にも開く", mock.patch.object(think_sheet, "mine", lambda handler, sid: {"OWN-1"}), OWN_STAGE, "ほかの人"),
            ("記録の後も開く", mock.patch.object(words, "key_open", lambda w: True), OWN_STAGE, "記録の後"),
            ("工夫を記録に結ばない", mock.patch.object(talk_log, "bind", lambda *a: (0, 0)), OWN_STAGE, "結ばれ"),
            ("札を受けない", mock.patch.object(making_log, "EVENTS", ()), OWN_STAGE, "札を受けない"),
            ("工夫を受けない", mock.patch.object(think_sheet, "usable", lambda handler, sid, hid: False), OWN_STAGE, "工夫を受けない"),
            ("記録の欄に出ない", mock.patch.object(toy, "record_form", lambda *a, **k: ""), OWN_STAGE, "記録の欄"),
            ("工夫が材料に渡らない", mock.patch.object(loop, "maker_talk", no_own_talk), MATERIAL, "材料に無い"),
            ("工夫が束に渡らない", mock.patch.object(engine_bundle, "build", no_own_bundle), BUNDLE, "束に無い"))
    if cycle.has("own_next"):
        from web import play_server  # noqa: E402

        real_versions, real_params = loop.adopted_versions, loop.version_params

        def versions_on_own(sid, h):  # 自分の紙に版が足された形
            return [2] if str(h).startswith("OWN-") else real_versions(sid, h)

        def wrong_evidence(sid, h, version):  # 版 2 の根拠が別の記録の形
            params, made = real_params(sid, h, version)
            return (params, {**made, "record_ids": ["R-9999"]}) if version == 2 and made else (params, made)

        def extra_param(sid, h, version):  # たたき台の版 2 に、選んだ寸法のほかの違いが入った形
            params, made = real_params(sid, h, version)
            return ({**params, "混ざった": 1}, made) if version == 2 and made else (params, made)

        def no_paper(missing):  # その版の紙だけ、刷ったのにファイルが無い形
            return lambda source_id, hid, out, version=1, pending=None: 0 if version == missing else light_print(source_id, hid, out, version, pending)

        real_next = loop.next_version

        def two_versions(rid, by, content, change, source, sheet_dir):  # 1 回の操作で版が 2 つ足された形
            out = real_next(rid, by, content, change, source, sheet_dir)
            sid, base = source["source_id"], loop.next_target(source["source_id"], loop.record(rid)["hypothesis_id"])
            done = loop.folder() / f"version-{sid}-{base}-2.json"
            (loop.folder() / f"version-{sid}-{base}-3.json").write_text(done.read_text(encoding="utf-8"), encoding="utf-8")
            return out

        cuts += (("次の版を自分の紙へ向ける", mock.patch.object(loop, "next_target", lambda sid, h: h), OWN_NEXT, "次の版の欄が出ない"),
                 ("説明を受けない", mock.patch.object(loop, "save_explanation", lambda *a: [Failure("F9.human", "x", "受けない")]), OWN_NEXT, "説明を受けない"),
                 ("次の版の欄が出ない", mock.patch.object(toy, "next_form", lambda *a, **k: ""), OWN_NEXT, "欄が出ない"),
                 ("自分の紙に版が足される", mock.patch.object(loop, "adopted_versions", versions_on_own), OWN_NEXT, "版が足された"),
                 ("版 2 の根拠が別の記録", mock.patch.object(loop, "version_params", wrong_evidence), OWN_NEXT, "根拠"),
                 ("版 2 にほかの違いが入る", mock.patch.object(loop, "version_params", extra_param), OWN_NEXT, "ほかの違い"),
                 ("次の人が刷れない", mock.patch.object(play_server, "print_latest", lambda sid, h: None), OWN_NEXT, "刷れない"),
                 ("次の版が床に落ちる", mock.patch.object(loop, "next_version", lambda *a: (None, [Failure("F7.revision", "x", "落ちた")])), OWN_NEXT, "次の版を受けない"),
                 ("次の人が刷っても版を残さない", mock.patch.object(play_server, "print_latest", lambda sid, h: 2), OWN_NEXT, "版 2 でない"),
                 ("版 2 の紙が無い", mock.patch.object(hypotheses, "print_sheet", no_paper(2)), OWN_NEXT, "版 2 の紙が開かない"),
                 ("前の版の紙が無い", mock.patch.object(hypotheses, "print_sheet", no_paper(1)), OWN_NEXT, "版 1 の紙が開かない"),
                 ("版が 2 つ足される", mock.patch.object(loop, "next_version", two_versions), OWN_NEXT, "版 2 にならない"))
    for why, cut, where, word in cuts:
        with cut:
            r = cycle.run(engine_repo=NO_ENGINE)
        assert r.rc == 3 and r.stages[-1].status == cycle.FAILED and r.stages[-1].name == where and word in r.stages[-1].detail, (why, r.stages)

# 段の間は、鍵が環境に無く、置き場は一時の場所
inside = {}
with mock.patch.object(cycle, "STAGES", (("見る", lambda c: inside.update(key=os.environ.get("ANTHROPIC_API_KEY"), data=os.environ["OMOCHAE_DATA"])),)):
    assert cycle.run(engine_repo=NO_ENGINE).rc == 0
assert inside["key"] is None, "鍵が環境に残っている"
assert not pathlib.Path(inside["data"]).is_relative_to(WATCH) and not pathlib.Path(inside["data"]).is_relative_to(ROOT), inside

# 部品の形が変わって例外が出ても、段の名前と一緒に知らせて 3 で止まる
with mock.patch.object(cycle.engine_bundle, "build", side_effect=TypeError("形が違う")):
    r = cycle.run(keep_going=True, engine_repo=NO_ENGINE)
assert r.rc == 3 and r.stages[-1].status == cycle.FAILED and r.stages[-1].name == "ループ3 の束" and "形が違う" in r.stages[-1].detail, r.stages

# 落ちた段では、後ろの段を回さない（--keep-going でも。後ろの段が前の結果を使うため）
ran = []


def raises(c):
    raise cycle.Failed("つながらない")


fake_stages = (("前", lambda c: ran.append("前")), ("落ちる", raises), ("後ろ", lambda c: ran.append("後ろ")))
for going in (False, True):
    ran.clear()
    with mock.patch.object(cycle, "STAGES", fake_stages):
        r = cycle.run(keep_going=going, engine_repo=NO_ENGINE)
    assert ran == ["前"] and [s.status for s in r.stages] == [cycle.PASSED, cycle.FAILED] and r.rc == 3, (going, ran, r.stages)
    assert "つながらない" in r.stages[-1].detail, r.stages

# 段 10 は、声と映像の形のファイルと、床に当たるはずの字を、全部のファイルから探す。話した字が無ければ飛ばす
floor = pathlib.Path(tempfile.mkdtemp())
(floor / "clean.json").write_text("{}", encoding="utf-8")
c = cycle.Context(sid=G, folder=floor, talked=True)
assert "1" in cycle.stage_floor(c)
for suffix in sorted(cycle.VOICE_SUFFIXES):
    bad = floor / f"voice{suffix.upper()}"  # 字の大きさの違いでも見つける
    bad.write_bytes(b"")
    try:
        cycle.stage_floor(c)
        raise AssertionError(f"声の形を見逃した: {suffix}")
    except cycle.Failed as e:
        assert bad.name in str(e), e
    bad.unlink()
(floor / "deep").mkdir()
for mark in cycle.PROBE_MARKS:
    bad = floor / "deep" / "talk.json"
    bad.write_text(json.dumps({"text": f"前 {mark} 後"}, ensure_ascii=False), encoding="utf-8")
    try:
        cycle.stage_floor(c)
        raise AssertionError(f"床に当たる字を見逃した: {mark}")
    except cycle.Failed as e:
        assert bad.name in str(e), e
    bad.unlink()
c.talked = False
try:
    cycle.stage_floor(c)
    raise AssertionError("話した字が無いのに床を見たと言った")
except cycle.Skipped as e:
    assert "話した字" in str(e), e

# 段 2 は、床に当たる字が残らない事を本当に試す。話す口が字を残したら落ちる（話す口の床を試さなくなると、ここで分かる）
if cycle.has("talk_log"):
    from omochae import talk_log  # noqa: E402

    tried = []

    def keeps(sid, scene, text, **kw):
        tried.append(text)
        return "残した", []

    with mock.patch.object(talk_log, "add", keeps):
        try:
            cycle.stage_talk(cycle.Context(sid=G, folder=floor, hid=hypotheses.sheet_of(G)["id"]))
            raise AssertionError("床に当たる字が残ったのに通った")
        except cycle.Failed as e:
            assert "床に当たる" in str(e), e
    assert set(tried) & set(cycle.PROBES), tried
    assert all(any(mark in probe for probe in cycle.PROBES) for mark in cycle.PROBE_MARKS), "探す字と試す字が合っていない"

light.stop()

# 9. エンジンの入口の呼び方。偽の repo で、置き場の向け先と鍵を見る。本物の repo の置き場と台帳に書かない
fake = pathlib.Path(tempfile.mkdtemp()) / "engine"
(fake / "src/omochae").mkdir(parents=True)
(fake / "src/omochae/__init__.py").write_text("", encoding="utf-8")
(fake / "src/omochae/engine_loop.py").write_text(
    """import json, os, pathlib, sys
here = pathlib.Path(os.environ["OMOCHAE_ENGINE_LOOP"])
(here / "issues").mkdir(parents=True, exist_ok=True)
mode = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
env = {k: os.environ.get(k) for k in ("OMOCHAE_ENGINE_LOOP", "OMOCHAE_ENGINE_LEDGER", "ANTHROPIC_API_KEY", "PYTHONPATH")}
(here / "seen.json").write_text(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "env": env}), encoding="utf-8")
if mode == "ok":
    (here / "issues" / "EP-0001.md").write_text("下書き", encoding="utf-8")
if mode == "refuse":
    print("FAIL 束の形が違う", file=sys.stderr)
    sys.exit(3)
""",
    encoding="utf-8",
)
work = pathlib.Path(tempfile.mkdtemp())
(work / "bundle.json").write_text("ok", encoding="utf-8")
c = cycle.Context(sid=G, folder=work, engine_repo=fake)
c.bundle = work / "bundle.json"
detail = cycle.stage_engine(c)
assert "1" in detail, detail
seen = json.loads((work / "engine-loop/seen.json").read_text(encoding="utf-8"))
assert seen["argv"] == ["take", str(work / "bundle.json")], seen
assert pathlib.Path(seen["cwd"]).resolve() == fake.resolve(), seen
assert seen["env"]["OMOCHAE_ENGINE_LOOP"] == str(work / "engine-loop"), seen
assert pathlib.Path(seen["env"]["OMOCHAE_ENGINE_LEDGER"]).is_relative_to(work), seen
assert seen["env"]["PYTHONPATH"] == str(fake / "src"), seen
assert seen["env"]["ANTHROPIC_API_KEY"] is None, "鍵を渡した"
assert not (fake / "local").exists() and not (fake / "data").exists(), "本物の置き場に書いた"
(work / "bundle.json").write_text("no-draft", encoding="utf-8")
c.folder = pathlib.Path(tempfile.mkdtemp())
c.bundle = work / "bundle.json"
try:
    cycle.stage_engine(c)
    raise AssertionError("案が起きないのに通った")
except cycle.Failed as e:
    assert "下書き" in str(e), e
(work / "bundle.json").write_text("refuse", encoding="utf-8")
try:
    cycle.stage_engine(c)
    raise AssertionError("入口が断ったのに通った")
except cycle.Failed as e:
    assert "rc 3" in str(e) and "束の形が違う" in str(e), e
# 探す順: 渡された所だけを見る。渡されなければ環境の値
assert cycle.find_engine_repo(str(fake)) == fake and cycle.find_engine_repo(NO_ENGINE) is None
with mock.patch.dict(os.environ, {"OMOCHAE_ENGINE_REPO": str(fake)}):
    assert cycle.find_engine_repo() == fake
    assert cycle.find_engine_repo(NO_ENGINE) is None, "渡された場所が無いのに、ほかを見た"

# 10. 命令。結果の終わりの値は段の結果どおり。手元のパスを出さない。呼び方の誤りは 4
env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
env["PYTHONPATH"] = "src"
cli = subprocess.run([sys.executable, "-m", "omochae.cycle", "--engine-repo", NO_ENGINE], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
assert cli.returncode == (4 if missing else 0), (cli.returncode, cli.stdout[-300:], cli.stderr[-300:])
assert "段 1 最初の紙: 通った" in cli.stdout, cli.stdout
assert str(ROOT) not in cli.stdout and tempfile.gettempdir() not in cli.stdout and "/home/" not in cli.stdout, cli.stdout
assert cycle.main(["--toy", "no-such-toy"]) == 4
full = pathlib.Path(tempfile.mkdtemp())
(full / "x").write_text("x", encoding="utf-8")
with contextlib.redirect_stderr(io.StringIO()):
    assert cycle.main(["--keep", str(full)]) == 4, "空でない所に書いた"
    assert cycle.main(["--no-such-option"]) == 4
    assert cycle.main(["--keep", str(ROOT / "data" / "cycle-kept")]) == 4, "repo の中に書いた"
assert not (ROOT / "data" / "cycle-kept").exists()
assert (full / "x").read_text(encoding="utf-8") == "x" and [p.name for p in full.iterdir()] == ["x"]
print(f"ok 段 {len(order)}・まだ main に無い部品 {len(missing)}")
