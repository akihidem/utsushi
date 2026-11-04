# 本物の Claude API の最初の試験（7 回）の手順書

- 対象: utsushi（hackathon-utsushikagami）。U-05 の「試験の手順書」（J-023（docs/process/decisions/J023-first-test-later.md） の「まだ作り込む物」）
- 状態: 案。本人が承認するまで本物は 0 回のまま。モデルは全部 Opus 5.5（J-017）
- この手順書を書いた時に確かめた事: 下の `--dry-run` と下見の python は、手元の別の置き場（`OMOCHAE_DATA` を作業用の場所に向けた）で動かし、通信なしで止まる事を見た。本物の 7 本は動かしていない

## 目的

本物の API を 7 回だけ呼び、5 つの役（generate / words / interpret / propose / ask）が、決定的な床（F5・F7・F8・F9）と「順位を付けない」「仮説を漏らさない」の線を守って結果を返すか、1 回いくらかかるかを実測する。

## なぜか

- 輪の後半も仮説の口も、偽の応答と偽の送り先でしか試していない（J-010、`tests/test_agent_sdk.py`）。図の読みや解釈の質、1 回の費用は本物でしか分からない（J-017 の「まだ分からない事」）
- U-12（拡大の道具を生成に組み込むか）は「本物で道具あり・なしを少数回比べる」が閉じる条件で、U-05 の後に置かれている

## どうしたらいいか（代替案と推し）

| 案 | 中身 | 見立て |
|---|---|---|
| **A（推し）** | 安い役から高い役へ 7 回を 1 日で順に。1 回ごとに床と線を見て、1 つでも落ちたらその日は止める | 失う額が小さい順に確かめられる。予算は下の通り日割りの 1/3 以下 |
| B | generate だけを 7 回 | 費用の見積もりは厚くなるが、interpret・propose・ask が本物で 0 回のまま |
| C | 本物を呼ばず、Claude Code の Skill で作った案を `import-draft` で入れる（research/14 の案 b） | 鍵が要らない。ただし API の口と費用の実測にはならない |

## ゴールの要件

1. 7 回（6・7 回目は下の条件つき）を回し、回ごとに「通った床・落ちた床・費用・止まった理由」が 1 行ずつ残る
2. 案は全部 `pending_human` のまま残り、人が採るまで一覧に入らない（F9.human）
3. 費用の合計が下の上限の中に収まり、`out/api-usage.jsonl` の行と Console の数が並べて書かれる
4. 結果を docs に要約し、U-05 を閉じる。U-12 は比べた結果か「比べられなかった理由」を書く

## 共通の準備

- 置き場は既定のまま使う（`OMOCHAE_DATA` は設定しない）。案と下見は `data/loop/`、費用の行は `out/api-usage.jsonl`。どちらも `.gitignore` に入っていて git に載らない
- 毎回の順: ① `--dry-run`（または下見の python）で送る中身を書き出す → ② 本人が `data/loop/preview-<役>.json` を見る → ③ 本物
- 呼ぶ前の費用の数: `PYTHONPATH=src .venv/bin/python -c "from api import budget; print(budget.spent())"`（今日・累計。通信なし）
- 以下のコマンドは repo の根で、`PYTHONPATH=src .venv/bin/python` を `PY` と略す

## 7 回の中身と順

