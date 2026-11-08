## もちよるの「今残した」札にも畳み「のこした記録」を付ける（声の担当、voice/own-record-details、11-08 昼）

- 目的: #653 の続き。修正の担当 d の気づき（11-08）: 記録を残した画面の もちよる では、その記録は頭の「今残した」札（own）だけに出て、他の人が作った物 の並びには出ない。own の札には畳みが無かったので、残した人の画面のどこにも 4 つの欄（最初に動いた所・引っかかった所・変えると違いが出そうな所・思いついた事）が出なかった
- どうしたか: own_item の札の末に、made_item と同じ record_details の畳み（型紙の版と 4 つの欄）を足した。今残した札は記録を残した画面にだけ出る（合言葉付きの場だけ）ので、欄の字はそのまま出す。メモ（ひとこと）は own の札にも出さない（もちよる なので・統括の答え C のまま）
- 新しい字: 無い
- ゴールの要件: tests/test_mochiyoru_record_details.py の 6 の前の段（記録を残した画面の もちよる の今残した札に、畳みと 4 つの欄があり、メモは無い）
- 検証ゲート: **済み**。Red: 今の main（60ffdc86）の木で rc 1（`docs/process/gate-evidence/red-own-record-details.txt`）。Green: rc 0（`green-own-record-details.txt`）
- エビデンスゲート: 関わる試験 16 本（test_made_records・test_screen_close・test_nokosu_flow・test_build_now・test_words_review・test_public_open・test_public_inner_marks ほか）が rc 0
- マージ後の書き戻し: Issue は立てていない
