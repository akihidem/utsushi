## やさしい日本語のルビの見張りを、混んだ機械でも 300 秒の上限に入る速さにする（サイトの担当、fix/easy-ruby-speed、11-08）

- 目的: tests/test_easy_ruby.py（#583）が run_floors の 1 本 300 秒の上限で「検査できない（時間切れ）」にならないようにする
- なぜか: #605 の ./run.sh（11-08）で rc 4。中身は通る（1 本だけ回すと rc 0）が、全部の道（約 750）で日本語とやさしい日本語の 2 枚をサーバから 1 つずつ読み、混んだ機械（load 42）で 5 分 45 秒かかった。みんなの ./run.sh でも止まりうる
- どうしたらいいか: サーバのやさしい日本語は、日本語の頁に i18n.page_easy を掛けた物（play_server._send・/en の下は掛けない）なので、日本語の頁を 1 枚だけ読み、同じ出口を試験の側で掛ける。読むのは thread で並べ（網の待ち）、変換と照らしは process で並べる（字の処理は 1 つの process の中では並ばない）。process は fork で分け、サーバと読む thread を止めた後に分ける（spawn だと子がこの試験を頭から回し直し、thread のある process の fork は危ない）。見る事は前と同じ。道を読めていない時に照らす物が無くて通らないよう、読めた頁が 100 を超える事も見る。サーバが出したやさしい日本語の頁そのものの形は test_easy_all が見る
- 失敗した版: 1 つ目は読む所だけを thread で並べた。それでも 300 秒で時間切れ（gate-evidence/try-easy-ruby-speed-threads.txt）。サーバと試験が 1 つの process で字の処理を取り合っていたため
- ゴールの要件: 混んだ機械でも 300 秒の上限の中で rc 0・見る事は前と同じ
- 検証ゲート: **済み**。Red: 今の main（`ace2a5f0`）の試験を 300 秒の上限で回すと時間切れ（rc 124・gate-evidence/red-easy-ruby-speed.txt）。Green: この枝で同じ上限で rc 0・61 秒（load 32・gate-evidence/green-easy-ruby-speed.txt）。どれも `python -m omochae.gate_evidence write` で書いた
- エビデンスゲート: 上と ./run.sh
- マージ後の書き戻し: 無し
