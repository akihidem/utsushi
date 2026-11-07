"""雛形 pendulum_wave: 振り子の波（物理の作例。江戸の玩具ではない試作）。

制作者の言葉（2026-11-07）「内部構造を持つ機構をつくれるシステム」と、制作者の指示（同じ日）「何個かつくってみてよ。」
（江戸の玩具以外の、物理現象などの紙のモデルを試作する）による試作の雛形。制作者の言葉（同じ日）「作ってみる。試作して開発中と書く」により、
試作して開発中の雛形として README に書く。

長さを少しずつ変えた振り子を梁に並べる。決まった時間 Γ（cycle_s 秒）の間に、いちばん長い振り子が n0 回、次が n0 + 1 回、…
振れるように長さを決めると、放した後に振り子の並びが波のように見え、Γ 秒でまた全部がそろう。
- 周期: 糸の重さを入れず、玉（粘土の球）を点の重りと見て T = 2π√(L/g)（L は支点の線から玉の真ん中まで）。L は L = g(T/2π)²。
  玉の回る重さ（剛体の振り子の 2r²/5 の項）は入れない。糸は玉の真ん中を梁に沿う向き（揺れの軸と平行）に通るので、玉は糸を軸に
  回れて、揺れても向きを変えずに動くため（見直しの指摘で、前の剛体の式から替えた。剛体の式との差は長さで 0.2〜0.3mm で、
  糸の長さを手で合わせる確かさ（1mm ほど）より小さい）。
- n0 は、いちばん長い振り子が longest_mm に収まる、いちばん小さい整数。長い振り子ほど Γ 秒の振れる回数が少ない。
- 吊り方は V の字（1 本の糸を梁の 2 つの穴から下ろし、真ん中に玉）。V の面は梁に沿うので、玉は梁に直交する面の中だけで振れ、
  隣の玉の面と交わらない（1 本の糸だと円を描きやすい）。支点の線は 2 つの穴を結ぶ線で、L は梁の下の面から玉の真ん中まで。
- 梁は U の字（穴のある面が下）で、上が開いているので、糸の端を梁の中でテープで留め、長さを合わせられる。梁は 2 つの塔
  （三角の筒）の上に乗る。塔の高さは、いちばん長い振り子の玉の下が机から CLEAR 離れる高さ。
- 長さは刷った「糸の物差し」で合わせる（左の端を梁の下の面に当て、玉の真ん中を番号の線に合わせる）。
この型紙の寸法の決まり（玉が隣と当たらない・穴の組が重ならない・V が浅すぎない・梁の端が塔に乗る）は、範囲の床（F5.range）で
落とす（試作で、凍結の床を足さないため）。周期と長さ・Γ でそろう事は試験（tests/test_pendulum_wave.py）で見る。
限り: 小さい振れの式（放す角は swing_deg まで）。空気・糸の伸び・梁のたわみ・塔の揺れは入れない。どの振り子も同じ角で放さないと、
大きい振れの分（周期が θ²/16 だけ延びる）が振り子ごとに違い、Γ でそろわない。実物で確かめていない。
"""
import math

from ..model import Failure, Part
from ..paper_words import paper_name
from ..textfit import text_width

ID = "pendulum_wave"
DEFAULTS = {
    "kind": "wave",
    "count": 6,  # 振り子の数
    "cycle_s": 20,  # 全部がそろう時間 Γ（秒）
    "longest_mm": 80,  # いちばん長い振り子の長さの上限（梁の下の面から玉の真ん中まで）
    "spacing": 18,  # 隣の振り子の間（梁の長さの向き）
    "v_span": 12,  # 1 つの振り子の 2 つの穴の間（V の上の幅）
    "bob_g": 2.0,  # 粘土の玉 1 つの重さ
    "swing_deg": 10,  # 放す角の目安（小さい振れの式の範囲）
    "tower_side": 26,  # 塔の三角の 1 辺
    "beam_side": 16,  # 梁の U の 1 辺
    "end": 18,  # 梁の端から外の振り子の真ん中まで（塔の上に乗る所）
    "glue": 8,
    "paper_gsm": 150,
}
RANGES = {
    "count": (3, 8), "cycle_s": (10, 60), "longest_mm": (50, 120), "spacing": (10, 30), "v_span": (6, 24),
    "bob_g": (0.5, 5.0), "swing_deg": (3, 15), "tower_side": (20, 40), "beam_side": (12, 24), "end": (10, 30),
    "glue": (5, 12), "paper_gsm": (40, 400),
}
KINDS = ("wave",)
FORM = "kind"
FORMS = KINDS
SOURCE = "PRINCIPLE-pendulum-wave"
TITLES = {"wave": "長さを変えた振り子の波"}
G_MM = 9806.65  # 重力の加速度 mm/s²
CLAY_DENSITY = 1.8e-3  # 油粘土の密度 g/mm³（ほかの雛形と同じ見込み）
CLEAR = 5.0  # 玉の下と机の間 mm
BOB_GAP = 2.0  # 隣の玉の間の余り mm
HOLE_R = 1.0  # 穴の半径（竹串の先であける）
HOLE_GAP = 3.0  # 隣の穴の縁どうしの間の下限 mm（紙が裂けない見込み）
V_DEPTH = 2.0  # V の深さ（いちばん短い振り子の長さ）は上の幅の何倍以上か。浅いと糸が開いて玉の高さが合わせにくい
TIE = 60  # 糸の結び代とテープの分（両端の合わせ）mm
LABEL_SIZE = 2.8  # 札の字の大きさ（compose.LABEL_SIZE と同じ。雛形から compose を読むと読み込みの輪になるので、値を写す）
LABEL_LINE = 1.25
MARK = "#9b3b2a"


