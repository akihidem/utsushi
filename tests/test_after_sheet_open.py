"""サイトで紙を作っていない案の記録でも、札の「試した後の紙」と「PDF」が開く（#320）。

なぜ: 場で配られた紙で作った人は「型紙を見る」を押さないので、置き場に紙が無い。札のリンクは紙があるかを見ずに出すので、PDF は 404 で、
字のリンクの窓には紙が出なかった。試した後の紙は次に変える条件と札を渡す所なので、ここで止まると輪の次の段に進みにくい。
開く時に作るのは、前に残した記録と、置き場が空になった後の記録も同じ道で開くため。記録の無い案には作らない（S-03）。型紙の確定は増やさない。
"""
import os
import re
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import loop, making_log, records  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

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
    assert code == 200 and "試した後の紙が開けます" in page, (sid, hid, code)
    return page


def files(sid, hid):
    return {p.name: p.stat().st_mtime_ns for p in out_dir(sid).glob(f"{hid}_v*")} if out_dir(sid).exists() else {}


def window(page):
    return page[page.index('id="win"'):page.index('id="tsukuru"')]


def pdf_text(path):
    return subprocess.run(["pdftotext", "-", "-"], input=get(path)[1], capture_output=True, check=True).stdout.decode()


# 記録の前は渡さない（S-03）。URL を知っていても作らない
assert get(f"/sheet/{DEN}/H-A_v1_after.pdf")[0] == 403
code, body = get(f"/toy/{DEN}?see=H-A&kind=after&v=1")
assert code == 200 and "H-A_v1_after" not in body.decode() and not files(DEN, "H-A"), "記録の前に作らない"

# 紙を作らずに記録を残す（場で配られた紙で作った人）。札のリンクは頁から読み、本当に開くかを見る
page = record(DEN, "H-A")
link = re.search(r'<a href="(/toy/[^"]*kind=after[^"]*)">試した後の紙</a>', page).group(1)
pdf = re.search(r'<a href="(/sheet/[^"]*_after\.pdf)"[^>]*>PDF</a>', page).group(1)
assert pdf == f"/sheet/{DEN}/H-A_v1_after.pdf" and "see=H-A&" in link, (link, pdf)

# 字のリンク: 窓に試した後の紙が出て、窓の絵も拡大も PDF も開く
code, body = get(link.split("#")[0])
shown = window(body.decode())
assert code == 200 and f"/sheet/{DEN}/H-A_v1_after.png" in shown, "窓に試した後の紙が出ない"
assert "仮説の札を押すと、紙を作ってここに出します" not in shown
for ext in ("png", "svg"):
    assert get(f"/sheet/{DEN}/H-A_v1_after.{ext}")[0] == 200, ext
code, body = get(pdf)
assert code == 200 and body[:4] == b"%PDF", code

# PDF を先に開いても開く（手帖のリンクは PDF だけ）
record(DEN, "H-B")
code, body = get(f"/sheet/{DEN}/H-B_v1_after.pdf")
assert code == 200 and body[:4] == b"%PDF", code

# 型紙の確定の記録の線は変えない: 人が刷ると選んだ操作でないので、確定も頁の段の「刷った」も増えない
assert loop.sheet_confirmations(DEN) == []
assert {s["stage"] for s in making_log.stages(DEN)} == {"record"}

# 記録の無い版は作らない。あるのは版 1 の記録だけ
assert get(f"/sheet/{DEN}/H-A_v2_after.pdf")[0] == 404
assert not [n for n in files(DEN, "H-A") if "_v2" in n]

# 前に残した記録と、置き場が空になった後の記録も同じ道で開く
for p in out_dir(DEN).glob("H-A_v1*"):
    p.unlink()
code, body = get(f"/sheet/{DEN}/H-A_v1_after.pdf")
assert code == 200 and body[:4] == b"%PDF", code

# サイトで紙を作った案は、作り直さない。確定は押した 1 回のまま
assert post(f"/toy/{GO}/print", {"hypothesis": "H-C"})[0] == 200
made = files(GO, "H-C")
record(GO, "H-C")
assert get(f"/sheet/{GO}/H-C_v1_after.pdf")[0] == 200
assert files(GO, "H-C") == made, "作り直した"
assert [(c["hypothesis_id"], len(c["confirmations"])) for c in loop.sheet_confirmations(GO)] == [("H-C", 1)]

# 自分の仮説: 窓に出ないので、字のリンクも PDF へ向ける（窓へ向けると、ほかの案の紙が出る）。型紙なしの紙の人にも試した後の紙を渡す
for name in ("糸で引く", "紙の張りで開く"):
    assert post(f"/toy/{GO}/own", {"name": name, "how": "下の紙を引くと、上が開く", "evidence": "図の右の糸"})[0] == 200
assert post(f"/toy/{GO}/print-own", {"id": "OWN-2"})[0] == 200
for own in ("OWN-1", "OWN-2"):
    assert get(f"/sheet/{GO}/{own}_v1_after.pdf")[0] == 403, ("記録の前に渡さない", own)
page = record(GO, "OWN-1")
assert f'<a href="/sheet/{GO}/OWN-1_v1_after.pdf"' in page and "see=OWN-1" not in page
code, body = get(f"/sheet/{GO}/OWN-1_v1_after.pdf")
assert code == 200 and body[:4] == b"%PDF", code
text = pdf_text(f"/sheet/{GO}/OWN-1_v1_after.pdf")
assert "試した後の紙" in text and "糸で引く" in text, text[:200]
# 記録の無い版は作らない。自分の仮説は版の番号の分だけ紙が増えてしまうので、ここで止める
assert get(f"/sheet/{GO}/OWN-1_v2_after.pdf")[0] == 404
assert not [n for n in files(GO, "OWN-1") if "_v2" in n]

# 作れない時も玩具の頁は落とさない。紙が無いだけなので、PDF は 404 のまま（字の断りを足さない）
real = loop.print_version


def broken(*a, **k):
    raise RuntimeError("試験で壊した")


record(GO, "H-D")
for fake in (broken, lambda *a, **k: 3):
    loop.print_version = fake
    assert get(f"/toy/{GO}?see=H-D&kind=after&v=1")[0] == 200
    assert get(f"/sheet/{GO}/H-D_v1_after.pdf")[0] == 404
loop.print_version = real
assert get(f"/sheet/{GO}/H-D_v1_after.pdf")[0] == 200, "直ったら開く"

server.shutdown()
print("ok")
