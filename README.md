# うつしかがみ

江戸の絵本『江都二色』の図と歌から、動く仕組みの仮説を立て、紙の型紙に刷り、作って試した記録で次の版と次の仮説を変える道具（開発中）。

## 開発の過程

調査・比較・捨てた案・試行の記録を repo の中に残している。入口は [docs/process/README.md](docs/process/README.md)。

- 調査メモ: [docs/process/research/](docs/process/research/)
- 判断の記録: [docs/process/decisions/](docs/process/decisions/)
- 試行の索引（仮説 → 型紙 → 実物 → 記録 → 次の版）: [docs/process/trials/](docs/process/trials/)

## 開発基盤と提出物の切り分け

提出するコード・機能・データは、開発期間（2026-11-02 12:00 〜 2026-11-08 20:00 JST）中に、この repo で新規に作った。開発には、従前から運用している Claude Code の作業基盤を道具として使ったが、そのコードは含めていない。題材については開発の開始前に調査と構想の検討をしており、そのメモは参考資料として手元に置いた。この repo には入れていない。扱いは [docs/process/README.md](docs/process/README.md) に書いた。

## できること（実装済み）

- NDL の manifest から出典の記録を作る
- 御来迎の型紙（押し方 3 通り）を A4 の PDF に刷る。寸法・重なり・文字の検査を通らなければ出さない
- 所蔵・改変・出典 ID・仮説の印を PDF から読み直して検査する

## 動かし方

```
./init.sh
PYTHONPATH=src .venv/bin/python -m omochae --out out/templates/slider_fan_v1
./run.sh
```

poppler（pdftotext・pdftoppm）、uv、字 Noto Serif CJK JP が要る。

## Claude の活用

生成（Claude）→ 決定的な検査 → 人の確認、の分担で作る。製品の中で Claude を呼ぶ所はまだ無い。詳細は [docs/claude-usage.md](docs/claude-usage.md)。

## 評価（凍結した基準と実行結果）

基準は [tests/frozen/criteria.md](tests/frozen/criteria.md)。`./run.sh` の結果は `out/RESULT.md` に出る。

## データの扱い

人の記録はまだ無い。子どもの写真や声は扱わない。

## 素材の出典一覧

| 出典ID | 素材 | 所蔵・出典 | ライセンス | 改変 |
|---|---|---|---|---|
| NDL-1187053-R0000005-L | 『江都二色』御来迎 | 国立国会図書館デジタルコレクション info:ndljp/pid/1187053（米山堂・1931 年の複製） | PDM | 図をもとに型紙を起こした翻案 |
| NDL-1187053-R0000014-R | 『江都二色』張子の首振り虎 | 同上 | PDM | まだ使っていない |

依存: cairosvg（LGPL-3）、shapely（BSD-3）、drawsvg（MIT）、fontTools（MIT）。

## 将来構想（未実装）

仮説生成、記録の解釈、次の版の提案、虎の雛形、図鑑の画面。
