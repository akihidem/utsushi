## 輪の図の英語の字の大きさを CSS から外し、字の大きさの床（12px）で落ちた main を緑に戻す（直しの担当、fix/ring-en-tap、11-08 昼）

- 目的: 統括の急ぎ（11-08）。#680 で英語の頁の時だけ輪の図の字を CSS（font-size の px）で小さくしたので、押す所と字の大きさの床（`tests/test_tap_size.py`・頁の CSS の字は 12px 以上）が /about の 9.5px と 11px で落ち、main が赤になった
- どうしたか: 輪の図 2 つ（型紙の窓 `src/web/wa.py`・学びの輪 `src/web/loop_figure.py`）を、日本語の図と英語の図の 2 つの SVG にし、頁の言葉（html の lang）で片方だけを見せる（`src/web/en_fig.py` の TOGGLE）。英語の図は訳の表の英語を直に持ち、字の大きさは SVG の中の値（wa.EN_FS・loop_figure.EN_FS）で持つ。英語の頁の CSS の字の大きさの指定（#680 の html[lang=en] の決まり）は外した。日本語の図は替えていない
- 残る事（次の直し）: 英語の図の字の、画面に出る大きさは #680 と同じでまだ小さい（幅 390 で名が約 6px）。統括の決め（11-08）の下限（幅 390 で 10px 以上・名と真ん中の小さな 1 行は 9px 以上）にする英語の並べ方は、続きの PR で作る（en_fig の wrap・user_size・FIG_390 はそのための部品）
- 検証ゲート: Red: 今の main 095fb28b の `tests/test_tap_size.py` が rc 1（`docs/process/gate-evidence/red-ring-en-tap.txt`。/about の 9.5px と 11px）。Green: rc 0（`green-ring-en-tap.txt`、a2efb56a）
- 確かめていない事: 英語の図の字の画面の大きさ（次の直し）
- マージ後の書き戻し: Issue は立てていない
