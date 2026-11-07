"""場面 15 の別版（demo.core_loop_ban・型紙の版が変わる絵）と、差し替えの設定（demo.build の --swap）の床。

なぜ: 窓口の決め方（11-07）「デモは版が変わる場面ひとつの別版」「本線の台本は触らない・差し替えの設定で」を、手で見なくても崩れないよう固定する。
見る事:
1. 別版の秒・合図・字幕は core_loop の物そのもの（写した物でなく同じ物）。新しい字幕（EXTRA_LINE）は秒の出所が決まるまで空
2. --swap が無い時の台本の順と場面の作りは今のまま
3. --swap core_loop=core_loop_ban はその場面の作りだけを替える。知らない組・2 度の差し替え・--clip との重なりは 4 で止める
4. 紙の絵が無くても、エンジンの版の表が無くても止まらずに描ける。札は「型紙の版」と数だけで、エンジンの版は表がある時だけ
5. 紙の絵を入れる命令は、当たる紙が 1 枚ずつでない時に 3 で止め、置き場が無い時は 4
"""
import json
import pathlib
import shutil
import tempfile

from demo import build, core, core_loop_ban, script, words
from demo import ban_take_in
from demo.flip import H, W

# 手と声の置き場は空の置き場を見る（test_demo_build と同じ。手元の本物の置き場を読まない）
build.SLOT_DIR = script.SLOT_DIR = tempfile.mkdtemp()

# 1. 秒・合図・字幕は core_loop と同じ物
base = core.scene_module("core_loop")
assert core_loop_ban.CUES is base.CUES, "合図は写さず同じ物を読む（拍合わせが両方に効く）"
assert core_loop_ban.DURATION == base.DURATION == core.SECONDS["core_loop"]
assert core_loop_ban.CHUNKS == words.chunks_of("core_loop")
assert core_loop_ban.NAME == "core_loop"
assert core_loop_ban.EXTRA_LINE == "", "窓口が採った字幕は、秒の出所が決まるまで出さない"
assert [n for _, n in core_loop_ban.VERSIONS] == [10, 11, 12, 13, 14], "御来迎の v10 → v14 だけ（虎はこの場面に入れない）"
assert core_loop_ban.LABEL.format(n=14) == "型紙の版 14" and core_loop_ban.ENGINE_LABEL.format(n=7) == "エンジンの版 7"

# 2. 台本の順は今のまま。既定の差し替えは場面 15 の版の並び（窓口の決定 11-07、084919 の ①）。--swap core_loop=core_loop で前の輪の図に戻る
assert build.SCENES == ["opening", "talk_toys", "talk_lost", "scene2", "flip", "word_touch", "scene3", "core_make", "scene5", "core_keep", "core_gallery",
                        "border", "talk_physics", "talk_claude", "core_loop", "word_ai", "scene7", "close", "ask"]
assert "core_loop_ban" not in build.SCENES and build.parse_swaps([]) == {}
assert build.DEFAULT_SWAPS == {"core_loop": "core_loop_ban"}
for name in build.SCENES:
    assert build.scene_for(name, {}) is script.load_scene(name), name
assert build.scene_for("core_loop", build.parse_swaps(["core_loop=core_loop"])) is script.load_scene("core_loop"), "前の輪の図に戻せる"

# 3. 差し替えはその場面だけ
swaps = build.parse_swaps(["core_loop=core_loop_ban"])
assert swaps == {"core_loop": "core_loop_ban"}
for name in build.SCENES:
    want = core_loop_ban if name == "core_loop" else script.load_scene(name)
    assert build.scene_for(name, swaps) is want, name
for bad in (["core_loop=nope"], ["scene7=core_loop_ban"], ["core_loop"], ["core_loop=core_loop_ban", "core_loop=core_loop_ban"]):
    try:
        build.parse_swaps(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"受けてはいけない差し替えを受けた: {bad}")
out = tempfile.mkdtemp()
for argv in (["--swap", "core_loop=nope"], ["--swap", "word_ai=core_loop_ban"]):
    assert build.main(["--out", out, *argv]) == 4, argv
