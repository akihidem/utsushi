"""型紙エンジンが出す作り方の 3D（JSON）を、組み立ての頁が読む形にする。

決定（2026-11-07）: サイトの 3D の作り直しは、型紙エンジンが JSON で出し、サイトはそれを読んで描く形で進める。
本人の指示（11-07）「サイトの作り方の3Dは古い型のものだから、新しいのにしないと。」の作り方。
前は、サイトが自分で組んでいた（assembly の _slider_fan・_pivot_counterweight）。その作りは前の組（tora-v4・goraigo-v10）の形のまま残し、
今の組だけを JSON で描く。紙の仕組みの正はエンジンで（README の決まり）、同じ組み方をサイトで書き直すと、エンジンの直しが漏れても見つけにくいため。

置き場: data/kumitate/<組の名>.json（エンジンの出力を写す。頁はエンジンの repo を読まずに動く）。形の名は FORMAT。
読む物（無い物はサイトが今の決め方で足す）:
- parts: 部品ごとの面（poly と、面の中の穴 inner）と面のつながり（tree の root と rows: 子の面 → 親の面・折り線の 2 点・谷か山）
- steps: 手順の文と 1 対 1 の段。段ごとの poses（動きの区切り）。finale: 段の後のできあがりの動き
- POSE: parts の部品ごとに place（根の面の行列）・turns（折り線の向きのまわりの向き付きの角。無ければ angles と谷山から出す）・
  panels（面ごとの行列）・lift（貼って重なる面の前後のずらし。見せる時だけ）・custom（折りで表せない形。panels だけで描く）。
  hidden・rods（棒と糸）・balls（粘土の玉）・view・on_paper・tool・attached（切るまで面についている切れ端）・order・dur・cam
- 行列は CSS の matrix3d と同じ列優先の 16 個で、長さは mm（頁が px に直す）。座標は x 右・y 下・z 見る人の方で、刷った面は +z

判断の芯:
- 絵と刷った線はサイトの部品（刷った紙と同じ物）から描き、JSON からは面の形と動きだけを取る。JSON の部品の形がサイトの部品と
  違えば（外形・穴・折り線）、3D を出さずに文と絵だけにする（tests/test_assembly_json.py が見る）。違う紙の立体を見せないため
- 手順の文はサイトの文を使い、JSON の段とは数だけを合わせる（サイトとエンジンで字の違う手順がある）。数が違えば F13.assembly で落とす
"""
import json
import math
import pathlib
from dataclasses import dataclass, field

from shapely.geometry import Polygon, box

from . import assembly
from .model import Failure, Part

FORMAT = "omochae-assembly-3d/1"
DIR = assembly.ROOT / "data/kumitate"
# 頁が描く棒と糸の名（kumitate の rt-rod）。エンジンの名からこの名へ移す。知らない名の棒は竹串、糸は扇の要からの糸として描く
RODS = {"skewer": "axle", "axle": "axle", "poke": "poke", "row": "row", "thread": "thread"}
CLAY = "#8d6b4a"  # 粘土の玉の色（前の組の組み立てと同じ）。JSON に色があればそれを使う
BALL_SEGS = 16  # 粘土の玉は、見る人に向けた丸い面で描く（前の組と同じ。玉の立体は描かない）


def rounds(part):
    """部品の中を切る丸い穴。丸い穴の欄が無い部品の型（虎の今の組の欄が入る前の型）は空と読む。"""
    return list(getattr(part, "round_cuts", ()))


def path_of(name):
    return DIR / f"{name}.json"


def load(name):
    """組の名の JSON。無い時は None。"""
    p = path_of(name)
    if not p.exists():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("format") != FORMAT:
        raise ValueError(f"{p.name}: 形が {doc.get('format')!r} で、{FORMAT} でない")
    return doc


def rows_of(cols):
    """列優先の 16 個 → 行の並びの 4×4。"""
    return [[float(cols[c * 4 + r]) for c in range(4)] for r in range(4)]


