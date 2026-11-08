## English の頭の試験で、数える前に head の meta を除く（直しの線、fix/en-meta-count、11-08）

- 目的: main（82dac852）で落ちていた tests/test_paper_to_toy.py を通す
- なぜか: #619 で英語の入口 /en の description に en.POSITION を入れたので、同じ字が head と本文の 2 回になった。この試験は本文の順と回数を見るので、head の meta まで数えて落ちた
- どうしたか: 数える前に <meta> を除く（tests/test_kumitate.py と同じ形）。見る事は前のまま。meta の字は tests/test_page_description.py が見る
- 誤りの記録: #619 で関わる試験を選んだ時に、/en と en.POSITION を見るこの試験を拾えていなかった。今回は description に使った定数を参照する試験を全部拾って回した（15 本）
- 検証ゲート: **済み**。Red: gate-evidence/red-en-meta-count.txt（main の試験の字で rc 1）。Green: gate-evidence/green-en-meta-count.txt
- マージ後の書き戻し: Issue は立てていない
