"""英語の言葉の決め（本人の決め 11-08「英語の『作る』は make でよい・用語の対応も推しのとおり」）を、訳の表で見る。

決めの元: grove の state/english-review-20261107.md の 1（make と craft）と 2（用語の対応）・9 の推し（玩具の名は日本語の名の訳・引用符は “ ” ’）。
後から足した字が前の言い方に戻ると、頁ごとに同じ物が別の英語で出るので、ここで止める。
本人の言葉と決めの記録（鍵に「本人」か「」がある字）と、独立した引用（原文＋英訳の値）は、人の字の英訳なので、言葉の決めの外に置く（英語の引用の決め: 窓口の決め 11-07）。
"""
import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from web.toys import sources  # noqa: E402

table = json.loads((ROOT / "data/i18n/en.json").read_text(encoding="utf-8"))["strings"]
# 独立した引用（値が原文の字で始まり、英訳を添える形。英語の引用の決め (a)）も、人の言葉の英訳なので外に置く
own = lambda k, v: "本人" in k or "「" in k or v.startswith(k)  # noqa: E731
vals = {k: v for k, v in table.items() if v != "=" and not own(k, v)}

# 1. make と craft: 手で作るのは make。craft は決まった名詞だけ（papercraft・craft knife・craftsperson / craftspeople）
CRAFT = re.compile(r"\bcraft(?!s?(?:person|people)\b| knife\b)", re.I)
bad = [k for k, v in vals.items() if CRAFT.search(v.replace("papercraft", ""))]
assert not bad, ("craft を動詞か道しるべに使っている", bad[:5])

# 2. 用語の対応（1 つの日本語に 1 つの英語）
OLD = {
    r"\bIdea [A-Z]\b": "仮説の札は Guess A",
    r"\btrial (?:plan|idea)s?\b": "仮説は guess",
    r"\[Guess\]": "〔推測〕は [Speculation]",
    r"\btweak": "工夫は what you changed",
    r"\bsteps sheet": "手順の紙は instruction sheet",
    r"\bafter-trying sheet": "試した後の紙は results sheet",
    r"\bswa(?:y|ys|yed|ying)\b": "虎の首は swing",
}
for rx, why in OLD.items():
    bad = [k for k, v in vals.items() if re.search(rx, v, re.I)]
    assert not bad, (why, bad[:5])
assert table["揺れた"] == "It swung" and table["揺れない"] == "It did not swing", "札は It moved と同じ形"

# 3. 玩具の英語の名は 1 つ（日本語の名の訳）。toys.json の名と、表の題（図・作りながら見る・型紙・手帖・組み方）が同じ
names = json.loads((ROOT / "data/en/toys.json").read_text(encoding="utf-8"))["toys"]
TITLE = {"の図": r"^Picture: (.*)$", " · 作りながら見る": r"^(.*) · Make while you watch$", " · 手帖": r"^(.*) · Notebook$",
         " 仮説 A の型紙": r"^(.*): Guess A template$", ": 組み方": r"^(.*): how to assemble$"}
for sid in sources():
    ja, name = hypotheses.load(sid)["toy"], names.get(sid, {}).get("name")
    if not name:
        continue
    for suf, rx in TITLE.items():
        v = table.get(ja + suf)
        if v is not None:
            m = re.match(rx, v)
            assert m and m.group(1) == name, ("玩具の名が頁ごとに違う", ja + suf, v, name)

# 4. 引用符: 語の中の ' は ’（同じ名が頁ごとに ' と ’ で揺れないため）
bad = [k for k, v in vals.items() if re.search(r"[A-Za-z]'[A-Za-z]", v)]
assert not bad, ("語の中の ' が残る", bad[:5])
bad = [sid for sid, o in names.items() if re.search(r"[A-Za-z]'[A-Za-z]", o.get("name", "") + o.get("intro", ""))]
assert not bad, ("toys.json の語の中の ' が残る", bad[:5])
# 5. 本人の言葉と独立した引用の英訳でも、仮説は guess・工夫は what you changed（窓口の決め 11-08「仮説は guess・工夫は what you changed にそろえる」）。
#    字の意味は替えない。英訳の部分（引用の形なら原文の後）だけを見る
def english(k, v):
    return v[len(k):] if v.startswith(k) else v


