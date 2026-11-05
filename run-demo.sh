#!/bin/bash
# run-demo.sh — デモの一周（選ぶ → 型紙 → 作る → 質問 → 上げる → フィードバック → 次の版）を、パソコン・iPad・iPhone の
# どれからでも開ける形で立てる（本人の決定 A、11-04「AWS でトンネルを立ててよい。合言葉付きのリンクで、3台がどの網でも開ける形で」）。
# なぜトンネルか: 3 台が同じ網にいるとは限らず、iPhone の音声認識は https でないと動かないため。cloudflared の一時の名前（https）で出す。
# なぜ合言葉か: 一時の名前でも URL を知れば誰でも開ける。合言葉付きのリンクを知る人だけが入れる（play_server の _gate）。
# なぜ 2 つ立てるか: 本人の決定（11-05 朝）「日本画かジンで行く。それぞれのデザインのサイトを 2 つ作る」。皮ごとに 1 サイト（--look）で、
#   白の展示（tenji）と黒のジン（zine）を別の port・別のトンネルで立て、リンクを 2 本出す。合言葉は 2 つで同じ。
# なぜ置き場が 1 つか: 本人の決定（11-05 朝、カード 083822 の判断 1）「記録は共有。片方で書いた記録がもう片方でも読める形」。まだデモなので仮の形で、
#   2 つのサーバが同じ out/demo-data を読み書きする（記録の印 R-番号は exclusive create で付け直すのでぶつからない）。
# なぜ data/ と別か: デモで上げた物と予想を、本物の記録（data/）と混ぜないため。置き場は out/demo-data（git の外）。
# 使い方: ./run-demo.sh            前回の置き場を続けて使う
#         ./run-demo.sh --fresh    置き場を空にして始める
# 止める: Ctrl+C（サーバとトンネルを全部止める）。リンクは止めるたびに変わる。
set -u
cd "$(dirname "$0")" || exit 4
PORT=${DEMO_PORT:-8767}          # 白の展示。黒のジンは次の番号
[ -x .venv/bin/python ] || ./init.sh >/dev/null || exit 4
command -v cloudflared >/dev/null || { echo "cloudflared が無いので外の機器からは開けません" >&2; exit 4; }
# 原図の写し（切り出し）は git の外なので、足りない分を起動のたびに取る（出典の記録の URL から。網が無ければ字だけで動く）。
# なぜ毎回か: 前は最初の 1 枚が在ると残りを取らず、38 種が字だけで出ていた（本人「図がないおもちゃは図を入れて」、11-05）。
PYTHONPATH=src .venv/bin/python -m omochae.ingest images || echo "写しの一部を取り込めませんでした。その玩具は字だけで動きます"
[ "${1:-}" = "--fresh" ] && rm -rf out/demo-data
mkdir -p out/demo-data
umask 077
# 合言葉は手元のファイルにだけ置く（引数・環境変数に出さない）。
[ -s out/demo-key ] || .venv/bin/python -c "import secrets;print(secrets.token_urlsafe(18))" > out/demo-key
PIDS=""
trap 'kill $PIDS 2>/dev/null' EXIT INT TERM
for look in tenji zine; do
  port=$PORT; [ "$look" = zine ] && port=$((PORT + 1))
  OMOCHAE_DATA="$PWD/out/demo-data" PYTHONPATH=src .venv/bin/python -m web.play_server "$port" --look "$look" --public-key-file out/demo-key > "out/demo-server-$look.log" 2>&1 &
  PIDS="$PIDS $!"
  cloudflared tunnel --no-autoupdate --protocol http2 --url "http://127.0.0.1:$port" > "out/demo-tunnel-$look.log" 2>&1 &
  PIDS="$PIDS $!"
done
for look in tenji zine; do
  URL=""
  for _ in $(seq 60); do
    URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "out/demo-tunnel-$look.log" | head -1)
    [ -n "$URL" ] && break
    sleep 1
  done
  [ -n "$URL" ] || { echo "トンネルの名前が出ませんでした（out/demo-tunnel-$look.log）" >&2; exit 4; }
  echo "$URL/?k=$(cat out/demo-key)" > "out/demo-url-$look"
done
# 前からの置き場（out/demo-url）は白の展示のリンクを指す。
cp out/demo-url-tenji out/demo-url
echo "外の機器から開くリンク（合言葉付き）は out/demo-url-tenji（白の展示）と out/demo-url-zine（黒のジン）にあります。渡す時はこのリンクだけを渡す"
wait
