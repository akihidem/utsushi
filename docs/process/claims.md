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
| C-01 | 検査に落ちる型紙は、PDF と PNG を正しい名前で残さない（rc 3。描く前の検査で落ちる時は何も残らず、刷った後の検査で落ちる時は .rejected.pdf と、同じ名前の .svg が残る） | 自動試験 | [criteria.md](../../tests/frozen/criteria.md)、[__main__.py](../../src/omochae/__main__.py)、[run_floors.py](../../tests/run_floors.py)、[__main__.py](../../src/omochae/__main__.py)、[test_tpl_stick_prop.py](../../tests/test_tpl_stick_prop.py) |
| C-02 | 玩具の頁を開いたらすぐ、たたき台の型紙を作れる（予想の段は本人の決定 11-05、#242 で外した。型紙は玩具ごとに 1 枚、J-032） | 自動試験 | [test_build_now.py](../../tests/test_build_now.py)、[test_one_sheet_page.py](../../tests/test_one_sheet_page.py) |
| C-03 | 人の説明の前に Claude の解釈を呼ばない | 偽の応答の試験 | [test_loop.py](../../tests/test_loop.py) |
| C-04 | 順位と、結果を数えた集計は学ぶ人の画面に出さない（頁の輪の節に出すのは、変えた寸法・理由の文・根拠の記録の番号と、待っている報告の件数と番号。動いた数や止まった数は出さない） | 自動試験 | [test_loop.py](../../tests/test_loop.py)、[test_play_server.py](../../tests/test_play_server.py)、[test_making_log.py](../../tests/test_making_log.py)、[kaizen.py](../../src/web/kaizen.py)、[test_kaizen.py](../../tests/test_kaizen.py) |
| C-05 | 人が確定していない解釈は根拠にできない | 偽の応答の試験 | [loop.py](../../src/omochae/loop.py)、[test_api_review_fixes.py](../../tests/test_api_review_fixes.py) |
| C-06 | 持ち寄りは端末で人が打たないと公開できない | 自動試験 | [test_contrib.py](../../tests/test_contrib.py) |
| C-07 | 下から押す形は、初期の寸法（筒の高さ 90mm・押す部品 70mm）では行程が 20mm 足りなかった。今は検査 F5.stroke が止める | 計算 | [03-mechanism-dimensions.md](research/03-mechanism-dimensions.md)、[criteria.md](../../tests/frozen/criteria.md) |
| C-08 | 台に載せる形は扇が 180° で筒にぶつかる | 計算 | [08-fan-axle.md](research/08-fan-axle.md) |
| C-09 | 虎の紙の頭は重りより桁で軽い | 計算 | [12-tiger.md](research/12-tiger.md) |
| C-10 | 図を貼らず描き直すと PDF が 1.8MB から約 0.1MB になった | 測定 | [J007-redraw-not-paste.md](decisions/J007-redraw-not-paste.md)、[README.md](trials/sheets/README.md) |
| C-11 | 11-02 の 393 分（14:00〜20:33）のうち、作る側の最後の出力から次の文が届くまでの間隔は最長 124 分で、10 分以上の間隔は計 223 分（判断待ちの目安。間隔は本人が考えていた時間とは限らず、待ちの全部が本人の側の原因ではない） | 測定 | [how-it-was-built.md](how-it-was-built.md)、[how-it-was-built.md](how-it-was-built.md)、[how-it-was-built.md](how-it-was-built.md)、[how-it-was-built.md](how-it-was-built.md) |
| C-12 | AI の版の調整が学習を上げた直接の証拠は見つかっていない（検索は少ない） | 文献 | [13-critical-review.md](research/13-critical-review.md) |
| C-13 | 素の GPT で練習は 48% 上がり、試験は 17% 下がった例がある（Bastani ら。トルコの高校 1 校の数学。作業論文の数値で、PNAS の版は未読） | 文献 | [13-critical-review.md](research/13-critical-review.md)、[13-critical-review.md](research/13-critical-review.md) |
| C-14 | 紙の型紙が実物で開くか。11-04 に前の組の御来迎が筒から扇を開いて動いた動画があるが、どの案の紙かは分からない。今の組（goraigo-v14・tora-v7）のたたき台（御来迎は H-C、虎は H-A）は、実物で動いた記録が無い | 測定 | [README.md](trials/README.md)、[README.md](trials/README.md)、[README.md](trials/README.md)、[README.md](trials/sheets/README.md) |
| C-15 | 本物の Claude API で輪が回るか | 未確認 | [J010-loop-back-half.md](decisions/J010-loop-back-half.md) |
| C-16 | 作っているうちに新しい考えが湧く | 未確認 | [J013-core-words.md](decisions/J013-core-words.md) |
| C-17 | 最初に返事をするのは素材と工作（紙）。仕組みについて AI が返すのは人の説明の後で、作っている途中の手順の質問には答える形まで作った（本物の API では未実行。J-013。本人の決定 11-04 で、子どもも AI から直接返事をもらってよい） | 立場 | [J013-core-words.md](decisions/J013-core-words.md)、[test_ai_feedback.py](../../tests/test_ai_feedback.py)、[ask.py](../../src/api/ask.py)、[workshop-design.md](workshop-design.md) |
| C-18 | 学習の効果より学習の再定義を物差しにする | 立場 | [J013-core-words.md](decisions/J013-core-words.md) |
| C-19 | 出発は本人の教育現場（学校の理科の授業や探究の授業）で、本人も使い続ける。その現場の今の生徒では試していない（試行は卒業生の成人 5 人）。理科教育の人、自由研究、館のワークショップ、家庭への広がりは本人の見立てで、まだ試していない | 未確認 | [17-field-and-continuers.md](research/17-field-and-continuers.md)、[decided-and-open.md](decided-and-open.md)、[17-field-and-continuers.md](research/17-field-and-continuers.md)、[README.md](trials/README.md) |
| C-20 | 言葉の口は人の文を書き換えず、隠れた寸法の補いを通さない | 偽の応答の試験 | [test_words.py](../../tests/test_words.py) |
| C-21 | 試した後の紙は対比を先に出し、説明は折って閉じた札に置く | 自動試験 | [test_words.py](../../tests/test_words.py) |
| C-22 | 閉じた札が考える邪魔をしないか | 未確認 | [J013-core-words.md](decisions/J013-core-words.md) |
| C-23 | 手元でトイモデルと遊ぶ体験をしないと科学の面白さに気づけない | 立場 | [philosophy.md](philosophy.md) |
| C-24 | 御来迎の前の組（goraigo-v10）の本体は紙と糸で作る。ただし軸の竹串なども使う（紙一枚は必須の条件でない。本人の決定 11-05 19:44） | 自動試験 | [philosophy.md](philosophy.md)、[slider_fan.py](../../src/omochae/templates/slider_fan.py)、[test_ways.py](../../tests/test_ways.py)、[J032-one-sheet-per-toy.md](decisions/J032-one-sheet-per-toy.md) |
| C-25 | 虎の物差しは頭が揺れるかどうか（本人の判断）。たたき台は首を通す形（H-A、J-032）で、ほかの作り方は作る側の控え | 立場 | [15-philosophy-review.md](research/15-philosophy-review.md)、[J032-one-sheet-per-toy.md](decisions/J032-one-sheet-per-toy.md) |
| C-26 | 日本の小 4 の理科の実験は週 1 回以上が 59.6%（国際平均 31.5%。TIMSS 2023）で、実験経験が無いとは言えない | 文献 | [15-philosophy-review.md](research/15-philosophy-review.md)、[15-philosophy-review.md](research/15-philosophy-review.md) |
| C-27 | 「学習の再定義」は立場の言葉で、実装に対応する物は無い。「AI と子どものタッグ」は、考えを話すと紙を作り直す口まで作ったが（今は必須 2 種だけ）、本物の API では未実行で、子どもでは試していない | 未確認 | [15-philosophy-review.md](research/15-philosophy-review.md)、[think_sheet.py](../../src/web/think_sheet.py)、[README.md](trials/README.md)、[think_sheet.py](../../src/web/think_sheet.py) |
| C-28 | 試行の記録は成績でなく観察の記録である | 立場 | [philosophy.md](philosophy.md) |
| C-29 | 学ぶ人の紙に成功、失敗、正解の語は刷らない（試験が見るのは必須 2 種の紙）。例外は仮説の文の打ち消し「正解ではありません」で、本人の決定（#258）で刷る | 自動試験 | [test_records.py](../../tests/test_records.py)、[test_records.py](../../tests/test_records.py) |
| C-30 | 昔の玩具が再現されたかは、原物が無いので測り切れない | 立場 | [philosophy.md](philosophy.md) |
| C-31 | 批評は Claude のセッションだけで行い、人のレビューは受けない | 立場 | [J018-no-peer-review.md](decisions/J018-no-peer-review.md) |
| C-32 | 型紙をたたき台の 1 枚にする前（J-032）に並べていた御来迎の 5 つの仮説のうち、開く角度で分かれるのは H-E を含む組だけだった（記録として残す。今の組で刷るのは H-A だけ。見比べる紙と計算の道具は #366 で外した） | 計算 | [J019-experiment-sheet.md](decisions/J019-experiment-sheet.md) |
| C-33 | 日本の中 2 で「理科を使うことが含まれる職業につきたい」は 27%、国際平均は 58%（TIMSS 2023） | 文献 | [18-field-evidence.md](research/18-field-evidence.md) |
| C-34 | 「大きな装置にしか真理がない」と生徒が思っている事を測った調査は見つからなかった。本人の印象のまま | 未確認 | [18-field-evidence.md](research/18-field-evidence.md) |
| C-35 | 型紙は正解でなく AI が考えた仮説である前提を、輪を回す担当の全部（仮説・読み・案・言葉・観察）に渡す（本人の言葉 11-05） | 自動試験 | [test_loop_premise.py](../../tests/test_loop_premise.py) |
| C-36 | 話した字は、記録に結んでいても学ぶ人の頁に出さない。頁に出す字は AI が整理した字だけで、話した字は作る側の頁と輪の材料だけが読む（本人の決定 11-06、J-034） | 自動試験 | [test_talk_not_shown.py](../../tests/test_talk_not_shown.py) |
