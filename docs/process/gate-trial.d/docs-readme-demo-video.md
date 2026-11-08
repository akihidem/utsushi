## README の頭にデモ動画のリンクを足す（型紙の担当、docs/readme-demo-video、11-08）

- 目的: 提出の床が README の頭の 30 行を見る。窓口が公開で上げた完成版（2 分 56 秒）のリンクを置く（統括の頼み 11-08）
- どうしたか: 3 行の要約の直後に「- デモ動画（2 分 56 秒）: https://www.youtube.com/watch?v=YmPd2FHN8Nw」の 1 行だけ（新しい言い回しを足さない）。頭の試験の並びと、投稿ビデオの項の見張り（「デモ動画」の字はこの 1 行だけ）を合わせた
- 検証ゲート: **済み**。Red: 今の main に新しい頭の試験だけを置くと rc 1（gate-evidence/red-readme-demo-video.txt）。Green: この枝で rc 0（gate-evidence/green-readme-demo-video.txt）
- 確かめていない事: 全部の試験（`./run.sh`）。動画の中身（窓口が上げた物）