def cols_of(m):
    """行の並びの 4×4 → 列優先の 16 個（書き出す時の桁は 1e-6 mm まで。読み戻した形が頁で同じ px になる）。"""
    return [round(m[r][c], 6) for c in range(4) for r in range(4)]


@dataclass
class Plate:
    """部品 1 つ。絵と線はサイトの部品から、面と面のつながりは JSON から。assembly.Sheet と同じ口を持つ（頁はどちらも同じに読む）。"""
    part: object
    panels: list
    tree: dict  # 面 → (親の面, 折り線の番号)
    lines: list  # [(線の 2 点, "valley"|"mountain")]
    root: int = 0

    # 折り線のまわりの回し方は Sheet と同じ計算を使う（面と線の持ち方が同じなので、書き直さない）
    hinge = assembly.Sheet.hinge
    turn = assembly.Sheet.turn
    depth = assembly.Sheet.depth
    matrices = assembly.Sheet.matrices


@dataclass
class Shown:
    """JSON から作った組み立て。頁（web.kumitate）と assemble の 1 対 1 の確かめが読む所は、assembly.Bench と同じ名にした。"""
    sheets: dict
    frames: list
    paper: object = None
    failures: list = field(default_factory=list)
    params: dict = field(default_factory=dict)


def _plate(jp, part):
    panels = []
    for pn in sorted(jp["panels"], key=lambda q: int(q["id"])):
        panels.append(Polygon([tuple(x) for x in pn["poly"]], [[tuple(x) for x in ring] for ring in pn.get("inner") or []]).buffer(0))
    if not any(pn.get("inner") for pn in jp["panels"]):
        # 面の中の穴を JSON が書いていない時は、サイトの部品の中を切る所（四角と丸）を面から抜く（assembly.Sheet と同じ）。抜かないと穴が塞がって見える
        holes = [box(x, y, x + w, y + h) for x, y, w, h in part.cuts] + [assembly.round_hole(x, y, r) for x, y, r in rounds(part)]
        for hole in holes:
            panels = [s.difference(hole) for s in panels]
    tree, lines = {}, []
    for k, (child, row) in enumerate(sorted(jp["tree"]["rows"].items(), key=lambda kv: int(kv[0]))):
        tree[int(child)] = (int(row["parent"]), k)
        lines.append((tuple(tuple(x) for x in row["hinge"]), row["kind"]))
    return Plate(part, panels, tree, lines, int(jp["tree"]["root"]))


def _ball(n, r, color):
    circle = [(r * math.cos(2 * math.pi * i / BALL_SEGS), r * math.sin(2 * math.pi * i / BALL_SEGS)) for i in range(BALL_SEGS)]
    part = Part(n, "clay", "粘土", circle, label="", art=[{"kind": "poly", "pts": circle, "fill": color}])
    return Plate(part, [Polygon(circle)], {}, [], 0)


def _turns(plate, got):
    """POSE の turns（向き付きの角）。無ければ angles（谷と山の種類のとおりの角）から、Sheet と同じ決め方で向きを付ける。"""
    if "turns" in got:
        return {int(i): float(d) for i, d in got["turns"].items()}
    by_line = {plate.tree[int(i)][1]: float(d) for i, d in (got.get("angles") or {}).items()}
    return {i: plate.turn(i, by_line) for i in plate.tree}


def _place_of(plate, got, turns):
    """面ごとの行列（lift を入れない形）。custom の部品と、面の行列だけがある部品は panels を使い、ほかは place と turns から組む。"""
    if got.get("custom") or "place" not in got:
        return {int(i): rows_of(m) for i, m in got["panels"].items()}
    place = rows_of(got["place"])
    out = {plate.root: place}

    def of(i):
        if i not in out:
            point, axis = plate.hinge(i)
            out[i] = assembly.mul(of(plate.tree[i][0]), assembly.rotate_axis(point, axis, turns[i]))
        return out[i]

    for i in range(len(plate.panels)):
        of(i)
    return out


