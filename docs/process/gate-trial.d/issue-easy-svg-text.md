## やさしい日本語で SVG の字にルビを入れない（サイトの担当、issue/easy-svg-text、11-07 夜）

- 目的: やさしい日本語の頁で、学びの輪の図の字が図の外へ追い出される事を止める（#589 の止めの元）
- なぜか: 別の目の知らせ（のこす の頁で撮って確かめた）。SVG の <text> の中に <ruby> が入ると、ブラウザが SVG の外へ追い出し、図の字が図の下に縦に並んだ。#589（4.json）が図の字の鍵を足したので起きる
- どうしたらいいか: i18n に SVG_TEXT（text・tspan・textPath）を足し、その中の字はルビの印を外した字にした（<title>・<option> と同じ道）。比べた案: 読みを 漢字（よみ） で添える（#583 の <title>・<option> の形）。#583 と #589 の 4.json を重ねた試しの木で幅 390 を撮ると、図の札が図の外へはみ出し、札どうしが重なった（grove の state/easy-svg-text-20261107/paren-overflow-390.png）ので採らなかった。図の字の読みは、図のすぐ上の文（同じ言葉に全部ルビ）が持つ
- 確かめていない事: #583 が入った後、<title>・<option> は 漢字（よみ）、SVG の字は印を外した字のまま（#583 の側で SVG_TEXT を印を外す道に残す）
- ゴールの要件: SVG の text・tspan の中に <ruby> が無い（字は消さない）・SVG の外の字の節は前と同じくルビ・全部の頁で <svg> の中に <ruby> が無い
- 検証ゲート: **済み**。Red: 今の main（`6e0880ed`）に tests/test_easy_svg_text.py だけを置くと、SVG の text の中に <ruby> が入って rc 1（gate-evidence/red-easy-svg-text.txt）。Green: この枝で rc 0（gate-evidence/green-easy-svg-text-plain.txt。green-easy-svg-text.txt は、読みを添える形も通す前の版の試験で回した物）。どちらも `python -m omochae.gate_evidence write` で書いた
- エビデンスゲート: 上と ./run.sh
- マージ後の書き戻し: 無し
