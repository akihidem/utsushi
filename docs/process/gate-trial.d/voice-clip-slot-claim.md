## 声とカメラの区切りが同時に届いても、同じ番号を取って前の区切りを上書きしない（声の担当、voice/clip-slot-claim、11-08 昼）

- 目的: #642 の確かめの気づき（11-08）「_free_slot には錠が無く、同時に 2 つ届くと同じ番号を取りうる」を直す。同じ番号を取ると、後の区切りが前の区切りを上書きし（声は ffmpeg の -y・カメラは O_TRUNC）、前の声か映像が字にならずに消える
- どうしたか: 区切りは置き場の中の一時のファイル（.tmp- の名・0600）に書き、名は `_claim` が os.link で付ける（名が在れば落ちる）。落ちたら空いた番号を見直す（1 度落ちるたびに番号が 1 つ埋まるので、CLIP_MAX 回で終わる）。錠を持たないので、別の作業列や別のサーバの間でも効く。一時のファイルは置いた後と断った時に消し、途中で止まって残った物は sweep_clips が 72 時間で消す
- ゴールの要件: tests/test_voice_clip_race.py の 3 つ（番号を見る所が 1 度だけ古い答えを返しても、声もカメラも前の区切りを上書きせず次の番号に置く・一時のファイルが残らない・上限は今のまま・古い一時のファイルは掃除が消す）
- 検証ゲート: **済み**。Red: 今の main（21583c61）の木で rc 1（同じ番号の t1.mka に置いた。`docs/process/gate-evidence/red-voice-clip-race.txt`）。Green: rc 0（`green-voice-clip-race.txt`）
- エビデンスゲート: 関わる試験 13 本（test_voice_clips・test_voice_text・test_video_up・test_techo_site・test_media_review・test_public_open・test_engine_bundle・test_media_strip・test_ledger・test_gate_evidence・test_gate_trial_merge・test_frozen_manifest・test_min_python）が rc 0
- 確かめていない事: 本当に 2 つの受け取りを同時に走らせた形（試験は番号を見る所が古い答えを返す形で、間の取り合いを作った）
- マージ後の書き戻し: Issue は立てていない
