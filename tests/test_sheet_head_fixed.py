"""刷る紙の題から仮説の印を外しても、部品の置き場が 1 つも動かない（統括の決め 11-08 の (b)）。

なぜ: 本人の言葉（11-08）「つくる、のところ仮説Cとか仮説Aとかはなしで仮説、と表記する」で紙の題が短くなり、この機械の字（Noto Serif CJK JP）では
虎 v7 の型紙の「刷った組」が題の行に入って頭の段が 1 行減り、部品の並び全体が 3.5mm 上へ動いた（別の目が --dump で比べて見つけた）。
compose の fit_title で、頭の段の高さと「刷った組」の置き方を前の題（印のある形）で決め、刷る字だけを新しい題にした。

見る事（2 通りの字の測り方: 決まった字の幅 standin と、この機械の字 real）:
1. 全部の玩具の今のたたき台の型紙で、「前の題で組んだ紙」と「新しい題を前の題の組み方で組んだ紙」の SVG を要素ごとに比べ、違うのは
   題の行（大きさ 5.0 の字）だけ。その字は前の題と新しい題。図形と、ほかの字の要素は 1 つも違わない
2. 負の対照: 組み方を前の題で決めない（fit_title を渡さない）と、この機械の字では虎 v7 の型紙の図形が動く（試験が動きを拾う事）。
   この機械の字が凍結の床の控えと違う機械では、2 は見ない（字の幅が違うと、もとから行の折り方が違う）
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from omochae import hypotheses, textfit  # noqa: E402
from omochae.compose import TEMPLATES, compose  # noqa: E402
from omochae.render import to_svg  # noqa: E402
from test_floor_pin import PIN, _Standin, font_mark, normalize  # noqa: E402

TORA = "NDL-1187053-R0000014-R"


def papers(sid, fit=True):
    """(前の題で組んだ SVG, 新しい題で組んだ SVG, 前の題, 新しい題)。たたき台の寸法が無い玩具は None。"""
    data = hypotheses.load(sid)
    h = hypotheses.sheet_of(sid)
    if not h or h.get("params") is None or h.get("template_id", "") is None:
        return None
    source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    tid = h.get("template") or data.get("template", "slider_fan")
    label = hypotheses.paper_label(data, 1)
    old = f"{data['toy']} 型紙 仮説 {hypotheses.letter(h)}「{h['name']}」{label}"
    new = f"{data['toy']} 型紙 {hypotheses.shown_name(h)}{label}"
    a = compose(tid, h["params"], source, "A4", 1, old)[1]
    try:
        b = compose(tid, h["params"], source, "A4", 1, new, fit_title=old if fit else None)[1]
    except TypeError:  # fit_title の口の無い前の作り（直す前の失敗を取る時）。新しい題だけで組む
        b = compose(tid, h["params"], source, "A4", 1, new)[1]
    if a is None or b is None:
        return None
    return to_svg(a), to_svg(b), old, new


def split(svg):
    """(題の行の字の並び, 題のほかの要素の並び)。要素は「<…>字」の形で、題の行（大きさ 5.0 の字）は字だけを取り出す。"""
    titles, rest = [], []
    skip = False
    for e in re.findall(r"<[^>]+>[^<]*", normalize(svg)):
        if re.match(r'<text [^>]*font-size="5\.0"', e):
            titles.append(e.split(">", 1)[1])
            skip = True  # 次の </text> は題の行の閉じ
            continue
        if skip and e.startswith("</text>"):
            skip = False
            if e[len("</text>"):].strip():
                rest.append(e[len("</text>"):])
            continue
        rest.append(e)
    return titles, rest


def only_title_differs(sid, a, b, old, new, kind):
    """題の行のほかの要素が全部同じで、題の行の字が前の題と新しい題（行の折り方は替わってよい。印を外すと短くなる）。"""
    ta, ra = split(a)
    tb, rb = split(b)
    diff = [(x, y) for x, y in zip(ra, rb) if x != y]
    assert len(ra) == len(rb) and not diff, (sid, kind, "題のほかの要素が違う", len(ra), len(rb), diff[:2])
    assert "".join(ta).replace(" ", "") == old.replace(" ", ""), (sid, kind, ta)
    assert "".join(tb).replace(" ", "") == new.replace(" ", ""), (sid, kind, tb)


def run(kind):
    seen = 0
    for path in sorted((ROOT / "data/hypotheses").glob("NDL-*.json")):
        sid = path.stem
        got = papers(sid)
        if got is None:
            continue
        only_title_differs(sid, *got, kind)
        seen += 1
    return seen


# 1. この機械の字（real）と、決まった字の幅（standin）の両方で
real_n = run("real")
keep = textfit._font
textfit._font = lambda: (_Standin(), _Standin(), 1000)
try:
    standin_n = run("standin")
finally:
    textfit._font = keep
assert real_n >= 2 and real_n == standin_n, (real_n, standin_n)

# 2. 負の対照: 組み方を前の題で決めないと、この機械の字では虎 v7 の型紙の図形が動く
same_font = json.loads(PIN.read_text(encoding="utf-8"))["font"] == font_mark()
if same_font:
    a, b, old, new = papers(TORA, fit=False)
    ra, rb = split(a)[1], split(b)[1]
    moved = [(x, y) for x, y in zip(ra, rb) if x != y]
    assert moved and any(x.startswith("<path") for x, _ in moved), "組み方を前の題で決めない時に図形が動く事を、この試験が拾えていない"
note = "" if same_font else "。この機械の字が控えと違うので、負の対照は見ていない"
print(f"ok 刷る紙の題から印を外しても部品は動かない: 玩具 {real_n} 種の型紙で、違うのは題の行だけ（この機械の字と決まった字の幅の両方）{note}")
