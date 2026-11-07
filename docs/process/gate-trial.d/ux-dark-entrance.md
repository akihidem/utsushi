## 暗い画面の版の入口を、白と同じ作りで色だけ暗くする（UX の担当、ux/dark-entrance、11-08）

- 目的: 本人の決め 11-08「もう1つ立てる」（HMD のための暗い皮の公開デモ）と、統括の頼み 11-08「本人の頼みは『暗い画面の版』なので、入口も白と同じ作り（縦の題字・まずはここから・小さい写し）で色だけ暗くする形にそろえる」。立てた暗い版の入口は黒のジンの前の作り（額の表紙・縦読みの章・まずはここから 無し・大きい写し）で、final-rebuild-check.sh が 3 つ ng を出していた
- どうしたか: web/looks.py に yoru（tenji(photos, dark=True)）。白の入口の CSS の色だけを DARK の対（皮の表 tenji → zine に寄せた）で置き換え、帯の変数は皮 zine の物。body の印は tenji yoru。皮 zine のサイトの / と /look/zine は yoru を出す（PAGES）。前の zine() は道から外した（試験が関数を読むので、消すのは別の PR で）
- 序の頁: 前に黒の入口にあった北斎漫画の縦読み（案 2）を、白と同じく序の頁へ（web/about.py・黒の色）。押すと重なる案 1 は前のとおり白だけ
- 試験の直し（前の黒の入口の作りを前提にしていた所を、新しい作りへ）: test_two_sites（body の印）・test_cover_growing（表紙の節は tj-hall）・test_site_hokusai（縦読みは入口でなく暗い版の序の頁）・test_ux_stage0（暗い版の入口も白と同じ見方）。弱める向きの直しは無い（見る所を前の作りから今の作りへ移した）
- 検証ゲート: **済み**。Red: main の頭 da1aaa36 に新しい試験 tests/test_dark_entrance.py だけを置くと rc 1（gate-evidence/red-dark-entrance.txt）。Green: gate-evidence/green-dark-entrance.txt。幅 390 と 1440 の Chromium で、縦の題字・まずはここから・全部のおもちゃの節が暗い地で出るのを見た
- 確かめていない事: Vision Pro と透けて見える眼鏡での見え方（本人の試し）。眼鏡向けに字を大きくする事は提出の後
