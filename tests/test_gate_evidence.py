"""関門の証拠のファイルの頭に、回した命令と commit の番号を書く命令（#171）と、頭がそろっている事の検査（#252）。

なぜ要るか: 証拠のファイルの多くは出力だけで、どの命令をどの commit で回したかが後から引けなかった。手で書くと、抜けるか、個人のパスが混じる。
"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import gate_evidence as ge  # noqa: E402

d = pathlib.Path(tempfile.mkdtemp())
ge.EVIDENCE = d
head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
has_git = head.returncode == 0  # git の外の写し（zip で配った物など）でも試験は回す

# 1. 落ちる命令も残す（Red は落ちるのが正しい）。頭に命令と commit、終わりに rc。命令の rc に関わらず、書けたら 0
script = 'import sys; print("見た事"); print("' + str(ROOT) + '/tests/x.py"); sys.exit(1)'
rc = ge.write("red-sample", [sys.executable, "-c", script])
text = (d / "red-sample.txt").read_text(encoding="utf-8")
lines = text.splitlines()
assert rc == 0, rc
assert lines[0].startswith("# 命令: ") and "見た事" in lines[0], lines[0]
assert lines[1].startswith("# commit: "), lines[1]
if has_git:
    assert head.stdout.strip() in lines[1], lines[1]
assert "見た事" in lines[2] and lines[-1] == "rc=1", lines

# git の外の写しでも、書いた物は検査を通る（zip で配った repo で ./run.sh を回しても、この試験が落ちない）
keep_commit = ge._commit
ge._commit = lambda: "不明（git の外）"
assert ge.write("no-git", [sys.executable, "-c", "pass"]) == 0
ge._commit = keep_commit
assert (d / "no-git.txt").read_text(encoding="utf-8").splitlines()[1].startswith("# commit: 不明")
assert ge.missing() == [], ge.missing()
(d / "no-git.txt").unlink()

# 2. 手元のパスを残さない（push の門が止める物。証拠のファイルで前に当たった）
assert str(ROOT) not in text and str(pathlib.Path.home()) not in text.replace(lines[0], ""), text
assert "tests/x.py" in text, text

# 3. 証拠は上書きしない（失敗した版も残す決まり）。名前の形も見る。どちらも書かずに 3
keep = (d / "red-sample.txt").read_text(encoding="utf-8")
assert ge.write("red-sample", [sys.executable, "-c", "print('別')"]) == 3
assert (d / "red-sample.txt").read_text(encoding="utf-8") == keep, "上書きした"
for bad in ("../outside", "a/b", "Red Sample", ""):
    assert ge.write(bad, [sys.executable, "-c", "pass"]) == 3, bad
assert not (d.parent / "outside.txt").exists()

# 4. 回せない命令と時間切れは、書かずに 4（検査できない）
assert ge.write("no-such", ["/no/such/command"]) == 4 and not (d / "no-such.txt").exists()
assert ge.write("too-slow", [sys.executable, "-c", "import time; time.sleep(30)"], timeout=1) == 4 and not (d / "too-slow.txt").exists()

# 5. check: 頭が無いファイルを名指しする。全部あれば 0
assert ge.missing() == []
(d / "old.txt").write_text("ok\nrc 0\n", encoding="utf-8")
(d / "half.txt").write_text("# 命令: x\nok\n", encoding="utf-8")
(d / "text-not-sha.txt").write_text("# 命令: x\n# commit: 無い\nok\n", encoding="utf-8")
assert ge.missing() == ["half.txt", "old.txt", "text-not-sha.txt"], ge.missing()
# 命令が残っていない古い証拠は、そう書いてあればよい（推測で埋めない）
(d / "old.txt").write_text("# 命令: 残っていない\n# commit: 1234abc（このファイルを足した commit）\nok\n", encoding="utf-8")
assert ge.missing() == ["half.txt", "text-not-sha.txt"], ge.missing()

# 6. 命令の入口: 正しい呼び方は 0、間違った呼び方は 3（exit code の決まりの中）、check は頭の無いファイルで 3
env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


def cli(*a):
    return subprocess.run([sys.executable, "-m", "omochae.gate_evidence", *a], cwd=ROOT, env=env, capture_output=True, text=True)


assert cli().returncode == 3 and cli("write").returncode == 3 and cli("write", "x").returncode == 3
assert cli("nothing").returncode == 3
# check の入口: 頭の無いファイルがあれば名指しして 3、そろえば 0（ここの置き場は 5 で残した見本）
assert ge.main(["check"]) == 3
(d / "half.txt").unlink()
(d / "text-not-sha.txt").unlink()
assert ge.main(["check"]) == 0

# 7. 本物の証拠の置き場の頭も見る（#252）。./run.sh がこの試験を回すので、頭の無い証拠を足すと main に入らない
real = cli("check")
assert real.returncode == 0, f"{real.stdout}証拠は python -m omochae.gate_evidence write <名前> -- <命令...> で書く（手で書かない）"
print("ok")
