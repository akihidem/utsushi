## 審査用の頁の型紙の版を「型紙の版 7」の形にそろえる（凍結明けの直し、fix/judge-ban-no-v、11-10）

- 目的: カード 20261107-090257 の決め A（窓口の記録 11-10「頁は「型紙の版 14」「エンジンの版 7」の形で、「v14」は使わない」）に合わせ、審査用の頁（/kaizen）に残った「型紙の版 v3 → v4」「刷った型紙の版 v7」の形を、玩具の頁の札の脇・輪の図の真ん中・手帖の山場の 1 行（#544）と同じ v の無い形にする
- どうしたか: src/web/kaizen_judge.py の次の版の行と _sheet から v を外した。訳の表（英語・やさしい日本語）の同じ 6 つの鍵と値からも v だけを外した。数と、改善の歴史の表から取る作りは替えていない。新しい字は無い
- 試験の足し: tests/test_kaizen_judge.py を v なしの形で見るように替え、頁の全体（ワークショップの節の「刷った型紙」も）に「型紙の版 v」が出ない事を足した
- 検証ゲート: **済み**。Red: main（a584b2c5）の作りに新しい試験を置いて rc 1（`docs/process/gate-evidence/red-judge-ban-no-v.txt`）。Green: aaf1909e で rc 0（`green-judge-ban-no-v.txt`）。test_kaizen_ws・test_kaizen_kata・test_kaizen_band・test_kaizen_history・test_en_all・test_easy_all・test_easy_ruby・test_en_terms・test_reader_words・test_plain_words・test_min_python・test_page_description・test_naoru・test_ban_ayumi も rc 0
- 本人の決めとの照らし: 636（版の数は 15・8 にそろえる）・カード 182815（ワークショップの字 14・7 は事実のまま）→ 数は替えていない（この頁の数は済んだ一周の版の移り変わりと、ワークショップで刷った版で、どちらも事実の数）
- 確かめていない事: 改善の歴史の表の字（山場の流れの文の「虎 v6」「型紙を v7 に直す」・エンジンの直しの行の「虎 v7 は版 7・御来迎 v14 は版 14」）は、表の字のまま写す決まり（kaizen_judge・kaizen_rekishi）なので、この枝では替えていない。この字は審査用の頁の山場の段と序の頁の改善の歴史の節の両方に出る（表の作り手のエンジンが出し直す物。別の目の読みの注）
