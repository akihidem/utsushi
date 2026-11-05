"""頁に出る型紙はたたき台の 1 枚だけ（本人の決定 11-05、J-032、#332 の 2 本目）。

ここの「1 枚」は玩具ごとの型紙の数で、作り方の印の one_sheet（紙一枚。紙だけで作れる事）とは別の物。
本人の決定（19:44）で紙一枚は必須でなく、竹ひごやタコ糸を使うたたき台もある。

見る事:
1. 玩具の頁・英語の頁は、たたき台の札だけを出す。紙を選ぶ欄が無い。ほかの仮説の札を送っても刷らない
2. 作りながら見る頁は、紙の印なしでたたき台を開く。ほかの仮説だけを刷った置き場でも、その紙は開かない
3. 記録は、手帖・作りながら見る頁・玩具の頁のどこからでも、たたき台の hypothesis_id で残る
4. 前の記録と、それで刷った紙は読める（R-0002 は H-C の記録）
5. 一覧の「紙 1 枚」の絞り込みは、たたき台の印で数える。必須 2 種は入らなくてよい（本人の決定 19:44）
6. ways --json の行は sheet と reading_of を持つ（エンジンの形と同じ）。行は消さない
7. 次の版の欄と「次の版を待つ報告」は、たたき台の記録だけに出す。ほかの仮説の記録の欄は、送っても理由の合わない失敗の文になるだけだった
8. 札の上の断り（記録の note）は頁に出さない（本人の決定 11-05・案 A）。note は作る側の控えとして記録と一覧の命令に残す
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import hypotheses, making_log, records, ways  # noqa: E402
from omochae.metrics import ALLOWED  # noqa: E402
from web import toy, toys  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
TRIAL = next(p.stem for p in sorted((ROOT / "data/hypotheses").glob("*.json"))
             if json.loads(p.read_text(encoding="utf-8")).get("stage") == "試作" and len(json.loads(p.read_text(encoding="utf-8"))["hypotheses"]) > 1)
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a):
        return None


def get(path):
    try:
        return urllib.request.urlopen(base + path, timeout=120).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


def post(path, form):
    req = urllib.request.Request(base + path, urllib.parse.urlencode(form).encode(), {"Origin": base, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        r = urllib.request.build_opener(NoRedirect).open(req, timeout=120)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def others(sid):
    data = hypotheses.load(sid)
    return data["sheet"], [h for h in data["hypotheses"] if h["id"] != data["sheet"]]


# 1. 頁はたたき台の 1 枚だけ。紙を選ぶ欄が無い。紙を刷る前と後の両方で見る
for sid in (G, T, TRIAL):
    sheet, rest = others(sid)
    assert rest and sheet == "H-A", sid
    for when in ("刷る前", "刷った後"):
        page = get(f"/toy/{sid}")
        assert page.count('<div class="plate">') == 1, (sid, when)
        assert '<select name="hypothesis">' not in page, (sid, when, "紙を選ぶ欄")
        assert f'<input type="hidden" name="hypothesis" value="{sheet}"' in page, (sid, when)
        for h in rest:
            letter = hypotheses.letter(h)
            assert f"仮説 {letter}" not in page, (sid, when, letter)
            assert f'value="{h["id"]}"' not in page, (sid, when, h["id"])
        assert ('id="ask"' in page) == (when == "刷った後"), (sid, when, "聞く欄は、たたき台の紙を刷った後に出す")
        if when == "刷った後":
            assert re.findall(r'name="hypothesis" value="([^"]+)"', page.split('id="ask"', 1)[1].split("</form>", 1)[0]) == [sheet], (sid, "聞く口はたたき台を送る")
        if when == "刷る前":
            for h in rest:
                assert post(f"/toy/{sid}/print", {"hypothesis": h["id"]})[0] == 422, (sid, h["id"])
                assert post(f"/en/toy/{sid}/print", {"hypothesis": h["id"]})[0] == 422, (sid, h["id"])
                assert not list(out_dir(sid).glob(f'{h["id"]}_v*')), "断った紙を残さない"
            assert post(f"/toy/{sid}/print", {"hypothesis": sheet})[0] == 303, sid
    en = get(f"/en/toy/{sid}")
    assert en.count('<div class="plate">') == 1 and "Idea B" not in en and f'name="hypothesis" value="{sheet}"' in en, sid

# 2. 作りながら見る頁は、紙の印なしでたたき台を開く。先に刷ったほかの仮説の紙では開かない（虎 B だけの置き場で開いていた形）
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
sheet, rest = others(TRIAL)
out_dir(TRIAL).mkdir(parents=True, exist_ok=True)
assert hypotheses.print_sheet(TRIAL, rest[0]["id"], str(out_dir(TRIAL) / f'{rest[0]["id"]}_v1'), 1) == 0
assert 'class="tsukuru' not in get(f"/toy/{TRIAL}/tsukuru"), "ほかの仮説の紙だけなら、作りながら見る頁は開かない"
assert f'href="/toy/{TRIAL}/tsukuru"' not in get(f"/toy/{TRIAL}")
assert post(f"/toy/{TRIAL}/print", {"hypothesis": sheet})[0] == 303
tsukuru_page = get(f"/toy/{TRIAL}/tsukuru")
assert 'class="tsukuru' in tsukuru_page and f'name="hypothesis" value="{sheet}"' in tsukuru_page, "たたき台を開く"
assert f'value="{rest[0]["id"]}"' not in tsukuru_page
# 作りながら見る頁の出来事も、その頁の form が送る番号で残る
assert post(f"/toy/{TRIAL}/step", {"hypothesis": re.search(r'name="hypothesis" value="([^"]+)"', tsukuru_page).group(1), "step": "1", "event": "next"})[0] == 303
assert {e["hypothesis_id"] for e in making_log.steps(TRIAL)} == {sheet}

# 聞く口は、たたき台の紙について聞く。ほかの仮説の紙も刷ってある置き場で、form の中の番号を見る
# （頁全体で探すと、聞く口の番号を替えても、ほかの form のたたき台の番号に当たって通る）
ask_form = get(f"/toy/{TRIAL}").split('id="ask"', 1)[1].split("</form>", 1)[0]
assert re.findall(r'name="hypothesis" value="([^"]+)"', ask_form) == [sheet], "聞く口はたたき台を送る"

# 手帖も、ほかの仮説の紙が刷ってあっても、たたき台の 1 枚だけを出す
techo = get(f"/toy/{TRIAL}/techo")
assert re.findall(r'data-hid="([^"]+)"', techo) == [sheet], "手帖の紙もたたき台だけ"

# 3. 記録はその 1 枚の hypothesis_id で残る（頁の form が送る値のまま送る）
sent = re.search(r'name="hypothesis" value="([^"]+)"', get(f"/toy/{TRIAL}").split('id="record"', 1)[1]).group(1)
assert sent == sheet
result = hypotheses.load(TRIAL).get("template")
from omochae.compose import TEMPLATES  # noqa: E402

first_result = TEMPLATES[result].RESULTS[0]
assert post(f"/toy/{TRIAL}/record", {"hypothesis": sent, "result": first_result})[0] in (200, 303)
assert post(f"/toy/{TRIAL}/record-json", {"hypothesis": re.findall(r'data-hid="([^"]+)"', techo)[0], "result": first_result, "json": "1"})[0] == 201
got = [r["hypothesis_id"] for r in records.all_records(TRIAL) if r.get("source_id") == TRIAL]
assert got == [sheet, sheet], got

# 4. 前の記録は読める。ほかの仮説で試した記録の紙は、記録からのリンクで開ける（札には出さない）
assert post(f"/toy/{TRIAL}/record", {"hypothesis": rest[0]["id"], "result": first_result})[0] in (200, 303)
page = get(f'/toy/{TRIAL}?see={rest[0]["id"]}&kind=sheet&v=1')
assert f'/sheet/{TRIAL}/{rest[0]["id"]}_v1.png' in page, "記録のある前の紙は読める"
never = rest[1]["id"] if len(rest) > 1 else None
if never:
    assert f'/sheet/{TRIAL}/{never}_v1.png' not in get(f"/toy/{TRIAL}?see={never}&kind=sheet&v=1")
# 札に無い紙（記録の無い紙）は、印を変えても窓に出ない
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
out_dir(TRIAL).mkdir(parents=True, exist_ok=True)
assert hypotheses.print_sheet(TRIAL, rest[0]["id"], str(out_dir(TRIAL) / f'{rest[0]["id"]}_v1'), 1) == 0
assert post(f"/toy/{TRIAL}/print", {"hypothesis": sheet})[0] == 303
win = get(f'/toy/{TRIAL}?see={rest[0]["id"]}&kind=sheet&v=1').split('id="win"', 1)[1].split("</section>", 1)[0]
assert f'/sheet/{TRIAL}/{sheet}_v1.png' in win and f'/sheet/{TRIAL}/{rest[0]["id"]}_v1.png' not in win
(pathlib.Path(os.environ["OMOCHAE_DATA"]) / "records").mkdir(parents=True, exist_ok=True)
for rid in ("R-0001", "R-0002"):
    (pathlib.Path(os.environ["OMOCHAE_DATA"]) / "records" / f"{rid}.json").write_text((ROOT / "data/records" / f"{rid}.json").read_text(encoding="utf-8"), encoding="utf-8")
gpage = get(f"/toy/{G}")
assert "R-0002" in gpage and "R-0001" in gpage, "R-0001・R-0002 が読める"

# 5. 一覧の「紙 1 枚」は、たたき台の印で数える（前は全部の仮説の印で 39 種。本人の決定 19:44 で必須 2 種が 0 種でよい）
papers = toys.paper_only_sids(toys.sources())
assert len(papers) == 33 and G not in papers and T not in papers, len(papers)
table = ways.table()
assert sorted(papers) == sorted(r["source_id"] for r in table if r["sheet"] and r["one_sheet"])
listed = toys.page("tenji", "/toys", paper=True)
assert f'href="/toy/{G}"' not in listed and "先頭の 0 つ" not in listed and "全部を型紙にする途中の試作です" in listed
assert "紙一枚" not in ways.toy_labels(G) and "紙一枚" not in ways.toy_labels(T)

# 6. ways の行は sheet と reading_of と source_id を持つ（エンジンの形）。ほかの仮説の行も消さない
sheets = {}
for r in table:
    assert isinstance(r["sheet"], bool) and r["source_id"], r
    if r["sheet"]:
        assert r["reading_of"] is None and r["source_id"] not in sheets, r
        sheets[r["source_id"]] = r["hypothesis_id"]
assert len(sheets) == 83 and set(sheets.values()) == {"H-A"}
assert all(r["reading_of"] == sheets[r["source_id"]] for r in table if not r["sheet"]) and len(table) > 83
out = subprocess.run([sys.executable, "-m", "omochae.ways", "--json"], capture_output=True, text=True)
assert out.returncode == 0 and json.loads(out.stdout) == json.loads(json.dumps(table, ensure_ascii=False))

# 7. 次の版の欄は、たたき台の記録だけ。本物の記録で見る（R-0001 は H-A、R-0002 は H-C。どちらも説明がある）
(pathlib.Path(os.environ["OMOCHAE_DATA"]) / "loop").mkdir(parents=True, exist_ok=True)
for rid in ("R-0001", "R-0002"):
    (pathlib.Path(os.environ["OMOCHAE_DATA"]) / "loop" / f"explanation-{rid}.json").write_text((ROOT / "data/loop" / f"explanation-{rid}.json").read_text(encoding="utf-8"), encoding="utf-8")
gpage = get(f"/toy/{G}")
assert "/record/R-0001/next" in gpage and "/record/R-0002/next" not in gpage and 'id="next-R-0002"' not in gpage
kaizen = gpage.split('id="kaizen"', 1)[1]
assert 'href="#R-0001"' in kaizen and 'href="#R-0002"' not in kaizen, "次の版に進めない記録を、待つ報告に数えない"
assert "説明: " in gpage.split('id="R-0002"', 1)[1].split('id="R-0001"', 1)[0] or "説明: " in gpage.split('id="R-0002"', 1)[1], "記録の説明は読める"
assert post("/record/R-0002/next", {"interpretation": "x", "param": "fold_count", "to": "24", "why": "x", "by": "x"})[0] == 422
assert not list(out_dir(G).glob("H-C_v2*"))
# 試作の玩具でも、ほかの仮説の記録からは次の版を作らない（作っても札に出ない紙が増えるだけ）
own_data = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = own_data
out_dir(TRIAL).mkdir(parents=True, exist_ok=True)
other = rest[0]["id"]
assert hypotheses.print_sheet(TRIAL, other, str(out_dir(TRIAL) / f"{other}_v1"), 1) == 0
assert post(f"/toy/{TRIAL}/record", {"hypothesis": other, "result": first_result})[0] in (200, 303)
rid = records.all_records(TRIAL)[0]["id"]
assert post(f"/record/{rid}/explain", {"text": "説明", "next_idea": "次", "by": "書いた人"})[0] in (200, 303)
tpage = get(f"/toy/{TRIAL}")
assert f"/record/{rid}/next" not in tpage and f'href="#{rid}"' not in tpage.split('id="kaizen"', 1)[1]
# 値は、断りが無ければ版が作れる物にする（範囲の外の値だと、断りを外しても 422 になり、見張りにならない）
param = sorted(ALLOWED[result])[0]
to = {**TEMPLATES[result].DEFAULTS, **rest[0]["params"]}[param] - 1
assert post(f"/record/{rid}/next", {"interpretation": "x", "param": param, "to": str(to), "why": "x", "by": "x"})[0] == 422
assert not list(out_dir(TRIAL).glob(f"{other}_v2*"))

# 8. 札の上の断りは頁に出さない（本人の決定 11-05・案 A）。作る側の控えとしては残す
sids = toys.sources()
assert len(sids) == 83
for sid in sids:
    data = hypotheses.load(sid)
    page = toy.toy_page(sid)
    assert data["note"] and data["note"] not in page, (sid, "断りを頁に出さない")
    assert "どれも試していない" not in page and "どれが正しいかは書かない" not in page, sid
    assert ways.NOTE in page, (sid, "作り方の印の断りは残す")
    assert data["note"] in hypotheses.list_lines(data), (sid, "作る側の一覧の命令には残す")

server.shutdown()
print("ok 頁に出る型紙はたたき台の 1 枚だけ。記録はその 1 枚の番号で残り、前の記録と紙は読める")
