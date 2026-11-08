## つくるの外の頁でも、部品が作る仮説の字を印なしの「仮説」にする（直しの担当、fix/kasetsu-plain-all、11-08 朝）

- 目的: 本人の答え（11-08）「そろえる。」。#621（つくるの頁と刷る紙）の続きで、つくるの外（作る側の頁の「仮説 A 版 N」・もちよると のこすの記録の札の「A の紙」）も「仮説」だけにする。印は記録の番号として残す（同じ）
- どうしたか: 呼び名は #621 の `hypotheses.SHOWN`・shown_name を使う。替えた所は、作る側の頁の改善の輪の版の行（`src/web/kaizen.py`）と版の歩みの札の題（`src/web/ayumi.py`）・話した事の紙の呼び名と考えの行（`src/web/hanasu.py` の maker_section）・作る側の頁の記録の紙の呼び名（kaizen.toy_page）・もちよる と のこす の記録の札（`src/web/techo_site.py` の made_item・own_item・records_page）・作る側のギャラリーの札（`src/omochae/gallery.py`）・英語の玩具の頁 /en/toy の仮説の札（`src/web/en.py`。大きな印の字を外し Idea A → Guess）・くずし字の頁の仮説の行（`src/web/zukan.py` の hypothesis_lines）
- 替えていない所: 記録の中の字（人の説明・本人の所見とつぶやき・本人の決定の記録・版の台帳の文・AI の読み）。人の言葉と記録の字で、2 つの仮説を比べる文（「仮説Aにある土台が仮説Cにもあると、作りやすい」「仮説 D は型紙が仮説 C と同じ」など）は、印を外すと意味が通らないため。作る側の字を描く時に替える表（`src/web/wording.py` の H-C → 仮説 C）も、同じ理由で替えていない
- 見つけた事: 記録の札の字（「仮説 C の紙・動いた」など）の英語は、前から表に無い（試験の場に記録が無いので、全頁の英語の試験に出ない）。今回の直しで抜けた物ではない
- ゴールの要件: 部品が作る字に「仮説 A 版 N」「A の紙」「Idea A」の形が無い。記録の中の字は前のまま
- 検証ゲート: Red: 今の main 6c5fc344 の木に `tests/test_kasetsu_plain_all.py` だけを当てて rc 1（`docs/process/gate-evidence/red-kasetsu-plain-all.txt`。くずし字の頁の仮説の行が「仮説 C 柄を下から押し上げる: …」）。Green: rc 0（`green-kasetsu-plain-all.txt`、6c64c9e9）
- 確かめていない事: 本人が頁で見る事
- マージ後の書き戻し: Issue は立てていない
