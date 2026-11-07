## 英語の頁の頭の断り「Draft translation…」を外す（README の担当、fix/no-en-draft、11-07）

- 目的: 英語の頁（全頁の lang=en と、前からの /en・/en/toy/<印>）の頭に出していた断り「Draft translation. A native speaker has not checked it yet.」を出さない
- なぜか: 本人の言葉（11-07）「これ要らない。Draft translation. A native speaker has not checked it yet.」。やさしい日本語の頁の頭の「下書きです」を外したのと同じ扱い（#583）
- どうしたか: `src/web/en.py` の DRAFT と、前からの英語の頁の 2 か所の字を外した。`src/web/i18n.py` の頭の札（draft_note・class="en-draft"）を外し、説明の文を直した。`docs/features.json` の英語の機能の文から「頁の頭に下書きの札」を外した
- 変えていない事: 訳の表の中身（英語の見直しの直しは本人の決め待ちなので混ぜない）・日本語の頁の「（英語の文は案です）」・やさしい日本語の表（対応する鍵は無かった）。`_after_main` は、やさしい日本語の頁がまだ使うので残した
- ゴールの要件: 英語の頁のどこにも断りの字と札が出ない（`tests/test_en.py`・`tests/test_en_all.py`）。`./run.sh` が全部期待どおり
- 検証ゲート: **済み**。Red: 直す前の頁で 2 つの試験が rc 1（gate-evidence/red-no-en-draft.txt）。Green: 直した後 rc 0（gate-evidence/green-no-en-draft.txt）
- エビデンスゲート: 上の 2 つの出力と、`./run.sh` の 270 本すべて期待どおり（rc 0）
- マージ後の書き戻し: Issue は立てていない（新しい Issue は提出を止める物だけ）
