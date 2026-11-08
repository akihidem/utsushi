## 輪の図の下の正直な 1 行を、事実に合う字（本人が選んだ A）にする（直しの担当、fix/honest-line、11-08 昼）

- 目的: 本人の言葉（11-08・決めの記録 521）「文書がおかしい。次の型紙をよくするのは今、記録を Claude に渡して回しています。その事実に合う文に直してください。」。前の字「次の型紙をよくするのは今、記録を Claude に渡して回しています。」は、誰の記録を渡して何をしているのかと、版を人が決める事が読めなかった
- どうしたか: のこすの頁と説明の頁の輪の図の下の 1 行（`src/web/loop_figure.py` の HONEST）を、2 案（A・B）から本人の答え「(A) でよい。」（決めの記録 525）の A にした: 「今は、作った人の記録を Claude に渡して、次の型紙の案を作っています。どの版にするかは人が決めます。」。英語の表とやさしい日本語の表（`data/i18n/yasashii.d/5-one-loop.json`）の前の字の行を、A の行に置き換えた（英語は英語の見直しの言葉の決めに合わせた）
- デモの台本: デモの語りの下書き（grove の state/demo-narration-oneloop-20261108-g.md・g-a.md）が、冒頭の正直さの字を前の字にそろえていたので、デモの担当へ知らせた（repo の外）
- ゴールの要件: 図の下の 1 行が A。前の字が頁に出ない。英語とやさしい日本語の表に A がある
- 検証ゲート: Red: 今の main 4af9fe0d の木に直した `tests/test_loop_figure.py` を当てて rc 1（`docs/process/gate-evidence/red-honest-line.txt`。前の字のまま）。Green: rc 0（`green-honest-line.txt`、72157690）
- 確かめていない事: 本人が頁で見る事
- マージ後の書き戻し: Issue は立てていない
- 追い（11-08 昼・同じ PR）: 本人の言葉「のこすのうつしの輪は、記入欄の下にする。」（決めの記録 530）。のこすの頁（`src/web/techo_site.py` の records_page）で、うつしの輪の節（manabi_box・字 1・絵 A・正直な 1 行）を記入の節（id=kinyu・のこすの釦）のすぐ下へ移し、直った例の集（naoru.box）をその下にした。並びの試験（`tests/test_nokosu_flow.py`・`tests/test_nokosu_wa.py`）を新しい順にした（見る所の数は替えず、記入の節と輪の節の間にほかの節が入らない事を足した）。Red: 今の main 743706e5 の木に直した `tests/test_nokosu_flow.py` を当てて rc 1（`docs/process/gate-evidence/red-nokosu-wa-move.txt`）。画面: 日本語・英語・やさしい日本語の 3 つ × 幅 320・390・1440 の 9 通りで、記入の節 → 輪 → 直った例の集の順に箱が重ならず（間は 22px）、横のはみ出し 0。幅 390 の絵は grove の state/nokosu-wa-move/
