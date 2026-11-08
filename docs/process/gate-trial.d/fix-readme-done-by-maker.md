## README の「まだ」を、作る側で行った事とサイトの口のまだに分ける（型紙の担当、fix/readme-done-by-maker、11-08）

- 目的: 本人の言葉 11-08「GitHub の記録の読み、動画の 3 コマは 10 本と 2 本の動画でやったことなので実施済みなのではないか。」「次の手の案も、型紙が版を重ねているので実施済みです。」
- 確かめた事: 動画のコマは作る側の Claude Code が型紙レビューの動画 10 本と虎の一周の動画 2 本から 3 コマずつ計 36 コマを直に見た（grove の state/review-videos-faces-20261108.md・決め 444）。次の版の案は作る側の Claude Code がエンジンの台帳の案 EP-0011〜EP-0049 を作り、エンジンの PR で版に入れた（engine/data/engine/versions.json）。サイトの中の口（observe・propose）は手元の使用記録に呼んだ行が無い（役ごとに ask 1・interpret 1・words 5・generate 12）
- どうしたか: Claude の使い方の表の「まだ」はサイトの口の事として残し、表の下に作る側で行った事の 2 行。まだの事の行も分けた
- 検証ゲート: **済み**。Red: 今の main に新しい頭の試験だけを置くと rc 1（gate-evidence/red-readme-done-by-maker.txt）。Green: この枝で rc 0（gate-evidence/green-readme-done-by-maker.txt）
- 確かめていない事: 全部の試験（`./run.sh`）
