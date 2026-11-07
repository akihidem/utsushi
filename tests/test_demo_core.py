"""核の一周（demo.core）の床: まだ無い物を動いているように見せない事、例の記録が例と分かる事、1 コマが時刻だけで決まる事を見る。

Chrome も網も使わない。画面の絵は偽物を渡す。画面を撮る所は書き出しの時に通り、そこで本物の口を通らなければ止まる。
"""
import types

from PIL import Image

from demo import core, flip, script, words

# 手で作る → 持ち寄り → AI は後、の順（本人の言葉 11-05 夕）。
# つなぎ 2 は前は持ち寄りの場面の次だった（本人の決定 11-05）。表と裏に分けた（本人の決定 11-06、カード 125217）ので、
# 持ち寄りの後に境目の札と語りの後ろの 2 文が入り、その次につなぎ 2 の輪が来る
order = script.SCENES
# 「紙で作って、動いた。」は作る頁のすぐ後（窓口の決定 11-07）: 作る → 動いた → 残す → 持ちよる
assert order.index("scene3") < order.index("core_make") < order.index("scene5") < order.index("core_keep") \
    < order.index("core_gallery") < order.index("core_loop") < order.index("word_ai") < order.index("ask")
assert order.index("border") == order.index("core_gallery") + 1
assert order.index("border") < order.index("talk_physics") < order.index("talk_claude") and order.index("core_loop") == order.index("talk_claude") + 1

# まだ無い物の場面は図で描く。画面として撮らない
assert core.SOON == "これから作る"
for name in ("core_map", "core_voice", "core_loop"):
    assert not isinstance(core.build_scene(name, dict(core.CUES_ALL[name])), core.Screens), name
# 図は本人のループの定義（11-05 17:57）の 4 本。今動いていない所（型紙が生まれる・エンジンごと直る・システムが直る）は点線
assert [kind for _, _, kind in core.LOOPS] == ["now", "done", "now", "half"]
assert "".join(core.LOOPS[0][1]) == "型紙が生まれる" and "".join(core.LOOPS[1][1]) == "型紙が直る" and "".join(core.LOOPS[2][1]) == "エンジンごと直る"
assert "システムも直る" in core.LOOPS[3][1] and "ギャラリーへ" in core.LOOPS[3][1]

# 地図の真ん中は手で作る所。AI の字を置かない（本人の言葉 11-05 夕: AI が良くなるのは副次的で、手で作る楽しさに気づく事が最初）
assert "手で作る" in core.MAP_TITLE
for s in (core.MAP_TITLE, core.MAP_SUB, *(x for label, inside, _ in core.LOOPS for x in (label, *inside))):
    assert "AI" not in s, s
the_map = core.build_scene("core_map", dict(core.CUES_ALL["core_map"]))
assert the_map.frame(8.9).tobytes() != the_map.frame(0.1).tobytes()

# 字幕の案は 1 かたまりで短く（本人の方針 11-05 20:10。なるべく 15 字前後まで）
for s in (core.MAP_TITLE, core.MAP_SUB, core.GALLERY_LINE):
    assert len(s) <= 15, s

# 手で作る所を長く。作る 3 場面は 30 秒を切らない。AI の場面（word_ai・core_loop）は作る 3 場面より短い。全体は 179.5 秒以内
# 11-07 に場面 15（版の並び）へ字幕 1 つの秒を回した（窓口の決定 084919 の ③・(1) A。版の歩みは本人の言う山場）ので、
# AI の場面の上限を前の 22.5 秒から 27 秒にした。作る 3 場面より長くしない線は前のまま
making = sum(script.load_scene(n).DURATION for n in ("scene3", "core_make", "core_keep"))
ai = sum(script.load_scene(n).DURATION for n in ("word_ai", "core_loop"))
assert making >= 30 and ai < 27.0 and making > ai, (making, ai)
assert sum(script.load_scene(n).DURATION for n in script.SCENES) <= 179.5
# 本人の言葉の札は手で作る場面の直前へ戻した。同じ秒だけ他を削ったので、全体は戻す前の 178.9 秒を越えない（本人の決定 11-06）
# 表と裏に分けた後も、word_touch は手で作る場面の直前（前は語りの後。今は「絵は止めて残した」の後）。境目の 3 秒は始まりから取った
assert order.index("flip") + 1 == order.index("word_touch") and order.index("word_touch") + 1 == order.index("scene3")
assert round(sum(script.load_scene(n).DURATION for n in script.SCENES), 1) <= 178.9

# 例の記録は字の頭が「（例）」。人の報告に見せかけない
for key in ("note", "impression", "fix_part", "fix_change", "fix_outcome"):
    assert core.EXAMPLE[key].startswith("（例）"), key
for rec in (core.EXPLAIN, {k: v for k, v in core.NEXT.items() if k not in ("param", "to")}):
    assert all(v.startswith("（例）") for v in rec.values()), rec

