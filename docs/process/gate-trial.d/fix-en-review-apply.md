## 英語の言葉の決めを訳の表に当てる（README の担当、fix/en-review-apply、11-08）

- 目的: 本人の決め（11-08）「英語の『作る』は make でよい・用語の対応も推しのとおり」を、今の main の訳の表と玩具の英語の名に当てる。決め待ちの残り（玩具の名・引用符）は推しで進める（統括の頼み）
- なぜか: 同じ日本語が頁ごとに別の英語で出ていた（仮説が Idea・trial plan・trial idea、工夫が tweak、虎の首が swing と sway、玩具の名が 83 種中 81 種で 2 つ）。決めの元は grove の state/english-review-20261107.md の 1・2・9
- どうしたか: 見直しの直す案のうち、今の main で鍵があり字が見直した時のままの物だけを当てた（1350 件のうち 1347。鍵が消えた 3 件は外した）。見直しの後に入った 165 件も同じ決めで見て 7 件の案を出し、6 件を当てた（11 月のワークショップの札の 1 件は、本人が決めた札と組なので戻して本人に聞く）。作り直した時の main（6f5e05ce・#597 の後）で増えた 134 件のうち、決めから外れた 2 件を直した（ほかの見直しは後の commit）。開いていた PR の見直しの案のうち main に入った 3 件も当てた。玩具の名は、題の鍵（図・作りながら見る・型紙・手帖・組み方など）と data/en/toys.json の 78 種を日本語の名の訳にそろえた（〔観察〕などの絵を言い表した文は替えない）。語の中の ' を ’ に、対の " を “ ” にした（HTML の断片は替えない）
- 比べた案: 玩具の名を絵を言い表した名にそろえる案（推しの B）は採らない（本人が推し A を採った）。見直しの案を全部当て直す案は、字の替わった鍵で前の字に戻す事があるので採らない（今回は 0 件）
- ゴールの要件: tests/test_en_terms.py（make と craft・用語の対応・玩具の名が 1 つ・語の中の引用符）が通る。全頁の英語の試験が通る。./run.sh が全部期待どおり
- 検証ゲート: **済み**。Red: 今の main の表で tests/test_en_terms.py が rc 1（gate-evidence/red-en-terms.txt）。1 回目の Green は rc 1 だった（gate-evidence/green-en-terms.txt。作り直した時の main に入った新しい字 2 つが仮説を idea・工夫を tweak と書いていた。試験が狙いどおりに止めた）。その 2 つを直し、独立した引用（原文＋英訳）の値を、本人の言葉と同じく決めの外に置いて、Green: rc 0（gate-evidence/green-en-terms-2.txt）
- エビデンスゲート: test_en・test_en_all・test_sakurei_gallery・test_reader_words・test_easy_all・test_ledger が rc 0。./run.sh は前の基点（80b1395f）で 272 本のうち 271 本が期待どおりで、test_easy_ruby だけが機械の負荷で時間切れ（300 秒・負荷の平均 22）。単独で回すと rc 0（268 秒）。test_sakurei_gallery は、今の main の表と試験のままでも落ちる（日ごとの見出し・この PR の外）
- 照らし: 本人の決めの行と 1 件ずつ照らした表は PR の本文
- マージ後の書き戻し: Issue は立てていない（新しい Issue は提出を止める物だけ）
- 窓口の決め（11-08）を当てた: 本人の言葉の英訳の版の番号の取り違えを直す（「撮影は v{3} のまま」が v{0} と訳されていた）・本人の言葉と決めの記録の英訳でも仮説は guess（Idea A・C → Guess A・C、both ideas → both guesses。字の意味は替えない）・11 月のワークショップは複数 workshops（11-04〜07 の 4 日）。決めの記録の英訳の steps sheet も instruction sheet にした（用語の対応・本人の決め 380）。tests/test_en_terms.py に 3 つの確かめを足した（本人の言葉の英訳の用語・鍵と英語の版の番号の組・workshops）。Red は 1 つずつ: 前の頭の表で rc 1（gate-evidence/red-en-terms-owner.txt）、版の番号だけ前に戻すと rc 1（red-en-terms-version.txt）、workshops だけ前に戻すと rc 1（red-en-terms-workshops.txt）。Green rc 0（green-en-terms-3.txt）
