## 呼び名を「ワークショップの型紙レビュー」にそろえ、構成の表の「正はエンジンの側」を事実の文にする（直しの線、fix/review-name、11-08）

- 目的: utsushi の側の呼び名を、写したエンジンと同じ字にする。構成の表の engine/ の行の書き方を、今の事実に合わせる
- なぜか: エンジンは制作者の言葉（2026-11-08）「全てがワークショップです。」で、呼び名「作る前のレビュー」を「ワークショップの型紙レビュー」に替えた。utsushi の src/omochae/ はエンジンの写しから分かれていて、「正はエンジンの側」と合わない（どちらも engine/ の写し直し #637 の別の目の点検で見つかった・統括の頼み）
- どうしたか: 版の歩みの表の kind 2 と line 2（why の text と changed は替えない）・kaizen_versions.REVIEW_NAME・about.py の輪・kaizen_judge.py と engine_bundle.py の注・訳の表（英語 6 鍵・やさしい日本語 4 鍵）・試験 3 か所・構成の表の engine_bundle の行・README の版の歩みの 1 行。構成の表の engine/ の行は、2 つの omochae の数（両方にある 19 のうち違う 14・engine/ にだけ 22・src/omochae/ にだけ 33）と、どちらが何に使われるか（サイトが刷る時は src/omochae/・engine/ は一周の入口と版の台帳）を書いた。あわせて、版の歩みの刷った PDF の出所の表の日時を「1970-01-01（日時を入れない刷りの既定の値）」にした（#678 の別の目の直し）
- 比べた案: 版の歩みの表を写す口で作り直す（写す元の表は git の外にあり、作り直すと why の字まで替わりうる。統括の頼みは呼び名だけ）
- ゴールの要件: 前の呼び名が作り・表・訳の表・README に残らない。utsushi の呼び名が engine/ の中のエンジンの呼び名と同じ。版の歩みの表の why の text と changed が替える前と一字も同じ（のこすの直った例を替えない）
- 検証ゲート: **済み**。Red: src/web/kaizen_versions.py だけを main の物に戻した木で tests/test_review_name.py が rc 1（gate-evidence/red-review-name.txt）。Green: rc 0（green-review-name.txt）。why の字に 1 字足した表でも落ちる
- エビデンスゲート: 関わる試験 71 本（呼び名・訳の表・README・版の歩み・序の頁の輪・src の全体を見る試験）が通る。main を取り込んだ後に README・版の歩み・表の試験 8 本をもう一度回して通る
- マージ後の書き戻し: Issue は立てていない
