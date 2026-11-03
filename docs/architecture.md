# 構成

## 処理の流れ（型紙）

寸法の JSON → `compose.py`（範囲と物理の検査、部品表の検査、配置、印字域と重なりの検査）→ `render.py`（SVG・PDF）→ `marks.py`（PDF から印を読み直し、貼られた画像が無い事を見る）→ PNG。

検査に落ちると exit 3 で、検査の名前と場所を stderr に出す。検査できない時は exit 4。

## 置き場

| パス | 役割 |
|---|---|
| `src/omochae/hypotheses.py` | 使い手の入口。予想か自分の仮説を受け、仮説を並べ、選んだ仮説の型紙を刷る |
| `data/hypotheses/` | 玩具ごとの仮説（根拠・弱い所・測る事）。順位は持たない |
| `src/omochae/instructions.py` | 手順の紙と試した後の紙 |
| `src/api/words.py` | 言葉の仮説を雛形の寸法に写す口 |
| `src/omochae/records.py` | 試した記録の入口と集計。記録は `data/records/` |
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
| `src/omochae/loop.py` | 輪の後半。人の説明と思いつき、解釈の確定、提案の検査、人の採否、版・順位（作り手用）・新しい仮説 |
| `src/omochae/metrics.py` | 変更の向きを数え直す式と、変えてよい寸法 |
| `src/api/agent.py`・`src/api/loop_agents.py`・`src/api/config.py` | 上限つきの Claude の輪（キャッシュ、送る物の下見 `--dry-run`）、頼みと道具、モデルの設定 |
| `src/api/generate.py` | 裏の制作の 1 段。図・歌・記録から仮説と寸法の案を作る |
| `src/api/budget.py` | API の消費の見積もりと上限 |
| `src/api/mcp_server.py`・`.mcp.json` | 工房の道具を Claude Code から呼ぶ MCP サーバ（API の輪と同じ道具） |
| `.claude/skills/backstage`・`.claude/agents/second-eye.md`・`.claude/hooks/ledger-check.sh` | 作り手の工房: 裏の制作の手順、別の目、台帳の検査のフック |
| `data/records/`・`data/loop/` | 試行の記録と、解釈・提案・版・順位の記録（個人の記録なので git に入れない） |
| `data/sources/` | 出典の記録 |
| `tests/frozen/` | 凍結した基準と場面 |
| `tests/run_floors.py`・`run.sh` | 検査の入口 |
| `docs/features.json` | 機能の状態（`id`・`name`・`status`・`evidence`・`unverified`）。todo = 未着手、doing = 動くが `unverified` が残る、done = 残りが無い |
| `docs/process/` | 開発の過程。`index.json`（地図の正本）、`claims.json`（主張と根拠の正本） |
| `src/omochae/ledger.py` | 台帳の検査と、地図と主張の表の描画 |

## 雛形を足す時

`templates/` に `DEFAULTS`・`RANGES`・`check_range`・`check_physics`・`parts`・`bom`・`materials`・`title`・`place`・`steps`・`measures`・`diagram` を持つモジュールを置き、`compose.py` の `TEMPLATES` に足す。
