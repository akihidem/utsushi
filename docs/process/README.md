# 開発の過程の読み方

この作品は、できた物だけでなく、どう調べ、何を比べ、何を捨てて決めたかが repo から読めるように作っている。記録は作業しながら残し、後からまとめて書かない。時刻の証拠は commit の履歴。

| 置き場 | 中身 |
|---|---|
| `research/` | 調べた事のメモ。一次資料か実験の結果と、そこから言える事・言えない事 |
| `decisions/` | 判断の記録 J-nnn。比べた案・捨てた案・決めた理由 |
| `trials/` | 仮説 → 型紙 → 実物の試行 → 記録 → 次の版 の流れの索引。実際に試した物だけを載せる。型紙の全版は `trials/sheets/` |
| `issues/` | 閉じた Issue の記録。1 本ごとに、中身・決まった事と出所・やった事・残った事と誰が決めるか。GitHub の Issue は閉じても、ここから読める |
| `../progress.md` | 作業の 1 行記録 |

**作り方**: 本人は窓口を通して決め、作る側のセッションには触れない。その事実と弱さは [how-it-was-built.md](how-it-was-built.md)。

## 記録の詳しさの基準

日記の羅列でなく、読み手が判断を追える形で詳しく残す（本人の方針）。決めた点では次を書く。

| 書く事 | 無い時 |
|---|---|
| 比べた代案と、捨てた理由 | 比べていないなら、そう書く |
| 失敗と、その原因 | 原因が不明なら不明と書き、確かめ方を書く |
| 測った数値と、測り方 | 測っていないなら推定と書く |
| 誰が決めたか、誰が試したか | 本人か、Claude のセッションかを分ける |

成果物は捨てずに置く。型紙の版は失敗した物も [trials/sheets](trials/sheets/README.md) に、実物の試行は [trials](trials/README.md) に載せる。作業の順を並べるだけの記録は `../progress.md` の 1 行で足りる。個人の記録と秘密は載せない。

調査メモと判断の案は Claude Code のセッションが書いた。人が決めた事と、人の手で試した事は、その旨を明記する。

## 設計の核（本人の言葉）

> 科学の面白さを伝える。自然とのコールアンドレスポンス。おもちゃで遊び続ける。（全文と「玩具」の定義は [philosophy.md](philosophy.md)）

> 目の前のトイモデルは自分の予想が具現化される場で工作することで予測が正しかったかすぐにフィードバックされる。作っているうちに新しいアイディアが湧く。この体験をさせたい。学習の効果よりも学習の再定義、そのあたりに転がっている真理を見つける練習。知識伝達型の教育へAIと子供がタッグを組んで挑む。

> AI は鏡。江戸の絵を映すことはできるが、映すだけでは遊べない。

読み取りと、[批判的レビュー](research/13-critical-review.md)の読み直しは [J-013](decisions/J013-core-words.md)。名前の決め方は [J-014](decisions/J014-name-utsushi.md)。この体験が他の人に起きるかは、まだ試していない（実物の試行は 0 件）。

## 地図

1 行の一言つきの索引。正本は [index.json](index.json) で、主張から根拠へは [claims.md](claims.md) から届く。

