# 02 型紙の描画の下回りを実験で比べる

**事前メモとの関係**: 事前メモは drawsvg と cairosvg を挙げていた。それを前提にせず、同じ小さな頁（日本語の字・出典 ID・破線）を 4 通りで作って比べた。

見るのは、A4 の大きさになるか、刷り込んだ字が `pdftotext` で取り出せるか（出典の印を機械で検査する前提）。

| 方式 | 結果 | 字の取り出し | 頁の大きさ | 時間 |
|---|---|---|---|---|
| drawsvg → cairosvg | 通る | 取れる | 595.276×841.89pt | 0.26s |
| SVG を文字列で → cairosvg | 通る | 取れる | 595.276×841.89pt | 0.04s |
| reportlab | 失敗 | — | — | — |
| pycairo | 導入できず | — | — | — |

- reportlab の失敗: `TTFError: ... postscript outlines are not supported`。この機械の Noto Serif CJK は CFF の輪郭なので埋め込めない。
- pycairo の失敗: ビルドに cairo の開発用の headers が要る（`Dependency "cairo" not found`）。使い手の機械にも同じ物を求めることになる。
- drawsvg と文字列は同じ PDF の大きさになった。0.22s の差は drawsvg の読み込みが大半と見られる【未測定】。

時間の数字は 1 回だけの測定で、順序の目安にしかならない。判断は [J-001](../decisions/J001-render-backend.md)。
