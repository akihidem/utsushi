## 新しく開いたサイトの入口は、いつも日本語から始まる（README の担当、fix/lang-session-cookie、11-08）

- 目的: 本人の言葉（11-08）「サイトトップのデフォルトの表示は日本語で。」
- なぜか: 言葉の cookie（utsushi_lang）に 1 年の期限（Max-Age=31536000）が付いていて、一度 English か やさしい日本語 を押した端末は、次の日に開き直しても前の言葉の入口が出た
- どうしたか: `src/web/play_server.py` の `_pick_lang` で、言葉の cookie から期限を外した。ブラウザを閉じれば消えるので、新しく開いた入口は日本語から始まる。開いている間は cookie が残るので、頁をたどっても選んだ言葉のまま
- 比べた案: 入口（/）だけ cookie を見ずにいつも日本語にする案は、英語で読んでいる人が入口へ戻るたびに日本語へ戻るので採らない
- ゴールの要件: tests/test_lang_session.py（?lang=en・easy・ja の cookie に Max-Age も Expires も無い・cookie 無しの / は日本語で言葉の cookie を渡さない・cookie がある間は / も玩具の頁も選んだ言葉のまま）
- 検証ゲート: **済み**。Red: 直す前で rc 1（gate-evidence/red-lang-session.txt）。Green: rc 0（gate-evidence/green-lang-session.txt）
- エビデンスゲート: 言葉の関わる試験（test_en_all・test_easy_all・test_kasetsu_plain・test_easy_ruby・test_easy_svg_text）rc 0
- 限り: ブラウザが閉じた後も前の画面を戻す形（タブの復元）では、ブラウザが cookie を残す事がある。サーバからは止められない
- マージ後の書き戻し: Issue は立てていない
