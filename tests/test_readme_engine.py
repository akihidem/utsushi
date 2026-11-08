"""README の「開発基盤と提出物の切り分け」の、エンジンを提出のために 1 つの repo にまとめる段落（本人の言葉 11-07「提出はひとつのリポジトリにして
欲しいと運営から言われた。うつしにエンジンを追加する。まだ開発中なので最後にやる。その際、うつしに「エンジンは別で開発して、提出のために一緒にした」
という説明を追加する。」と、本人の訂正「先に用意して今のうちに載せてください」「別レポのリンクは一緒にしてもそのまま残しておいておきましょう」）。

見る事:
1. 節の中に、別の repo の paper-to-toy へのリンクがある（まとめた後も残す、本人の訂正）
2. 置き場の字（engine/・エンジンの版の台帳・版の歩みの表）があり、この repo に在るはずの表（data/history/kaizen-history.json）が在る
3. 時の書き方: engine/ がまだ無い間は「まとめる」の形で、「まとめた」と書かない。engine/ が在る（まとめた）後は、commit の欄に
   入れたエンジンの頭を書き、それが engine/ を入れた commit の印（git-subtree-split）と同じ。この repo の履歴が全部ある時は、印が在る事も求める
4. エンジンも今回のハッカソンのために作っている事と、うつしとエンジンの両方を審査の対象にしてほしい事（本人の言葉 11-07「これでいいけど、
   今回のハッカソンのためにエンジンも作ってると書いて。どっちもハッカソンの審査対象にして欲しい」）。段落の前からの字は替えない
5. 同じ節の 2 段落目（11-04 の切り出し）は「paper-to-toy は単独の提出物ではなく、1 つの提出物の中に入る」の向き（窓口の決め 11-07）。
   「単独の提出物ではない」で文を切ると、両方を審査の対象にしてほしい事と読み違えやすいため
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
readme = (ROOT / "README.md").read_text(encoding="utf-8")
# README の組み直し（11-08）で、この節は「決まりと出典」の節の中の小見出し（### ）になった。次の見出し（## か ###）までを節とする
a = readme.index("### 開発基盤と提出物の切り分け\n")
sec = readme[a:min(i for i in (readme.find("\n## ", a + 4), readme.find("\n### ", a + 4), len(readme)) if i >= 0)]

# 1. 別の repo へのリンク
assert "[paper-to-toy](https://github.com/akihidem/paper-to-toy)" in sec, "paper-to-toy の repo へのリンクを残す"

# 2. 置き場
# まだ木に無いパス（engine/・エンジンの repo の中の台帳）は逆引用符の外に書く（push の門 F が、逆引用符の中のパスが木に在るかを見るため）
assert "engine/ にまとめる" in sec and "data/engine/versions.json" in sec and "`data/history/kaizen-history.json`" in sec, sec[-400:]
assert "`engine/`" not in sec and "`data/engine/versions.json`" not in sec, "まだ木に無いパスを逆引用符で書かない"
assert (ROOT / "data/history/kaizen-history.json").exists(), "書いた表の置き場が repo に在る"

# 3. 時の書き方
if not (ROOT / "engine").exists():
    assert "にまとめる" in sec and "にまとめた" not in sec, "まだまとめていないので「まとめる」の形"
    assert "その commit は、まとめる時にここへ書く" in sec, "engine/ の commit の欄は、まとめる時に埋める"
else:
    # まとめた後は、書いた commit を、engine/ を入れた commit の印と照らす（40 字の写し違いは、目でもほかの試験でも気づきにくいため）。
    # 取り直した時は新しく入れた commit が先に出るので、いちばん新しい印と同じかを見る。git の履歴が無い写し（tar など）では字の形だけを見る
    import re
    import subprocess
    m = re.search(r"エンジンの main の頭 `([0-9a-f]{40})`", sec)
    assert m and "まとめる時にここへ書く" not in sec, "まとめたので、engine/ の commit の欄を埋める"
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, timeout=120)
    try:
        top, shallow = git("rev-parse", "--show-toplevel"), git("rev-parse", "--is-shallow-repository")
        # この repo の履歴が全部ある時だけ、印が在る事まで求める（浅い clone・ほかの repo の中の写しでは、印の commit が届かないことがある）
        full = top.returncode == 0 and pathlib.Path(top.stdout.strip()).resolve() == ROOT and shallow.stdout.strip() == "false"
        log = git("log", "--format=%(trailers:key=git-subtree-split,valueonly)", "--grep=git-subtree-dir: engine", "HEAD")
        heads = [ln.strip() for ln in log.stdout.splitlines() if ln.strip()] if log.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired):
        full, heads = False, []
    # 印が消えると照らしが空になって素通りするので、履歴が全部ある時は印が在る事を求める（別の目の指摘: PR を squash で合わせると、
    # engine/ を入れた commit の文の印が消える。合わせは merge の commit で入れる）
    assert heads or not full, "engine/ を入れた commit の印（git-subtree-dir: engine・git-subtree-split）が履歴に無い"
    assert not heads or m.group(1) == heads[0], ("README の commit が、engine/ に入れたエンジンの頭と違う", m.group(1), heads[:1])
# 4. エンジンも今回のために作った事と、両方を審査の対象に
# 本人は「これでいいけど」と前の字を採った上で足すと言ったので、前の字の最後の文の後ろに続く事まで見る（前の字を書き替えて足すと落ちる）
assert "エンジンも、今回のハッカソンのために開発期間の中で作っている" in sec, "エンジンも今回のハッカソンのために作っている事"
assert "うつしとエンジンの両方を、今回のハッカソンの審査の対象にしてほしい" in sec, "両方を審査の対象にしてほしい事"
assert "一つの具体例にあたる。エンジンも、今回のハッカソンのために" in sec, "前の字の後ろに足す"
# 5. 切り出しの段落の字の向き
assert "paper-to-toy は単独の提出物ではなく、1 つの提出物の中に入る" in sec, "1 つの提出物の中に入る向き"
assert "単独の提出物ではない。" not in sec, "単独の提出物ではない、で文を切らない"
print("ok README のエンジンを 1 つの repo にまとめる段落（リンクを残す・置き場・まとめる前の時の書き方とまとめた後の commit・エンジンも今回のために作り、両方を審査の対象に・1 つの提出物の中に入る）")
