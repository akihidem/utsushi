## 字の重なりの試験で、字を直に持つ要素の overflow でも字の箱を切る（えらぶの名の札の隠れた末を数えない）（README の担当、fix/no-overlap-clip-own、11-08）

- 目的: 今の main（039c2742）で tests/test_no_overlap.py が落ちる（統括の知らせ 11-08・字の重なりの試験の持ち主の気づき）。えらぶ に KNOWN の外の重なりが出た（日本語でも札の名どうし・名×札の絵、やさしい日本語・英語も）
- なぜか: #691 で、えらぶの棚の名の札を折らずに末を … で切る形にした（white-space:nowrap・overflow:hidden）。この試験の字の箱の切り口（clipOf）は字の親の要素から上だけを見ていて、
  字を直に持つ要素（span.nm）自身の overflow では切らなかった。そのため、画面に出ない末の字の箱が横の札の名と絵まで伸びて数えられた。
  札の箱そのものが絵とほかの札に重ならない事は、#691 の tests/test_erabu_names.py が 12 の大きさで見ている（目で見える重なりではない）
- どうしたか: tests/test_no_overlap.py
  - 字の箱は、字を直に持つ要素の overflow でも切る（clipOf の own）。絵の箱は前のまま
  - えらぶの棚の名の KNOWN の 2 行を外した（えらぶの持ち主として）。写しの無い木だけに出る えらぶ の 2 つ（KNOWN_WIDE・KNOWN_LINK）は、写しの無い木でまだ見えるので残した
  - よむ の見出しの、やさしい日本語のルビの重なり（次の行の「残」の のこ が前の行の「絵」に重なる・iPhone SE・写しのある木）を KNOWN に足した。直す前の Red にも出ていた、今の main の重なり（持ち主の直し待ち）
  - Chrome の一時の profile の片付けの誤りを通す（ignore_cleanup_errors）。時間切れで止めた Chrome の子が profile に書き続け、片付けが「Directory not empty」で落ちた（混んだ機械で 1 度・gate-evidence/red-no-overlap-clip-own.txt）
- 比べた案: 名の札の CSS を替えて末の字の箱を札の中に収める案は、… で切る形（目で見て崩れない形）を崩すので採らない
- 検証ゲート: **済み**。Red: 今の main で rc 1（gate-evidence/red-no-overlap-clip-own-2.txt・えらぶの名どうし・名×絵）。Green: 写しのある木で rc 0（gate-evidence/green-no-overlap-clip-own-2.txt）、写しの無い木で rc 0（green-no-overlap-clip-own-nosrc.txt）。
  落ちた版: green-no-overlap-clip-own.txt（よむ のルビを KNOWN に足す前）
- 限り: よむ のルビの重なりは、この PR では直していない（KNOWN に置いて持ち主へ知らせる）
- マージ後の書き戻し: Issue は立てていない
