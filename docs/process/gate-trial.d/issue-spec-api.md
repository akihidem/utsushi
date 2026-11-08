## 仕様書の本物の API の字を事実に直す（型紙の担当、issue/spec-api、11-08）

- 目的: 仕様書（docs/process/spec.md）の「本物の API は 0 回」「未」「まだ確かめていない事: 本物の API」を、11-07 に手元で本物の鍵を置いて 4 つの口を呼んだ事実に直す（統括の頼み 11-08）
- 始めた所: docs/claude-usage.md の 11-07 の事実の文と、README の Claude の使い方の表（4 つは動いた・記録の動画の 3 コマと次の手の案はまだ）
- どうしたか: B5 と H2 の状態の欄（H2 は手順書の 7 回を流した記録がまだなので「一部」）と、まだ確かめていない事の頭を直した。tests/test_spec_api.py を足した
- 検証ゲート: **済み**。Red: 今の main（`26c1f0df`）に新しい試験だけを置くと rc 1（gate-evidence/red-spec-api.txt）。Green: この枝で rc 0（gate-evidence/green-spec-api.txt）
- 確かめていない事: 全部の試験（`./run.sh`）。decided-and-open の U-05（手順書の 7 回）の閉じ方は替えていない
