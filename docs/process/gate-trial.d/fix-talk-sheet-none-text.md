## 作り直しの口で、字を残した後の止めも口の字にそろえ、字の欄の下にキーボードのマイクの 1 行を足す（Issue 対応の担当、fix/talk-sheet-none-text、11-08）

- 目的: 型紙を印刷する の「Claude に話して型紙を作り直す」口の字を、残りの 1 つの止めでもこの口の字にそろえる
- なぜか: #721 の別の目の気づき（11-08・統括を通して）。字を残した後の止め（残した考えが選べない・頼み済みの案の鍵が閉じている時など）で、request が前の口の字（think_sheet.NONE「先に、考えを話すか書いて「残す」を押してください。」）を返し、この口にそのまま出た
- どうしたらいいか: think-talk から頼んだ時に request が NONE を返したら、この口の TALK_NO_SCREEN（本人の答え「4つともこの字でよい」の字）にする。部品の節（think_sheet.section）と think-sheet の受け口は前の字のまま
- ゴールの要件: `tests/test_talk_sheet_window.py`（字を残した後の止めでも TALK_NO_SCREEN が出て NONE が出ない・W-番号を作らない）
- 検証ゲート: **済み**。Red は `docs/process/gate-evidence/red-talk-sheet-none-text.txt`（今の main a6c7c232 で NONE が出て rc 1）
- エビデンスゲート: **済み**。Green は `docs/process/gate-evidence/green-talk-sheet-none-text.txt`
