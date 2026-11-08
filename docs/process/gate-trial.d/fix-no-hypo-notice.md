## 無い仮説の断りから、内部の番号を外す（直しの担当、fix/no-hypo-notice、11-08 昼）

- 目的: 統括の決め（11-08）。頼まれた仮説が無い時の 422 の断り「仮説 {hid} は無い」（`src/web/play_server.py` の 3 か所: 記録を残す・刷る・考えを話す）が、内部の番号（H-A など）をそのまま出していた。印（A・C）と番号を学ぶ人に出さない決め（本人の答え 11-08「そろえる。」）に外れる（別の目の気づき）
- どうしたか: 断りの字を 1 か所の定数 NO_HYPOTHESIS「その仮説は見つかりません。頁を開き直してください。」（統括の決めの向き・新しい字は本人の確かめ待ち）にし、3 か所で使う。英語の表に 1 行（That guess could not be found. Please open the page again.・英語の見直しの言葉の決め「仮説は guess」）、やさしい日本語は `data/i18n/yasashii.d/no-hypo.json`
- ゴールの要件: 無い仮説を頼んだ時の断りに内部の番号が出ず、新しい字が出る
- 検証ゲート: Red: 今の main cbb9c8c8 の木に直した `tests/test_reply_visible.py` を当てて rc 1（`docs/process/gate-evidence/red-no-hypo-notice.txt`。「仮説 H-ZZ は無い」）
- 確かめていない事: 新しい字（本人の確かめ待ち）
- マージ後の書き戻し: Issue は立てていない
