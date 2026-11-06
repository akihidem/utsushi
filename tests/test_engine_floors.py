"""同じ名前の床が paper-to-toy と同じ意味を持つ（#164）。

なぜ: `src/omochae/` は 2 つの repo にあり、別々に直されていた。F2.bom は部品表だけを見るので虎の首の形の部品 5 が表に無くても通り、
F1.marks は短い語が残れば本文が欠けても通り、F5.image_box は幅 0 の線で見るので糊代を横切る線を拾えなかった。
正は paper-to-toy なので、あちらの床をこちらへ入れる。入れた床は全部の仮説で通らなければ、提出の紙が刷れなくなる。

条件を 1 つずつ回して全部の結果を出す。assert を並べると、直す前は最初の 1 つで止まり、ほかの条件が落ちる事を確かめられない。
"""
import json
import pathlib
import sys
import tempfile

from omochae import floors
from omochae.compose import TEMPLATES, compose
from omochae.fan_model import shortest_free_thread
from omochae.marks import FROZEN_SETS, OWN_HYPOTHESIS, check_pdf
from omochae.model import Failure, Part
from omochae.render import write_all
from omochae.templates import pivot_counterweight as pc
from omochae.templates import slider_fan as sf

ROOT = pathlib.Path(__file__).resolve().parents[1]
GORAIGO = "NDL-1187053-R0000005-L"
SQUARE = [(0, 0), (40, 0), (40, 20), (0, 20)]
GLUE = [[(30, 0), (40, 0), (40, 20), (30, 20)]]


def source(sid=GORAIGO):
    return json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))


def floor_names(fails):
    return sorted({f.floor for f in fails})


def art(item):
    return floors.check_art([Part(1, "t", "試し", SQUARE, glue=GLUE, art=[item])])


