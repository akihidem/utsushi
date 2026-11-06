# utsushi

> 失われた玩具の動きを、紙で実験して確かめる道具

「AIが良くなるのは副次的なもので、みんなが手で実際に作ることその楽しさに気づくことが最初。」（本人の言葉）

<!-- 4 つのループの絵の置き場。序の頁に入れる案の絵で、本人の採否待ち。 -->
<!-- デモ動画のリンクの置き場。上げた後に足す。 -->

江戸の絵本『江都二色』（1773）には、玩具の図と歌だけが残っています。動く仕組みは書かれていません。

Claude が考えた型紙を紙に刷り、切って、折って、作って、動きを確かめます。

型紙は正解ではなく、Claude が考えた仮説です。作った人の工夫から、人が直しを選んで、次の版にします。

<details>
<summary>くわしい要約（10 項目）</summary>

<!-- summary:start -->
## 30 秒の要約

- **なぜ**: 日本の生徒は実験を国際的にとても多くしている。それでも中学 2 年で「理科を使う職業につきたい」は 27%で、国際平均 58%の半分に満たない（TIMSS 2023）。本人は理科と探究の授業、進路指導の場で、生徒が科学を自分の手の届く物と思っていないと感じてきた（最後の文は本人の印象で、調査の数とは分けた。[research/18](docs/process/research/18-field-evidence.md)）。
- **何か**: 失われた玩具の動きを、紙で実験して確かめる道具（本人の決定の一言。紙で動いても昔の作り方の証明にはならない）。目的は科学の面白さを手元で見つける事。江戸の絵本『江都二色』（1773）に図と歌だけが残る玩具の動く仕組みを予想し、紙の型紙に刷り、紙と糸で作って確かめる。まず紙が返事をし、Claude からも返事をもらえる（子どもも直接。本人の決定 11-04）。
- **誰と、どの場面で**: 出発は本人の教育現場の学習活動で、本人も使い続ける。広がりとして博物館・科学館のワークショップ、理科教育で興味や関心を引き出す人、小学校の夏休みの自由研究、公開した後は家庭の子どもと親（本人の見立て。どの場面でもまだ試していない）。価値の 1 つに、古い玩具の技術継承を置く。
- **玩具とは**: 飾る完成品でなく、手で動かして確かめられる型（トイ＝モデル）。
- **足りない物**: 手元のトイモデルで自然とやりとりする体験。無いと、大型の装置や計算資源を使う科学にしか真理がないと思ってしまう（本人の言葉からの読み）。
- **核**（本人の言葉「今話してるこの部分が今回のハッカソンの核になる」）: 「AIが良くなるのは副次的なもので、みんなが手で実際に作ることその楽しさに気づくことが最初。」（本人の言葉 11-05）。その後ろで 4 つのループが回る: ①仮説を見ながら考えを話す（反応して型紙が生まれる。ループ 1）→ ②作りながら工夫を話す（型紙が直る。ループ 2。エンジンごと直る。ループ 3）→ ③できた物を上げて工夫と考えを残す（ギャラリーで見られ、型紙もシステムも直る。ループ 4）。話す口とエンジンごとの改善は作っている途中（[research/34](docs/process/research/34-talk-build-share-loop.md)）。
- **輪**: 玩具を開く → 型紙を刷る（型紙は正解でなく Claude が考えた仮説）→ 作って試す → 記録と人の工夫と説明 → 版の間に Claude が案を出し人が採る → 次の版。Claude の返事は学ぶ人の記録と説明の後で、採点しない。
- **哲学**: 「AI は鏡。江戸の絵を映すことはできるが、映すだけでは遊べない。」全文は [docs/process/philosophy.md](docs/process/philosophy.md)。
- **今の状態**: 型紙の生成と検査は動く（`./run.sh` の場面と試験が全部期待どおり。数は `./run.sh` の最後の行と `out/RESULT.md` に出る）。実物の試行は 1 回（11-04、本人の教え子の卒業生 5 人・全員成人。御来迎は前の組の紙で、筒から扇を開いて動いた。どの案の紙かは分からず、今の組の紙は実物で確かめていない。[記録](docs/process/trials/README.md)）。試した記録は[再現ギャラリー](docs/gallery/index.html)に記録の順で並ぶ。手帖は入口のサイトの中の頁（玩具の頁の「手帖をひらく」から入る）で、作りながら声で手順を聞き、写真と動画を記録に添え、フィードバックもそこで受ける（人が使った確認はまだ）。図鑑の頁と、作った物と職人の言葉の頁もサイトの中にある。本物の Claude API は未実行。学習の効果は主張しない。成立の条件と今の状態は[仕様書](docs/process/spec.md)、取り込みの関門は[関門の試行の帳面](docs/process/gate-trial.md)。
- **次に読む**: 主張と根拠は [docs/process/claims.md](docs/process/claims.md)、過程の地図は [docs/process/README.md](docs/process/README.md)、機能の状態は [docs/features.json](docs/features.json)、判断待ちは [docs/process/open.json](docs/process/open.json)。
<!-- summary:end -->

