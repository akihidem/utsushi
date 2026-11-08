## 入口の英語の頁を横書きにし、題字「うつし」の下に読みを入れる（README の担当、ux/entrance-en-yomi、11-08）

- 目的: 本人の言葉（11-08）「トップページ、英語版は余白維持で横書きにしてください。うつし、のひらがなの下に utushi と読みをいれる。」。綴りは本人の答え（11-08）「utsushi。」
- どうしたか: 題字のひらがなを英語の頁でも訳さない（lang="ja"）形にし、下に読み（`looks.YOMI`・1 か所の定数）を置いた。読みは縦書きの題の行の中で横書きの小さな塊にしたので、題の縦書きはそのまま。英語の頁（html[lang=en]）は題・副題・英字を横書きにし、題の間の 3 列・高さ・余白は日本語の頁のまま。1 列に積む幅の日本語の頁は、読みの分（24px）だけ上の余白を詰めた（読みを足すと、幅 390×844 で「このサイトについて」が最初の画面の外の 857px に出たため。main では 834px）
- 比べた案: 英語の頁の題を "utsushi" の字のまま横にし、読みを付けない案は、本人の言葉「ひらがなの下に」と合わないので採らない。読みを日本語の頁だけに出す案は、本人の言葉が頁を分けていないので採らない（全部の頁の推し・統括）
- ゴールの要件: tests/test_entrance_yomi.py（白と暗い版・日本語・やさしい日本語・英語・幅 320/390/1440: 読みはひらがなの真下で 12px 以上・英字と題と副題と このサイトについて が重ならない・幅の外に出ない・横にはみ出さない・英語は横書き・日本語の題は縦書き・幅 390×844 と 1440×900 で このサイトについて が最初の画面の中）
- 検証ゲート: **済み**。Red: 直す前で rc 1（gate-evidence/red-entrance-yomi.txt・読みが無い）。Green: rc 0（gate-evidence/green-entrance-yomi.txt）
- エビデンスゲート: test_hall_tate・test_ukabu・test_dark_entrance（題の字の形を新しい形に合わせた）・test_white_only・test_cover_growing・test_ux_stage0・test_looks_motion・test_about_site・test_entrance_scroll・test_en_all・test_easy_all・test_tap_size・test_en_terms・test_ledger が rc 0。白と暗い版の幅 1440 の絵を目で見た
- 気づき（直していない）: 英語の頁の副題の 2 行目は今も "Finding out how lost toys moved"（前の題の訳）で、3 行目 "brought back to life in paper" と 1 つの句につながらない。UX の担当の案は 2 行目を "the lost movements of toys" とする形。本人の副題の字の訳なので、替えるかは統括と本人
- マージ後の書き戻し: Issue は立てていない