def hypotheses():
    """型紙にできる仮説を全部。(出典, 仮説の番号, 雛形の ID, 寸法)。"""
    for f in sorted((ROOT / "data/hypotheses").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for h in d["hypotheses"]:
            if h.get("params") is not None and h.get("template_id", "") is not None:
                t = h.get("template") or d.get("template", "slider_fan")
                yield f.stem, h["id"], t, {**TEMPLATES[t].DEFAULTS, **h["params"]}


def bom_neck_arm():
    neck = {**pc.DEFAULTS, "mount": "neck"}
    assert floors.check_bom(pc.bom(neck), pc.parts(neck)) == []
    # 表から行を消す・別の物を指す・番号が重なる、のどれも落ちる
    short = [r for r in pc.bom(neck) if r["number"] != 5]
    assert floor_names(floors.check_bom(short, pc.parts(neck))) == ["F2.bom"]
    other = [dict(r, key="other", name="別の物") if r["number"] == 5 else r for r in pc.bom(neck)]
    assert floor_names(floors.check_bom(other, pc.parts(neck))) == ["F2.bom"]
    twice = pc.bom(neck) + [dict(pc.bom(neck)[0])]
    assert floor_names(floors.check_bom(twice, pc.parts(neck))) == ["F2.bom"]
    # 行を足しても、紙に刷る「用意する物」は竹串と粘土のまま（行の位置で引くと別の行を刷る）。道具の行は首の形だけカッターが付く（次の組、#294）
    assert pc.materials(neck)[2:] == pc.materials({**neck, "mount": "hang"})[2:]


def bom_through_compose():
    # 部品の照合が compose につながっている。floors.check_bom を直に呼ぶだけでは、compose が部品を渡さなくなっても通ってしまう
    tiger = source("NDL-1187053-R0000014-R")
    assert "F2.bom" not in floor_names(compose(pc.ID, {"mount": "neck"}, tiger)[2])
    orig = pc.bom
    pc.bom = lambda p: [r for r in orig(p) if r["number"] != 5]
    try:
        fails = compose(pc.ID, {"mount": "neck"}, tiger)[2]
    finally:
        pc.bom = orig
    assert "F2.bom" in floor_names(fails), [f.line() for f in fails]


def bom_every_hypothesis():
    bad = []
    for sid, hid, t, p in hypotheses():
        tpl = TEMPLATES[t]
        bad += [f"{sid}/{hid} {f.line()}" for f in floors.check_bom(tpl.bom(p), tpl.parts(p))]
    assert not bad, f"{len(bad)} 件。先頭: {bad[:3]}"


def bom_forms_without_hypothesis():
    # 仮説に今は無い形も、寸法を変えれば刷れるので落ちない
    tpl = TEMPLATES["wheel_cart"]
    for body in ("cart", "bale"):
        for drive in ("pull", "slope"):
            p = {**tpl.DEFAULTS, "body": body, "drive": drive}
            assert floors.check_bom(tpl.bom(p), tpl.parts(p)) == [], (body, drive)


def marks_whole_text():
    src = source()
    with tempfile.TemporaryDirectory() as d:
        _, layout, fails = compose("slider_fan", {"push_part": "tab"}, src)
        assert not fails
        pdf = write_all(layout, pathlib.Path(d) / "m")
        assert check_pdf(pdf, src) == []
        # 短い語（「改変」「仮説」）は紙に残っていても、刷るはずの文が無ければ落ちる
        other = {**src, "holding": src["holding"] + "（別の文）", "modification_note": "改変: 別の注記"}
        assert sorted(f.where for f in check_pdf(pdf, other)) == ["所蔵の文", "改変"]
        # 自分の仮説の紙は、自分の仮説の文を探す。AI の文の紙を「自分で立てた」と読まない
        assert [f.where for f in check_pdf(pdf, {**src, "hypothesis_mark": OWN_HYPOTHESIS})] == ["仮説"]
        own = {**src, "hypothesis_mark": OWN_HYPOTHESIS}
        _, layout, fails = compose("slider_fan", {"push_part": "tab"}, own)
        assert not fails
        assert check_pdf(write_all(layout, pathlib.Path(d) / "own"), own) == []
        # 必須 2 種の今の組は凍結の文、ほかの玩具は新しい文を刷る。どちらの紙でも、刷った文を探す
        sid, _, t, p = next(h for h in hypotheses() if h[0] not in FROZEN_SETS)
        other = source(sid)
        _, layout, fails = compose(t, p, other)
        assert not fails, [f.line() for f in fails]
        assert check_pdf(write_all(layout, pathlib.Path(d) / "other"), other) == []


def image_box_line_across_glue():
    assert floor_names(art({"kind": "line", "pts": [(5, 10), (38, 10)], "stroke": "#000", "sw": 0.3})) == ["F5.image_box"]
    assert art({"kind": "line", "pts": [(5, 10), (25, 10)], "stroke": "#000", "sw": 0.3}) == []


def image_box_printed_width():
    # 中心線は糊代の手前でも、刷られる太さで糊代にかかれば落とす
    assert floor_names(art({"kind": "line", "pts": [(29.5, 2), (29.5, 18)], "stroke": "#000", "sw": 2.0})) == ["F5.image_box"]
    assert art({"kind": "line", "pts": [(29.5, 2), (29.5, 18)], "stroke": "#000", "sw": 0.3}) == []
    # 輪郭線つきの面は、線の太さのぶん外へ広がって刷られる
    framed = {"kind": "poly", "pts": [(5, 5), (29.5, 5), (29.5, 15), (5, 15)], "fill": "#ccc", "stroke": "#000", "sw": 2.0}
    assert floor_names(art(framed)) == ["F5.image_box"]
    # 折れ曲がる線は、SVG と同じく尖った角の先まで見る
    assert floor_names(art({"kind": "line", "pts": [(10, 4), (28.0, 10), (10, 16)], "stroke": "#000", "sw": 1.5})) == ["F5.image_box"]


def image_box_fold_at_printed_width():
    # 折り線も刷られる太さで見る。中心線は届かなくても、帯が折り線にかかれば落とす
    def on_fold(sw):
        item = {"kind": "line", "pts": [(19.5, 2), (19.5, 18)], "stroke": "#000", "sw": sw}
        return floors.check_art([Part(1, "t", "試し", SQUARE, valley=[((20, 0), (20, 20))], art=[item])])

    assert floor_names(on_fold(2.0)) == ["F5.image_box"]
    assert on_fold(0.3) == []


def stand_figure_small_heights():
    # 絵の高さは範囲の下の端まで許す。輪郭線の太さは縮尺で細らないので、小さい絵でも帯の線が折り線と糊代にかからない事を見る
    tpl = TEMPLATES["stand_figure"]
    low = tpl.RANGES["fig_h"][0]
    bad = []
    for motif in tpl.MOTIFS:
        for fig_h in (low, 33):
            bad += [f"{motif} {fig_h} {f.line()}" for f in compose(tpl.ID, {"motif": motif, "fig_h": fig_h}, source())[2] if f.floor == "F5.image_box"]
    assert not bad, f"{len(bad)} 件。先頭: {bad[:3]}"


def fan_leg():
    low = {"push_part": "tab", "pivot_above_rim": 0, "fold_count": 6, "fold_width": 5, "fold_height": 40}
    _, _, fails = compose("slider_fan", low, source())
    assert "F5.fan_leg" in floor_names(fails), [f.line() for f in fails]
    # 足が糊代より短い時は足の絵を描かない（描くと形が裏返る）。板の色の 6 枚だけになる
    fan = next(q for q in sf.parts({**sf.DEFAULTS, **low}) if q.key == "fan")
    assert len(fan.art) == 6


def figure_base():
    _, _, fails = compose("slider_fan", {"push_part": "tab", "figure_w": 30, "base_side": 10}, source())
    assert floor_names(fails) == ["F5.figure_base"], [f.line() for f in fails]
    # 検査と刷る足の幅が同じ値を使う
    figure = next(q for q in sf.parts(sf.DEFAULTS) if q.key == "figure")
    assert figure.glue[0][0][0] == sf.DEFAULTS["figure_w"] * sf.FOOT[0]


def hole_every_template():
    # 御来迎だけでなく、どの雛形の部品の穴も見る。床の名は F5.hole の 1 つにする
    out = Part(1, "t", "試し", SQUARE, holes=[(38, 10, 5)])
    assert floor_names(floors.check_holes([out])) == ["F5.hole"]
    assert floors.check_holes([Part(1, "t", "試し", SQUARE, holes=[(20, 10, 5)])]) == []
    low = {"push_part": "tab", "fold_count": 6, "fold_width": 5, "fold_height": 20, "figure_h": 15, "pivot_above_rim": 21}
    _, _, fails = compose("slider_fan", low, source())
    assert floor_names(fails) == ["F5.hole"], [f.line() for f in fails]


def thread_from_hole():
    # 開く糸は筒の穴から結ぶので、穴から測る。口から測ると最大で約 3mm ずれた
    p = {**sf.DEFAULTS, "push_part": "tab", "tube_side": 26, "pusher_side": 22, "base_side": 22, "pivot_above_rim": 2, "push_amount": 69, "fold_height": 38, "fold_count": 10}
    tube = next(q for q in sf.parts(p) if q.key == "tube")
    assert tube.holes[0][1] == sf.THREAD_DEPTH
    z0 = p["pivot_above_rim"] + sf.THREAD_DEPTH
    assert abs(sf.thread_mm(p) - shortest_free_thread(p["tube_side"], sf.THREAD_RADIUS, z0 - p["push_amount"], z0)) < 1e-9
    assert abs(sf.thread_mm(p) - 30.3) < 0.1, sf.thread_mm(p)


def next_reasons_no_new_words():
    # 入れた床の文は学ぶ人にまだ見せない（利用者に見せる新しい文は本人の確認の後）。前からある「近い値を試す」の 1 行だけを出す
    from web.toy import next_reasons

    for floor in ("F5.fan_leg", "F5.figure_base", "F5.hole"):
        out = next_reasons([Failure(floor, "蛇腹の扇", "検査の文")], GORAIGO, "H-A", "pivot_above_rim")
        assert not any("検査の文" in line for line in out) and any("近い値を試す" in line for line in out), (floor, out)


CASES = (bom_neck_arm, bom_through_compose, bom_every_hypothesis, bom_forms_without_hypothesis, marks_whole_text, image_box_line_across_glue,
         image_box_printed_width, image_box_fold_at_printed_width, stand_figure_small_heights, fan_leg, figure_base, hole_every_template,
         thread_from_hole, next_reasons_no_new_words)


def main():
    bad = 0
    for case in CASES:
        try:
            case()
            print(f"ok   {case.__name__}")
        except Exception as e:  # 直す前は新しい名前が無く AttributeError や TypeError にもなる。どれも「まだ」として数える
            bad += 1
            print(f"FAIL {case.__name__}: {type(e).__name__}: {str(e)[:300]}")
    # 数を斜線で並べる形は、年の無い日付と読まれて push の門で落ちる
    print(f"{len(CASES)} 条件のうち {len(CASES) - bad} が通った")
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
