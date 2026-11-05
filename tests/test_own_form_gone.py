"""玩具の頁に、仮説を書く欄を出さない（本人の決定 11-05 18:08「仮説は書かず、話すことができる」、J-032 の点 2、#332）。

書く代わりの道は、話した考えから紙を作る節（web/think_sheet.py の試験が見る）。話した案は同じ OWN-n の形で持つので、
自分の仮説の記録の形と紙の道は消さない。外すのは頁の欄と札と口だけ。

見る事:
1. 玩具の頁に書く欄が無い。前に書いた仮説が置き場にあっても、札も記録の欄の選択肢も出ない
2. 書く口と、書いた仮説の紙を刷る口は閉じる。開いたままの古い頁から届いても、何も増えない
3. 前に書かれた自分の仮説の記録と、それで刷った紙は読める。札を外した分、紙は記録の札から開く
4. 紙へのリンクは、話した案（作った本人の画面からだけ開く）と合言葉なしの場（OWN-n の紙を開かない）の札には出さない
5. 話して作った本人の紙だけは、記録の欄で選んだ形で出す（たたき台の記録に取り違えない）。書いた仮説は並べない
"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from api import ask, words  # noqa: E402
from omochae import hypotheses, loop, records, store  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402
from web.toy import toy_page  # noqa: E402

ask._key_present = lambda: False  # 合言葉なしの場は鍵のある所で立たない。鍵のある機械でも同じに動かす
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
TRIAL = "NDL-1187053-R0000006-R"  # 試作の玩具（糸からくりの絵箱）
WRITTEN = ("書いた案の名前", "書いた動かし方", "書いた図の所")


def up(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"


base, opened = up(), up(public_open=True)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a):
        return None


def get(path, at=None):
    try:
        return urllib.request.urlopen((at or base) + path, timeout=120).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


def status(path):
    """紙を開いた時の (状態, 種類)。"""
    try:
        r = urllib.request.urlopen(base + path, timeout=120)
        return r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, ""


def post(path, form):
    req = urllib.request.Request(base + path, urllib.parse.urlencode(form).encode(), {"Origin": base, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        r = urllib.request.build_opener(NoRedirect).open(req, timeout=120)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def written(sid, name=WRITTEN[0], params=None, printed=True):
    """前に書かれた自分の仮説と、それで刷った紙が置き場にある形を作る。"""
    own, failures = hypotheses.save_own(sid, name, WRITTEN[1], WRITTEN[2], params)
    assert not failures, failures
    if printed:
        out_dir(sid).mkdir(parents=True, exist_ok=True)
        assert hypotheses.print_own(sid, own["id"], str(out_dir(sid) / f'{own["id"]}_v1')) == 0, sid
    return own["id"]


def recorded(sid, oid, words_text):
    """その紙の記録を残し、説明を足す。古い頁と作る側の道から届く形（頁の欄はもう送らない）。"""
    result = TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].RESULTS[0]
    assert post(f"/toy/{sid}/record", {"hypothesis": oid, "result": result, "impression": words_text})[0] == 303, (sid, oid)
    rid = [r["id"] for r in records.all_records(sid) if r["hypothesis_id"] == oid][-1]
    assert post(f"/record/{rid}/explain", {"text": f"{words_text}の説明", "next_idea": f"{words_text}の次", "by": "書いた人"})[0] == 303, rid
    return rid


def card_of(page, rid):
    return page.split(f'id="{rid}"', 1)[1].split("</article>", 1)[0]


for sid in (G, T, TRIAL):
    sheet = hypotheses.sheet_of(sid)["id"]
    # 1. 書く欄が無い。前に書いた仮説が置き場にあっても、札と選択肢を出さない
    page = get(f"/toy/{sid}")
    assert "自分の仮説を立てる" not in page and f"/toy/{sid}/own" not in page, (sid, "書く欄")
    oid = written(sid)
    page = get(f"/toy/{sid}")
    assert "自分の仮説を立てる" not in page and f"/toy/{sid}/print-own" not in page and f'id="own-{oid}"' not in page, (sid, "札")
    assert not [w for w in WRITTEN if w in page], (sid, "書いた文を頁に出さない")
    assert '<select name="hypothesis">' not in page and "どの仮説の紙か" not in page, (sid, "記録の欄の選ぶ欄")
    form = page.split('id="record"', 1)[1].split("</form>", 1)[0]
    assert re.findall(r'name="hypothesis" value="([^"]+)"', form) == [sheet], (sid, "記録の欄はたたき台の番号を送る")

    # 2. 口は閉じる。古い頁から届いても、仮説も紙も増えない
    waiting = written(sid, "刷っていない案", printed=False)
    before = [h["id"] for h in hypotheses.own_hypotheses(sid)]
    assert post(f"/toy/{sid}/own", {"name": "新しい案", "how": "押す", "evidence": "図"})[0] == 404, sid
    assert post(f"/toy/{sid}/print-own", {"id": waiting})[0] == 404, sid
    assert [h["id"] for h in hypotheses.own_hypotheses(sid)] == before, sid
    assert not list(out_dir(sid).glob(f"{waiting}_v*")), (sid, "閉じた口から紙を作らない")

    # 3. 前の記録と、それで刷った紙は読める。紙は記録の札から開く
    rid = recorded(sid, oid, "前の感想")
    card = card_of(get(f"/toy/{sid}"), rid)
    assert "自分の仮説の紙" in card and "感想: 前の感想" in card and "説明: 前の感想の説明" in card and "次の思いつき: 前の感想の次" in card, card
    paper = f"/sheet/{sid}/{oid}_v1_free.pdf"
    assert f'<a href="{paper}"' in card and "型紙なしの紙" in card, (sid, "刷った紙への道")
    assert status(paper) == (200, "application/pdf"), (sid, paper)
    after = f"/sheet/{sid}/{oid}_v1_after.pdf"
    assert f'<a href="{after}"' in card and status(after) == (200, "application/pdf"), (sid, after)
    assert f"/record/{rid}/next" not in card, (sid, "型紙なしの紙の記録に、次の版の向く先は無い")
    # 記録の無い紙は頁に出ないが、道そのものは消さない
    alone = written(sid, "記録の無い案")
    assert "記録の無い案" not in get(f"/toy/{sid}") and status(f"/sheet/{sid}/{alone}_v1_free.pdf") == (200, "application/pdf"), sid

# 寸法つきの仮説は型紙と手順の紙を刷る（作る側の命令の道。頁の札にはリンクが無かった）。これも記録の札から開く
typed = written(G, "寸法つきの案", {"push_part": "tab", "hub": "axle", "pusher_height": 15})
rid_typed = recorded(G, typed, "寸法つきの感想")
card = card_of(get(f"/toy/{G}"), rid_typed)
for stem, label in ((f"{typed}_v1", "型紙"), (f"{typed}_v1_tejun", "手順の紙")):
    assert re.search(rf'<a href="/sheet/{G}/{stem}\.pdf"[^>]*>{label}</a>', card), (stem, card)
    assert status(f"/sheet/{G}/{stem}.pdf") == (200, "application/pdf"), stem
assert f"{typed}_v1_free" not in card

# 札を外しても、寸法つきの前の記録からの次の版はたたき台の紙になる。その人の案には版を足さない（細かい所は tests/test_loop1_next.py が見る）
assert f"/record/{rid_typed}/next" in card
assert post(f"/record/{rid_typed}/next", {"interpretation": "読み", "param": "fold_height", "to": "47.5", "why": "試す", "by": "書いた人"})[0] == 303
assert (out_dir(G) / "H-A_v2.pdf").exists() and not list(out_dir(G).glob(f"{typed}_v2*"))

# 4. 話した案の札には紙へのリンクを出さない（紙は作った本人の画面からだけ開くので、ほかの人には行き止まりになる）
spoken = written(G, "話した案")
rid_spoken = recorded(G, spoken, "話した案の感想")  # 話した案の記録は本人の鍵がある画面から届く。鍵の試験は tests/test_loop1_own_private.py が見るので、ここは印を後から置く
store.write_json(loop.folder() / "words-W-9001.json", {"id": "W-9001", "source_id": G, "typed_by": words.THINK_BY, "own_id": spoken})
assert spoken in words.spoken_own_ids(G)
assert f"{spoken}_v1_free" not in card_of(get(f"/toy/{G}"), rid_spoken), "話した案の紙への道を札に出さない"

# 合言葉なしの場は OWN-n の紙を開かないので、札にも出さない。人の書いた文も出さない
rid_written = next(r["id"] for r in records.all_records(G) if r["hypothesis_id"] == "OWN-1")
public = get(f"/toy/{G}", at=opened)
assert "OWN-1_v1_free" not in card_of(public, rid_written) and not [w for w in ("前の感想", *WRITTEN) if w in public], "合言葉なしの場"

# 5. 話して作った本人の紙だけ、記録の欄で選んだ形で出す。書いた仮説は並べない
form = toy_page(G, mine={spoken}).split('id="record"', 1)[1].split("</form>", 1)[0]
assert f'<option value="{spoken}" selected>' in form and "どの仮説の紙か" in form, form
assert re.findall(r'<option value="([^"]+)"', form.split('name="hypothesis"', 1)[1].split("</select>", 1)[0]) == [hypotheses.sheet_of(G)["id"], spoken], form
assert "OWN-1" not in form and WRITTEN[0] not in form

print("ok: 玩具の頁に書く欄は無く、前の自分の仮説の記録と紙は読める")
