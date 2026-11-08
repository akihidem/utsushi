## 声を録る釦の注の字を、頁の字の見張りに当たらない形に直す（UX の担当、fix/clips-note-no-soto、11-08）

- 目的: #699 で足した web/clips.py の台本の注「…釦の外で止まった時も…」は頁に入る（台本の中の注）。test_next_form の「の外 が頁に無い」（幅の外の値の断りの字の見張り）に当たり、main で rc 1 になった
- どうしたか: 注を「釦を押さずに止まった時も」に言い直した（意味は同じ・code は替えていない）
- 失敗と原因: 台本の中の注は頁に出るので、頁の字を見る試験に当たる。#699 の関わる試験に test_next_form を入れていなかった
- 検証ゲート: Red: main c63822f3 で test_next_form が rc 1（gate-evidence/red-clips-note-no-soto.txt）。Green: gate-evidence/green-clips-note-no-soto.txt。test_clips_client・test_ai_name・test_reader_words・test_hanasu・test_voice_pause・test_frozen_manifest・test_gate_trial_merge・test_gate_evidence も rc 0
