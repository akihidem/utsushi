## くずし字の図 49 の「正しいか」の直し（型紙の担当、fix/kuzushi-score-word、11-08）

- 目的: main で tests/test_kuzushi.py が落ちる。#694 で入れた図 49 の言葉の意味の「その読み直しが正しいかは」の「正しい」が、くずし字の頁の採点の言葉の見張り（J-025）に当たった
- 原因の元: くずし字の組を入れた時、関わる試験に test_kuzushi.py（頁の採点の言葉）を入れていなかった（test_kuzushi_notes だけを回していた）
- どうしたか: 「当たっているかは」に替えた（R0000028-L-2・-L-3。やさしい日本語も・英語の鍵も）
- 検証ゲート: **済み**。Red: 今の main で test_kuzushi が rc 1（gate-evidence/red-kuzushi-score-word.txt）。Green: この枝で rc 0（gate-evidence/green-kuzushi-score-word.txt）
- 確かめていない事: 全部の試験（`./run.sh`）
