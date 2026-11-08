## 玩具の英語の名を、前後の道・頁の題・作例の一覧でも 1 つにそろえる（README の担当、fix/en-names-align、11-08）

- 目的: #609 で玩具の英語の名を日本語の名の訳にそろえた後も残っていた揺れを直す（統括の気づき 11-08。別の目の確かめ #609 の気づきから）
- なぜか: 前後の道（「X →」「← X」）・頁へもどる・くずし字と図鑑の頁の題で、#609 の題と違う名が残っていた（糸からくりの絵箱が String-trick picture box、石橋の獅子頭が Lion head of the Stone Bridge、木菟の凧が Eared owl kite）。作例の報告の玩具の一覧の日の付く行が、日の付かない行と別の名（monkey climbing a pole・mouse cart・rattle drum）だった。御来迎が Goraigo と Goraigō で揺れていた
- どうしたか: 訳の表の 14 鍵を toys.json の名にそろえた。作例の一覧の「竿登りの猿」は、竿（棒）を登る形なので のぼり猿（Climbing monkey）と読んだ（竹の筒を登る 竹登り猿 Bamboo-climbing monkey ではない）。御来迎は、本人が採った INTRO と同じ Goraigo にした
- ゴールの要件: tests/test_en_terms.py の 8（前後の道・頁へもどる・くずし字と図鑑の頁の題・一覧の名で toys.json の名）・9（Goraigō が無い）・10（作例の一覧の玩具の名が toys.json の名の頭）が通る
- 検証ゲート: **済み**。Red は 1 つずつ rc 1（gate-evidence/red-en-names-title.txt・red-en-names-goraigo.txt・red-en-names-list.txt）。Green rc 0（gate-evidence/green-en-names.txt）
- エビデンスゲート: test_en_all・test_en・test_kuzushi_notes・test_sakurei_gallery・test_reader_words・test_ledger・test_gate_trial_merge が rc 0
- 照らし: 本人の決めの行と 1 件ずつ照らした表は PR の本文
- マージ後の書き戻し: Issue は立てていない
