"""話した工夫の字を、ギャラリーと玩具の頁の記録の札に出す（#315）。本人の決定（11-05、2b「全部見せる」）: 記録に入った字は、記録の感想と同じに、ほかの人の頁に文で出す。
選び肢は置かない。作る側が隠した字と、入口の床に当たる字は出さない。考えの字は、見分ける見出しの文が本人の確認待ちなので、まだ出さない。合言葉なしで開いた場では文を出さない（J-028）。"""
import os
import re
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_SAMPLES"] = "0"

from omochae import records, talk_log  # noqa: E402
from web import hanasu  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
WHO = "abcde12345"
CRAFT, KEEP, THINK, OTHER = "糊代に先に折り癖を付けたら貼りやすかった", "上げた後に気づいた事: 筒を太く巻くとよい", "下から開くのかもしれない", "記録に入っていない字"
TYPED = "外筒 / 太く巻いた / 内筒が入りやすくなった"

rid, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた", "fixes": [{"part": "外筒", "change": "太く巻いた", "outcome": "内筒が入りやすくなった"}]})
assert rid and not fails, fails
# 話した字だけの記録: 写真も感想も無くても、札に出る
only, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動かない", "fixes": []})
assert only and not fails, fails
for scene, text, step in (("craft", CRAFT, 3), ("think", THINK, None)):
    assert talk_log.add(G, scene, text, hypothesis_id="H-A", sheet_version=1, step=step, who=WHO)[1] == []
assert talk_log.bind(G, "H-A", 1, WHO, rid)[0] == 1
assert talk_log.add(G, "keep", KEEP, record_id=only)[1] == []
assert talk_log.add(G, "craft", OTHER, hypothesis_id="H-A", sheet_version=1, step=1, who="zzzzz99999")[1] == []
# 床に当たる字は残らない
assert talk_log.add(G, "keep", "田中と申します。三年二組です", record_id=only)[1], "名乗りの形は残さない"

srv = serve(0)
threading.Thread(target=srv.serve_forever, daemon=True).start()


def get(path, server=srv):
    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}") as r:
        return r.read().decode()


for path in ("/gallery", f"/toy/{G}"):
    page = get(path)
    assert f"手順 3: {CRAFT}" in page, f"{path}: 作りながら話した工夫（手順の番号つき）"
    assert KEEP in page, f"{path}: 上げた後に残した字"
    assert page.count(TYPED) == 1, f"{path}: 記録の欄の工夫は 1 回だけ（話した字と同じ節）"
    assert hanasu.KUFU_HEAD in page and f'data-kufu="{rid}"' in page and f'data-kufu="{only}"' in page
    assert THINK not in page, f"{path}: 考えの字はまだ出さない"
    assert OTHER not in page, f"{path}: 記録に入っていない字は出さない"
    assert "田中" not in page, f"{path}: 床に当たる字は出さない"
    assert "出してよい" not in page, f"{path}: 選び肢は置かない"
    assert not re.search(r"順位|ランキング|人気|点数|\d+ 位|いいね", page), path

# 作る側が隠した字は出ない。戻すと出る。記録の欄の工夫は隠れない
assert talk_log.set_share(G, rid, False)[1] == []
for path in ("/gallery", f"/toy/{G}"):
    page = get(path)
    assert CRAFT not in page and page.count(TYPED) == 1, path
assert talk_log.set_share(G, rid, True)[1] == []
assert CRAFT in get("/gallery")

# 合言葉なしで開いた場では、文を出さない（J-028）
opened = serve(0, public_open=True)
threading.Thread(target=opened.serve_forever, daemon=True).start()
for path in ("/gallery", f"/toy/{G}"):
    page = get(path, opened)
    assert CRAFT not in page and KEEP not in page and TYPED not in page and hanasu.KUFU_HEAD not in page, path
opened.shutdown()

# 記録を取り下げると字も消える
assert not records.withdraw(rid)[1]
for path in ("/gallery", f"/toy/{G}"):
    page = get(path)
    assert CRAFT not in page and TYPED not in page, path
srv.shutdown()
print("ok")
