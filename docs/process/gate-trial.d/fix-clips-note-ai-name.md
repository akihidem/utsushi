## clips.py の注の字を、名の無い AI の断りの見張りに当たらない形に直す（UX の担当、fix/clips-note-ai-name、11-08）

- 目的: #682 で足した web/clips.py の頭の注「開かない時は OPEN_WAIT の後に断り、送る側は…」が、test_ai_name の名の無い日本語の断りの形（「AI」の後 16 字の内に「送」）に当たり、main で rc 1 になった。当たったのは「OPEN_WAIT」の中の「AI」（AI の断りの文ではない）
- どうしたか: 注を 2 つの文に分けて言い直した（「開かない時は、待つ秒（OPEN_WAIT）を過ぎたら断る。送る側は、それを送れなかった事として扱う（CLIP_FAIL）。」）。意味と code は替えていない
- 失敗と原因: #682 の関わる試験に、src/web の全部の字を見る test_ai_name を入れていなかった（注を足す PR でも、全体を見る見張りを回す）
- 検証ゲート: Red: main 8e8eacf8 で rc 1（gate-evidence/red-clips-note-ai-name.txt）。Green: gate-evidence/green-clips-note-ai-name.txt。test_clips_client・test_reader_words・test_gate_evidence・test_gate_trial_merge・test_frozen_manifest も rc 0
