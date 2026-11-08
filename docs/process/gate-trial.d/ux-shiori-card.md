## しおりの紙を描く生成器（表と裏の 2 頁・UX の担当、ux/shiori-card、11-08）

- 目的: 本人の答え 11-08「しおりは型紙の PDF に一緒に刷る。」。設計は grove の state/shiori-in-sheet-20261108.md の 2.1 版（別の目の確かめ 2 回で「作ってよい」）。この枝は紙を描く所だけで、刷る道（合言葉付きの場の PDF の釦の POST・待ち・のこすの確かめで結ぶ）は別の PR
- どうしたか: src/omochae/shiori_card.py を足した。pages(印, 玩具, 順, 版, 刷った時, 決まった番地) は A4 縦の 2 頁の PDF を返す。表と裏を別の頁にし（設計の推し (a)・本人の答え待ち）、同じ位置（左 80mm・上 40mm）に 50×150mm を 1 枚ずつ置く
  - 表: 穴の印・原画・縦書きの題字「うつし」と玩具の名・右下に 22mm の QR（決まった番地/s/<印>・墨を地に寄せた茶・四角の点・誤りの直し M・形で描く）。印の 22 字は字で刷らない
  - 裏: 9 つの絵（開く頁と同じ並び web.shiori_open.PICTURE_IDS）の 3 つに朱の ①②③・裏の字 3 文・玩具の名と型紙の版と刷った日（東京の日付）。頁の頭に写さない断り
  - 2 頁とも、しおりの下に切り方の 1 行。字は設計の 6 節の一覧のまま（どれも本人の確かめ待ち）
  - merge(型紙の PDF, しおりの 2 頁) は型紙の頁を書き直さずに後ろへ足す。PDF の情報は題だけ（作った道具の名も入れない）
  - QR は segno 1.6.6、PDF を合わせるのは pypdf 7.0.0（どちらも BSD・OSV に知らせ無し）を requirements.txt に足した
- 失敗と直し: cairosvg が絵をそのままの画素で埋め、2 頁で 1.8MB になった。しおりの頁の絵だけを JPEG に詰め直して 0.6MB（原画のある所）。題字と玩具の名は縦書きの 2 列なので、字を取り出すと行ごとに混ざる（試験は 1 字ずつ見る）
- 歩いて確かめた事: 刷った PDF を 300dpi で絵にし、手元で一度 OpenCV で読むと https://utsushi.konoba.workers.dev/s/<印> と出た（試験の機械には OpenCV が無いので、試験は点の並びを segno の符号と照らし、読む道具がある時だけ読む）
- 検証ゲート: Red: main 095fb28b に試験だけを置くと rc 1（gate-evidence/red-shiori-card.txt・shiori_card が無い）。Green: gate-evidence/green-shiori-card.txt（「測れない」は QR を読む道具が無い 1 行）。test_shiori・test_shiori_open・test_ai_name・test_reader_words・test_frozen_manifest・test_gate_evidence・test_gate_trial_merge・test_ledger も rc 0

| 決めの行 | 照らし | 根拠 |
|---|---|---|
| 本人「しおりは型紙の PDF に一緒に刷る。」 | 一部（紙を描く所と、型紙の PDF の後ろに足す merge。刷る道は別の PR） | src/omochae/shiori_card.py・tests/test_shiori_card.py |
| QR は道だけ・順は裏（2″・2‴ の 1） | 守った（表と裏を別の頁・印を字で刷らない・①②③ は裏の頁だけ） | test_shiori_card の 1・2 |
| 決まった番地だけを刷る | 守った（番地が無い時は刷らない） | test_shiori_card の 6 |
| GPL を入れない・費用 | 守った（segno・pypdf は BSD・API を呼ばない） | requirements.txt |
| 新しい字は本人の確かめ | 答え待ち（設計の 6 節の字のまま） | shiori_card の定数 |
- 直し（11-08 15:45）: 試験の試しの印を、決まった字から回すたびに作る印（secrets.token_urlsafe(16)）に替えた。push の門の C（鍵らしい字）が試験の字の印に当たったため。Green は gate-evidence/green-shiori-card-token.txt
