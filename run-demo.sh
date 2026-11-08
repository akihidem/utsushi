#!/bin/bash
# run-demo.sh — デモの一周（選ぶ → 型紙 → 作る → 質問 → 上げる → フィードバック → 次の版）を、パソコン・iPad・iPhone の
# どれからでも開ける形で立てる（本人の決定 A、11-04「AWS でトンネルを立ててよい。合言葉付きのリンクで、3台がどの網でも開ける形で」）。
# なぜトンネルか: 3 台が同じ網にいるとは限らず、iPhone の音声認識は https でないと動かないため。cloudflared の一時の名前（https）で出す。
# なぜ合言葉か: 一時の名前でも URL を知れば誰でも開ける。合言葉付きのリンクを知る人だけが入れる（play_server の _gate）。
# なぜ白の 1 つだけか: 本人の決定（11-06）「ページは白案で統一します。黒案にだけある要素は白案に入れてください」。
#   前は本人の決定（11-05 朝）「日本画かジンで行く。それぞれのデザインのサイトを 2 つ作る」で、白の展示（tenji）と黒のジン（zine）を
#   別の port・別のトンネルで立て、リンクを 2 本出していた。黒の皮の作りは残すが（--look zine で立てれば見られる）、デモでは立てない。
# なぜ置き場が 1 つか: 本人の決定（11-05 朝、カード 083822 の判断 1）「記録は共有。片方で書いた記録がもう片方でも読める形」。まだデモなので仮の形で、
#   2 つのサーバが同じ out/demo-data を読み書きする（記録の印 R-番号は exclusive create で付け直すのでぶつからない）。
# なぜ data/ と別か: デモで上げた物と予想を、本物の記録（data/）と混ぜないため。置き場は out/demo-data（git の外）。
# なぜ開くかを見てから案内するか: サーバやトンネルが立っていないのにリンクを渡すと、撮影の最中や渡した先で初めて気づく（#159）。
#   手元の口と、トンネルの名前越しの両方を、サイトごとに開いて確かめ、開かなければ案内せずにログの末尾を出して 4 で止める。
# 使い方: ./run-demo.sh            前回の置き場と合言葉を続けて使う（合言葉付きのリンク）
#         ./run-demo.sh --fresh    置き場を空にし、合言葉も作り直して始める（前のデモで渡したリンクでは入れない）
#         ./run-demo.sh --open --public-think   合言葉なしで開き、型紙を印刷する の作り直す口だけが Claude を呼べる形（本人の決め 11-08）
#         ./run-demo.sh --open     合言葉なしで、他の人も見られる形に開く（本人の許可 11-05「デモサイト 2 つを他の人でも見れるように公開していいよ」）。
#                                  置き場は別（out/demo-data-open）: 合言葉付きの時に書かれた記録と写真を、開いた場に出さないため。
#                                  開いた場では写真と動画を受けない（誰でも上げられる所に、確かめていない写真を載せない）。
# 止める: Ctrl+C（サーバとトンネルを全部止める）。リンクは止めるたびに変わるので、out/demo-url* も消す。
# 途中でサーバかトンネルが止まった時は、理由を出して 4 で終わる（片方だけ残して黙らない）。
set -u
cd "$(dirname "$0")" || exit 4
# 上げた動画の声を字にする道具（requirements-asr.txt で作る .venv-asr）。在れば渡す（本人の言葉 11-08「全部残していいことにしたい。」）。
# 渡さないと、道具の在る機械でもサーバが受けた時に声を落とす（道具の場所を知らないため）。無い機械では今までどおり受けた時に落とす
if [ -z "${OMOCHAE_ASR_PYTHON:-}" ] && [ -x .venv-asr/bin/python ]; then export OMOCHAE_ASR_PYTHON="$PWD/.venv-asr/bin/python"; fi
PORT=${DEMO_PORT:-8767}          # 白の展示。黒のジンは次の番号
[ -x .venv/bin/python ] || ./init.sh >/dev/null || exit 4
command -v cloudflared >/dev/null || { echo "cloudflared が無いので外の機器からは開けません" >&2; exit 4; }
check() { PYTHONPATH=src .venv/bin/python -m web.demo_check "$@"; }
LOOKS="tenji"  # 白の 1 つだけ（本人の決定 11-06）。黒も立てる時は "tenji zine" に戻す
port_of() { if [ "$1" = zine ]; then echo $((PORT + 1)); else echo "$PORT"; fi; }
# 何より先に、2 つの port を見る。塞いでいるのが動いているデモなら、そのリンク・合言葉・置き場に触らずに止めるため。
for look in $LOOKS; do check --port-free "$(port_of "$look")" || exit 4; done
OPEN=""; DATA=out/demo-data; THINK=""
for a in "$@"; do [ "$a" = "--open" ] && { OPEN=1; DATA=out/demo-data-open; }; done
# --public-think: 合言葉なしの場（--open）で、型紙を印刷する の作り直す口だけが Claude を呼べる形に立てる（本人の決め 11-08「公開のデモにも、
# 本当に動く形で出してください。…この口だけは本人の決めで開けます。他の口は閉じたままにしてください。」）。ほかの AI の口は閉じたまま。
# この印の時だけ、鍵のある所でも開いた場を立てる。鍵を置くのは本人か窓口（このスクリプトは鍵を読まない）
for a in "$@"; do [ "$a" = "--public-think" ] && THINK="--public-think"; done
mkdir -p out
rm -f out/demo-url out/demo-url-tenji out/demo-url-zine  # 前回が止まり切らずに残したリンクを、今回の物と取り違えない
# 原図の写し（切り出し）は git の外なので、足りない分を起動のたびに取る（出典の記録の URL から。網が無ければ字だけで動く）。
# なぜ毎回か: 前は最初の 1 枚が在ると残りを取らず、38 種が字だけで出ていた（本人「図がないおもちゃは図を入れて」、11-05）。DEMO_NO_IMAGES は試験の口（網に出ない）。
[ -n "${DEMO_NO_IMAGES:-}" ] || PYTHONPATH=src .venv/bin/python -m omochae.ingest images || echo "写しの一部を取り込めませんでした。その玩具は字だけで動きます"
for a in "$@"; do [ "$a" = "--fresh" ] && rm -rf "$DATA" out/demo-key; done
mkdir -p "$DATA"
umask 077
# 合言葉は手元のファイルにだけ置く（引数・環境変数に出さない）。
[ -n "$OPEN" ] || [ -s out/demo-key ] || .venv/bin/python -c "import secrets;print(secrets.token_urlsafe(18))" > out/demo-key
SRV=""; TUN=""
# サーバの終わりまで待つ。すぐ立て直した時に、自分の前の回を「使用中」と読まないため。
trap 'kill $SRV $TUN 2>/dev/null; wait $SRV 2>/dev/null; rm -f out/demo-url out/demo-url-tenji out/demo-url-zine' EXIT
trap 'exit 0' INT TERM  # 人が止めた時。片づけは EXIT の方でする
alive() { kill -0 "$1" 2>/dev/null; }
give_up() { echo "$1（$2 の末尾）:" >&2; tail -n 20 "$2" >&2; exit 4; }
# 開くまで待つ。つなぐ相手（$4）が止まったら待たない。合言葉はファイルで渡し、画面に出さない。
wait_open() {  # wait_open <URL の頭> <回数> <ログ> <pid> [demo_check の引数]
  local base=$1 tries=$2 log=$3 pid=$4 why="" how="--key-file out/demo-key"
  shift 4
  [ -z "$OPEN" ] || how="--no-key"
  for _ in $(seq "$tries"); do
    alive "$pid" || give_up "止まりました" "$log"
    # shellcheck disable=SC2086
    why=$(check "$base" $how "$@" 2>&1) && return 0
    sleep 1
  done
  give_up "$base が開けません: $why" "$log"
}
for look in $LOOKS; do
  port=$(port_of "$look")
  if [ -n "$OPEN" ]; then
    OMOCHAE_DATA="$PWD/$DATA" PYTHONPATH=src .venv/bin/python -m web.play_server "$port" --look "$look" --public $THINK > "out/demo-server-$look.log" 2>&1 &
  else
    OMOCHAE_DATA="$PWD/$DATA" PYTHONPATH=src .venv/bin/python -m web.play_server "$port" --look "$look" --public-key-file out/demo-key > "out/demo-server-$look.log" 2>&1 &
  fi
  pid=$!
  SRV="$SRV $pid"
  wait_open "http://127.0.0.1:$port" 30 "out/demo-server-$look.log" "$pid"
