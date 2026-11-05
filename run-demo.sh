#!/bin/bash
# run-demo.sh — デモの一周（選ぶ → 型紙 → 作る → 質問 → 上げる → フィードバック → 次の版）を、パソコン・iPad・iPhone の
# どれからでも開ける形で立てる（本人の決定 A、11-04「AWS でトンネルを立ててよい。合言葉付きのリンクで、3台がどの網でも開ける形で」）。
# なぜトンネルか: 3 台が同じ網にいるとは限らず、iPhone の音声認識は https でないと動かないため。cloudflared の一時の名前（https）で出す。
# なぜ合言葉か: 一時の名前でも URL を知れば誰でも開ける。合言葉付きのリンクを知る人だけが入れる（play_server の _gate）。
# なぜ別の置き場か: デモで上げた物と予想を、本物の記録（data/）と混ぜないため。置き場は out/demo-data（git の外）。
# なぜ開くかを見てから案内するか: サーバやトンネルが立っていないのにリンクを渡すと、撮影の最中や渡した先で初めて気づく（#159）。
#   手元の口と、トンネルの名前越しの両方を合言葉付きで開いて確かめ、開かなければ案内せずにログの末尾を出して 4 で止める。
# 使い方: ./run-demo.sh            前回の置き場と合言葉を続けて使う
#         ./run-demo.sh --fresh    置き場を空にし、合言葉も作り直して始める（前のデモで渡したリンクでは入れない）
# 止める: Ctrl+C（サーバとトンネルを両方止める）。リンクは止めるたびに変わるので、out/demo-url も消す。
# 途中でサーバかトンネルが止まった時は、理由を出して 4 で終わる（片方だけ残して黙らない）。
set -u
cd "$(dirname "$0")" || exit 4
PORT=${DEMO_PORT:-8767}
[ -x .venv/bin/python ] || ./init.sh >/dev/null || exit 4
command -v cloudflared >/dev/null || { echo "cloudflared が無いので外の機器からは開けません" >&2; exit 4; }
check() { PYTHONPATH=src .venv/bin/python -m web.demo_check "$@"; }
# 何より先に見る。塞いでいるのが動いているデモなら、そのリンク・合言葉・置き場に触らずに止めるため。
check --port-free "$PORT" || exit 4
mkdir -p out
rm -f out/demo-url  # 前回が止まり切らずに残したリンクを、今回の物と取り違えない
if [ ! -f out/sources/NDL-1187053-R0000005-L.jpg ]; then
  PYTHONPATH=src .venv/bin/python -m omochae.ingest || echo "原図の写しを取り込めませんでした。図の所は字だけで動きます"
fi
[ "${1:-}" = "--fresh" ] && rm -rf out/demo-data out/demo-key
mkdir -p out/demo-data
umask 077
# 合言葉は手元のファイルにだけ置く（引数・環境変数に出さない）。
[ -s out/demo-key ] || .venv/bin/python -c "import secrets;print(secrets.token_urlsafe(18))" > out/demo-key
OMOCHAE_DATA="$PWD/out/demo-data" PYTHONPATH=src .venv/bin/python -m web.play_server "$PORT" --public-key-file out/demo-key > out/demo-server.log 2>&1 &
SRV=$!
TUN=""
# サーバの終わりまで待つ。すぐ立て直した時に、自分の前の回を「使用中」と読まないため。
trap 'kill $SRV $TUN 2>/dev/null; wait "$SRV" 2>/dev/null; rm -f out/demo-url' EXIT
trap 'exit 0' INT TERM  # 人が止めた時。片づけは EXIT の方でする
alive() { kill -0 "$1" 2>/dev/null; }
give_up() { echo "$1（$2 の末尾）:" >&2; tail -n 20 "$2" >&2; exit 4; }
# 開くまで待つ。つなぐ相手（$4）が止まったら待たない。合言葉はファイルで渡し、画面に出さない。
wait_open() {  # wait_open <URL の頭> <回数> <ログ> <pid> [demo_check の引数]
  local base=$1 tries=$2 log=$3 pid=$4 why=""
  shift 4
  for _ in $(seq "$tries"); do
    alive "$pid" || give_up "止まりました" "$log"
    why=$(check "$base" --key-file out/demo-key "$@" 2>&1) && return 0
    sleep 1
  done
  give_up "$base が開けません: $why" "$log"
}
wait_open "http://127.0.0.1:$PORT" 30 out/demo-server.log "$SRV"
cloudflared tunnel --no-autoupdate --protocol http2 --url "http://127.0.0.1:$PORT" > out/demo-tunnel.log 2>&1 &
TUN=$!
URL=""
for _ in $(seq 60); do
  alive "$TUN" || give_up "トンネルが止まりました" out/demo-tunnel.log
  URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" out/demo-tunnel.log | head -1)
  [ -n "$URL" ] && break
  sleep 1
done
[ -n "$URL" ] || give_up "トンネルの名前が出ませんでした" out/demo-tunnel.log
# 名前が出てから世の中に届くまで少しかかるので、回数を多めに取る。DEMO_TUNNEL_VIA は試験の口（網を使わずに手元へ向ける）。
wait_open "$URL" "${DEMO_TUNNEL_TRIES:-60}" out/demo-tunnel.log "$TUN" ${DEMO_TUNNEL_VIA:+--via "$DEMO_TUNNEL_VIA"}
echo "$URL/?k=$(cat out/demo-key)" > out/demo-url
echo "外の機器から開くリンク（合言葉付き）は out/demo-url にあります。渡す時はこのリンクだけを渡す"
while alive "$SRV" && alive "$TUN"; do sleep 1; done
alive "$SRV" || give_up "サーバが止まりました。リンクはもう開きません" out/demo-server.log
give_up "トンネルが止まりました。リンクはもう開きません" out/demo-tunnel.log