def title(p):
    return TITLES[p["kind"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "kind": KINDS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "kind":
            if v not in KINDS:
                out.append(Failure("F5.range", k, f"{v} は {KINDS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
        elif k == "count" and not float(v).is_integer():
            out.append(Failure("F5.range", k, f"{v} は整数でない（振り子の数）"))
    return out


def bob_r(g):
    """粘土の玉の半径 mm。"""
    return (3 * g / (4 * math.pi * CLAY_DENSITY)) ** (1 / 3)


def first_swings(p):
    """いちばん長い振り子が Γ 秒に振れる回数 n0。玉を点と見た長さ g(Γ/2πn)² が longest_mm に収まる、いちばん小さい整数
    （長さの式と同じ、点の重りの長さ）。"""
    return math.ceil(p["cycle_s"] / (2 * math.pi) * math.sqrt(G_MM / p["longest_mm"]) - 1e-9)


def swings(p):
    n0 = first_swings(p)
    return [n0 + k for k in range(int(p["count"]))]


def length_for(period):
    """周期 period（秒）で振れる振り子の長さ（支点の線から玉の真ん中まで）。点の重りの L = g(T/2π)²。"""
    return G_MM * (period / (2 * math.pi)) ** 2


def period_of(L):
    """長さ L の振り子の周期（秒）。点の重りの T = 2π√(L/g)。"""
    return 2 * math.pi * math.sqrt(L / G_MM)


def lengths(p):
    return [length_for(p["cycle_s"] / n) for n in swings(p)]


def tower_height(p):
    """塔の高さ（机から梁の下の面まで）。いちばん長い振り子の玉の下が机から CLEAR 離れる高さを、mm の整数に切り上げる。"""
    return math.ceil(lengths(p)[0] + bob_r(p["bob_g"]) + CLEAR)


def beam_length(p):
    return 2 * p["end"] + (int(p["count"]) - 1) * p["spacing"]


def thread_length(p, L):
    """1 本の糸の長さ（V の 2 本の辺と結び代）。整数 mm に切り上げる。"""
    return math.ceil(2 * math.hypot(L, p["v_span"] / 2) + TIE)


def check_physics(p):
    out = []
    r = bob_r(p["bob_g"])
    if p["spacing"] < 2 * r + BOB_GAP:
        out.append(Failure("F5.range", "spacing", f"隣の振り子の間 {p['spacing']}mm が、玉の直径 {2 * r:.1f}mm ＋ {BOB_GAP:g}mm より狭く、静かな時に玉が当たる"))
    if p["spacing"] - p["v_span"] < 2 * HOLE_R + HOLE_GAP:
        out.append(Failure("F5.range", "v_span", f"隣の振り子の穴どうしの縁の間 {p['spacing'] - p['v_span'] - 2 * HOLE_R:.1f}mm が {HOLE_GAP:g}mm より狭く、梁の紙が裂けやすい"))
    if lengths(p)[-1] < V_DEPTH * p["v_span"]:
        out.append(Failure("F5.range", "v_span", f"いちばん短い振り子 {lengths(p)[-1]:.1f}mm が V の上の幅の {V_DEPTH:g} 倍より短く、糸が開いて玉の高さを合わせにくい"))
    if p["end"] < p["tower_side"] / 2 + 2:
        out.append(Failure("F5.range", "end", f"梁の端の長さ {p['end']}mm が塔の幅の半分 ＋ 2mm より短く、梁が塔の上に乗らない"))
    return out


def _tower(p, number, key):
    """塔（三角の筒）。部品の key は英小文字だけ（omochae.foldsim が書き出しの名に使う）。3 つの面と横の糊代、真ん中の面の上に三角のふた。ふたは上で折ってテープで留める。"""
    a, g, H = p["tower_side"], p["glue"], tower_height(p)
    cap = a * math.sqrt(3) / 2
    outline = [(0, cap), (a, cap), (1.5 * a, 0), (2 * a, cap), (3 * a, cap), (3 * a + g, cap + 2), (3 * a + g, cap + H - 2), (3 * a, cap + H), (0, cap + H)]
    mountain = [((a, cap), (a, cap + H)), ((2 * a, cap), (2 * a, cap + H)), ((3 * a, cap), (3 * a, cap + H)), ((a, cap), (2 * a, cap))]
    glue = [[(3 * a, cap), (3 * a + g, cap + 2), (3 * a + g, cap + H - 2), (3 * a, cap + H)]]
    # 面の境の折り線を絵がまたがないよう、面ごとに塗る
    art = [{"kind": "poly", "pts": [(i * a + 0.2, cap + 0.2), ((i + 1) * a - 0.2, cap + 0.2), ((i + 1) * a - 0.2, cap + H - 0.2), (i * a + 0.2, cap + H - 0.2)], "fill": "#e8dfc8"} for i in range(3)]
    name = f"{number} 塔"
    return Part(number, key, "塔", outline, label_xy=(2, cap + 2), label=name, mountain=mountain, glue=glue, art=art)


def _beam(p):
    """梁（U の字）。真ん中の面（穴のある面）が下になる。振り子 k の 2 つの穴は、真ん中の線から v_span/2 ずつ離れる。
    穴の組の上に番号を刷る（糸の物差しの番号と同じ）。"""
    b, L, n = p["beam_side"], beam_length(p), int(p["count"])
    outline = [(0, 0), (L, 0), (L, 3 * b), (0, 3 * b)]
    mountain = [((0, b), (L, b)), ((0, 2 * b), (L, 2 * b))]
    holes, lines = [], [("1 梁", 1.5, 1.0)]
    for k in range(n):
        x = p["end"] + k * p["spacing"]
        holes += [(x - p["v_span"] / 2, 1.5 * b, HOLE_R), (x + p["v_span"] / 2, 1.5 * b, HOLE_R)]
        num = str(k + 1)
        lines.append((num, x - text_width(num, LABEL_SIZE) / 2, b + 1.0))
    art = [{"kind": "mark", "pts": [(p["end"] + k * p["spacing"], 1.5 * b + 2.5), (p["end"] + k * p["spacing"], 2 * b - 1.0)], "mark": "hang"} for k in range(n)]
    return Part(1, "beam", "梁", outline, label_xy=(1.5, 1.0), label="1 梁", label_lines=lines, mountain=mountain, holes=holes, art=art)


def _gauge(p):
    """糸の物差し（横に長い帯）。左の端を梁の下の面に当て、玉の真ん中を同じ番号の線に合わせる。線は振り子 k の長さ L_k の所。
    番号は線の右に、上と下の段を交互に置く（隣の線は数 mm しか離れないので、同じ段に並べると字が重なる）。"""
    Ls = lengths(p)
    w, h = math.ceil(Ls[0]) + 8, 16.0
    outline = [(0, 0), (w, 0), (w, h), (0, h)]
    art = [{"kind": "line", "pts": [(L, 0.3), (L, h - 0.3)], "stroke": "#1d1d1d", "sw": 0.3} for L in Ls]
    lines = [("4 糸の物差し", 1.5, 1.0)]
    for k, L in enumerate(Ls):
        num = str(k + 1)
        lines.append((num, L + 0.6, 1.0 if k % 2 == 0 else h - 1.0 - LABEL_SIZE * LABEL_LINE))
    return Part(4, "gauge", "糸の物差し", outline, label_xy=(1.5, 1.0), label="4 糸の物差し", label_lines=lines, art=art)


def parts(p):
    return [_beam(p), _tower(p, 2, "lefttower"), _tower(p, 3, "righttower"), _gauge(p)]


def place(by_key, page, top, gap):
    """塔 2 つを上の段に並べ、梁と糸の物差しを下の段に縦に置く。説明の列は部品の下に左から置く。"""
    x, y = page.x0, top
    row = 0.0
    for key in ("lefttower", "righttower"):
        q = by_key[key]
        q.x, q.y = x - min(a for a, _ in q.outline), y - min(b for _, b in q.outline)
        x += q.width + gap
        row = max(row, q.height)
    y += row + gap
    for key in ("beam", "gauge"):
        q = by_key[key]
        q.x, q.y = page.x0, y
        y += q.height + gap
    return y, page.x1 - page.x0, page.x0


def bom(p):
    paper = paper_name(gsm=p["paper_gsm"])
    why = "家庭のプリンタで刷って作るため"
    n = int(p["count"])
    total = sum(thread_length(p, L) for L in lengths(p))
    return [
        {"number": 1, "key": "beam", "name": "梁", "qty": 1, "material": paper, "substituted": False, "original_guess": "無し（作例）", "reason": why},
        {"number": 2, "key": "lefttower", "name": "塔", "qty": 1, "material": paper, "substituted": False, "original_guess": "無し（作例）", "reason": why},
        {"number": 3, "key": "righttower", "name": "塔", "qty": 1, "material": paper, "substituted": False, "original_guess": "無し（作例）", "reason": why},
        {"number": 4, "key": "gauge", "name": "糸の物差し", "qty": 1, "material": paper, "substituted": False, "original_guess": "無し（組むための物差し）", "reason": "糸の長さを合わせるため"},
        {"number": 7, "key": "thread", "name": "糸", "qty": n, "material": f"たこ糸（合わせて 約 {math.ceil(total / 10)}cm）", "substituted": False, "original_guess": "無し（作例）", "reason": "伸びにくく、結びやすいため"},
        {"number": 8, "key": "bob", "name": "玉", "qty": n, "material": f"油粘土 {p['bob_g']:g}g ずつ（直径 約 {2 * bob_r(p['bob_g']):.0f}mm）", "substituted": False, "original_guess": "無し（作例）", "reason": "重さをそろえやすいため"},
    ]


def materials(p):
    Ls = lengths(p)
    cuts = "・".join(f"{k + 1} は {thread_length(p, L)}mm" for k, L in enumerate(Ls))
    return [f"{paper_name(gsm=p['paper_gsm'])}を 1 枚", "のり、はさみ、定規、セロハンテープ、時計（秒が分かる物）",
            f"たこ糸を {len(Ls)} 本（{cuts}）", f"油粘土 {p['bob_g']:g}g を {len(Ls)} 個（同じ重さの玉に丸める）",
            "竹串 1 本（梁の穴をあける）。小さい丸い印は穴"]


def steps(p):
    n, cyc = int(p["count"]), p["cycle_s"]
    return [
        "刷った物差しに定規を当て、10cm か確かめる",
        "部品を実線で切る。1 梁の小さい穴は竹串の先であける",
        "2・3 塔を破線で山折りして三角の筒にし、糊代で貼る。上の三角のふたを折って、テープで留める",
        "1 梁を破線で山折りして U の字にする（穴と番号のある面が下）",
        "1 梁の両端の下の面を、2・3 塔のふたの上に貼る",
        # 糸は玉の真ん中を横に通す。長さの式（点の重り）は、吊った時に糸が玉の真ん中を梁と同じ向きに横切り、玉が糸を軸に
        # 回れる事を前に置く（見直しの指摘: 「糸に付ける」だけでは、玉の表に付けたり真ん中から外したりできた）
        f"糸を {n} 本切る（長さは用意する物のとおり）。粘土を {n} 個の同じ重さの玉にし、糸の真ん中をはさんで丸め直して、"
        "糸が玉の真ん中を横に通る形にする（吊った時に、糸が玉を梁と同じ向きに横切る）",
        "糸の両端を、1 梁の同じ番号の 2 つの穴に下から通し、梁の中でテープで仮に留める（V の字になる）",
        "4 糸の物差しの左の端を梁の下の面に当て、玉の真ん中が同じ番号の線に来るまで糸を引いて合わせ、テープで留める",
        f"全部の玉を、梁に直交する向きへ同じだけ（{p['swing_deg']:g}° くらい）引いて、一度に放す。{cyc:g} 秒でまた全部がそろう",
    ]


def check_build(p):
    """組み立てに使う量（試験と組み方の頁が読む）。"""
    return {"swings": swings(p), "lengths": lengths(p), "tower_height": tower_height(p), "beam_length": beam_length(p)}
