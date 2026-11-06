"""ループ1（Issue #335）: 取り下げの時に、文が話した字の引用かを見分ける比べ方（records._quotes）。

材料は tests/quote_cases.json（手で作った例で、実在の人の話でも、本物の Claude の文でもない）。ここで固定するのは比べ方の振る舞いで、
数は本物の文の取りこぼしの率ではない。要約（E）はどの比べ方でも拾えないので、Claude が書いた文は引用の有無によらず消す（records._scrub_quotes）。
比べ方: 話した字の 6 字の一部が写っていれば引用。6 字以下の話は、4 字以上なら語尾 1 字を落とした全部（活用の違いを拾う）、4 字未満はそのまま全部。1 字は読まない。字の幅と空白はそろえる。
"""
import json
import pathlib

from omochae import records

CASES = json.loads((pathlib.Path(__file__).resolve().parent / "quote_cases.json").read_text(encoding="utf-8"))
HIT = lambda said, text: records._quotes(text, [records._flat(said)])  # noqa: E731


def found(form, cases=None):
    """その形の文のうち、引用と読めた数と、その形の文の数。"""
    rows = [(c["said"], c["forms"][form]) for c in (cases or CASES["cases"]) if form in c["forms"]]
    return sum(1 for said, text in rows if HIT(said, text)), len(rows)


assert len(CASES["cases"]) == 28
assert found("A") == (28, 28), "全文の引用は全部拾う"
assert found("B") == (20, 20), "長い一部の引用は全部拾う"
assert found("C") == (6, 20), "短い語句の一部を拾う（短すぎる語句まで拾うと、関わりの無い文を消す）"
assert found("D") == (23, 28), "活用を変えた写しを拾う"
short = [c for c in CASES["cases"] if len(records._flat(c["said"])) <= 8]
assert found("D", short) == (len(short), len(short)), "短い話の活用違いも拾う（例: 紙が破れた → 紙が破れている）"
assert found("E") == (0, 28), "要約は比べ方では拾えない（Claude の文を全部消す理由）"

# 関わりの無い文を、引用と読まない（消し過ぎない）
neutral = CASES["neutral_reading"] + CASES["neutral_toy_text"]
assert len(neutral) == 54
wrong = [(c["said"], text) for c in CASES["cases"] for text in neutral if HIT(c["said"], text)]
assert wrong == [], wrong[:5]  # 28 × 54 = 1512 組で誤り 0

# 決まりの端
assert HIT("紙が破れた", "紙が破れている"), "6 字以下は語尾を落として見る"
assert HIT("三年生の弟には", "三年生の弟に聞いた"), "7 字の話は 6 字の一部で見る"
assert HIT("筒が固い", "筒が固かった"), "語尾 1 字を落とす"
assert not HIT("開く", "開かない") and HIT("開く", "開くと思う"), "4 字未満はそのまま全部"
assert not HIT("紙", "紙が開いた"), "1 字は読まない"
assert HIT("ABCDEFGH", "ＡＢＣＤ　ＥＦＧＨと話した"), "字の幅と空白をそろえて比べる"
assert not HIT("短い考え", "短い話です"), "関わりの無い文"
print("ok")
