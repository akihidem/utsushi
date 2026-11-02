# utsushi

江戸の絵本『江都二色』の図と歌から、動く仕組みの仮説を立て、紙の型紙に刷り、作って試した記録で次の版と次の仮説を変える道具（開発中）。

## 開発の過程

調査・比較・捨てた案・試行の記録を repo の中に残している。入口は [docs/process/README.md](docs/process/README.md)。

- 調査メモ: [docs/process/research/](docs/process/research/)
- 判断の記録: [docs/process/decisions/](docs/process/decisions/)
- 試行の索引（仮説 → 型紙 → 実物 → 記録 → 次の版）: [docs/process/trials/](docs/process/trials/)

## 構成

[docs/architecture.md](docs/architecture.md) に置き場と処理の流れ、[docs/features.json](docs/features.json) に機能の状態を書いている。

## 開発基盤と提出物の切り分け

提出するコード・機能・データは、開発期間（2026-11-02 12:00 〜 2026-11-08 20:00 JST）中に、この repo で新規に作った。開発には、従前から運用している Claude Code の作業基盤を道具として使ったが、そのコードは含めていない。題材については開発の開始前に調査と構想の検討をしており、そのメモは参考資料として手元に置いた。この repo には入れていない。扱いは [docs/process/README.md](docs/process/README.md) に書いた。

## できること（実装済み）

- NDL の manifest から出典の記録を作る
- 御来迎と張子の首振り虎の動く仕組みを、複数の仮説として並べ、使い手が先に書いた予想と一緒に見せる。予想が無ければ一覧も型紙も出さない
- 仮説を自分で立てて型紙にし、比べたい時に用意された仮説を並べて見る道も選べる
- 試した結果を 3 値と測った数で記録する。「わからない」を「動いた」に数えない（`python -m omochae.records add`）
- 人の説明と次の思いつきを先に受け、その後で解釈と次の手の案を作る。人が確定して採った物だけで版 2・順位（作り手用）・新しい仮説が変わる。API の鍵が無くても、人が書けば同じ道で回る（`python -m omochae.loop`）
- 図と歌と記録から Claude が仮説と寸法の案を作る制作の道具（裏で使う。案は検査と人の確認を経て内容になる。本物の API では未実行）
- 選んだ仮説の型紙と手順の紙を A4 の PDF に刷る。寸法・重なり・文字・扇の開きの形の検査を通らなければ出さない
- NDL の図を参照して、筒の面と像の色と線を描き直す。絵が折り線をまたがない事と、図を貼っていない事を検査する
- 所蔵・改変・出典 ID・仮説の印を PDF から読み直して検査する
- 玩具の写真・情報・思い出・作り方の知見を手元の画面で受け付け、人が確認した物だけを公開の頁に出す（`PYTHONPATH=src .venv/bin/python -m web.contrib_server`。ssh で転送する時は手元と同じポート番号で）

## 動かし方

要る物: [uv](https://docs.astral.sh/uv/)、poppler（`pdftotext`・`pdftoppm`）、fontconfig（`fc-match`）、字 Noto Serif CJK JP。Ubuntu なら `sudo apt install poppler-utils fontconfig fonts-noto-cjk`。

```
git clone <この repo の URL>
cd <この repo>
./init.sh   # 環境を作る。足りない物があれば名指しして止まる
./run.sh    # 検査を全部回す。結果は out/RESULT.md
```

動く仕組みの答えは 1 つに決めていない。自分の予想を先に書くと、仮説が並び、試したい仮説の型紙を刷れる。

```
export PYTHONPATH=src
.venv/bin/python -m omochae.hypotheses predict "筒を押すと上の飾りが開く。動力は手"
.venv/bin/python -m omochae.hypotheses list
.venv/bin/python -m omochae.hypotheses print H-A   # out/templates/H-A_v1.pdf と手順の紙 H-A_v1_tejun.pdf
.venv/bin/python -m omochae.records add --hypothesis H-A --result わからない --opened-deg 90 --opener 紙の力
```

仮説を自分で立てたい時は、図を見て自分の案を書き、型紙にして試し、比べたくなった時に一覧を見る。

```
.venv/bin/python -m omochae.hypotheses picture
.venv/bin/python -m omochae.hypotheses own "自分の仮説の名前" --how "動かし方" --evidence "図のどこを見たか" \\
  --params '{"push_part": "stick", "hub": "axle", "pusher_height": 84}'
.venv/bin/python -m omochae.hypotheses print-own OWN-1
.venv/bin/python -m omochae.hypotheses list
```

`--params` が無い仮説や今の雛形に乗らない仮説は、記録として残り、型紙にはならない。虎は `--source NDL-1187053-R0000014-R` を付ける（`python -m omochae.hypotheses --source NDL-1187053-R0000014-R predict "…"`）。100% で刷り、紙の物差しが 10cm か確かめる。寸法を直接試す時は `python -m omochae --params 寸法.json`（`push_part` が必須）。

型紙の生成に API の鍵は要らない。

## Claude の活用

生成（Claude）→ 決定的な検査 → 人の確認、の分担で作る。製品の中で Claude を呼ぶ所はまだ無い。詳細は [docs/claude-usage.md](docs/claude-usage.md)。

## 評価（凍結した基準と実行結果）

基準は [tests/frozen/criteria.md](tests/frozen/criteria.md)。`./run.sh` の結果は `out/RESULT.md` に出る。

## データの扱い

人の記録はまだ無い。子どもの写真や声は扱わない。持ち寄りの投稿は確認前も確認後も git に入れない。連絡先は公開しない。

## 素材の出典一覧

| 出典ID | 素材 | 所蔵・出典 | ライセンス | 改変 |
|---|---|---|---|---|
| NDL-1187053-R0000005-L | 『江都二色』御来迎 | 国立国会図書館デジタルコレクション info:ndljp/pid/1187053（米山堂・1931 年の複製） | PDM | 図を参照して寸法・形・色・線を描き直した翻案 |
| NDL-1187053-R0000014-R | 『江都二色』張子の首振り虎 | 同上 | PDM | 図を参照して寸法・形・色・線を描き直した翻案 |

依存: cairosvg（LGPL-3）、shapely（BSD-3）、drawsvg（MIT）、fontTools（MIT）。

## ライセンス

コードと文書は [MIT](LICENSE)。NDL の図と歌は上の出典の表のとおりで、MIT の対象ではない。

## 将来構想（未実装）

写真つきの記録、図鑑の画面、外の人が投稿できる入口。

