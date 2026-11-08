## 安全の事項 5 への対応: 公開の場では、立てた後に鍵が置かれても、どの AI の口も Claude を呼ばない（修正の担当、fix/s05-public-no-ai、11-08 夕）

- 目的: 本人の指示（11-08）の安全の事項 5「公開モードの AI 禁止が起動時の状態に依存する」。本人の条件「サイトの機能は維持した状態で、見た目、挙動は変えずに、セキュリティの事項にだけ対応する」
- どうしたか: 手順の質問の口（/toy/<玩具>/ask と /ask-json・play_server._ask）は、公開の場で ask.answer に allow_ai=False を渡し、鍵の有り無しに関わらず Claude を呼ばない。返す字は鍵が無い時と同じ（語の問いは語の表・仕組みの問いは断り・ほかは鍵が無い時の字）。ほかの AI の口（記録の解釈と観察・話した考えから紙を作る口・作業の頁の聞く口・カメラの区切りの読み）は前から公開の場を見て閉じている
- ゴールの要件: tests/test_public_ai_closed.py（立てた後に鍵が置かれた形を偽の鍵と偽の Claude で作り、公開の場の 6 つの口で Claude を呼ばず、返す字が鍵が無い時のまま・合言葉の場では同じ差し替えで偽の Claude に届く見比べ）
- 検証ゲート: **済み**。Red: 今の main（7f6c06e5）の木に新しい試験だけを置いて rc 1（公開の場の /ask が偽の Claude まで届いた。`docs/process/gate-evidence/red-public-ai-closed.txt`）。Green: rc 0（`green-public-ai-closed-2.txt`。`green-public-ai-closed.txt` は合言葉の場の呼び方を替えていた時の物）
- エビデンスゲート: test_ask・test_public_open・test_call_timeouts・test_demo_walk・test_failure_log・test_ask_floor・test_api_review_fixes・test_reply_visible・test_tsukuru・test_making_log・test_kasane_ask・test_public_links・test_voice_walk・test_budget_after_period が rc 0
- まだの所: 事項 5 の「公開プロセスを分離し、API 鍵を読み取れない権限にする」は置き方（機械と権限）の話で、この PR では作りを替えていない
- マージ後の書き戻し: Issue は立てていない
