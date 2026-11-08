## しおりの裏の「いちばん新しく刷ったしおりだけが使えます。」を刷らない（UX の担当、fix/shiori-newest-line、11-08）

- 目的: #702 の 17:00 の最低限の形では、同じ人の刷り直しで前のしおりを使えなくする所を入れていない（待ちが切れるだけで、前に刷ったしおりも開く）。裏の 3 行目「いちばん新しく刷ったしおりだけが使えます。」は事実と合わない（統括の決め 11-08）
- どうしたか: omochae/shiori_card.py の裏の字（BACK_LINES）から 3 行目を外した。字は足していない。刷り直しで前を使えなくする所を入れる時に戻すかを決める
- 検証ゲート: Red: main a6d622ed に試験だけを置くと rc 1（gate-evidence/red-shiori-newest-line.txt）。Green: gate-evidence/green-shiori-newest-line.txt。test_shiori_sheet・test_shiori・test_shiori_open・test_ai_name・test_reader_words・test_frozen_manifest・test_gate_trial_merge・test_gate_evidence・test_ledger も rc 0