def _pose(sheets, got, owner0, rods0):
    parts = got.get("parts") or {}
    hidden = set(got.get("hidden") or [])
    panels, state = {}, {}
    for key, plate in sheets.items():
        mine = parts.get(key)
        if key == "clay":
            continue
        shown = mine is not None and key not in hidden
        ms = {}
        if shown:
            turns = _turns(plate, mine)
            ms = _place_of(plate, mine, turns)
            lift = {int(i): float(d) for i, d in (mine.get("lift") or {}).items()}
            ms = {i: (assembly.mul(m, assembly.translate(0, 0, lift[i])) if lift.get(i) else m) for i, m in ms.items()}
            if not mine.get("custom") and "place" in mine:
                state[key] = {"place": rows_of(mine["place"]), "turns": turns, "nudge": lift}
        for i in range(len(plate.panels)):
            panels[f"{key}:{i}"] = ms.get(i)
    if "clay" in sheets:
        at = (got.get("balls") or {}).get("clay")
        shown = at is not None and "clay" not in hidden
        m = assembly.translate(*at["at"]) if shown else None
        panels["clay:0"] = m
        if shown:
            state["clay"] = {"place": m, "turns": {}, "nudge": {}}
    extras = {}
    for name, rod in (got.get("rods") or {}).items():
        rod = {**(rods0.get(name) or {}), **rod}  # 棒の種類と持ち主は、JSON の頭の rods にも書ける（段ごとの値が先）
        extras[RODS.get(name, "thread" if rod.get("kind") == "thread" else "axle")] = (tuple(rod["from"]), tuple(rod["to"]), rod.get("owner") or owner0)
    attached = got.get("attached") or []
    view = got.get("view") or {}
    pose = {"panels": panels, "view": {k: view[k] for k in ("rx", "ry") if k in view}, "extras": extras, "state": state, "dur": got.get("dur"),
            "paper": bool(got.get("on_paper")), "scrap": any(a.endswith(":slot") for a in attached), "plug": any(a.endswith(":cut") for a in attached)}
    if view.get("focus"):
        pose["focus"] = tuple(view["focus"])
    for name in ("cam", "order"):
        if got.get(name) is not None:
            pose[name] = got[name] if name != "order" else {k: {int(i): v for i, v in o.items()} for k, o in got[name].items()}
    tool = got.get("tool")
    if tool:
        pts = [tuple(x) for x in tool["path"]]
        if tool["kind"] in ("scissors", "knife"):
            pose["cut"] = [x[:2] for x in pts]
            if tool["kind"] == "knife":
                pose["knife"] = True
        elif tool["kind"] == "ruler":
            pose["ruler"] = pts[0][:2]
        elif tool["kind"] == "poke":
            extras["poke"] = (pts[0], pts[-1], tool.get("owner") or owner0)
    return pose


def bench_of(doc, parts, words, paper=None):
    """JSON（doc）とサイトの部品（parts）から、頁が読む組み立てを作る。words はサイトの手順の文。"""
    by = {q.key: q for q in parts}
    shown = Shown({}, [], paper, params=dict(doc.get("params") or {}))
    for jp in doc["parts"]:
        if jp["key"] not in by:
            shown.failures.append(Failure("F13.assembly", jp["key"], "JSON の部品がサイトの型紙に無い"))
            continue
        shown.sheets[jp["key"]] = _plate(jp, by[jp["key"]])
    ball = (doc.get("balls") or {}).get("clay")
    if ball:
        shown.sheets["clay"] = _ball(len(parts) + 1, float(ball["r"]), ball.get("color") or CLAY)
    owner0 = next(iter(shown.sheets), "")
    rods0 = doc.get("rods") or {}
    steps = doc.get("steps") or []
    for n, st in enumerate(steps, 1):
        poses = [_pose(shown.sheets, got, owner0, rods0) for got in st["poses"]]
        last = poses[-1]
        shown.frames.append({"step": n, "text": words[n - 1] if n <= len(words) else st.get("text", ""), "poses": poses, "panels": last["panels"],
                             "view": last["view"], "extras": last["extras"], "state": last["state"]})
    if doc.get("finale"):
        poses = [_pose(shown.sheets, got, owner0, rods0) for got in doc["finale"]["poses"]]
        last = poses[-1]
        shown.frames.append({"step": len(steps) + 1, "text": "", "poses": poses, "panels": last["panels"], "view": last["view"],
                             "extras": last["extras"], "state": last["state"]})
    if len(steps) != len(words):
        shown.failures.append(Failure("F13.assembly", "手順", f"JSON の段が {len(steps)} で、手順の文 {len(words)} と 1 対 1 に並ばない"))
    return shown


