## 公開の場を http で開く試験 test_explain_no_name の CookieJar に、Secure の cookie も送り返させる（README の担当、fix/test-cookie-secure-http、11-08）

- 目的: 今の main で tests/test_explain_no_name.py が落ちる（統括の知らせ 11-08・#735 から）
- なぜか: #735 で公開の場の所有者の cookie に Secure を付けた。この試験は Python の CookieJar で http://127.0.0.1 から公開の場を開くので、記録の cookie を送り返さなかった（#735 の test_clip_receipt・test_media_strip と同じ形）
- どうしたか: サイトの作りは替えず、試験の CookieJar だけ http でも送り返す決まり（secure_protocols に http）にした。本番の公開デモは https 越しなので届く
- ほかの試験: 公開の場を CookieJar で開く試験 9 本を今の main で回し、落ちるのはこの 1 本だけだった（test_load_guard・test_page_description・test_own_form_gone・test_shiori_sheet・test_ux_keep_gallery・test_unknown_record・test_words_card_1106・test_write_limit は rc 0）
- 検証ゲート: **済み**。Red: 今の main（c63822f3）で rc 1。Green: rc 0（gate-evidence/green-explain-cookie-http.txt）
- マージ後の書き戻し: Issue は立てていない