clip = pathlib.Path(out) / "c.mp4"
clip.write_bytes(b"")
assert build.main(["--out", out, "--swap", "core_loop=core_loop_ban", "--clip", f"core_loop={clip}"]) == 4, "--clip と --swap の両方は止める"
prev = tempfile.mkdtemp()
assert build.main(["--out", out, "--run", prev, "--only", "scene7", "--swap", "core_loop=core_loop_ban"]) == 4, "差し替えた場面を作り直さない時は止める"

# 4. 紙の絵とエンジンの表が無くても描ける
empty = tempfile.mkdtemp()
scene = core_loop_ban.BanCard(core_loop_ban.CUES, folder=empty, engine=pathlib.Path(empty) / "engine.json")
assert scene.sheets == [None] * 5 and scene.engine is None
for t in (0.0, 1.0, 3.0, 5.5, 9.0, scene.duration - 0.01):
    assert scene.frame(t).size == (W, H), t
# 現れる順は版の順。最初は輪の合図の頭、最後は 3 つ目の字幕の頭（字幕「次の型紙を少しずつよくしていきます。」と合わせる）
at = [scene.appear_at(i) for i in range(5)]
assert at == sorted(at) and at[0] == core_loop_ban.CUES["rings"][0] and abs(at[-1] - core_loop_ban.CUES["c2"][0]) < 1e-9
# 紙の絵がある時も描ける（偽の紙 1 枚）
from PIL import Image  # noqa: E402

Image.new("RGB", (1148, 1641), (255, 255, 255)).save(pathlib.Path(empty) / "goraigo-v12.png")
eng = pathlib.Path(empty) / "engine.json"
eng.write_text(json.dumps({"engine_version": 7}), encoding="utf-8")
scene = core_loop_ban.BanCard(core_loop_ban.CUES, folder=empty, engine=eng)
assert scene.sheets[2] is not None and scene.sheets[2].width <= core_loop_ban.SHEET_W and scene.sheets[2].height <= core_loop_ban.SHEET_H
assert scene.engine == 7 and scene.frame(scene.duration - 0.5).size == (W, H)
for bad in ("", "{}", '{"engine_version": 0}', '{"engine_version": "7"}', "[1]"):
    eng.write_text(bad, encoding="utf-8")
    assert core_loop_ban.engine_version(eng) is None, bad

# 5. 紙の絵を入れる命令
assert ban_take_in.main([str(pathlib.Path(empty) / "無い")]) == 4
if shutil.which("pdftoppm"):
    root = pathlib.Path(tempfile.mkdtemp())
    for _, pattern in ban_take_in.SOURCES:
        p = root / pattern.replace("*", "（頭の印）")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"%PDF-1.4\n")
    assert ban_take_in.main([str(root), "--dry-run"]) == 0
    # 同じ版に 2 枚当たると 3（違う紙を黙って映さない）
    twin = root / ban_take_in.SOURCES[-1][1].replace("*", "（別の頭の印）")
    twin.write_bytes(b"%PDF-1.4\n")
    assert ban_take_in.main([str(root), "--dry-run"]) == 3
    twin.unlink()
    (root / ban_take_in.SOURCES[0][1].replace("*", "（頭の印）")).unlink()
    assert ban_take_in.main([str(root), "--dry-run"]) == 3, "当たる紙が無い版があると 3"
# 同じ枠で切る: 描いてある所の少ない紙も同じ大きさのまま
a = Image.new("RGB", (400, 600), (255, 255, 255))
b = a.copy()
a.paste((0, 0, 0), (40, 50, 360, 560))
b.paste((0, 0, 0), (100, 100, 200, 200))
box = ban_take_in.union([ban_take_in.drawn_box(a), ban_take_in.drawn_box(b)])
assert ban_take_in.cut(a, box).size == ban_take_in.cut(b, box).size
assert ban_take_in.drawn_box(Image.new("RGB", (10, 10), (255, 255, 255))) is None
print("ok: 別版は core_loop の秒と字のまま、差し替えの設定でだけ入れ替わる")
