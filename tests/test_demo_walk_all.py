"""増やした雛形の玩具にもデモで触れる（本人の決定 Q3 (b)、11-04）。雛形ごとに試作の玩具を 1 つ選び、
入口 → 図鑑 → 玩具の頁 → 型紙 → 手帖 → 質問 → 記録 → 説明 → 次の版 を通す。鍵は使わない。
試作の玩具がまだ無い雛形は飛ばす（線を取り込むたびに、この試験が増えた雛形を通す）。"""
import json
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api import ask  # noqa: E402

ask._key_present = lambda: False

from omochae import hypotheses  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from omochae.metrics import ALLOWED  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

server = serve(0)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
host = f"127.0.0.1:{port}"


def call(path, form=None):
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    headers = {"Host": host} | ({"Origin": f"http://{host}", "Content-Type": "application/x-www-form-urlencoded"} if data else {})
    try:
        with urllib.request.urlopen(urllib.request.Request(f"http://{host}{path}", data=data, headers=headers)) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


assert 'href="/zukan"' in call("/")[1], "入口から図鑑へ行ける"
zukan = call("/zukan")[1]
picked = {}
for sid in sources():
    d = hypotheses.load(sid)
    if hypotheses.stage(sid) == "試作" and d["hypotheses"]:
        picked.setdefault(d.get("template", "slider_fan"), sid)
walked = []
for tid, sid in sorted(picked.items()):
    tpl = TEMPLATES[tid]
    h = hypotheses.load(sid)["hypotheses"][0]
    assert f"/zukan/{sid}" in zukan, (tid, "図鑑の一覧から入れる")
    assert call(f"/toy/{sid}")[0] == 200, (tid, sid)
    assert call(f"/toy/{sid}/print", {"hypothesis": h["id"]})[0] in (200, 303), (tid, sid)
    with urllib.request.urlopen(urllib.request.Request(f"http://{host}/sheet/{sid}/{h['id']}_v1.pdf", headers={"Host": host})) as r:
        assert r.read(4) == b"%PDF", (tid, "型紙が開ける")
    assert call(f"/toy/{sid}/techo")[0] == 200, (tid, "手帖が開く")
    code, ans = call(f"/toy/{sid}/ask-json", {"hypothesis": h["id"], "question": "谷折りって？"})
    assert code == 200 and json.loads(ans)["text"], (tid, ans)
    code, rec = call(f"/toy/{sid}/record-json", {"hypothesis": h["id"], "result": tpl.RESULTS[0], "note": "試した"})
    assert code == 201, (tid, rec)
    rid = json.loads(rec)["id"]
    assert call(f"/record/{rid}/explain", {"by": "本人", "text": "こう読んだ", "next_idea": "寸法を変える"})[0] in (200, 303), tid
    # 次の版: 変えてよい寸法のどれかを少し動かして、床を通る版が 1 つは刷れる事を見る（落ちた値は理由付きで断られる）
    base = {**tpl.DEFAULTS, **h["params"]}
    made = False
    for param in sorted(ALLOWED[tid]):
        lo, hi = tpl.RANGES[param]
        v = base.get(param)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            continue
        for to in (v * 1.05, v * 0.95, (lo + hi) / 2):
            to = round(min(max(to, lo), hi)) if isinstance(v, int) else round(min(max(to, lo), hi), 2)
            if to == v:
                continue
            code, out = call(f"/record/{rid}/next", {"interpretation": "少し変える", "param": param, "to": str(to), "why": "確かめ", "by": "本人"})
            assert code in (200, 303, 422), (tid, code)
            if code in (200, 303):
                made = True
                break
            assert re.search(r'<p id="msg">.+?<', out), (tid, "断る時は理由を見せる")
        if made:
            break
    assert made, (tid, sid, "次の版が 1 つも刷れない")
    walked.append(tid)
server.shutdown()
print("ok", len(walked), "種の雛形を通した", " ".join(walked))
