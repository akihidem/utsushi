"""無い記録の番号へ送った時は 404 にする（公開の前の点検、J-028）。

なぜ: 説明・次の版・AI の 2 つの口は記録を読む所で落ち、「少し待って、もう一度送ってください」の 500 を返していた。
送り直しても直らない案内で、説明の口は合言葉なしの場の誰でも押せた。打ち間違いの番号や、取り下げた後の古い頁から届く形。
"""
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
FORM = {"text": "折りが固い", "next_idea": "幅を変える", "by": "大人", "param": "fold_count", "to": "13", "why": "理由", "interpretation": "読み"}


def start(public):
    s = serve(0, public_open=public)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{s.server_address[1]}", s


def post(base, path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    try:
        with urllib.request.urlopen(r) as res:
            return res.status, res.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


closed, cs = start(False)
opened, os_ = start(True)
for act in ("explain", "next", "ai-interpret", "ai-observe"):
    st, body = post(closed, f"/record/R-9999/{act}", FORM)
    assert st == 404 and "もう一度送って" not in body, (act, st, body[-200:])
st, body = post(opened, "/record/R-9999/explain", FORM)
assert st == 404 and "もう一度送って" not in body, ("合言葉なしの場の説明の口", st)
for act in ("next", "ai-interpret", "ai-observe"):
    assert post(opened, f"/record/R-9999/{act}", FORM)[0] == 403, ("合言葉なしの場では今までどおり閉じた口", act)

# 対照: ある記録へは今までどおり。説明は残り、玩具の頁の記録の札へ戻る
assert post(closed, f"/toy/{G}/print", {"hypothesis": "H-A"})[0] in (200, 303)
assert post(closed, f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた"})[0] in (200, 303)
st, body = post(closed, "/record/R-0001/explain", FORM)
assert st == 200 and "説明を残しました" in body, (st, body[-200:])
cs.shutdown()
os_.shutdown()
print("ok: 無い記録の番号へ送った時は 404")
