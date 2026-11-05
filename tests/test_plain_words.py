"""小学生・中学生の目で文を数える道具の試験（#317）。

本物の頁の残りの数は見ない。文の入れ替えが別の枝で進むので、数を固定すると、よい直しまで落としてしまう。
見本の頁で数え方の正しさを見て、本物の頁は開けて数えられる事だけを見る。
"""
import contextlib
import io
import os
import pathlib
import tempfile

_data = tempfile.TemporaryDirectory()
os.environ["OMOCHAE_DATA"] = _data.name

from web import plain_words as pw  # noqa: E402

SAMPLE = """<!doctype html><html><head><title>翻案の頁</title>
<style>.x::before{content:"復元"}</style></head><body>
<p>開く角だけの線の絵。どう開くかは描いていない。それを紙で確かめます。</p>
<p>これは、とても長い説明の文で、四十字を超えるところまで、わざと言葉を重ねて書いてあります。</p>
<p>仮説を紙で確かめます。ためしの案（仮説）も見ます。</p>
<blockquote>引用の中の翻案は数えない。</blockquote>
<div class="songs"><span>歌の中の検討は数えない。</span></div>
<div class="samples"><p class="sample">見本の声の端末は数えない。</p></div>
<ul><li>印刷する紙と、すぐ刷る紙</li><li>出版の版画と、次の版</li></ul>
<input placeholder="連絡先は書かないでください" aria-label="寸法">
<script>
// コメントの糊代は数えない
const a = '行程を見ます';
</script>
</body></html>"""

r = pw.census({"/見本": SAMPLE})
words = {(h["word"], h["where"]) for h in r["words"]}

# 語: 本文・題・入力欄の字・画面に出す JS の字を見る。CSS・JS のコメント・引用・歌・見本の声は見ない
for w in ("翻案", "連絡先", "寸法", "行程"):
    assert (w, "/見本") in words, w
for w in ("復元", "検討", "端末", "糊代"):
    assert (w, "/見本") not in words, w
# 語の形: 「印刷」「出版」「版画」に当てず、「刷る」と「版」だけに当てる
hits = {h["word"]: h["count"] for h in r["words"]}
assert hits["刷る"] == 1 and hits["版"] == 1, hits
# 文: です・ますでない説明の文を拾う。引用の文は拾わない
ends = [s["text"] for s in r["not_polite"]]
assert ends == ["開く角だけの線の絵。", "どう開くかは描いていない。"], ends
# 文: 40 字を超える文を拾う
assert [len(s["text"]) > 40 for s in r["long"]] == [True] and "わざと" in r["long"][0]["text"], r["long"]
assert r["sentences"] == 6, r["sentences"]

# 「仮説」が頁の最初で「ためしの案」と並ばない頁を拾う。並んでいる頁は拾わない
assert r["hypothesis_alone"] == ["/見本"], r["hypothesis_alone"]
ok = pw.census({"/並ぶ": "<p>ためしの案（仮説）を見ます。仮説は紙で確かめます。</p>", "/無い": "<p>紙で確かめます。</p>"})
assert ok["hypothesis_alone"] == [], ok
assert ok["words"] == [] and ok["not_polite"] == [] and ok["long"] == [], ok

# です・ますの形を広く受ける（断り・問い・かっこの閉じ）
for good in ("見ました。", "ありません。", "作りましょう。", "書いてください。", "動きますか？", "どうでしょうか。", "（紙で確かめます。）", "「作ります。」"):
    assert pw.census({"/": f"<p>{good}</p>"})["not_polite"] == [], good

# 表: 言いかえの欄に入れてよいのは本人が採った字だけ。まだの語は空にして、案を code に持たない
assert len({e["word"] for e in pw.TABLE}) == len(pw.TABLE)
filled = {e["word"]: e["plain"] for e in pw.TABLE if e["plain"]}
assert filled == {"連絡先": "住所・電話番号・メール", "上下はありません": "どれがえらい、ということはありません", "仮説": "ためしの案（仮説）", "正解": "正しい答えではありません"}, filled
assert not hasattr(pw, "PROPOSED")
# 内輪の言葉は #135 の表の受け持ち。同じ語を両方に書かない
assert not {e["word"] for e in pw.TABLE} & {"本人", "棚卸し", "雛形", "複写", "鍵", "型紙エンジン"}
# data の札の文に残る語も、言いかえの欄を空にして数える（案は本人の確認待ち）
for w in ("本文", "翻刻", "見込み", "未確認", "推定", "通例", "趣旨", "確度"):
    assert w in {e["word"] for e in pw.TABLE if not e["plain"]}, w

# 本物の頁: 全部の種類が開けて数えられる。頁を開くだけで記録の置き場に書かない
before = sorted(p.relative_to(_data.name) for p in pathlib.Path(_data.name).rglob("*.json"))
G = "NDL-1187053-R0000005-L"
pages = pw.collect([G])
for p in ("/", "/about", "/toys", "/gallery", "/zukan", f"/zukan/{G}", f"/toy/{G}", f"/toy/{G}/tsukuru", f"/toy/{G}/techo", "/loop", f"/loop/{G}"):
    assert p in pages and "</html>" in pages[p].lower(), p
assert pw.census(pages)["sentences"] > 50
assert sorted(p.relative_to(_data.name) for p in pathlib.Path(_data.name).rglob("*.json")) == before

# 命令: 既定は数を出すだけで 0。--strict は語か文が残っていれば 3。結果の紙を --out に書く
out = pathlib.Path(_data.name) / "plain-words.md"
with contextlib.redirect_stdout(io.StringIO()) as printed:
    assert pw.main(["--toy", G, "--out", str(out)]) == 0
    assert pw.main(["--toy", G, "--out", str(out), "--strict"]) == 3
assert "語" in printed.getvalue() and out.exists()
text = out.read_text(encoding="utf-8")
for w in ("## 語", "## です・ますでない文", "## 40 字を超える文", "連絡先"):
    assert w in text, w
# 紙の PDF は語だけを見る: 手順の言い切りをどうするかは決める点なので、文には数えない
assert pw.census({}, sheets={"H-A.pdf": "切る。折る。\n糊代を折ります。"})["sentences"] == 0
assert [(h["word"], h["where"]) for h in pw.census({}, sheets={"H-A.pdf": "切る。折る。\n糊代を折ります。"})["words"]] == [("糊代", "H-A.pdf")]
print("ok")
