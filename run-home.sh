#!/bin/bash
# run-home.sh — 本番想定で、家のパソコンで utsushi を動かす入口（本人の「本番想定して動かすところまで」、11-04）。
# なぜ 1 本にまとめるか: 環境の確かめ・鍵の有無・データの置き場・家の網に開く、を毎回同じ順で行い、打ち間違いを減らすため。
# 使い方: ./run-home.sh          手元だけで開く（白の展示のサイト、8766）
#         ./run-home.sh --lan    家の網に開く（iPhone から手帖を使う。本人の決定 U-36）
#         ./run-home.sh 8768 --look zine   黒のジンのサイトを別に立てる（皮ごとに 1 サイト。本人の決定 11-05 朝）。2 つ同時に立てる時は
#                                          同じ data/ を見るので、記録は片方ずつ書く
# 鍵の値は読まない。置かれているかだけを数で見る（無ければ、よくある言葉の答えだけで動く）。
set -u
cd "$(dirname "$0")" || exit 4
./init.sh || exit 4
# 原図の写し（切り出し）は git の外なので、足りない分を起動のたびに取る（国立国会図書館、PDM。出典の記録の URL から）。
# なぜ毎回か: 前は最初の 1 枚が在ると残りを取らず、38 種が字だけで出ていた（本人「図がないおもちゃは図を入れて」、11-05）。
PYTHONPATH=src .venv/bin/python -m omochae.ingest images || echo "写しの一部を取り込めませんでした。その玩具は字だけで動きます"
keyfile=".env"
if [ -f "$keyfile" ] && [ "$(grep -c '^ANTHROPIC_API_KEY=.' "$keyfile")" = "1" ]; then
  echo "鍵: 置かれている（Claude の答え・読み・観察が動きます）"
else
  echo "鍵: 置かれていない（よくある言葉の答え・紙・記録・ギャラリーは動きます）"
fi
mkdir -p data/records data/loop
echo "記録の置き場: data/records と data/loop（git の外。試行の 1 回分だけが repo に入っている）"
exec env PYTHONPATH=src .venv/bin/python -m web.play_server "$@"
