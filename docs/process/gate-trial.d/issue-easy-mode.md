## やさしい日本語（3 つ目の言葉・lang=easy）の土台を足す（サイトの担当、issue/easy-mode、11-07 夜）

- 目的: 頭の帯の やさしい で、今の頁をやさしい日本語（ルビつき）で読めるようにする土台を作る。表の中身は 3 つの窓が分けて書く
- なぜか: 本人の言葉（11-07 夜）「サイト、言語でやさしい日本語選べるように。このモードはルビつけてやさしい日本語に全体の文が変換されるモード」「まだひつようなところは実装しよう」。設計は UX の担当（grove の state/yasashii-mode-20261107.md）
- どうしたらいいか: 全頁の英語（J-035・web.i18n）と同じ出口の置き換えに 3 つ目の言葉を足す。表は data/i18n/yasashii.json と窓ごとの yasashii.d/*.json を重ねて読む（1 つのファイルを 3 本で書き足すと衝突するため）。値の ｜漢字《よみ》 を出口で <ruby> にする（字の節）／印を外す（属性・<title>・<option>）。表に無い鍵は元の日本語のまま
- 比べた案: 実行の時に形態素解析でルビを振る案は採らない（読みの誤り、とくに御来迎・江都二色・張子などを表の中で直せないため・設計の推し）。頁ごとにやさしい日本語の頁を書く案は、英語の時と同じ理由で採らない
- ゴールの要件: 全部の頁の道が、やさしい日本語でも日本語と同じ状態で開く。ルビの印が崩れない。<title> にルビが入らない。頁の頭の札が 1 つ。?lang=easy の cookie と ?lang=ja で戻る。英語の頁は替えない
- 検証ゲート: **済み**。Red: 今の main（`57cfadf4`）にこの試験（tests/test_easy_all.py）だけを置くと、やさしい日本語の表が引けずに rc 1（gate-evidence/red-easy-mode.txt）。Green: この枝で rc 0（gate-evidence/green-easy-mode.txt）。どちらも `python -m omochae.gate_evidence write` で書いた
- エビデンスゲート: 上の 2 つと、test_en_all・test_nav_same・test_nav_arrow・test_ux_stage1・test_tap_size・test_landscape_fit・test_ledger の rc 0 と ./run.sh
- マージ後の書き戻し: 表の中身（分け 1〜3）は 3 つの窓の PR で yasashii.d/ に足す
