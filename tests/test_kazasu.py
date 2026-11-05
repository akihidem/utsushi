"""かざして選ぶ（試作）の試験。本人の案（11-05 朝）: 内カメラの自分の映像に原図を重ねて見せ、どう動くと思うかを札のタップで選ぶ。本物の API は呼ばない。

見る線:
- 映像は端末の外へ出さない。頁の JS に、画素を取り出す・録る・網へ送る物が無い（canvas・toBlob・toDataURL・MediaRecorder・fetch・XMLHttpRequest・sendBeacon）。
  サーバへ行くのは、押した札の印（フォームの送信）だけ。
- 札は仮説の動かし方の文だけ。名前・字（仮説 A）・根拠は出さない。成績の言葉も出さない（J-025）。
- 選ぶと予想として残り（文に仮説の印を入れない）、仮説の所へ戻る。無い札は 422、別の出所からは 403。
- カメラが無くても同じ札で選べる。文字で書く今の道は残る。
"""
import json
import os
import pathlib
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA

from omochae import hypotheses  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
data = hypotheses.load(G)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def up(look):
    server = serve(0, look=look)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"


base = up("tenji")


def get(path, b=None):
    try:
        r = opener.open((b or base) + path)
        return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)


def post(path, form, origin=None):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(form).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": origin or base})
    try:
        r = opener.open(req)
        return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)


# 入口: 予想の前の玩具の頁から行ける。文字で書く道も残っている
code, toy, _ = get(f"/toy/{G}")
assert code == 200 and f'href="/toy/{G}/kazasu"' in toy and "先に、予想を書く" in toy and f'action="/toy/{G}/predict"' in toy
# 予想の前の玩具の頁には、今までどおり仮説の中身を出さない
for h in data["hypotheses"]:
    assert h["name"] not in toy and h["how_it_moves"] not in toy

code, page, _ = get(f"/toy/{G}/kazasu")
assert code == 200
# 札: 動かし方の文だけ。名前・字・根拠は出さない
import re  # noqa: E402

from web import kazasu  # noqa: E402

cards = kazasu.cards(data)
assert [c[0] for c in cards] == [h["id"] for h in data["hypotheses"]], "御来迎は動かし方が全部違うので、札は仮説の数だけ"
for hid, text, _ in cards:
    assert f'<button name="hypothesis" value="{hid}">{text}</button>' in page, hid
for h in data["hypotheses"]:
    assert h["name"] not in page, h["id"]
    for e in h["evidence"]:
        assert e["what"] not in page
assert "仮説 A" not in page and "仮説 B" not in page
# 札の文に仮説の印（H-C など）を出さない。印が出る注の一文は落とす（印は送る値にだけある）
shown = re.sub(r'value="[^"]*"', "", page)
assert not re.search(r"H-[A-Z0-9]", shown), re.findall(r".{12}H-[A-Z0-9].{6}", shown)
assert any("H-" in h["how_it_moves"] for h in data["hypotheses"]), "この試験の前提: 御来迎の動かし方の文に印が出る一文がある"
# 並びは記録の並び
order = [page.index(f'value="{hid}"') for hid, _, _ in cards]
assert order == sorted(order)
# 動かし方の文が同じ仮説は 1 枚にまとめる（虎の A と B は、する事が同じ）
T = "NDL-1187053-R0000014-R"
tcards = kazasu.cards(hypotheses.load(T))
texts = [c[1] for c in tcards]
assert len(texts) == len(set(texts)) and any(len(c[2]) > 1 for c in tcards), tcards
tpage = get(f"/toy/{T}/kazasu")[1]
for _, text, _ in tcards:
    assert tpage.count(f">{text}</button>") == 1, text
# 映像は端末の外へ出さない: 画素を取り出す・録る・送る物が無い。カメラは求める形だけ
for bad in ("<canvas", "toBlob", "toDataURL", "MediaRecorder", "fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "captureStream", "ImageCapture"):
    assert bad not in page, bad
assert "getUserMedia" in page and "facingMode:'user'" in page and "audio:false" in page
assert "playsinline" in page and "muted" in page and "getTracks().forEach(t=>t.stop())" in page
assert "映像はこの端末の中だけで、送りも残しもしません。" in page and "カメラは使わずに選べます" in page
# 開いただけではカメラを求めない（押した時か、確かめ用の ?cam=1 の時だけ）
assert "addEventListener('click',start)" in page and "get('cam')==='1'" in page
# 画面の線
assert "100svh" in page and "prefers-reduced-motion" in page and "IntersectionObserver" not in page and "whileInView" not in page
for w in ("成功", "失敗", "正解", "順位", "点数", "当たり"):
    assert w not in page, w
# どれでもない → 文字で書く道。聞く口（手帖）は選んだ後
assert f'href="/toy/{G}#yosou"' in page and "手帖" in page
# 皮: 黒のジンのサイトでは黒の変数
assert "--bg:#fcfcfa" in page and "--bg:#0b0a09" in get(f"/toy/{G}/kazasu", up("zine"))[1]

# 無い札は 422、別の出所からは 403。どちらも予想は残らない
assert post(f"/toy/{G}/predict-choice", {"hypothesis": "H-Z"})[0] == 422
assert post(f"/toy/{G}/predict-choice", {"hypothesis": "H-B"}, origin="http://evil.example")[0] == 403
assert not hypotheses.predictions(G)

# 選ぶ: 予想として残り、仮説の所へ戻る
hb = next(h for h in data["hypotheses"] if h["id"] == "H-B")
code, _, headers = post(f"/toy/{G}/predict-choice", {"hypothesis": "H-B"})
loc = headers.get("Location", "")
assert code == 303 and loc.startswith(f"/toy/{G}?") and "see=H-B" in loc and loc.endswith("#kasetsu"), (code, loc)
preds = hypotheses.predictions(G)
assert len(preds) == 1
rec = json.loads(preds[0].read_text(encoding="utf-8"))
hb_text = next(c[1] for c in cards if c[0] == "H-B")
assert rec["text"] == f"かざして選んだ: {hb_text}" and "H-" not in rec["text"] and hb["name"] not in rec["text"]
assert rec["via"] == "kazasu" and rec["choice"] == "H-B" and rec["by"] == "human" and "same_action" not in rec
code, toy, _ = get(loc.split("#")[0])
assert code == 200 and "予想を残しました。紙で確かめます" in toy and "かざして選んだ" in toy
# 仮説が開く（予想の後）。選んだ札を特別扱いしない: 並びは元のまま
assert "仮説 A" in toy and toy.index("仮説 A「") < toy.index("仮説 B「")
# 映像の置き場が無い事: 記録の置き場に増えたのは予想の 1 本だけ
files = sorted(p.name for p in pathlib.Path(DATA).rglob("*") if p.is_file())
assert files == [preds[0].name], files
# まとめた札を選ぶと、同じ文だった仮説の印が全部残る。まとめられて札にならなかった印は受けない
first, _, same = next(c for c in tcards if len(c[2]) > 1)
assert post(f"/toy/{T}/predict-choice", {"hypothesis": same[1]})[0] == 422
assert post(f"/toy/{T}/predict-choice", {"hypothesis": first})[0] == 303
trec = json.loads(hypotheses.predictions(T)[0].read_text(encoding="utf-8"))
assert trec["choice"] == first and trec["same_action"] == same
print("ok: かざして選ぶ（試作）")
