"""エンジンを探す所が、この repo の中の engine/ を、隣の repo より先に見る事を確かめる（11-07 夜、engine/ を入れた PR の別の目の下見の気づき）。

なぜ要るか: 提出の repo は engine/ にエンジンの頭を入れた。審査の人は utsushi だけを clone するので、隣の paper-to-toy は無い。
エンジンを探す所（版の歩みの台帳を読む kaizen_versions.engine_ledger と、一周の入口の cycle.find_engine_repo）が
環境の値の次に隣の repo だけを見ると、engine/ が在るのに「エンジンが無い・読めない」になる。

見る事:
1. find_engine_repo: 環境の値が無い時は、engine/ を隣の repo より先に返す。engine/ が無ければ隣の repo。渡された所・環境の値が先なのは前のまま
2. engine_ledger: 環境の値が無い時は、engine/ の台帳を、隣の repo の main の台帳より先に読む。engine/ が無ければ隣の repo。環境の値が先なのは前のまま
3. 今の repo: engine/ の台帳が在る時、環境の値が無ければ、その台帳を読む
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from omochae import cycle  # noqa: E402
from web import kaizen_versions as kv  # noqa: E402

base = pathlib.Path(tempfile.mkdtemp())
here = base / "utsushi"
sibling = base / "paper-to-toy"
for repo in (here / "engine", sibling):
    (repo / "src/omochae").mkdir(parents=True)
    (repo / "src/omochae/engine_loop.py").write_text("", encoding="utf-8")
    (repo / "data/engine").mkdir(parents=True)
(here / "engine/data/engine/versions.json").write_text(json.dumps({"versions": [{"version": 5}]}), encoding="utf-8")
# 隣の repo は、main の中身を git から読む（前からの読み方）。main の台帳を 7 にする
git = lambda *a: subprocess.run(["git", "-C", str(sibling), "-c", "user.name=t", "-c", "user.email=t@example.com", *a], check=True, capture_output=True)
(sibling / "data/engine/versions.json").write_text(json.dumps({"versions": [{"version": 7}]}), encoding="utf-8")
git("init", "-q")
git("add", "-A")
git("commit", "-qm", "ledger")
git("update-ref", "refs/remotes/origin/main", "HEAD")
other = base / "other"
(other / "src/omochae").mkdir(parents=True)
(other / "src/omochae/engine_loop.py").write_text("", encoding="utf-8")
(other / "data/engine").mkdir(parents=True)
(other / "data/engine/versions.json").write_text(json.dumps({"versions": [{"version": 9}]}), encoding="utf-8")

no_env = {k: v for k, v in os.environ.items() if k != "OMOCHAE_ENGINE_REPO"}
rel = lambda p: p.relative_to(base).as_posix() if p else None  # 落ちた時の字に、一時の置き場の絶対のパスを出さない
real_cycle, real_kv = cycle.ROOT, kv.ROOT
cycle.ROOT, kv.ROOT = here, here
try:
    with mock.patch.dict(os.environ, no_env, clear=True):
        # 1. 一周の入口
        assert cycle.find_engine_repo() == here / "engine", ("engine/ を隣の repo より先に見る", rel(cycle.find_engine_repo()))
        # 2. 版の歩みの台帳
        assert kv.engine_ledger() == {"versions": [{"version": 5}]}, ("engine/ の台帳を、隣の main の台帳より先に読む", kv.engine_ledger())
    with mock.patch.dict(os.environ, {"OMOCHAE_ENGINE_REPO": str(other)}):
        assert cycle.find_engine_repo() == other and kv.engine_ledger()["versions"][0]["version"] == 9, "環境の値が engine/ より先（前のまま）"
    assert cycle.find_engine_repo(str(other)) == other, "渡された所が先（前のまま）"
    # engine/ が無い repo（提出の前の木・engine/ を入れていない写し）は、前と同じに隣の repo を見る
    for p in sorted((here / "engine").rglob("*"), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
    (here / "engine").rmdir()
    with mock.patch.dict(os.environ, no_env, clear=True):
        assert cycle.find_engine_repo() == sibling, ("engine/ が無ければ隣の repo", rel(cycle.find_engine_repo()))
        assert kv.engine_ledger() == {"versions": [{"version": 7}]}, ("engine/ が無ければ隣の main の台帳", kv.engine_ledger())
finally:
    cycle.ROOT, kv.ROOT = real_cycle, real_kv

# 3. 今の repo: engine/ の台帳が在れば、環境の値が無い時はそれを読む
inside = ROOT / "engine/data/engine/versions.json"
if inside.exists():
    with mock.patch.dict(os.environ, no_env, clear=True):
        assert kv.engine_ledger() == json.loads(inside.read_text(encoding="utf-8")), "今の repo の engine/ の台帳を読む"
        assert cycle.find_engine_repo() == ROOT / "engine", "今の repo の engine/ を返す"
print("ok エンジンを探す所が engine/ を隣の repo より先に見る（一周の入口・版の歩みの台帳・環境の値と渡された所が先・engine/ が無ければ隣・今の repo の台帳）")
