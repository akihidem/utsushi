"""関門の帳面の末尾に 2 本の枝が節を足しても、合わせる時に衝突しない事を見る（#232）。

帳面は 1 件 1 節の追記で、どの枝も同じ末尾に足す。使い捨ての repo で同じ形を作り、repo の `.gitattributes` を置いた時だけ通る事を見る。
属性なしで衝突する事も見るのは、git の既定が変わって属性なしでも通るようになった時に、この試験が何も見ていない形で残らないため。
"""
import os
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = "docs/process/gate-trial.md"
# push の門の hook の中で回ると GIT_DIR などが渡るので、外の repo と手元の設定に触らないよう消す
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def git(repo, *args, check=True):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=repo, env=ENV, check=check, capture_output=True, text=True, timeout=60)


def merged(attributes):
    """2 本の枝が末尾に節を足した形を合わせて、merge の結果と帳面の中身を返す。"""
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        git(repo, "init", "-q", "-b", "main")
        ledger = repo / LEDGER
        ledger.parent.mkdir(parents=True)
        ledger.write_text("# 帳面\n\n## 前からの節\n", encoding="utf-8")
        if attributes:
            (repo / ".gitattributes").write_text(attributes, encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "base")
        for branch, section in (("a", "## 枝 a の節\n"), ("b", "## 枝 b の節\n")):
            git(repo, "checkout", "-qb", branch, "main")
            with ledger.open("a", encoding="utf-8") as f:
                f.write("\n" + section)
            git(repo, "commit", "-qam", branch)
        result = git(repo, "merge", "--no-edit", "a", check=False)
        return result.returncode, ledger.read_text(encoding="utf-8")


rc, text = merged("")
assert rc != 0 and "<<<<<<<" in text, "属性なしで衝突しないなら、この試験は何も見ていない"

attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8") if (ROOT / ".gitattributes").exists() else ""
rc, text = merged(attributes)
assert rc == 0, f"{LEDGER} の末尾で衝突する。.gitattributes を見る"
assert "<<<<<<<" not in text and "枝 a の節" in text and "枝 b の節" in text and "前からの節" in text, text
print("ok")
