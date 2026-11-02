# J-001 型紙の描画は drawsvg → cairosvg にする

- **状態**: 決定（実験 `research/02-render-backends.md` による）
- **比べた案**: drawsvg → cairosvg / SVG の文字列 → cairosvg / reportlab / pycairo
- **捨てた案と理由**:
  - reportlab: この字の形式を埋め込めず、実験で失敗した。字を替えると原画の佇まいと合わせる選択肢が減る。
  - pycairo: 開発用の headers が要り、クリーンな機械での導入が重くなる。
  - 文字列の SVG: 動くが、属性の書き間違いや文字のエスケープを自分で持つことになる。速さの差は 1 枚あたり 1 秒未満で効かない。
- **決めた理由**: 字が取り出せて A4 の大きさが正確で、導入が pip だけで済む。
- **注意**: cairosvg は LGPL-3。コードを写さず依存として使い、README の出典・ライセンスに書く。
