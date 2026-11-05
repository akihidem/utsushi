"""作り方の印（#261）。仮説ごとに「紙一枚」「折るだけ」「当時の材料」を出す。どれも上下の印ではない。

本人の言葉（11-05）「一枚の紙から作る選択肢もある」と、本人の決定「両方を別の印で持つ」による。名前と判定はエンジン（paper-to-toy の omochae.ways）とそろえる。
- one_sheet（紙一枚）: A4 1 枚に刷った紙だけで作れる。糊・はさみ・定規などの道具は使ってよい。ほかの材料（竹串・糸・粘土・テープなど）は使わない。
- fold_only（折るだけ）: 1 枚の紙を切らずに折るだけで作る。部品が 1 つで、外形が長方形、中の切り込みも穴も糊代も無く、折り線が 1 本以上ある。
- period（当時の材料）: 紙のほかの材料が全部、江戸の頃にもあった物の語の一覧に当たる。知らない物には付けない（#311）。本人の言葉「竹とか糸は江戸時代にもあったし使ったらよく再現できるということ」による、再現の良さの別の軸。

判断の芯:
- 印は雛形や記録に宣言させず、部品表（bom）・用意する物（materials）・部品（parts）から出す。宣言だと、部品を変えた時に印と食い違う。
- エンジンは形（form）ごとに出す。こちらは仮説ごとに寸法があるので、仮説の寸法で出す。
- 語の一覧はエンジンの物に、こちらの雛形にだけある材料（竹ひご・楊枝・つまようじ・紐）を足した。
"""
import argparse
import functools
import json
import re
import sys

from .compose import TEMPLATES
from .hypotheses import ROOT, load

# 紙一枚の印を外す材料の語。道具（のり・はさみ・定規など）は玩具の材料でないので入れない。
OTHER = re.compile(r"竹串|竹ひご|楊枝|つまようじ|割り?ピン|粘土|糸|紐|輪ゴム|テープ|ビーズ|割り箸|厚紙|ストロー|水よけ|ろう|鈴|玉")
# 江戸の頃にもあった材料の語。竹串と竹ひごは竹、楊枝とつまようじと割り箸は木。本人の言葉の竹と糸に、エンジンの一覧の木・鈴・玉を足した。
PERIOD = re.compile(r"竹串|竹ひご|楊枝|つまようじ|割り箸|糸|紐|鈴|玉")
# 江戸の頃に無かった、今の物で代えた材料の語。油粘土は当時の土や練り物の代わりで、物としては今の物なので、当時の材料に数えない（#311）。
MODERN = re.compile(r"油粘土|輪ゴム|テープ|割り?ピン|ビーズ|ストロー|厚紙|水よけ|ろう")
LABELS = (("one_sheet", "紙一枚"), ("fold_only", "折るだけ"), ("period", "当時の材料"))
NOTE = "紙一枚・折るだけ・当時の材料は、作り方の違いです。どの印も上下を表しません。"


def _is_paper(material):
    m = str(material)
    return "紙" in m and "厚紙" not in m and not OTHER.search(m.replace("紙", ""))


def fold_only(parts):
    """部品が 1 つで、外形が軸にそろった長方形、中の切り込みも穴も糊代も無く、折り線が 1 本以上ある。"""
    if len(parts) != 1:
        return False
    q = parts[0]
    xs = {round(x, 6) for x, _ in q.outline}
    ys = {round(y, 6) for _, y in q.outline}
    return len(q.outline) == 4 and len(xs) == 2 and len(ys) == 2 and not q.cuts and not q.holes and not q.glue and bool(q.valley or q.mountain)


def details(template_id, params):
    tpl = TEMPLATES[template_id]
    p = {**tpl.DEFAULTS, **params}
    rows, listed = tpl.bom(p), [str(m) for m in tpl.materials(p)]
    others = [r["name"] for r in rows if not _is_paper(r.get("material", ""))]
    for m in listed:
        for w in OTHER.findall(m):
            if w not in others and not any(w in o for o in others):
                others.append(w)  # 同じ語を 2 度数えない
    text = " ".join([str(r.get("material", "")) for r in rows] + listed)
    modern = sorted(set(MODERN.findall(text)))
    # 部品表の紙でない素材と、用意する物の文の中の材料の語を、全部一覧に当てる。どちらの一覧にも無い物は知らない物なので、印を付けない
    materials = [str(r.get("material", "")) for r in rows if not _is_paper(r.get("material", ""))] + [w for m in listed for w in OTHER.findall(m)]
    # 紙のほかの材料が要るなら「紙を折るだけ」にならない。部品表が 1 行でない時は部品が 1 つでないので、描く前に分かる（一覧の頁を開く時の重さ）
    return {"one_sheet": not others, "fold_only": not others and len(rows) == 1 and fold_only(tpl.parts(p)), "period": not modern and all(PERIOD.search(m) for m in materials),
            "other_materials": others, "modern_substitutes": modern}


def marks(template_id, params):
    d = details(template_id, params)
    return {k: d[k] for k, _ in LABELS}


def labels(marked):
    """付いている印の名前。決まった順で、付いていない印は出さない。"""
    return [name for key, name in LABELS if marked[key]]


def of_hypothesis(data, h):
    return details(h.get("template", data.get("template", "slider_fan")), h["params"])


@functools.lru_cache(maxsize=None)
def toy_labels(source_id):
    """玩具のどれかの仮説に付く印の名前。元の記録だけを見るので、頁を開くたびに数え直さない。"""
    data = load(source_id)
    found = [of_hypothesis(data, h) for h in data["hypotheses"] if h.get("params") is not None]
    return [name for key, name in LABELS if any(d[key] for d in found)]


def table():
    """全部の玩具の全部の仮説の印。"""
    out = []
    for path in sorted((ROOT / "data/hypotheses").glob("*.json")):
        data = load(path.stem)
        out += [{"source_id": path.stem, "hypothesis_id": h["id"], **of_hypothesis(data, h)} for h in data["hypotheses"]]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.ways", description="仮説ごとの作り方の印（紙一枚・折るだけ・当時の材料）を出す。どれも上下の印ではない")
    ap.add_argument("--json", action="store_true", help="JSON で出す")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    rows = table()
    if args.json:
        print(json.dumps(rows, ensure_ascii=False))
        return 0
    for r in rows:
        mark = "・".join(labels(r)) or "—"
        print(f"{r['source_id']} {r['hypothesis_id']} {mark} 材料: {'・'.join(r['other_materials']) or '紙だけ'}"
              f"{'（今の物で代えた: ' + '・'.join(r['modern_substitutes']) + '）' if r['modern_substitutes'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
