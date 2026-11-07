"""作り方の印（#53）。形ごとに「紙一枚」「折るだけ」「当時の材料」を出す。どれも優劣の印ではない。

制作者の言葉（2026-11-05）「一枚の紙から作る選択肢もある」と、制作者の決定 (c)「両方を別の印で持つ」による。
- one_sheet（紙一枚）: A4 1 枚に刷った紙だけで作れる。糊・はさみ・定規・カッター・下敷き・目打ちは道具なので使ってよい。
  ほかの材料（竹串・割ピン・粘土・糸・輪ゴム・テープ・厚紙など）は使わない。
- fold_only（折るだけ）: 1 枚の紙を切らずに折るだけで作る。部品が 1 つで、外形が長方形、中の切り込みも穴も糊代も無く、折り線が 1 本以上ある。
- period（当時の材料）: 紙のほかの材料が全部、江戸の頃にもあった物の語の一覧（竹・糸・紐・木・鈴・玉）に当たる。知らない物には付けない。
  制作者の言葉「竹とか糸は江戸時代にもあったし使ったらよく再現できるということ」による、再現の良さの別の軸。
  紙一枚の印は優劣の印ではない。今の物で代えた材料（輪ゴム・テープ・割ピン・ストローなど）は modern_substitutes に出す。
- premise（材料の前提）: 制作者の言葉（2026-11-07）「エンジン、紙だけで再現と言ったかも。竹、木、糸、布、接着剤、なるべくは樹脂、
  金属は使わずに考えるようにして設計を再考してもいいかもしれない」による、設計を考え直す所を見る軸（落とす検査ではない）。
  紙のほかの材料を、使ってよい（紙・竹・木・糸・布・接着剤。油粘土も、制作者の言葉「油粘土も使ってよい」で使ってよい）／
  なるべく使わない（金属・樹脂）／一覧に無い（ろう・油粘土のほかの粘土・知らない材料など、
  どちらとも決まっていない物）に分け、部品表と用意する物の文を別の一覧で出す。道具（はさみ・カッター・目打ち・硬貨など）は数えない。
判断の芯:
- 印は雛形に宣言させず、部品表（bom）・用意する物（materials）・部品（parts）から出す。宣言だと、部品を変えた時に印と食い違う。
- 材料は、部品表の素材と、用意する物の文の両方で見る。部品表に載らない物（割ピン・テープなど）が、用意する物にだけ書かれる雛形があるため。
"""
import json
import re
import sys

from .__main__ import Parser
from .compose import TEMPLATES
from .sheets import is_sheet, reading_of, source_of

# 紙一枚の印を外す材料の語。道具（糊・はさみ・定規・カッター・下敷き・目打ち・鉛筆・ニッパー・紙やすり、
# 硬さを測るのに下げる硬貨）は、玩具の材料でないので入れない。
OTHER = re.compile(r"竹串|割り?ピン|粘土|糸|輪ゴム|テープ|ビーズ|割り箸|厚紙|ストロー|水よけ|ろう|鈴|玉")


# 江戸の頃にもあった材料の語。竹串と竹ひごは竹、楊枝とつまようじと割り箸は木。制作者の言葉の竹と糸に、木・鈴・玉を足した。
PERIOD = re.compile(r"竹串|竹ひご|楊枝|つまようじ|割り箸|糸|紐|鈴|玉")
# 江戸の頃に無かった、今の物で代えた材料の語。油粘土は当時の土や練り物の代わりで、物としては今の物なので、当時の材料に数えない。
MODERN = re.compile(r"油粘土|輪ゴム|テープ|割り?ピン|ビーズ|ストロー|厚紙|水よけ|ろう")


def _params(tpl, form):
    p = {**tpl.DEFAULTS, tpl.FORM: form}
    return tpl.filled(p) if hasattr(tpl, "filled") else p


def _is_paper(material):
    m = str(material)
    return "紙" in m and "厚紙" not in m and not OTHER.search(m.replace("紙", ""))


def fold_only(parts):
    """部品が 1 つで、外形が軸にそろった長方形、中の切り込み（cuts・round_cuts）も穴（holes）も糊代（glue）も無く、折り線が 1 本以上ある。"""
    if len(parts) != 1:
        return False
    q = parts[0]
    xs = sorted({round(x, 6) for x, _ in q.outline})
    ys = sorted({round(y, 6) for _, y in q.outline})
    rect = len(q.outline) == 4 and len(xs) == 2 and len(ys) == 2
    return rect and not q.cuts and not q.round_cuts and not q.holes and not q.glue and bool(q.valley or q.mountain)


