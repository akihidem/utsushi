"""くずし字を読む頁の、歌の現代語訳と言葉の意味（data/kuzushi_notes。本人の言葉 11-08「ぐずし字を読む、のところは、現代語訳や関連する言葉の意味を書く。」）。

なぜ: 字は本人の決め（11-08「開いている PR は今の字で全部入れてよい」）で入れた案の字。意味は辞書と本（本人が渡した本のデータの、
有坂与太郎『日本玩具史 後編』の狂歌の注）から自分の言葉で短くし、出所の名を付けた。分からない所は「わかっていません」と書く。
見る線:
- 置き場の全部の json（御来迎と虎と、11-08 から 10 歌ずつ足す玩具）が置き場の形（gendaigo と words）で、意味には出所の名がある\n- 本人の決め（11-08「A にそろえる」）で読みにした歌の玩具は、頁に「読み: 1997 年の翻刻による」を出し、「確かめた人」を出さない（統括の決め 11-08）
- 玩具の動く仕組みを書かない（辞書の「御来迎」の項は仕組みを書いているので、その語義は引いていない）。「本人」「制作者」を書かない
- 言葉の意味の見出しの言葉は、頁に出る確かめた読みの中にある（読みの字は濁点を付けずに刷られているので、けれと → けれど として比べる）
- 頁に「現代語訳」と「言葉の意味」が出る。json の無い玩具には出ない
- 御来迎の確かめた読みは「怠らじ」（本人の決め 11-08「御来迎の歌の読みは「怠らじ」」）。活字と同じ字になったので、「字が違う所があります」の文は出ない
- 字は全部、英語の表とやさしい日本語の表にあり、やさしい日本語は全ての漢字にルビ（本人の言葉 11-07「ルビも全ての漢字にふる」）
"""
import json
import os
import pathlib
import re
import sys
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from web import i18n, kuzushi  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
# 注の json の無い玩具（10 歌ずつ足していくので、名指しにせず、注の無い玩具の頭を選ぶ）
PLAIN = next(p.stem for p in sorted((ROOT / "data/sources").glob("NDL-*.json"))
             if (ROOT / "data/hypotheses" / p.name).exists() and not (ROOT / "data/kuzushi_notes" / p.name).exists())
SOURCES = ("精選版 日本国語大辞典より", "デジタル大辞泉より", "字通より", "有坂与太郎『日本玩具史 後編』")
# 辞書の「御来迎」の項の、玩具の仕組みの言い方（学ぶ人の頁に仕組みの答えを出さない決まり）と、張子の虎の動き方の言い方
MECHANISM = ("竹筒", "糸の仕掛け", "仕掛け", "後光が開", "せり出", "下げると", "押し上げ", "押し出", "上下する", "おもり", "重り", "釣り合")
VOICE = str.maketrans({"と": "ど"})


def reading(sid):
    """頁の訳の元の読み。人が確かめた読みが 1 つあればそれ、無ければ本人の決め（11-08「A にそろえる」）で読みにした歌（decided_by）が 1 つ。"""
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    took = [e for e in src["transcription"]["entries"] if e.get("checked_by") and not e.get("rejected_by")]
    if not took:
        took = [e for e in src["transcription"]["entries"] if e.get("decided_by") and not e.get("rejected_by")]
    assert len(took) == 1, sid
    return "".join(took[0]["text"].split())


# 11-08 から、御来迎と虎のほかの玩具にも、歌の現代語訳と言葉の意味を 10 歌ずつ足す（本人の答え「この出し方でよい。」・統括の段取り）。
# 置き場の全部の json を同じ線で見る。同じ図の玩具は、出典の記録の全部に同じ字を置く（統括の決め 11-08）
NOTED = sorted(p.stem for p in (ROOT / "data/kuzushi_notes").glob("*.json"))
# 10 歌ずつ足した注の玩具の数が減っていない事（御来迎と虎の 2・最初の組 20・2 番目の組 16・3 番目の組 16・4 番目と 5 番目の組 25 の 79。図 53 は本人の決め待ちで、まだ入れていない）
assert G in NOTED and T in NOTED and len(NOTED) >= 79, (len(NOTED), "注の玩具が減った")
texts = []
for sid in NOTED:
    d = json.loads((ROOT / "data/kuzushi_notes" / f"{sid}.json").read_text(encoding="utf-8"))
    assert set(d) == {"gendaigo", "words"} and isinstance(d["gendaigo"], str) and d["gendaigo"].strip(), sid
    assert d["words"] and all(set(w) == {"word", "meaning"} for w in d["words"]), sid
    said = reading(sid)
    for w in d["words"]:
        assert any(s in w["meaning"] for s in SOURCES), ("意味に出所の名が無い", sid, w["word"])
        assert w["word"] in said or w["word"] in said.translate(VOICE), ("見出しの言葉が歌の読みに無い", sid, w["word"], said)
    every = d["gendaigo"] + "".join(w["word"] + w["meaning"] for w in d["words"])
    assert not [m for m in MECHANISM if m in every], ("仕組みの言い方", sid, [m for m in MECHANISM if m in every])
    assert "本人" not in every and "制作者" not in every, sid
    # 辞書の中身を手元で確かめられない言い切り（「辞書はこの歌を…例に挙げる」「…の呼び名にも使われた」）は書かない（別の目の確かめ 11-08・#661 の後）
    assert not [w for w in ("例として挙げて", "呼び名にも使われました") if w in every], (sid, "確かめられない辞書の中身の言い切り")
    # ふりがなの字は一覧で確かでない所があるので、「ふりがなは「…」」と言い切らない（別の目の確かめ 11-08・#677 の後）
    assert "ふりがなは「" not in every and "とふりがながあり" not in every, (sid, "ふりがなの言い切り")
    # 濁点の無い刷りは、確かめた所（1997 年の翻刻の字）までで言う。「にごる点を書かずに…と刷られています」と元の本の刷りを言い切らない
    # （別の目の確かめ 11-08・#686 の後。どの本の字かを名指して「1997 年の本では…と刷られています」と言う所は、写した字なので残す）
    assert "にごる点を書かずに" not in every, (sid, "刷りの言い切り")
    texts += [d["gendaigo"], *(x for w in d["words"] for x in (w["word"], w["meaning"]))]

