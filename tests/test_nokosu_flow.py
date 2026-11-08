"""のこすの頁: 記入 → のこす → 内容の確かめ → 承認 → もちよる（本人 11-08 402・405。web.nokosu・設計は grove の state/nokosu-flow-20261108.md の 3 版）。

なぜ: 前の のこすの頁は、記入の欄も上げる欄も無く、道しるべの「のこす」がギャラリーへ行くだけだった（本人 402「記入、アップロード欄がない」）。
見る事:
1. 並び: 題 → 記入の節（その最後が「のこす」の釦・405）→ のこした記録から直った所 → 学びの輪 → 手帖をひらく → 上げる の節。道しるべは「のこす」の 1 つで、
   前の道しるべの「のこす」（/gallery#ageta）も「もちよる」の釦も無い。公開の場でも同じ並び
2. 「のこす」では何も送らない（確かめの画面に替えるだけ）。確かめの画面に、学びの輪の文と図と naoru の 1 行・「承認」「直す」
3. 承認の時に叩く順: /talk → /record-json → utsushiNewWho → /record/<番号>/media → /gallery#ageta。/talk が断られたら記録を作らない。
   「写真あり」の合図（attach）を使わない。記入の中身を端末に残さない（utsushi-who を読むのはよい）
4. 写真と動画は 3 つまで・約束の印を押さないと確かめへ進まない
5. 台本の無い画面: 写真なしで記録を残す素のフォーム（/toy/<印>/record・隠した欄に紙と back=techo）。送ると記録の頁の #mine へ戻る
6. 刷った紙が無い時は記入の節を出さず、紙を作る道
7. のこした記録から直った所: 4 つの例の字は改善の歴史の表のその版の why と changed にあり、見出しと最後の 1 行は本人の OK の字。手帖の作る頁には出ない
"""
import json
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import hypotheses, records  # noqa: E402
from web import loop_figure, naoru, nokosu, play_server, techo_site, techo_step  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
H = hypotheses.sheet_of(G)["id"]


def roads(page):
    return [re.sub(r"<[^>]+>", "", m).strip() for m in re.findall(r'class="road"[^>]*>(?:<input[^>]*>)*<(?:a|button)[^>]*>(.*?)</(?:a|button)>', page)]


def between(text, a, b):
    i = text.index(a)
    return text[i:text.index(b, i)]


# 1 並びと道しるべ（合言葉付きの場と公開の場）
for public in (False, True):
    page = techo_site.records_page(G, paper=(H, 9), public=public)
    marks = ('<div class="top"><h1>手帖</h1>', 'id="kinyu"', 'class="naoru"', 'id="manabi"', "手帖をひらく", 'aria-label="上げる"')
    at = [page.index(x) for x in marks]
    assert at == sorted(at), (public, at)
    assert roads(page) == ["のこす"], (public, roads(page))
    assert 'href="/gallery#ageta">のこす' not in page and ">もちよる</a>" not in page and ">もちよる</button>" not in page, public
    form = between(page, '<form id="nk"', "</form>")
    assert form.endswith('<p class="road"><button type="submit" class="go" id="nk-keep">のこす</button></p>'), (public, "記入の欄の最後が「のこす」", form[-200:])
    for x in ('name="result"', 'id="nk-kufu"', 'id="nk-impression"', 'id="nk-files"', 'id="nk-ok"'):
        assert form.index(x) < form.index('id="nk-keep"'), (public, x, "「のこす」は記入の欄の下（405）")
    for r in records.results_for(G):
        assert f'value="{r}"' in form, r

script = nokosu.SCRIPT
# 2 「のこす」では何も送らない
keep = between(script, "f.onsubmit", "$('nk-fix')")
assert "post(" not in keep and "fetch(" not in keep and "location" not in keep, keep
check = between(page, 'id="nk-check"', "</div><noscript>") if "</div><noscript>" in page else between(page, 'id="nk-check"', "<noscript>")
for x in (loop_figure.ADOPTED, "<svg", naoru.LINES[0], nokosu.APPROVE, nokosu.FIX, nokosu.CHECK_HEAD):
    assert x in check, x

