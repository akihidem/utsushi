## 無い仮説の断りの続き: 記録を残す口と、次の版の断りからも内部の番号を外す（直しの担当、fix/no-hypo-notice-2、11-08 昼）

- 目的: 統括の割り振り（11-08・#685 の別の目の続き）。(1) 記録を残す口（/toy/<印>/record）に無い仮説で送ると、受け口の断り（NO_HYPOTHESIS）を通らず、記録の床の字「仮説 H-ZZ は実在しない」が 3 つの言葉とも訳されずに出た (2) 押し方の違う紙の記録から次の版を作ろうとした時の断り「次の版はたたき台（H-C）にだけ足す」が、たたき台の内部の番号を出した
- どうしたか: (1) 記録を残す口の受け口で、先に仮説の有無を見る（`omochae.records.known_hypothesis`）。無ければ NO_HYPOTHESIS（#685 の字）。(2) 次の版の断りを 1 か所の定数 NEXT_SHEET_ONLY「次の版は、今のたたき台の型紙にだけ足せます。」（新しい字・本人の確かめ待ち）にした（`src/web/play_server.py`）。英語の表に 1 行（The next version can only be added to the current starting template.）、やさしい日本語は `data/i18n/yasashii.d/no-hypo.json` に足した
- 試験: `tests/test_reply_visible.py` に、記録を残す口の断り（日本語・英語・やさしい日本語で、内部の番号と床の字が出ず、NO_HYPOTHESIS の訳が出る）と、前の組（goraigo-v7）の H-C の記録からの次の版の断り（内部の番号が出ず NEXT_SHEET_ONLY）を足した
- 検証ゲート: Red: 今の main の木に直した `tests/test_reply_visible.py` を当てて rc 1（`docs/process/gate-evidence/red-no-hypo-notice-2.txt`。「仮説 H-ZZ は実在しない」）
- 確かめていない事: 新しい字（本人の確かめ待ち）
- マージ後の書き戻し: Issue は立てていない