</details>

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

型紙を作って検査する仕組み（`src/omochae/` の生成と検査の部分）は、期間中にエンジン paper-to-toy として別の repo にも切り出した（本人の決定、11-04）。提出物はこの repo で、paper-to-toy は単独の提出物ではない。切り出した元の commit は `1d17988`。型紙を作る仕組みと検査を直す時は、先に paper-to-toy を直して、それからこの repo に取り込む（両方を比べる道具は `tests/compare_engine.py`）。

## できること（動く物。実物の試行は 11-04 の 1 回、本物の API は未確認。機能ごとの状態は `docs/features.json`）

- NDL の manifest から出典の記録を作る
- 御来迎と張子の首振り虎は、おもちゃごとに型紙を 1 枚だけ出します。開いたら、すぐ型紙を作れます。型紙は正解ではなく、Claude が考えた仮説（ためしの案）です。紙にも頁にもそう書いています。
- 『江都二色』のほかの玩具も、試作として図鑑から入れる。入口の主役は御来迎と虎の 2 種のまま。雛形は置くだけで読み込まれる。足し方は [docs/architecture.md](docs/architecture.md) の「雛形を足す時」。今の数は次のとおり（`PYTHONPATH=src .venv/bin/python -m omochae.ledger render` が tree から数えて書き、`./run.sh` が照らす）。

<!-- counts:start -->
- 玩具: 83 件（`data/hypotheses` のファイルの数。必須の 2 種を含む）
- 雛形: 9 本（`src/omochae/templates`。必須の 2 本を含む）
- 凍結の場面: 34 本（`tests/frozen/scenarios`。うち 27 本は落ちるべき紙を入れる負の場面）
<!-- counts:end -->

