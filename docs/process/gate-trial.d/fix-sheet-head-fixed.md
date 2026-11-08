## 刷る紙の題から仮説の印を外しても、部品が 1 つも動かない頭の段にする（直しの担当、fix/sheet-head-fixed、11-08 朝）

- 目的: 統括の決め（11-08 の (b)）。#621（本人の言葉「つくる、のところ仮説Cとか仮説Aとかはなしで仮説、と表記する」）で紙の題が短くなり、この機械の字（Noto Serif CJK JP）では「刷った組」が題の行に入って頭の段が 1 行減り、部品の並び全体が 3.5mm 上へ動いた（別の目が `tests/test_floor_pin.py --dump` で比べて見つけた）。題は「仮説「…」」のまま、頭の段を前と同じ組み方に固定する
- どうしたか: `src/omochae/compose.py` の compose に fit_title を足した。頭の字の段の高さ（次の y）と「刷った組」の置き場は fit_title（前の題＝印のある形）で決め、刷る字は title のまま。刷る紙（`src/omochae/hypotheses.py` の print_sheet）は前の題を fit_title に渡す。凍結の床の試験も、今の組を同じ組み方で組む
- 見つけた事: 直す前の組み方だと、この機械の字で部品が動く玩具は 6 種（虎 v7 のほか、控えに入っていない試作の玩具 5 種）。決まった字の幅（standin）では 0 種
- 凍結の床: `tests/floor_pin.json` の今の組の 4 枚を外して `--add` で取り直した（理由は `docs/claude-usage.md`）。替わった指紋は虎 v7 の型紙の real の 1 つだけ。#621 の前の紙と `--dump` で比べ、4 枚とも 2 通りの字の測り方で違うのは題の 1 行だけ、ほかの 30 枚は 1 バイトも違わない
- ゴールの要件: 全部の玩具の今のたたき台の型紙で、前の題で組んだ紙と新しい題で組んだ紙の違いが題の行だけ（standin と real の両方）
- 検証ゲート: Red: 今の main 611d1591 の木に `tests/test_sheet_head_fixed.py` だけを当てて rc 1（`docs/process/gate-evidence/red-sheet-head-fixed.txt`。この機械の字で NDL-1187053-R0000009-L の型紙の図形が 3.5mm 動く）。Green: rc 0（`green-sheet-head-fixed.txt`、67b95228。83 種）
- 確かめていない事: 刷った紙を物差しで測る事（配置の SVG で比べた）
- マージ後の書き戻し: Issue は立てていない
