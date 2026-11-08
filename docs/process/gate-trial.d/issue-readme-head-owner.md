## README の頭の 3 つの項目を本人の字に置き換える（型紙の担当、issue/readme-head-owner、11-08）

- 目的: 本人が README の頭の 3 つ（何か・題材・どう直るか）を書き直した。一字も替えずに置く
- 始めた所: grove の standing-decisions の最後の行（本人が書き直した字）
- どうしたか: README の頭の 3 つの項目と、試験の控えを本人の字に。30 秒の要約の何か（README の畳みと CLAUDE.md）の頭にも本人の何かの字を置き、前からの一言と目的の字はその後に残した
- 本人に確かめた所: どう直るかの最後の文「それぞれ版 は、版14・版 7 まで重なりました。」は打ち間違いに見えたので窓口が確かめ、本人の答え「(A) でよい。」で「それぞれ版 14・版 7 まで重ねました。」にした
- 検証ゲート: **済み**。Red: 今の main（`743706e5`）に新しい頭の試験だけを置くと rc 1（gate-evidence/red-readme-head-owner.txt）。Green: この枝で rc 0（gate-evidence/green-readme-head-owner.txt）
- 確かめていない事: 全部の試験（`./run.sh`）
