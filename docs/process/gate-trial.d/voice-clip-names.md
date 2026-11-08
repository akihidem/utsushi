## 押した時だけ録る声とカメラの区切りの server 側（voice_text の t・k の名と掃除）（声の担当、voice/clip-names、11-08）

- 目的: 本人の言葉（11-08）「声も送って解析に使う形にする。カメラの映像は、押した時の短い区切りだけ。」と窓口の決め「声とカメラそれぞれ 5 つまで」を受ける置き場と掃除を、受け口の枝（UX の担当）より先に作る。72 時間（345）と「全部残していいことにしたい。」（349）は #599 の決まりのまま
- なぜか: 設計（grove の state/voice-camera-send-20261108.md の 4 節・別の目の確かめ済み）で、#599 の pending は voice と m の名だけを拾い、音の無いカメラの区切りは 72 時間を過ぎても消えなかった。UX の担当と分け、server 側（omochae.voice_text と techo_site.media_bytes）をこの枝で作る（境目の名と引数は UX の担当の案のまま・設計は grove の state/voice-clip-names-design-20261108.md）
- どうしたか: put_voice_clip（webm・mp4 の声を voice/t<n>.mka へ・元の形は置かない）・put_cam_clip（voice/k<n>.<webm|mp4>・絵の流れだけ・音と撮影の情報を落とす）・clips_waiting・clip_wait・clip_done（読み終えた印 k<n>.done.json）・sweep_clips（72 時間で読まずに消し、k<n>.dropped.json に why・at・wait）。5 つは記録ごとの通しの数（字・印が番号を持ち続ける）。pending に t<n> を入れた。Worker と video_up の掃除が sweep_clips も回す。media_bytes に k を足した。一覧（list）に区切りの行を足した
- ゴールの要件: tests/test_voice_clips.py の 9 つ（頭の注のとおり）
- 検証ゲート: **済み**。Red: 今の main（82dac852）の木で rc 1（put_voice_clip が無い。`docs/process/gate-evidence/red-voice-clips.txt`）。Green: rc 0（`green-voice-clips.txt`）
- エビデンスゲート: 写しの木で、Worker の掃除から sweep_clips を外す・空いた番号を音と区切りのファイルだけで数える・カメラの区切りの音を残す、の 3 通りで rc 1。関わる試験 12 本（test_voice_text・test_video_up・test_media_strip・test_photo_owner_only・test_public_open・test_engine_bundle・test_techo_site・test_made_records・test_min_python・test_ledger・test_frozen_manifest・test_gate_evidence）が rc 0
- 確かめていない事: 本物の端末が録った webm・mp4（試験は ffmpeg で作った作り物）。受け口から呼ぶ所は UX の担当の枝。断りの字は受け口へ返す字で、利用者に見せるかは受け口の枝が決める（見せるなら本人の確かめ）
- マージ後の書き戻し: Issue は立てていない
