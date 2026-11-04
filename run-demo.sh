#!/bin/bash
# run-demo.sh — デモの一周（選ぶ → 型紙 → 作る → 質問 → 上げる → フィードバック → 次の版）を、パソコン・iPad・iPhone の
# どれからでも開ける形で立てる（本人の決定 A、11-04「AWS でトンネルを立ててよい。合言葉付きのリンクで、3台がどの網でも開ける形で」）。
# なぜトンネルか: 3 台が同じ網にいるとは限らず、iPhone の音声認識は https でないと動かないため。cloudflared の一時の名前（https）で出す。
# なぜ合言葉か: 一時の名前でも URL を知れば誰でも開ける。合言葉付きのリンクを知る人だけが入れる（play_server の _gate）。
# なぜ別の置き場か: デモで上げた物と予想を、本物の記録（data/）と混ぜないため。置き場は out/demo-data（git の外）。
# 使い方: ./run-demo.sh            前回の置き場を続けて使う
#         ./run-demo.sh --fresh    置き場を空にして始める
# 止める: Ctrl+C（サーバとトンネルを両方止める）。リンクは止めるたびに変わる。
set -u
cd "$(dirname "$0")" || exit 4
PORT=${DEMO_PORT:-8767}
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
OMOCHAE_DATA="$PWD/out/demo-data" PYTHONPATH=src .venv/bin/python -m web.play_server "$PORT" --public-key-file out/demo-key > out/demo-server.log 2>&1 &
SRV=$!
cloudflared tunnel --no-autoupdate --protocol http2 --url "http://127.0.0.1:$PORT" > out/demo-tunnel.log 2>&1 &
TUN=$!
trap 'kill $SRV $TUN 2>/dev/null' EXIT INT TERM
URL=""
for _ in $(seq 60); do
  URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" out/demo-tunnel.log | head -1)
  [ -n "$URL" ] && break
  sleep 1
done
[ -n "$URL" ] || { echo "トンネルの名前が出ませんでした（out/demo-tunnel.log）" >&2; exit 4; }
echo "$URL/?k=$(cat out/demo-key)" > out/demo-url
echo "外の機器から開くリンク（合言葉付き）は out/demo-url にあります。渡す時はこのリンクだけを渡す"
wait $SRV
