"""工作の手帖の 1 手 1 画面（本人の決定 11-05、Issue #87）。押す所の名前・1 画面の数・字のかたまり・絵・声の決まりを見る。

ブラウザは使わない（./run.sh はブラウザなしで動く決まり）。頁の字と CSS と JS の字を読み、場面ごとに出る物は data-on から数える。
大きさと、押して進む事は、手元のブラウザで別に測った（gate-trial の節に書く）。
"""
import html.parser
import json
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, instructions, making_log, render, talk_log  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web import hanasu, skin, techo_step  # noqa: E402
from web.play_server import serve  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def req(path, data=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    r = urllib.request.Request(base + path, data=body, method="POST" if body is not None else "GET",
                               headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    try:
        x = urllib.request.urlopen(r)
        return x.status, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class Page(html.parser.HTMLParser):
    """頁を読み、押す所と字のかたまりを、どの場面で出るか（data-on）といっしょに集める。"""
    VOID = {"input", "meta", "br", "img", "link", "path", "rect", "circle", "line", "polygon", "polyline"}
    BLOCKS = {"p", "li", "h1", "h2", "button", "a", "label", "textarea", "summary"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.targets, self.blocks = [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.VOID:
            return
        cell = {"tag": tag, "attrs": a, "text": ""}
        self.stack.append(cell)
        if tag in ("button", "a", "summary") or (tag == "label" and "key" in a.get("class", "")):
            self.targets.append(cell)
        if tag in self.BLOCKS and not any(c["tag"] in self.BLOCKS for c in self.stack[:-1]):
            self.blocks.append(cell)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        while self.stack and self.stack.pop()["tag"] != tag:
            pass

    def handle_data(self, data):
        if any(c["tag"] in ("style", "script") or "aria-hidden" in c["attrs"] or "sr" in c["attrs"].get("class", "").split() for c in self.stack):
            return
        for c in self.stack:
            c["text"] += data

    def _shown(self, cell, scene):
        chain = self.stack_of(cell)
        for c in chain:
            on = c["attrs"].get("data-on")
            if on is not None and scene not in on.split():
                return False
            if "hidden" in c["attrs"] and c["attrs"].get("id") not in ("mic",):
                return False
        return True

    def stack_of(self, cell):
        return cell.get("chain", [cell])

    def feed_all(self, text):
        # 親のたどりを持たせるため、開く時に今の stack を写す
        orig = self.handle_starttag

        def start(tag, attrs):
            orig(tag, attrs)
            if tag not in self.VOID:
                self.stack[-1]["chain"] = list(self.stack)
        self.handle_starttag = start
        self.feed(text)
        return self

    def shown_targets(self, scene):
        return [c for c in self.targets if self._shown(c, scene) and c["attrs"].get("id") not in ("mic", "close")]

    def shown_blocks(self, scene):
        return [c for c in self.blocks if self._shown(c, scene) and c["text"].strip()]


def read(page):
    return Page().feed_all(page)


def visible(page):
    """人が読む字だけ（style・script・属性を除く）。"""
    return re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script)\b.*?</\1>", " ", page, flags=re.S))


NAMES = ("つぎ", "もどる", "こまった", "とって", "のこす", "はじめる")  # 本人の決定 11-05。一字も変えない

# ---- 紙が無い時は、紙を作る道だけ
code, none = req(f"/toy/{G}/techo")
assert code == 200 and "紙を作る" in none and f'href="/toy/{G}"' in none and "はじめる" not in none, "刷った紙が無い時は作る道へ"

assert req(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] in (200, 303)
assert req(f"/toy/{T}/print", {"hypothesis": "H-A"})[0] in (200, 303)
code, page = req(f"/toy/{G}/techo")
assert code == 200
doc = read(page)

# ---- 押す所の名前は 6 つ。字を一字も変えない
assert techo_step.NAMES == NAMES
for name in NAMES:
    assert any(c["text"].strip() == name for c in doc.targets), name
for scene in ("start", "step", "end"):
    names = [c["text"].strip() for c in doc.shown_targets(scene)]
    assert all(n in NAMES for n in names if n), (scene, names)
assert [c["text"].strip() for c in doc.shown_targets("start")] == ["はじめる"]
assert [c["text"].strip() for c in doc.shown_targets("step")] == ["もどる", "つぎ", "こまった"]
# 「のこす」の画面: 声と動画が主で、字は畳んだ追加（本人の方針 19:45、#335）。押す所は とって・畳み（字なしの形）・のこす
assert sorted(c["text"].strip() for c in doc.shown_targets("end")) == sorted(["とって", "", "のこす"])
fold = page.split('<details class="fold" id="fold">', 1)[1].split("</details>", 1)[0]
assert '<textarea id="kufu"' in fold and "<summary" in fold and '<details class="fold" id="fold" open' not in page, "字の欄は畳んだ追加として残る"
assert page.count("<textarea") == 1, "打つ欄はこの 1 つだけ"

# ---- 1 画面に 3 つまで（閉じる印とマイクを除く）。結果の札も雛形の値の数（3 つまで）
for scene in ("start", "step", "henji", "end", "kekka"):
    assert len(doc.shown_targets(scene)) <= 3, (scene, [c["text"] for c in doc.shown_targets(scene)])
for tpl in TEMPLATES.values():
    assert len(tpl.RESULTS) <= 3, tpl.ID
# ---- 結果の札は雛形の値のまま。既定の選びを置かない（凍結の床 F3 と instructions の決まり）
tiles = [c for c in doc.targets if "tile" in c["attrs"].get("class", "")]
assert [c["attrs"].get("value") for c in tiles] == list(TEMPLATES["slider_fan"].RESULTS) and not any("aria-pressed" in c["attrs"] for c in tiles)

# ---- 最初の画面: 手順の 1 文を除いて、字のかたまりは 3 個以下
first = doc.shown_blocks("start")
rest = [c for c in first if c["tag"] != "li"]
assert len(rest) <= 3, [c["text"][:20] for c in rest]
assert len([c for c in first if c["tag"] == "li"]) == 1, "手順の文は今の 1 つだけ"

# ---- 一番大きい物は今の手順の絵。絵の枠は画面の高さの半分以上（CSS で持つ。実物の大きさは手元のブラウザで測る）
assert re.search(r"\.koma\{[^}]*min-height:50svh", techo_step.STYLE), "絵の枠の床"
assert page.index('id="koma"') < page.index('id="steps"') < page.index('id="start"'), "絵 → 文 → 押す所の順"
# ---- 押す所は 64px 以上、「つぎ」と「はじめる」は 96px 以上
assert re.search(r"\.key\{[^}]*min-height:64px", techo_step.STYLE) and re.search(r"\.key\.go\{[^}]*min-height:96px", techo_step.STYLE)
for sel in (r"\.mic\{", r"\.close\{", r"\.tile\{"):
    assert re.search(sel + r"[^}]*(min-)?(width|height):(6[4-9]|[7-9]\d|\d{3,})px", techo_step.STYLE), sel
assert 'id="close"' in page

# ---- 頁の字に、版の名・記録の番号・「の紙」が無い。記録が在っても出さない
from omochae import records  # noqa: E402

rid, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた", "impression": "KANSOU"})
page = req(f"/toy/{G}/techo")[1]
doc = read(page)
text = visible(page)
assert "の紙" not in text and "版 " not in text and not re.search(r"R-\d{4}", text) and "KANSOU" not in text, "作る側の印を出さない"
assert TEMPLATES["slider_fan"].SHEET_SET not in page, "組の版の名は頁のどこにも置かない"
for h in hypotheses.load(G)["hypotheses"]:
    assert h["how_it_moves"] not in page and h["name"] not in page, "仮説の名前と動き方は出さない"
assert 'type="radio"' not in page and "<select" not in page, "紙を選ぶ札は作らない（#332）"
# 順位や成績の言葉・祝う演出が無い。試した後の紙は記録の前に渡さない（S-03）
for word in ("おめでとう", "すごい", "合格", "正解", "点数", "順位", "ランキング", "やったね", "_after", "confetti"):
    assert word not in page, word

# ---- 頁の骨: 帯なし（字を減らす）。マイクは 1 つ。録る口を持たない
assert '<nav class="nav"' not in page and skin.TAP_FLOOR in page, "帯なし。指の床は届く"
assert page.count('id="mic"') == 1 and "hanasu-mic" not in page, "マイクは 1 頁に 1 つ"
for word in ("getUserMedia", "MediaRecorder", "getDisplayMedia", "toDataURL", "drawImage", "captureStream"):
    assert word not in page, word

# ---- 声の決まり: 全体が一致した時だけ操作。ほかは質問。操作の字は送らない
W = techo_step.WORDS
for said, op in (("つぎ", "next"), ("次", "next"), ("できた", "next"), ("もどる", "back"), ("戻る", "back"), ("もう一回", "again"), ("もういっかい", "again"),
                 ("とって", "photo"), ("撮って", "photo"), ("のこす", "keep"), ("残す", "keep"), ("こまった", "stuck"), ("困った", "stuck")):
    assert W.get(said) == op, said
for said in ("次の手順ってどうやるの", "つぎはどうするの", "戻るってどういうこと", "もう一回やりたいんだけど"):
    assert techo_step.clean(said) not in W, said
js = techo_step.SCRIPT
assert "WORDS[clean(t)]" in js, "声は全部が一致した時だけ操作にする"
assert js.index("WORDS[clean(t)]") < js.index("ask(t)"), "操作の字は質問に送らない"
assert "includes(" not in js.split("const heard")[1].split("};")[0] and "indexOf(" not in js.split("const heard")[1].split("};")[0], "部分一致で進めない"
# 結果の札も声で選べる（字は値のまま残す）。どの雛形の値にも言い方がある
for tpl in TEMPLATES.values():
    for r in tpl.RESULTS:
        assert r in techo_step.RESULT_WORDS.values(), r
        assert techo_step.RESULT_WORDS[r] == r
# 読み上げの間は聞かない。「もう一回」は今の手順の文を読む
assert "if (speaking) return" in js and "sayStart" in js and "sayEnd" in js
# ---- 声を字にする所は #308 の切り替えのまま（本人の決定待ち。どちらにも切り替えられる形を保つ）
same = "typeof REC.available==='function'&&'processLocally' in REC.prototype"
assert same in hanasu.SCRIPT and same in js, "端末の中で字にできるかの見分けは話す口と同じ"
assert "processLocally = true" in js and "REC.install" in js
# 聞くと頁ごと落ちる画面がある。全員が押す釦なので、聞く前に印を置き、開き直した時は端末の中の口を使わない（同じ所で止まり続けない）
assert js.index("mem(true)") < js.index("REC.available({") and "if (how === 'local' && mem()) how = want === 'browser' ? 'browser' : 'none';" in js
assert js.index("to(n > total ? 'end' : 'step'); wake();") > 0, "聞く前に手順の画面へ移る（返事が来なくても手順は進める）"
assert hanasu.DEFAULT_MODE == "browser"
assert f'data-voice="{hanasu.mode()}"' in page
keep = os.environ.get("OMOCHAE_VOICE")
for mode in hanasu.MODES:
    os.environ["OMOCHAE_VOICE"] = mode
    assert f'data-voice="{mode}"' in req(f"/toy/{G}/techo")[1], mode
os.environ.pop("OMOCHAE_VOICE") if keep is None else os.environ.update(OMOCHAE_VOICE=keep)
# 「声が使えない画面」: 口が無い時はマイクを隠し、ボタンだけで通る
assert "mic.hidden = false" in js or "mic.hidden=false" in js
assert '<button type="button" class="mic" id="mic"' in page and "hidden" in page.split('id="mic"')[1].split(">")[0]

# ---- 断りの文: 採られた文のまま。新しい文は本人の確認までマージしない（本人の指示 11-05）
assert hanasu.UPLOAD_NOTICE in page and f'<p class="meta" id="up-notice">{hanasu.UPLOAD_NOTICE}</p>' in page
assert making_log.ASK_NOTICE not in page, "手帖は ③ の頁なので、聞く口の断りの文は使わない（本人の決定 11-05、#275）"
assert making_log.ASK_NAME_VOICE in page
assert hanasu.NOTICE in page
# 声がどこへ行くかは、マイクが起きる前（はじめるの画面）に言う
note = page.split('id="start-note"', 1)[1].split("</p>", 1)[0]
assert hanasu.HOW_LOCAL in note and hanasu.HOW_BROWSER in note and making_log.ASK_NAME_VOICE in note

# ---- 写真の決まりは前のまま: 手元だけの確かめ・数と大きさの決まり・内側のカメラを求めない
form = page.split('<form id="up-form"', 1)[1].split("</form>", 1)[0]
assert "大人の手元だけ・顔なし・声なし" in form and "3 つまで・1 つ 20MB まで" in form and 'data-max-n="3"' in form
assert 'capture="environment"' in form and "video/mp4" in form, "とっては外のカメラ（顔を写さない）。動画が撮れる"
# 聞いた字は畳みを開いて見せる（字は本人が見てから残す。隠したまま送らない）。床に落ちた時も開く
assert js.count("fold.open = true") == 2
assert 'id="picked"' in form and 'id="thumbs"' in form
# 確かめの欄は写真を選んだ時に出る。押さないと送らない
assert "ok.checked" in js

# ---- 上げる順: 工夫の字を床に通す → 記録 → 欄を空に → 写真。押し直しで記録を増やさない（#143）
up = js[js.index("const save"):]
assert up.index("/talk") < up.index("record-json") < up.index("form.reset()") < up.index("/media")
assert "if (go.disabled) return" in up and "go.disabled = true" in up
assert "上げました" in up and "に入りました" not in up, "工夫の数を知らせる文は本人の確認が済むまで出さない"
assert "/techo/kiroku" in up

# ---- 絵: 御来迎は折る順の 4 コマ（手順の紙と同じ形）。手順の順に進み、最後は 4 コマ目
data = hypotheses.load(G)
tpl = TEMPLATES["slider_fan"]
for h in data["hypotheses"]:
    p = {**tpl.DEFAULTS, **h["params"]}
    texts = tpl.steps(p)
    pictures, which = instructions.step_pictures("slider_fan", p, texts)
    assert len(pictures) == 4 and len(which) == len(texts), h["id"]
    assert which[0] == 0 and which[-1] == 3 and which == sorted(which) and set(which) == {0, 1, 2, 3}, (h["id"], which)
p = {**tpl.DEFAULTS, **data["hypotheses"][0]["params"]}
layout, _ = instructions.compose_sheet("slider_fan", p, json.loads((hypotheses.ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8")), "t", "h")
rects = [s for s in layout["shapes"] if s.get("tag") == "order_panel"]
assert len(rects) == 4
pictures, _ = instructions.step_pictures("slider_fan", p, tpl.steps(p))
for rect, shapes in zip(rects, pictures):
    # 手順の紙の order_panel の枠の中にある形と同じ（紙と画面で絵が食い違わない）
    def moved(s, dx, dy):
        if s["kind"] == "rect":
            return ("rect", round(s["x"] + dx, 3), round(s["y"] + dy, 3), round(s["w"], 3), round(s["h"], 3))
        return ("line", round(s["x1"] + dx, 3), round(s["y1"] + dy, 3), round(s["x2"] + dx, 3), round(s["y2"] + dy, 3))
    want = {moved(s, 0, 0) for s in layout["shapes"] if s["kind"] in ("rect", "line") and s.get("tag") != "order_panel"}
    got = {moved(s, rect["x"], rect["y"]) for s in shapes}
    assert got and got <= want, sorted(got - want)[:3]
# 絵に字を入れない。線と塗りだけ
svg = render.shapes_svg(pictures[0])
assert svg.startswith("<svg") and "<text" not in svg and 'viewBox="' in svg
assert page.count("<svg") >= 4 and page.count('class="on"') >= 1
# 全部の玩具: たたき台の紙に絵があり、手順ごとに絵が決まる。ほかの雛形は手順の紙の図を出す（段 2 まで）
from web.play_server import sources  # noqa: E402

for sid in sources():
    d = hypotheses.load(sid)
    h = d["hypotheses"][0]
    t = h.get("template") or d.get("template", "slider_fan")
    q = {**TEMPLATES[t].DEFAULTS, **h.get("params", {})}
    texts = TEMPLATES[t].steps(q)
    pics, which = instructions.step_pictures(t, q, texts)
    assert pics and all(pics) and len(which) == len(texts) and all(0 <= k < len(pics) for k in which), sid
    assert (len(pics) == 4) == (t == "slider_fan"), (sid, t, len(pics))
    assert "<svg" in render.shapes_svg(pics[0]) and not any(re.search(r"の紙|版 ?\d|R-\d", x) for x in texts), sid

# ---- 紙: たたき台（先頭）を作る。先頭が無ければ刷ってある紙
assert 'data-hid="H-A"' in page and 'data-v="1"' in page
assert req(f"/toy/{G}/print", {"hypothesis": "H-C"})[0] in (200, 303)
assert 'data-hid="H-A"' in req(f"/toy/{G}/techo")[1], "ほかの案が刷ってあっても、たたき台を作る"
assert techo_step.sheet_of(data, ["H-C"]) == "H-C" and techo_step.sheet_of(data, ["H-C", "H-A"]) == "H-A" and techo_step.sheet_of(data, []) == ""

# ---- 開く所を URL で持つ（場のリンク n=2）。最後の次は「とって・のこす」の画面
assert 'data-n="2"' in req(f"/toy/{G}/techo?n=2")[1] and 'data-n="1"' in req(f"/toy/{G}/techo?n=abc")[1]
total = len(tpl.steps(p))
assert f'data-n="{total + 1}"' in req(f"/toy/{G}/techo?n=99")[1], "範囲の外は最後の画面"

# ---- 札を押した事は作りながら見る頁と同じ口に残す
who = "abcde12345"
step = lambda n, ev: req(f"/toy/{G}/step", {"hypothesis": "H-A", "step": n, "event": ev, "json": "1", "sheet_version": 1, "who": who})
assert step(1, "start")[0] == 200 and step(1, "next")[0] == 200 and step(2, "stuck")[0] == 200 and step(total, "done")[0] == 200
got = [(s["step"], s["event"]) for s in making_log.steps(G)]
assert (1, "start") in got and (2, "stuck") in got and (total, "done") in got
for ev in ("next", "back", "stuck", "done", "start"):
    assert f"'{ev}'" in js, ev

# ---- 残す: 記録の値だけで残り、話した工夫がその記録に入り、記録の頁に出る。床に当たる字は残らない
assert req(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": "H-A", "sheet_version": 1, "step": total, "text": "電話は090-1234-5678", "via": "voice", "who": who, "json": "1"})[0] == 422
code, body = req(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": "H-A", "sheet_version": 1, "step": total, "text": "紙を二重にした", "via": "voice", "who": who, "json": "1"})
assert code == 200 and json.loads(body)["kept"]
# 字を打たなくても残せる（本人の方針 19:45）。字の無い記録も、結果の札だけで残る
code, body = req(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "sheet_version": 1, "who": "nowords0000"})
assert code == 201, body
code, body = req(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "わからない", "sheet_version": 1, "who": who})
j = json.loads(body)
assert code == 201 and j["kufu"] == 1, body
code, listed = req(f"/toy/{G}/techo/kiroku?msg=" + urllib.parse.quote("上げました"))
assert code == 200 and '<div id="mine">' in listed and j["id"] in listed and "紙を二重にした" in listed and "上げました" in listed
# 記録の頁は順路の帯を持ち、試した後の紙・説明・AI の順の札がここにある
assert '<nav class="nav"' in listed and "試した後の紙" in listed and 'name="back" value="techo"' in listed
assert listed.count("<script>(()=>{\nconst REC=") == 1
assert talk_log.kufu(G, j["id"], shared_only=True)[0]["text"] == "紙を二重にした"
# 手帖から説明を送ると、記録の頁へ戻る
op = urllib.request.build_opener(type("NoRedirect", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))
x = urllib.request.Request(base + f"/record/{j['id']}/explain", data=urllib.parse.urlencode({"text": "開いた", "next_idea": "速く押す", "by": "本人", "back": "techo"}).encode(),
                           headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
try:
    op.open(x)
    raise AssertionError("303 のはず")
except urllib.error.HTTPError as e:
    assert e.code == 303 and f"/toy/{G}/techo/kiroku?msg=" in e.headers["Location"] and e.headers["Location"].endswith("#mine"), e.headers["Location"]
# 話す口の「戻る」も記録の頁へ（JS が無い時の頁）
code, back = req(f"/toy/{G}/talk", {"scene": "keep", "record": j["id"], "text": "足した字"})
assert code == 200 and f'/toy/{G}/techo/kiroku#mine' in back

# ---- 虎: 絵は手順の紙の図。結果の札は虎の値
page = req(f"/toy/{T}/techo")[1]
doc = read(page)
assert [c["attrs"].get("value") for c in doc.targets if "tile" in c["attrs"].get("class", "")] == ["揺れた", "揺れない"]
assert "の紙" not in visible(page) and TEMPLATES["pivot_counterweight"].SHEET_SET not in page
server.shutdown()
print("ok")
