"""次の版の欄に、1 つ変えるだけでは動かせない寸法を出さない。動かせない理由は検査の誤りでなく型の拘束である事も見張る。

なぜ: 御来迎の押し上げる量は 10〜90 の 261 値を試して 1 つも通らなかった。つまみの形では、扇を隠す床（中心の高さ＋扇の高さ ≦ 押し上げる量）と、
内筒を収める床（内筒の長さ ≦ 筒の高さ − 押し上げる量）に挟まれ、今の寸法だと 69 ちょうどしか通らない（21＋48＝84−15）。どちらも凍結の基準どおりの検査。
欄は「寸法を 1 つ変える」形なので、選んでも必ず断られる項目になっていた。ほかの寸法を変えると通る幅が開くので、固定の表でなく今の版の値で決める。

折りの数の 31.4 は幅の中なのに「6〜40 の間で」と断っていた。整数だけの寸法は欄が整数だけを受け（step=1 とブラウザの標準の吹き出し）、新しい字を足さない。
床の文は作る側の字なので頁に出さない。JS が無い時や直に送った時は、前からある「今の値と次の一手」の文を出す。
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

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")

from omochae import hypotheses, loop  # noqa: E402
from omochae.compose import TEMPLATES, compose  # noqa: E402
from omochae.metrics import ALLOWED  # noqa: E402
from omochae.templates import den_den, slider_fan, spin_toy  # noqa: E402
from web import skin, toy  # noqa: E402
from web.play_server import serve  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    return urllib.request.urlopen(base + path).read().decode()


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    try:
        x = urllib.request.urlopen(r)
        return x.status, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def options(page):
    form = page.split('action="/record/R-0001/next#next-R-0001"', 1)[1].split("</form>", 1)[0]
    return re.findall(r'<option value="([a-z_]+)">', form)


def source(sid):
    return json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))


# 1. 欄に出ない。御来迎で動かせない寸法は押し上げる量だけで、ほかの 7 つは出る
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] in (200, 303)
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた"})[0] in (200, 303)
assert post("/record/R-0001/explain", {"text": "折りが固くて戻る", "next_idea": "厚さを変える", "by": "大人"})[0] in (200, 303)
shown = options(get(f"/toy/{G}"))
assert "push_amount" not in shown, "選んでも必ず断られる寸法が欄に出ている"
assert sorted(shown) == sorted(ALLOWED["slider_fan"] - {"push_amount"}), shown

# 2. 動かせない理由は型の拘束。69 より小さいと扇が隠れず、大きいと内筒が収まらない。検査の誤りで落ちているなら、ここが崩れる
now = {**slider_fan.DEFAULTS, **loop.version_params(G, "H-A", 1)[0]}
assert now["pivot_above_rim"] + now["fold_height"] == now["push_amount"] == now["tube_height"] - now["pusher_height"], now
for s in range(*slider_fan.RANGES["push_amount"]):
    floors = {f.floor for f in slider_fan.check_physics({**now, "push_amount": s})}
    assert floors == (set() if s == 69 else {"F5.fan_height"} if s < 69 else {"F5.stroke"}), (s, floors)

# 3. 直に送っても断る（欄に出さないだけで、床は同じ）。断りの文は今までどおりで、版は増えない
form = {"interpretation": "折りが固い", "why": "開きを見る", "by": "大人"}
code, page = post("/record/R-0001/next", {**form, "param": "push_amount", "to": "70"})
assert code == 422 and "押し上げる動きが筒の中に収まりません" in page and loop.latest_version(G, "H-A") == 1, (code, page[:300])

# 4. ほかの寸法を変えて幅が開くと、欄に出て通る。表で固定しない
assert post("/record/R-0001/next", {**form, "param": "fold_height", "to": "47.5"})[0] in (200, 303)
assert loop.latest_version(G, "H-A") == 2
page = get(f"/toy/{G}")
assert "push_amount" in options(page) and "押し上げる量（mm）: 今 69（" in page, options(page)
assert post("/record/R-0001/next", {**form, "param": "push_amount", "to": "68.6"})[0] in (200, 303)
assert loop.latest_version(G, "H-A") == 3 and loop.version_params(G, "H-A", 3)[0]["push_amount"] == 68.6

# 5. 整数だけの寸法は、欄が整数だけを受ける。数の欄で、既定は小数も通し（step=any）、選んだ寸法が整数だけの時に JS が step=1 にする。min と max は付けない（幅の外は今ある字で断る）
page = get(f"/toy/{G}")
box = page.split('action="/record/R-0001/next#next-R-0001"', 1)[1].split("</details>", 1)[0]
assert '<input type="number" step="any" name="to" inputmode="decimal" required>' in box, box[:900]
assert " min=" not in box and " max=" not in box
assert ',w=["fold_count"];' in box and 'addEventListener("change"' in box and 't.step=w.includes(s.value)?"1":"any"' in box, box[-500:]
# 欄に戻した値は step の起点になる（31.4 を戻すと 32 が断られる）ので、起点を 0 に戻す。動きは Chromium で見た
assert 't.value=t.value;t.removeAttribute("value")' in box, box[-500:]
# 数の欄も字の欄と同じ形にする（皮の字の色と地。黒のジンで白く浮かないように）
assert "input[type=text],input[type=number],textarea,select{display:block" in skin.BASE
assert "label:not(.sr):has(>input[type=number])" in skin.TAP_FLOOR
# JS が無い時や直に送った時: 床の文を頁に出さず、幅の中なので幅も言わない。今の値と次の一手だけを言い、書いた値を欄に戻す
code, page = post("/record/R-0001/next", {**form, "param": "fold_count", "to": "31.4"})
assert code == 422 and "折りの数は今 28 です。近い値を試すか、別の寸法を変えてください。" in page, page[:400]
assert "折り数は整数" not in page and "6〜40 の間で" not in page, page[:400]
assert 'name="to" inputmode="decimal" required value="31.4"' in page
assert loop.latest_version(G, "H-A") == 3
# 幅の外は今ある字のまま
code, page = post("/record/R-0001/next", {**form, "param": "fold_count", "to": "99"})
assert code == 422 and "折りの数は 6〜40 の間で書いてください（今 28）。" in page, page[:400]
# 整数の決まりを持つほかの雛形も同じ。床の文（数は整数・枚数・本数なので整数）を出さない
DEN, SPIN = "NDL-1187053-R0000007-R", "NDL-1187053-R0000020-R"
for sid, tpl, param, to in ((DEN, den_den, "beads_inside", 1.5), (SPIN, spin_toy, "blade_count", 4.5)):
    params = {**tpl.DEFAULTS, **hypotheses.sheet_of(sid)["params"], param: to}
    lines = toy.next_reasons(tpl.check_range(params), sid, hypotheses.sheet_of(sid)["id"], param, to)
    assert len(lines) == 1 and lines[0].endswith("近い値を試すか、別の寸法を変えてください。") and "整数" not in lines[0], lines
    assert param in toy.whole_params(tpl.ID), (tpl.ID, toy.whole_params(tpl.ID))
# 整数だけの寸法の表は、範囲の検査と同じ答え。整数なら通り、整数でなければ落ちる寸法だけが入る
for tid, tpl in TEMPLATES.items():
    for k in sorted(ALLOWED[tid]):
        lo, hi = tpl.RANGES[k]
        half = lo + (hi - lo) * 0.6317
        assert (k in toy.whole_params(tid)) == bool(tpl.check_range({**tpl.DEFAULTS, k: half})), (tid, k)
        assert not tpl.check_range({**tpl.DEFAULTS, k: lo}), (tid, k, lo)
assert toy.whole_params("slider_fan") == ["fold_count"] and toy.whole_params("pivot_counterweight") == []
# 整数だけの寸法を持たない玩具には、JS を付けない（虎。欄は小数も通す）
assert "<script" not in toy.next_form({**loop.record("R-0001"), "source_id": "NDL-1187053-R0000014-R", "hypothesis_id": "H-A"})

# 6. 欄に出す寸法には、配置の検査まで通る値がある（画面の判定は範囲と物理の床だけなので、ここで compose と照らす）。雛形ごとに 1 つと、動かない寸法を持つ玩具で見る
seen, sample = set(), [G, "NDL-1187053-R0000021-L-2", "NDL-1187053-R0000029-R-2"]
for path in sorted((ROOT / "data/hypotheses").glob("*.json")):
    t = hypotheses.load(path.stem).get("template", "slider_fan")
    if t not in seen:
        seen.add(t)
        sample.append(path.stem)
for sid in sample:
    t, hid = hypotheses.load(sid).get("template", "slider_fan"), hypotheses.sheet_of(sid)["id"]
    current, _ = loop.version_params(sid, hid, loop.latest_version(sid, hid))
    found = loop.movable_params(sid, hid)
    for k, v in found.items():
        assert v != {**TEMPLATES[t].DEFAULTS, **current}[k], (sid, k, v)
        assert compose(t, {**current, k: v}, source(sid))[2] == [], (sid, k, v)
    # 欄に出さない寸法は、細かく試しても通らない
    for k in sorted(ALLOWED[t] - set(found)):
        lo, hi = TEMPLATES[t].RANGES[k]
        for i in range(161):
            v = lo + (hi - lo) * i / 160
            v = int(v) if float(v).is_integer() else v
            if v != {**TEMPLATES[t].DEFAULTS, **current}.get(k):
                assert compose(t, {**current, k: v}, source(sid))[2] != [], (sid, k, v)

# 試す値の形: 近くを細かく（幅が狭くても見つける）、近くの整数と遠くの整数（整数の寸法のため）、幅の両端まで（今の値から離れた所に通る幅があっても見つける）。
# 今のデータでは重なっていて、頁の答えだけでは見張れないので、形を直に見る
trial = loop._trial_values(10, 90, 69)
assert trial[:2] == [68.9, 69.1] and {68, 70, 10, 90, 14, 66} <= set(trial) and 69 not in trial, trial[:8]
whole = {v for v in loop._trial_values(6, 40, 28) if float(v).is_integer()}
assert {25, 26, 27, 29, 30, 31, 6, 40} <= whole and {8, 23} <= whole, sorted(whole)
assert all(isinstance(v, int) for v in whole), "画面の口と同じに、整数で言える値は整数で渡す"
assert loop._trial_values(1, 2, 2)[-1] == 1 and all(1 <= v <= 2 for v in loop._trial_values(1, 2, 2))

# 7. 出す寸法が 1 つも無ければ、欄ごと出さない
real, record = loop.movable_params, loop.record("R-0001")
loop.movable_params = lambda *a: {}
assert toy.next_form(record) == "", "選べる物が無い欄を出さない"
loop.movable_params = real
# 全部の玩具: 版 1 で動かせない寸法は、御来迎の押し上げる量（1 で見た）と独楽 2 種の胴を分ける枚数だけ。御来迎はここでは版 3 で、押し上げる量も動く
fixed = set()
for path in sorted((ROOT / "data/hypotheses").glob("*.json")):
    sid, hid = path.stem, hypotheses.sheet_of(path.stem)["id"]
    fixed |= {(sid, k) for k in ALLOWED[hypotheses.load(sid).get("template", "slider_fan")] - set(loop.movable_params(sid, hid))}
assert fixed == {("NDL-1187053-R0000021-L-2", "cone_pieces"), ("NDL-1187053-R0000029-R-2", "cone_pieces")}, sorted(fixed)

server.shutdown()
print("ok 次の版の欄には、今の版で 1 つ変えて通る寸法だけが出る")