done
LINKS=""
for look in $LOOKS; do
  port=$(port_of "$look")
  cloudflared tunnel --no-autoupdate --protocol http2 --url "http://127.0.0.1:$port" > "out/demo-tunnel-$look.log" 2>&1 &
  pid=$!
  TUN="$TUN $pid"
  URL=""
  for _ in $(seq 60); do
    alive "$pid" || give_up "トンネルが止まりました" "out/demo-tunnel-$look.log"
    URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "out/demo-tunnel-$look.log" | head -1)
    [ -n "$URL" ] && break
    sleep 1
  done
  [ -n "$URL" ] || give_up "トンネルの名前が出ませんでした" "out/demo-tunnel-$look.log"
  # 名前が出てから世の中に届くまで少しかかるので、回数を多めに取る。DEMO_TUNNEL_VIA は試験の口（網を使わずに手元へ向ける）。
  wait_open "$URL" "${DEMO_TUNNEL_TRIES:-60}" "out/demo-tunnel-$look.log" "$pid" ${DEMO_TUNNEL_VIA:+--via "$DEMO_TUNNEL_VIA"}
  LINKS="$LINKS $look=$URL"
done
# 2 つとも開くと確かめてから、リンクを置く（片方だけ開く状態で案内しない）。
for pair in $LINKS; do
  look=${pair%%=*}; URL=${pair#*=}
  if [ -n "$OPEN" ]; then echo "$URL/" > "out/demo-url-$look"; else echo "$URL/?k=$(cat out/demo-key)" > "out/demo-url-$look"; fi
done
# 前からの置き場（out/demo-url）は白の展示のリンクを指す。
cp out/demo-url-tenji out/demo-url
echo "外の機器から開くリンクは out/demo-url-tenji（白の展示）にあります（--open の時は合言葉なし）。渡す時はこのリンクだけを渡す"
while :; do
  for pid in $SRV; do alive "$pid" || give_up "サーバが止まりました。リンクはもう開きません" out/demo-server-tenji.log; done
  for pid in $TUN; do alive "$pid" || give_up "トンネルが止まりました。リンクはもう開きません" out/demo-tunnel-tenji.log; done
  sleep 1
done