- 用意した型紙に乗らない仮説には、寸法を作らず、身の回りの紙と紐で作るための「型紙なしの紙」を刷る
- 型紙を見て考えを話すと、その考えに合わせて紙を作り直します。今は御来迎と虎だけです。本物の Claude では、まだ試していません。
- 試した結果を、どの玩具も動きの言葉・その打ち消し・わからないの 3 値で記録し、測った数も残せる。「わからない」を「動いた」に数えない（`PYTHONPATH=src .venv/bin/python -m omochae.records add`）
- 人の説明と次の思いつきを先に受け、その後で解釈と次の手の案を作る。人が確かめて採った物だけで、次の版ができます。次の版にできない案は、作る側の控えに残します。API の鍵が無くても、人が書けば同じ道で回る（`PYTHONPATH=src .venv/bin/python -m omochae.loop`）
- 図と歌と記録から Claude が仮説と寸法の案を作る制作の道具（裏で使う。案は検査と人の確認を経て内容になる。本物の API では未実行）
- 大人が打った言葉の仮説を、Claude が雛形の寸法に写す。人の文は書き換えず、正しさも評価しない。補った寸法は人が見てから採る（`hypotheses words`。本物の API では未実行）
- 頁に出ている 1 枚の型紙と、手順の紙と、試した後の紙を、A4 の PDF にします。試した後の紙は次に変える条件を先に出し、物理の説明は折って閉じた札にする。寸法・重なり・文字・扇の開きの形の検査を通らなければ出さない
- NDL の図を参照して、筒の面と像の色と線を描き直す。絵が折り線をまたがない事と、図を貼っていない事を検査する
- 所蔵・改変・出典 ID・仮説の印を PDF から読み直して検査する
- 先生の見る紙を刷る。4 つの着目（動いたか・楽しさ・仕組みの納得・哲学の効果）ごとに見た事を書き、点は付けない（`hypotheses print-teacher`）
- 試した記録を 1 件 1 枚にして、記録の順に並べた再現ギャラリーを書き出す。順位と「再現できた」は書かない（`PYTHONPATH=src .venv/bin/python -m omochae.gallery`、出来上がりは [docs/gallery/index.html](docs/gallery/index.html)）
- 作っている途中の手順の質問に、聞かれた時だけ答える。仕組みとどの仮説かは答えない。よくある言葉（谷折り・山折り・糊代など）そのものを尋ねる短い問いは刷った説明からその場で答え、それ以外は鍵がある時だけ Claude が答える（`src/api/ask.py`。Claude の分は偽の応答でだけ確かめた）
- 手帖: 入口のサイトの中の頁（玩具の頁の「手帖をひらく」から入る）で、1 手 1 画面で今の手順の絵と 1 文を出す。「はじめる」の後は声かボタンで進み（言葉の全部が一致した時だけ操作にして、ほかは質問として聞く）、答えを読み上げ、写真と動画を試した記録に添える。写真と動画の撮影情報は保存の時に外し、中身が写真・動画として読めない物は置かない。動画に ffmpeg を使うので、無い機械では動画を受けない（`src/web/techo_site.py`。人が使った確認はまだ）
- 話す口: 仮説を見て考えを話す（玩具の頁）、作りながら工夫を話す（作りながら見る頁）、できた物を上げた後に足す（手帖の記録の札）の 3 か所で、声か字を、字だけで残す。声は録らず、送らない。作りながら話した工夫は、記録を残すと、その記録に結ばれる。話した字は、ほかの人の頁に出さず、作る側の頁と、型紙をよくする輪の材料だけが読む（本人の決定 11-06、J-034。頁に出すのは Claude が整理した字だけで、その置き場はまだ無い。名前などは書かないお願いを出し、連絡先・名乗り・学年と組・学校の名前の形は入口で落とす）。話す釦は、声を端末の中だけで字にできる画面ではその形で聞き、できない画面（iPhone・iPad など）ではブラウザの既定の音声認識で聞いて、断りを出す（`OMOCHAE_VOICE=local` で、端末の中だけで字にできる画面に限る。`off` で釦を出さない）。字は、残す前に本人が見て直せる（`src/web/hanasu.py`・`src/omochae/talk_log.py`。実機で声を入れた確認はまだ）
- 型紙の折りの部品を Origami Simulator が読める SVG に書き出す。作り手用で、学ぶ人の画面には出さない（`PYTHONPATH=src .venv/bin/python -m omochae.foldsim H-A`）
- 手元のブラウザの画面で、玩具を選び、仮説を見て型紙を刷り、試した記録と工夫と説明を残す。試した後の紙は記録の後に開く（`PYTHONPATH=src .venv/bin/python -m web.play_server`。人が使った確認はまだ）
- 玩具の写真・情報・思い出・作り方の知見を手元の画面で受け付け、人が確認した物だけを公開の頁に出す（`PYTHONPATH=src .venv/bin/python -m web.contrib_server`。ssh で転送する時は手元と同じポート番号で）

