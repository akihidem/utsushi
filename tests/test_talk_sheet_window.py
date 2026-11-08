"""型紙を印刷する（玩具の頁の #win）の中の「Claude に話して型紙を作り直す」口（本人の言葉 11-08「版が若いものは、型紙を出力する前に、自分で仮説を話して
よくしてから作りたいと思うと思う。型紙のところに、クロードに自分の考えを話して型紙を改善するボタンを設置して、再生成してもらうボタンをつけたい。」・
設計 grove の state/tsukuru-talk-sheet-20261108.md 2 版・本人の答え 11-08「釦は 1 つ『Claude に話して型紙を作り直す』」「断りの字はこのままでよい」）。

見る事:
1. 呼び名のそろった玩具（御来迎・虎）の型紙を印刷する に、口が 1 つ（錨 #think）。見出しと PDF（刷る前は刷る つくる）の後・紙の絵の前。字の欄・1 つの釦・断りの字。
   声を録る釦は置かない。頁の #think は 1 つ（仮説の段には無い）。呼び名のそろわない玩具には出さない（81 種に広げるかは本人の答え待ち）
2. 1 回押すと、字を残して（考え）続けて頼み、頼んだ後の様子の所（at=think-<印>#think）へ戻る。戻った頁の口に様子が出る
3. 字が空の時は頼まずに断る（422）。合言葉なしの場は口を出さず、受け口は 403。受け口は書き込みの数の止めに入る
4. 釦と断りの字は英語とやさしい日本語の表にある
5. 断る時はこの口の字で、Claude に頼まない（W-番号を作らない）: 名前などの言葉（TALK_BLOCKED）・空（TALK_EMPTY）・画面の印が無い（JS の無い画面・TALK_NO_SCREEN）。
   呼び名のそろわない玩具の受け口は 404。作る側の待ちの間は、釦を出さず待ちの字（TALK_WAITING）（押すと新しく頼み、1 日の回数が減るため）
   （別の目の検品 11-08 #714 の 1〜3）
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

from omochae import hypotheses, loop  # noqa: E402
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
            box = w[w.index('id="think"'):w.index("型紙を刷ります。")]  # 口の箱（中に返事の文の div が入りうるので、次の字の所まで）
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
    box = lw[lw.index('id="think"'):lw.index("型紙を刷ります。")]
    # 鍵の無い場なので作る側の待ち。待ちの字が出て、頼む釦は出ない（5）
    assert think_sheet.TALK_WAITING in box and think_sheet.WAITING not in box, "戻った頁の口に待ちの字が無い"
    assert "think-talk" not in box and "<button" not in box, "待ちの間に頼む釦を出した"
    # 3・5
    words_n = lambda: len(list(loop.folder().glob("words-*.json")))
    for form, want in (({"who": "talkwin0002", "text": " "}, think_sheet.TALK_EMPTY),
                       ({"who": "talkwin0004", "text": "電話番号は 090-1234-5678 です"}, think_sheet.TALK_BLOCKED),
                       ({"text": "扇を大きく"}, think_sheet.TALK_NO_SCREEN)):
        before = words_n()
        code, body, _ = send(base, f"/toy/{G}/think-talk", form)
        assert code == 422 and want in body and words_n() == before, (form, code, "この口の字で断らないか、Claude に頼んだ")
        for old in ("「残す」", "聞き取れませんでした", think_sheet.NONE):
            assert old not in body[body.index('id="think"'):body.index('id="think"') + 1500], (form, old, "前の口の字が出た")
    assert send(base, f"/toy/{PLAIN}/think-talk", {"who": "talkwin0005", "text": "大きく"})[0] == 404, "呼び名のそろわない玩具の受け口が開いている"
    # 字を残した後の止め（残した考えが選べない・頼み済みの案の鍵が閉じている時など）も、この口の字（前の口の NONE を出さない・#721 の別の目の気づき）
    from api import words  # noqa: E402

    keep_latest = words.latest_think
    words.latest_think = lambda sid, who: (None, None)
    try:
        before = words_n()
        code, body, _ = send(base, f"/toy/{G}/think-talk", {"who": "talkwin0006", "text": "扇を大きく"})
        assert code == 422 and think_sheet.TALK_NO_SCREEN in body and think_sheet.NONE not in body and words_n() == before, (code, "字を残した後の止めで前の字が出た")
    finally:
        words.latest_think = keep_latest
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
for t in (think_sheet.TALK_GO, think_sheet.TALK_NOTICE, think_sheet.TALK_BLOCKED, think_sheet.TALK_EMPTY, think_sheet.TALK_NO_SCREEN, think_sheet.TALK_WAITING):
    assert t in en and t in easy, t
print("ok 型紙を印刷する の中の作り直しの口: 御来迎と虎に 1 つ（見出しと PDF の後・紙の絵の前）・1 回で字を残して頼む・この口の字で断り頼まない・待ちの間は釦なし・404 と 403・訳の表にある")