| 回 | 役 | 入力（本物か用意か） | 下見 → 本物のコマンド |
|---|---|---|---|
| 1 | ask | 御来迎 `NDL-1187053-R0000005-L` の H-A の紙。用意した手順の質問「はさみはどこから切りますか」（言葉の表にも仕組みの語にも当たらないので Claude に届く） | 下見: `PY -c "from api import ask; c,h=ask.sheet_context('NDL-1187053-R0000005-L','H-A'); print(ask.SYSTEM); print(c)"` → 本物: `PY -c "from api import ask; print(ask.answer('NDL-1187053-R0000005-L','H-A','はさみはどこから切りますか'))"` |
| 2 | interpret | 本物の記録 R-0001（11-04 の試行、H-A）と本人の説明 `data/loop/explanation-R-0001.json` | 下見: `PY -c "from api import agent, loop_agents; loop_agents.draft_interpretation('R-0001', client=agent.PreviewClient())"`（`Preview` の例外で止まれば成功）→ 本物: `PY -m omochae.loop interpret R-0001` |
| — | 人 | 2 の案を本人が読んで確定する（API は呼ばない） | `PY -m omochae.loop confirm R-0001 --by 本人の名前`（書き直す時は `--text`） |
| 3 | propose | R-0001 と、本人が確定した解釈 | 下見: `PY -c "import json; from api import agent, loop_agents; s=json.load(open('data/sources/NDL-1187053-R0000005-L.json')); loop_agents.draft_proposal('R-0001', s, client=agent.PreviewClient())"` → 本物: `PY -m omochae.loop propose R-0001` |
| 4 | words | 用意した言葉の仮説（本人か大人が打つ）。例「筒の中の板を押し上げると扇が開く」、名前「押し上げ」、図のどこ「左下の筒」 | `PY -m omochae.hypotheses words "筒の中の板を押し上げると扇が開く" --name 押し上げ --evidence 左下の筒 --by 本人の名前 --dry-run` → 同じ文で `--dry-run` を外す |
| 5 | generate（拡大あり） | 御来迎の図と歌。**本人の本物の予想が先に要る**（U-08。無いと F9.prediction で止まり、呼ばない） | `PY -m omochae.hypotheses predict "本人の予想"` → `PY -m omochae.hypotheses generate --dry-run` → `PY -m omochae.hypotheses generate` |
| 6 | generate（拡大なし・U-12） | 5 と同じ図・歌・予想 | 切り替えを足した（11-04、`hypotheses generate --no-zoom`、`tests/test_generate_zoom_switch.py`）。5 と同じ入力で `--no-zoom` を付けて流す |
| 7 | generate（予備） | 5 か 6 が床で落ちた時の 1 回だけのやり直し。使わなければ虎 `NDL-1187053-R0000014-R`（本人の予想が要る）で 1 回 | `PY -m omochae.hypotheses --source NDL-1187053-R0000014-R generate --dry-run` → `--dry-run` を外す |

U-12 は 1 回ずつの比べなので、どちらが良いかの結論にはしない。「道具を何回使い、根拠の欄に拡大した所が出たか」の観察として残す。

## 見る物（回ごとの合否）

| 回 | 通る条件 | 落ちる条件 |
|---|---|---|
| 1 ask | 3 文以内の手順の答え。返り値の 2 つ目が `ai` | 仮説の名前・動き方の文・「仮説」の語が出る（`ask.leaks` が拾えば `refuse` に替わる。替わった事も記録する）。下見の文に無い作り方を足す |
| 2 interpret | `observed`・`causes`・`unknown` が分かれ、人の入れた結果と説明を書き換えない | 動かない結果を「失敗」と呼ぶ。歴史の事実として断定する |
| 3 propose | `check_proposal` を通る（F4.evidence、F7.revision の向きと変えてよい寸法、F8.references、F9.human） | 仮説に順位を付ける・どれが正しいと言う（J-025）。実在しない記録 ID を引く |
| 4 words | `filled_in` と `from_words` で全寸法の出所が分かる（F9.own）。`compose` の床（F5.*）を通る | 人の文を書き換える・評価する・別案を勧める。隠れた補い |
| 5〜7 generate | 仮説 2〜3 本、前例が実在（F8.references）、寸法が雛形の範囲（F5.range）、予想との共通点と違いを並べる | どちらが正しいかを言う。順位。雛形に無い機構を作れると言う。採らなかった歌の読みを根拠にする |

床の検査はコード（`check_result`・`check_proposal`）が落とし、落ちれば 2 回までやり直して止まる。上の「落ちる条件」のうち順位・断定・書き換えはコードが見ないので、本人が案の JSON（`show-generated` / `show-words` / `show`）を読んで見る。

**下見で見つけた事（11-04 に直した）**: 5 の下見の送る中身に、採らなかった読み「怠らし」が、採った読みの注（checked_scope）の中から 1 か所渡っていた。修正の決まり（Red→Green）に沿って直し、渡すのは読みの文・出所・確かめた人だけにした（`tests/test_transcription_filter.py`、gate-trial.md）。根拠の欄に「怠らし」が出たら、それでも落ちとして記録する。

