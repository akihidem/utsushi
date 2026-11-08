"""つくるの外の頁でも、部品が作る仮説の字を印なしの「仮説」にする（本人の答え 11-08「そろえる。」）。

見る事:
1. 作る側の頁（版の歩み /loop/ayumi・改善の輪 /loop/<玩具>）の版の札の題が「仮説 版 N」の形で、「仮説 A 版 N」の形が無い
2. のこす（手帖の記録の頁）・もちよる（ギャラリー）・作る側の頁の記録の札が「仮説の紙」で、「A の紙」の形が無い
3. 英語の玩具の頁（/en/toy/<玩具>）の仮説の札に大きな印の字（div.letter）が無く、「Idea A」「Guess A」の形も無い（呼び名は Guess）
4. くずし字の頁の仮説の行（zukan.hypothesis_lines）が「仮説「…」: …」の形
5. 記録の中の字（人の説明・本人の所見と決定・版の台帳の文・AI の読み）は替えない。2 つの仮説を比べる文があり、印を外すと意味が通らないため。
   ここでは、版の台帳の文に印つきの字が前のまま残る事を見る（部品の直しが記録の字まで書き換えていない事）
"""
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
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from web import zukan  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
VERSION_MARK = re.compile(r"仮説 [A-Z] 版 \d")
PAPER_MARK = re.compile(r"(?<![A-Za-z0-9])[A-Z] の紙")
EN_MARK = re.compile(r"\b(?:Idea|Guess|Hypothesis) [A-Z]\b")

# 4. くずし字の頁の仮説の行
lines = zukan.hypothesis_lines(G, hypotheses.load(G))
assert lines and all(x["text"].startswith(hypotheses.shown_name(hypotheses.sheet_of(G)) + ": ") for x in lines if x["label"] == zukan.HYPO), lines[:1]

srv = serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"


def get(path, cookie=""):
    req = urllib.request.Request(base + path, headers={"Cookie": cookie} if cookie else {})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read().decode("utf-8")


def text(page):
    return re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S))


try:
    hid = hypotheses.sheet_of(G)["id"]
    urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/print", data=urllib.parse.urlencode({"hypothesis": hid}).encode(), headers={"Origin": base}), timeout=300).read()
    urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/record", data=urllib.parse.urlencode({"hypothesis": hid, "result": "動いた"}).encode(), headers={"Origin": base}), timeout=120).read()
    # 1. 作る側の頁の版の札の題（試験の場には採った版が無いので、版の札の部品を直に呼ぶ）
    from web import ayumi as ay
    card = ay._version_item(G, hid, hypotheses.version_head(hypotheses.sheet_of(G), False), {"version": 2, "changes": [], "record_ids": []})
    assert "仮説 版 2" in card and not VERSION_MARK.search(card), card[:200]
    ayumi = text(get("/loop/ayumi"))
    assert not VERSION_MARK.search(ayumi), VERSION_MARK.findall(ayumi)[:3]
    # 5. 版の台帳の文（記録の字）は前のまま（印つき）
    assert re.search(r"仮説 [A-E]", ayumi), "記録の中の字は替えない"
    # 2. 記録の札
    for path in (f"/toy/{G}/techo/kiroku", "/gallery", f"/loop/{G}"):
        page = text(get(path))
        assert not PAPER_MARK.search(page), (path, PAPER_MARK.findall(page)[:3])
    assert "仮説の紙" in text(get(f"/loop/{G}")), "作る側の頁の記録の札は「仮説の紙」"
    # 3. 英語の玩具の頁
    en = get(f"/en/toy/{G}")
    assert 'class="letter"' not in en and not EN_MARK.search(text(en)) and "Guess" in en, EN_MARK.findall(text(en))[:3]
finally:
    srv.shutdown()
print("ok つくるの外も印なしの「仮説」: 版の札の題・記録の札（のこす・もちよる・作る側）・英語の玩具の頁・くずし字の仮説の行。記録の中の字は前のまま")
