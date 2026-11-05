# utsushi

<!-- summary:start -->
## 30 秒の要約

- **なぜ**: 日本の生徒は実験を国際的にとても多くしている。それでも中学 2 年で「理科を使う職業につきたい」は 27%で、国際平均 58%の半分に満たない（TIMSS 2023）。本人は理科と探究の授業、進路指導の場で、生徒が科学を自分の手の届く物と思っていないと感じてきた（最後の文は本人の印象で、調査の数とは分けた。[research/18](docs/process/research/18-field-evidence.md)）。
- **何か**: 失われた玩具の動きを、紙で実験して確かめる道具（本人の決定の一言。紙で動いても昔の作り方の証明にはならない）。目的は科学の面白さを手元で見つける事。江戸の絵本『江都二色』（1773）に図と歌だけが残る玩具の動く仕組みを予想し、紙の型紙に刷り、紙と糸で作って確かめる。まず紙が返事をし、AI からも返事をもらえる（子どもも直接。本人の決定 11-04）。
- **誰と、どの場面で**: 出発は本人の教育現場の学習活動で、本人も使い続ける。広がりとして博物館・科学館のワークショップ、理科教育で興味や関心を引き出す人、小学校の夏休みの自由研究、公開した後は家庭の子どもと親（本人の見立て。どの場面でもまだ試していない）。価値の 1 つに、古い玩具の技術継承を置く。
- **玩具とは**: 飾る完成品でなく、手で動かして確かめられる型（トイ＝モデル）。
- **足りない物**: 手元のトイモデルで自然とやりとりする体験。無いと、大型の装置や計算資源を使う科学にしか真理がないと思ってしまう（本人の言葉からの読み）。
- **核**（本人の言葉「今話してるこの部分が今回のハッカソンの核になる」）: みんなが手で実際に作る事、その楽しさに気づく事が最初。AI が良くなるのは副次的（本人の言葉 11-05）。その後ろで 4 つのループが回る: ①仮説を見ながら考えを話す（反応して型紙が生まれる。ループ 1）→ ②作りながら工夫を話す（型紙が直る。ループ 2。エンジンごと直る。ループ 3）→ ③できた物を上げて工夫と考えを残す（ギャラリーで見られ、型紙もシステムも直る。ループ 4）。話す口とエンジンごとの改善は作っている途中（[research/34](docs/process/research/34-talk-build-share-loop.md)）。
- **輪**: 玩具を開く → 型紙を刷る（型紙は正解でなく AI が考えた仮説）→ 作って試す → 記録と人の工夫と説明 → 版の間に Claude が案を出し人が採る → 次の版。AI の返事は学ぶ人の記録と説明の後で、採点しない。
- **哲学**: 「AI は鏡。江戸の絵を映すことはできるが、映すだけでは遊べない。」全文は [docs/process/philosophy.md](docs/process/philosophy.md)。
- **今の状態**: 型紙の生成と検査は動く（`./run.sh` の場面と試験が全部期待どおり。数は `./run.sh` の最後の行と `out/RESULT.md` に出る）。実物の試行は 1 回（11-04、本人の教え子の卒業生 5 人・全員成人。御来迎が筒から扇を開いて動いた。[記録](docs/process/trials/README.md)）。試した記録は[再現ギャラリー](docs/gallery/index.html)に記録の順で並ぶ。手帖は入口のサイトの中の頁（玩具の頁の「手帖をひらく」から入る）で、作りながら声で手順を聞き、写真と動画を記録に添え、フィードバックもそこで受ける（人が使った確認はまだ）。図鑑の頁と、上げた物と職人の言葉の頁もサイトの中にある。本物の Claude API は未実行。学習の効果は主張しない。成立の条件と今の状態は[仕様書](docs/process/spec.md)、取り込みの関門は[関門の試行の帳面](docs/process/gate-trial.md)。
- **次に読む**: 主張と根拠は [docs/process/claims.md](docs/process/claims.md)、過程の地図は [docs/process/README.md](docs/process/README.md)、機能の状態は [docs/features.json](docs/features.json)、判断待ちは [docs/process/open.json](docs/process/open.json)。
<!-- summary:end -->

## 開発の過程

調査・比較・捨てた案・試行の記録を repo の中に残している。入口は [docs/process/README.md](docs/process/README.md)。

