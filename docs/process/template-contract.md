# 雛形の線の契約（全部の玩具を並列で作る、11-04）

本人の指示（11-04）: 「なるべく並列ですべて作ろう」。『江都二色』のほかの玩具の型紙も、なるべく並列に全部作る。凍結（11-05）の床は、必須の 2 種（御来迎・張子の首振り虎）の完成で、これを崩さない。

この文書は、並列の線（1 線 = 1 枝 = 1 作業ツリー = 1 担当）に渡す凍結の契約です。対象の一覧は `data/inventory/edo-nishiki.json` の `lane` の欄です。

## 線と対象

| 線 | 雛形（templates/ の 1 本） | 対象（棚卸しの family） | 形の考え |
|---|---|---|---|
| figure | `stand_figure` | static（人形・張子・ままごと道具・建物） | 箱形か筒形の胴に、原図から描き直した絵。台で立つ |
| prop | `stick_prop` | wear（団扇・羽子板・面・刀・幟・首人形） | 平らな形を棒に貼る。手で持って振る・かざす |
| string | `string_pull` | pull_string（凧・のぼり猿・米搗き・木偶の相撲） | 糸か棒を引くと動く。凧は糸目と骨の位置 |
| spin | `spin_toy` | spin（風車・独楽・手車） | 回る芯（つまようじ・竹ひご）と羽か円盤 |
| drum | `den_den` | sound（でんでん太鼓・振り鼓） | 柄を回すと玉が当たる。紙の太鼓の胴と皮 |
| cart | `wheel_cart` と `balance_toy` | roll・pivot_counterweight・rock_upright（鼠車・俵・釣り合い人形・起き上がり） | 車輪の軸と台、釣り合いの支点と重り |
| later | 作らない（理由を一覧に残す） | 紙での実現の見込みが低い物、からくりの読みが割れている物、重ねて数えた物 | — |

## 線が持つファイル（これ以外は書き換えない）

- `src/omochae/templates/<雛形>.py`
- `data/hypotheses/<玩具の印>.json`（その線の玩具だけ）
- `data/sources/<玩具の印>.json`（`python -m omochae.ingest` が、仮説の記録を置いた玩具の分だけ作る。手で書かない）
- `tests/test_tpl_<雛形>.py`

共有のファイル（compose・metrics・play_server・looks・zukan・ingest・棚卸し）を直したくなったら、直さずに返事に書く。統合の担当がまとめて直す。

## 雛形の 1 本が持つ物

`tests/test_tpl_registry.py` が全部の雛形に求める名前です。形は `pivot_counterweight.py` に倣う。

- `ID`、`SHEET_SET`（`<雛形>-v1`）、`DEFAULTS`、`RANGES`
- `HYP_KEY`: 仮説を分ける寸法の名前。DEFAULTS に既定の値を置く
- `ALLOWED`: 次の版で変えてよい寸法。RANGES にある物だけ
- `metrics(p)`: 台帳の式（F7）。数を返す
- `RESULTS`: 人が見た事の言葉（2〜3 個）
- `title`、`spec`、`check_range`、`check_physics`: 床。落ちる時は Failure の一覧を返す
- `parts`、`place`、`bom`、`materials`、`steps`、`measures`、`diagram`
- 無くてもよい物: `PARAM_NAMES`（画面での呼び名）、`RECORD_EXTRA`（記録の足しの欄）

## 玩具ごとの仮説の記録

- `"stage": "試作"`、`"template": "<ID>"` を置く。入口の主役には出ず、図鑑から入る
- `written_by` は「Claude Code のセッションが案を書いた。人の確認はまだ」
- 仮説は 2〜3 個。HYP_KEY の値で分ける。仕組みを事実として書かない。絵で見た事は「観察」、そこからの読みは「推測」と分ける
- 名前は棚卸しの見立てで、人の確認はまだ。翻刻の欄（transcription）は空のまま（読みは本人が確かめる、U-01）
- 書く欄は今の 2 種の記録に倣う（`questions`・`hypotheses` の `evidence`・`against`・`to_measure`）

## 線の完成の定義

- その線の全部の玩具・全部の仮説の版 1 が、本物の道（`hypotheses.print_sheet`）で床を通って刷れる。`tests/test_tpl_<雛形>.py` が一時の置き場で確かめる
- 床に落ちる値を 1 つ以上入れ、落ちる事を試験で見る
- `./run.sh` が全部期待どおり。必須の 2 種の試験は 1 本も変えない
- API の鍵は使わない
- commit は題が日本語で、本文に「なぜ」の行と `Co-Authored-By` の行を置く。push はしない（統合の担当が PR で入れる）

## 統合

統合の担当（hack-main）が、線ごとに PR を出して取り込む。取り込むのは、`./run.sh` と push の門と、まっさらな clone での試験が全部通る線だけ。

凍結の後に仕上がった線も、必須の 2 種の道と試験に触れていない時だけ取り込む。
