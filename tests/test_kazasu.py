"""かざして選ぶ（U-44、Issue #118）の試験。本人の案（11-05 朝）: 内カメラの自分の映像に原図を重ねて見せ、タップで選ぶ。本物の API は呼ばない。

見る線（Issue #118 のゴールの要件のうち、機械で見られる物）:
- 予想の前に、仮説の名前と仕組みの文が出ない。選ぶ物は「動く所の候補の絵」（原図の上の枠と、部品の呼び名）だけ。
- 映像は端末の外へ出さない。頁の JS に、画素を取り出す・録る・網へ送る物が無い。サーバへ行くのは、押した候補の印（フォームの送信）だけ。
- 候補を選ぶと、予想として残る（kind: choice）。無い候補は 422、別の出所からは 403。
- 候補を置いたのは必須の 2 種だけ。候補の無い玩具では、動かし方の文を札にしない。
- 重ねた絵は指で動かせる（pointer の出来事と CSS の transform。画素には触らない）。
- 必須の 2 種の仮説の中身（寸法など）は変えない。足したのは move_candidates だけ。
"""
import hashlib
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

from omochae import hypotheses  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402
from web import kazasu  # noqa: E402
from web.play_server import serve  # noqa: E402

G, T, OTHER = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R", "NDL-1187053-R0000016-L"


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


# 候補の置き場: 必須の 2 種の仮説の記録にだけ在り、2〜3 枚。箱は写しに対する 0〜1 の割合。呼び名は部品の名前だけ
with_cands = sorted(p.stem for p in (ROOT / "data/hypotheses").glob("NDL-*.json") if json.loads(p.read_text(encoding="utf-8")).get("move_candidates"))
assert with_cands == [G, T], with_cands
for sid in (G, T):
    raw = json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8"))
    cs = raw["move_candidates"]
    assert 2 <= len(cs) <= 3 and kazasu.candidates(raw) == cs, sid
    assert len({c["id"] for c in cs}) == len(cs) and all(re.fullmatch(r"[a-z]+", c["id"]) for c in cs), sid
    for c in cs:
        assert set(c) == {"id", "label", "box"} and len(c["label"]) <= 8, c
        x0, y0, x1, y1 = c["box"]
        assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, c
        # 呼び名に、仮説の名前・動かし方の言葉・成績の言葉を入れない
        for h in raw["hypotheses"]:
            assert c["label"] not in h["name"] or len(c["label"]) <= 2, (c["label"], h["name"])
        for w in ("押", "引", "上げ", "下げ", "揺", "開", "回", "吹", "あお"):
            assert w not in c["label"], (c["label"], w)