# 材料の前提の語（制作者の言葉 2026-11-07）。当時の材料（PERIOD・MODERN）と分けるのは、物差しが違うため:
# 厚紙は今の物でも紙なので使ってよい側、鈴は当時の物でも金属なので避ける側。
# 語は長い物から当てる（「セロハンテープ」をテープより先に、「油ねんど」を、ほかの語より先に）。
PREMISE_WORDS = {
    "metal": ("割りピン", "割ピン", "針金", "鈴", "クリップ", "ホチキス", "画鋲", "釘", "ワイヤー"),
    "resin": ("セロハンテープ", "梱包テープ", "テープ", "ストロー", "ビーズ", "消しゴム", "輪ゴム", "プラ板"),
    # 樹脂でも金属でもないが、使ってよい物の一覧にも無い物。使うかは、これから決める。油粘土のほかの粘土（石粉粘土など）も
    # ここに入る（使ってよいとされたのは油粘土だけ。広い語の「粘土」を使ってよい側に置くと、樹脂粘土なども通った。見直しの指摘）
    "unlisted": ("粘土", "ねんど", "ろう"),
    # 油粘土は、制作者の言葉（2026-11-07）「油粘土も使ってよい」で使ってよい側（重り・台・栓・玉に広く使っている）。
    # 語は長い物から当てるので、「油粘土」は「粘土」より先に当たる
    "ok": ("竹串", "竹ぐし", "竹ひご", "楊枝", "つまようじ", "割り箸", "木", "糸", "紐", "布", "のり", "接着剤", "厚紙", "紙",
           "油粘土", "油ねんど"),
}
# 材料の名の頭に付いて、その材料の分けを決める語（樹脂粘土・樹脂ねんど・ビニールテープ・アルミの針金・金属の軸など）。
# 頭の語に続く名の字（かな・カタカナ・漢字。助詞の と・や・か・を・に・で・は・が は区切り）を 1 つの材料として、頭の語の分けに入れる。
# 2 つの語が入った名を、別々の分けに 2 度数えないため（見直しの指摘: 名を 1 つずつ足すと、樹脂ねんどのような書き方の揺れを取りこぼした）。
# ただし、もう一方の避ける側の語（樹脂の頭なら金属の語、金属の頭なら樹脂の語）の手前では止める。数字・記号・空白でも止める
# （見直しの指摘: 何でも飲み込むと、「樹脂＋針金」の針金を見落とし、「樹脂粘土3g」と「樹脂粘土5g」を別の物として残した）
PREMISE_HEADS = {"樹脂": "resin", "プラスチック": "resin", "ビニール": "resin", "発泡": "resin", "金属": "metal", "アルミ": "metal"}
_NAME_CHAR = "(?![とやかをにではが])[ぁ-んァ-ヶー一-鿿々]"


def _alt(words):
    return "|".join(sorted(map(re.escape, words), key=len, reverse=True))


def _head_pattern(cls, other):
    heads = [h for h, k in PREMISE_HEADS.items() if k == cls]
    stop = _alt(list(PREMISE_WORDS[other]) + [h for h, k in PREMISE_HEADS.items() if k == other])
    return f"(?:{_alt(heads)})(?:(?!{stop}){_NAME_CHAR})*"


_PREMISE = re.compile(_head_pattern("resin", "metal") + "|" + _head_pattern("metal", "resin") + "|"
                      + _alt({w for ws in PREMISE_WORDS.values() for w in ws}))
_PREMISE_CLASS = {w: k for k, ws in PREMISE_WORDS.items() for w in ws}


def _premise_class(word):
    """当たった語の分け。頭の語で始まる名は、頭の語の分け。"""
    return next((k for h, k in PREMISE_HEADS.items() if word.startswith(h)), None) or _PREMISE_CLASS[word]


def _premise_name(word):
    """出す名。頭の語で始まる名の終わりの「の」は落とす（「樹脂の針金」の樹脂の側を「樹脂」と出す）。"""
    return word.rstrip("の") if any(word.startswith(h) for h in PREMISE_HEADS) else word
# 道具の語は、材料の前提に数えない（玩具の材料でない）。10 円玉は、腕や弓の硬さを確かめる重りで、玩具に入らない
PREMISE_TOOLS = re.compile(r"はさみ|定規|カッター|ニッパー|目打ち|下敷き|まち針|えんぴつ|鉛筆|ペン|紙やすり|時計|洗面器|皿|10 円玉|硬貨")


def _premise_of(texts, unknown_unlisted):
    """文の並びから、材料の前提の語を分けて集める（同じ語は 1 度。道具の語は先に外す）。unknown_unlisted なら、どの語にも
    当たらない文を丸ごと一覧に無い物に入れる。部品表の行（紙の行も、いくつかの材料が混ざった行も全部）に使う。
    1 行にどれかの語が当たれば、同じ行の知らない材料は出さない（README の限り）。用意する物の文は、知っている語だけを見る。"""
    out = {"metal": [], "resin": [], "unlisted": []}
    for text in texts:
        t = PREMISE_TOOLS.sub(" ", str(text))
        words = _PREMISE.findall(t)
        if not words and unknown_unlisted and t.strip():
            out["unlisted"].append(str(text))
        for w in words:
            k, name = _premise_class(w), _premise_name(w)
            if k != "ok" and name not in out[k]:
                out[k].append(name)
    return out


