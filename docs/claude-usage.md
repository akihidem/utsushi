# Claude の使い方の記録

作業しながら更新する。まだ実施していない事は実施したように書かない。

## 開発で使った物

| 面 | 用途 |
|---|---|
| Claude Code（Opus 5.5） | 調査、案の比較、設計、コード、試験、文書の作成 |
| Claude Code の Web 検索 | 先行例の確認（`docs/process/research/05-three-axes.md`） |

## 製品の中で Claude を呼ぶ所

まだ無い。実行時のモデルは本人の判断待ち。

## 決定的な検査との境目

型紙の座標と SVG・PDF は生成器が描き、寸法と印は検査が見る。基準は `tests/frozen/criteria.md`、入口は `./run.sh`。

## 検証

- 実施済み: `./run.sh` の全場面と試験、まっさらな clone での実行、PNG の目視
- 未実施: 実物での試作、生成と別のセッションによる検証、敵対的な試験

## 凍結の変更の記録

- 基準の文は変更なし。基準に名前を決めてあった負の対照 `neg_bom_material`・`neg_bom_original` の場面を、部品表の検査を作る時に足した。
- 既定の寸法を手元の複写の基準に変えたので、場面 `pos_tube`・`pos_stick` の押す部品の長さを 84 に、`neg_figure_height` の像の高さを 55 に直した。検査の基準の文は変えていない。狙いの検査も同じ。理由は `docs/process/research/07-own-scans.md`。
- 床 F5.fan_clearance・F5.image_box・F5.image_count を足した。既定を軸の形に変えたので、F5.fan_height の軸の形の式を基準に書き足した。理由は `docs/process/research/08-fan-axle.md`。
- 本人の決定で持ち寄りの場が範囲に入ったので、床 F10 を基準に足した。