# 見るのは本人の言葉と決めの記録（鍵に「本人」）と独立した引用（原文＋英訳）。「」で語を引くだけの頁の字（釦の名・語の名）は 2 で見ている
for k, v in table.items():
    if v == "=" or not ("本人" in k or v.startswith(k)):
        continue
    e = english(k, v)
    if "仮説" in k:
        assert "guess" in e.lower() and not re.search(r"\b[Ii]dea [A-Z]\b", e), ("本人の言葉の英訳でも仮説は guess", k)
    if "工夫" in k:
        assert not re.search(r"\btweak", e, re.I), ("本人の言葉の英訳でも工夫は what you changed", k)

# 6. 版の番号: 鍵の v{n} の組と、英語（引用の形なら英訳の部分）の v{n} の組が同じ（窓口の決め 11-08「版番号の取り違えは直す」）。
#    英訳が別の版を言うと、どの紙の事かを取り違えるため（前に「撮影は v{3} のまま」が v{0} と訳されていた）
VER = re.compile(r"v\{\d+\}")
for k, v in table.items():
    if v == "=" or not VER.search(k):
        continue
    assert set(VER.findall(k)) == set(VER.findall(english(k, v))), ("版の番号が鍵と英語で違う", k, english(k, v))

# 7. 11 月のワークショップは 4 日（11-04〜07）あるので複数（窓口の決め 11-08「ワークショップの英語は複数形 workshops」）
bad = [k for k, v in table.items() if re.search(r"\bNovember workshop\b(?!s)", v)]
assert not bad, ("11 月のワークショップは workshops", bad[:5])
# 8. 玩具の名は、題のほか、前後の道・頁へもどる・くずし字と図鑑の頁の題・一覧の名でも toys.json の名（統括の気づき 11-08: 頁ごとに名が揺れた）
from web.i18n import key_of  # noqa: E402

for sid in sources():
    ja, name = hypotheses.load(sid)["toy"], names.get(sid, {}).get("name")
    jk = key_of(ja)[0]
    if not name or "{" in jk:  # 名の中の数が頁で替わる玩具（「（2つ目）」）は、ここでは見ない
        continue
    for k in (jk, f"← {jk}", f"{jk} →", f"{jk}の頁へもどる", f"くずし字を読む · {jk} · うつし", f"図鑑 · {jk} · うつし", f"{jk} · うつし"):
        v = table.get(k)
        if v is not None and v != "=":
            assert name.lower() in v.lower(), ("玩具の名が toys.json と違う", k, v, name)

# 9. 御来迎は Goraigo（本人が採った INTRO と同じ字。Goraigō と揺れていた）
bad = [k for k, v in table.items() if "Goraigō" in v]
assert not bad, ("御来迎は Goraigo", bad[:5])

# 10. 作例の報告の玩具の一覧（「いろいろな玩具（…）」）の名は、一覧の日本語の名と同じ玩具の toys.json の名（の頭）。日の付く行と付かない行の両方
base = {}
for sid in sources():
    ja, name = hypotheses.load(sid)["toy"], names.get(sid, {}).get("name")
    if name:
        base.setdefault(re.split(r"[（(]", ja)[0], re.split(r" \(", name)[0])
for k, v in table.items():
    m = re.search(r"いろいろな玩具（([^）]*)）", k)
    if not m or v == "=":
        continue
    for w in re.split(r"[・、]", m.group(1).replace("など", "")):
        if w in base:
            assert base[w].lower() in v.lower(), ("作例の一覧の玩具の名が toys.json と違う", k, w, base[w])
print("ok 英語の言葉の決め: make と craft・用語の対応・玩具の名が 1 つ（題・前後の道・作例の一覧）・Goraigo・引用符・本人の言葉の英訳の用語・版の番号・workshops")
