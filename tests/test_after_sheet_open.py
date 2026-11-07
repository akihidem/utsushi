"""サイトで紙を作っていない案の記録でも、試した後の紙の道（/sheet/…_after）が開く（#320）。
11-06 から試した後の紙は刷らない（本人の決まり「文章のプリントは廃止」）。札・知らせ・窓からの道は外し、/sheet の道と作る仕組みだけを残す。

なぜ: 場で配られた紙で作った人は「型紙を見る」を押さないので、置き場に紙が無い。札のリンクは紙があるかを見ずに出すので、PDF は 404 で、
字のリンクの窓には紙が出なかった。試した後の紙は次に変える条件と札を渡す所なので、ここで止まると輪の次の段に進みにくい。
開く時に作るのは、前に残した記録と、置き場が空になった後の記録も同じ道で開くため。記録の無い案には作らない（S-03）。型紙の確定は増やさない。
作るのは試した後の紙だけ。型紙（H-A_v1.pdf）があれば刷った案と読まれ、窓の最初の案や記録の欄の既定が、開いただけの案へ移るため。
"""
import os
import re
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import hypotheses, loop, making_log, records  # noqa: E402
from omochae.marks import HYPOTHESIS, OWN_HYPOTHESIS  # noqa: E402
from web.play_server import out_dir, printed_versions, serve  # noqa: E402

DEN = "NDL-1187053-R0000007-R"  # でんでん太鼓（#320 で見た玩具）
GO = "NDL-1187053-R0000005-L"  # 御来迎（必須の 1 つ）
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    try:
        with urllib.request.urlopen(base + path, timeout=180) as x:
            return x.status, x.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    with urllib.request.urlopen(r, timeout=180) as x:
        return x.status, x.read().decode()


def record(sid, hid):
    """記録を残し、着いた頁を返す。"""
    code, page = post(f"/toy/{sid}/record", {"hypothesis": hid, "result": records.results_for(sid)[0]})
    assert code == 200 and "記録を残しました。" in page and "試した後の紙が開けます" not in page, (sid, hid, code)
    return page


def files(sid, hid):
    return {p.name: p.stat().st_mtime_ns for p in out_dir(sid).glob(f"{hid}_v*")} if out_dir(sid).exists() else {}


def window(page):
    return page[page.index('id="win"'):page.index('id="tsukuru"')]


def pdf_text(data):
    return subprocess.run(["pdftotext", "-", "-"], input=data, capture_output=True, check=True).stdout.decode()


def only_after(sid, hid, version=1):
    """試した後の紙（PDF・PNG・SVG）だけで、型紙と手順の紙は無い。"""
    return sorted(files(sid, hid)) == [f"{hid}_v{version}_after.{ext}" for ext in ("pdf", "png", "svg")]


# 記録の前は渡さない（S-03）。URL を知っていても作らない
assert get(f"/sheet/{DEN}/H-A_v1_after.pdf")[0] == 403
code, body = get(f"/toy/{DEN}?see=H-A&kind=after&v=1")
assert code == 200 and "H-A_v1_after" not in body.decode() and not files(DEN, "H-A"), "記録の前に作らない"

# 紙を作らずに記録を残す（場で配られた紙で作った人）。札にも知らせにも、試した後の紙への道は出さない（11-06）
page = record(DEN, "H-A")
assert "kind=after" not in page and "_after.pdf" not in page, "札に試した後の紙への道を出さない"
pdf = f"/sheet/{DEN}/H-A_v1_after.pdf"
# 前の札のリンク（kind=after）で窓へ来ても、試した後の紙は出さず、開いただけで作らない
code, body = get(f"/toy/{DEN}?see=H-A&kind=after&v=1")
assert code == 200 and "H-A_v1_after" not in window(body.decode()) and not files(DEN, "H-A"), "窓は試した後の紙を出さない"
# 前に配ったリンクのために残した /sheet の道は開く（PDF・絵・拡大）
code, body = get(pdf)
assert code == 200 and body[:4] == b"%PDF", code
for ext in ("png", "svg"):
    assert get(f"/sheet/{DEN}/H-A_v1_after.{ext}")[0] == 200, ext