# 必須の 2 種の仮説の中身は変えない（寸法・名前・根拠）。足したのは move_candidates だけ。指紋は、足す前の記録から取った値
FINGERPRINT = {G: "37d71d75fbebd8f2", T: "cd34b20ec3e677b3"}
for sid, fp in FINGERPRINT.items():
    raw = json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8"))
    got = hashlib.sha256(json.dumps(raw["hypotheses"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    assert got == fp, (sid, got, "仮説の中身が変わった。変えたのなら、理由を書いてこの指紋を直す")

# 入口: 予想の前の玩具の頁から行ける。文字で書く道も残っている。予想の前の頁には、今までどおり仮説の中身を出さない
data = hypotheses.load(G)
code, toy, _ = get(f"/toy/{G}")
assert code == 200 and f'href="/toy/{G}/kazasu"' in toy and "先に、予想を書く" in toy and f'action="/toy/{G}/predict"' in toy
for h in data["hypotheses"]:
    assert h["name"] not in toy and h["how_it_moves"] not in toy

pages = {}
for sid in (G, T):
    d = hypotheses.load(sid)
    code, page, _ = get(f"/toy/{sid}/kazasu")
    assert code == 200
    pages[sid] = page
    # 候補の絵: 2〜3 枚。同じ写しの上に枠を重ねる（新しい画像は作らない）。札の字は呼び名だけ
    cs = kazasu.candidates(d)
    assert page.count('class="cand"') == len(cs) and 2 <= len(cs) <= 3, sid
    for c in cs:
        assert f'name="choice" value="{c["id"]}"' in page and f'<span class="lb">{c["label"]}</span>' in page, c
    assert page.count('class="mark"') == len(cs) and page.count(f"background-image:url(/picture/{sid})") == len(cs) + 1
    order = [page.index(f'value="{c["id"]}"') for c in cs]
    assert order == sorted(order), "並びは記録の並び"
    # 予想の前に、仮説の名前・動かし方の文・根拠・字・印を出さない（F9.prediction）
    for h in d["hypotheses"]:
        assert h["name"] not in page and h["how_it_moves"] not in page, (sid, h["id"])
        for part in h["how_it_moves"].split("。"):
            assert not part.strip() or part.strip() not in page, (sid, part)
        for e in h["evidence"]:
            assert e["what"] not in page
    assert "仮説 A" not in page and "仮説 B" not in page and not re.search(r"H-[A-Z0-9]", page) and 'name="hypothesis"' not in page
    # 映像は端末の外へ出さない: 画素を取り出す・録る・送る物が無い。カメラは求める形だけ
    for bad in ("<canvas", "canvas", "toBlob", "toDataURL", "MediaRecorder", "fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "captureStream", "ImageCapture", "getImageData"):
        assert bad not in page, bad
    assert "getUserMedia" in page and "facingMode:'user'" in page and "audio:false" in page
    assert "playsinline" in page and "muted" in page and "getTracks().forEach(t=>t.stop())" in page
    assert "映像はこの端末の中だけで、送りも残しもしません。" in page and "カメラは使わずに選べます" in page
    # 開いただけではカメラを求めない（押した時か、確かめ用の ?cam=1 の時だけ）
    assert "addEventListener('click',start)" in page and "get('cam')==='1'" in page
    # 重ねた絵は指で動かせる: pointer の出来事と CSS の transform。つまみ（大きさ）と、元の位置へ戻す釦
    assert 'id="pic"' in page and "pointerdown" in page and "pointermove" in page and "touch-action:none" in page
    assert "translate(var(--tx" in page and "scale(var(--sc" in page and 'type="range" id="size"' in page and 'id="reset"' in page
    # 画面の線
    assert "100svh" in page and "prefers-reduced-motion" in page and "IntersectionObserver" not in page and "whileInView" not in page
    for w in ("成功", "失敗", "正解", "順位", "点数", "当たり"):
        assert w not in page, w
    # どれでもない → 文字で書く道。聞く口（手帖）は選んだ後
    assert f'href="/toy/{sid}#yosou"' in page and "手帖" in page
# 皮: 黒のジンのサイトでは黒の変数
assert "--bg:#fcfcfa" in pages[G] and "--bg:#0b0a09" in get(f"/toy/{G}/kazasu", up("zine"))[1]

# 候補の無い玩具（試作）: 重ねた絵と、自分の言葉で書く道だけ。動かし方の文を札にしない。選ぶ口も無い
od = hypotheses.load(OTHER)
code, opage, _ = get(f"/toy/{OTHER}/kazasu")
assert code == 200 and 'name="choice"' not in opage and 'class="cand"' not in opage and "predict-choice" not in opage
assert f'href="/toy/{OTHER}#yosou"' in opage and "自分の言葉で予想を書く" in opage
for h in od["hypotheses"]:
    assert h["name"] not in opage and h["how_it_moves"] not in opage, h["id"]
assert post(f"/toy/{OTHER}/predict-choice", {"choice": "head"})[0] == 422 and not hypotheses.predictions(OTHER)

# 無い候補は 422、別の出所からは 403。仮説の印を送っても受けない。どれも予想は残らない
assert post(f"/toy/{G}/predict-choice", {"choice": "wing"})[0] == 422
assert post(f"/toy/{G}/predict-choice", {"choice": "H-B"})[0] == 422 and post(f"/toy/{G}/predict-choice", {"hypothesis": "H-B"})[0] == 422
assert post(f"/toy/{G}/predict-choice", {"choice": "fan"}, origin="http://evil.example")[0] == 403
assert not hypotheses.predictions(G)

# 選ぶ: 予想として残り（kind: choice）、仮説の所へ戻る
code, _, headers = post(f"/toy/{G}/predict-choice", {"choice": "fan"})
loc = headers.get("Location", "")
assert code == 303 and loc.startswith(f"/toy/{G}?") and "see=" not in loc and loc.endswith("#kasetsu"), (code, loc)
preds = hypotheses.predictions(G)
assert len(preds) == 1
rec = json.loads(preds[0].read_text(encoding="utf-8"))
assert rec["text"] == "ここが動くと思う: 扇の所" and rec["kind"] == "choice" and rec["choice"] == "fan" and rec["via"] == "kazasu" and rec["by"] == "human"
assert "H-" not in rec["text"] and all(h["name"] not in rec["text"] for h in data["hypotheses"])
assert not hypotheses.need_prediction(G), "選んだ事が予想として数えられる"
code, toy, _ = get(loc.split("#")[0])
assert code == 200 and "予想を残しました。紙で確かめます" in toy and "ここが動くと思う: 扇の所" in toy
# 仮説が開く（予想の後）。選んだ候補で仮説を特別扱いしない: 並びは元のまま
assert "仮説 A" in toy and toy.index("仮説 A「") < toy.index("仮説 B「")
# 映像の置き場が無い事: 記録の置き場に増えたのは予想の 1 本だけ
files = sorted(p.name for p in pathlib.Path(DATA).rglob("*") if p.is_file())
assert files == [preds[0].name], files
# 虎でも同じに残る
assert post(f"/toy/{T}/predict-choice", {"choice": "head"})[0] == 303
trec = json.loads(hypotheses.predictions(T)[0].read_text(encoding="utf-8"))
assert trec["text"] == "ここが動くと思う: 頭" and trec["kind"] == "choice" and trec["choice"] == "head"
print("ok: かざして選ぶ（候補の絵）")
