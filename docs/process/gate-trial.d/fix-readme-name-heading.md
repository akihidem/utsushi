## README の見出しを「名前に込めた思い」にする（型紙の担当、fix/readme-name-heading、11-08）

- 目的: 本人の訂正 11-08「GitHub（README）では、「名前の心」ではなくて「名前に込めた思い」。」
- どうしたか: README の見出しだけを「## 名前に込めた思い」に（README の中に同じ見出しを指す目次や錨は無い・英語の README は無い）。序の頁の見出しは「名前の心」のまま。試験 2 本の見出しの字を合わせた
- 検証ゲート: **済み**。Red: 今の main に新しい試験だけを置くと rc 1（gate-evidence/red-readme-name-heading.txt）。Green: この枝で rc 0（gate-evidence/green-readme-name-heading.txt）
- 確かめていない事: 全部の試験（`./run.sh`）
