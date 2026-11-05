"""作りながら見る（観察 A の試作）。本人の案の具体化（11-05 朝）「端末を机の端に置いて…作成の様子を見れるようにする」の一番浅い段。

見る線: 映像は端末の中だけ（画素を取り出す・録る・送る JS が頁に無い）。残るのは字と数だけ（手順の番号と出来事。人の印は持たない）。
予想の前と刷る前は開かない。手順の文は手順の紙と同じ物。止まった手順の数は作る側の頁だけに出し、学ぶ人の頁には出さない。本物の API は呼ばない。
"""
import html
import json
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA

from omochae import hypotheses, making_log  # noqa: E402
from web import tsukuru  # noqa: E402
from web.kazasu import PRIVACY  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def get(path):
    # 絵（PNG）も同じ口で取るので、字にできない所は置き換える（見るのは返事の番号だけ）
    try:
        r = opener.open(base + path)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def post(path, data, origin=None):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": origin or base})
    try:
        r = opener.open(req)
        return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)


def step(n, event, hid="H-A", **more):
    return post(f"/toy/{G}/step", {"hypothesis": hid, "step": str(n), "event": event, **more})


# 予想の前は開かない（札も受けない）
body = get(f"/toy/{G}/tsukuru")[1]
assert "先に予想を書くと、作りながら見る頁が開きます" in body and 'class="tsukuru' not in body
assert step(1, "next")[0] == 422
assert post(f"/toy/{G}/predict", {"text": "筒を持つと扇が開くと思う"})[0] == 303
# 刷る前は開かない。玩具の頁に入口も出さない
body = get(f"/toy/{G}/tsukuru")[1]
assert "先に紙を刷ると、作りながら見る頁が開きます" in body and 'class="tsukuru' not in body
assert step(1, "next")[0] == 422 and f'href="/toy/{G}/tsukuru"' not in get(f"/toy/{G}")[1]
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303
assert f'href="/toy/{G}/tsukuru"' in get(f"/toy/{G}")[1]

# 開く: 手順の文（手順の紙と同じ物）と、手順の紙の絵、断り
code, t = get(f"/toy/{G}/tsukuru")
assert code == 200 and 'class="tsukuru' in t
texts = tsukuru.step_texts(G, "H-A")
assert len(texts) >= 3 and all(html.escape(s, quote=True) in t for s in texts)
assert f'<img class="sheet" src="/sheet/{G}/H-A_v1_tejun.png"' in t and get(f"/sheet/{G}/H-A_v1_tejun.png")[0] == 200
assert tsukuru.NOTICE in t and PRIVACY in t and "次の手順へ" in t and "止まった" in t and "できた" in t
# 刷っていない紙は h で指しても開かない
assert 'class="tsukuru' not in get(f"/toy/{G}/tsukuru?h=H-B")[1]
# 映像は端末の中だけ: 画素を取り出す・録る・送る JS が無い。送るのは聞く口と札（form の欄）だけ
for w in ("canvas", "toBlob", "toDataURL", "MediaRecorder", "captureStream", "ImageCapture", "WebSocket", "sendBeacon", "XMLHttpRequest", "IntersectionObserver"):
    assert w not in t, w
assert set(re.findall(r"fetch\(`([^`]+)`", t)) == {"/toy/${sid}/step", "/toy/${sid}/ask-json"} and t.count("fetch(") == 2
assert "audio:false" in t and "100svh" in t and "prefers-reduced-motion" in t
# 仮説の名前と動かし方は出さない（字と版だけ）。成績の言葉と祝いの演出も無い
for h in hypotheses.load(G)["hypotheses"]:
    assert h["name"] not in t and h["how_it_moves"] not in t, h["id"]
for w in ("成功", "失敗", "正解", "順位", "点数", "紙吹雪", "confetti", "おめでとう"):
    assert w not in t, w

# 札: 押した事だけが残る（欄はちょうど決めた 6 つ。人の印は無い）
code, body, _ = step(1, "start", json="1")
assert code == 200 and json.loads(body) == {"ok": True, "step": 1}
code, _, headers = step(1, "next")
assert code == 303 and headers["Location"] == f"/toy/{G}/tsukuru?h=H-A&n=2"
assert json.loads(step(2, "back", json="1")[1])["step"] == 1
assert step(2, "stuck")[0] == 303 and step(2, "stuck", json="1")[0] == 200 and step(3, "stuck", json="1")[0] == 200
assert step(len(texts), "next", json="1")[1] == json.dumps({"ok": True, "step": len(texts)}), "最後の手順より先へは進まない"
code, _, headers = step(len(texts), "done")
assert code == 303 and headers["Location"].endswith("&ev=done")
files = sorted((pathlib.Path(DATA) / "making").glob("step-*.json"))
assert len(files) == 8
for f in files:
    rec = json.loads(f.read_text(encoding="utf-8"))
    assert set(rec) == set(making_log.STEP_FIELDS), rec
    assert rec["source_id"] == G and rec["hypothesis_id"] == "H-A" and rec["sheet_version"] == 1 and isinstance(rec["step"], int)
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d\+09:00", rec["at"]), rec["at"]  # 分まで
    assert re.fullmatch(r"step-\d{8}-\d{4}-[0-9a-f]{8}\.json", f.name), f.name
sm = making_log.summary(G)
assert sm["stuck_steps"] == {2: 2, 3: 1} and sm["steps_done"] == 1
# 止まった・できたの文は、押した時だけ出る（JS が無い時は ?ev= で出す）
assert '<p id="msg-stuck" class="msg" hidden>' in t and '<p id="msg-done" class="msg" hidden>' in t
assert '<p id="msg-stuck" class="msg">' in get(f"/toy/{G}/tsukuru?h=H-A&n=2&ev=stuck")[1]
assert '<p id="msg-done" class="msg">' in get(f"/toy/{G}/tsukuru?h=H-A&n=2&ev=done")[1]
# 作る側の頁に、止まった手順とできたの回数。学ぶ人の頁には出さない
lp = get(f"/loop/{G}")[1]
assert "止まった手順" in lp and "<td>手順 2</td><td>2 回</td>" in lp and "<td>手順 3</td><td>1 回</td>" in lp and "できたの札: 1 回" in lp
toy = get(f"/toy/{G}")[1]
assert "止まった手順" not in toy and "できたの札" not in toy and "2 回" not in toy
# 決まりの外は 422（知らない札・数でない番号・手順の数の外・無い仮説・刷っていない紙）。何も残らない
for bad in (step(1, "win"), step("abc", "next"), step(0, "next"), step(999, "next"), step(1, "next", hid="H-Z"), step(1, "next", hid="H-B")):
    assert bad[0] == 422, bad[:2]
assert len(list((pathlib.Path(DATA) / "making").glob("step-*.json"))) == 8
# 別の出所からは受けない
assert post(f"/toy/{G}/step", {"hypothesis": "H-A", "step": "1", "event": "next"}, origin="http://evil.example")[0] == 403
# 道具の側: 決まりの外は残さない
assert making_log.add_step(G, "H-A", 1, 1, "win") is None and making_log.add_step(G, "H-A", 1, 0, "next") is None and making_log.add_step(G, "H-A", 1, True, "next") is None
print("ok: 作りながら見る")
