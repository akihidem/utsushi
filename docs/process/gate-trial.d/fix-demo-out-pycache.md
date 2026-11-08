## 動画の作りを外した見張りを、git が追うファイルで見る（サイトの担当、fix/demo-out-pycache、11-08）

- 目的: tests/test_demo_out_of_repo.py が、手元の作業の木に残った src/demo/__pycache__（git の外・.gitignore の物）で落ちないようにする
- なぜか: 統括の知らせ（11-08）。3 人の担当の ./run.sh で毎回落ちた（合体の道は新しい木なので落ちない）。試験が「在るかどうか」で見ていたため
- どうしたらいいか: 外した物が残っていないかを、`git ls-files -- <外した物>` で git が追うファイルだけで見る形にした。サイトの物が残っているかの照らしは前のまま（在るかどうか）
- 確かめた事: 追うファイルを src/demo に 1 つ足すと、前と同じく落ちる（見張りは弱めていない）
- 足した事（別の目の気づき・統括の頼み 11-08）: git の無い木（GitHub の zip・git archive）では git ls-files が落ちて rc 1 になったので、その時は前の「在るか」の見方に __pycache__ だけの所を除いて戻す。git の無い木で、__pycache__ だけなら通り、src/demo に本物のファイルを置けば落ちる事を確かめた
- ゴールの要件: 残った __pycache__ があっても通る・追うファイルが src/demo にあれば落ちる
- 検証ゲート: **済み**。Red: 今の main（`3ea71f8d`）の試験のまま、作業の木に src/demo/__pycache__/build.cpython-314.pyc を置くと rc 1（gate-evidence/red-demo-out-pycache.txt）。Green: この枝で同じ物を置いて rc 0（gate-evidence/green-demo-out-pycache.txt）。どちらも `python -m omochae.gate_evidence write` で書いた
- 検証ゲート（git の無い木）: **済み**。Red: afc94d6b を git archive した木で rc 1（git ls-files が落ちる・gate-evidence/red-demo-out-nogit.txt）。Green: 直した commit を git archive した木で rc 0（gate-evidence/green-demo-out-nogit.txt）
- エビデンスゲート: 上と ./run.sh
- マージ後の書き戻し: 無し
