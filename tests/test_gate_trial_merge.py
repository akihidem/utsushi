"""関門の帳面の節を、2 本の枝が足しても合わせる時に衝突しない事と、帳面の節を全部同じ検査で読める事を見る（#232・11-07）。

前の形: 帳面（gate-trial.md）は 1 件 1 節の追記で、どの枝も同じ末尾に足す。手元の merge は `.gitattributes` の `merge=union` で両方が残る（#232）。
ただし GitHub はこの属性を使わないので、1 本が main に入るたびに列のほかの PR が衝突した（11-07 に開いていた 21 本のうち 17 本）。
今の形（11-07 から）: 新しい節は gate-trial.d/<枝の名>.md に 1 枝 1 ファイルで書く。足す所が重ならないので、属性なしでも衝突しない。
前の節は gate-trial.md にそのまま残り、union の属性も残す（前の帳面の末尾を直す枝のため）。
使い捨ての repo で両方の形を作る。属性なしで末尾の追記が衝突する事も見るのは、git の既定が変わって属性なしでも通るようになった時に、
この試験が何も見ていない形で残らないため。
"""
import os
import pathlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = "docs/process/gate-trial.md"
SECTIONS = "docs/process/gate-trial.d"
# 検証ゲートの行を持たない前の節（11-07 の時点の 2 つ。どちらも書き戻しや取り下げの記録）。新しい節には例外を足さない
NO_GATE_LINE = {"取り込みの後の書き戻し（統括の担当、11-05 朝）",
                "合言葉なしで開いた場で、上げた画面から写真と動画を取り下げる（サイトの線、issue/public-withdraw、11-06。#474 の後）"}
# push の門の hook の中で回ると GIT_DIR などが渡るので、外の repo と手元の設定に触らないよう消す
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def git(repo, *args, check=True):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=repo, env=ENV, check=check, capture_output=True, text=True, timeout=60)


def merged(attributes, into_dir=False):
    """2 本の枝が節を足した形を合わせて、merge の結果と、合わせた後の節の字を返す。
    into_dir=False は前の形（帳面の末尾に足す）、True は今の形（gate-trial.d に枝ごとのファイルを足す）。"""
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        git(repo, "init", "-q", "-b", "main")
        ledger = repo / LEDGER
        ledger.parent.mkdir(parents=True)
        ledger.write_text("# 帳面\n\n## 前からの節\n", encoding="utf-8")
        (repo / SECTIONS).mkdir()
        (repo / SECTIONS / "README.md").write_text("# 節の置き場\n", encoding="utf-8")
        if attributes:
            (repo / ".gitattributes").write_text(attributes, encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "base")
        for branch, section in (("fix/a", "## 枝 a の節\n"), ("issue/b", "## 枝 b の節\n")):
            git(repo, "checkout", "-qb", branch, "main")
            if into_dir:
                (repo / SECTIONS / f"{branch.replace('/', '-')}.md").write_text(section, encoding="utf-8")
                git(repo, "add", "-A")
            else:
                with ledger.open("a", encoding="utf-8") as f:
                    f.write("\n" + section)
            git(repo, "commit", "-qam", branch)
        result = git(repo, "merge", "--no-edit", "fix/a", check=False)
        text = ledger.read_text(encoding="utf-8") + "".join(p.read_text(encoding="utf-8") for p in sorted((repo / SECTIONS).glob("*.md")))
        return result.returncode, text


attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8") if (ROOT / ".gitattributes").exists() else ""

# 前の形: 属性なしで衝突し、repo の属性があれば両方が残る（前の帳面の末尾を直す枝のため、属性は残す）
rc, text = merged("")
assert rc != 0 and "<<<<<<<" in text, "属性なしで衝突しないなら、この試験は何も見ていない"
rc, text = merged(attributes)
assert rc == 0, f"{LEDGER} の末尾で衝突する。.gitattributes を見る"
assert "<<<<<<<" not in text and "枝 a の節" in text and "枝 b の節" in text and "前からの節" in text, text

# 今の形: 枝ごとのファイルなら、属性が無くても（GitHub と同じ）衝突しない
for attrs in ("", attributes):
    rc, text = merged(attrs, into_dir=True)
    assert rc == 0 and "<<<<<<<" not in text and "枝 a の節" in text and "枝 b の節" in text and "前からの節" in text, (bool(attrs), rc, text)


def sections():
    """repo の帳面の節を、前の帳面と今の置き場の両方から読む。(ファイル, 見出し, 本文) の並び。"""
    out = []
    files = [ROOT / LEDGER] + sorted(p for p in (ROOT / SECTIONS).glob("*.md") if p.name != "README.md")
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "<<<<<<<" not in text and ">>>>>>>" not in text and "\n=======\n" not in text, (path, "衝突の印が残っている")
        parts = re.split(r"(?m)^## ", text)
        if path.parent.name == pathlib.Path(SECTIONS).name:
            assert re.fullmatch(r"[a-z0-9][a-z0-9._-]*\.md", path.name), (path.name, "名は「枝の名.md」（/ は - に）")
            assert parts[0].strip() == "" and len(parts) > 1, (path.name, "ファイルは節（## の見出し）で始める")
        for part in parts[1:]:
            head, _, body = part.partition("\n")
            out.append((path.name, head.strip(), body))
    return out


found = sections()
heads = [h for _, h, _ in found]
assert all(heads), "見出しの無い節がある"
dups = sorted({h for h in heads if heads.count(h) > 1})
assert not dups, ("同じ見出しの節が 2 つある（前の帳面と今の置き場の両方で見る）", dups)
lacking = [(f, h) for f, h, b in found if "検証ゲート" not in b and h not in NO_GATE_LINE]
assert not lacking, ("検証ゲートの行が無い節", lacking)
in_dir = [h for f, h, _ in found if f != pathlib.Path(LEDGER).name]
assert in_dir, "今の置き場に節が 1 つも無い（この試験の置き場の読みを見られない）"
print(f"ok 帳面の節 {len(found)} 個（前の帳面 {len(found) - len(in_dir)}・今の置き場 {len(in_dir)}）。枝ごとのファイルは属性なしでも衝突しない")
