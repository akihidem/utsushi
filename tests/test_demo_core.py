"""核の一周（demo.core）の床: まだ無い物を動いているように見せない事、例の記録が例と分かる事、1 コマが時刻だけで決まる事を見る。

Chrome も網も使わない。画面の絵は偽物を渡す。画面を撮る所は書き出しの時に通り、そこで本物の口を通らなければ止まる。
"""
from PIL import Image

from demo import core, flip, script

# 真ん中に置く: 3 段と輪が、言葉の札の間にある
order = script.SCENES
assert order.index("word_touch") < order.index("core_map") < order.index("scene3") < order.index("core_make") < order.index("core_keep") \
    < order.index("scene5") < order.index("scene6") < order.index("core_gallery") < order.index("core_loop") < order.index("word_ai") < order.index("ask")
# つなぎ 2 は持ち寄りの場面の次（本人の決定 11-05）。手で作る → 持ち寄り → AI は後、の順
assert order.index("core_loop") == order.index("core_gallery") + 1

# まだ無い物の場面は図と書き、これから作ると書く。画面として撮らない
assert core.SOON == "これから作る"
assert "これから" in core.VOICE_LINE
# つなぎ 2 は本人が決めた字のまま。AI はまだ動いていないので「いま作っているところです」を一緒に出す
assert "".join(core.BRIDGE2) == "作ったものを持ちよると、AI もそれを見て、次の型紙を少しずつよくしていきます。"
assert core.NOW_LINE == "いま作っているところです" and core.NOW_MAKING == "いま作っているところ"
# 図は本人のループの定義（11-05 17:57）の 4 本。今動いていない所は点線で、いま作っているところと分かる
assert [name for name, _, _ in core.LOOPS] == ["ループ 1", "ループ 2", "ループ 3", "ループ 4"]
flat = lambda lines: "".join(lines)
now = {flat(lines) for _, _, results in core.LOOPS for lines, making in results if making}
assert now == {"反応して型紙が生まれる", "エンジンごと直る", "システムも直る"}, now
done = {flat(lines) for _, _, results in core.LOOPS for lines, making in results if not making}
assert done == {"型紙が直る", "ギャラリーで見られる", "型紙も直る"}, done
assert [flat(top)[0] for _, top, _ in core.LOOPS] == ["①", "②", "そ", "③"]
assert "本物の Claude API は、まだ 1 度も動かしていません" in core.AI_NOTE
assert "これから" in core.build_scene("core_make", dict(core.CUES_ALL["core_make"]), shots={
    "make": (Image.new("RGB", (2560, 2000), (250, 250, 250)), {"stage": [0, 0, 1280, 900], "henji": [700, 200, 500, 400], "h": 1000}, 1280)}).note
for name in ("core_map", "core_voice", "core_loop"):
    assert not isinstance(core.build_scene(name, dict(core.CUES_ALL[name])), core.Screens), name

# 例の記録は字の頭が「（例）」。人の報告に見せかけない
for key in ("note", "impression", "fix_part", "fix_change", "fix_outcome"):
    assert core.EXAMPLE[key].startswith("（例）"), key
for rec in (core.EXPLAIN, {k: v for k, v in core.NEXT.items() if k not in ("param", "to")}):
    assert all(v.startswith("（例）") for v in rec.values()), rec
assert "作り物" in core.EXAMPLE_NOTE

# 写真は確かめ表で通った物だけ（demo.scene5 と同じ表）
from demo import scene5  # noqa: E402
assert core.PHOTO.stem in scene5.allowed_photos(), core.PHOTO

# 合図の表は順に並び、場面の長さの中
for name, cues in core.CUES_ALL.items():
    spans = list(cues.values())
    assert spans == sorted(spans) and spans[-1][1] <= core.SECONDS[name], name
    assert script.load_scene(name).DURATION == core.SECONDS[name]

# 地図の真ん中は手で作る所。AI の字を置かない（本人の言葉 11-05 夕: AI が良くなるのは副次的で、手で作る楽しさに気づく事が最初）
assert "手で作る" in core.MAP_TITLE
for s in (core.MAP_TITLE, core.MAP_SUB, core.VOICE_LINE, *(s for _, top, results in core.LOOPS for s in (*top, *(x for lines, _ in results for x in lines)))):
    assert "AI" not in s, s
the_map = core.build_scene("core_map", dict(core.CUES_ALL["core_map"]))
drawn = the_map.frame(8.9).tobytes()
real_bridge, real_note = core.BRIDGE2, core.AI_NOTE
core.BRIDGE2, core.AI_NOTE = ("別の字", "別の字"), "別の字"
assert the_map.frame(8.9).tobytes() == drawn, "地図が AI の字を読まない"
core.BRIDGE2, core.AI_NOTE = real_bridge, real_note

