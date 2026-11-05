"""核の一周（demo.core）の床: まだ無い物を動いているように見せない事、例の記録が例と分かる事、1 コマが時刻だけで決まる事を見る。

Chrome も網も使わない。画面の絵は偽物を渡す。画面を撮る所は書き出しの時に通り、そこで本物の口を通らなければ止まる。
"""
from PIL import Image

from demo import core, flip, script

# 真ん中に置く: 3 段と輪が、言葉の札の間にある
order = script.SCENES
assert order.index("word_touch") < order.index("core_map") < order.index("scene3") < order.index("core_make") < order.index("core_keep") \
    < order.index("scene5") < order.index("core_gallery") < order.index("word_ai") < order.index("core_loop") < order.index("ask")

# まだ無い物の場面は図と書き、これから作ると書く。画面として撮らない
assert core.SOON == "これから作る"
assert "これから" in core.VOICE_LINE
# AI が動きを強める輪は図のままで、作っている途中と書く。本物の API はまだ動かしていないので、そう書く
assert "作っている途中" in core.LOOP_OUTER and "AI" in core.LOOP_OUTER
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

# 偽の画面で 1 コマを描く
fake = {
    "make": (Image.new("RGB", (2560, 2000), (250, 250, 250)), {"stage": [0, 0, 1280, 900], "henji": [700, 200, 500, 400], "h": 1000}, 1280),
    "keep": (Image.new("RGB", (2000, 3000), (245, 245, 245)), {"up": [100, 900, 800, 500], "h": 1500}, 1000),
    "gallery": (Image.new("RGB", (2800, 2400), (240, 240, 240)), {"made": [100, 100, 1200, 900], "h": 1200}, 1400),
    "toy": (Image.new("RGB", (2800, 6000), (235, 235, 235)), {"kaizen": [100, 2000, 1200, 500], "minna": [100, 1400, 1200, 500], "h": 3000}, 1400),
}
for name in core.SECONDS:
    scene = core.build_scene(name, dict(core.CUES_ALL[name]), shots=fake)
    assert scene.duration == core.SECONDS[name]
    d = scene.duration
    for t in (0.0, d * 0.3, d * 0.6, d - 0.05):
        a, b = scene.frame(t), scene.frame(t)
        assert a.size == (flip.W, flip.H) and a.tobytes() == b.tobytes(), (name, t)
    assert scene.frame(0.0).tobytes() != scene.frame(d - 0.05).tobytes(), name
# 画面の場面は 2 段目で別の頁に替わる
gal = core.build_scene("core_gallery", dict(core.CUES_ALL["core_gallery"]), shots=fake)
assert gal.frame(3.0).tobytes() != gal.frame(gal.duration - 1.0).tobytes()
# ギャラリーの字幕は、作った物が持ち寄られる事を言う。寄りは持ち寄られた物の列を下へ動く（1 つの記録だけに見せない）
assert "持ち寄られ" in gal.segs[0]["sub"] and "ギャラリー" in gal.segs[0]["sub"]
assert gal.segs[0]["to"][1] > gal.segs[0]["from"][1]
assert "持ち寄" in core.GALLERY_LINE and "今ある" in core.GALLERY_LINE
# 次の版を決めるのは人。「どれを使うか」と選ばせる形にしない（本人の決定 11-05 17:26: 型紙はおもちゃ一個につき一個）
assert gal.segs[1]["sub"].endswith("決めるのは人") and "どれ" not in gal.segs[1]["sub"]
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
