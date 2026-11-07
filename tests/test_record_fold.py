"""記録の欄を、作る前から重く見せない（#300）。

なぜ: 欄の全部が刷る前の頁から開いていて、必須は見た事だけなのに「全部書くのか」と読める。すぐ作る形（#242）と逆の重さになる。
見る線: 最初に見える欄は、見た事・感想・工夫の 3 つ。残りはその後ろに置き、見出しの文があれば素の details に畳む（閉じたままでも送られる）。
記録の形と、試した後の紙が開く条件は変えない。
紙はたたき台の 1 枚なので、ふだんは選ぶ欄が無く、記録はたたき台に入る（#332）。話した本人の案がある時と、版が 2 つ以上ある時だけ選ぶ欄が出て、
それは畳まない: 見えないまま送ると、記録と試した後の紙が別の案になる。
畳みの見出しは本人が採った文を入れる。入れる前の形（定数が空で畳まない）と畳んだ形は、試験の中で見出しの例を置いて見る。
"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import hypotheses, records  # noqa: E402
from web import skin, toy  # noqa: E402
from web.play_server import out_dir, serve, sources  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台の仮説（次の組は H-C の柄を下から押し上げる形・前の組は H-A。本人の決定 2026-11-06。hypotheses.sheet_id）
GS = hypotheses.sheet_of(G)["id"]
T = "NDL-1187053-R0000014-R"
FIRST = {"result", "impression", "fix_part", "fix_change", "fix_outcome"}  # 見た事・感想・工夫の 3 つ
REST = {"first_moved", "stuck", "what_if", "idea", "note"}
SHIPPED = vars(toy).get("RECORD_MORE")  # 入っている見出し。下で例に置き換える前に控える
EXAMPLE = "見出しの例"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def post(path, **data):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST", headers={"Origin": base})
    try:
        r = opener.open(req)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def get(path):
    return urllib.request.urlopen(base + path).read().decode()


def status(path):
    try:
        return urllib.request.urlopen(base + path).status
    except urllib.error.HTTPError as e:
        return e.code


class Fields(HTMLParser):
    """form の欄を、畳みの外と中に分けて拾う。"""

    def __init__(self, form):
        super().__init__()
        self.depth, self.in_summary, self.summary = 0, False, ""
        self.outer, self.inner, self.required_inner, self.details = set(), set(), set(), []
        self.feed(form)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "details":
            self.depth += 1
            self.details.append(a)
        elif tag == "summary":
            self.in_summary = True
        elif tag in ("input", "select", "textarea") and a.get("name") and a.get("type") != "hidden":
            (self.inner if self.depth else self.outer).add(a["name"])
            if self.depth and "required" in a:
                self.required_inner.add(a["name"])

    def handle_endtag(self, tag):
        if tag == "details":
            self.depth -= 1
        elif tag == "summary":
            self.in_summary = False

    def handle_data(self, data):
        if self.in_summary:
            self.summary += data


def form_of(page):
    return page.split('id="record"', 1)[1].split("</form>", 1)[0]


def chosen(form, name="hypothesis"):
    """その select で選ばれている値。何も印が無ければ None（ブラウザは先頭を送る）。"""
    box = re.search(rf'<select name="{name}">(.*?)</select>', form, flags=re.S).group(1)
    got = re.findall(r'<option value="([^"]*)" selected>', box)
    assert len(got) <= 1, got
    return got[0] if got else None


# 見出しがある時: どの玩具でも、最初に見える欄は 3 つ。残りは閉じた details の中にあり、必須は畳みに入れない
# （閉じた欄に必須があると、ブラウザは知らせる先を出せず、送れないままになる）。
toy.RECORD_MORE = EXAMPLE
for sid in sources():
    data = hypotheses.load(sid)
    form = toy.record_form(sid, data, [])
    f = Fields(form)
    assert f.outer == FIRST, (sid, f.outer)
    # 紙を選ぶ欄は無く、記録はたたき台に入る。御来迎の次の組は H-C（柄を下から押し上げる形・本人の決定 2026-11-06）、ほかの玩具は H-A（#332）
    want = "H-C" if sid == "NDL-1187053-R0000005-L" else "H-A"
    assert re.search(r'<input type="hidden" name="hypothesis" value="([^"]+)"', form).group(1) == hypotheses.sheet_of(sid)["id"] == want, sid
    assert REST <= f.inner, (sid, f.inner)
    assert not f.required_inner, (sid, f.required_inner)
    assert len(f.details) == 1 and "open" not in f.details[0] and f.summary == EXAMPLE, (sid, f.details, f.summary)
assert "opener" in Fields(toy.record_form(G, hypotheses.load(G), [])).inner
assert "power" in Fields(toy.record_form(T, hypotheses.load(T), [])).inner

# JS を切っても開ける: 素の details で、押す口に JS を足さず、隠す属性も付けない。
page = form_of(get(f"/toy/{G}"))
assert "open" not in Fields(page).details[0] and "<script" not in page and "onclick" not in page and " hidden" not in page, page
print("ok: 見出しがある時は 3 つを見せ、残りを素の details に畳む")

# 押す所の決まり（#137）で summary を inline-flex にする幅でも、開け閉めの印が出る。消えると、ただの字に見えて畳んだ欄に気づけない。
assert "summary::before" in skin.TAP_FLOOR and "details[open]>summary::before" in skin.TAP_FLOOR
assert "▶" not in skin.TAP_FLOOR, "iPhone で絵文字になる事がある"
assert skin.TAP_FLOOR in get(f"/toy/{G}")

# 試した後の紙が開く条件は変えない（S-03）。畳みは閉じたまま、見た事だけで残せて、開くのは記録のある案の紙だけ。
assert post(f"/toy/{G}/print", hypothesis=GS)[0] == 303
for hid in (GS, "H-B"):
    assert status(f"/sheet/{G}/{hid}_v1_after.pdf") == 403
assert post(f"/toy/{G}/record", hypothesis=GS, result="動いた")[0] == 303
assert records.all_records(G)[-1]["hypothesis_id"] == GS
assert status(f"/sheet/{G}/{GS}_v1_after.pdf") == 200
assert status(f"/sheet/{G}/H-B_v1_after.pdf") == 403
print("ok: 試した後の紙が開く条件は前と同じ（記録のある案の紙だけ開く）")

# 畳んだ欄に書いた字も送られ、記録の形は前と同じ。
form = form_of(get(f"/toy/{G}"))
written = {"first_moved": "外筒の先", "stuck": "折りの向き", "what_if": "折りの幅", "idea": "糊を減らす", "note": "紙が厚かった", "opener": "糸"}
assert set(written) <= Fields(form).inner, "畳んだ欄が同じ form の中にある（閉じたままでも送られる）"
assert post(f"/toy/{G}/record", hypothesis=GS, result="動いた", impression="楽しかった", fix_part="扇", fix_change="糊を減らした", fix_outcome="開いた", **written)[0] == 303
rec = records.all_records(G)[-1]
assert rec["hypothesis_id"] == GS and rec["result"] == "動いた" and rec["impression"] == "楽しかった" and rec["opener"] == "糸", rec
assert rec["answers"] == {"first_moved": "外筒の先", "stuck": "折りの向き", "what_if": "折りの幅"}, rec
assert rec["ideas"] == ["糊を減らす"] and rec["note"] == "紙が厚かった", rec
assert rec["fixes"] == [{"part": "扇", "change": "糊を減らした", "outcome": "開いた"}], rec
assert {"source_id", "hypothesis_id", "sheet_version", "result", "impression", "opened_deg", "opener", "power", "minutes_to_try", "fixes", "note", "answers", "ideas"} <= set(rec), rec
print("ok: 畳んだ欄に書いた字も送られ、記録の形は前と同じ")

# 通らなかった時は畳みを開いて、書いた字と選んだ物を見せる。最初の頁は閉じたまま。
bad = {"hypothesis": GS, "note": "3 枚目で<止まった>", "first_moved": "筒", "opener": "糸"}  # 見た事を選んでいない
code, page = post(f"/toy/{G}/record", **bad)
assert code == 422, code
form = form_of(page)
assert "open" in Fields(form).details[0], form
assert 'value="筒"' in form and "3 枚目で&lt;止まった&gt;</textarea>" in form and "<option selected>糸</option>" in form, form
assert "open" not in Fields(form_of(get(f"/toy/{G}"))).details[0]
print("ok: 通らなかった時は畳みを開き、書いた字を隠さない")

# 版が 2 つ以上ある時の欄は畳まない。見えないまま送ると、別の版の記録になる。版を言わなければ前と同じ「いちばん新しい版」。
(out_dir(G) / f"{GS}_v2.pdf").write_bytes(b"%PDF-1.4\n")
form = form_of(get(f"/toy/{G}"))
assert "sheet_version" in Fields(form).outer, form
assert chosen(form, "sheet_version") is None
print("ok: 版の欄は畳まない")

# 話した考えから作った本人の案がある時だけ、どの紙かを選ぶ欄が出る。畳まない: 見えないまま送ると、記録と試した後の紙が別の案になる。
form = toy.record_form(G, hypotheses.load(G), [{"id": "OWN-1", "name": "糸で開く形"}])
assert "hypothesis" in Fields(form).outer and "hypothesis" not in Fields(form).inner, form
assert chosen(form) == "OWN-1", "作った本人の案を選んだ形で出す（たたき台の記録に取り違えない）"
print("ok: 本人の案がある時のどの紙かの欄は畳まない")

# 見出しの文が無い時（本人の確認が済むまで）: 畳まず、全部の欄が見える。並びは同じで、残りが後ろに来る。
toy.RECORD_MORE = ""
for sid in sources():
    form = toy.record_form(sid, hypotheses.load(sid), [])
    f = Fields(form)
    assert not f.details and not f.inner and "<summary" not in form and (FIRST | REST) <= f.outer, (sid, f.outer)
    assert form.index('name="hypothesis"') < form.index('name="result"') < form.index('name="impression"') < form.index('name="fix_part"') < form.index('name="first_moved"'), sid
form = form_of(get(f"/toy/{G}"))
assert form.index('name="fix_outcome"') < form.index('name="opener"') < form.index('name="first_moved"'), form
assert EXAMPLE not in get(f"/toy/{G}")
code, page = post(f"/toy/{G}/record", **bad)
assert code == 422 and 'value="筒"' in form_of(page) and "<details" not in form_of(page)
print("ok: 見出しの文が無い間は畳まず、全部の欄が見える")

# 入っている見出し。本人が採った文そのものを字で見る。
ADOPTED = "もっと書く（あれば）"
assert SHIPPED == ADOPTED, SHIPPED
toy.RECORD_MORE = SHIPPED
f = Fields(form_of(get(f"/toy/{G}")))
assert f.summary == ADOPTED and "open" not in f.details[0] and FIRST <= f.outer and REST <= f.inner, (f.summary, f.outer)
print("ok: 本人が採った見出しで畳まれる")
print("ok")