- 調査メモ: [docs/process/research/](docs/process/research/)
- 判断の記録: [docs/process/decisions/](docs/process/decisions/)
- 試行の索引（仮説 → 型紙 → 実物 → 記録 → 次の版）: [docs/process/trials/](docs/process/trials/)
- 仕様書（成立の条件と今の状態）: [docs/process/spec.md](docs/process/spec.md)
- 関門の試行の帳面（Red → Green・証拠・取り込んだ後の書き戻し）: [docs/process/gate-trial.md](docs/process/gate-trial.md)
- 決まった事とまだ決まっていない事: [docs/process/decided-and-open.md](docs/process/decided-and-open.md)
- 再現ギャラリー（試した記録を記録の順に並べた静的な頁）: [docs/gallery/index.html](docs/gallery/index.html)

## 構成

[docs/architecture.md](docs/architecture.md) に置き場と処理の流れ、[docs/features.json](docs/features.json) に機能の状態を書いている。

## 開発基盤と提出物の切り分け

提出するコード・機能・データは、開発期間（2026-11-02 12:00 〜 2026-11-08 20:00 JST）中に、この repo で新規に作った。開発には、従前から運用している Claude Code の作業基盤を道具として使ったが、そのコードは含めていない。題材については開発の開始前に調査と構想の検討をしており、そのメモは参考資料として手元に置いた。この repo には入れていない。扱いは [docs/process/README.md](docs/process/README.md) に書いた。

型紙を作って検査する仕組み（`src/omochae/` の生成と検査の部分）は、期間中にエンジン paper-to-toy として別の repo にも切り出した（本人の決定、11-04）。提出物はこの repo で、paper-to-toy は単独の提出物ではない。切り出した元の commit は `1d17988`。

## できること（動く物。実物の試行は 11-04 の 1 回、本物の API は未確認。機能ごとの状態は `docs/features.json`）

- NDL の manifest から出典の記録を作る
- 御来迎と張子の首振り虎の動く仕組みを、複数の仮説として並べる。開いたらすぐ型紙を刷れる。型紙は正解ではなく、AI が考えた仮説と明示する
- 『江都二色』のほかの玩具も、試作として図鑑から入れる。入口の主役は御来迎と虎の 2 種のまま。雛形は置くだけで読み込まれる。足し方は [docs/architecture.md](docs/architecture.md) の「雛形を足す時」。今の数は次のとおり（`python -m omochae.ledger render` が tree から数えて書き、`./run.sh` が照らす）。

<!-- counts:start -->
- 玩具: 83 件（`data/hypotheses` のファイルの数。必須の 2 種を含む）
- 雛形: 9 本（`src/omochae/templates`。必須の 2 本を含む）
- 凍結の場面: 31 本（`tests/frozen/scenarios`。うち 24 本は落ちるべき紙を入れる負の場面）
<!-- counts:end -->

- 用意した型紙に乗らない仮説には、寸法を作らず、身の回りの紙と紐で作るための「型紙なしの紙」を刷る
- 仮説を自分で立てて型紙にし、比べたい時に用意された仮説を並べて見る道も選べる
- 試した結果を、どの玩具も動きの言葉・その打ち消し・わからないの 3 値で記録し、測った数も残せる。「わからない」を「動いた」に数えない（`python -m omochae.records add`）
- 人の説明と次の思いつきを先に受け、その後で解釈と次の手の案を作る。人が確定して採った物だけで版 2・新しい仮説が変わる。API の鍵が無くても、人が書けば同じ道で回る（`python -m omochae.loop`）
- 図と歌と記録から Claude が仮説と寸法の案を作る制作の道具（裏で使う。案は検査と人の確認を経て内容になる。本物の API では未実行）
- 大人が打った言葉の仮説を、Claude が雛形の寸法に写す。人の文は書き換えず、正しさも評価しない。補った寸法は人が見てから採る（`hypotheses words`。本物の API では未実行）
- 選んだ仮説の型紙と手順の紙と試した後の紙を A4 の PDF に刷る。試した後の紙は次に変える条件を先に出し、物理の説明は折って閉じた札にする。寸法・重なり・文字・扇の開きの形の検査を通らなければ出さない
- NDL の図を参照して、筒の面と像の色と線を描き直す。絵が折り線をまたがない事と、図を貼っていない事を検査する
- 所蔵・改変・出典 ID・仮説の印を PDF から読み直して検査する
- 2 つの仮説を見比べる紙を刷る。勝ち負けの欄を置かず、型紙が同じ組は 1 個を 2 通りに動かす（`hypotheses print-compare H-A H-C`）
- 先生の見る紙を刷る。4 つの着目（動いたか・楽しさ・仕組みの納得・哲学の効果）ごとに見た事を書き、点は付けない（`hypotheses print-teacher`）
- 試した記録を 1 件 1 枚にして、記録の順に並べた再現ギャラリーを書き出す。順位と「再現できた」は書かない（`python -m omochae.gallery`、出来上がりは [docs/gallery/index.html](docs/gallery/index.html)）
- 作っている途中の手順の質問に、聞かれた時だけ答える。仕組みとどの仮説かは答えない。よくある言葉（谷折り・山折り・糊代など）そのものを尋ねる短い問いは刷った説明からその場で答え、それ以外は鍵がある時だけ Claude が答える（`src/api/ask.py`。AI の分は偽の応答でだけ確かめた）
- 手帖: 入口のサイトの中の頁（玩具の頁の「手帖をひらく」から入る）で、ブラウザの音声認識で話し続けて手順を聞き、答えを読み上げ、写真と動画を試した記録に添える。写真と動画の撮影情報は保存の時に外し、中身が写真・動画として読めない物は置かない。動画に ffmpeg を使うので、無い機械では動画を受けない（`src/web/techo_site.py`。人が使った確認はまだ）
- 型紙の折りの部品を Origami Simulator が読める SVG に書き出す。作り手用で、学ぶ人の画面には出さない（`python -m omochae.foldsim H-A`）
- 手元のブラウザの画面で、玩具を選び、仮説を見て型紙を刷り、試した記録と工夫と説明を残す。試した後の紙は記録の後に開く（`PYTHONPATH=src .venv/bin/python -m web.play_server`。人が使った確認はまだ）
- 玩具の写真・情報・思い出・作り方の知見を手元の画面で受け付け、人が確認した物だけを公開の頁に出す（`PYTHONPATH=src .venv/bin/python -m web.contrib_server`。ssh で転送する時は手元と同じポート番号で）

