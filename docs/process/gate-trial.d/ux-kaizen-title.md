## 審査用の頁の題を「良くするための一周 ♻︎」にする（UX の担当、ux/kaizen-title、11-08）

- 目的: 本人 11-08「よくする一周は「良くするための一周 ♻︎」として出す。」（「よくする一周」は、前の題「改善の一周」のやさしい日本語の字）
- どうしたか: web/kaizen_judge.py の TITLE（題・頁の名）を替えた。♻ の後ろに字の形の異体字の印（U+FE0E）を付け、機械ごとに絵文字の色の絵になったり字になったりする揺れを無くす（統括の決め）。英語（A round to make it better ♻︎）とやさしい日本語（｜良《よ》くするための｜一周《いっしゅう》 ♻︎）の表も替え、前の題の鍵は外した
- 検証ゲート: **済み**。Red: main の頭 4af9fe0d に試験 tests/test_kaizen_judge.py だけを置くと rc 1（gate-evidence/red-kaizen-title.txt）。Green: gate-evidence/green-kaizen-title.txt

| 決めの行 | 照らし | 根拠 |
|---|---|---|
| 本人 11-08「良くするための一周 ♻︎」 | 直った | kaizen_judge.TITLE・訳の表 |
