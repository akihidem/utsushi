## えらぶの札の a に title で全名を足す（… で切れた名を見る道）（README の担当、ux/erabu-name-title、11-08）

- 目的: 統括の頼み（11-08・#691 の別の目の続き）。えらぶの札で名が … で切れる時（英語は 33 のうち 24〜31）、目で全名を見る道が無い
- どうしたか: src/web/toys.py の card で、札の a に title="名" を足した。字は名の字そのもので、新しい字は無い。英語とやさしい日本語の頁では、訳の出口（web.i18n の ATTR）が title も名と同じ字に替える。/toys の棚と、入口の畳みの中の棚（どちらも card）に効く
- ゴールの要件: tests/test_erabu_names.py の 4（札の a の title が、ルビの外の名の字と同じ・白と暗い版・3 つの言葉・12 の大きさ）
- 検証ゲート: **済み**。Red: 今の main（b1261495）で rc 1（gate-evidence/red-erabu-name-title.txt・title が空）。Green: rc 0（gate-evidence/green-erabu-name-title.txt）
- エビデンスゲート: test_toys・test_toys_genre・test_erabu_fold・test_easy_all・test_easy_ruby・test_en_all・test_en_terms・test_public_open・test_toy_foot_ndl・test_tap_size・test_gate_trial_merge・test_frozen_manifest が rc 0
- 限り: title は指を当てても出ない端末がある（iPhone の Safari など）。その時の全名は玩具の頁で読める
- マージ後の書き戻し: Issue は立てていない
