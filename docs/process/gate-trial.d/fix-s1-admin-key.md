## 安全の事項 1 の締め前の手当て: 管理の合言葉（UX の担当、fix/s1-admin-key、11-08）

- 目的: 共有の合言葉を知る人は、作る側の頁を読み、次の版を採る口と AI の口まで使えた（安全の第 2 回の確かめで残った所・本人の頼み 11-08）。締め前の小さな手当てとして、管理の口を別の管理の合言葉で分けられるようにする。設定が無い時は機能・見た目・挙動を替えない
- どうしたか: web/play_server.py。serve が、設定のファイル（環境変数 OMOCHAE_ADMIN_KEY_FILE が指す・16 字以上）を読んで server.admin_key に持つ（無い・読めない・短い時は None）。設定がある時だけ:
  - 門の頭で ?a=<管理の合言葉> を 1 回だけ受け、管理の cookie（utsushi_a・HttpOnly・7 日）に移して URL から消す（今の合言葉の ?k= と同じ形の別の入口・合言葉の門の無い手元の場でも）。管理の cookie は合言葉の門も通す
  - _admin_refuse が、管理の cookie の無い画面の管理の口（/loop・/loop/<玩具>・/loop/ayumi・/record/<番号>/next・ai-interpret・ai-observe）を 403 にする（断りの字は前からの「受け付けられません」）
- 試験 tests/test_admin_key.py: 設定あり＝合言葉だけの画面と手元の場は 403・?a= の入口で cookie に移り URL から消える・違う値では入れない・管理の cookie で通る・管理の口の外は今のまま／設定なし＝合言葉の画面と手元の場は今のまま
- 検証ゲート: Red: main 3b0da3c0 に試験だけを置くと rc 1（gate-evidence/red-admin-key.txt・管理の合言葉の作りが無い）。Green: gate-evidence/green-admin-key.txt。test_shiori_role・test_shiori_open・test_public_gate・test_public_open・test_play_server・test_kaizen・test_loop・test_loop1_next・test_ai_name・test_frozen_manifest・test_gate_trial_merge・test_gate_evidence・test_ledger も rc 0
- まだの所: 管理の合言葉の設定のファイルを置くかは運用の決め（置かなければ今のまま）。進行者の役（参加者と管理者の間）は分けていない。管理の合言葉のサーバ側の期限と人ごとの失効は無い
