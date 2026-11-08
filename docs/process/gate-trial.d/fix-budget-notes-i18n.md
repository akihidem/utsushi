## 予算の止めの字を、英語とやさしい日本語の頁で頁の言葉にする（直しの担当、fix/budget-notes-i18n、11-08 午後）

- 目的: 統括の割り振り（11-08・#692 の別の目の気づき・前からの漏れ）。予算の止めの字 3 つ（`src/api/budget.py` の BudgetStop.NOTES）が英語とやさしい日本語の表に無く、英語の頁でも日本語のまま出た。聞く口（/toy/<玩具>/ask-json）も同じ
- どうしたか: (1) 訳の表に、止めの字 3 つと、頁と聞く口に出る「今は AI に聞けません（…）」の形 3 つの鍵を足した（英語は前からの「You cannot ask the AI right now」に続ける形。新しい英語の字は本人の確かめ待ち）。やさしい日本語は `data/i18n/yasashii.d/budget-notes.json`（明日の読みは あした）。(2) 聞く口は JSON で返すので頁の出口の訳を通らない。出す所で頁の言葉に合わせる口 `Handler._say`（`src/web/play_server.py`）を足し、予算の止めの字に通した。日本語の字は替えていない
- 試験: `tests/test_budget_notes_i18n.py`（表にある・頁の出口で訳される・聞く口の JSON が 3 つの言葉で頁の言葉に合う・額とルビの印が出ない）
- 検証ゲート: Red: 今の main b1261495 の木に `tests/test_budget_notes_i18n.py` だけを当てて rc 1（`docs/process/gate-evidence/red-budget-notes-i18n.txt`。英語の表に止めの字が無い）。Green: rc 0（`green-budget-notes-i18n.txt`、44dd2c3c）
- 確かめていない事: 新しい英語の字（本人の確かめ待ち）
- マージ後の書き戻し: Issue は立てていない
