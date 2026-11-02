# 主張と根拠

`claims.json` から `python -m omochae.ledger render` で描いた表。手で直さない。根拠の文が今もファイルに在る事は `./run.sh` が確かめる。

## 確かさの種類

| 種類 | 意味 |
|---|---|
| 計算 | 式で出した。実物では未確認 |
| 測定 | ファイルや記録を測った |
| 自動試験 | 試験が通る |
| 偽の応答の試験 | Claude の応答は偽物 |
| 文献 | 批評役が読んだ範囲で、書き手は読み直していない |
| 未確認 | まだ試していない |
| 立場 | 作品の立場で、確かめる物ではない |

## 主張

| ID | 主張 | 確かさ | 根拠 |
|---|---|---|---|
| C-01 | 検査に落ちる型紙は刷らない | 自動試験 | [criteria.md](../../tests/frozen/criteria.md)、[run_floors.py](../../tests/run_floors.py) |
| C-02 | 予想を書く前に仮説を見せない | 自動試験 | [test_hypotheses.py](../../tests/test_hypotheses.py) |
| C-03 | 人の説明の前に Claude の解釈を呼ばない | 偽の応答の試験 | [test_loop.py](../../tests/test_loop.py) |
| C-04 | 順位と集計は学ぶ人の画面に出さない | 自動試験 | [test_loop.py](../../tests/test_loop.py) |
| C-05 | 人が確定していない解釈は根拠にできない | 偽の応答の試験 | [loop.py](../../src/omochae/loop.py) |
| C-06 | 持ち寄りは端末で人が打たないと公開できない | 自動試験 | [test_contrib.py](../../tests/test_contrib.py) |
| C-07 | 下から押す形は初期の寸法で行程が 20mm 足りない | 計算 | [03-mechanism-dimensions.md](research/03-mechanism-dimensions.md) |
| C-08 | 台に載せる形は扇が 180° で筒にぶつかる | 計算 | [08-fan-axle.md](research/08-fan-axle.md) |
| C-09 | 虎の紙の頭は重りより桁で軽い | 計算 | [12-tiger.md](research/12-tiger.md) |
| C-10 | 図を貼らず描き直すと PDF が 1.8MB から約 0.1MB になった | 測定 | [J007-redraw-not-paste.md](decisions/J007-redraw-not-paste.md)、[README.md](trials/sheets/README.md) |
| C-11 | 判断待ちの最長は 124 分で、10 分以上の待ちは計 223 分 | 測定 | [how-it-was-built.md](how-it-was-built.md) |
| C-12 | AI の版の調整が学習を上げた直接の証拠は見つかっていない | 文献 | [13-critical-review.md](research/13-critical-review.md) |
| C-13 | 素の GPT で練習は 48% 上がり、試験は 17% 下がった例がある | 文献 | [13-critical-review.md](research/13-critical-review.md) |
| C-14 | 紙の型紙が実物で開くか | 未確認 | [README.md](trials/README.md) |
| C-15 | 本物の Claude API で輪が回るか | 未確認 | [J010-loop-back-half.md](decisions/J010-loop-back-half.md) |
| C-16 | 作っているうちに新しい考えが湧く | 未確認 | [J013-core-words.md](decisions/J013-core-words.md) |
| C-17 | 返事をするのは AI でなく素材と工作 | 立場 | [J013-core-words.md](decisions/J013-core-words.md) |
| C-18 | 学習の効果より学習の再定義を物差しにする | 立場 | [J013-core-words.md](decisions/J013-core-words.md) |
| C-19 | 本人の現場と、誰が使い続けるかは、まだ言えない | 未確認 | [14-judging-criteria.md](research/14-judging-criteria.md) |
| C-20 | 言葉の口は人の文を書き換えず、隠れた寸法の補いを通さない | 偽の応答の試験 | [test_words.py](../../tests/test_words.py) |
| C-21 | 試した後の紙は対比を先に出し、説明は折って閉じた札に置く | 自動試験 | [test_words.py](../../tests/test_words.py) |
| C-22 | 閉じた札が考える邪魔をしないか | 未確認 | [J013-core-words.md](decisions/J013-core-words.md) |
| C-23 | 手元でトイモデルと遊ぶ体験をしないと科学の面白さに気づけない | 立場 | [philosophy.md](philosophy.md) |
| C-24 | 御来迎の本体は紙と糸で作る。ただし軸の竹串なども使う | 自動試験 | [philosophy.md](philosophy.md)、[slider_fan.py](../../src/omochae/templates/slider_fan.py) |
| C-25 | 虎の物差しは頭が揺れるかどうかで、仮説の違いは作り方の違い | 立場 | [15-philosophy-review.md](research/15-philosophy-review.md) |
| C-26 | 日本の小 4 の理科の実験は週 1 回以上が 59.6% で、実験経験が無いとは言えない | 文献 | [15-philosophy-review.md](research/15-philosophy-review.md) |
| C-27 | 「学習の再定義」と「AI と子どものタッグ」は、まだ実装に無い言葉 | 未確認 | [15-philosophy-review.md](research/15-philosophy-review.md) |
| C-28 | 試行の記録は成績でなく観察の記録である | 立場 | [philosophy.md](philosophy.md) |
| C-29 | 学ぶ人の紙に成功、失敗、正解の語は刷らない | 自動試験 | [test_records.py](../../tests/test_records.py) |
| C-30 | 昔の玩具が再現されたかは、原物が無いので測り切れない | 立場 | [philosophy.md](philosophy.md) |
