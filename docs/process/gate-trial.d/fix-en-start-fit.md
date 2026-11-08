## 英語の手帖の最初の画面で、幅 320×568 の「はじめる」を画面に入れる（README の担当、fix/en-start-fit、11-08）

- 目的: 英語の頁の手帖の最初の画面で、幅 320×568 の御来迎と虎の「はじめる」（Start）を最初の画面に入れる（統括の頼み 11-08）
- なぜか: 「はじめる」の下の端が 577px（画面の 9px 外）。測ると、効いていたのは「はじめる」の上の声の断り（幅 273px・13px の字で 3 行）だけで、「のこせる」の 1 行は「はじめる」の下にあり位置に効かない（その行を隠しても 577px のまま、断りを隠すと 512px）
- どうしたか: 声の断りの英語を、言葉の決めの内で短くして 2 行にした（この機械で字にする形: "“Speak” turns your voice into text on this device."／ブラウザで字にする形: "“Speak” uses your browser. Its maker may get your voice."／名前: "Please don’t say your name."）。どちらが出るかは機械で替わるので、両方で 2 行。英語の頁では断りの 2 つの文の間に空白を置いた（要素の間に空白が無く "device.Please" とくっついていた。日本語は替えない）
- 比べた案: 断りの行の高さや余白を詰める案は、字の大きさの決め（12px 以上）の内でも、ほかの幅の頁の見た目が替わるので採らない。日本語の文（採られた文のまま）は替えない
- ゴールの要件: tests/test_en_start_fit.py（英語の頁の手帖の最初の画面で、幅 320×568 の御来迎と虎の「はじめる」が画面の中・断りの 2 つの形とも・文の間に空白）
- 検証ゲート: **済み**。Red: 直す前で rc 1（gate-evidence/red-en-start-fit.txt・577px）。Green: rc 0（gate-evidence/green-en-start-fit.txt・555px）
- エビデンスゲート: test_en_terms・test_en_all・test_en・test_techo_step・test_landscape_fit・test_hanasu・test_mic_seen・test_tap_size・test_easy_all・test_ledger が rc 0
- マージ後の書き戻し: Issue は立てていない
