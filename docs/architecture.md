# 構成

## 処理の流れ（型紙）

寸法の JSON → `compose.py`（範囲と物理の検査、部品表の検査、配置、印字域と重なりの検査）→ `render.py`（SVG・PDF）→ `marks.py`（PDF から印を読み直し、貼られた画像が無い事を見る）→ PNG。

検査に落ちると exit 3 で、検査の名前と場所を stderr に出す。検査できない時は exit 4。

## 置き場

| パス | 役割 |
|---|---|
| `src/omochae/hypotheses.py` | 使い手の入口。玩具ごとのたたき台の仮説（記録の欄 sheet、読む所は sheet_of。J-032）と型紙を刷る。必須 2 種の今の組はたたき台だけを刷る。自分の仮説も受ける（話す形への直しは後） |
| `data/hypotheses/` | 玩具ごとの仮説（根拠・弱い所・測る事）。順位は持たない |
| `src/omochae/instructions.py` | 学ぶ人の紙（手順・試した後・見比べる・型紙なし）と先生の見る紙。測る欄は持たず、問いは本人の 4 つの着目に合わせる（U-25） |
| `src/api/words.py` | 言葉の仮説を雛形の寸法に写す口 |
| `src/omochae/records.py` | 試した記録の入口と集計。記録は `data/records/` |
| `src/omochae/ways.py` | 仮説ごとの作り方の印（紙一枚・折るだけ・当時の材料）を部品表と用意する物から出す。どの印も上下を表さない。紙一枚は必須の条件でない（J-032 の 1 枚は型紙の数） |
| `src/omochae/store.py` | 記録・輪・自分の仮説の置き場の読み書き。一時ファイル → 置き換え、読めない 1 件を飛ばす読み、プロセスをまたぐ排他（置き場の `.lock`） |
| `src/omochae/__main__.py` | 型紙を 1 枚作る共通の流れと、開発用の入口 |
| `src/omochae/compose.py` | 配置と描く前の検査。描画はしない |
| `src/omochae/floors.py` | 雛形によらない検査 |
| `src/omochae/marks.py` | 型紙の印と、刷った後の検査 |
| `src/omochae/render.py` | 描画 |
| `src/omochae/textfit.py` | 字の幅の測定 |
| `src/omochae/model.py` | 検査と描画が共に使う型（部品・字の箱・検査の失敗 `Failure`） |
| `src/omochae/page.py` | 頁の大きさと印字域（A4・B4 を同じ計算で扱う） |
| `src/omochae/foldsim.py` | 折りの部品を Origami Simulator が読める SVG に書き出す。作り手用で、学ぶ人の画面には道を作らない |
| `src/omochae/gallery.py` | 再現ギャラリーの静的な頁を書き出す。記録の順に並べ、順位を付けない |
| `src/omochae/templates/` のほかの雛形 | 試作の玩具の雛形（`balance_toy`・`den_den`・`spin_toy`・`stand_figure`・`stick_prop`・`string_pull`・`wheel_cart`）。図鑑から入る。足し方は下の「雛形を足す時」 |
| `src/omochae/templates/slider_fan.py` | 御来迎の雛形。寸法の初期値・範囲・式・部品・部品表 |
| `src/omochae/fan_model.py` | 扇の開きの幾何（開く角度の上限・口の角との干渉・糸の長さ） |
| `src/omochae/pivot_model.py` | 首振りの重心・傾き・周期の式 |
| `src/omochae/templates/pivot_counterweight.py` | 虎の雛形 |
| `src/omochae/ingest.py` | NDL から出典の記録と原図の写し（切り出し）を作る。`images` は足りない写しだけを取る（起動の台本が毎回回す） |
| `src/api/tools.py` | Claude に渡す道具（絵の拡大、公開済みの持ち寄り） |
| `src/omochae/contrib.py` | 持ち寄りの受付・確認・公開・取り下げ |
| `src/omochae/media_review.py` | 上げた写真と動画の、出す前の人の確認（物だけ／人や声が入る）。結果は写真の置き場に持つ。命令は端末で人が番号を打った時だけ進む（#314） |
| `src/web/contrib_server.py` | 持ち寄りの手元の画面 |
| `src/web/play_server.py` | 使い手の手元の画面の道と門（J-024）。皮はサーバごとに 1 つ（--look。皮ごとに 1 サイト）、刷った紙の口（PDF・PNG・SVG、インライン。試した後の紙は記録の後だけ）、合言葉の門 |
| `src/web/failure_log.py` | 作る側が読む失敗の記録（stderr）。道・役・型・トレースバックを出し、学ぶ人の書いた文と合言葉は出さない |
| `src/web/demo_check.py` | デモのリンクの先が開くかを見る（`run-demo.sh` から呼ぶ。合言葉付きのリンク → Cookie で頁まで。合言葉なしの形は入口が開くか）。port が空いているかも見る |
| `src/web/skin.py` | 骨と皮。皮は CSS の変数の表（白の展示 tenji・黒のジン zine）、骨は頭の帯と共通の部品。皮はサイトごとに 1 つで、頁の中に切り替えは無い（docs/process/site-requirements.md の 15） |
| `src/web/toy.py` | 玩具の頁。開いたらすぐ仮説の札（#242。1 枚のたたき台にする直しは J-032 の後の直し）→ 型紙の窓（PNG・SVG を画面に出し、押すと拡大。版を並べる）→ 作る → 記録 → 試した後の紙 → 人の説明 → AI → 次の版 → 戻る。たとえと関連する事柄の節（analogy_section、予想の後） |
| `src/web/en.py` | 英語の頁（J-030 の段 1）。入口と玩具ごとの頁。文は data/en の下。紙は日本語のままで、刷る口は日本語の頁と同じ `print_latest`。聞く口と記録の口は置かない |
| `src/web/hokusai.py` | 北斎漫画の節（本人の決定 11-05）。絵の取り込みは `src/omochae/hokusai.py`、権利と切り出しの枠は動画と同じ `src/demo/figures.json`・`src/demo/scene4_sources.json`。玩具の頁と一覧には置かない |
| `src/web/kaizen.py` | 改善の輪（J-026）。玩具の頁の節（どの報告がどの版を変えたか・次の版を待つ報告）と、サイト側の一覧 /loop。台帳は omochae.loop の版の記録をそのまま読む。玩具ごとの様子の頁 /loop/<印>（作る側の集計） |
| `src/web/tsukuru.py` | 作りながら見る（観察 A の試作）。机の端に立てた端末に、今の手順の文と手順の紙の絵・返事・小さな鏡。手順の進みだけを残す。映像は端末の中だけ |
| `src/omochae/making_log.py` | 工作の様子の蓄積（J-027）。聞く口の質問を、名前と連絡先の形を落として残す。玩具ごとの集計（聞かれた事・止まった所・感想・版ごとの動きの札）を作る側に渡す。手順の進み（何番で止まったか・できたか）も残す |
| `src/omochae/engine_bundle.py` | エンジンへ渡す束（Issue 278、U-55 の段取り 5）。試した記録・人の説明・手順の進み・聞く口の質問を読み、雛形の id と刷った組ごとに束ねた JSON 1 つを書く（件数と幅と文だけ。割合・平均・順位は入れない）。出す時に連絡先の形の床をもう一度当て、当たった文は入れずに数だけ入れる。名前・その場限りの印の値・メモ・秒は入れない。書く先は git の外か `out/` の下だけ。束の上の段に、群に出てくる雛形の今の刷った組も書く（Issue 309。前の組の紙の記録から起きた案を、エンジンの側で読む人が見分けるため）。束から直しの案を起こす所・人の採否・次の版は、型紙エンジン（paper-to-toy）の側が持つ |
| `src/web/failure_log.py` | 作る側が読む失敗の記録（stderr）。道・役・型・トレースバックを出し、学ぶ人の書いた文と合言葉は出さない |
| `src/web/toys.py` | 全部の玩具から 1 つ選ぶ頁（必須 2 を大きく、試作を札で） |
| `src/web/about.py` | 序（コンセプト・『江都二色』の解説・動機）。文面は本人の言葉の引用と書誌の値だけ。採否は本人 |
| `src/web/looks.py` | 入口。A′ 日本画展の展示と C 縦読みのジン（どちらのサイトかは --look）。全部の玩具の一覧の節を持つ。大判（A）は 11-05 朝に外した |
| `src/web/kuzushi.py` | くずし字を読む頁（f14）。先に自分の読みを書き、確かめた読みと並べる。書いた読みは保存しない |
| `src/web/plain_words.py` | 小学生・中学生の目で頁と紙の文を数える命令（#317）。語の表を 1 か所に置く。頁の字は変えない。結果は `out/` |
| `src/web/zukan.py` | 図鑑の頁（印つきの文、F6.label） |
| `src/web/techo.py` | 工作の手帖の頁を書き出す。中身は repo のコードから作り、型紙と手帖が食い違わないようにする |
| `src/web/demo_samples.py` | デモ用の見本（上げた物・声・職人の言葉）。本物の記録と混ぜず、見本の札を付ける |
| `src/api/observe.py` | 上げた動画を Claude が見る観察の補助。見えた事と見えなかった事だけを返し、成績にしない |
| `src/web/techo_site.py` | 手帖の頁（聞く・上げる・フィードバック）と、上げた物と職人の言葉の頁 |
| `src/omochae/loop.py` | 輪の後半。人の説明と思いつき、解釈の確定、提案の検査、人の採否、版・新しい仮説。画面の「次の版を作る」は 1 操作にまとめ、床と刷るのを先に済ませて、通った時だけ書く。紙の無い版は窓の釦で刷り直す。順位は持たない（J-025） |
| `src/omochae/metrics.py` | 変更の向きを数え直す式と、変えてよい寸法 |
| `src/api/agent.py`・`src/api/loop_agents.py`・`src/api/config.py` | 上限つきの Claude の輪（キャッシュ、送る物の下見 `--dry-run`）、頼みと道具、モデルの設定と、画面から呼ぶ役の時間切れ |
| `src/api/generate.py` | 裏の制作の 1 段。図・歌・記録から仮説と寸法の案を作る |
| `src/api/budget.py` | API の消費の見積もりと上限（日割りは、表に無い日は既定の額で続く。累計の停止線はどの日にも効く） |
| `src/api/mcp_server.py`・`.mcp.json` | 工房の道具を Claude Code から呼ぶ MCP サーバ（API の輪と同じ道具） |
| `.claude/skills/backstage`・`.claude/agents/second-eye.md`・`.claude/hooks/ledger-check.sh` | 作り手の工房: 裏の制作の手順、別の目、台帳の検査のフック |
| `data/records/`・`data/loop/` | 試行の記録と、解釈・提案・版の記録（個人の記録なので git に入れない） |
| `data/sources/` | 出典の記録 |
| `tests/frozen/` | 凍結した基準と場面。`manifest.json` は照合の表（場面ごとの sha256・期待の rc と床、基準の文の sha256、在るはずの試験の名前）。床の入口が回す前に照らし、合わなければ rc 4 でファイルを名指しする |
| `tests/test_floor_pin.py`・`tests/floor_pin.json` | 凍結の床の見張り。必須の 2 種の今の版（goraigo-v10・tora-v3）のたたき台 H-A の紙と先生の見る紙の 9 枚を刷る SVG の指紋を控えと比べる（J-032 で 31 枚から直した。外した 22 枚は控えの removed に残す）。控えは書き換えず、次の版は足す（U-43） |
| `tests/run_floors.py`・`run.sh` | 検査の入口 |
| `docs/features.json` | 機能の状態（`id`・`name`・`status`・`evidence`・`unverified`）。todo = 未着手、doing = 動くが `unverified` が残る、done = 残りが無い |
| `docs/process/` | 開発の過程。`index.json`（地図の正本）、`claims.json`（主張と根拠の正本） |
| `src/omochae/ledger.py` | 台帳の検査と、地図と主張の表の描画 |
| `src/omochae/gate_evidence.py` | 関門の証拠のファイルを、頭に命令と commit をつけて書き出す命令と、頭の検査 |
| `src/demo/` | デモ動画の 7 場面をコードだけで描いて録る。`prepare.py` が前の日の下ごしらえ（道具を名前で確かめる・江戸の絵を取り寄せて控えを残す・網を切る）。`build.py` が本番の入口（道具を確かめる → 試験を数える → 7 場面を書き出す（`--offline` で網を切る・`--run --only` で場面ごとに作り直す）→ つなぐ → build.json に commit と長さを残す）。場面は `flip.py`（1 北斎漫画の槍の型、書き出しと色・字の共有もここ）・`scene2.py`（江都二色）・`scene3.py`（予想が先 → 仮説、使い手の画面を手元で動かして撮る）・`scene4.py`（江戸の仕組みの絵から型紙へ）・`scene5.py`（11-04 の試行。写真は U-24 の表で許された物だけ）・`scene6.py`（所見 → T-0001 → 版の差 → 工作の手帖）・`scene7.py`（締めとクレジット）。`assemble.py` がつなぎ 3 分の床を見る。画像と動画は repo に入れない |

## 雛形を足す時

`src/omochae/templates/` にモジュールを 1 本置くだけでよい。`compose.py` の `_discover()` が、名前が `_` で始まらないモジュールを全部読んで `TEMPLATES` に載せる（必須の 2 種を先頭、残りは名前の順）。表を手で書き足さない。1 本が持つ物（`ID`・`HYP_KEY`・`DEFAULTS`・`RANGES`・`check_range`・`check_physics`・`parts`・`bom` など）と、仮説の記録・試験の置き方は [docs/process/template-contract.md](process/template-contract.md) の「雛形の 1 本が持つ物」にある。

今の雛形は、必須の `slider_fan`・`pivot_counterweight` と、試作の `balance_toy`・`den_den`・`spin_toy`・`stand_figure`・`stick_prop`・`string_pull`・`wheel_cart`。数は README の数の節にある。試作の雛形の玩具は図鑑から入り、入口の主役には出ない。雛形を足したら、ここに名前を足す（`python -m omochae.ledger check` が見る）。
