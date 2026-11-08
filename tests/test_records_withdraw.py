"""手帖から上げた記録の取り下げ（#157）。顔や名札が写った写真を誤って上げた時の戻り道。"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import urllib.request

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from omochae import gallery, loop, records  # noqa: E402
from web.play_server import serve  # noqa: E402
from web.techo_site import media_dir  # noqa: E402

G = "NDL-1187053-R0000005-L"
LOOP = pathlib.Path(tmp) / "loop"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()


def page(path):
    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}") as r:
        return r.read().decode()


def withdraw(*args):
    return subprocess.run([sys.executable, "-m", "omochae.records", "withdraw", *args], capture_output=True, text=True)


def trial():
    """記録 1 件に、写真と動画・説明・解釈・観察を添える。"""
    rid, failures = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "わからない"})
    assert not failures, failures
    media_dir(rid).mkdir(parents=True)
    for name in ("m1.jpg", "m2.mp4"):
        (media_dir(rid) / name).write_bytes(b"x")
    assert loop.save_explanation(rid, "作った人", "筒を押すと開いた", "筒を長くする") == []
    loop.save_interpretation_draft(rid, {"what_happened": "開いた", "why": "わからない"})
    (LOOP / f"observation-{rid}.json").write_text(json.dumps({"record_id": rid, "observed": ["扇が開く"], "unclear": [], "by": "claude", "label": "観察"}), encoding="utf-8")
    return rid


def own_files(rid):
    return [LOOP / f"{kind}-{rid}.json" for kind in ("explanation", "interpretation", "observation")]



# 取り下げると、記録と添えた物が全部消え、どの頁と集計にも出ない
rid = trial()
def pages():
    return {"手帖": page(f"/toy/{G}/techo/kiroku"), "玩具": page(f"/toy/{G}"), "ギャラリー": gallery.build()}


# 本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などはすべてもちよるに統合する。」で、つくるの頁から記録の札を外した。
# 記録は手帖の記録の頁とギャラリー（もちよる）に出る。つくるの頁には取り下げる前から出ない（取り下げた後に出ない事は、下で 3 つの頁とも見る）
for name, body in pages().items():
    if name == "玩具":
        assert rid not in body, "つくるの頁に記録の札が出た（上の理由で外した）"
        continue
    assert rid in body, f"取り下げる前は {name} に出る"
assert rid in records.summarize(records.all_records(G))["H-A"]["record_ids"]
r = withdraw(rid)
assert r.returncode == 0, r.stderr
assert rid in r.stdout and "取り下げ" in r.stdout
assert not (records.folder() / f"{rid}.json").exists()
assert not media_dir(rid).exists(), "写真と動画が残った"
assert not any(p.exists() for p in own_files(rid)), "説明・解釈・観察が残った"
for name, body in pages().items():
    assert rid not in body and f"/record/{rid}/media/" not in body, name
assert records.summarize(records.all_records(G)) == {}
assert rid not in loop.known_ids()

# 番号だけを残す。中身は残さず、次の記録に同じ番号を使い回さない
left = json.loads((records.folder() / "withdrawn" / f"{rid}.json").read_text(encoding="utf-8"))
assert set(left) == {"id", "status", "withdrawn_at"} and left["id"] == rid
other = trial()
assert other != rid, "取り下げた番号を使い回した"

# 同じ番号をもう一度取り下げても通る。途中で落ちた時に回し直せるようにするため
assert withdraw(rid).returncode == 0
# 記録が別の経路で戻っても、一覧には再び出さない
(records.folder() / f"{rid}.json").write_text(json.dumps({"id": rid, "source_id": G, "hypothesis_id": "H-A", "result": "わからない"}), encoding="utf-8")
assert rid not in [x["id"] for x in records.all_records()] and rid not in loop.known_ids()
(records.folder() / f"{rid}.json").unlink()

# 打ち間違いの番号で「取り下げた」と答えない。形の違う番号で置き場の外を消さない
assert withdraw("R-9999").returncode == 3
outside = pathlib.Path(tmp) / "keep.json"
outside.write_text("{}", encoding="utf-8")
assert withdraw("../keep").returncode == 3 and outside.exists()

# 根拠に使われている記録は、その事を言って止まり、何も消さない
(LOOP / "proposal-0001.json").write_text(json.dumps({"id": "P-0001", "record_ids": [other]}), encoding="utf-8")
r = withdraw(other)
assert r.returncode == 3 and "proposal-0001.json" in r.stderr and "--media-only" in r.stderr, r.stderr
assert (records.folder() / f"{other}.json").exists() and (media_dir(other) / "m1.jpg").exists() and all(p.exists() for p in own_files(other))
# 番号の一部が同じだけの物は、根拠と読まない
(LOOP / "proposal-0001.json").write_text(json.dumps({"id": "P-0001", "record_ids": [other + "0", "X" + other]}), encoding="utf-8")
assert records.used_by(other) == []
(LOOP / "proposal-0001.json").write_text(json.dumps({"id": "P-0001", "record_ids": [other]}), encoding="utf-8")

# 根拠に使われていても、写真と動画と、そこから作った観察は消せる。記録と説明と解釈は根拠なので残す
r = withdraw(other, "--media-only")
assert r.returncode == 0, r.stderr
assert not media_dir(other).exists() and not (LOOP / f"observation-{other}.json").exists()
assert (records.folder() / f"{other}.json").exists() and (LOOP / f"explanation-{other}.json").exists() and (LOOP / f"interpretation-{other}.json").exists()
assert not (records.folder() / "withdrawn" / f"{other}.json").exists(), "記録を残すのに取り下げの印を置いた"
assert other in [x["id"] for x in records.all_records()]

server.shutdown()
print("ok")
