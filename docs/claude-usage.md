# Claude の使い方の記録

作業しながら更新する。まだ実施していない事は実施したように書かない。

## 開発で使った物

| 面 | 用途 |
|---|---|
| Claude Code（Opus 5.5） | 調査、案の比較、設計、コード、試験、文書の作成 |
| Claude Code の Web 検索 | 先行例の確認（`docs/process/research/05-three-axes.md`） |

## 製品の中で Claude を呼ぶ所

裏の制作の仮説生成（`src/api/generate.py`）と輪の後半（記録の解釈・次の手の提案）で Messages API の tool use を呼ぶ形を作った。本物の API はまだ 1 回も呼んでいない。試験は記録した形の偽物。実行時のモデルの配分は本人の判断待ちで、今は `src/api/config.py` の Opus 5.5。

## 決定的な検査との境目

型紙の座標と SVG・PDF は生成器が描き、寸法と印は検査が見る。基準は `tests/frozen/criteria.md`、入口は `./run.sh`。

## 検証

- 実施済み: `./run.sh` の全場面と試験、まっさらな clone での実行、PNG の目視
- 持ち寄りの機能だけ、生成と別のセッション（同じアカウントの Claude）に検品させ、指摘を直した
- 未実施: 実物での試作、型紙の部分の別セッションでの検証、提出前の敵対的な試験

## 凍結の変更の記録

- 基準の文は変更なし。基準に名前を決めてあった負の対照 `neg_bom_material`・`neg_bom_original` の場面を、部品表の検査を作る時に足した。
- 既定の寸法を手元の複写の基準に変えたので、場面 `pos_tube`・`pos_stick` の押す部品の長さを 84 に、`neg_figure_height` の像の高さを 55 に直した。検査の基準の文は変えていない。狙いの検査も同じ。理由は `docs/process/research/07-own-scans.md`。
- 床 F5.fan_clearance・F5.image_box・F5.image_count を足した。既定を軸の形に変えたので、F5.fan_height の軸の形の式を基準に書き足した。理由は `docs/process/research/08-fan-axle.md`。
- 本人の決定で持ち寄りの場が範囲に入ったので、床 F10 を基準に足した。
- 本人の方針で図を貼らず描き直す事にしたので、F5.image_box・F5.image_count の基準の文と、場面 `neg_image_box`・`neg_image_count` の入力を直した。理由は `docs/process/decisions/J007-redraw-not-paste.md`。
- F10.public の見る事を足した（道具は CC BY だけ、戻された公開の記録も出さない）。F10.pii は受付の時にも見る。理由は `docs/process/decisions/J006-contributions-minimum.md`。
- 本人の指摘で仕組みを複数の仮説として並べる形に組み直したので、床 F9.prediction を足した。理由は `docs/process/decisions/J002-mechanism-hypotheses.md`。
- 本人の設計入力で自分の仮説から入る道を足したので、F9.prediction の文を直し、F9.own を足した。理由は `docs/process/decisions/J008-own-hypothesis-path.md`。
- 虎の雛形を作る時に、名前だけ決めてあった F5.pivot の中身と負の対照の名前を基準に書いた。
- 輪の後半を作る時に、F2・F3・F4・F7・F8・F9 の負の対照の欄を実際の試験の場所に直した。F9.human の文に、仮説の採否と型紙の確定の記録が未実装である事を書き足した。
