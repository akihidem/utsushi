"""刷った面の向き（本人の答え 2026-11-06「色がついている所が外を向くよう折った」と、決定「今のうちに直す」）。

型紙の折り線のとおりに折ると、絵のある面が見える側に来るかを、部品ごとに 3D の机（assembly.Bench）で見る。谷は刷った面がへこむ向き。
線を刷らない部品（色の境で折る）でも、線の種類は検査と 3D の組み立てが読むので、手順の文と同じ向きでなければならない。
形は、玩具の記録の案を全部と、雛形の選びの組を全部見る。必須 2 種（slider_fan・pivot_counterweight）は次の版の紙で直すので見ない。
見ない部品と理由:
- 絵の無い糊代だけを折る線（乗り手と表裏の下の糊代、支えの糊代、幟の糊代、絵の無い吊り橋）。板の表は、背中合わせに貼るか 1 枚で立てて外に出る
- 折らない部品（蓋、月、刀身など）
"""
import collections
import json
import math
import os
import pathlib
import tempfile

os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp())

from shapely.geometry import Polygon

from omochae import assembly
from omochae.templates import stand_figure, stick_prop, wheel_cart

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOOK = {}  # 雛形の ID → (雛形, 部品を見る関数, 選びの組)
WANT = set()  # 1 度は見るはずの (雛形, 部品)
seen = set()
bad = collections.Counter()


def bench(q, deg):
    b = assembly.Bench([q])
    b.fold(q.key, deg=deg)
    return b, b.sheets[q.key]


def colored(sheet):
    """絵のある面の番号。糊代だけの面（絵が無い）は見ない。"""
    art = [Polygon(a["pts"]).buffer(0) for a in sheet.part.art if a["kind"] == "poly"]
    return [i for i, s in enumerate(sheet.panels) if any(g.intersection(s).area > 0.5 for g in art)]


def middle(b, key):
    """折った形の真ん中（面の重心を面積で重みにした点）。"""
    sheet = b.sheets[key]
    pts = [(assembly.apply(b.world(key, i), (s.centroid.x, s.centroid.y)), s.area) for i, s in enumerate(sheet.panels)]
    total = sum(a for _, a in pts)
    return tuple(sum(c[k] * a for c, a in pts) / total for k in range(3))


def outward(q, deg):
    """閉じる形と 2 つ折りで貼る形。絵のある面が、折った形の真ん中から外を向くか。Returns 内を向いた面。閉じ切る手前の角で見る。"""
    b, sheet = bench(q, deg)
    faces = colored(sheet)
    assert faces, q.key
    return b.faces_out(q.key, faces, middle(b, q.key))


def leaning(q, at=None, want=-1, only_colored=False):
    """面 at（無ければ一番広い面）を動かさずに折り、ほかの面が刷った面の裏（want=-1）か表（want=+1）へ折れるか。Returns 向きの違う面。

    見る面を根にする。歯のように 1 本の線を何枚も分け合う所では、根が歯だと、隣の歯が根の歯のまわりで折れてしまうため。"""
    if at is None:
        big = max(assembly.Sheet(q).panels, key=lambda s: s.area).representative_point()
        at = (big.x, big.y)
    b = assembly.Bench([q], roots={q.key: at})
    b.fold(q.key, deg=90.0)
    sheet = b.sheets[q.key]
    others = [i for i in (colored(sheet) if only_colored else range(len(sheet.panels))) if i != sheet.root]
    assert others, q.key
    out = []
    for i in others:
        c = sheet.panels[i].centroid
        if assembly.apply(b.world(q.key, i), (c.x, c.y))[2] * want <= 0:
            out.append(i)
    return out


def wrong(tid, q, why, faces):
    seen.add((tid, q.key.rstrip("0123456789")))
    if faces:
        bad[f"{tid} {q.name}（{q.key}）: {why}"] += 1


# --- wheel_cart: 線 cart の車と俵。今の向きのままで合う（見張り） ---

def look_wheel_cart(p):
    for q in wheel_cart.parts(p):
        if q.key == "deck":
            # 台は縁を下へ折った浅い箱。板と 4 つの縁の刷った面が箱の外（手順「絵を外にして下へ折る」）
            wrong("wheel_cart", q, "色の面が箱の内を向く", outward(q, 90.0))
        elif q.key.startswith("wheel"):
            # 車は 2 枚の円を橋で折って貼り合わせる。刷った面が両側の外
            wrong("wheel_cart", q, "色の面が貼り合わせる側を向く", outward(q, 170.0))
        elif q.key == "tube":
            # 俵の筒は絵を外にして丸める（折り線は無い）。上下の歯は刷った面の裏（筒の中）へ折り、蓋を外から貼る
            at = (math.pi * p["bale_d"] / 2, wheel_cart.TAB + p["bale_length"] / 2)
            wrong("wheel_cart", q, "歯が絵の側（筒の外）へ折れる", leaning(q, at))
        elif q.key == "ramp":
            # 坂の溝は上が開いた樋。縁を刷った面の側へ起こすと、刷った面が溝の内になり上から見える
            at = (p["ramp_length"] / 2, p["rail"] + wheel_cart.ramp_inner(p) / 2)
            wrong("wheel_cart", q, "縁が刷った面の裏へ折れ、溝の内の色が上から見えない", leaning(q, at, want=1))


