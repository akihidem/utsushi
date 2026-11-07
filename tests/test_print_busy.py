"""紙を作る釦は、押した時に形が変わって押せなくなる。JS が無くても今までどおり刷れる（#301）。

なぜ: 紙を作るのに数秒かかり、その間は釦が何も変わらなかった。もう一度押す人が出て、送信が 2 回出ていた。
押した時の動きはブラウザが要る。./run.sh はブラウザなしで動く決まりなので、ここでは頁の字と JS なしの送信を見る。
動きそのものは実物のブラウザで測った（gate-evidence/green-print-busy-browser.txt）。
"""
import os
import re
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import hypotheses  # noqa: E402
from api import config  # noqa: E402
from web import think_sheet  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
BUSY = " data-busy"
# 押した時に釦に出す字（本人の決定 11-05）。一字も変えない。
ADOPTED_JA, ADOPTED_EN = "作っています…", "Making…"
# 紙を作る送信。記録や説明の送信は速く、押せなくすると書き直す道を狭めるので、印を付けない。
SHEET = re.compile(rf"/toy/{G}/(print|reprint|think-sheet|think-ok)#|/record/R-\d+/next#")
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


# 1 つのブラウザとして動く（記録を残した画面の鍵の cookie を持つ。説明と字を足す口は、その画面にだけ開く）
urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPCookieProcessor()))


def get(path):
    return urllib.request.urlopen(base + path).read().decode()


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    return urllib.request.urlopen(r).status


def forms(page):
    return re.findall(r'<form method="post" action="([^"]+)"[^>]*>(.*?)</form>', page, re.S)


def marked(page):
    """紙を作る釦にだけ印がある事を見て、印のある送信の行き先を返す。
    型紙を玩具ごとに 1 枚にする決定（#332）で札の数が変わるので、札の数や字に結ばない。"""
    made = []
    for action, inner in forms(page):
        assert (BUSY in inner) == bool(SHEET.match(action)), action
        if BUSY in inner:
            assert re.search(r"<button[^>]* data-busy[ >][^<]*</button>", inner), inner
            made.append(action)
    # 形と字を変えるのは押した時だけ
    assert 'data-busy="on"' not in page and f">{ADOPTED_JA}<" not in page and f">{ADOPTED_EN}<" not in page
    return made


def busy_script(page):
    found = [s for s in re.findall(r"<script>.*?</script>", page, re.S) if "button[data-busy]" in s]
    assert len(found) == 1, len(found)  # 2 つあると、1 回の押しに 2 度当たる
    return found[0]


page = get(f"/toy/{G}")
# 刷れるのは今の組のたたき台の紙だけ（J-032）。御来迎の今の組 goraigo-v14 は H-C なので、たたき台を先頭に並べる
ids = [hypotheses.sheet_of(G)["id"]] + [h["id"] for h in hypotheses.load(G)["hypotheses"] if h["id"] != hypotheses.sheet_of(G)["id"]]
assert any("/print#" in a for a in marked(page))

# 押した時の動き: 形を変える・押せなくする・戻る操作と時間切れで元に戻す
js = busy_script(page)
assert "addEventListener('submit'" in js and "dataset.busy='on'" in js and ".disabled=true" in js, js
assert "addEventListener('pageshow'" in js and "setTimeout(" in js, js
# 字は頁の言葉で選び、押した釦だけを替える。戻す時は元の字に戻す
assert f"'{ADOPTED_JA}'" in js and f"'{ADOPTED_EN}'" in js and "documentElement.lang" in js, js
assert '<html lang="ja">' in page and "b.textContent=word" in js and "b.textContent=b.dataset.was" in js, js
# 読み上げの道具にも待っている事を伝える
assert "setAttribute('aria-busy','true')" in js and "removeAttribute('aria-busy')" in js, js
# 押した釦だけ輪が回る。動きを減らす設定では回さない
assert "button[data-busy]:disabled{" in page and "button[data-busy=on]::after{" in page
# 押した釦の字は読ませる字なので薄くしない（白の皮は 0.7 だと字と地の比が 3.58 で、4.5 に届かない）
assert page.index("button[data-busy]:disabled{") < page.index("button[data-busy=on]:disabled{opacity:1}")
assert "@media (prefers-reduced-motion:reduce){button[data-busy=on]::after{animation:none}}" in page

# JS なしの送信は今までどおり刷れる。押した後の頁で釦は元の形に戻っている
assert post(f"/toy/{G}/print", {"hypothesis": ids[0]}) == 200
assert (out_dir(G) / f"{ids[0]}_v1.pdf").exists()
assert any("/print#" in a for a in marked(get(f"/toy/{G}")))

# 話した考えから紙を作る釦と、「この紙にする」の釦
page = get(f"/toy/{G}")
assert any("/think-sheet#" in a for a in marked(page))
# 考えから紙を作る釦は Claude を呼ぶ。呼び出しの上限より先に押せるように戻ると、費用のかかる呼び出しが 2 回走る
wait = int(re.search(r'data-busy-for="(\d+)"', page).group(1))
assert wait > config.RUN_TIME_LIMIT["words"], wait
assert "b.dataset.busyFor" in busy_script(page)
check = think_sheet._status(G, {"status": "pending_human", "token": "t", "how_it_moves": "下から押す", "result": {"fits": False, "not_fit": []}})
assert re.search(r"<button[^>]* data-busy>[^<]+</button>", check) and "/think-ok#" in check, check

# 次の版の紙を作る釦
assert post(f"/toy/{G}/record", {"hypothesis": ids[0], "result": "動いた"}) == 200
assert post("/record/R-0001/explain", {"text": "折りが固くて戻る", "next_idea": "厚さを変える", "by": "大人"}) == 200
assert any("/next#" in a for a in marked(get(f"/toy/{G}")))

# 紙の無い版を作り直す釦。押すたびに確定の記録が 1 件増えるので、2 回送ると確定も増えていた
form = {"interpretation": "折りが固い", "param": "paper_thickness", "to": "0.2", "why": "開きを見る", "by": "大人"}
assert post("/record/R-0001/next", form) == 200
for gone in out_dir(G).glob(f"{ids[0]}_v2*"):
    gone.unlink()
assert any("/reprint#" in a for a in marked(get(f"/toy/{G}?see={ids[0]}")))

# 英語の頁の釦も同じ。字を選ぶ言葉は頁の lang から読む
page = get(f"/en/toy/{G}")
assert '<html lang="en">' in page
assert re.search(r"<button[^>]* data-busy>[^<]+</button>", page)
busy_script(page)

print("ok")