# 写真は確かめ表で通った物だけ（demo.scene5 と同じ表）
from demo import scene5  # noqa: E402
assert core.PHOTO.stem in scene5.allowed_photos(), core.PHOTO

# 合図の表は順に並び、場面の長さの中
for name, cues in core.CUES_ALL.items():
    spans = list(cues.values())
    assert spans == sorted(spans) and spans[-1][1] <= core.SECONDS[name], name
    assert script.load_scene(name).DURATION == core.SECONDS[name]

# 偽の画面で 1 コマを描く
fake = {
    "make1": (Image.new("RGB", (2560, 2000), (251, 250, 250)), {"stage": [0, 0, 1280, 900], "h": 1000}, 1280),
    "make2": (Image.new("RGB", (2560, 2000), (249, 250, 250)), {"stage": [0, 0, 1280, 900], "h": 1000}, 1280),
    "make3": (Image.new("RGB", (2560, 2000), (248, 250, 250)), {"stage": [0, 0, 1280, 900], "h": 1000}, 1280),
    "make": (Image.new("RGB", (2560, 2000), (250, 250, 250)), {"stage": [0, 0, 1280, 900], "henji": [700, 200, 500, 400], "h": 1000}, 1280),
    "keep": (Image.new("RGB", (2000, 3000), (245, 245, 245)), {"up": [100, 200, 800, 1200], "record": [120, 900, 760, 300], "h": 1500}, 1000),
    "gallery": (Image.new("RGB", (2800, 2400), (240, 240, 240)), {"made": [100, 100, 1200, 900], "first_made": [100, 700, 1200, 120], "h": 1200}, 1400),
}
for name in core.SECONDS:
    scene = core.build_scene(name, dict(core.CUES_ALL[name]), shots=fake)
    assert scene.duration == core.SECONDS[name]
    d = scene.duration
    for t in (0.0, d * 0.3, d * 0.6, d - 0.05):
        a, b = scene.frame(t), scene.frame(t)
        assert a.size == (flip.W, flip.H) and a.tobytes() == b.tobytes(), (name, t)
    assert scene.frame(0.0).tobytes() != scene.frame(d - 0.05).tobytes(), name
# ギャラリーの字幕は持ち寄りを言う。寄りは持ち寄られた物の列を下へ動く（1 つの記録だけに見せない）
gal = core.build_scene("core_gallery", dict(core.CUES_ALL["core_gallery"]), shots=fake)
# 列は台本が作った本物の作った物の札の下で止まる（見本の畳みは開かない。統括の決め 11-06。前は 1 つ目の見本の下で止めていた）
gal_end = gal.segs[0]["to"]
assert gal_end[1] > gal.segs[0]["from"][1] and gal_end[1] + gal_end[2] * core.ASPECT / 2 <= 700 + 120 + core.SAMPLE_GAP, gal_end
assert gal.segs[0]["line"] == core.GALLERY_LINE and "持ちよ" in core.GALLERY_LINE
assert gal.segs[0]["to"][1] > gal.segs[0]["from"][1]
# 場面 8 は手帖の 1 手 1 画面を順に映し、「こまった」を押した後の聞く画面で止まる（統括の決め 11-06。前は作りながら見る頁）。
# 字は上の 1 行だけで、同じ字が続く段では点滅しない
stepping = core.build_scene("core_make", dict(core.CUES_ALL["core_make"]), shots=fake)
assert [s["shot"] for s in stepping.segs] == ["make1", "make2", "make3", "make"]
assert all("/techo?" in core.PAGES[s["shot"]][0] for s in stepping.segs), "作る場面は手帖だけを映す（作る口は手帖 1 つ）"
assert not any("tsukuru" in v[0] for v in core.PAGES.values()), "作りながら見る頁は撮らない"
assert "data-scene=henji" in core.PAGES["make"][2]["henji"], "聞く画面に替わった時だけ当たる形で測る（押せていない画面を撮らない）"
# 手帖は 1 手 1 画面なので、頁の全体を映したまま送る（寄らない）
assert len({(s["from"], s["to"]) for s in stepping.segs}) == 1 and stepping.segs[0]["from"] == stepping.segs[0]["to"]
at = core.CUES_ALL["core_make"]["step2"]
band = (0, 0, flip.W, core.BOX[1] - 10)
assert stepping.frame(at[0] + 0.05).crop(band).tobytes() == stepping.frame(at[0] - 0.5).crop(band).tobytes()
assert stepping.segs[-1]["line"] == "止まったら、そのまま声か字で聞ける"
# 手帖は上げる欄から、上げた記録へ動く。同じ頁の中なので段の替わり目で絵が変わらない
keeping = core.build_scene("core_keep", dict(core.CUES_ALL["core_keep"]), shots=fake)
assert [s["shot"] for s in keeping.segs] == ["keep", "keep"] and keeping.segs[1]["to"][1] > keeping.segs[1]["from"][1]
# 字幕「工夫した所を記録に添える」の間は、上げた記録の頭から映す（節の下の端を基準にすると、記録の欄が伸びた時に写真が枠の外へ出る）
keep_end = keeping.segs[1]["to"]
assert 900 - 40 <= keep_end[1] - keep_end[2] * core.ASPECT / 2 <= 900, keep_end
mark = core.CUES_ALL["core_keep"]["record"]
# 字幕は下の帯（11-07 の組み直し）で枠の下に重なるので、帯より上の枠の中を比べる
upper = (core.BOX[0], core.BOX[1], core.BOX[2], min(core.BOX[3], words.H - words.BAND_BOTTOM - 260))
assert keeping.frame(mark[0] + 0.05).crop(upper).tobytes() == keeping.frame(mark[0] - 0.1).crop(upper).tobytes()
# 手順が替わる時は、前の画面を頁の地の色へ溶かしてから次の画面を出す（2 つの頁の字を重ねない）
middle = sum(core.CUES_ALL["core_make"]["step2"]) / 2
assert len(stepping.frame(middle).crop(upper).convert("RGB").getcolors(flip.W * flip.H)) <= 2  # 帯より上の枠の中
assert stepping.frame(middle).getpixel((core.BOX[0] + 50, core.BOX[1] + 50)) == core.page_color(fake["make2"][0])
# 写真は確認の記録が無いとギャラリーに出ない（#314）。例の記録に一時の置き場で確認を残す。出なければ止まる（通った振りをしない）
real_post, real_run, real_open = core._post, core.subprocess.run, core.urllib.request.urlopen
answers = {"/print": (303, ""), "/record-json": (201, '{"id": "R-0001"}'), "/media": (201, "m1.jpg"), "/explain": (303, ""), "/next": (303, "")}
core._post = lambda base, path, data, ctype=None: next(v for k, v in answers.items() if path.endswith(k))
ran = []
core.subprocess.run = lambda cmd, **k: ran.append((cmd, k["env"])) or types.SimpleNamespace(returncode=0, stderr="")