LOOK["wheel_cart"] = (wheel_cart, look_wheel_cart, [{"body": b, "drive": d} for b in wheel_cart.BODIES for d in wheel_cart.DRIVES])
WANT |= {("wheel_cart", "deck"), ("wheel_cart", "wheel"), ("wheel_cart", "tube"), ("wheel_cart", "ramp")}


# --- stick_prop: 持ち物の玩具。閉じる筒と笠と 2 つ折りの羽は、外から見る ---

def look_stick_prop(p):
    for q in stick_prop.parts(p):
        if not (q.valley or q.mountain):
            continue
        if q.key == "lantern":
            # 行灯は 4 面を折り、糊代で閉じる四角い筒
            wrong("stick_prop", q, "色の面が筒の内を向く", outward(q, 90.0))
        elif q.key == "sleeve":
            # 鞘は 2 面を折り、糊代で閉じる平たい筒。刀身を中に差す
            wrong("stick_prop", q, "色の面が筒の内を向く", outward(q, 170.0))
        elif q.key == "tokin":
            # 兜巾の笠は、1 区切りを切り落として閉じる浅い六角の笠。額に当てる
            wrong("stick_prop", q, "色の面が笠の内を向く", outward(q, 20.0))
        elif q.key.startswith("fletch"):
            # 矢羽は白と墨の境で 2 つ折りにし、つまようじの頭を挟んで貼る
            wrong("stick_prop", q, "色の面が貼り合わせる側を向く", outward(q, 170.0))


LOOK["stick_prop"] = (stick_prop, look_stick_prop, [{"shape": s, "hold": h} for s, hs in stick_prop.HOLDS.items() for h in hs])
WANT |= {("stick_prop", "lantern"), ("stick_prop", "sleeve"), ("stick_prop", "tokin"), ("stick_prop", "fletch")}


# --- stand_figure: 人形を立てる箱。台は伏せて外を見せ、器は上が開いて中を上から見る ---

def look_stand_figure(p):
    for q in stand_figure.parts(p):
        if q.key != "tray":
            continue
        if p["form"] == "base":
            # 台は伏せて置き、上の面に人形を貼る。天板と 4 つの壁の刷った面が箱の外
            wrong("stand_figure", q, "色の面が伏せた箱の内を向く", outward(q, 90.0))
        else:
            # 浮かべる器と物を入れる器は、上が開いた器。人形や豆を中に置き、底と壁の内（刷った面）を上から見る
            at = (p["base_h"] + p["base_w"] / 2, p["base_h"] + p["base_d"] / 2)
            wrong("stand_figure", q, "壁が刷った面の裏へ折れ、器の内の色が上から見えない", leaning(q, at, want=1, only_colored=True))
        seen.add(("stand_figure", f"tray/{p['form']}"))


LOOK["stand_figure"] = (stand_figure, look_stand_figure, [{"form": f} for f in stand_figure.FORMS])
WANT |= {("stand_figure", "tray/base"), ("stand_figure", "tray/float"), ("stand_figure", "tray/box")}


def cases():
    """(雛形の ID, 寸法)。玩具の記録の案を全部と、雛形の選びの組のうち範囲の内の物を全部。"""
    for f in sorted((ROOT / "data/hypotheses").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for h in d.get("hypotheses", []):
            tid = h.get("template") or d.get("template")
            if tid in LOOK:
                yield tid, {**LOOK[tid][0].DEFAULTS, **(h.get("params") or {})}
    for tid, (tpl, _, picks) in LOOK.items():
        for pick in picks:
            p = {**tpl.DEFAULTS, **pick}
            if not tpl.check_range(p):
                yield tid, p


count = collections.Counter()
for tid, p in cases():
    count[tid] += 1
    LOOK[tid][1](p)

assert not bad, "刷った面が見えない側に来る部品:\n" + "\n".join(f"{k}（{n} 形）" for k, n in sorted(bad.items()))
assert seen >= WANT, f"見なかった部品 {sorted(WANT - seen)}"
print("見た形: " + "・".join(f"{t} {n}" for t, n in sorted(count.items())))
print("ok")
