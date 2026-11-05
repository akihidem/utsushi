"""英語の頁（J-030 の段 1）を試験で見る。本人の言葉（2026-11-05）「いろんな国の人に知って欲しい」「実装までやって」。

見る事:
- 全部の玩具に英語の名前と短い紹介があり、英語の入口と玩具の頁が開く。予想なしで刷れる（#242）。
- 断りを短くする時に落とさない: 動いても昔の作り方の証明にならない・型紙は AI の仮説で答えではない・紙は日本語だけ・訳は案。
- 必須 2 種の手順の文が全部訳してある。原文が変わるとここで落ちるので、訳し直しが分かる。
- 使わない言葉（guess を求める段・採点の語・英語で避ける語）が無い。聞く口と記録の口は置かない（J-030 の方針 7）。
- 日本語の玩具の頁に英語の帯と道がある。紙の指紋は tests/test_floor_pin.py が見る。
"""
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
tmp = tempfile.TemporaryDirectory()
os.environ["OMOCHAE_DATA"] = f"{tmp.name}/data"
os.chdir(tmp.name)

from omochae import hypotheses, ways  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web import about, en  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def get(path):
    return urllib.request.urlopen(base + path, timeout=30).read().decode("utf-8")


def post(path, form):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(form).encode(), headers={"Origin": base, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        r = urllib.request.build_opener(NoRedirect).open(req, timeout=120)
        return r.status, r.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "")


table = json.loads((ROOT / "data/en/toys.json").read_text(encoding="utf-8"))["toys"]
required = json.loads((ROOT / "data/en/required.json").read_text(encoding="utf-8"))
assert sorted(table) == sorted(sources()), "全部の玩具に英語の名前と紹介がある"
for sid, t in table.items():
    assert t["name"].strip() and t["intro"].strip(), sid
    assert not re.search(r"[぀-ヿ一-鿿]", t["name"] + t["intro"]), sid

idx = get("/en")
assert '<html lang="en"' in idx and all(f'href="/en/toy/{s}"' in idx for s in sources())
assert en.DRAFT in idx and "does not prove how the original was made" in idx and "none of them is the answer" in idx and "Japanese only" in idx

for sid in (G, T):
    page = get(f"/en/toy/{sid}")
    assert '<html lang="en"' in page and en.PREMISE in page and en.JA_ONLY in page and en.DRAFT in page and "does not prove how the original was made" in page
    assert page.index('id="premise"') < page.index('class="plates"')
    d = hypotheses.load(sid)
    assert sorted(required["toys"][sid]["hypotheses"]) == sorted(h["id"] for h in d["hypotheses"])
    for h in d["hypotheses"]:
        tpl = TEMPLATES[h.get("template") or d.get("template", "slider_fan")]
        for s in tpl.steps({**tpl.DEFAULTS, **h["params"]}):
            assert s in required["steps"], ("手順の訳が無い。原文が変わったら訳し直す", s)
        assert not any(x.startswith("See step") for x in en.steps_for(sid, h, d))
    # 結果の札の訳（将来の記録の口と文を揃える）
    for r in tpl.RESULTS:
        assert r in required["results"], r
    for w in ("guess how", "Make a guess", "correct answer", "pattern", "/predict", "action=\"/en/toy/" + sid + "/record", "/ask"):
        assert w not in page, w

# 試作の玩具は見立ての印つきで、英語の手順は紙へ案内する
trial = next(s for s in sources() if hypotheses.stage(s) == "試作")
page = get(f"/en/toy/{trial}")
assert "Untested draft" in page and "described in Japanese on the sheet" in page

# 予想なしで刷れて、英語の頁に戻る
code, at = post(f"/en/toy/{G}/print", {"hypothesis": "H-A"})
assert code == 303 and at.startswith(f"/en/toy/{G}") and at.endswith("#ideas"), (code, at)
page = get(at)
assert "Printed." in page and f"/sheet/{G}/H-A_v1.pdf" in page and f"/sheet/{G}/H-A_v1_tejun.pdf" in page
assert post(f"/en/toy/{G}/print", {"hypothesis": "H-Z"})[0] == 422

# 作り方の印を分けて出す。上下を付けない。印の語は日本語の札（omochae.ways）の全部に当たる
page = get(f"/en/toy/{G}")
assert "One sheet" in page and en.WAYS_NOTE in page
assert set(en.WAY_EN) == {name for _, name in ways.LABELS}

# 本人が採った文（11-05、#318）。一字でも変わったら落ちるように、ここに決定の文を書く
assert en.PREMISE == "This template is not the answer. It is a guess made by an AI. Some parts may not work. Tell us how you fixed them. That helps us make the next version better."
assert en.PREMISE in get(f"/en/toy/{G}")

# 序の頁に英語の短い紹介（#260）。頭の文は本人が採った文（11-05、#318）。一字でも変わったら落ちるように、ここに決定の文を書く
HEAD = "is a Japanese picture book of toys from 1773. It has pictures and short poems, but it does not say how the toys worked. utsushi turns the pictures into paper models you can print. Each model is a guess about how the toy moved."
for look in ("tenji", "zine"):
    about_page = about.page(look)
    assert HEAD in about_page and en.SHORT_INTRO in about_page, look
    assert 'lang="en"' in about_page and 'href="/en"' in about_page, look
    assert en.DRAFT in about_page, "英語を母語とする人が読むまで draft の印を付ける"
readme = (ROOT / "README.md").read_text(encoding="utf-8")
# README の頭に見える字は本人が採った字だけ（tests/test_readme_head.py）なので、畳んだ要約のすぐ後に置く
assert "*Edo nishiki* " + HEAD in readme and readme.index("</details>") < readme.index(HEAD) < readme.index("## 開発の過程"), "README の畳んだ要約の後に同じ文"
# README は審査員が読む所なので Claude、序の頁は学ぶ人の頁なので AI（本人の決定 11-06）。違うのはこの 1 語だけ
SAID = "After you explain what you saw, {} can respond too."
assert SAID.format("Claude") in readme and SAID.format("AI") not in readme
assert SAID.format("AI") in en.SHORT_INTRO and SAID.format("Claude") not in en.SHORT_INTRO
assert en.SHORT_INTRO.replace("<i>Edo nishiki</i>", "*Edo nishiki*").replace(SAID.format("AI"), SAID.format("Claude")) in readme, "README と序の頁で違うのは 1 語だけ"
assert en.DRAFT in readme, "README にも draft の印"

# 日本語の頁に帯と道
ja = get(f"/toy/{G}")
assert 'id="english"' in ja and f'href="/en/toy/{G}"' in ja and table[G]["name"] in ja
assert 'href="/en"' in get("/")
print("ok")
