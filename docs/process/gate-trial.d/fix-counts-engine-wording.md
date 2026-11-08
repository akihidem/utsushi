## 数の欄のエンジンの版の注の言い過ぎを直す（型紙の担当、fix/counts-engine-wording、11-08）

- 目的: 台帳が描く数の欄の「エンジンの版: 7（型紙を作る仕組みの版。全部の玩具の型紙に効く）」は、#671 で直したのと同じ言い過ぎ（3D の確かめは御来迎と虎だけ・エンジンの版 3〜7 は 1 つの玩具の組だけ）
- どうしたか: 描く元の src/omochae/ledger.py の字を「そのエンジンが作る型紙のどれにも使われる」にして render。tests/test_kaizen_history.py に見張りを足した
- 検証ゲート: **済み**。Red: 今の main に新しい試験だけを置くと rc 1（gate-evidence/red-counts-engine-wording.txt）。Green: この枝で rc 0（gate-evidence/green-counts-engine-wording.txt）
- 確かめていない事: 全部の試験（`./run.sh`）