# 手で作る所を長く。作る場面（scene3・core_make・core_keep）は前の 31 秒より長く、AI の場面（word_ai・core_loop）は前の 22 秒より短い。全体は 3 分以内
making = sum(script.load_scene(n).DURATION for n in ("scene3", "core_make", "core_keep"))
ai = sum(script.load_scene(n).DURATION for n in ("word_ai", "core_loop"))
assert making > 31 and ai < 22 and making > ai, (making, ai)
assert sum(script.load_scene(n).DURATION for n in script.SCENES) <= 180

# 偽の画面で 1 コマを描く
fake = {
    "make1": (Image.new("RGB", (2560, 2000), (251, 250, 250)), {"stage": [0, 0, 1280, 900], "h": 1000}, 1280),
    "make2": (Image.new("RGB", (2560, 2000), (249, 250, 250)), {"stage": [0, 0, 1280, 900], "h": 1000}, 1280),
    "make": (Image.new("RGB", (2560, 2000), (250, 250, 250)), {"stage": [0, 0, 1280, 900], "henji": [700, 200, 500, 400], "h": 1000}, 1280),
    "keep": (Image.new("RGB", (2000, 3000), (245, 245, 245)), {"up": [100, 200, 800, 1200], "h": 1500}, 1000),
    "gallery": (Image.new("RGB", (2800, 2400), (240, 240, 240)), {"made": [100, 100, 1200, 900], "h": 1200}, 1400),
}
for name in core.SECONDS:
    scene = core.build_scene(name, dict(core.CUES_ALL[name]), shots=fake)
    assert scene.duration == core.SECONDS[name]
    d = scene.duration
    for t in (0.0, d * 0.3, d * 0.6, d - 0.05):
        a, b = scene.frame(t), scene.frame(t)
        assert a.size == (flip.W, flip.H) and a.tobytes() == b.tobytes(), (name, t)
    assert scene.frame(0.0).tobytes() != scene.frame(d - 0.05).tobytes(), name
# ギャラリーの字幕は、作った物が持ち寄られる事を言う。寄りは持ち寄られた物の列を下へ動く（1 つの記録だけに見せない）
gal = core.build_scene("core_gallery", dict(core.CUES_ALL["core_gallery"]), shots=fake)
assert "持ち寄られ" in gal.segs[0]["sub"] and "ギャラリー" in gal.segs[0]["sub"]
assert gal.segs[0]["to"][1] > gal.segs[0]["from"][1]
# 作りながら見る頁は手順を順に映す。同じ字幕が続く段で、字と枠が点滅しない
stepping = core.build_scene("core_make", dict(core.CUES_ALL["core_make"]), shots=fake)
assert [s["shot"] for s in stepping.segs] == ["make1", "make2", "make"]
at = core.CUES_ALL["core_make"]["step2"]
title_box = (80, 62, 900, 180)
assert stepping.frame(at[0] + 0.05).crop(title_box).tobytes() == stepping.frame(at[0] - 0.5).crop(title_box).tobytes()
# 手帖は上げる欄から、上げた記録へ動く。同じ頁の中なので段の替わり目で絵が変わらない
keeping = core.build_scene("core_keep", dict(core.CUES_ALL["core_keep"]), shots=fake)
assert [s["shot"] for s in keeping.segs] == ["keep", "keep"] and keeping.segs[1]["to"][1] > keeping.segs[1]["from"][1]
mark = core.CUES_ALL["core_keep"]["record"]
box_only = core.BOX
assert keeping.frame(mark[0] + 0.05).crop(box_only).tobytes() == keeping.frame(mark[0] - 0.1).crop(box_only).tobytes()
# 上げた記録の所は例の記録が映るので、隅の札で作り物と言う
assert keeping.segs[1]["note"] == core.EXAMPLE_NOTE
# 聞く口の答えが AI のものに見えないように書く（本物の API は未実行）
make = core.build_scene("core_make", dict(core.CUES_ALL["core_make"]), shots=fake)
assert "AI の答えは、まだ動かしていません" in make.segs[0].get("note", make.note)
# 頁の頭から映す（題から読ませる）
head = core._cam_page(1280)
assert abs(head[1] - head[2] * core.ASPECT / 2) < 1e-6 and head[0] == 640
# 撮った枠の外は、撮った頁の地の色で埋める（皮の色を書き込まない）
assert core._view(Image.new("RGB", (800, 800), (252, 252, 250)), (200, 200, 1200)).getpixel((0, 0)) == (252, 252, 250)
# 曲の拍へ寄せた表（同じ dict）が、作った場面に効く
mod = script.load_scene("core_map")
assert mod.CUES is script.load_scene("core_map").CUES
print("ok")
