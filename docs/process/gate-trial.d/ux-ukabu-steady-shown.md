## 触って送っても動かない事の試験に、玩具が見えている事の確かめを足し、赤の証拠を今の試験で取り直す（README の担当、ux/ukabu-steady-shown、11-08）

- 目的: #688 の別の目の気づき 2 つ（統括を通して 11-08）
  - 赤の証拠 docs/process/gate-evidence/red-ukabu-steady.txt は、今の試験に無い古い段（幅を替えて戻す）で取った物。今の試験で取り直す
  - tests/test_ukabu_steady.py に、玩具が見えている事の確かめを足す（見えていないと、動かない事を見ても空の確かめになる）
- どうしたか: tests/test_ukabu_steady.py の 0 を足した。開いた後に層に .placed があり、4 つのうち 3 つ以上が出ていて絵が読めている（visibility・naturalWidth・offsetHeight）
- 検証ゲート: **済み**。Red: 今の試験（0 を足した物）を、#688 の触って送る直しの前の台本（6fd0cb76 の src/web/ukabu.py）で回して rc 1（gate-evidence/red-ukabu-steady-5.txt・320×568 で高さを戻すと徳利が 236,543 から 228,590 へ）。Green: 今の main の台本で rc 0（gate-evidence/green-ukabu-steady-5.txt）
- 前の赤の証拠の扱い: red-ukabu-steady.txt・-2・-3 は前の版の試験（幅を替えて戻す段があった版）で取った物、-4 は 0 を足す前の今の試験で取った物。gate_evidence は書き換えない決まりなので残し、今の試験の赤は -5 とした
- 限り: iPhone の Safari と iPad の実機では見ていない
- マージ後の書き戻し: Issue は立てていない