# 頁: 2 つの見出しが出て、json の無い玩具には出ない
for sid in NOTED:
    html = kuzushi.page(sid)
    assert html.count('id="yomi-notes"') == 1 and "<h2>現代語訳</h2>" in html and "<h2>言葉の意味</h2>" in html, sid
assert 'id="yomi-notes"' not in kuzushi.page(PLAIN)

# 御来迎の読み: 「怠らじ」。活字と同じ字なので、活字の文と「字が違う所があります」は出さない
assert reading(G) == "御来迎拝むにつけて怠らじ朝な夕なに南無あめの鳥"
lines = " ".join(x["text"] for x in kuzushi.split_lines(json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))))
assert "字が違う所があります" not in lines and "怠けらじ" not in lines, lines
# 字が違う時は、前と同じに 2 文を出す（活字の字と確かめた読みが 1 字違う形を作って見る）
src = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
took = next(e for e in src["transcription"]["entries"] if e.get("checked_by") and not e.get("rejected_by"))
took["text"] = took["printed_text"].replace("怠らじ", "怠けらじ")
differ = " ".join(x["text"] for x in kuzushi.split_lines(src))
assert "字が違う所があります" in differ and took["printed_text"] in differ, differ
page = kuzushi.page(G, mine="御来迎")
assert "怠らじ" in page and "怠けらじ" not in page and "字が違う所があります" not in page

# 本人の決めで読みにした歌の玩具（人が確かめた読みが無い）: 頁の注の段に読みの出所の 1 行（genga.READ_A）を出し、「確かめた人」は出さない
# （頁に本人と出すと 1 字ずつ確かめたように読めて事実と違う・統括の決め 11-08）。出典の記録の出所の欄（source_note）に決めの事を書く
from web import genga  # noqa: E402

for sid in NOTED:
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    dec = [e for e in src["transcription"]["entries"] if e.get("decided_by") and not e.get("rejected_by")]
    checked = [e for e in src["transcription"]["entries"] if e.get("checked_by") and not e.get("rejected_by")]
    html = kuzushi.page(sid)
    if checked:
        assert genga.READ_A not in html, sid
        continue
    # A（1997 年の翻刻）か B（有坂の本の見出し。本人の答え 11-08「図 13 は B の読みでよい。」など）。出所の欄と頁の 1 行と並べる名を、読みにした本で言い分ける
    assert len(dec) == 1 and dec[0]["checked_by"] is None and dec[0]["set"] in ("A", "B"), sid
    book, line, name = (("1997 年の翻刻", genga.READ_A, "1997 年の翻刻の読み") if dec[0]["set"] == "A"
                        else ("『日本玩具史 後編』", genga.READ_B, "『日本玩具史 後編』の見出しの読み"))
    assert book in dec[0]["source_note"] and "1 字ずつの確かめはまだ" in dec[0]["source_note"], sid
    assert line in html, ("読みの出所の 1 行", sid)
    after = kuzushi.page(sid, mine="□")
    assert "確かめた人" not in after and line in after and name in after, ("書いた後の頁に確かめた人を出さない", sid)
    texts.append(reading(sid))
texts += [genga.READ_A, genga.READ_B]

# 英語とやさしい日本語の表（鍵は頁の字の形）
en, easy = i18n.table("en"), i18n.table("easy")
KANJI = re.compile(r"[一-龥々]")
for t in texts + [reading(G)]:
    k = i18n.key_of(t)[0]
    assert k in en, ("英語の表に無い", k[:40])
    assert k in easy, ("やさしい日本語の表に無い", k[:40])
    assert not KANJI.findall(i18n.RUBY.sub("", easy[k])), ("ルビの無い漢字", k[:40], KANJI.findall(i18n.RUBY.sub("", easy[k])))
assert "御来迎拝むにつけて怠けらじ朝な夕なに南無あめの鳥" not in en, "前の読みの鍵は外した"
print(f"ok 現代語訳と言葉の意味 {len(NOTED)} 玩具（頁の字 {len(texts)}）・御来迎の読みは怠らじ・決めで読みにした歌は 1997 年の翻刻の 1 行")
