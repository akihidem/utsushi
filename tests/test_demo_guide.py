"""デモの小さな案内役（demo.guide）の床。本人の決定 11-06: 「デモ動画に、小さな小人の案内役を足す。北斎漫画のアニメ化で。」・候補 B。

見る事: 出る場面は 4 つだけ（本人の言葉の札・締め・問い・始まり・語りには出ない）／秒を足さない／出所と改変は figures.json に残る（PDM）／
前の日の取り寄せ（demo.prepare）に頁が入る／1 コマは時刻だけで決まる／本物の画面の場面では、画面の右の余白に立って画面を隠さない／
クレジットの字は今のまま。網を使わないよう、頁の代わりに作り物の絵で見る。
"""
import pathlib
import tempfile

from PIL import Image, ImageDraw

from demo import flip, guide, prepare, scene7, script, words

# 出る場面
assert set(guide.PLANS) == {"scene3", "core_make", "border", "core_loop"}
assert set(guide.PLANS) <= set(script.SCENES)
for name in (*words.CARDS, "close", "ask", "opening", "talk_toys", "talk_lost", "talk_physics", "talk_claude", "scene2"):
    assert name not in guide.PLANS, name
# 秒は足さない
assert round(sum(script.load_scene(n).DURATION for n in script.SCENES), 1) == 178.9
for name, plan in guide.PLANS.items():
    (t0, _), (t1, _) = plan["walk"]
    assert 0 <= t0 < t1 <= script.load_scene(name).DURATION, name
# 出所と改変（PDM）
rec = guide.record()
assert rec["rights"] == "PDM" and rec["iiif"].startswith("https://dl.ndl.go.jp/api/iiif/851646/") and "国立国会図書館" in rec["attribution"]
assert "描き直していない" in rec["modification_note"] and any(f["id"] == guide.FIG for f in rec["figures"])
# 前の日の取り寄せに入る（撮る日は網を切って書き出すため）
with tempfile.TemporaryDirectory() as tmp:
    rows = prepare.wanted(pathlib.Path(tmp) / "cache", pathlib.Path(tmp) / "sources")
    assert any(r["label"] == f"cache/{guide.PAGE}.jpg" and r["url"] == guide.page_url() for r in rows)
# クレジットの字は今のまま（本人の決定 11-06: 「図の手入れ」の行に 1 句は足さない）
assert dict(scene7.CREDITS)["図の手入れ"] == "切り出し、重ね、墨一色。線は描き直していない"

# 作り物の頁で切り出しと重ね方を見る: 枠の中に墨の人を描き、種の点から拾えるか
page = Image.new("L", (3543, 3014), 255)
d = ImageDraw.Draw(page)
fig = next(f for f in rec["figures"] if f["id"] == guide.FIG)
x, y, w, h = fig["box_pct"]
bx, by, bw, bh = x / 100 * 3543, y / 100 * 3014, w / 100 * 3543, h / 100 * 3014
d.rectangle((bx + bw * 0.3, by + bh * 0.05, bx + bw * 0.6, by + bh * 0.98), fill=20)  # 体（種の点が当たる所）
d.rectangle((bx + bw * 0.9, by, bx + bw, by + bh * 0.2), fill=20)                    # 離れた所の線（隣の人の代わり。拾わない）
cut = guide.cut(page, fig)
assert cut.mode == "RGBA" and cut.height > cut.width
key = "作り物"
guide._CUT[key] = cut
real_figure = guide.figure
guide.figure = lambda cache: guide._CUT[str(cache)]
try:
    base = Image.new("RGB", (flip.W, flip.H), flip.PAPER)
    for name, plan in guide.PLANS.items():
        (t0, _), (t1, _) = plan["walk"]
        assert guide.overlay(base, name, t0 - 0.05, key).tobytes() == base.tobytes(), (name, "出る前は重ねない")
        a, b = guide.overlay(base, name, t1 + 0.2, key), guide.overlay(base, name, t1 + 0.2, key)
        assert a.tobytes() == b.tobytes() and a.tobytes() != base.tobytes(), (name, "時刻だけで決まり、出ている")
        bb = Image.eval(a.convert("L"), lambda v: 255 if v < 200 else 0).getbbox()
        assert bb and bb[0] >= 0 and bb[2] <= flip.W and bb[3] <= flip.H, (name, bb)
        if name in ("scene3", "core_make"):
            assert bb[0] >= 1760, (name, "本物の画面の右の余白に立つ（画面を隠さない）", bb)
        if name == "core_loop":
            assert bb[3] <= words.BANDS["bottom"][0], (name, "数の行の帯の上を歩く", bb)
    # 歩く間は揺れて動き、止まった後は動かない
    (t0, _), (t1, _) = guide.PLANS["border"]["walk"]
    mid = (t0 + t1) / 2
    assert guide.overlay(base, "border", mid, key).tobytes() != guide.overlay(base, "border", mid + 0.2, key).tobytes()
    late = guide.PLANS["border"]["tilt"][0] + 0.7
    assert guide.overlay(base, "border", late, key).tobytes() == guide.overlay(base, "border", late + 0.3, key).tobytes()
    # 書き出しの口: 案内役の出る場面の名前なら包み、ほかの名前はそのまま
    card = words.ChunkCard("border", words.cues_of("border"))
    real_root = flip.ROOT
    # 書き出しの通り道は、どの場面も後入れの札の包み（demo.later）を重ね、案内役の出る場面だけ案内役を重ねる
    from demo import later

    assert isinstance(flip.guided(card, "border").scene, guide.Guided) and flip.guided(card, "word_ai").scene is card
    assert isinstance(flip.guided(card, "word_ai"), later.Later) and flip.guided(flip.guided(card, "border"), "border").scene.scene is card, "2 度重ねない"
    wrapped = guide.Guided(card, "border", key)
    assert wrapped.duration == card.duration and getattr(wrapped, "ground", flip.PAPER) == getattr(card, "ground", flip.PAPER)
finally:
    guide.figure = real_figure
    guide._CUT.pop(key, None)
print("ok 案内役は 4 場面にだけ、秒を足さず、出所つきで、画面を隠さずに重なる")
