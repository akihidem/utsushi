## English の頭に、うつしの位置づけ（英語 2 文）と paper to toy の仕組み（英語 3 文）を足す（UX の担当、ux/paper-to-toy、11-07。本人の言葉と窓口の決め）

- 目的: 本人の言葉（11-07 昼）「想定する相手は教育分野から、みんなが使える公開のサービスへ広げる。utsushi は paper to toy の具体例、という説明をサイトに」の English の側
- なぜか: English の頁には paper to toy の説明が無い
- どうしたか: 窓口の決め（11-07）「序の頁の位置づけは序の頁と README の担当の作りでそろえる。UX 案の置き場のうち English の頭は英語 3 文を入れる形で生かす」に合わせ、English の頭に、型紙エンジンの README と版の台帳から作った材料の英語 3 文を、字を変えずに置いた。J-030 と同じ紹介の文（INTRO）は変えず、別の段
- 前の形（失敗した版も残す）: 最初は序の頁の頭と なぜ の末にも位置づけと相手の字を置いた（gate-evidence/red-paper-to-toy.txt・green-paper-to-toy.txt）。窓口の決めで序の頁は別の作りにそろえるので、序の頁の分を外した
- 比べた案: 入口の最初の画面にも置く案は、入口の頭は『江都二色』の話だけという本人の決め（#517）を崩すので採らない
- ゴールの要件: English の頭に 3 文が 1 回（合言葉なしの場でも）、紹介の文は今のまま、入口と序の頁には足さない
- 検証ゲート: **済み**。Red: main（f8873d89）にこの試験だけを置くと rc 1（gate-evidence/red-paper-to-toy-en.txt）。Green: gate-evidence/green-paper-to-toy-en.txt
- エビデンスゲート: 上の 2 つの記録と `tests/test_paper_to_toy.py`
- 確かめていない事: English の文は英語を母語にする人が見ていない（頁の断りのとおり）。3 文は材料の字のままで、本人の確かめは窓口へ
- 最後の形（11-07 13 時台）: 本人が位置づけの英文を採った（「この英文でよい」「#526 の英文は案のままで合体してよい」）。窓口の決め 130735「/en の英語 3 文は #526 の 1 本にまとめる。#527 は /en の分を外す」。English の頭に、位置づけの 2 文（POSITION）→ 仕組みの 3 文（ENGINE）の順。位置づけは「これから」の向きの字を使わない（本人の言葉「これからというよりは、みんなが使えるサービスとして作った」）。test_reader_words の「調べの番号」の式を research から research/\d に狭めた（本人の英文の research＝研究 が当たったため。research/22・docs/process/research/36 の形は今も当たる）。Red: main（62dd1119）にこの試験だけを置くと rc 1（gate-evidence/red-paper-to-toy-en-final.txt）。Green: gate-evidence/green-paper-to-toy-en-final.txt
