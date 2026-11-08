## 安全の事項 3 への対応: AI の費用を呼ぶ前に予約し、同時に呼んでも上限を越えない（修正の担当、fix/s03-budget-hold、11-08 夕）

- 目的: 本人の指示（11-08）の安全の事項 3「AI の予算上限が同時実行で超過する」。本人の条件「サイトの機能は維持した状態で、見た目、挙動は変えずに、セキュリティの事項にだけ対応する」
- どうしたか: `api.budget.check` は台帳の錠（台帳の横の .lock・flock）の中で、済んだ額・予約中の額・この 1 回の最大の見込み額を足して見て、通れば最大の見込み額を予約する（台帳の横の .holds.json）。`add` は錠の中で実費を書いて予約を消す。呼べなかった時は `release` で返す（手順の質問・作業の頁の聞く口・観察・区切りの読み・輪の 5 か所）。返し忘れた予約は 15 分で数えない。記録の後の次の版（next）と AI の口（ai-interpret・ai-observe）を、同じ相手からの書き込みの数の上限に入れた
- ゴールの要件: tests/test_budget_hold.py（同じプロセスの 4 本と別のプロセスの 4 本が同時に check しても、通るのは上限の内の 1 本で、精算の後の額が上限を越えない・精算で予約が消える・API の失敗で予約が返る・古い予約は数えない・next と AI の口が数の上限に入る）
- 検証ゲート: **済み**。Red: 今の main（7f6c06e5）の木に新しい試験だけを置いて rc 1（同時の 4 本が全部通った。`docs/process/gate-evidence/red-budget-hold.txt`）。Green: rc 0（`green-budget-hold.txt`）。前の作りに無い名を試験の片付けが呼んで、振る舞いを見る前に落ちた最初の Red は残していない（片付けを直してから取り直した）
- エビデンスゲート: test_agent_sdk・test_ai_feedback・test_api_review_fixes・test_ask・test_ask_floor・test_budget_after_period・test_budget_notes_i18n・test_budget_one_ledger・test_call_timeouts・test_failure_log・test_kasane_ask・test_loop1_words・test_words・test_words_review・test_write_limit・test_public_open・test_demo_walk・test_min_python・test_loop1_round が rc 0
- まだの所: 事項 3 の「AI 呼び出しの同時数・利用者別回数・待ち行列の上限」のうち、同時数と待ち行列の全体の上限は入れていない（予約で額は越えない。回数は口ごとの止めと書き込みの数の止め）。提供元の利用上限の設定は置き方の話
- マージ後の書き戻し: Issue は立てていない
