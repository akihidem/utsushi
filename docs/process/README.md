# 開発の過程の読み方

この作品は、できた物だけでなく、どう調べ、何を比べ、何を捨てて決めたかが repo から読めるように作っている。記録は作業しながら残し、後からまとめて書かない。時刻の証拠は commit の履歴。

| 置き場 | 中身 |
|---|---|
| `research/` | 調べた事のメモ。一次資料か実験の結果と、そこから言える事・言えない事 |
| `decisions/` | 判断の記録 J-nnn。比べた案・捨てた案・決めた理由 |
| `trials/` | 仮説 → 型紙 → 実物の試行 → 記録 → 次の版 の流れの索引。実際に試した物だけを載せる |
| `../progress.md` | 作業の 1 行記録 |

調査メモと判断の案は Claude Code のセッションが書いた。人が決めた事と、人の手で試した事は、その旨を明記する。

## 設計の核（本人の言葉）

> 目の前のトイモデルは自分の予想が具現化される場で工作することで予測が正しかったかすぐにフィードバックされる。作っているうちに新しいアイディアが湧く。この体験をさせたい。学習の効果よりも学習の再定義、そのあたりに転がっている真理を見つける練習。知識伝達型の教育へAIと子供がタッグを組んで挑む。

> AI は鏡。江戸の絵を映すことはできるが、映すだけでは遊べない。

読み取りと、[批判的レビュー](research/13-critical-review.md)の読み直しは [J-013](decisions/J013-core-words.md)。名前の決め方は [J-014](decisions/J014-name-utsushi.md)。この体験が他の人に起きるかは、まだ試していない（実物の試行は 0 件）。

## 順に読む

| 順 | 記録 | 何が分かったか |
|---|---|---|
| 1 | [research/01](research/01-primary-source.md) | NDL の図の観察。側面の棒 |
| 2 | [research/02](research/02-render-backends.md)・[J-001](decisions/J001-render-backend.md) | 描画の方式の実験と決定 |
| 3 | [research/03](research/03-mechanism-dimensions.md)・[J-002](decisions/J002-mechanism-hypotheses.md) | 行程の不足の発見と、押し方の仮説 |
| 4 | [research/04](research/04-questioned-assumptions.md) | 疑わしい前提 Q1〜Q9 |
| 5 | [research/05](research/05-three-axes.md) | 3 つの物差しの採点と、鋭くする案 |
| 6 | [J-003](decisions/J003-zoom-tool.md) | 絵を拡大する道具 |
| 7 | [J-004](decisions/J004-parallel-lines.md) | 担当の分割の案と取りやめ |
| 8 | [research/06](research/06-rederive-defaults.md) | 初期値の出し直し |
| 9 | [research/07](research/07-own-scans.md) | 手元の複写での照合 |
| 10 | [research/08](research/08-fan-axle.md)・[J-005](decisions/J005-axle-default.md) | 扇の中心の位置、開く力、原図の入れ方 |
| 11 | [research/09](research/09-contributions-design.md)・[J-006](decisions/J006-contributions-minimum.md) | 持ち寄りの場の設計と最小の形 |
| 12 | [research/10](research/10-redraw-colors.md)・[J-007](decisions/J007-redraw-not-paste.md) | 図を貼らず描き直す |
| 13 | [J-002 の組み直し](decisions/J002-mechanism-hypotheses.md) | 1 つの既定をやめ、複数の仮説として並べる |
| 14 | [research/11](research/11-naming.md) | 名前の候補。「かがみ」は哲学の話という訂正を含む |
| 15 | [J-008](decisions/J008-own-hypothesis-path.md) | 仮説を自分で立てる道を足す |
| 16 | [J-009](decisions/J009-sheet-and-records.md) | 手順の紙と記録の入口 |
| 17 | [research/12](research/12-tiger.md) | 虎の仮説と寸法。紙の頭は重りより桁で軽い |
| 18 | [J-010](decisions/J010-loop-back-half.md) | 輪の後半と、人が確定する線 |
| 19 | [J-011](decisions/J011-generate-on-the-spot.md) | AI がその場で仮説と寸法を作る本線 |
| 20 | [J-012](decisions/J012-backstage-content-and-own-hypothesis.md) | 山場の置き直し。裏で作って確かめる内容と、自分の仮説を型紙にする口 |
| 21 | [research/13](research/13-critical-review.md) | 前提への批判的レビュー。固めるのは答えか条件か |
| 22 | [J-013](decisions/J013-core-words.md) | 本人の言葉を設計の核にし、レビューの決める点を読み直す |
| 23 | [J-014](decisions/J014-name-utsushi.md) | 名前を utsushi にする。決め方の経緯 |

## 事前の検討との関係（正直に書く所）

開発の開始より前に、題材の調査と構想の検討をしたメモが手元にある。

- メモは参考資料で、repo には入れていない。期間前の試作のコードは読んでも写してもいない。
- 提出するコード・データ・記録はこの repo で期間中に作った。
- `research/` の各メモの「事前メモとの関係」の行に、前から知っていた事か、ここで初めて分かった事か、メモと違う結論になった事かを書く。前から知っていた事を、ここでの発見のようには書かない。