# 開いても刷った案にならない。型紙と手順の紙を作らず、紙を選ぶ口と聞く口の線も変わらない
assert only_after(DEN, "H-A"), sorted(files(DEN, "H-A"))
assert printed_versions(DEN, "H-A") == []
try:
    post(f"/toy/{DEN}/ask", {"hypothesis": "H-A", "question": "谷折りって何？"})
    raise AssertionError("刷っていない紙には答えない")
except urllib.error.HTTPError as e:
    assert e.code == 422, e.code

# 道の PDF を直に開いても開く（手帖からの道は 11-06 に外した）
record(DEN, "H-B")
code, body = get(f"/sheet/{DEN}/H-B_v1_after.pdf")
assert code == 200 and body[:4] == b"%PDF" and only_after(DEN, "H-B"), code

# 型紙の確定の記録の線は変えない: 人が刷ると選んだ操作でないので、確定も頁の段の「刷った」も増えない
assert loop.sheet_confirmations(DEN) == []
assert {s["stage"] for s in making_log.stages(DEN)} == {"record"}

# 記録の無い版は作らない。あるのは版 1 の記録だけ
assert get(f"/sheet/{DEN}/H-A_v2_after.pdf")[0] == 404
assert not [n for n in files(DEN, "H-A") if "_v2" in n]

# 手作りの URL の桁の多い版の数字は、道に当たらず 404（int の上限で 500 にしない）。窓の版の数字は読めなければ無指定と同じ
many = "9" * 5000
assert get(f"/sheet/{DEN}/H-A_v{many}_after.pdf")[0] == 404, "桁の多い版の数字"
assert get(f"/toy/{DEN}?see=H-A&kind=after&v={many}")[0] == 200

# 前に残した記録と、置き場が空になった後の記録も同じ道で開く
for p in out_dir(DEN).glob("H-A_v1*"):
    p.unlink()
code, body = get(f"/sheet/{DEN}/H-A_v1_after.pdf")
assert code == 200 and body[:4] == b"%PDF" and only_after(DEN, "H-A"), code

# 後から人が「型紙を見る」を押せば、いつもの刷り方になる。確定は押した分だけ残る
assert post(f"/toy/{DEN}/print", {"hypothesis": "H-A"})[0] == 200
assert printed_versions(DEN, "H-A") == [1] and "H-A_v1.png" in files(DEN, "H-A")
assert [(c["hypothesis_id"], len(c["confirmations"])) for c in loop.sheet_confirmations(DEN)] == [("H-A", 1)]

GS = hypotheses.sheet_of(GO)["id"]  # 御来迎の今の組（goraigo-v14）のたたき台は H-C
# サイトで紙を作った案は、作り直さない。確定は押した 1 回のまま（必須 2 種の今の組で刷れるのは、たたき台の 1 枚だけ。#332）
assert post(f"/toy/{GO}/print", {"hypothesis": GS})[0] == 200
made = files(GO, GS)
record(GO, GS)
assert get(f"/sheet/{GO}/{GS}_v1_after.pdf")[0] == 200
# 型紙は作り直さない（試した後の紙は 11-06 から刷る時に組まないので、道を開いた時にそれだけが足される）
assert {k: v for k, v in files(GO, GS).items() if k in made} == made, "作り直した"
assert [(c["hypothesis_id"], len(c["confirmations"])) for c in loop.sheet_confirmations(GO)] == [(GS, 1)]

