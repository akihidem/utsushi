"""合言葉なしの場の札のリンクは、どれも開く（行き止まりを作らない。J-028、#336 の続き）。

なぜ: この場では OWN-n の紙を開かない（think_sheet.opens）のに、自分の仮説の記録の札に「試した後の紙」のリンクが残っていて、
押すと 404 だった。1 つのリンクだけを見ると次の行き止まりを見逃すので、記録が出る頁のリンクを全部開いて見る。

見る事:
1. 合言葉なしの場: 玩具の頁・手帖・ギャラリー・図鑑に、開けないリンクが無い。自分の仮説の記録の札は出て、紙への道だけが無い
2. 同じ場で、たたき台とほかの仮説の前の記録の札は、紙への道が残って開く（出さない形が広がっていない対照）
3. 合言葉のある場: 同じ札に紙への道があって開く（同じ対照）
"""
import html
import os
import pathlib
import re
import shutil
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from api import ask, words  # noqa: E402
from omochae import hypotheses, loop, records, store  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

ask._key_present = lambda: False  # 合言葉なしの場は鍵のある所で立たない。鍵のある機械でも同じに動かす
ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
TRIAL = "NDL-1187053-R0000006-R"  # 試作の玩具（糸からくりの絵箱）
data = pathlib.Path(os.environ["OMOCHAE_DATA"])
for name in ("records", "loop"):  # 本物の記録（R-0001 は H-A、R-0002 は H-C）の札も同じ頁に出す
    shutil.copytree(ROOT / "data" / name, data / name)


def up(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"


opened, closed = up(public_open=True), up()


def page_at(base, path):
    return urllib.request.urlopen(base + path, timeout=120).read().decode("utf-8", "replace")


def status(base, path):
    try:
        return urllib.request.urlopen(base + path, timeout=120).status
    except urllib.error.HTTPError as e:
        return e.code


def links(page):
    """頁の中から同じサイトへ向くリンクと絵（錨だけの物は除く）。"""
    return sorted({html.unescape(x) for x in re.findall(r'(?:href|src)="(/[^"#]*)', page)})


def card_of(page, rid):
    return page.split(f'id="{rid}"', 1)[1].split("</article>", 1)[0]


def own_record(sid, name, params=None):
    """前に書かれた自分の仮説と、それで刷った紙と、その記録が置き場にある形を作る。"""
    own, failures = hypotheses.save_own(sid, name, "動かし方", "図の所", params)
    assert not failures, failures
    out_dir(sid).mkdir(parents=True, exist_ok=True)
    assert hypotheses.print_own(sid, own["id"], str(out_dir(sid) / f'{own["id"]}_v1')) == 0, sid
    rid, failures = records.add({"source_id": sid, "hypothesis_id": own["id"], "sheet_version": 1, "result": records.results_for(sid)[0], "impression": name})
    assert rid, failures
    return own["id"], rid


mine = {sid: [own_record(sid, "書いた案")] for sid in (G, T, TRIAL)}
mine[G].append(own_record(G, "寸法つきの案", {"push_part": "tab", "hub": "axle", "pusher_height": 15}))
spoken = own_record(G, "話した案")
store.write_json(loop.folder() / "words-W-9001.json", {"id": "W-9001", "source_id": G, "typed_by": words.THINK_BY, "own_id": spoken[0]})
mine[G].append(spoken)

# 1. 合言葉なしの場に、開けないリンクが無い。全部の札を出す頁を全部歩く
checked = 0
for sid in (G, T, TRIAL):
    for path in (f"/toy/{sid}", f"/toy/{sid}/techo", f"/zukan/{sid}"):
        found = links(page_at(opened, path))
        assert found, path
        dead = [(x, code) for x in found if (code := status(opened, x)) >= 400]
        assert not dead, (path, dead)
        checked += len(found)
dead = [x for x in links(page_at(opened, "/gallery")) if status(opened, x) >= 400]
assert not dead, ("/gallery", dead)
assert checked > 20, checked

# 自分の仮説の記録の札は出て、紙への道だけが無い（札を消して通っているのではない）
for sid, owned in mine.items():
    page = page_at(opened, f"/toy/{sid}")
    for oid, rid in owned:
        card = card_of(page, rid)
        assert "自分の仮説" in card, (sid, rid)
        assert "/sheet/" not in card and "試した後の紙" not in card, (sid, rid, "開かない紙への道を出さない")
    techo = page_at(opened, f"/toy/{sid}/techo")
    assert not [oid for oid, _ in owned if f"/sheet/{sid}/{oid}_" in techo], (sid, "手帖の札にも出さない")

# 2. 同じ場で、たたき台とほかの仮説の前の記録の紙への道は残る
page = page_at(opened, f"/toy/{G}")
techo = page_at(opened, f"/toy/{G}/techo")
for rid, hid in (("R-0001", "H-A"), ("R-0002", "H-C")):
    paper = f"/sheet/{G}/{hid}_v1_after.pdf"
    assert paper in card_of(page, rid) and paper in techo and status(opened, paper) == 200, (rid, paper)
    assert f"/toy/{G}?see={hid}&kind=after&v=1#win" in card_of(page, rid), rid

# 3. 合言葉のある場では、同じ札に紙への道があって開く
for sid, owned in mine.items():
    page, techo = page_at(closed, f"/toy/{sid}"), page_at(closed, f"/toy/{sid}/techo")
    for oid, rid in owned:
        paper = f"/sheet/{sid}/{oid}_v1_after.pdf"
        assert paper in card_of(page, rid) and paper in techo and status(closed, paper) == 200, (sid, rid)
free_paper = f"/sheet/{G}/{mine[G][0][0]}_v1_free.pdf"
assert free_paper in card_of(page_at(closed, f"/toy/{G}"), mine[G][0][1]) and status(closed, free_paper) == 200

print(f"ok: 合言葉なしの場のリンク {checked} 本はどれも開き、OWN-n の紙への道は札に出ない")
