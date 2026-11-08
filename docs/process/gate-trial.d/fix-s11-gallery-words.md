## 安全の事項 11（しおりの範囲）への対応: しおりだけの画面の もちよる の字（UX の担当、fix/s11-gallery-words、11-08）

- 目的: #730 の別の目の気づき。しおりで開いただけの画面（合言葉の cookie が無い）にも、もちよる（/gallery）の他の人の札の感想の字が、人の確かめの前でも出ていた（合言葉の画面と同じ扱い）。安全の事項 11（しおりの範囲を本人に関係するデータに閉じる）として、統括の決め 11-08 で作る（合言葉の画面・手元の場・公開の場は一字も替えない）
- どうしたか: web/techo_site.py の made_item と gallery_page に shiori の引数を足し、しおりだけの画面の時だけ、人の書いた文（感想・工夫・のこした記録の欄）を人が確かめた字だけにし、記録の番号を出さない（公開の場と同じ線）。web/play_server.py の /gallery が、門の控えた印（しおりだけで通った画面）を見て渡す。今残した 1 つの札（自分の記録・記録の鍵で見分ける）は今のまま
- 試験 tests/test_shiori_gallery.py: しおりだけの画面は確かめた字だけ・番号なし／合言葉の画面・両方の画面・手元の場の もちよる の中身が前の作り（gallery_page の既定）と一字も同じ／公開の場は前のまま
- 検証ゲート: Red: main a6f352df に試験だけを置くと rc 1（gate-evidence/red-shiori-gallery.txt）。Green: gate-evidence/green-shiori-gallery.txt
