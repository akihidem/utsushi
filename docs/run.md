# 動かし方とできる事（くわしく）

README の「repo の地図と動かし方」の続きです。字は 2026-11-08 の README の「できること」「動かし方」「評価」の節から、そのまま移しました（README を審査の方が読める形に組み直した時）。

## できること（動く物。機能ごとの状態は `docs/features.json`）

- NDL の manifest から出典の記録を作る
- 御来迎と張子の首振り虎は、おもちゃごとに型紙を 1 枚だけ出します。開いたら、すぐ型紙を作れます。型紙は正解ではなく、Claude が考えた仮説（ためしの案）です。紙にも頁にもそう書いています。
- 『江都二色』のほかの玩具も、試作として図鑑から入れる。入口の主役は御来迎と虎の 2 種のまま。雛形は置くだけで読み込まれる。足し方は [docs/architecture.md](architecture.md) の「雛形を足す時」。今の数は README の「確かめた事と、まだの事」の数の欄にある（`PYTHONPATH=src .venv/bin/python -m omochae.ledger render` が tree から数えて書き、`./run.sh` が照らす）。

- 用意した型紙に乗らない仮説には、寸法を作らず、身の回りの紙と紐で作るための「型紙なしの紙」を刷る
- 型紙を見て考えを話すと、その考えに合わせて紙を作り直します。今は御来迎と虎だけです。本物の Claude では、まだ試していません。
- 試した結果を、どの玩具も動きの言葉・その打ち消し・わからないの 3 値で記録し、測った数も残せる。「わからない」を「動いた」に数えない（`PYTHONPATH=src .venv/bin/python -m omochae.records add`）
- 人の説明と次の思いつきを先に受け、その後で解釈と次の手の案を作る。人が確かめて採った物だけで、次の版ができます。次の版にできない案は、作る側の控えに残します。API の鍵が無くても、人が書けば同じ道で回る（`PYTHONPATH=src .venv/bin/python -m omochae.loop`）
- 図と歌と記録から Claude が仮説と寸法の案を作る制作の道具（裏で使う。案は検査と人の確認を経て内容になる。11-07 に本物の鍵で手元から呼び、動いた）
- 大人が打った言葉の仮説を、Claude が雛形の寸法に写す。人の文は書き換えず、正しさも評価しない。補った寸法は人が見てから採る（`hypotheses words`。11-07 に本物の鍵で手元から呼び、動いた）
- 頁に出ている 1 枚の型紙と、手順の紙と、試した後の紙を、A4 の PDF にします。試した後の紙は次に変える条件を先に出し、物理の説明は折って閉じた札にする。寸法・重なり・文字・扇の開きの形の検査を通らなければ出さない
- NDL の図を参照して、筒の面と像の色と線を描き直す。絵が折り線をまたがない事と、図を貼っていない事を検査する
- 所蔵・改変・出典 ID・仮説の印を PDF から読み直して検査する
- 先生の見る紙を刷る。4 つの着目（動いたか・楽しさ・仕組みの納得・哲学の効果）ごとに見た事を書き、点は付けない（`hypotheses print-teacher`）
- 試した記録を 1 件 1 枚にして、記録の順に並べた再現ギャラリーを書き出す。順位と「再現できた」は書かない（`PYTHONPATH=src .venv/bin/python -m omochae.gallery`、出来上がりは [docs/gallery/index.html](gallery/index.html)）
- 作っている途中の手順の質問に、聞かれた時だけ答える。仕組みとどの仮説かは答えない。よくある言葉（谷折り・山折り・糊代など）そのものを尋ねる短い問いは刷った説明からその場で答え、それ以外は鍵がある時だけ Claude が答える（`src/api/ask.py`。Claude の分は 11-07 に本物の鍵で手元から呼び、動いた）
- 手帖: サイトの中の頁（玩具の頁の型紙の窓の「つくる」から入る）で、1 手 1 画面で今の手順の絵と 1 文を出す。「はじめる」の後は声かボタンで進み（言葉の全部が一致した時だけ操作にして、ほかは質問として聞く）、答えを読み上げ、写真と動画を試した記録に添える。写真と動画の撮影情報は保存の時に外し、中身が写真・動画として読めない物は置かない。動画に ffmpeg を使うので、無い機械では動画を受けない（`src/web/techo_site.py`。人が使った確認はまだ）
- 上げた動画の声: 頁に出す動画からは落とし、別に非公開で写して、この機械の中で字にしてから消す。字にできなければ 72 時間で消す。字は作る側だけが読み、頁には出さない（`src/omochae/voice_text.py`）。
- 話す口: 仮説を見て考えを話す（玩具の頁）、作りながら工夫を話す（作りながら見る頁）、できた物を上げた後に足す（手帖の記録の札）の 3 か所で、字の欄に書いた字（端末のキーボードのマイクで話して入れてもよい）を残す。作りながら見る頁と のこすの頁の工夫の欄では、「声を録る」を押してから、もう一度押すまでの声も録り、のこすで承認した時に送る（サーバの中で字にしてから消す。記録の札の足す口では録らない）。作りながら話した工夫は、記録を残すと、その記録に結ばれる。話した字は、ほかの人の頁に出さず、作る側の頁と、型紙をよくする輪の材料だけが読む（本人の決定 11-06、J-034。頁に出すのは Claude が整理した字だけで、その置き場はまだ無い。名前などは書かないお願いを出し、連絡先・名乗り・学年と組・学校の名前の形は入口で落とす）。サイトは声を字にしない（11-08 にブラウザの音声認識と切り替え `OMOCHAE_VOICE` を外した）。字は、残す前に本人が見て直せる（`src/web/hanasu.py`・`src/omochae/talk_log.py`。実機でキーボードのマイクの字を入れた確認はまだ）
- 型紙の折りの部品を Origami Simulator が読める SVG に書き出す。作り手用で、学ぶ人の画面には出さない（`PYTHONPATH=src .venv/bin/python -m omochae.foldsim H-A`）
- 手元のブラウザの画面で、玩具を選び、仮説を見て型紙を刷り、試した記録と工夫と説明を残す。試した後の紙は記録の後に開く（`PYTHONPATH=src .venv/bin/python -m web.play_server`。人が使った確認はまだ）
- 玩具の写真・情報・思い出・作り方の知見を手元の画面で受け付け、人が確認した物だけを公開の頁に出す（`PYTHONPATH=src .venv/bin/python -m web.contrib_server`。ssh で転送する時は手元と同じポート番号で）

## 動かし方の続き

ほかの始め方: `./run-home.sh` は家のパソコンで手元の画面を開く（`--lan` で家の網に開く）。`./run-demo.sh` はデモの一周の画面（最初の頁と手帖。置き場は本物の記録と分けた `out/demo-data`）を立て、パソコン・iPad・iPhone から開ける合言葉付きの https のリンクを作る（cloudflared が要る。止めるとリンクは変わる）。合言葉とリンクは git の外の `out/demo-key`・`out/demo-url` にだけ置く。commit に入れない。

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

## 評価（凍結した基準と実行結果）

基準は [tests/frozen/criteria.md](../tests/frozen/criteria.md)。`./run.sh` の結果は `out/RESULT.md` に出る。

- 結果の数は `./run.sh` の最後の行と `out/RESULT.md` で見る（試験は増えていくので、ここには書かない）。凍結の場面の数は README の数の欄にある
- 負の場面の例: `neg_fan_clearance` は扇の中心を縁に置き（`hub: rim`）、帯の開く上限が筒の口の角に当たる寸法を入れ、床 F5.fan_clearance で落ちて紙を出さない（rc 3）事を確かめる