<!-- map:start -->
| 順 | 記録 | 一言 | 状態 |
|---|---|---|---|
| 1 | [philosophy](philosophy.md) | 包み紙と紐で自然とやりとりする。記録は成績でなく観察 | 本人の言葉 |
| 2 | [research/01](research/01-primary-source.md) | NDL の図の観察。筒の側面の棒を見つけた | 調査 |
| 3 | [research/02](research/02-render-backends.md) | 描画の方式を 4 つ実験で比べた | 調査 |
| 4 | [J-001](decisions/J001-render-backend.md) | 描画は drawsvg → cairosvg に決めた | 決定 |
| 5 | [research/03](research/03-mechanism-dimensions.md) | 初期の寸法では下から押す行程が 20mm 足りない | 調査 |
| 6 | [J-002](decisions/J002-mechanism-hypotheses.md) | 仕組みを 1 つに決めず複数の仮説として並べる | 決定 |
| 7 | [research/04](research/04-questioned-assumptions.md) | 疑わしい前提 Q1〜Q9。一番は折り目の弾性 | 調査 |
| 8 | [research/05](research/05-three-axes.md) | 3 つの物差しの採点と、鋭くする案の比較 | 調査 |
| 9 | [J-003](decisions/J003-zoom-tool.md) | Claude に絵を拡大する道具を渡す | 作った。組み込みは未定 |
| 10 | [J-004](decisions/J004-parallel-lines.md) | 担当を 2 つに分ける案。取りやめた | 取りやめ |
| 11 | [research/06](research/06-rederive-defaults.md) | 初期値を絵の測定と紙面の制約から出し直した | 調査 |
| 12 | [research/07](research/07-own-scans.md) | 手元の複写を基準に寸法と読みを照合した | 調査 |
| 13 | [research/08](research/08-fan-axle.md) | 台に載せる形は 180° で筒にぶつかると計算 | 調査 |
| 14 | [J-005](decisions/J005-axle-default.md) | 扇の中心の置き方を比べた。中心の軸で開くのを試行で確かめた | 試行で確かめた |
| 15 | [research/09](research/09-contributions-design.md) | 持ち寄りの場の受付と権利の線の設計 | 調査 |
| 16 | [J-006](decisions/J006-contributions-minimum.md) | 持ち寄りは確認つきの受付を先に作る | 決定。外の入口は判断待ち |
| 17 | [research/10](research/10-redraw-colors.md) | 図を描き直すための色と線を調べた | 調査 |
| 18 | [J-007](decisions/J007-redraw-not-paste.md) | 図を貼らず描き直す。PDF が約 0.1MB に | 決定 |
| 19 | [J-008](decisions/J008-own-hypothesis-path.md) | 仮説を自分で立てる道を足した | 決定 |
| 20 | [J-009](decisions/J009-sheet-and-records.md) | 手順の紙と 3 値の記録の入口 | 決定 |
| 21 | [research/11](research/11-naming.md) | 名前の候補の比較と、鏡の論点の取り違え | 調査 |
| 22 | [research/12](research/12-tiger.md) | 虎の仮説。物差しは頭が揺れるか。紙の頭は桁で軽い | 調査 |
| 23 | [J-010](decisions/J010-loop-back-half.md) | 輪の後半と、人が確定する線 | 作った。API 未実行、モデル判断待ち |
| 24 | [J-011](decisions/J011-generate-on-the-spot.md) | その場の生成を本線に。11 分後に置き直した | J-012 で置換 |
| 25 | [J-012](decisions/J012-backstage-content-and-own-hypothesis.md) | 裏で確かめる内容と自分の仮説の口 | J-013 で読み直し |
| 26 | [research/13](research/13-critical-review.md) | 前提への批判。物理と歴史の問いが混ざっていた | 調査 |
| 27 | [J-013](decisions/J013-core-words.md) | 設計の核: 素材が返事をし、考えが湧く | 決定。決める点 2 は 11-04 に本人が変えた（子どもも AI から直接返事） |
| 28 | [J-014](decisions/J014-name-utsushi.md) | 名前を utsushi に。決め方の経緯 | 決定 |
| 29 | [J-015](decisions/J015-ai-readable.md) | AI の読み手に伝わる作り。主張から根拠へ | 決定 |
| 30 | [J-016](decisions/J016-zukan-labels.md) | 図鑑の文の印は 3 分類。文言は検査しない | 決定 |
| 31 | [J-017](decisions/J017-runtime-model.md) | 製品の実行モデルは全部 Opus。比べた結果ではない | 決定 |
| 32 | [J-018](decisions/J018-no-peer-review.md) | 人のレビューは受けず、批評は Claude だけ | 決定 |
| 33 | [J-019](decisions/J019-experiment-sheet.md) | 型紙を実験装置に。角度で分かれるのは H-E を含む組だけ | 決定 |
| 34 | [J-020](decisions/J020-gate-without-trial.md) | 今夜の関門は試行の結果なしで迎える。実物が要る物は 11-04 の試行の後へ | 決定 |
| 35 | [J-021](decisions/J021-contributions-form-students.md) | 持ち寄りの入口は既製のフォーム。生徒の記録と本人の聞き取りを載せる形と、同意・名前を外す扱い | 入口と公開の条件は決定。生徒の分は設計だけで、集めない |
| 36 | [J-022](decisions/J022-video-gallery.md) | 動画を Claude が見るのは観察の補助と型紙の判定だけ。成績にしない再現ギャラリーと有識者の声 | 1〜3 は本人が採った。有識者は仕組みだけ |
| 37 | [J-023](decisions/J023-first-test-later.md) | 本物の API の最初の試験は作り込んでから。下見・キャッシュ・費用の数え方を足した | 決定 |
| 38 | [J-024](decisions/J024-entrance-and-workshop.md) | 使い手の入口は手元のブラウザの画面、作り手の工房は Claude Code の機能 | 決定。ルックブックは A と C を残した（11-04）。画面は人がまだ使っていない |
| 39 | [J-025](decisions/J025-no-ranking.md) | 仮説の順位をやめ、記録は次に試す物の提案の材料だけにする | 決定 |
| 40 | [J-030](decisions/J030-reach-abroad.md) | 届け先はいろんな国の人。絵を先に、字の少ない道を太く。英語の紹介文の案と段 | 本人の方針（11-05）。紹介の文は本人が採った（#318）。段の範囲は本人の採否待ち |
| 41 | [claude-story](claude-story.md) | Claude の使い方の物語。機能の選び分けと、Claude Code のセッションを並べる作り方 | 1・2 節は 11-03 に本人が確認し、後に直しあり。3 節は本人の決定（11-06）: C の下書きで、本人の確認待ち |
| 42 | [research/16](research/16-scan-titles.md) | 複写 2 式の書名を特定し、本人が確認した。歌の読みは本人が決めた | 調査。書名と読みは本人の確認済み |
| 43 | [research/17](research/17-field-and-continuers.md) | 現場の具体と続ける人を本人の言葉からまとめ、6 点の答えをそろえた | 調査。6 点とも本人の答えあり |
| 44 | [research/18](research/18-field-evidence.md) | 現場の印象を補う調査。理科の職業を望む中 2 は日本 27%・国際 58% | 調査 |
| 45 | [research/19](research/19-emil-skills-review.md) | 参照のルックブックの観察と A の再現、Skill 集から拾った物 | 評価。A は作り替えた。人の目はまだ |
| 46 | [research/20](research/20-worksheet-rethink.md) | 学習プリントの問いかけを本人の 4 つの着目で考え直す案 | 案。採るかは本人（U-25） |
| 47 | [research/21](research/21-prior-art-compare.md) | Wandy を含む先行事例と今の実装の比較 | 比較。Wandy の実物は未確認 |
| 48 | [research/22](research/22-origami-papercraft-ai.md) | 折り紙・ペーパークラフトと AI の研究の系譜と取り入れる候補 | 調査。候補を採るかは本人（U-26） |
| 49 | [research/23](research/23-phone-artifact.md) | iPhone で手順を聞き、できた物を上げるアーティファクトの案 | 案。決める点は U-35 |
| 50 | [research/24](research/24-hallmark-impeccable-review.md) | デザインの Skill 2 つを入口の磨きの参考として評価 | 評価。拾った 1〜5 は A′・C・A に入れた |
| 51 | [research/25](research/25-kuzushi-reading.md) | くずし字を読む頁: 先に書き、確かめた読みと並べる | 作った。印の当て方と保存は未決 |
| 52 | [how-it-was-built](how-it-was-built.md) | 本人は窓口を通して決める。待ちと取り違えも | 記録 |
| 53 | [research/14](research/14-judging-criteria.md) | 審査基準の 4 項目で点検。現場と継続利用が欠けている | 判断待ち O-08〜O-11 |
| 54 | [research/15](research/15-philosophy-review.md) | 哲学への批判。言葉は紙と紐、実装は型紙一式。虎は本人が回答 | 残りの 4 点は本人が決めた |
| 55 | [open](open.json) | 今の判断待ちの一覧 | 機械可読 |
| 56 | [decided-and-open](decided-and-open.md) | 決まったことと、まだ決まっていないこと（閉じる条件つき）の 1 枚 | 11-05 の凍結の前の一覧。提出前に数え直す |
| 57 | [spec](spec.md) | 今回の実装が成立する条件の仕様書（哲学・決定・実装から起こした） | 11-05 の凍結に使う。決まっていない点は U-27〜U-31 |
| 58 | [gate-trial](gate-trial.md) | 関門の試行（Red/Green・証拠・書き戻し）の帳面 | 試行中（11-04〜） |
| 59 | [demo-notes](demo-notes.md) | デモ動画の準備の参考と当てはめの案 | 11-06〜07 に使う（U-19） |
| 60 | [api-test-plan](api-test-plan.md) | 本物の API の最初の試験 7 回の手順書 | 本人の承認待ち（U-05） |
| 61 | [contributions-form](contributions-form.md) | 外の入口の Google フォームの表と取り込みの流れ | 本人がフォームを作れば開く（f17） |
| 62 | [claims](claims.md) | 主張ごとの確かさの種類と根拠の表 | 自動で描く |
| 63 | [trials](trials/README.md) | 実物の試行の索引。まだ 0 件 | 0 件 |
| 64 | [trials/sheets](trials/sheets/README.md) | 型紙の全版。失敗した版も残す | 記録 |
| 65 | [template-contract](template-contract.md) | 全部の玩具を並列で作る線の契約。線が持つファイルと雛形の 1 本が持つ名前 | 設計 |
| 66 | [site-requirements](site-requirements.md) | サイトの要件定義。順路 1 つ・皮 2 つ（白の展示・黒のジン）・型紙の窓。本人の指示で実装まで | 実装した（11-05 未明）。本人の採否はカード |
| 67 | [workshop-design](workshop-design.md) | 場の全体デザイン。本線は型紙で作る道で、話す・作る・残すの一周を 1 コマに置く | 案（版 2、11-05 午後）。場はまだ開いていない |
| 68 | [workshop-guide](workshop-guide.md) | 進行者の手引き。時間割と言う事・止まった人への段・場の後の 15 分を A4 両面の 1 枚に | 本人の覚え書き（本人の決定、11-05）。文面は確定しない |
| 69 | [J-029](decisions/J029-trial-video.md) | 作成の過程の動画を記録に結び、札と人の確かめから型紙の版まで回す（本人の指示） | 本人の指示と決定（11-05）。作り物の動画で通した。本人の動画での 1 周はこれから |
| 70 | [J-031](decisions/J031-build-now.md) | 予想の段を無くし、開いたらすぐ作る。他の人の作った物のギャラリーを作る（本人の決定） | 本人の決定（11-05）。作りは #242 の枝で入れた |
| 71 | [research/26](research/26-picture-boxes.md) | 全部の玩具に図を付ける。38 種の写しが無かった原因（取り込みが 1 枚の失敗で止まる）と、83 の箱を目で確かめた記録 | 11-05 直した。人の確認（crop_status）はまだ |
| 72 | [research/27](research/27-analogy-all-toys.md) | 全部の玩具に「たとえと、関連する事柄」。欄の形・出し方・分身 3 本の書き方・守った線 | 11-05 朝 83 種に入れた。文の人の確認はまだ |
| 73 | [research/28](research/28-sheet-qa.md) | 全玩具の型紙 171 本を刷って検めた。刷れない物 0、印や字の欠け 7 種。雛形は直さず報告だけ | 11-05 朝に検めた。直しは型紙エンジンの側 |
| 74 | [J-026](decisions/J026-site-side-loop.md) | 改善の輪はサイト側でも回す。報告（動きと感想）を型紙の改善に回し、次に作る人に直した版を渡す | 本人の方針（11-05 朝）。作った |
| 75 | [research/29](research/29-making-data-to-service.md) | 工作の様子の蓄積を、サービス全体の何にどう回すか。蓄積する物・改善の行き先・段取り・決める点 | 本人の問いへの答え（11-05 朝）。段 0 は作業中 |
| 76 | [research/30](research/30-kazasu-camera-choice.md) | かざして選ぶ（内カメラに原図を重ね、予想を選ぶ）の設計・守る線・重さの見積もり | 本人の案（11-05 朝）。タップの形は #242 で外した。観察 A は残した |
| 77 | [J-027](decisions/J027-making-data.md) | 工作の様子（聞いた事・止まった所・動き・感想）を蓄積してサービス全体の改善に回す。残す物と残さない物、出し方の線 | 本人の決定（11-05 朝）。最初の一切れを作った |
| 78 | [J-028](decisions/J028-open-demo.md) | デモの 2 サイトを合言葉なしで開く。置き場を分け、写真と動画は人が確かめてから出す | 本人の許可（11-05 朝）。開く操作は人の手か、許しが出た時 |
| 79 | [research/31](research/31-observation-depth.md) | 観察の深さを運用の必要から決める。先行例つき。A を土台に、聞く時の 1 枚を次に | 本人の問いへの答え（11-05 朝）。決める点 3 つ |
| 80 | [research/33](research/33-observe-from-picture.md) | 型紙なしで絵だけから作る過程を、机の端の端末のカメラで観察し、再生の知見を得る案 | 案。採否は本人（U-46） |
| 81 | [research/32](research/32-contributor-recognition.md) | 型紙を直した人を示す案（本人の種）。J-025 との切り分けと形の 3 案 | 種の記録（11-05）。形は本人が決める |
| 82 | [research/34](research/34-talk-build-share-loop.md) | 話す・作る・残すの一周とエンジンごとの改善。提出の核。今ある物と無い物 | 本人の言葉（11-05 昼）。音声とエンジンは別の担当で作る |
| 83 | [research/35](research/35-sukeroku-mame-gangu.md) | 浅草の助六の豆玩具の記事を読んだ。小ささの理由・職人の数・紙と貝と風で動くずぼんぼ。職人と玩具店の話を集める手がかり | 記事を読んだだけ（2017 年の記事）。店には確かめていない |
| 84 | [J-033](decisions/J033-assembly-3d.md) | 手順どおりに 3D で組み立て、組めない所を自己検証の結果に残す。本線は紙のまま（本人の考え） | 芯と頁を作る（11-05〜06）。頁の文と置き場は本人の決定（11-06） |
| 85 | [research/36](research/36-road-and-audience.md) | 使う人の道（6 工程）と、相手を全年齢・外国の人に広げる当てはめ。文書の直す案 | 道の設計は本人の決定（11-06）。持ち寄る場の設計と文書の直しは案。頁はまだ変えていない |
| 86 | [J-032](decisions/J032-one-sheet-per-toy.md) | 型紙は玩具 1 つに 1 枚のたたき台。自分の案は話す形、見比べる紙は外す（本人の決定） | 本人の決定（11-05）。J-002・J-019・J-008 を置き換えた。作りは #332 で順に入れる |
| 87 | [J-034](decisions/J034-talk-not-shown.md) | 頁に出す字は AI が整理した字だけ。話した字は作る側だけが読む（本人の決定） | 本人の決定（11-06）。記録の札から話した字の行を外した。整理した字の置き場はまだ |
| 88 | [J-035](decisions/J035-all-pages-english.md) | 全頁を英語で読めるようにする。頁ごとに書かず、出口で訳の表を引く（本人の言葉・窓口の決め 130735 の案 B） | 本人の言葉と窓口の決め（11-07）。訳は作る側の下書き。台本が出す字はまだ日本語 |
<!-- map:end -->

## 事前の検討との関係（正直に書く所）

開発の開始より前に、題材の調査と構想の検討をしたメモが手元にある。

- 提出するコード・データ・記録はこの repo で期間中に作った。
- `research/` の各メモの「事前メモとの関係」の行に、前から知っていた事か、ここで初めて分かった事か、メモと違う結論になった事かを書く。前から知っていた事を、ここでの発見のようには書かない。
