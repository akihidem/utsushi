## もちよるの記録の札に、玩具の頁の記録の札にだけあった 6 つを畳み「のこした記録」で足す（声の担当、voice/mochiyoru-record-details、11-08 昼）

- 目的: 本人の言葉（11-08）477「復元の記録などはすべてもちよるに統合する。」・統括の決め（11-08）: 玩具の頁から記録の札を外すと（つくるの作り直しの枝 1）、型紙の版・最初に動いた所・引っかかった所・変えると違いが出そうな所・思いついた事・メモ の 6 つがサイトのどこにも出なくなる。#646 の上の小さな枝で、枝 1 より先に入れる
- どうしたか: (1) もちよるの「他の人が作った物」の記録の札（made_item）の末に、ふだん閉じた畳み（見出しは前からある字「のこした記録」）。中は型紙の版の札と 5 つの欄で、字と並びは玩具の頁の記録の札と同じ (2) 欄だけの記録（写真も感想も工夫も無い）も札を出す (3) 公開の場は感想と同じく人が確かめた字だけ: words_review の確かめる字（words_of）に、欄がある時だけ details を足した（確かめる人に欄の字が見え、指紋と連絡先の形の床も欄にかかる）。欄の無い記録の字の形と指紋は前と同じなので、前の確かめは外れない
- 新しい字: 無い（「のこした記録」・欄の名・版の札は前からある字）
- ゴールの要件: tests/test_mochiyoru_record_details.py の 5 つ（頭の注のとおり）
- 検証ゲート: **済み**。Red: #646 の頭 8541ba82 の木で rc 1（欄の字が札に出ない。`docs/process/gate-evidence/red-mochiyoru-record-details.txt`）。Green: rc 0（`green-mochiyoru-record-details.txt`）
- エビデンスゲート: 写しの木で、確かめる字から欄を外すと rc 1（欄だけの記録が確かめを待たない）。関わる試験 25 本（test_words_review・test_made_records・test_public_open・test_mochiyoru_toy_place・test_screen_close・test_nokosu_flow・test_en_all・test_easy_all ほか）が rc 0
- 確かめていない事: 公開デモの記録の置き場の本物の記録（欄のある記録が公開の場で確かめを待つ物に入る数）。人が使った確かめ
- マージ後の書き戻し: Issue は立てていない
- 追い（11-08 昼・統括の答え C）: ./run.sh（09db5382）は 302 本中 301 本。落ちた test_build_now は前の決まり（11-05 の別の目の検品の直し「ひとこと（note）はギャラリーに出さない」）を見ていて、6 つ目のメモ（ひとこと）を もちよる に出した所とぶつかった。統括に聞き、答え C「メモは もちよる に出さない（みんなが見る所なので前の決まりを守る）。代わりに手帖の自分の記録の頁の札に出す」で直した: もちよるの畳み「のこした記録」は型紙の版と 4 つの欄。確かめる字（words_review の details）からもメモを外した。手帖の記録の頁（records_page）で、その画面が残した自分の記録（records.mine）の札にだけ「メモ: …」を出す（開いた場は出さない）。Red: 09db5382 の木に今の試験を当てて rc 1（`docs/process/gate-evidence/red-mochiyoru-record-details-memo.txt`）。Green: rc 0（`green-mochiyoru-record-details-memo.txt`）。test_build_now を含む関わる試験 24 本が rc 0
