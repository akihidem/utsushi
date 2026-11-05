"""合言葉なしで開いた場に、内部の番号と作る側の控えを出さない（J-028。公開の前の点検で見つけた物）。

見る事:
1. 記録の番号（R-番号）を、玩具の頁・手帖・図鑑の字に出さない。札へ飛ぶ道（#R-番号）は残す
2. 改善の輪の節に、閉じた口への案内と、次の版の理由と根拠の番号を出さない
3. 読みと観察の文（AI の文）を出さない
4. script と style の注釈を送らない。動く所（字の中の // や URL）は切らない
5. Server の見出しに Python の版を出さない
6. 置き場の道（data/…）と決定の番号（J-021）は、どちらの場でも字に出さない
対照: 合言葉の場では、1〜4 の物が今までどおり出る。
"""
import http.client
import os
import re
import tempfile
import threading
import urllib.parse

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from api import ask, observe  # noqa: E402
from omochae import hypotheses, loop, records, store  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web import wording  # noqa: E402
from web.play_server import serve, sources  # noqa: E402
from web.toy import evidence_item  # noqa: E402

ask._key_present = lambda: False  # 合言葉なしの場は鍵のある所で立たない。鍵のある機械でも同じに動かす
G = "NDL-1187053-R0000005-L"
TRIAL = "NDL-1187053-R0000004-L"  # 試作の玩具。根拠の字に置き場の道が入っている
WHY, READ, CAUSE, UNKNOWN, SEEN = "版の理由の目印", "読みの目印", "原因の目印", "分からない事の目印", "観察の目印"


def up(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server.server_address[1]


closed, opened = up(), up(public_open=True)


def call(port, path, form=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=120)
    host = f"127.0.0.1:{port}"
    if form is None:
        c.request("GET", path, headers={"Host": host})
    else:
        c.request("POST", path, urllib.parse.urlencode(form), {"Host": host, "Origin": f"http://{host}", "Content-Type": "application/x-www-form-urlencoded"})
    r = c.getresponse()
    body = r.read().decode(errors="replace")
    c.close()
    return r.status, dict(r.getheaders()), body


def page(port, path):
    st, _, body = call(port, path)
    assert st == 200, (path, st)
    return body


def visible(html):
    """人の目に入る字。script と style と属性は外す。"""
    return re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S))


def add_record():
    result = TEMPLATES[hypotheses.load(G).get("template", "slider_fan")].RESULTS[0]
    rid, failures = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": result})
    assert not failures, failures
    return rid