# 紙の組で刷った物と、試した後の紙だけを作った物は同じ文になる（題と印を分けて持たない）
with tempfile.TemporaryDirectory() as tmp:
    assert hypotheses.print_after(GO, GS, f"{tmp}/x") == 0
    with open(f"{tmp}/x_after.pdf", "rb") as f:
        assert pdf_text(f.read()) == pdf_text(get(f"/sheet/{GO}/{GS}_v1_after.pdf")[1])

# ほかの案を刷った後に、紙を作っていない案の前の札のリンクで窓へ来ても、窓の最初の案は刷った案のまま（記録の欄の既定もこれを読む）。
OTHER = "H-A" if GS != "H-A" else "H-C"  # 今の組で刷れない案
# 窓は試した後の紙を出さず、開いただけで作らない（11-06）。刷れない案（今の組 goraigo-v14 では、前の組のたたき台 H-A など）の記録でも同じ
record(GO, OTHER)
time.sleep(1.1)  # 置き場の時刻の刻みで、後から作った事が分かるように
code, body = get(f"/toy/{GO}?see={OTHER}&kind=after&v=1")
shown = window(body.decode())
assert code == 200 and f"{OTHER}_v1_after" not in shown and not files(GO, OTHER), "窓は試した後の紙を出さず、作らない"
code, body = get(f"/toy/{GO}")
shown = window(body.decode())
assert code == 200 and f"/sheet/{GO}/{GS}_v1.png" in shown and f"{OTHER}_v1" not in shown.split('class="win"')[1], "開いただけの案へ移らない"

# 自分の仮説: 窓に出ないので、字のリンクも PDF へ向ける（窓へ向けると、ほかの案の紙が出る）。型紙なしの紙の人にも試した後の紙を渡す
# 頁の書く欄は外した（J-032 の点 2）。前に書かれた仮説と、それで刷った紙が置き場にある形で見る
for name in ("糸で引く", "紙の張りで開く"):
    assert not hypotheses.save_own(DEN, name, "下の紙を引くと、上が開く", "図の右の糸")[1]
out_dir(DEN).mkdir(parents=True, exist_ok=True)
assert hypotheses.print_own(DEN, "OWN-2", str(out_dir(DEN) / "OWN-2_v1")) == 0
for own in ("OWN-1", "OWN-2"):
    assert get(f"/sheet/{DEN}/{own}_v1_after.pdf")[0] == 403, ("記録の前に渡さない", own)
page = record(DEN, "OWN-1")
assert "OWN-1_v1_after" not in page and "see=OWN-1" not in page, "札に試した後の紙への道を出さない（11-06）"
code, body = get(f"/sheet/{DEN}/OWN-1_v1_after.pdf")
assert code == 200 and body[:4] == b"%PDF", code
text = pdf_text(body)
assert "試した後の紙" in text and "糸で引く" in text, text[:200]
flat = "".join(text.split())
assert "".join(OWN_HYPOTHESIS.split())[:12] in flat and "".join(HYPOTHESIS.split())[:12] not in flat, "人が立てた仮説を AI が考えたと刷らない"
# 記録の無い版は作らない。自分の仮説は版の番号の分だけ紙が増えてしまうので、ここで止める
assert get(f"/sheet/{DEN}/OWN-1_v2_after.pdf")[0] == 404
assert not [n for n in files(DEN, "OWN-1") if "_v2" in n]

# 作れない時も玩具の頁は落とさない。紙が無いだけなので、PDF は 404 のまま（字の断りを足さない）
real = loop.print_after


def broken(*a, **k):
    raise RuntimeError("試験で壊した")


record(GO, "H-D")
for fake in (broken, lambda *a, **k: 3):
    loop.print_after = fake
    assert get(f"/toy/{GO}?see=H-D&kind=after&v=1")[0] == 200
    assert get(f"/sheet/{GO}/H-D_v1_after.pdf")[0] == 404
loop.print_after = real
assert get(f"/sheet/{GO}/H-D_v1_after.pdf")[0] == 200, "直ったら開く"

server.shutdown()
print("ok")
