# 開発の過程の読み方

この作品は、できた物だけでなく、どう調べ、何を比べ、何を捨てて決めたかが repo から読めるように作っている。記録は作業しながら残し、後からまとめて書かない。時刻の証拠は commit の履歴。

| 置き場 | 中身 |
|---|---|
| `research/` | 調べた事のメモ。一次資料か実験の結果と、そこから言える事・言えない事 |
| `decisions/` | 判断の記録 J-nnn。比べた案・捨てた案・決めた理由 |
| `trials/` | 仮説 → 型紙 → 実物の試行 → 記録 → 次の版 の流れの索引。実際に試した物だけを載せる |
| `../progress.md` | 作業の 1 行記録 |

調査メモと判断の案は Claude Code のセッションが書いた。人が決めた事と、人の手で試した事は、その旨を明記する。

## 順に読む

| 順 | 記録 | 何が分かったか |
|---|---|---|
| 1 | [research/01](research/01-primary-source.md) | NDL の図の観察。側面の棒 |
| 2 | [research/02](research/02-render-backends.md)・[J-001](decisions/J001-render-backend.md) | 描画の方式の実験と決定 |
| 3 | [research/03](research/03-mechanism-dimensions.md)・[J-002](decisions/J002-mechanism-tab.md) | 行程の不足の発見と、押し方の仮説 |
| 4 | [research/04](research/04-questioned-assumptions.md) | 疑わしい前提 Q1〜Q9 |
| 5 | [research/05](research/05-three-axes.md) | 3 つの物差しの採点と、鋭くする案 |
| 6 | [J-003](decisions/J003-zoom-tool.md) | 絵を拡大する道具 |
| 7 | [J-004](decisions/J004-parallel-lines.md) | 担当の分割の案と取りやめ |
| 8 | [research/06](research/06-rederive-defaults.md) | 初期値の出し直し |
| 9 | [research/07](research/07-own-scans.md) | 手元の複写での照合 |

## 事前の検討との関係（正直に書く所）

開発の開始より前に、題材の調査と構想の検討をしたメモが手元にある。

- メモは参考資料で、repo には入れていない。期間前の試作のコードは読んでも写してもいない。
- 提出するコード・データ・記録はこの repo で期間中に作った。
- `research/` の各メモの「事前メモとの関係」の行に、前から知っていた事か、ここで初めて分かった事か、メモと違う結論になった事かを書く。前から知っていた事を、ここでの発見のようには書かない。