## 動かし方

要る物: git、Python 3.11 以上、[uv](https://docs.astral.sh/uv/)、poppler（`pdftotext`・`pdftoppm`）、fontconfig（`fc-match`）、FFmpeg（`ffmpeg`・`ffprobe`）、字 Noto Serif CJK JP。Ubuntu 24.04 なら `sudo apt install git python3 pipx poppler-utils fontconfig ffmpeg fonts-noto-cjk`、`pipx install uv`、`export PATH="$HOME/.local/bin:$PATH"` で揃う。

```
git clone https://github.com/akihidem/utsushi.git
cd utsushi
./init.sh   # 環境を作る。足りない物があれば名指しして止まる
./run.sh # 検査を全部回す。8〜9 分かかります。結果は out/RESULT.md
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

動く仕組みの答えは、1 つに決めていません。おもちゃを開くと、仮説（ためしの案）を 1 つ見て、その型紙をすぐ作れます。型紙は正解ではなく、Claude が考えた仮説です。一覧の命令（list）は、作る側の控えの案も出します。

```
export PYTHONPATH=src
.venv/bin/python -m omochae.hypotheses list
.venv/bin/python -m omochae.hypotheses print H-A   # out/templates/NDL-1187053-R0000005-L_H-A_v1.pdf と手順の紙 NDL-1187053-R0000005-L_H-A_v1_tejun.pdf
.venv/bin/python -m omochae.records add --hypothesis H-A --result わからない --opened-deg 90 --opener 紙の力
```

仮説ごとの作り方の印（紙一枚・折るだけ・当時の材料）は、部品表と用意する物から出す。頁に札で出し、一覧でも並びは変えない。どの印も上下を表さない。名前と判定はエンジンとそろえてある。

```
.venv/bin/python -m omochae.ways          # 一覧
.venv/bin/python -m omochae.ways --json
```

手帖から上げた記録を消す時は、番号を渡す。記録と、添えた写真・動画・説明・解釈・観察をまとめて消し、番号だけを残す。提案や版の根拠に使われている記録は、その事を言って止まる。その時も `--media-only` で写真と動画と観察は消せる。デモの置き場の記録は `OMOCHAE_DATA` を同じにして打つ。git に入れた物は、履歴からは消えない。話した字（考え・工夫・上げた後）と、記録に書いた字（ひとこと・感想・答え・思いつき・工夫）と、手書きの説明の字と、字が刷られた紙は `--talk-only` で消せる。その記録を根拠に Claude が書いた解釈と案の文も全部消え、ほかの人が書いた文は引用を含む文が消える（記録の番号と寸法の根拠と、説明があった印は残る）。

取り下げると、このサイトの中からは消えます。前にエンジンへ渡した分は残ります

```
.venv/bin/python -m omochae.records withdraw R-0003
.venv/bin/python -m omochae.records withdraw R-0003 --media-only
.venv/bin/python -m omochae.records withdraw R-0003 --talk-only
```

自分の案を試したい時は、頁で考えを話します。命令で試す時は、図を見て自分の案を書き、型紙にできます。

```
.venv/bin/python -m omochae.hypotheses picture
.venv/bin/python -m omochae.hypotheses own "自分の仮説の名前" --how "動かし方" --evidence "図のどこを見たか" \
  --params '{"push_part": "stick", "hub": "axle", "pusher_height": 84}'
.venv/bin/python -m omochae.hypotheses print-own OWN-1
.venv/bin/python -m omochae.hypotheses list
```

`--params` が無い仮説や今の雛形に乗らない仮説は、記録として残り、型紙にはならない。虎は `--source NDL-1187053-R0000014-R` を付ける（`PYTHONPATH=src .venv/bin/python -m omochae.hypotheses --source NDL-1187053-R0000014-R list`）。100% で刷り、紙の物差しが 10cm か確かめる。寸法を直接試す時は `PYTHONPATH=src .venv/bin/python -m omochae --params 寸法.json`（`push_part` が必須）。

型紙の生成に API の鍵は要らない。

## Claude の活用

中心は、作り方そのものにある。この作品は、Claude Code のセッションを担当ごとに並べ、同時に作った。最初（11-02 から 11-04 の昼まで）は作る側の 1 本のセッションが作り、11-04 から順に下の形にした。詳しくは [docs/process/claude-story.md](docs/process/claude-story.md) の 3 節。担当・worktree・PR の数は、提出の日に数え直して書く。

- **設計を先に**: 作る前に Issue を書く。目的・なぜか・どうしたらいいか（比べた案と推し）・ゴールの要件の 4 つで書く。線を大きく分けた回（4 つのループをつなぐ回）では、担当の線ごとの持つファイルと待つ物、合体の順を足し、担当どうしで持つファイルが重ならないか、待つ順に輪が無いかを機械で確かめてから配った。不具合の直しと既存の動作の変更は、変える前に落ちて変えた後に通る試験を Issue に書いてから取り込む（11-04 からの試行）
- **担当ごとに worktree を分けて同時に作る**: 1 担当 = 1 つの枝・1 つの git worktree・1 つの Claude Code のセッション。枝は今の main から切る。同じ作業の木を 2 つの担当で書かない
- **別の目の確かめ**: 作った担当と別のセッションが、枝の差分か PR を読む（すべての PR で読んだかは数えていない）。止める時は判断のキューに止めの札を上げ、見つけた穴は作った担当へ返して直させる
- **合体の道**（11-05 の夜から）: 合体は 1 つの道を通し、1 本ずつ流す。まっさらな clone で「今の main ＋ PR の頭」を合わせ、`./init.sh` と `./run.sh` の全部の試験が通った木だけを、頭の commit を固定して合体する。止めの札がある PR、下書き、「本人の OK まで合体しません」と書いた PR は、ここで機械が止める
- **本人の決定の流れ**: 本人は作る側の画面の前にいない。手元のチャットで窓口（本人の個人のエージェント、Claude のセッション）に話す。本人の前に出すのは、外に出る操作・文面と哲学の採否・検査に落ちた物の 3 種類だけ（11-04 の本人の線引き）。担当はそれを推しを付けて判断のキューに上げ、窓口が 1 件ずつ本人に見せる。小さい判断は推しで進め、1 件ずつ記録に残す。11-06 からは、推しで大丈夫そうな判断を窓口が本人の委任で選び、その印を付けて残す。今は、利用者に見せる新しい文の PR は本文に「本人の OK まで合体しません」と書き、本人が読んで OK を出してから合体する
- **短い文脈で回す**: 長く動いたセッションは、仕事の節目で短い引き継ぎメモを書いてから新しく始め、メモと決まりのファイルだけを読んで続ける（本人の指示で 11-06 から試している。効き目はまだ測っていない）。大事な決まりは、前から会話でなくファイルに置いている
- **弱さ**: 合体の道ができる前は、GitHub の判定だけを見て合体した PR で、main の試験が落ちた。並べた事で速くなったか、品質が上がったかは測っていない。ほかの弱さも claude-story.md の 3 節に書いた

作品の側では、生成（Claude）→ 決定的な検査 → 人の確認、の分担で作る。輪の後半・裏の制作・言葉の仮説を寸法に写す口（`src/api/words.py`）・作っている途中の手順の質問の口（`src/api/ask.py`）は Messages API を呼ぶ形を作ったが、本物の API では未実行。詳細は [docs/claude-usage.md](docs/claude-usage.md)、機能の選び分けは [docs/process/claude-story.md](docs/process/claude-story.md) の 2 節。

開発の作り方の一文: 「設計を先に固め、Claude Code のセッションを担当ごとに worktree で並べて同時に作る。作った者と別の目が読み、合わせた木で全部の試験が通った物だけを 1 つの道で合体する。本人は手元のチャットから、決める事だけをする。」

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

