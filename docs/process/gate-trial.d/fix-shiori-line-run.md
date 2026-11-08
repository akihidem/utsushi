## のこすの確かめの画面のしおりの 1 行を、結べる時だけ出す（UX の担当、fix/shiori-line-run、11-08）

- 目的: #702 の別の目の確かめ。のこすの頁を直に開いた時、確かめの画面に「この記録を、さっき刷ったしおりに入れます。」が見えるのに、承認しても結ばれなかった（字の約束と違う）。原因: 1 行を出すかを頁を読んだ時に決めていて、その後の開いた時の判定（web.clips の openedAs の nokosu・直に開いた時は作り始め）が回を替えていた
- どうしたか: web/nokosu.py。出すかを、確かめの画面を出す時と承認の時に、その都度見直す（今の回が刷った時の回と同じ時だけ出し、同じ時だけ結ぶ印を送る）。字は足していない
- 幅 390 の頭なしの Chromium で歩いた: 刷る → のこすの頁を直に開く → 確かめの画面の 1 行は隠れたまま・承認に shiori の印なし／刷る → 頁の道から のこす → 1 行が見える・承認に shiori=1
- 検証ゲート: Red: main 64298cd6 に試験だけを置くと rc 1（gate-evidence/red-shiori-line-run.txt）。Green: gate-evidence/green-shiori-line-run.txt。test_nokosu_flow・test_nokosu_route・test_clips_client・test_voice_walk・test_techo_site・test_ai_name・test_reader_words・test_frozen_manifest・test_gate_trial_merge・test_gate_evidence・test_ledger も rc 0
