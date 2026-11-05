"""押して止まる所（使い勝手の点検で見つけた 3 件）。新しい字は足さない。

1. 手帖の約束の印は、写真か動画を選んだ時だけ要る。「記録だけ残す」は印が無くても押せる。合言葉なしの場は写真の口が閉じているので、印を出さない
2. 写真を選ばずに残した時の返事を「上げました」にしない（上げていないので）。字は頁の記録の返事に今ある字
3. 「この考えから紙を作る」の戻り先は #think。断りの文はそこにあり、頁の頭に戻ると見えなかった（幅 390 で 2978px 下）
4. 「残す」の前に釦を押しても、話した字を消さない。字はタブの中にだけ持ち、サーバへ送らない（送るのは「残す」の時だけ、hanasu の決まり）

押した時の動きはブラウザが要るので、ここでは頁と script の形を見る（./run.sh はブラウザなしで動く決まり）。実物で押した結果は帳面の節に書く。
"""
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import hanasu, techo_site, think_sheet  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
ROOT = pathlib.Path(__file__).resolve().parents[1]
shut = []


def start(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    shut.append(server)
    return f"http://127.0.0.1:{server.server_address[1]}"


def get(base, path):
    return urllib.request.urlopen(base + path, timeout=60).read().decode()


def post(base, path, data):
    q = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    try:
        r = urllib.request.urlopen(q, timeout=60)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


base, public = start(), start(public_open=True)

# 1. 約束の印
page = get(base, f"/toy/{G}/techo")
mark = re.search(r'<input type="checkbox" id="ok"[^>]*>', page)
assert mark, "写真の口が開いている場には印を出す"
assert "required" not in mark.group(0), ("写真を選ばない時は要らない", mark.group(0))
picked = techo_site.SCRIPT[techo_site.SCRIPT.index("function showPicked"):techo_site.SCRIPT.index("picker.onchange")]
assert re.search(r"\.required = kept\.length > 0", picked), "選んだ写真か動画がある時だけ要る"
assert 'getElementById(\'ok\')' in picked and "if (promise)" in picked, "印の無い場（合言葉なし）でも止まらない"
shown = get(public, f"/toy/{G}/techo")
assert 'id="ok"' not in shown and "大人の手元だけ" not in shown, "写真の口が閉じている場に印を出さない"
assert '<input type="file" id="files" disabled>' in shown, "対照: 合言葉なしの場の頁を見ている"

# 2. 返事
up = techo_site.SCRIPT[techo_site.SCRIPT.index("getElementById('up-form')"):]
assert "done = files.length ? '上げました' : '記録を残しました'" in up, "写真を選ばずに残したら「上げました」と言わない"
assert "記録を残しました" in (ROOT / "src/web/play_server.py").read_text(encoding="utf-8"), "新しい字でなく、頁の記録の返事に今ある字"

# 3. 戻り先
page = get(base, f"/toy/{G}")
assert f'action="/toy/{G}/think-sheet#think"' in page, "断りの文のある節へ戻す"
pending = think_sheet._status(G, {"status": "pending_human", "how_it_moves": "x", "token": "t", "result": {}})
assert f'action="/toy/{G}/think-ok#think"' in pending, "こちらの釦も同じ節へ戻す"
code, body = post(base, f"/toy/{G}/think-sheet", {"who": ""})
assert code == 422 and think_sheet.NONE in body.split('id="think"', 1)[1].split("</section>", 1)[0], "断りの文は #think の中"

# 4. 話した字
assert page.index('id="hanasu"') < page.index('id="think"'), "字の欄は釦の節のすぐ前"
go = re.search(r'<form[^>]*think-sheet[^>]*>(.*?)</form>', page, re.S).group(1)
assert "<textarea" not in go and "<input" not in go, "釦は字を送らない"
script = hanasu.SCRIPT
keep = script[script.index("// 「残す」の前に"):script.index("addEventListener('pagehide',stop)")]
assert "e.target.closest('#think')" in keep, "#think の釦を押す時に持つ"
assert "sessionStorage.setItem" in keep and "sessionStorage.removeItem" in keep, "タブの中に持ち、読み直したら消す"
assert "fetch" not in keep, "サーバへ送らない"
assert "via:box.dataset.via" in keep and "box.dataset.via=d.via" in keep, "話した字か書いた字かも一緒に持って戻す"
assert "if(d&&!said.value){said.value=d.text" in keep, "読み直した後の空の欄にだけ戻す（書きかけの字を上書きしない）"

for server in shut:
    server.shutdown()
print("ok 写真を選ばずに残せて、釦は断りの文のある節へ戻り、話した字は消えない")
