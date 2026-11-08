## README の仕組みの図を SVG の絵にする（型紙の担当、issue/readme-loop-svg、11-08）

- 目的: 本人の言葉 11-08「flowchart LRがそのまま字で表示されてる。図として出るように直してください。」mermaid の書き方は正しいが、GitHub の携帯のアプリなどでは描かれず字のまま出る
- いきさつ: #654 の枝に載せて push したが、その前の頭で #654 が合体していたため、今の main から切り直した枝に載せた
- どうしたか: docs/img/feedback-loop.svg を手で書いた（字は絵の中・箱は明るい地の色と濃い字・矢印は中間の灰色・字体は端末の日本語の字体を順に探す）。README は説明の字（alt）に輪の順を書いた絵 1 つにし、mermaid の塊は外した。図の下の 5 行はそのまま。architecture.md に絵の行を足した
- 確かめ: 頭のない Chrome で幅 390 の明るい頁（#ffffff）と暗い頁（#0d1117）に開き、字と矢印が読める事を見た
- 検証ゲート: **済み**。Red: 今の main（`fe38ca6c`）に新しい頭の試験だけを置くと rc 1（gate-evidence/red-readme-loop-svg.txt）。Green: この枝で rc 0（gate-evidence/green-readme-loop-3.txt。#654 の枝で書いた名のまま）
- 確かめていない事: 全部の試験（`./run.sh`）。GitHub の携帯のアプリでの目での確かめ