## 費用の見積もり

単価は `src/api/budget.py`: Opus 5.5 入力 $4・出力 $20（100 万トークンあたり）、キャッシュ書き込み 1.25 倍・読み出し 0.05 倍。1 回の出力の上限は `MAX_TOKENS` 16,000（ask は 2,000）。輪は最大 13 往復（道具 8 + やり直し 2 + 3）。

| 役 | 往復の上限 | 上限の計算 | 1 回の上限（見積もり） |
|---|---|---|---|
| ask | 1 | 入力 約 1,500 × $4 + 出力 2,000 × $20 | 約 $0.05 |
| interpret | 3（道具なし、出さなければやり直し 2 回で止まる） | 3 ×（入力 約 3,000 + 出力 16,000） | 約 $1.0 |
| propose / words / generate | 13 | `PER_RUN_CAP` $3 で止まる。判定は呼ぶ前なので、止まる直前の 1 往復（出力 16,000 で $0.32 + 入力）が上に乗る | 約 $3.8 |

7 回の上限の合計: 0.05 + 1.0 + 3.8 × 5 = **約 $20**。11-04 の日割りの上限 $60（11-05 は $70）と累計の停止線 $475 の中。普段の額は未実測で、これは上限。図 1 枚（1600×2656）と拡大 1 枚あたりのトークン数も実測で確かめる。

**日付の注意**: `DAILY_CAP` は 11-02〜11-08 しか無い。それ以外の日は上限が 0 になり、`budget.check` が全部の呼び出しを止める。試験は 11-08 までに行う。

## 止める条件（当たったらその日は止め、本人へ報告）

| 当たった物 | 出方 | すること |
|---|---|---|
| 予算 | `BudgetStop`（1 回 $3・日割り・累計 $475） | 止める。上限は本人の承認なしに変えない |
| 断り | `AgentStopped: Claude が応答を断った` | 止める。入力の何が当たったかを下見と並べて報告 |
| 長さ | `AgentStopped: 応答が長さの上限に達した` | 止める。`MAX_TOKENS` は変えずに報告 |
| 床 | `検査に落ち続けた: F5.../F8...`、終わりの値 3 | 1 回だけ 7 回目で取り直してよい。2 回落ちたら止める |
| 漏れ・順位 | 本人が読んで見つける（上の表） | その回は落ち。案は採らず、続けない |
| 鍵・通信 | `検査できない: Claude を呼べなかった`、終わりの値 4 | 止める。表示された文に鍵の値が出ていないかも見る |

## 記録の置き場

| 物 | 置き場 | git |
|---|---|---|
| 下見 | `data/loop/preview-<役>.json`（画像は大きさだけ） | 載らない |
| 案 | `data/loop/generated-*.json`・`words-*.json`・`interpretation-R-0001.json`・`proposal-*.json`（中に model・道具の回数・トークン数） | 載らない |
| 費用 | `out/api-usage.jsonl`（日・役・トークン・キャッシュ・$）。正は Console | 載らない |
| ask の答え | 残らない（`answer` は記録しない）。端末の出力を要約に写す | — |
| 要約 | 7 回の表（回・役・通った床・落ちた床・トークン・$・止まった理由）を docs/process の決定の記録に 1 枚足し、J-017 の「1 回の費用は未実測」、U-05、U-12 を書き換える | 載せる。案の中身と鍵は載せない |

## 本人が承認する事

- [ ] 7 回の中身と順（6 回目の拡大なしは `--no-zoom` で流す）
- [ ] 費用の上限 約 $20 と、試験の日（11-08 まで）
- [ ] 5・7 回目に使う本人の予想（U-08）と、4 回目の言葉の仮説の文
- [ ] 採らなかった読みが `checked_scope` に残る件を、試験の前に直すか
- [ ] 鍵は本人が repo の鍵の置き場（git の外）に自分の手で置き、試験の後に外すか残すかを決める
- [ ] 止める条件の表で止まったら、その日は再開しない
