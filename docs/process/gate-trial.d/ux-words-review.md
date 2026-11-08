## 公開の場の札に、人が確かめた後だけ感想と工夫の行を出す（UX の担当、ux/words-review、11-08）

- 目的: 本人 11-08「…できたおもちゃはギャラリーの形で並べる。感想も見れるように」と、窓口の決め A（公開のデモでも、人が確かめた後に感想と工夫の行を出す。確かめていない物は出さない線は残す）
- どうしたか: omochae/words_review.py（media_review と同じ形。結果は記録の写真の置き場の words.json に、字の指紋・確かめた人・時刻だけ。字が替わると確かめていない扱いに戻る・出す時に連絡先の形の床を当て直す・命令は端末で人が番号を打った時だけ）。web/techo_site.py の made_item の公開の場の線を「確かめた字なら出す」に。進め役の手順を docs/process/workshop-guide.md に
- 検証ゲート: **済み**。Red: main の頭 ace2a5f0 に新しい試験 tests/test_words_review.py だけを置くと rc 1（gate-evidence/red-words-review.txt）。Green: gate-evidence/green-words-review.txt

| 決めの行 | 照らし | 根拠 |
|---|---|---|
| 404 できたおもちゃはギャラリーの形で・感想も見れるように | 直った（公開の場は人が確かめた後） | made_item の公開の場の線 |
| 窓口の決め A（確かめていない物は出さない線は残す・両方の向きの試験） | 守った | tests/test_words_review.py |
| J-028 文の中の名前は機械で落とせない | 守った | 人の目を間に入れ、確かめるまで出さない |
