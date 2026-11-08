"""型紙を印刷する（玩具の頁の #win）の中の「Claude に話して型紙を作り直す」口（本人の言葉 11-08「版が若いものは、型紙を出力する前に、自分で仮説を話して
よくしてから作りたいと思うと思う。型紙のところに、クロードに自分の考えを話して型紙を改善するボタンを設置して、再生成してもらうボタンをつけたい。」・
設計 grove の state/tsukuru-talk-sheet-20261108.md 2 版・本人の答え 11-08「釦は 1 つ『Claude に話して型紙を作り直す』」「断りの字はこのままでよい」）。

見る事:
1. 呼び名のそろった玩具（御来迎・虎）の型紙を印刷する に、口が 1 つ（錨 #think）。見出しと PDF（刷る前は刷る つくる）の後・紙の絵の前。字の欄・1 つの釦・断りの字。
   声を録る釦は置かない。頁の #think は 1 つ（仮説の段には無い）。呼び名のそろわない玩具には出さない（81 種に広げるかは本人の答え待ち）
2. 1 回押すと、字を残して（考え）続けて頼み、頼んだ後の様子の所（at=think-<印>#think）へ戻る。戻った頁の口に様子が出る
3. 字が空の時は頼まずに断る（422）。合言葉なしの場は口を出さず、受け口は 403。受け口は書き込みの数の止めに入る
4. 釦と断りの字は英語とやさしい日本語の表にある
"""
import json
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

from omochae import hypotheses  # noqa: E402
from web import play_server, think_sheet  # noqa: E402
from web.play_server import print_latest  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T, PLAIN = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R", "NDL-1187053-R0000009-L-2"
opener = urllib.request.build_opener(type("NoRedirect", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))


def serve(public=False):
    s = play_server.serve(0, public_open=public)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


def send(base, path, data=None, cookie=""):
    headers = {"Origin": base, **({"Cookie": cookie} if cookie else {})}
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode() if data is not None else None, headers=headers)
    try:
        r = opener.open(req)
    except urllib.error.HTTPError as e:
        r = e
    return getattr(r, "code", None) or r.status, r.read().decode(), dict(r.headers)


def win(page):
    a = page.index('<section class="sec" id="win">')
    return page[a:page.index('id="kiroku"', a)]


server, base = serve()
try:
    # 1
    for sid in (G, T):
        for printed in (False, True):
            if printed:
                assert print_latest(sid, hypotheses.sheet_of(sid)["id"]) is not None, sid
            page = send(base, f"/toy/{sid}")[1]
            w = win(page)
            assert page.count('id="think"') == 1 and w.count('id="think"') == 1, (sid, printed, "口が型紙を印刷する の中に 1 つでない")
            box = w[w.index('id="think"'):]
            box = box[:box.index("</div>") + 6]
            head = w.index("<h2>型紙を印刷する</h2>")
            first = w.index("PDF を開いて印刷する") if printed else w.index(f'action="/toy/{sid}/print#win"')
            assert head < first < w.index('id="think"') < w.index("型紙を刷ります。"), (sid, printed, "見出し → PDF（刷る つくる）→ 口 の順でない")
            if printed:
                assert w.index('id="think"') < w.index('<figure class="sheet">'), (sid, "口が紙の絵の後")
            assert f'action="/toy/{sid}/think-talk#think"' in box and "<textarea" in box and f">{think_sheet.TALK_GO}</button>" in box, (sid, box[:300])
            assert think_sheet.TALK_NOTICE in box and "声を録る" not in box and "hanasu-mic" not in box, (sid, "断りの字が無いか、声を録る釦がある")
            assert box.count("<button") == 1, (sid, "釦が 1 つでない")
            assert 'id="think"' not in page[page.index('id="kasetsu-fuda"'):page.index('id="tatoe"')], (sid, "仮説の段に口が残った")
    page = send(base, f"/toy/{PLAIN}")[1]
    assert 'id="think"' not in page and think_sheet.TALK_GO not in page, "呼び名のそろわない玩具に口を出した"
    # 2
    code, body, h = send(base, f"/toy/{G}/think-talk", {"who": "talkwin0001", "text": "扇をもっと大きく開きたい"})
    assert code == 303 and re.search(rf"^/toy/{G}\?msg=[^&]*&at=think-[A-Za-z0-9_-]+#think$", h.get("Location", "")), (code, h.get("Location"), body[:200])
    key = h["Set-Cookie"].split(";")[0]
    landed = send(base, h["Location"].split("#")[0], cookie=key)[1]
    lw = win(landed)
    assert lw.count('id="think"') == 1 and think_sheet.WAITING in lw[lw.index('id="think"'):], "戻った頁の口に頼んだ後の様子が無い"
    # 3
    code, body, _ = send(base, f"/toy/{G}/think-talk", {"who": "talkwin0002", "text": " "})
    assert code == 422 and 'id="think"' in body, (code, "空の字で頼んだ")
    assert play_server.WRITE_PATHS.fullmatch(f"/toy/{G}/think-talk"), "書き込みの数の止めに入っていない"
finally:
    server.shutdown()
pub, pbase = serve(public=True)
try:
    page = send(pbase, f"/toy/{G}")[1]
    assert 'id="think"' not in page and think_sheet.TALK_GO not in page, "合言葉なしの場に口を出した"
    assert send(pbase, f"/toy/{G}/think-talk", {"who": "talkwin0003", "text": "大きく"})[0] == 403, "合言葉なしの場の受け口が開いている"
finally:
    pub.shutdown()
# 4
en = json.loads((ROOT / "data/i18n/en.json").read_text(encoding="utf-8"))["strings"]
easy = {}
for f in sorted((ROOT / "data/i18n/yasashii.d").glob("*.json")):
    easy.update(json.loads(f.read_text(encoding="utf-8"))["strings"])
for t in (think_sheet.TALK_GO, think_sheet.TALK_NOTICE):
    assert t in en and t in easy, t
print("ok 型紙を印刷する の中の作り直しの口: 御来迎と虎に 1 つ（見出しと PDF の後・紙の絵の前）・1 回で字を残して頼む・空は断る・公開の場は閉じる・訳の表にある")
