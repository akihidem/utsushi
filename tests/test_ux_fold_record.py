"""玩具の頁の記録の欄を、見出しのまま畳む（地図 state/journey-map.md の工程 4「声と動画が主で、字は畳んだ追加。残す口は 1 つ」）。

なぜ: 玩具の頁に記録の欄が 13 開いたままで、「全部書くのか」と読める。残す口は手帖の「のこす」で、玩具の頁の欄は字で残したい人と
JS の無い画面のための追加。欄そのものは残し、見出し「試した記録を残す」を畳みの見出しにする（新しい字は無い）。

見る事:
1. ふだんは閉じている。畳みの外（玩具の頁で最初から見える所）に、記録の欄が 1 つも無い。欄と送る釦は畳みの中に全部ある
2. 送って通らなかった時は開いて、書いた字が欄に戻る（#300 と同じ線: 書いた字を隠さない）
3. 残せた時の返事の文は、畳みに隠れない所に出る（残した記録の札へ戻る）。#kiroku の道で着いた時に畳みを開く動き（FOLD_SCRIPT）が頁にある
4. 送る形は変えない: 畳んだままの欄から残せる
"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import toy  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def post(path, **data):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST", headers={"Origin": base})
    try:
        r = opener.open(req, timeout=120)
        return r.status, r.read().decode(), r.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.headers.get("Location", "")


def get(path):
    return urllib.request.urlopen(base + path, timeout=120).read().decode()


def section(page):
    i = page.index('<section class="sec" id="kiroku">')
    return page[i:page.index("</section>", i) + len("</section>")]


def outside_details(html):
    """畳み（details）の外の字。入れ子の details も外す。"""
    out, depth, pos = [], 0, 0
    for m in re.finditer(r"<details\b|</details>", html):
        if depth == 0:
            out.append(html[pos:m.start()])
        depth += 1 if m.group(0) != "</details>" else -1
        pos = m.end()
    if depth == 0:
        out.append(html[pos:])
    return "".join(out)


FIELD = re.compile(r'<(?:input(?![^>]*type="hidden")|textarea|select)\b[^>]*>')
HEAD = '<details class="fold-sec"><summary><h2>試した記録を残す</h2></summary>'

# ---- 1 ふだんは閉じている
post(f"/toy/{G}/print", hypothesis="H-A")
page = get(f"/toy/{G}")
kiroku = section(page)
assert HEAD in kiroku, ("記録の節は、見出しのまま畳む", kiroku[:300])
assert not FIELD.findall(outside_details(kiroku)) and "<button>記録を残す</button>" not in outside_details(kiroku), "畳みの外に記録の欄を出さない"
inside = kiroku[kiroku.index(HEAD):]
assert len(FIELD.findall(inside)) >= 8 and '<form method="post" action="/toy/' in inside and "<button>記録を残す</button>" in inside, "欄と送る釦は畳みの中に全部ある"
assert toy.FOLD_SCRIPT in page, "#kiroku の道で着いた時に畳みを開く"

# ---- 2 通らなかった時は開いて、書いた字を戻す（見た事の札を選ばずに送る）
code, body, _ = post(f"/toy/{G}/record", hypothesis="H-A", impression="糊がはみ出した")
assert code >= 400 or "糊がはみ出した" in body, code
kiroku = section(body)
assert '<details class="fold-sec" open><summary><h2>試した記録を残す</h2></summary>' in kiroku, ("通らなかった時は開く", kiroku[:300])
assert "糊がはみ出した" in kiroku, "書いた字が欄に戻る"

# ---- 3・4 畳んだままの欄から残せる。返事の文は畳みの外
code, _, where = post(f"/toy/{G}/record", hypothesis="H-A", result="動いた", sheet_version="1")
assert code == 303 and "msg=" in where, (code, where)
msg = urllib.parse.parse_qs(urllib.parse.urlsplit(where).query)["msg"][0]
back = get(where.split("#")[0].replace(base, ""))
# 残せた後は、残した記録の札（#R-…）へ戻る。返事の文は、畳みに隠れない所に出る
assert HEAD in section(back) and msg in outside_details(back), ("返事の文は畳みの外に出る", msg)
server.shutdown()
print("ok 玩具の頁の記録の欄は見出しのまま畳み、通らなかった時は開いて書いた字を戻し、返事の文は畳みの外に出る（地図の工程 4）")
