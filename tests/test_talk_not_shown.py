"""話した字は、学ぶ人の頁に出さない（本人の決定 2026-11-06、J-034）。

本人の決定「頁に出す字は B。AI が整理した字だけを出す（話した字は作る側だけが読む）」。11-05 の「記録に入った工夫の字は、
記録の感想と同じに、手帖の記録の札に文で出す」を変えた。整理した字の置き場はまだ無いので、今は話した字の行を頁に出さない。

見る線:
1. 学ぶ人の頁（表紙・玩具の棚・玩具の頁・作る頁・作りながら見る頁・手帖の記録の頁・ギャラリー）に、話した字が 1 つも出ない。
   場面は 3 つとも（仮説を見て話した考え・作りながら話した工夫・上げた後に足した字）。記録に結んであっても出ない
2. 記録の欄に書いた直した点（部品・変えた事・結果）は、今までどおり、記録の札の「工夫した所（直した所）」に出る（書いた字は変えない）
3. 字は消していない: 記録に結んだまま、作る側の頁（/loop/<印>）と型紙の版の歩み（/loop/ayumi が読む record_words）と、輪の材料が読む
本物の API は呼ばない。
"""
import os
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import loop, records, talk_log  # noqa: E402
from web import hanasu, kaizen_versions  # noqa: E402
from web.play_server import serve  # noqa: E402

G, WHO = "NDL-1187053-R0000005-L", "talkhide01"
THINK, CRAFT, KEEP = "扇が上に開くと思う", "糊代を先に折ったら貼りやすかった", "上げた後に、扇の根元を糸で留めた"
FIX = ("外筒", "太く巻いた", "内筒が入りやすくなった")

# 話した字を 3 つの場面で残し、記録に結ぶ（記録を残す口が呼ぶのと同じ bind）。記録の欄にも直した点を 1 つ書く
assert talk_log.add(G, "think", THINK, hypothesis_id="H-A", who=WHO)[1] == []
assert talk_log.add(G, "craft", CRAFT, hypothesis_id="H-A", sheet_version=1, step=2, who=WHO)[1] == []
rid, failures = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた",
                             "fixes": [dict(zip(("part", "change", "outcome"), FIX))]})
assert not failures, failures
assert talk_log.bind(G, "H-A", 1, WHO, rid) == (1, 1)
assert talk_log.add(G, "keep", KEEP, record_id=rid)[1] == []
SAID = (THINK, CRAFT, KEEP)
assert {t["text"] for t in talk_log.kufu(G, rid, shared_only=True)} == set(SAID), "3 つとも記録に結んである（隠していない）"

server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    try:
        r = urllib.request.urlopen(base + path, timeout=120)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


# ---- 1. 学ぶ人の頁に出ない
LEARNER = ("/", "/toys", f"/toy/{G}", f"/toy/{G}/techo", f"/toy/{G}/tsukuru?h=H-A&n=2", f"/toy/{G}/techo/kiroku", "/gallery")
pages = {}
for path in LEARNER:
    code, pages[path] = get(path)
    assert code == 200, (path, code)
    for text in SAID:
        assert text not in pages[path], ("話した字が学ぶ人の頁に出た", path, text)

# ---- 2. 記録の欄に書いた直した点は、記録の札に出る
kiroku = pages[f"/toy/{G}/techo/kiroku"]
assert rid in kiroku and f'<li>{" / ".join(FIX)}</li>' in kiroku, "記録の欄の直した点は出る"
block = hanasu.kufu_block(G, loop.record(rid))
assert block == (f'<div class="hanasu-kufu" data-kufu="{rid}"><p class="hanasu-kufu-head">{hanasu.KUFU_HEAD}</p>'
                 f'<ul><li>{" / ".join(FIX)}</li></ul></div>'), ("節に並ぶのは直した点だけ", block)
# 話した字だけが結んである記録には、節を出さない
rid2, failures = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
assert not failures and talk_log.add(G, "keep", "話した字だけの記録", record_id=rid2)[1] == []
assert hanasu.kufu_block(G, loop.record(rid2)) == "" and "話した字だけの記録" not in get(f"/toy/{G}/techo/kiroku")[1]

# ---- 3. 作る側は読める（字は消していない）
code, maker = get(f"/loop/{G}")
assert code == 200 and all(text in maker for text in SAID), "作る側の頁には、話した字がそのまま並ぶ"
words = kaizen_versions.record_words(rid)
assert f"手順 2 で話した工夫 {rid}: {CRAFT}" in words and f"上げた後の話 {rid}: {KEEP}" in words, ("版の歩みの字に、話した工夫が入る", words)
assert {t["text"] for t in loop.maker_talk(rid)["items"]} == {CRAFT, KEEP}, "輪の材料に、話した工夫が入る（考えはループ 1 の材料）"
server.shutdown()
print("ok 話した字は学ぶ人の頁に出ない（3 つの場面・7 つの頁）。記録の欄の直した点は札に出る。作る側の頁と輪の材料には残る")
