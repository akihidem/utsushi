# 構成

## 処理の流れ（型紙）

寸法の JSON → `compose.py`（範囲と物理の検査、部品表の検査、配置、印字域と重なりの検査）→ `render.py`（SVG・PDF）→ `marks.py`（PDF から印を読み直し、貼られた画像が無い事を見る）→ PNG。

検査に落ちると exit 3 で、検査の名前と場所を stderr に出す。検査できない時は exit 4。

## 置き場

| パス | 役割 |
|---|---|
| `src/omochae/hypotheses.py` | 使い手の入口。予想か自分の仮説を受け、仮説を並べ、選んだ仮説の型紙を刷る |
| `data/hypotheses/` | 玩具ごとの仮説（根拠・弱い所・測る事）。順位は持たない |
| `src/omochae/instructions.py` | 学ぶ人の紙（手順・試した後・見比べる・型紙なし）と先生の見る紙。測る欄は持たず、問いは本人の 4 つの着目に合わせる（U-25） |
| `src/api/words.py` | 言葉の仮説を雛形の寸法に写す口 |
| `src/omochae/records.py` | 試した記録の入口と集計。記録は `data/records/` |
| `src/omochae/store.py` | 記録・輪・予想の置き場の読み書き。一時ファイル → 置き換え、読めない 1 件を飛ばす読み、プロセスをまたぐ排他（置き場の `.lock`） |
| `src/omochae/__main__.py` | 型紙を 1 枚作る共通の流れと、開発用の入口 |
| `src/omochae/compose.py` | 配置と描く前の検査。描画はしない |
| `src/omochae/floors.py` | 雛形によらない検査 |
| `src/omochae/marks.py` | 型紙の印と、刷った後の検査 |
| `src/omochae/render.py` | 描画 |
| `src/omochae/textfit.py` | 字の幅の測定 |
| `src/omochae/templates/slider_fan.py` | 御来迎の雛形。寸法の初期値・範囲・式・部品・部品表 |
| `src/omochae/fan_model.py` | 扇の開きの幾何（開く角度の上限・口の角との干渉・糸の長さ） |
| `src/omochae/pivot_model.py` | 首振りの重心・傾き・周期の式 |
| `src/omochae/templates/pivot_counterweight.py` | 虎の雛形 |
| `src/omochae/ingest.py` | NDL から出典の記録を作る |
| `src/api/tools.py` | Claude に渡す道具（絵の拡大、公開済みの持ち寄り） |
| `src/omochae/contrib.py` | 持ち寄りの受付・確認・公開・取り下げ |
| `src/web/contrib_server.py` | 持ち寄りの手元の画面 |
| `src/web/play_server.py` | 使い手の手元の画面の道と門（J-024）。皮の cookie、刷った紙の口（PDF・PNG・SVG。試した後の紙は記録の後だけ）、合言葉の門 |
| `src/web/demo_check.py` | デモのリンクの先が開くかを見る（`run-demo.sh` から呼ぶ。合言葉付きのリンク → Cookie で頁まで）。port が空いているかも見る |
| `src/web/skin.py` | 骨と皮。皮は CSS の変数の表（白の展示 tenji・黒のジン zine）、骨は頭の帯と共通の部品。入口で選んだ皮が cookie で全部の頁に続く（docs/process/site-requirements.md） |
| `src/web/toy.py` | 玩具の頁。記録を読む → 予想 → 仮説の札 → 型紙の窓（PNG・SVG を画面に出し、押すと拡大。版を並べる）→ 作る → 記録 → 試した後の紙 → 人の説明 → AI → 次の版 → 戻る |
| `src/web/toys.py` | 全部の玩具から 1 つ選ぶ頁（必須 2 を大きく、試作を札で） |
| `src/web/about.py` | 序（コンセプト・『江都二色』の解説・動機）。文面は本人の言葉の引用と書誌の値だけ。採否は本人 |
| `src/web/looks.py` | 入口。A′ 日本画展の展示（既定）と C 縦読みのジン。全部の玩具の一覧の節を持つ。A 大判写真集はルックブックの再現として /look/taiban に残す（J-024） |
| `src/web/kuzushi.py` | くずし字を読む頁（f14）。先に自分の読みを書き、確かめた読みと並べる。書いた読みは保存しない |
| `src/web/zukan.py` | 図鑑の頁（印つきの文、F6.label） |
| `src/web/techo_site.py` | 手帖の頁（聞く・上げる・フィードバック）と、上げた物と職人の言葉の頁 |
| `src/omochae/loop.py` | 輪の後半。人の説明と思いつき、解釈の確定、提案の検査、人の採否、版・新しい仮説。順位は持たない（J-025） |
| `src/omochae/metrics.py` | 変更の向きを数え直す式と、変えてよい寸法 |
| `src/api/agent.py`・`src/api/loop_agents.py`・`src/api/config.py` | 上限つきの Claude の輪（キャッシュ、送る物の下見 `--dry-run`）、頼みと道具、モデルの設定と、画面から呼ぶ役の時間切れ |
| `src/api/generate.py` | 裏の制作の 1 段。図・歌・記録から仮説と寸法の案を作る |
| `src/api/budget.py` | API の消費の見積もりと上限（日割りは、表に無い日は既定の額で続く。累計の停止線はどの日にも効く） |
| `src/api/mcp_server.py`・`.mcp.json` | 工房の道具を Claude Code から呼ぶ MCP サーバ（API の輪と同じ道具） |
| `.claude/skills/backstage`・`.claude/agents/second-eye.md`・`.claude/hooks/ledger-check.sh` | 作り手の工房: 裏の制作の手順、別の目、台帳の検査のフック |
| `data/records/`・`data/loop/` | 試行の記録と、解釈・提案・版の記録（個人の記録なので git に入れない） |
| `data/sources/` | 出典の記録 |
| `tests/frozen/` | 凍結した基準と場面。`manifest.json` は照合の表（場面ごとの sha256・期待の rc と床、基準の文の sha256、在るはずの試験の名前）。床の入口が回す前に照らし、合わなければ rc 4 でファイルを名指しする |
| `tests/test_floor_pin.py`・`tests/floor_pin.json` | 凍結の床の見張り。必須の 2 種の今の版（goraigo-v10・tora-v3）の紙 31 枚を刷る SVG の指紋を控えと比べる。控えは書き換えず、次の版は足す（U-43） |
| `tests/run_floors.py`・`run.sh` | 検査の入口 |
| `docs/features.json` | 機能の状態（`id`・`name`・`status`・`evidence`・`unverified`）。todo = 未着手、doing = 動くが `unverified` が残る、done = 残りが無い |
| `docs/process/` | 開発の過程。`index.json`（地図の正本）、`claims.json`（主張と根拠の正本） |
| `src/omochae/ledger.py` | 台帳の検査と、地図と主張の表の描画 |
| `src/demo/` | デモ動画の 7 場面をコードだけで描いて録る。`prepare.py` が前の日の下ごしらえ（道具を名前で確かめる・江戸の絵を取り寄せて控えを残す・網を切る）。`build.py` が本番の入口（道具を確かめる → 試験を数える → 7 場面を書き出す（`--offline` で網を切る・`--run --only` で場面ごとに作り直す）→ つなぐ → build.json に commit と長さを残す）。場面は `flip.py`（1 北斎漫画の槍の型、書き出しと色・字の共有もここ）・`scene2.py`（江都二色）・`scene3.py`（予想が先 → 仮説、使い手の画面を手元で動かして撮る）・`scene4.py`（江戸の仕組みの絵から型紙へ）・`scene5.py`（11-04 の試行。写真は U-24 の表で許された物だけ）・`scene6.py`（所見 → T-0001 → 版の差 → 工作の手帖）・`scene7.py`（締めとクレジット）。`assemble.py` がつなぎ 3 分の床を見る。画像と動画は repo に入れない |

## 雛形を足す時

`templates/` に `DEFAULTS`・`RANGES`・`check_range`・`check_physics`・`parts`・`bom`・`materials`・`title`・`place`・`steps`・`measures`・`diagram` を持つモジュールを置き、`compose.py` の `TEMPLATES` に足す。