## 動かし方

要る物: Python 3.11 以上、[uv](https://docs.astral.sh/uv/)、poppler（`pdftotext`・`pdftoppm`）、fontconfig（`fc-match`）、FFmpeg（`ffmpeg`・`ffprobe`）、字 Noto Serif CJK JP。Ubuntu 24.04 なら `sudo apt install python3 pipx poppler-utils fontconfig ffmpeg fonts-noto-cjk`、`pipx install uv`、`export PATH="$HOME/.local/bin:$PATH"` で揃う。

```
git clone https://github.com/akihidem/utsushi.git
cd utsushi
./init.sh   # 環境を作る。足りない物があれば名指しして止まる
./run.sh    # 検査を全部回す。結果は out/RESULT.md
```

ほかの入口: `./run-home.sh` は家のパソコンで手元の画面を開く（`--lan` で家の網に開く）。`./run-demo.sh` はデモの一周の画面（入口と手帖。置き場は本物の記録と分けた `out/demo-data`）を立て、パソコン・iPad・iPhone から開ける合言葉付きの https のリンクを作る（cloudflared が要る。止めるとリンクは変わる）。合言葉とリンクは git の外の `out/demo-key`・`out/demo-url` にだけ置く。commit に入れない。

### デモ動画を作る

要る物は上に足して、`google-chrome` か `chromium` の名前で呼べるブラウザ。ffmpeg も要る。足りない物は、書き出しの最初に名前で出て exit 4 で止まる。

```
export PYTHONPATH=src
OUT_DIR="$HOME/utsushi-demo"                           # 書き出す置き場。repo の外にする
.venv/bin/python -m demo.prepare                       # 前の日、網のある所で。道具を確かめ、江戸の絵を全部取り寄せて控えを残す
.venv/bin/python -m demo.prepare --check               # 撮る日の朝、網なしで。写しが控えと合うか
.venv/bin/python -m demo.build --out "$OUT_DIR" --offline          # 網を切って 7 場面を書き出す
PREV_DIR=$(ls -d "$OUT_DIR"/*/ | tail -1)              # 一番新しい書き出しの置き場（フォルダの名前は日時）
.venv/bin/python -m demo.build --out "$OUT_DIR" --run "$PREV_DIR" --only scene3   # 1 場面だけ作り直してつなぎ直す
```

動く仕組みの答えは 1 つに決めていない。玩具を開くと仮説が並び、試したい仮説の型紙をすぐ刷れる。型紙は正解ではなく、AI が考えた仮説です。

```
export PYTHONPATH=src
.venv/bin/python -m omochae.hypotheses list
.venv/bin/python -m omochae.hypotheses print H-A   # out/templates/H-A_v1.pdf と手順の紙 H-A_v1_tejun.pdf
.venv/bin/python -m omochae.records add --hypothesis H-A --result わからない --opened-deg 90 --opener 紙の力
```

仮説ごとの作り方の印（紙一枚・折るだけ・当時の材料）は、部品表と用意する物から出す。頁に札で出し、一覧でも並びは変えない。どの印も上下を表さない。名前と判定はエンジンとそろえてある。

```
.venv/bin/python -m omochae.ways          # 一覧
.venv/bin/python -m omochae.ways --json
```

手帖から上げた記録を消す時は、番号を渡す。記録と、添えた写真・動画・説明・解釈・観察をまとめて消し、番号だけを残す。提案や版の根拠に使われている記録は、その事を言って止まる。その時も `--media-only` で写真と動画と観察は消せる。デモの置き場の記録は `OMOCHAE_DATA` を同じにして打つ。git に入れた物は、履歴からは消えない。

```
.venv/bin/python -m omochae.records withdraw R-0003
.venv/bin/python -m omochae.records withdraw R-0003 --media-only
```

仮説を自分で立てたい時は、図を見て自分の案を書き、型紙にして試し、比べたくなった時に一覧を見る。

```
.venv/bin/python -m omochae.hypotheses picture
.venv/bin/python -m omochae.hypotheses own "自分の仮説の名前" --how "動かし方" --evidence "図のどこを見たか" \
  --params '{"push_part": "stick", "hub": "axle", "pusher_height": 84}'
.venv/bin/python -m omochae.hypotheses print-own OWN-1
.venv/bin/python -m omochae.hypotheses list
```

`--params` が無い仮説や今の雛形に乗らない仮説は、記録として残り、型紙にはならない。虎は `--source NDL-1187053-R0000014-R` を付ける（`python -m omochae.hypotheses --source NDL-1187053-R0000014-R list`）。100% で刷り、紙の物差しが 10cm か確かめる。寸法を直接試す時は `python -m omochae --params 寸法.json`（`push_part` が必須）。

型紙の生成に API の鍵は要らない。

## Claude の活用

生成（Claude）→ 決定的な検査 → 人の確認、の分担で作る。輪の後半・裏の制作・言葉の仮説を寸法に写す口（`src/api/words.py`）・作っている途中の手順の質問の口（`src/api/ask.py`）は Messages API を呼ぶ形を作ったが、本物の API では未実行。詳細は [docs/claude-usage.md](docs/claude-usage.md)、機能の選び分けと開発の運転の形は [docs/process/claude-story.md](docs/process/claude-story.md)。

開発の運転の形の一文: 「Claude Code を作る側の 1 本に据え、人は判断だけをする。判断は 1 か所のキューに集め、PC の前にいなくても手元のチャットから運転できる形にした。決まりで止める所は、作る側の判断でなく機械に任せた。」

## 評価（凍結した基準と実行結果）

基準は [tests/frozen/criteria.md](tests/frozen/criteria.md)。`./run.sh` の結果は `out/RESULT.md` に出る。

- 結果の数は `./run.sh` の最後の行と `out/RESULT.md` で見る（試験は増えていくので、ここには書かない）。凍結の場面の数は「できること」の節にある
- 負の場面の例: `neg_fan_clearance` は扇の中心を縁に置き（`hub: rim`）、帯の開く上限が筒の口の角に当たる寸法を入れ、床 F5.fan_clearance で落ちて紙を出さない（rc 3）事を確かめる

## データの扱い

人の記録は 11-04 の試行の 1 回分（本人の教え子の卒業生 5 人・全員成人のつぶやき、本人の所見、手元の写真と動画。本人の決定で全部載せ、写真は位置情報を外した）。子どもの写真や声は扱わない。持ち寄りの投稿は確認前も確認後も git に入れない。連絡先は公開しない。

## 素材の出典一覧

| 出典ID | 素材 | 所蔵・出典 | ライセンス | 改変 |
|---|---|---|---|---|
| NDL-1187053-R0000005-L | 『江都二色』御来迎 | 国立国会図書館デジタルコレクション info:ndljp/pid/1187053（米山堂・1931 年の複製） | PDM | 図を参照して寸法・形・色・線を描き直した翻案 |
| NDL-1187053-R0000014-R | 『江都二色』張子の首振り虎 | 同上 | PDM | 図を参照して寸法・形・色・線を描き直した翻案 |

依存: cairosvg（LGPL-3）、shapely（BSD-3）、drawsvg（MIT）、fontTools（MIT）、jsonschema（MIT）、anthropic（Apache-2.0）、pillow（MIT-CMU）。版は `requirements.txt`。

## ライセンス

コードと文書は [MIT](LICENSE)。NDL の図と歌は上の出典の表のとおりで、MIT の対象ではない。

## 将来構想（未実装）

外の人が投稿できる入口（入口の形は Google フォームに決めた。生徒の分は集めない。[J-021](docs/process/decisions/J021-contributions-form-students.md)）。写真つきの記録は、手帖から試した記録に写真と動画を添える所までは作った（上の「できること」）。

