"""ループ1（Issue #335）の画面: 玩具の頁の小さな節と受け口。中身の道は tests/test_loop1_words.py が見る。本物の API は呼ばない（Claude は記録した形の偽物）。

見る線:
- 印（who）のある人だけが頼め、頼んだ後は本人の印（token）の URL で様子が見える。番号では開かない。押し直すと同じ案へ戻る（案を並べない）。
- 確かめる所に内部の名前を出さない。本人が押すまで刷らない。乗らない考えは型紙なしの紙になる。
- 紙を作った直後に、その紙の絵が出る。順位・点・推しを付けない（#145 の要件を話す道でも）。
- 話した字は、採った後も玩具の頁の札と図鑑に出さない（記録に結ぶ前の字は学ぶ人の頁に出さない決まり）。
- 文は「文面は本人の確認待ち」の新しい文（文字列をここに固定しない。定数で見る）。
"""
import json
import os
import re
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from types import SimpleNamespace as NS

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import words  # noqa: E402
from omochae import hypotheses, making_log, talk_log  # noqa: E402
from omochae.marks import OWN_HYPOTHESIS  # noqa: E402
from web import think_sheet, zukan  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
WHO, OTHER = "abcdefgh12", "zyxwvuts98"


class Fake:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        return NS(content=[NS(type="tool_use", name="submit_result", input=self.script.pop(0), id="t")], stop_reason="tool_use", usage=NS(input_tokens=10, output_tokens=5))


def flat_pdf(path):
    return "".join(subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True).stdout.split())


def think(text, who=WHO, hid=None):
    path, fs = talk_log.add(G, "think", text, hypothesis_id=hid, who=who)
    assert path and not fs, fs


base_params = words.base_of(G)[1]

# ── 鍵なしの道を画面の関数で ──
SAID = "つまみを 長い棒にしたら、もっと大きく開くと思う"
think(SAID)
assert think_sheet.request(G, "")[1] == think_sheet.NONE, "印の無い画面からは頼めない"
assert think_sheet.request(G, OTHER)[1] == think_sheet.NONE, "ほかの人の考えは選ばない"
w, why = think_sheet.request(G, WHO)
assert w and why is None and w["status"] == "waiting_maker" and w["name"].startswith("仮説 A ")
assert think_sheet.request(G, WHO)[0]["id"] == w["id"] and len(words.waiting()) == 1, "押し直すと同じ案へ戻り、案を並べない"
assert not out_dir(G).exists() and hypotheses.own_hypotheses(G) == [], "頼んだだけでは何も刷らない"
assert think_sheet.WAITING in think_sheet.section(G, f"think-{w['token']}")
assert think_sheet.confirm(G, w["token"])[0] is None, "作る側が書く前は採れない"
assert not words.fill_think(w["id"], words.think_result(w["base_params"], {"push_part": "stick", "pusher_height": 84}), "作る側")[1]
html = think_sheet.section(G, f"think-{w['token']}")
assert think_sheet.CHECK in html and think_sheet.OK in html and think_sheet.SAME in html
assert think_sheet.GO not in html, "確かめている間は、作り直す釦を並べない"
assert f"{think_sheet.NAMES['push_part']}: {think_sheet.VALUES['tab']} → {think_sheet.VALUES['stick']}" in html, "変えた所を、もと → 今で見せる"
assert "push_part" not in html and "stick" not in html and "pusher_height" not in html, "内部の名前を見せない"
assert hypotheses.own_hypotheses(G) == [], "本人が押すまで残らない"
name, why = think_sheet.confirm(G, w["token"])
oid = words.by_token(G, w["token"])["own_id"]
assert name == f"{oid}_v1.pdf" and why is None
assert "".join(OWN_HYPOTHESIS.split()) in flat_pdf(out_dir(G) / name), "紙に「自分で立てた」の印"
done = think_sheet.section(G, f"think-{w['token']}")
assert think_sheet.DONE in done and name in done and SAID in done
assert f'<img src="/sheet/{G}/{name[:-4]}.png"' in done and (out_dir(G) / f"{name[:-4]}.png").exists(), "紙を作った直後に、その紙の絵が出る（#145）"
assert think_sheet.confirm(G, w["token"])[0] is None, "同じ案を 2 度は採らない"
# 採った後に刷れなかった時は、もう一度押せば刷り直す（案を失わない）
for p in out_dir(G).glob(f"{oid}_v1*"):
    p.unlink()
again = think_sheet.section(G, f"think-{w['token']}")
assert think_sheet.FAILED in again and think_sheet.OK in again, "「できました」と言わない"
assert think_sheet.confirm(G, w["token"])[0] == name and (out_dir(G) / name).exists()
# 話した字は、ほかの人の頁に出さない（図鑑。玩具の頁は下の頁の節で見る）
assert not any(SAID in x["text"] for x in zukan.hypothesis_lines(G, hypotheses.load(G))), "図鑑に出さない"
# 乗らない考えは型紙なしの紙
think("水を入れた重さで開くのかも")
w2, _ = think_sheet.request(G, WHO)
assert not words.fill_think(w2["id"], words.think_result(w2["base_params"], not_fit=["水の重さで動く機構は雛形に無い"]), "作る側")[1]
assert think_sheet.NO_FIT in think_sheet.section(G, f"think-{w2['token']}")
free = think_sheet.confirm(G, w2["token"])[0]
assert free.endswith("_free.pdf") and f'<img src="/sheet/{G}/{free[:-4]}.png"' in think_sheet.section(G, f"think-{w2['token']}"), "型紙なしの紙でも絵が出る"