class Page:
    def __init__(self, text):
        self.text = text

    def read(self):
        return self.text.encode("utf-8")


core.urllib.request.urlopen = lambda url, timeout=0: Page('<img src="/record/R-0001/media/m1.jpg">')
assert core.seed("http://x", {"OMOCHAE_DATA": "/tmp/一時"}) == "R-0001"
assert ran[0][1]["OMOCHAE_DATA"] == "/tmp/一時" and ran[0][0][-2:] == ["R-0001", "m1.jpg"], ran
core.urllib.request.urlopen = lambda url, timeout=0: Page("写真なし")
try:
    core.seed("http://x", {"OMOCHAE_DATA": "/tmp/一時"})
    raise AssertionError("ギャラリーに写真が出ないのに通った")
except OSError as e:
    assert "ギャラリー" in str(e)
core.urllib.request.urlopen = lambda url, timeout=0: Page('<img src="/record/R-0001/media/m1.jpg">')
core.subprocess.run = lambda cmd, **k: types.SimpleNamespace(returncode=3, stderr="だめ")
try:
    core.seed("http://x", {"OMOCHAE_DATA": "/tmp/一時"})
    raise AssertionError("確認が残らないのに通った")
except OSError as e:
    assert "確認" in str(e)
core._post, core.subprocess.run, core.urllib.request.urlopen = real_post, real_run, real_open
# 頁の頭から映す（題から読ませる）
head = core._cam_page(1280)
assert abs(head[1] - head[2] * core.ASPECT / 2) < 1e-6 and head[0] == 640
# 撮った枠の外は、撮った頁の地の色で埋める（皮の色を書き込まない）
assert core._view(Image.new("RGB", (800, 800), (252, 252, 250)), (200, 200, 1200)).getpixel((0, 0)) == (252, 252, 250)
# 輪の場面: 字は 1 かたまりずつ。「いま作っているところです」の間は、点線の輪が濃くなる
loop = core.build_scene("core_loop", dict(core.CUES_ALL["core_loop"]))
assert loop.chunks[-1] == (words.NOW_LINE,)
last = core.CUES_ALL["core_loop"][f"c{len(loop.chunks) - 1}"][0]
box = (core.RING_XS[0] - core.RING_R - 10, core.LOOP_Y - core.RING_R - 10, core.RING_XS[0] + core.RING_R + 10, core.LOOP_Y + core.RING_R + 10)
assert loop.frame(last - 1.0).crop(box).tobytes() != loop.frame(last + 1.0).crop(box).tobytes()
# 曲の拍へ寄せた表（同じ dict）が、作った場面に効く
mod = script.load_scene("core_map")
assert mod.CUES is script.load_scene("core_map").CUES
print("ok")
