# 構成

## 処理の流れ（型紙）

寸法の JSON → `compose.py`（範囲と物理の検査、部品表の検査、配置、印字域と重なりの検査）→ `render.py`（SVG・PDF）→ `marks.py`（PDF から印を読み直す）→ PNG。

検査に落ちると exit 3 で、検査の名前と場所を stderr に出す。検査できない時は exit 4。

## 置き場

| パス | 役割 |
|---|---|
| `src/omochae/__main__.py` | 生成の入口 |
| `src/omochae/compose.py` | 配置と描く前の検査。描画はしない |
| `src/omochae/floors.py` | 雛形によらない検査 |
| `src/omochae/marks.py` | 型紙の印と、刷った後の検査 |
| `src/omochae/render.py` | 描画 |
| `src/omochae/textfit.py` | 字の幅の測定 |
| `src/omochae/templates/slider_fan.py` | 御来迎の雛形。寸法の初期値・範囲・式・部品・部品表 |
| `src/omochae/ingest.py` | NDL から出典の記録を作る |
| `src/api/tools.py` | Claude に渡す道具（今は絵の拡大だけ） |
| `data/sources/` | 出典の記録 |
| `tests/frozen/` | 凍結した基準と場面 |
| `tests/run_floors.py`・`run.sh` | 検査の入口 |
| `docs/features.json` | 機能の状態（`id`・`name`・`status`: todo / doing / done） |
| `docs/process/` | 開発の過程 |

## 雛形を足す時

`templates/` に `DEFAULTS`・`RANGES`・`check_range`・`check_physics`・`parts`・`bom`・`materials`・`TITLES` を持つモジュールを置き、`compose.py` の `TEMPLATES` に足す。
