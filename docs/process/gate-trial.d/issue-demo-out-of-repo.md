## デモ動画の作りを repo の外へ移す（サイトの担当、issue/demo-out-of-repo、11-08）

- 目的: 提出のデモ動画の作り（台本・場面を描くコード・その試験と証拠・台本の案の記録）を utsushi の repo から外す
- なぜか: 本人の言葉（11-08・統括を通して）「この動画の作成はギットハブに入ってる？入れなくていいと思うと前に指摘したけど」。統括の決め: 置き場は作り手の手元（git の外へ push しない）、Drive にも控え、utsushi は main から 1 本の PR で外す
- どうしたらいいか: (1) サイトの北斎漫画が読んでいた絵の出所と権利の記録（figures.json・scene4_sources.json）を、字を替えずに data/hokusai/ へ移し、src/omochae/hokusai.py の読む所と注、src/web/hokusai.py の注を直した。前の docs/demo/plan.md の「1. 北斎漫画の絵の出所」は data/hokusai/README.md へ字を替えずに写した（中の figures.json への道だけ新しい置き場に）。(2) src/demo/・docs/demo/・tests/test_demo_{assemble,build,flip,prepare,scene2〜7}・動画の書き出しの証拠 6 つ・docs/process/demo-notes.md を外した。(3) tests/test_result_table.py が demo.build の数の読みも見ていたので、その照らしだけを外した。(4) 凍結の照合の表から消した 10 本の名だけを外し、理由を docs/claude-usage.md に書いた（場面と基準は替えない・表に載っていない今の試験は足していない）。(5) README の使い方の節・architecture の行・features の f29（dropped・注）・process の README の 1 行・索引の demo-notes を直し、古い記録の demo-notes.md へのリンク 5 つを字にした（中身は替えない）
- 残した物: 公開デモのサイトの物（run-demo.sh・web.demo_check・web.demo_samples・J028・test_run_demo・test_demo_samples・test_demo_walk・test_demo_walk_all と、その証拠）と、過程の記録（古い帳面・issues・progress の言及は移す前の物として残す）
- 確かめていない事: 前の commit の履歴には残る（force push はしない決まりなので書き換えない）。GitHub の lane/demo-try と古い try/demo-* の枝を消すかは、本人の「履歴からも消したい」への答えの後に統括が決める
- ゴールの要件: tests/test_demo_out_of_repo.py（動画の作りが無い・コードと試験と README と architecture に動画の作りを読む所が無い・北斎漫画の記録は data/hokusai でサイトはそこを読む・公開デモのサイトの物は残る）
- 検証ゲート: **済み**。Red: 今の main（`2b973590`）で、動画の作りが残っていて rc 1（gate-evidence/red-demo-out-of-repo.txt）。Green: この枝で rc 0（gate-evidence/green-demo-out-of-repo.txt）。どちらも `python -m omochae.gate_evidence write` で書いた。test_site_hokusai・test_ledger・test_gate_evidence・test_result_table・test_run_demo・test_demo_samples・test_demo_walk・test_demo_walk_all ほか 19 本 rc 0、凍結の照合 ok
- エビデンスゲート: 上と ./run.sh
- マージ後の書き戻し: 枝を消す時に、手元の写しの頭と GitHub の枝の SHA を照らした記録を統括の控えに