def same_parts(doc, parts, tol=0.05):
    """JSON の部品の形が、サイトの部品（刷る紙）と同じか。Returns 違う所の一覧（空なら同じ）。外形・穴・丸い穴・折り線を見る。
    面の形は、面を合わせた広さが外形と同じか（中の穴を除く）と、折り線が刷る線と同じかで見る（面の分け方はエンジンに任せる）。"""
    by = {q.key: q for q in parts}
    out = []
    keys = [jp["key"] for jp in doc["parts"]]
    for key in sorted(set(by) - set(keys)):
        out.append(f"{key}: サイトの部品が JSON に無い")
    for jp in doc["parts"]:
        q = by.get(jp["key"])
        if q is None:
            out.append(f"{jp['key']}: JSON の部品がサイトの型紙に無い")
            continue
        if "outline" in jp and Polygon(q.outline).buffer(0).symmetric_difference(Polygon(jp["outline"]).buffer(0)).area > tol * 10:
            out.append(f"{q.key}: 外形が違う")
        for name in ("holes", "round_cuts"):
            mine, theirs = [tuple(h) for h in (rounds(q) if name == "round_cuts" else q.holes)], [tuple(h) for h in jp.get(name) or []]
            if len(mine) != len(theirs) or any(max(abs(a - b) for a, b in zip(m, t)) > tol for m, t in zip(sorted(mine), sorted(theirs))):
                out.append(f"{q.key}: {name} が違う")
        plate = _plate(jp, q)
        area = sum(s.area for s in plate.panels)
        cut = sum(assembly.round_hole(0, 0, r).area for _, _, r in rounds(q)) + sum(w * h for _, _, w, h in q.cuts)
        if abs(area - (Polygon(q.outline).buffer(0).area - cut)) > max(1.0, 0.01 * area):
            out.append(f"{q.key}: 面を合わせた広さが紙と違う（{area:.1f} と {Polygon(q.outline).buffer(0).area - cut:.1f}mm²）")
        printed = [seg for seg in q.valley] + [seg for seg in q.mountain]
        hinges = [seg for seg, _ in plate.lines]
        for seg in printed:
            if not any(_on(seg, h, tol) for h in hinges):
                out.append(f"{q.key}: 刷る折り線 {seg} が JSON の面のつながりに無い")
                break
    return out


def _on(seg, hinge, tol):
    """刷る折り線 seg が、面のつながりの折り線 hinge と同じ直線の上で重なるか（エンジンが線を面ごとに分けても同じと読む）。"""
    (ax, ay), (bx, by) = seg
    (cx, cy), (dx, dy) = hinge
    n = math.hypot(bx - ax, by - ay)
    if n < 1e-9:
        return False
    far = lambda px, py: abs((bx - ax) * (py - ay) - (by - ay) * (px - ax)) / n
    if far(cx, cy) > tol or far(dx, dy) > tol:
        return False
    t = lambda px, py: ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / (n * n)
    lo, hi = sorted((t(cx, cy), t(dx, dy)))
    return hi > tol / n and lo < 1 - tol / n


