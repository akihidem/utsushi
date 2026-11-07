"""README の「開発基盤と提出物の切り分け」の、エンジンを提出のために 1 つの repo にまとめる段落（本人の言葉 11-07「提出はひとつのリポジトリにして
欲しいと運営から言われた。うつしにエンジンを追加する。まだ開発中なので最後にやる。その際、うつしに「エンジンは別で開発して、提出のために一緒にした」
という説明を追加する。」と、本人の訂正「先に用意して今のうちに載せてください」「別レポのリンクは一緒にしてもそのまま残しておいておきましょう」）。

見る事:
1. 節の中に、別の repo の paper-to-toy へのリンクがある（まとめた後も残す、本人の訂正）
2. 置き場の字（engine/・エンジンの版の台帳・版の歩みの表）があり、この repo に在るはずの表（data/history/kaizen-history.json）が在る
3. 時の書き方: engine/ がまだ無い間は「まとめる」の形で、「まとめた」と書かない（まとめる PR が、この試験ごと「まとめた」の形に替える）
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
readme = (ROOT / "README.md").read_text(encoding="utf-8")
a = readme.index("## 開発基盤と提出物の切り分け")
sec = readme[a:readme.index("\n## ", a + 3)]

# 1. 別の repo へのリンク
assert "[paper-to-toy](https://github.com/akihidem/paper-to-toy)" in sec, "paper-to-toy の repo へのリンクを残す"

# 2. 置き場
assert "`engine/`" in sec and "data/engine/versions.json" in sec and "data/history/kaizen-history.json" in sec, sec[-400:]
assert (ROOT / "data/history/kaizen-history.json").exists(), "書いた表の置き場が repo に在る"

# 3. 時の書き方
if not (ROOT / "engine").exists():
    assert "にまとめる" in sec and "にまとめた" not in sec, "まだまとめていないので「まとめる」の形"
    assert "その commit は、まとめる時にここへ書く" in sec, "engine/ の commit の欄は、まとめる時に埋める"
print("ok README のエンジンを 1 つの repo にまとめる段落（リンクを残す・置き場・まとめる前の時の書き方）")
