"""組み立ての 3D は、開いた時に 1 回だけ、動き方を見せる手順の手前まで続けて動かす（本人の答え 11-07・夕方のレビューの Q6）。

なぜ: 夕方のレビューで「釦を押さないと組み立て方が分からない」と言われ、本人が「開いた時に 1 回動かして見せる」と答えた。扇が開く所など、
動き方を見せる手順は、試す前に見せない（J-013・窓口の決め 11-07「扇が開く所は動かさない」）。動かすのは玩具の頁と組み立ての頁だけで、
作業の頁（重ねる頁・作りながら見る頁）は声と釦で 1 手ずつ送るので動かさない。動きを減らす設定の人も動かさない。
頁の JS は ./run.sh で動かせない（ブラウザなし）ので、ここでは頁に渡る印と、止める手順の決め方を Python の側で見る。
本物のブラウザでの長さ（約 20 秒）と止まる手順は、関門の帳面の節に測った値を残す。
"""
import re
import threading
import urllib.request

from omochae import assembly
from web import hmd, kumitate, play_server

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"  # 御来迎・虎


def tour_of(html):
    m = re.search(r"const TOUR=(\d),", html)
    return m and m.group(1)


# 1. 動かす印: 玩具の頁と組み立ての頁は 1、作業の頁（重ねる頁）と既定の block は 0。差し替えの印が残らない
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
toy_page = urllib.request.urlopen(f"{base}/toy/{G}").read().decode()
server.shutdown()
assert tour_of(toy_page) == "1", "玩具の頁の頭の立体は、開いた時に動かす"
assert tour_of(kumitate.page(G)) == "1", "組み立ての頁は、開いた時に動かす"
assert tour_of(kumitate.block(G)) == "0", "block の既定は動かさない（作りながら見る頁など、明示しない呼び手は動かさない）"
# 作業の頁（web.hmd）は 11-08 から 3D を出さない（本人 11-08「3D 重ねずに、質問もできるだけにしよう。」）。前はここで、開いても動かさない事を見ていた
assert "__TOUR" not in hmd.page(G) and 'id="rt-stage"' not in hmd.page(G), "作業の頁に 3D が残っている"
for html in (toy_page, kumitate.page(G), kumitate.block(G)):
    assert "__TOUR" not in html, "差し替えの印が残っている"

# 2. 頁の JS の決まり: 画面に入った時に 1 回（IntersectionObserver・disconnect）、動きを減らす設定の人は動かさない、長さの上限は TOUR_MS、
#    動き方を見せる手順まで動かすかは TOUR_SHOWS_MOVE（窓口の決めで動かさない）
script = kumitate.block(G, tour=True)
assert "if(TOUR&&!still&&'IntersectionObserver' in window)" in script and "io.disconnect()" in script
assert kumitate.TOUR_SHOWS_MOVE is False and "UNTIL=false||MOVE<1?L:MOVE-1" in script, "扇が開く所は動かさない（窓口の決め 11-07）"
assert f"{kumitate.TOUR_MS}-250*UNTIL" in script and kumitate.TOUR_MS == 20000
assert "const quit=()=>" in script, "見る人が押したら、自動の動きはやめる"


# 3. 止める手順: 頁の JS と同じ決め方（形に open・x・p を持つ最初の手順の手前）を Python でも計算し、組み立て終えた形で止まる事を見る
def until(sid):
    frames = kumitate.frames_of(assembly.assemble(sid))
    move = next((k for k, f in enumerate(frames) if any(("open" in q) or ("x" in q) or ("p" in q) for q in f["q"])), -1)
    return frames, (len(frames) - 1 if move < 1 else move - 1)


frames, stop = until(G)
assert stop == 15 and "外筒の下の口に入" in frames[stop]["t"], (stop, frames[stop]["t"])  # 18 手順の 16 番目。次の 17 番目で扇が開く
assert "押し上げる" in frames[stop + 1]["t"] and "扇" in frames[stop + 1]["t"], frames[stop + 1]["t"]
frames, stop = until(T)
assert stop == len(frames) - 2 and "尾" in frames[stop]["t"], (stop, frames[stop]["t"])  # 12 手順の 12 番目（尾を貼る）。次はできあがり
for sid in (G, T):
    frames, stop = until(sid)
    assert not any(("open" in q) or ("x" in q) or ("p" in q) for f in frames[:stop + 1] for q in f["q"]), (sid, "止める前に動き方を見せる手順がある")
print("ok: 組み立ての 3D は、玩具の頁と組み立ての頁でだけ、開いた時に 1 回、組み立て終えた形まで動かす")