# 3 承認の順・attach を使わない・端末に残さない
go = between(script, "go.onclick", "})()</script>")
order = [go.index(x) for x in ("/talk`", "/record-json`", "utsushiNewWho", "sendFiles(j.id", "/gallery?msg=")]
assert order == sorted(order), order
assert go.index("if (!tj.kept)") < go.index("/record-json`") and "return; }" in go[go.index("if (!tj.kept)"):go.index("/record-json`")], "工夫の字が断られたら記録を作らない"
assert "attach" not in script, "「写真あり」の合図を使わない（いつも新しい記録）"
urls = set(re.findall(r"`(/[^`$]*)", script)) | set(re.findall(r"'(/[^']*)'", script))
assert {u.split("$")[0] for u in urls} <= {"/toy/", "/record/", "/gallery?msg="}, urls
assert "localStorage" not in script and "indexedDB" not in script and "setItem" not in script, "記入の中身を端末に残さない"
assert "sessionStorage.getItem('utsushi-who')" in script, "結ぶ印を読む"
assert "go.disabled" in go, "押している間は押せない（2 度押しの止め）"

# 4 3 つまで・約束の印
assert f'data-max-n="{techo_site.MAX_PER_RECORD}"' in page and techo_site.MAX_PER_RECORD == 3
assert "つは上げません" in script and "!ok.checked" in keep and nokosu.PROMISE in page

# 5 台本の無い画面の素のフォーム
plain = between(page, "<noscript>", "</noscript>")
assert f'action="/toy/{G}/record"' in plain and f'name="hypothesis" value="{H}"' in plain and 'name="back" value="techo"' in plain
assert 'type="file"' not in plain and nokosu.NOSCRIPT in plain

# 6 刷った紙が無い時
bare = techo_site.records_page(G)
assert 'id="nk"' not in bare and roads(bare) == ["紙を作る"], roads(bare)

# 7 のこした記録から直った所
rows = json.loads((ROOT / "data/kaizen/examples.json").read_text(encoding="utf-8"))["examples"]
hist = json.loads((ROOT / "data/history/kaizen-history.json").read_text(encoding="utf-8"))
assert len(rows) == 4, rows
for e in rows:
    v = next(x for t in hist["toys"] if t["toy"] == e["toy"] for x in t["versions"] if str(x["sheet_version"]) == str(e["sheet_version"]))
    assert v["set"] == e["set"] and e["voice"] in " ".join(w["text"] for w in v["why"]) and e["change"] in v["changed"], e
assert all(t in page for t in naoru.examples()) and naoru.EXAMPLES_HEAD in page and naoru.FIXED_BY in page
assert naoru.FIXED_BY == "記録を Claude に渡して、Claude が直しました。どの版にするかは人が決めました。" and naoru.EXAMPLES_HEAD == "のこした記録から直った所"
assert "頭が揺れても前の壁に当たらない" not in page, "虎 版 7 の 1 行は外した（本人 403「唐突」）"
assert naoru.EXAMPLES_HEAD not in techo_step.page(G, [H], "tenji", step=99), "手帖の作る頁は版の名を出さない"

# サーバ: 紙の有り無しで記入の節が替わる・素のフォームで残すと #mine へ戻る
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class Stay(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kw):
        return None


op = urllib.request.build_opener(Stay)


def call(path, body=None):
    r = urllib.request.Request(base + path, data=body, headers={"Origin": base, "Content-Type": "application/x-www-form-urlencoded"} if body else {})
    try:
        with op.open(r) as x:
            return x.status, x.headers, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode()


assert 'id="nk"' not in call(f"/toy/{G}/techo/kiroku")[2], "刷る前は記入の節を出さない"
assert call(f"/toy/{G}/print", urllib.parse.urlencode({"hypothesis": H}).encode())[0] in (200, 303)
k = call(f"/toy/{G}/techo/kiroku")[2]
assert f'data-hid="{H}"' in k and roads(k) == ["のこす"], roads(k)
code, headers, _ = call(f"/toy/{G}/record", urllib.parse.urlencode({"hypothesis": H, "result": records.results_for(G)[0], "impression": "台本なしで残した", "back": "techo"}).encode())
assert code == 303 and headers["Location"].startswith(f"/toy/{G}/techo/kiroku?msg=") and headers["Location"].endswith("#mine"), (code, headers["Location"])
assert any(r.get("impression") == "台本なしで残した" for r in records.all_records(G))
server.shutdown()
print("ok: のこすの頁は 記入 → のこす → 内容の確かめ → 承認 → もちよる・記入の欄の下に「のこす」・承認まで送らない")