# ── 鍵ありの道（偽の Claude）を画面の関数で ──
think("割り箸の柄で押したい", who=OTHER)
CHANGED = {"push_part": "stick", "pusher_height": 84}
ok = {"fits": True, "params": {**base_params, **CHANGED}, "from_words": sorted(CHANGED),
      "filled_in": [{"param": k, "why": words.KEPT_AS_IS} for k in base_params if k not in CHANGED], "not_fit": []}
before = sorted(out_dir(G).glob("*.pdf"))
k, why = think_sheet.request(G, OTHER, claude=True, client=Fake([ok]))
assert k and k["status"] == "pending_human", why
assert sorted(out_dir(G).glob("*.pdf")) == before, "本人が採るまで何も刷らない"
html = think_sheet.section(G, f"think-{k['token']}")
assert think_sheet.CHECK in html and think_sheet.VALUES["stick"] in html and "push_part" not in html
assert think_sheet.section(G, f"think-{k['id']}").count(think_sheet.CHECK) == 0, "番号では開かない"
assert think_sheet.confirm(G, k["token"])[0], "採ると刷れる"
# 床に当たる字（手で置いた物）は Claude へ送らず、話す口の文で断る
never = Fake([])
bad = making_log.folder() / "talk-20261105-1800-00000001.json"
bad.write_text(json.dumps({"source_id": G, "hypothesis_id": "H-A", "scene": "think", "text": "連絡は a@example.com まで", "who": WHO, "record_id": None}, ensure_ascii=False), encoding="utf-8")
got, why = think_sheet.request(G, WHO, claude=True, client=never)
assert got is None and why and never.calls == []
bad.unlink()

# ── 頁（2 行の受け口と玩具の頁の節） ──
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def send(path, data=None):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode() if data is not None else None, method="POST" if data is not None else "GET",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    try:
        r = opener.open(req)
        return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)


code, body, _ = send(f"/toy/{G}")
assert code == 200 and think_sheet.GO in body and 'action="/toy/' + G + '/think-sheet"' in body
assert SAID not in body and "割り箸の柄で押したい" not in body, "採った案の字を、玩具の頁の札に出さない"
think("つまみを下に付けたい", who="pagewho123")
code, body, _ = send(f"/toy/{G}/think-sheet", {"who": ""})
assert code == 422 and think_sheet.NONE in body
code, _, h = send(f"/toy/{G}/think-sheet", {"who": "pagewho123"})
assert code == 303 and "at=think-" in h["Location"], code  # 試験の置き場には鍵が無いので、作る側の待ちに置かれる
code, body, _ = send(h["Location"].split("#")[0])
assert code == 200 and think_sheet.WAITING in body and think_sheet.ASKED in body
code, body, _ = send(f"/toy/{G}/think-ok", {"t": "nothing"})
assert code == 422 and think_sheet.FAILED in body
# 押した後に着く頁に絵が出て、その絵が本当に開く（#145）。どの状態の節にも順位・点・推しの言葉が無い。
think("柄を長くしたい", who="pagewho456")
_, _, h = send(f"/toy/{G}/think-sheet", {"who": "pagewho456"})
tok = urllib.parse.parse_qs(urllib.parse.urlsplit(h["Location"]).query)["at"][0][len("think-"):]
sections = [think_sheet.section(G, f"think-{tok}"), think_sheet.section(G)]
assert not words.fill_think(words.by_token(G, tok)["id"], words.think_result(words.by_token(G, tok)["base_params"], {"push_part": "stick", "pusher_height": 84}), "作る側")[1]
sections.append(think_sheet.section(G, f"think-{tok}"))
code, _, h = send(f"/toy/{G}/think-ok", {"t": tok})
assert code == 303, code
code, body, _ = send(h["Location"].split("#")[0])
src = re.search(r'<section class="sec" id="think">.*?<img src="([^"]+\.png)"', body, re.S)
assert code == 200 and src, "押した後に着く頁の節に、紙の絵"
r = opener.open(base + src.group(1))
assert r.status == 200 and r.headers["Content-Type"] == "image/png" and r.read()[:8] == b"\x89PNG\r\n\x1a\n", "絵が開く"
sections.append(think_sheet.section(G, f"think-{tok}"))
for html in sections:
    assert not [x for x in words.RANK_WORDS if x in html], "順位・点・推しを付けない"
assert not {"score", "rank", "points", "recommended"} & set(words.by_token(G, tok)), "記録にも持たない"
server.shutdown()
print("ok")
