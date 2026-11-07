## 手帖の鍵の「しおり」の台帳（UX の担当、ux/shiori-ledger、11-08）

- 目的: 本人の決め 11-08（手帖の鍵は「しおり」・「しおりに書いてある絵を押す」・しおりそのものが鍵の形で「この形でよい」・QR の行き先は「決まった番地を用意する」・QR の見た目は「A 朱の落款枠に朱」）。統括の段取り「番地が無くても作れる所（台帳・紙の版の形・試験）を、番地を差し込める形で先に進めてよい」の 1 つ目
- どうしたか: src/omochae/shiori.py。設計は grove の state/techo-card-20261108/README.md の 2″・2‴・6（別の目の検品 3 回）。決まった番地は設定の値 OMOCHAE_SHIORI_BASE で渡す（無い・https でない・一時のトンネルの番地の時は作らない）
- 検証ゲート: **済み**。Red: main の頭 80b1395f に新しい試験 tests/test_shiori.py だけを置くと rc 1（gate-evidence/red-shiori-ledger.txt）。Green: gate-evidence/green-shiori-ledger.txt
- 確かめていない事: 開く道・紙・進め役の道（決まった番地の後の PR）。止めの数の重さ（教室で使った時）
