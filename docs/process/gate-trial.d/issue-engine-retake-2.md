## engine/ を、エンジンの main の頭 d204a5a4 に写し直す（直しの線、issue/engine-retake-2、11-08）

- 目的: engine/ の中を、提出の前のエンジンの main の頭に合わせる（エンジンの #150・#152・#153・#154・#155 の後）。README の commit の欄も新しい頭にする
- なぜか: 本人の決め（11-08）「提出の前に写し直す」。#603 で写した頭 26156d35 の後に、エンジンの main に合体が入った。#154 は虎 v8 の手順の順の誤りの直しで、その前に写すと誤りが入るので、3 本（#153・#154・#155）の後に 1 度にした
- どうしたか: #565・#603 と同じ形（本人の決め「(A) 1本にまとめて入れる」）。1 本目で engine/ の木をエンジンの頭 d204a5a4a2d385e0a9fe4c78dd4c010833e58043（2026-11-08 09:47 JST・544 本）と同じにする（git-subtree の印つき）。2 本目で写した後の直し
- 写した後の直し: engine/SECURITY.md を外す（エンジンの SECURITY.md は 26156d35 から替わっていないので、一番上の SECURITY.md の節はそのまま）。engine/README.md のセキュリティの道 2 か所を一番上の SECURITY.md へ。エンジンの #155 で README に頭が入り、utsushi にだけあった頭の 43 文のうち 16 文が字のまま入ったので、utsushi の頭は戻さず（統括の決め）、エンジンの頭に無い 2 文（別の repo で開発して engine/ に一緒にした事・「どっちもハッカソンの審査対象にして欲しい」）だけを概要の 2 段落目の後に足した（前に本人が確かめた字のまま）。一番上の README の commit の欄と、写した後の直しの文を今の形にした
- 写さない物: エンジンの履歴（utsushi には 1 本の commit）。utsushi の src/omochae。data/history/kaizen-history.json は作り直さない（台帳 data/engine/versions.json の題 16 か所が替わったが、表は写す口で作る物で、この PR の外。のこすの直った例 4 つの字は替わらない）
- 秘密の点検（値は出さない）: エンジンの頭の木 377 ファイルに鍵の形 0・写した後の utsushi の木 2205 ファイルに鍵の形 0・提出の点検（grove の submit-scan）で FAIL と WARN 0
- ゴールの要件: engine/ の木が、写したエンジンの頭の木と、写した後の直し（README.md と SECURITY.md）のほかは同じ。README の commit の欄が engine/ を入れた commit の印と同じ。engine/README.md に utsushi の頭の字が 2 回並ばない
- 検証ゲート: **済み**。Red: 1 本目の木で、README の commit の欄が前の頭のままなので tests/test_readme_engine.py が rc 1（gate-evidence/red-engine-retake-2.txt）。Green: 2 本目で rc 0（green-engine-retake-2.txt）
- エビデンスゲート: utsushi の test_readme_engine・test_kaizen_history・test_kaizen_rekishi・test_loop_ayumi・test_engine_inside・test_readme_head・test_reach_words・test_readme_words と、engine/ の中の test_readme_commands（README の命令 28 本）・test_init_python・test_security・test_frozen_manifest が通る。engine/run.sh（engine/ の中の全部）は rc 0（243 本＝凍結の場面 190・試験 53、全部期待どおり）。回している間に、Red の証拠を取るため同じ木を一度 1 本目に戻した（1 本目の engine/ はエンジンの頭と同じ中身で、どちらの形でも通る見込みの物）。この repo の ./run.sh の全部は合体の道に任せる
- 確かめていない事: 写した後にエンジンの main がまた替わった時は、同じ手順（grove の state/engine-recopy-20261108.sh。utsushi の頭の当て直しは今回から要らない）で写し直す
- マージ後の書き戻し: Issue は立てていない。合体は merge の commit で（squash だと印が消え、test_readme_engine が素通りする）