# 版に使った記録・説明のある記録・説明を待つ記録の 3 つと、読みと観察の文を置く
assert call(closed, f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303
used, ready, waiting = add_record(), add_record(), add_record()
for rid in (used, ready):
    assert not loop.save_explanation(rid, "書いた人", "説明の字", "次の思いつきの字")
st, _, body = call(closed, f"/record/{used}/next", {"interpretation": "読み", "param": "fold_count", "to": "27", "why": WHY, "by": "採った人"})
assert st == 303, (st, body[-300:])
loop.save_interpretation_draft(ready, {"observed": [READ], "causes": [{"text": CAUSE, "confidence": "低い"}], "unknown": [UNKNOWN]}, {"model": "x"})
store.write_json(observe.path(ready), {"observed": [SEEN], "unclear": []})
TOY, TECHO, ZUKAN, ZUKAN_ONE = f"/toy/{G}", f"/toy/{G}/techo", "/zukan", f"/zukan/{G}"
NUM = re.compile(r"R-\d{4,}")

# 1. 記録の番号を字に出さない。札へ飛ぶ道は残す
for path in (TOY, TECHO, ZUKAN, ZUKAN_ONE):
    assert not NUM.findall(visible(page(opened, path))), (path, "記録の番号")
    assert NUM.search(visible(page(closed, path))), (path, "対照: 合言葉の場では番号が出る")
assert f'href="#{used}"' in page(opened, TOY) and f'id="{used}"' in page(opened, TOY), "札へ飛ぶ道は残す"

# 2. 改善の輪の節: 閉じた口へ案内しない。理由と根拠の番号を出さない。版が変わった事は読める
BASED = wording.BASED_ON.split("{}")[1].strip()  # 根拠の番号を添える文の、番号の後ろの字
kz = page(opened, TOY).split('id="kaizen"', 1)[1]
assert "次の版を待つ報告" not in kz and "説明を待つ報告" not in kz and WHY not in kz and BASED not in kz, kz[:400]
assert "仮説 A 版 2" in kz and f"/toy/{G}?see=H-A&amp;kind=sheet&amp;v=2" in kz.replace("&", "&amp;").replace("&amp;amp;", "&amp;"), kz[:400]
kz = page(closed, TOY).split('id="kaizen"', 1)[1]
assert "次の版を待つ報告 1 件" in kz and "説明を待つ報告 1 件" in kz and WHY in kz and BASED in kz, "対照: 合言葉の場の節は今までどおり"

# 3. 読みと観察の文を出さない
for path in (TOY, TECHO):
    body = page(opened, path)
    assert not [w for w in (READ, CAUSE, UNKNOWN, SEEN) if w in body], (path, "AI の文")
    assert "説明を残しました。" in body, path
    body = page(closed, path)
    assert not [w for w in (READ, CAUSE, UNKNOWN, SEEN) if w not in body], (path, "対照: 合言葉の場では読める")

# 4. 注釈を送らない。動く所は切らない
for path in ("/", TOY, TECHO, f"/toy/{G}/tsukuru", ZUKAN, "/gallery", f"/en/toy/{G}"):
    body = page(opened, path)
    for tag, part in re.findall(r"<(style|script)\b[^>]*>(.*?)</\1>", body, re.S):
        assert "/*" not in part or tag == "script", (path, re.search(r"/\*.{0,60}", part).group(0))
        assert not re.findall(r"(?m)^\s*//", part), (path, re.findall(r"(?m)^\s*//.{0,60}", part)[:2])
    assert "#124" not in body and "本人の" not in "".join(p for _, p in re.findall(r"<(style|script)\b[^>]*>(.*?)</\1>", body, re.S)), path
assert re.search(r"(?m)^\s*//", page(closed, TECHO)), "対照: 合言葉の場の頁は今までどおり（注釈を外すのは開いた場だけ）"
from web.play_server import without_notes  # noqa: E402

keep = "<style>a{color:red}/* 控え\n2 行 */b{c:d}</style><script>\n  // 控え\nconst u='http://x//y';\nf(); // 後ろの控え\nconst t=`//字`;\n</script><p>// 本文の字 /* そのまま */</p>"
out = without_notes(keep)
assert out == "<style>a{color:red}b{c:d}</style><script>\nconst u='http://x//y';\nf();\nconst t=`//字`;\n</script><p>// 本文の字 /* そのまま */</p>", out

# 5. Server の見出しに版を出さない
for port in (closed, opened):
    server = call(port, "/")[1].get("Server", "")
    assert "Python" not in server and "BaseHTTP" not in server, server

# 6. 置き場の道と決定の番号は、どちらの場でも字に出さない。根拠の行そのものは残す
for port in (closed, opened):
    body = page(port, f"/toy/{TRIAL}")
    assert "data/inventory" not in body, "置き場の道"
    assert "〔" in visible(body), "根拠の行は残す"
    assert "J-021" not in page(port, "/gallery"), "決定の番号"

left = [(s, e) for s in sources() for h in hypotheses.load(s)["hypotheses"] for e in h.get("evidence", []) if "data/" in evidence_item(e)]
assert not left, ("全部の玩具の根拠の行に置き場の道を出さない", left[:2])
assert evidence_item({"certainty": "推測", "what": "目印（data/x.json）の字", "where": "場所（data/x.json）"}) == "<li>〔推測〕目印の字（場所）</li>"

print("ok: 合言葉なしの場に、内部の番号と作る側の控えを出さない")
