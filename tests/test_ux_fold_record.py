"""玩具の頁の「試した記録を残す」を、のこす（手帖の最後と記録の頁）へ寄せる（本人の答え 11-07 夕の Q3「試した記録を残すは寄せる — のこすへ」）。

前は、玩具の頁の記録の欄（13 の欄）を見出しのまま畳んで置いた（地図の工程 4「残す口は 1 つ」）。本人の答えで欄を外し、
同じ所（錨 #kiroku）に記録の頁への道を 1 本だけ置く。受け口 /toy/<印>/record は残す（前からの道と作る側の道具のため）。

見る事:
1. 玩具の頁に記録の欄が無い（欄・送る釦・畳みの見出し「試した記録を残す」）。#kiroku の節は 1 つで、のこす（記録の頁）への道が 1 本
2. 道の行き先の記録の頁は、記録の無い人にも開く
3. 受け口は残る: 通らなかった時は、返事の文が #kiroku の節に出る（欄が無いので書いた字は戻らない）。残せた時は残した記録の札へ戻り、返事の文が出る
記録が残せる事・結果の札の字が読める事は、手帖の側の試験が守る（tests/test_techo_step.py・tests/test_result_readers.py・tests/test_result_words.py）
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


FIELD = re.compile(r'<(?:input(?![^>]*type="hidden")|textarea|select)\b[^>]*>')
OLD_HEAD = "<h2>試した記録を残す</h2>"
LINK = f'<a href="/toy/{G}/techo/kiroku">{toy.KIROKU_TO_NOKOSU}</a>'

# ---- 1 欄が無く、のこすへの道が 1 本
post(f"/toy/{G}/print", hypothesis="H-A")
page = get(f"/toy/{G}")
kiroku = section(page)
assert page.count('id="kiroku"') == 1 and LINK in kiroku, ("のこすへの道", kiroku[:300])
assert not FIELD.findall(kiroku) and "<form" not in kiroku and OLD_HEAD not in page and 'id="record"' not in page, "玩具の頁に記録の欄は無い"

# ---- 2 道の行き先は、記録の無い人にも開く
assert urllib.request.urlopen(base + f"/toy/{G}/techo/kiroku", timeout=120).status == 200

# ---- 3 受け口は残る
code, body, _ = post(f"/toy/{G}/record", hypothesis="H-A", impression="糊がはみ出した")
assert code == 422, code
kiroku = section(body)
assert LINK in kiroku and "糊がはみ出した" not in kiroku, "通らなかった時は、返事の文と道だけ（書いた字を戻す欄は無い）"
code, _, where = post(f"/toy/{G}/record", hypothesis="H-A", result="動いた", sheet_version="1")
assert code == 303 and "msg=" in where, (code, where)
msg = urllib.parse.parse_qs(urllib.parse.urlsplit(where).query)["msg"][0]
back = get(where.split("#")[0].replace(base, ""))
assert msg in back and 'id="record"' not in back, ("残せた時は返事の文が出る", msg)
server.shutdown()
print("ok 玩具の頁に記録の欄は無く、のこすへの道が 1 本。受け口は残り、返事の文が出る（本人の答え Q3）")
