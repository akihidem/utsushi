## 安全の事項 1・11 への対応: しおりだけの画面の 手帖の記録の頁の字（UX の担当、fix/s11-kiroku-words、11-08）

- 目的: 安全の第 2 回の確かめで残った所。しおりで開いただけの画面（合言葉の cookie が無い）にも、手帖の記録の頁で、ほかの人の記録の工夫の行・説明の字・記録の番号が、合言葉の画面と同じに出ていた（統括の決め 11-08: もちよる と同じ線に・合言葉の画面と手元の場は一字も替えない）
- どうしたか: web/techo_site.py の records_page に shiori_mine（そのしおりに結ばれた記録の番号の組）。組がある時だけ、ほかの人の記録の札を、公開の場の記録の頁と同じ閉じた形（記録の番号・ひとこと・自分の仮説の紙への道・工夫の行・説明と次の版の字を出さない）にし、結ばれた記録（本人の物）は今のまま。web/play_server.py の _kiroku が、門の控えた印（しおりだけで通った画面）を見て渡す。合言葉の画面・両方の画面・手元の場・公開の場は None で今のまま。写真は前からの見せる線のまま
- 試験 tests/test_shiori_kiroku.py: しおりだけの画面は自分の記録の工夫の行と説明が出て、ほかの人の工夫の行・説明・番号は出ない／合言葉の画面・両方の画面・手元の場は、ほかの人の字と番号が今のまま出る
- 検証ゲート: Red: main 3b0da3c0 に試験だけを置くと rc 1（gate-evidence/red-shiori-kiroku.txt）。Green: gate-evidence/green-shiori-kiroku.txt。test_shiori_role・test_shiori_gallery・test_shiori_sheet・test_shiori_open・test_techo_site・test_nokosu_flow・test_nokosu_route・test_record_fold・test_ux_fold_record・test_public_open・test_loop1_withdraw・test_ai_name・test_reader_words・test_frozen_manifest・test_gate_trial_merge・test_gate_evidence・test_ledger も rc 0
- まだの所: 参加者・進行者・管理者の 3 つの役の分け方（合言葉の画面が管理する側を兼ねる）
