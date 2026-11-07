"""同じ案の紙を同時に作っても落ちない。同じ案は 1 回分だけ作り、書き終えてから置き換える（#301）。

なぜ: 同じ名前の紙を同時に書くと、片方が書きかけの PDF を読んで（pdftotext・pdfimages・pdftoppm）500 の頁になった。
型紙を玩具ごとに 1 枚にする決定（#332）で、場では同じ釦に人が集まる。順に作り直すと、最後の人が人数分待つ。
秒数で重なりを作らない（混んだ機械で揺れる）。全部の人が止まったのを見てから放す。
"""
import os
import pathlib
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

import web.play_server as ps  # noqa: E402
from omochae import hypotheses  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台の仮説（次の組は H-C の柄を下から押し上げる形・前の組は H-A。本人の決定 2026-11-06。hypotheses.sheet_id）
GS = hypotheses.sheet_of(G)["id"]
server = ps.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
real_sheet, real_own = hypotheses.print_sheet, hypotheses.print_own


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    # 応答（刷った後に着く玩具の頁・約 670KB）を読み切ってから閉じる。読まずに閉じると、書いている途中の server の糸が BrokenPipe を
    # stderr に書き、試験の終わり（Python の後始末）とぶつかって rc 134（Fatal Python error）で落ちる事があった（11-07 の main で 10 回に 3 回）
    with urllib.request.urlopen(r) as res:
        res.read()
        return res.status


class Hold:
    """紙を作る所で止める。release を押すと then を呼ぶ。"""

    def __init__(self, then):
        self.then = then
        self.release = threading.Event()
        self.guard = threading.Lock()
        self.calls = []
        self.active = 0
        self.most = 0

    def __call__(self, *a, **k):
        with self.guard:
            self.calls.append(a[1])
            self.active += 1
            self.most = max(self.most, self.active)
        self.release.wait()
        try:
            return self.then(*a, **k)
        finally:
            with self.guard:
                self.active -= 1


def together(calls):
    """calls を同時に動かし、全部が止まってから返す。結果は results、例外は raised に入る。"""
    results, raised = [], []

    def run(call):
        try:
            results.append(call())
        except Exception as e:
            raised.append(e)

    threads = [threading.Thread(target=run, args=(c,)) for c in calls]
    for t in threads:
        t.start()
    end = time.time() + 180
    while True:
        # 作る人は Hold の中、待つ人は結果の前で、どちらも threading の wait で止まる
        frames = sys._current_frames()
        if all(t.ident in frames and frames[t.ident].f_code.co_name == "wait" for t in threads):
            return threads, results, raised
        assert time.time() < end, "全部の人が止まらない"
        time.sleep(0.01)


def finish(threads, hold):
    hold.release.set()
    for t in threads:
        t.join(180)
    assert not [t for t in threads if t.is_alive()], "放した後も待っている人がいる"


# 同じ案を 4 人が同時に押す: 作るのは 1 回分だけで、全員が同じ版を受け取る
hold = hypotheses.print_sheet = Hold(real_sheet)
threads, results, raised = together([lambda: ps.print_latest(G, GS)] * 4)
finish(threads, hold)
assert len(hold.calls) == 1 and hold.most == 1, (hold.calls, hold.most)
assert results == [1, 1, 1, 1] and not raised, (results, raised)

# 別の案は待たせない
hold = hypotheses.print_sheet = Hold(lambda *a, **k: 3)
threads, results, raised = together([lambda: ps.print_latest(G, GS), lambda: ps.print_latest(G, "H-B")])
assert hold.active == 2, hold.calls
finish(threads, hold)
assert results == [None, None] and not raised, (results, raised)

# 書きかけで落ちても、前の紙は残る。一時の場所も残らない
sheet = ps.out_dir(G) / f"{GS}_v1.pdf"
old = sheet.read_bytes()
assert old.startswith(b"%PDF")


def half(sid, hid, out, version=1, pending=None):
    pathlib.Path(f"{out}.pdf").write_bytes(b"half")
    return 3


hypotheses.print_sheet = half
assert ps.print_latest(G, GS) is None
assert sheet.read_bytes() == old, "書きかけの紙が置き場に出た"
assert not list(ps.out_dir(G).glob(".tmp-*"))

# 作っている間に読みに来た人には、書きかけでなく前の紙を渡す
seen = []


def reading(sid, hid, out, version=1, pending=None):
    pathlib.Path(f"{out}.pdf").write_bytes(b"half")
    seen.append(urllib.request.urlopen(f"{base}/sheet/{G}/{GS}_v1.pdf").read())
    return real_sheet(sid, hid, out, version, pending=pending)


hypotheses.print_sheet = reading
assert ps.print_latest(G, GS) == 1
assert seen == [old], "書きかけの紙を渡した"
assert sheet.read_bytes().startswith(b"%PDF")

# 作る人が落ちたら、待っている人も同じ失敗を受け取り、止まったままにならない。次の人は作れる


def broken(*a, **k):
    raise RuntimeError("作れない")


hold = hypotheses.print_sheet = Hold(broken)
threads, results, raised = together([lambda: ps.print_latest(G, GS)] * 3)
finish(threads, hold)
assert len(hold.calls) == 1 and not results and len(raised) == 3, (hold.calls, results, raised)
hypotheses.print_sheet = real_sheet
assert ps.print_latest(G, GS) == 1

# 自分の仮説の紙（話した考えから作る紙の道）も同じ。案の名前が違っても、同じ口を通る
own, failures = hypotheses.save_own(G, "ためしの案", "下から押す", "手元の絵")
assert not failures, failures
oid = own["id"]
hold = hypotheses.print_own = Hold(real_own)
threads, results, raised = together([lambda: ps.print_own(G, oid)] * 3)
finish(threads, hold)
hypotheses.print_own = real_own
assert len(hold.calls) == 1 and results == [0, 0, 0] and not raised, (hold.calls, results, raised)
own_sheet = ps.out_dir(G) / f"{oid}_v1_free.pdf"
old_own = own_sheet.read_bytes()
assert old_own.startswith(b"%PDF")


# 自分の仮説の道でも、書きかけで落ちたら前の紙が残る。一時の場所も残らない
def half_own(sid, oid, out, version=1):
    pathlib.Path(f"{out}_free.pdf").write_bytes(b"half")
    return 3


hypotheses.print_own = half_own
assert ps.print_own(G, oid) == 3
hypotheses.print_own = real_own
assert own_sheet.read_bytes() == old_own, "書きかけの紙が置き場に出た"
assert not list(ps.out_dir(G).glob(".tmp-*"))

# 本物の道具で、日本語の頁と英語の頁から同時に送る。片方が書きかけを読むと 500 になっていた
codes = []


def send(path):
    codes.append(post(path, {"hypothesis": GS}))


for _ in range(3):
    threads = [threading.Thread(target=send, args=(p,)) for p in (f"/toy/{G}/print", f"/toy/{G}/print", f"/en/toy/{G}/print", f"/toy/{G}/print")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(240)
assert codes == [200] * 12, codes
assert sheet.read_bytes().startswith(b"%PDF")
assert not list(ps.out_dir(G).glob(".tmp-*"))

# server の糸を止めてから終える（daemon の糸が書いている途中で Python の後始末が走らないように。上の post と同じ揺れの止め）
server.shutdown()
server.server_close()
print("ok")
