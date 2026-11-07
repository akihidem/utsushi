## engine/ を、提出の前にエンジンの main の新しい頭に写し直す（直しの担当、issue/engine-retake、11-08）

- 目的: engine/ の中を、提出の前のエンジンの main の頭に合わせる。README の commit の欄も新しい頭にする
- なぜか: 本人の決め（11-08）「提出の前に写し直す」。#565 で写した頭 6877522 の後に、エンジンの main に合体が入った（#108・#110・#109・#111・#149）
- どうしたか: #565 と同じ形（本人の決め「(A) 1本にまとめて入れる」）。engine/ の木をエンジンの main の頭 26156d35b02345b130e44708921bbd74f58cb1b9（2026-11-08 06:37 JST・#149 の合体・518 本） と同じにする 1 本の commit（git-subtree-dir・git-subtree-split の印つき）の後に、写した後の 2 つの直し（engine/SECURITY.md を外す・engine/README.md のセキュリティの節の道を一番上の SECURITY.md へ）と README の commit の欄を足した。押した commit は書き換えていない
- 写す前の秘密の点検（値は出さない）: 新しい頭の木（追跡 375 ファイル）に鍵の形 0・秘密らしい名前 0。6877522 からの新しい履歴（commit 22 本・blob 28）に鍵の形 0・commit の文に 0
- ゴールの要件: engine/ の木が、写したエンジンの頭の木と、写した後の 2 つの直しのほかは同じ。README の commit の欄が engine/ を入れた commit の印と同じ。engine/ の中で engine/run.sh が通る。この repo の ./run.sh が通る
- 検証ゲート: Red: 写した commit の木で、README の commit の欄が前の頭のままなので tests/test_readme_engine.py が rc 1（gate-evidence/red-engine-retake.txt）。Green: この枝で rc 0（green-engine-retake.txt）
- エビデンスゲート: engine/run.sh（engine/ の中・README の命令の試験を含む）rc 0（243 本＝凍結の場面 190・試験 53）。この repo の ./run.sh rc 0（271 本＝場面 34・試験 237）。押す前の門 FAIL 0
- 写した後の枝の頭から届く全履歴の点検（値は出さない）: commit 1674 本・blob 8211 に鍵の形 0・commit の文に 0・作者のメールは GitHub の 2 つだけ
- 確かめていない事: 写した後にエンジンの main がまた替わった時は、同じ手順で写し直す
- マージ後の書き戻し: Issue は立てていない
