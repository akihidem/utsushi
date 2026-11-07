# やさしい日本語の表の、窓ごとの置き場

- 1 つの窓（分け）が 1 つのファイルを書く: 1.json・2.json・3.json（鍵の一覧は grove の state/yasashii-keys/1.txt〜3.txt）
- 形は data/i18n/yasashii.json と同じ `{"note": "…", "strings": {"鍵": "値", …}}`。鍵は字の順（sorted）に並べる
- web.i18n が yasashii.json と、ここの *.json を名前の順に重ねて読む（同じ鍵は後のファイルが勝つ）。1 つのファイルを並べて書き足すと衝突するので分ける
