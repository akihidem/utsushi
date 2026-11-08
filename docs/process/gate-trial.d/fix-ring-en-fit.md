## 輪の図 2 つで、英語の字どうしが重ならないようにする（直しの担当、fix/ring-en-fit、11-08 昼）

- 目的: 統括の割り振り（11-08）。重なりの見回り（grove の state/no-overlap-20261108.md の 1 と 2）で、型紙の窓の輪の図（`src/web/wa.py`）と学びの輪の図（`src/web/loop_figure.py`）の英語の字どうしが重なった（8 つの大きさ全部・玩具の頁・のこす・よむ）。英語は日本語より長く、札の幅（日本語の字の数で決まる）と真ん中の丸に入らなかった
- どうしたか: 英語の頁（html lang="en"）の時だけ、図の字の大きさを CSS で替えた。日本語の図（字・大きさ・置き場）は替えていない
  - 型紙の窓の図: 札の字 14 → 10.5px、真ん中の「Current template」12 → 9.5px、「Version N」26 → 15px（wa.STYLE の html[lang=en] の決まり）
  - 学びの輪の図: 字に印（class lf-s・lf-w・lf-n・lf-c）を付け、図の中の style（loop_figure.EN_STYLE）で、札の字 20 → 13px、誰がするかの名 15 → 9.5px、真ん中の「Current template」20 → 15px、真ん中の小さな 1 行 13 → 11px にし、小さな 1 行は左右の札より下へ 22 下げた（左右の札の間に入らないため。下の札の上には届かない）
- ゴールの要件: 英語・日本語・やさしい日本語 × 8 つの大きさ × 4 つの頁（御来迎と虎の玩具の頁・のこす・よむ）で、輪の図の字の 1 行の箱どうしが重ならず、札の字が札からはみ出さない
- 試験: `tests/test_ring_en_fit.py` は、英語の字の幅を紙の型紙と同じ字の測り（`omochae.textfit`）で出し、札・丸・札の間に収まる事を見る（ブラウザが無くても回る）。日本語の字の大きさが前のままな事も見る
- 検証ゲート: Red: 今の main ad6d67f9 の木に `tests/test_ring_en_fit.py` だけを当てて rc 1（`docs/process/gate-evidence/red-ring-en-fit.txt`。「What you changed:」が型紙の窓の札に入らない）。Green: rc 0（`green-ring-en-fit.txt`、d411b890）
- エビデンスゲート: 頭なしの Chromium で、英語・日本語・やさしい日本語 × 8 つの大きさ（iPad 横と縦・PC 1280・1440・1920・iPhone SE・14・Max）× 4 つの頁で、字の 1 行の箱の重なりと札からのはみ出しが 0（直す前は英語の 32 の組で重なりかはみ出し）。英語の幅 390 の絵は grove の state/ring-en-fit/
- 確かめていない事: 本物の iPad・iPhone の Safari の字の形での見え方（測りは Chromium と、型紙の字の測り）
- マージ後の書き戻し: Issue は立てていない