def premise(template_id, form):
    """材料の前提の印。部品表（bom）と用意する物（prep）を別の一覧で出す。今のデータでは、作る途中だけ使う物（仮に留めるテープ
    など）と玩具に残る物を見分けられないので、どちらに書かれたかだけを出す。
    within は、知っている語の中に金属・樹脂・一覧に無い物が無い時（見直しの指摘で、意味をこう決めた）。知らない材料は、部品表の
    行がどの語にも当たらない時だけ丸ごと一覧に無い物に出す。知っている語と同じ行に混ざった知らない材料と、用意する物の文の中の
    知らない材料は見落とす（自由な文から材料を全部は拾えない。今の型紙の部品表に、どの語にも当たらない行が無い事は試験で見る）。"""
    tpl = TEMPLATES[template_id]
    p = _params(tpl, form)
    # 部品表は紙の行も含めて全部を当てる。紙の見分け（_is_paper）は紙一枚の印の古い語の一覧を使うので、先に外すと
    # 「紙と針金」のような混ざった行の針金を見落とした（見直しの指摘）。紙だけの行は「紙」に当たり、何も出さない
    bom = _premise_of([r.get("material", "") for r in tpl.bom(p)], True)
    prep = _premise_of(tpl.materials(p), False)
    return {"within": not any(d[k] for d in (bom, prep) for k in d), "bom": bom, "prep": prep}


def details(template_id, form):
    tpl = TEMPLATES[template_id]
    p = _params(tpl, form)
    rows = tpl.bom(p)
    others = [r["name"] for r in rows if not _is_paper(r.get("material", ""))]
    for m in tpl.materials(p):
        for w in OTHER.findall(str(m)):
            if w not in others and not any(w in o for o in others):
                others.append(w)  # 同じ語を 2 度数えない
    text = " ".join([str(r.get("material", "")) for r in rows] + [str(m) for m in tpl.materials(p)])
    modern = sorted(set(MODERN.findall(text)))
    # 部品表の紙でない素材と、用意する物の文の中の材料の語を、全部一覧に当てる。どちらの一覧にも無い物は知らない物なので、印を付けない
    materials = [str(r.get("material", "")) for r in rows if not _is_paper(r.get("material", ""))] + [w for m in tpl.materials(p) for w in OTHER.findall(str(m))]
    return {"one_sheet": not others, "fold_only": fold_only(tpl.parts(p)), "period": not modern and all(PERIOD.search(m) for m in materials),
            "other_materials": others, "modern_substitutes": modern}


def marks(template_id, form):
    d = details(template_id, form)
    return {"one_sheet": d["one_sheet"], "fold_only": d["fold_only"], "period": d["period"]}


def table():
    """全部の雛形の全部の形の印。サイトの絞り込みに使う。
    sheet は、その形が玩具の型紙の 1 枚か（制作者の決定「玩具 1 つに型紙 1 枚」・omochae.sheets）。サイトは sheet の行だけを
    型紙として出す。別の読みの行（sheet が false）も消さずに残し、reading_of で型紙の形を指す（試行錯誤のヒントに使える）。
    行を消さないのは、今の一覧を読む側（サイト）の形を壊さず、足した欄で絞れるようにするため。"""
    return [{"template": tid, "form": str(f), "source_id": source_of(tid, f), "sheet": is_sheet(tid, f),
             "reading_of": reading_of(tid, f), **details(tid, f), "premise": premise(tid, f)}
            for tid, t in sorted(TEMPLATES.items()) for f in t.FORMS]


def _premise_text(pr):
    """文の一覧に出す、材料の前提の外の物（部品表と用意する物を合わせて、分けの名ごとに）。"""
    if pr["within"]:
        return ""
    names = {"metal": "金属", "resin": "樹脂", "unlisted": "一覧に無い"}
    got = [f"{names[k]} {'・'.join(dict.fromkeys(pr['bom'][k] + pr['prep'][k]))}" for k in names if pr["bom"][k] or pr["prep"][k]]
    return "  材料の前提の外: " + "／".join(got)


def main(argv=None):
    ap = Parser(prog="omochae.ways", description="形ごとの作り方の印（紙一枚・折るだけ・当時の材料・材料の前提）を出す。どれも優劣の印ではない")
    ap.add_argument("--json", action="store_true", help="JSON で出す（サイトの絞り込みに使う）")
    args = ap.parse_args(argv)
    t = table()
    if args.json:
        print(json.dumps(t, ensure_ascii=False))
        return 0
    for r in t:
        mark = "・".join(n for n, k in (("紙一枚", "one_sheet"), ("折るだけ", "fold_only"), ("当時の材料", "period")) if r[k]) or "—"
        print(f"{r['template']:20s} {r['form']:12s} {mark:18s} 材料: {'・'.join(r['other_materials']) or '紙だけ'}"
              f"{'（今の物で代えた: ' + '・'.join(r['modern_substitutes']) + '）' if r['modern_substitutes'] else ''}"
              f"{_premise_text(r['premise'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
