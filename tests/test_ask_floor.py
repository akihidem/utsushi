"""聞く口にも話す口と同じ入口の床を当てる（#87）。手帖は 1 回押した後は聞き続けるので、名乗りや連絡先の形の話し声も字になって届く。

当たった字は Claude へ送らない・字を残さない・束にも入らない・落とした数だけ数える。返す字は採られた文。当たらない問いは今までどおり答える。
"""
import json
import os
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from api import ask  # noqa: E402
from omochae import engine_bundle, making_log, talk_log  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
from omochae import hypotheses  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    with urllib.request.urlopen(r, timeout=120) as x:
        return x.status, x.read().decode()


assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] == 200
sent = []
real = ask.answer
ask.answer = lambda sid, hid, q: (sent.append(q), ("答えの字", "claude"))[1]
try:
    # 床に当たる形: 連絡先・名乗り・学年と組・学校の名前
    BLOCKED = ("電話は090-1234-5678", "3年2組の田中です", "さくら小学校の田中です", "ぼくの名前は田中")
    for q in BLOCKED:
        assert talk_log.blocked(q), q
        code, body = post(f"/toy/{G}/ask-json", {"hypothesis": GS, "question": q, "step": "2", "who": "abcde12345"})
        j = json.loads(body)
        assert code == 200 and j["text"] == making_log.ASK_NAME_VOICE and j["from"] == "floor", (q, j)
    assert not sent, ("床に当たった字を Claude へ送った", sent)
    # JS が無い時の聞く口も同じ
    code, page = post(f"/toy/{G}/ask", {"hypothesis": GS, "question": "3年2組の山田です"})
    assert code == 200 and making_log.ASK_NAME_VOICE in page and not sent, sent
    # 字は残らず、数だけ残る。作る側の集計と束にも字が入らない
    kept = making_log.asks(G)
    assert len(kept) == len(BLOCKED) + 1 and all(a["dropped"] and not a["question"] for a in kept), kept
    assert sorted(a["dropped"] for a in kept).count("pii") == 1, "連絡先の形は今までと同じ印"
    assert making_log.summary(G)["asks_dropped"] == len(BLOCKED) + 1
    bundle = json.dumps(engine_bundle.build(), ensure_ascii=False)
    for word in ("田中", "山田", "090-1234", "さくら小学校", "3年2組"):
        assert word not in bundle, word
    assert engine_bundle.build()["dropped_pii"] >= len(BLOCKED) + 1
    # 当たらない問いは今までどおり答えて残す
    code, body = post(f"/toy/{G}/ask-json", {"hypothesis": GS, "question": "穴はどこにあける？", "step": "2"})
    assert json.loads(body)["text"] == "答えの字" and sent == ["穴はどこにあける？"], sent
    assert any(a["question"] == "穴はどこにあける？" and not a.get("dropped") for a in making_log.asks(G))
finally:
    ask.answer = real
    server.shutdown()
print("ok 聞く口の床: 当たった字は送らず残さず、数だけ残る")
