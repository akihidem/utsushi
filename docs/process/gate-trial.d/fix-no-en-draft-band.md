## 日本語の玩具の頁の英語への入口から、括弧の断り「（英語の文は案です）」を外す（README の担当、fix/no-en-draft-band、11-08）

- 目的: 日本語の玩具の頁の英語の帯の入口「Read and print in English（英語の文は案です）」の括弧を外す。入口は残す
- なぜか: 本人の決め（11-07）「外してよい」。英語の頁の頭の断り DRAFT を外した #590 と同じ扱い（前の頼みでは DRAFT と別の字なので残し、外すかを本人に聞いた）
- どうしたか: `src/web/en.py` の band の字から括弧を外した。頁に出なくなった字の訳を、英語の表（`data/i18n/en.json`）とやさしい日本語の表（`data/i18n/yasashii.d/1.json`）から外した
- ゴールの要件: 御来迎と虎の日本語の頁に、英語への入口があり、括弧の断りが無い（`tests/test_en.py`）。全頁の英語とやさしい日本語の試験が通る
- 検証ゲート: **済み**。Red: 直す前の帯で rc 1（gate-evidence/red-no-en-draft-band.txt）。Green: 直した後 rc 0（gate-evidence/green-no-en-draft-band.txt）
- エビデンスゲート: 上の 2 つの出力と、`test_en_all`・`test_easy_all`・`test_easy_part1` が rc 0。`./run.sh` の全部は合体の道が回す
- マージ後の書き戻し: Issue は立てていない（新しい Issue は提出を止める物だけ）
