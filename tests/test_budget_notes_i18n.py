"""予算の止めの字（api.budget.BudgetStop.NOTES）が、英語とやさしい日本語の頁でも頁の言葉で出る（統括の割り振り 11-08・#692 の別の目の気づき）。

なぜ: 止めの字 3 つが訳の表に無く、英語の頁でも日本語のまま出た。聞く口（/toy/<玩具>/ask-json）は JSON で返すので、頁の出口の訳
（web.i18n）を通らず、表に足すだけでも日本語のまま出る。出す所で頁の言葉に合わせる（play_server の Handler._say）。日本語の字は替えない。

見る事:
1. 止めの字 3 つと、聞く口の「今は AI に聞けません（…）」の形 3 つが、英語の表とやさしい日本語の表にある（英語の値に日本語が残らない）
2. 頁（HTML）では出口の訳で替わる（「今は AI に聞けません（…）」が英語の頁で英語）
3. 聞く口の JSON: 予算の止めの時、英語の頁は英語、やさしい日本語の頁はルビの印を外したやさしい日本語、日本語の頁は日本語の字のまま
"""
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api.budget import BudgetStop  # noqa: E402
from omochae import hypotheses  # noqa: E402
from web import i18n, play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
GS = hypotheses.sheet_of(G)["id"]
NOTES = BudgetStop.NOTES
assert set(NOTES) == {"day", "total", "run"}

# 1. 表にある
for kind, ja in NOTES.items():
    for text in (ja, f"今は AI に聞けません（{ja}）"):
        en = i18n.lookup(text)
        easy = i18n.lookup(text, "easy")
        assert en and en != i18n.KEEP and not i18n.CJK.search(en), ("英語の表に無い", kind, text, en)
        assert easy and easy != i18n.KEEP, ("やさしい日本語の表に無い", kind, text)
# 2. 頁の出口の訳
page = i18n.page_en(f'<html lang="ja"><body><p>今は AI に聞けません（{NOTES["day"]}）</p></body></html>')
assert i18n.lookup(f"今は AI に聞けません（{NOTES['day']}）") in page and "予算" not in page, page[-200:]

# 3. 聞く口の JSON
srv = play_server.serve(0)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"


def post(path, data, lang=None):
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": base}
    if lang:
        headers["Cookie"] = f"utsushi_lang={lang}"
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers=headers)
    op = urllib.request.build_opener(type("N", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))
    try:
        x = op.open(r)
        return x.status, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


try:
    assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] == 303
    for kind, ja in NOTES.items():
        def stop(self, *a, kind=kind, **k):
            raise BudgetStop("額の入った文（画面に出さない）", kind)
        play_server.Handler._ask = stop
        ja_text = f"今は AI に聞けません（{ja}）"
        for lang, want in ((None, ja_text), ("en", i18n.lookup(ja_text)), ("easy", i18n.ruby_plain(i18n.lookup(ja_text, "easy")))):
            code, body = post(f"/toy/{G}/ask-json", {"hypothesis": GS, "question": "竹串はいつ通すの？"}, lang)
            got = json.loads(body)
            assert code == 200 and got["from"] == "stop" and got["text"] == want, (kind, lang, got)
            assert "額" not in got["text"] and not re.search(r"[｜《》]", got["text"]), (kind, lang, got)
finally:
    srv.shutdown()
print("ok 予算の止めの字 3 つ: 英語とやさしい日本語の表にあり、頁は出口の訳で、聞く口の JSON は頁の言葉に合わせて返る。日本語の字は前のまま")