def dump(bench, words, meta=None):
    """サイトの組み立て（assembly.Bench）を同じ形の JSON にする。読む口の試験（書いて読み戻すと頁へ渡す形が同じ）と、
    エンジンへ渡す見本（サイトが読む形）に使う。開いた扇（前の組の御来迎の最後）は、頁の計算で動かすので書き出さない。"""
    def part_of(key, sheet):
        q = sheet.part
        return {"key": key, "number": q.number, "name": q.name, "outline": [list(x) for x in q.outline],
                "panels": [{"id": i, "poly": [list(x) for x in s.exterior.coords[:-1]], "inner": [[list(x) for x in r.coords[:-1]] for r in s.interiors]}
                           for i, s in enumerate(sheet.panels)],
                "tree": {"root": sheet.root, "rows": {str(i): {"parent": p, "hinge": [list(sheet.lines[k][0][0]), list(sheet.lines[k][0][1])], "kind": sheet.lines[k][1]}
                                                       for i, (p, k) in sorted(sheet.tree.items())}},
                "holes": [list(h) for h in q.holes], "round_cuts": [list(h) for h in rounds(q)]}

    def pose_of(pose):
        out = {"parts": {}, "hidden": [], "rods": {}, "view": dict(pose["view"]), "on_paper": pose["paper"],
               "attached": ([f"{k}:cut" for k, s in bench.sheets.items() if s.part.cuts or rounds(s.part)] if pose["plug"] else [])
               + (["tube:slot"] if pose["scrap"] else [])}
        for key, sheet in bench.sheets.items():
            if key == "clay":
                m = pose["panels"].get("clay:0")
                if m is not None:
                    out["balls"] = {"clay": {"at": [m[0][3], m[1][3], m[2][3]]}}
                continue
            ms = {i: pose["panels"][f"{key}:{i}"] for i in range(len(sheet.panels))}
            if all(m is None for m in ms.values()):
                out["hidden"].append(key)
                continue
            st = pose["state"].get(key)
            if st is None:
                out["parts"][key] = {"custom": True, "panels": {str(i): cols_of(m) for i, m in ms.items()}}
            else:
                lift = st["nudge"]
                bare = {i: (assembly.mul(m, assembly.translate(0, 0, -lift[i])) if lift.get(i) else m) for i, m in ms.items()}
                out["parts"][key] = {"place": cols_of(st["place"]), "turns": {str(i): d for i, d in st["turns"].items()},
                                     "panels": {str(i): cols_of(m) for i, m in bare.items()}, "lift": {str(i): d for i, d in lift.items()}}
        for name, (s, e, owner) in pose["extras"].items():
            if name == "poke":
                out["tool"] = {"kind": "poke", "path": [list(s), list(e)], "owner": owner}
            else:
                out["rods"][name] = {"kind": "thread" if name in ("row", "thread") else "rod", "from": list(s), "to": list(e), "owner": owner}
        if pose.get("focus"):
            out["view"]["focus"] = list(pose["focus"])
        if pose.get("cut"):
            out["tool"] = {"kind": "knife" if pose.get("knife") else "scissors", "path": [[x, y, 0.0] for x, y in pose["cut"]]}
        elif pose.get("ruler"):
            out["tool"] = {"kind": "ruler", "path": [[*pose["ruler"], 0.0]]}
        for name in ("dur", "cam"):
            if pose.get(name) is not None:
                out[name] = pose[name]
        if pose.get("order"):
            out["order"] = {k: {str(i): v for i, v in o.items()} for k, o in pose["order"].items()}
        return out

    doc = {"format": FORMAT, **(meta or {}), "parts": [part_of(k, s) for k, s in bench.sheets.items() if k != "clay"],
           "steps": [{"n": f["step"], "text": f["text"], "poses": [pose_of(p) for p in f["poses"]]} for f in bench.frames if f["step"] <= len(words)],
           "rods": {}, "balls": {}}
    if "clay" in bench.sheets:
        clay = bench.sheets["clay"].part
        doc["balls"]["clay"] = {"r": max(math.hypot(x, y) for x, y in clay.outline), "color": clay.art[0]["fill"]}
    rest = [f for f in bench.frames if f["step"] > len(words)]
    if rest:
        doc["finale"] = {"poses": [pose_of(p) for p in rest[0]["poses"]]}
    return doc
