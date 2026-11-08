## 玩具の頁の試験の「歌の読みが無い玩具」の見本を選び方にする（型紙の担当、fix/toy-foot-quiet、11-08）

- 目的: main で tests/test_toy_foot_ndl.py の「歌の字は読みのある玩具だけ」が rc 1。見本 QUIET（R0000013-L-5・亀）に #661 でくずし字の歌の読みが入ったため
- どうしたか: QUIET を、並びの中から出典の記録に読みの無い玩具を選ぶ形にした（見る線は替えない）。同じ見本を名指ししていた test_toy_page_tate も同じ形に
- 検証ゲート: **済み**。Red: 今の main（`9cd182a3`）で test_toy_foot_ndl が rc 1（gate-evidence/red-toy-foot-quiet.txt）。Green: この枝で rc 0（gate-evidence/green-toy-foot-quiet.txt）
- 確かめていない事: 全部の試験（`./run.sh`）。ほかに名指しの「読みの無い玩具」の見本は、test_genga・test_toy_head・test_kuzushi_notes（くずし字の 2 番目の組の枝で選び方に替え済み・まだ合体していない）
