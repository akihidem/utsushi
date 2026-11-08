"""安全の事項 5 への対応の試験: 合言葉なしの公開の場では、立てた後に鍵が置かれても、どの AI の口も Claude を呼ばない。本物の API は呼ばない。

前は、立てる時（serve）の鍵の確かめだけで公開の場の AI を閉じていて、手順の質問の口（/toy/<玩具>/ask と /ask-json）は、立てた後に鍵が
置かれると Claude を呼べた（鍵の有り無しは呼ぶたびに読み直すため）。ここでは「立てた後に鍵が置かれた」形を偽の鍵と偽の Claude で作り、
1. 公開の場: 手順の質問（/ask・/ask-json）・記録の解釈と観察（ai-interpret・ai-observe）・話した考えから紙を作る口（think-sheet）・
   作業の頁の聞く口（kasane/ask）のどれも Claude を呼ばない。返す字は、鍵が無い時の字のまま（頁の見た目と挙動を替えない）
2. 見比べ: 合言葉の場では、同じ偽の鍵で手順の質問が偽の Claude まで届く（この試験の差し替えが効いている事の確かめ）
"""
import json
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from types import SimpleNamespace

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tempfile.mkdtemp(), "api-usage.jsonl")
os.environ.pop("ANTHROPIC_API_KEY", None)

from api import agent, ask  # noqa: E402
from omochae import hypotheses, loop, records  # noqa: E402
from web import hmd, play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
HG = hypotheses.sheet_of(G)["id"]
CALLS = []


class FakeClaude:
    def __init__(self, role=None):
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **req):
        CALLS.append(req.get("model"))
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="偽の答え")], usage=SimpleNamespace(input_tokens=1, output_tokens=1))


def start(public_open):
    server = play_server.serve(0, public_open=public_open)  # 立てる時は鍵が無い（公開の場は鍵があると立たない）
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def post(base, path, data, ctype="application/x-www-form-urlencoded"):
    body = data if isinstance(data, bytes) else urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(base + path, data=body, headers={"Content-Type": ctype, "Origin": base})
    op = urllib.request.build_opener(type("N", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))
    try:
        r = op.open(req, timeout=120)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


pub, pbase = start(True)
lan, lbase = start(False)
try:
    for base in (pbase, lbase):  # 質問の口は刷った紙について聞くので、先に刷る
        assert post(base, f"/toy/{G}/print", {"hypothesis": HG})[0] == 303, base
    # ここから「立てた後に鍵が置かれた」形（鍵の有り無しを読む所と、Claude の口を偽にする）
    ask._key_present = lambda: True
    agent.default_client = lambda role=None: FakeClaude(role)

    # 1. 公開の場
    code, page = post(pbase, f"/toy/{G}/ask", {"hypothesis": HG, "question": "竹串はいつ通すの？"})
    assert code == 200 and ask.NO_KEY in page, ("手順の質問は、鍵が無い時の字のまま", code)
    code, got = post(pbase, f"/toy/{G}/ask-json", {"hypothesis": HG, "question": "竹串はいつ通すの？", "who": "a" * 22})
    assert code == 200 and json.loads(got) == {"text": ask.NO_KEY, "from": "no_key"}, (code, got)
    # 語の問いと仕組みの問いは前のとおり（Claude を呼ばない口のまま）
    code, got = post(pbase, f"/toy/{G}/ask-json", {"hypothesis": HG, "question": "谷折りって何", "who": "a" * 22})
    assert json.loads(got)["from"] == "glossary", got
    rid, _ = records.add({"source_id": G, "hypothesis_id": HG, "sheet_version": 1, "result": "動いた"})
    assert not loop.save_explanation(rid, "本人", "開いた", "速く押す")
    for act in ("ai-interpret", "ai-observe"):
        assert post(pbase, f"/record/{rid}/{act}", {"back": "techo"})[0] == 403, act
    code, _ = post(pbase, f"/toy/{G}/think-sheet", {"who": "a" * 22})
    assert code == 403, ("話した考えから紙を作る口は、公開の場では前から閉じている（Claude は呼ばない）", code)
    code, got = post(pbase, f"/toy/{G}/kasane/ask", json.dumps({"step": 1, "type": "audio/webm", "voice": "dg==", "frames": []}).encode(), "application/json")
    assert code == 403 and json.loads(got)["text"] == hmd.ASK_PUBLIC, (code, got)
    assert CALLS == [], ("公開の場で Claude を呼んだ", CALLS)

    # 2. 見比べ: 合言葉の場（公開でない場）では、同じ差し替えで手順の質問が偽の Claude まで届く
    code, got = post(lbase, f"/toy/{G}/ask-json", {"hypothesis": HG, "question": "竹串はいつ通すの？", "who": "b" * 22})
    assert code == 200 and json.loads(got) == {"text": "偽の答え", "from": "ai"} and len(CALLS) == 1, (code, got, CALLS)
finally:
    for s in (pub, lan):
        s.shutdown()
        s.server_close()
print("ok 公開の場では、立てた後に鍵が置かれても、どの AI の口も Claude を呼ばない（返す字は鍵が無い時のまま）")
