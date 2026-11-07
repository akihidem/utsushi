"""序の頁を「このサイトについて」の頁にする（本人のサイトレビュー 11-07 午後の 1・2・3、窓口の決め、本人「案のままでよい」）。

見る事:
1. 節の並び: 作った人の言葉 → なぜ → なぜ紙の型紙なのか → AI がしている事 → うつしと paper to toy（どれも 1 回）。前からの節は並べ替えない
2. 作った人の言葉の節の 1 つ目が思いの核の引用で、その後に 2 文が順に続き、前からの引用（WORDS）はその後
3. なぜ紙の型紙なのか の 4 文と、AI がしている事 の 2 文が、それぞれの節の中に順に出る。その間に学びの輪の段（見出しなし・本人の言葉 11-07 夕）が 1 回
4. 頁の見出しは「うつし」のまま。「あなたにしかない深さ」の字を出さない（窓口の決め）。頭の道の並びの後・CONCEPT の前に大前提の 3 段（本人の言葉 11-07 夜「入れる」）
5. README の頭の後の最初の節（うつしと paper to toy）に、思いの核の引用・その後の 2 文・なぜ紙の型紙なのか の 2 文（3D プリンタと比べる文と、型紙が直る文）
"""
import html
import os
import pathlib
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import about  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def esc(t):
    return html.escape(t, quote=False)


for k in ("tenji", "zine"):
    h = about.page(k)
    # 1. 節の並び
    heads = ["作った人の言葉", "なぜ", about.KAMI_HEAD, about.AI_HEAD, about.ENGINE_HEAD]
    marks = [f"<h2>{esc(t)}</h2>" for t in heads]
    assert all(h.count(m) == 1 for m in marks), (k, [h.count(m) for m in marks])
    at = [h.index(m) for m in marks]
    assert at == sorted(at), (k, "節の並び", at)
    # 2. 作った人の言葉の節
    sec = h[at[0]:at[1]]
    core = f"<blockquote>「{esc(about.CORE)}」</blockquote>"
    first_word = f"<blockquote>「{esc(about.WORDS[0])}」</blockquote>"
    assert core in sec and first_word in sec, (k, "思いの核と前からの引用")
    seq = [sec.index(core)] + [sec.index(f'<p class="lead">{esc(t)}</p>') for t in about.CORE_AFTER] + [sec.index(first_word)]
    assert seq == sorted(seq) and sec.index(core) < sec.index("<blockquote>", sec.index(core) + 1), (k, "思いの核が 1 つ目・2 文が続く", seq)
    # 3. なぜ紙・AI の節の中身
    for i, lines in ((2, about.KAMI), (3, about.AI_LINES)):
        part = h[at[i]:at[i + 1]]
        pos = [part.index(f'<p class="lead">{esc(t)}</p>') for t in lines]
        assert pos == sorted(pos), (k, heads[i])
    assert len(about.KAMI) == 4 and len(about.AI_LINES) == 2
    # 学びの輪の段: なぜ紙の節の後・AI の節の前に 1 回。見出しは付けない。字は本人が採った案 1 のまま
    # 文の後に学びの輪の図（UX の担当の部品 loop_figure.svg()。部品がまだ無い木では文だけ）
    try:
        from web import loop_figure
        fig = loop_figure.svg()
    except ImportError:
        fig = ""
    # 図がある時は、見出しに 1 本の輪の名（11-08 の組み直し）
    head = f'<h2>{esc(loop_figure.NAME)}</h2>' if fig else ""
    manabi = f'<section class="sec" id="manabi">{head}<p class="lead">{esc(about.MANABI)}</p>{fig}</section>'
    assert h.count(manabi) == 1 and at[2] < h.index(manabi) < at[3], (k, "学びの輪の段の置き場（文の後に図）")
    # 11-08 から本人の答え「字 1 と絵 A。」の字。のこすの頁の輪の節（loop_figure.ADOPTED）と同じ文
    assert about.MANABI == loop_figure.ADOPTED and about.MANABI.startswith("型紙は、AI が考えた ためしの案（仮説）です。"), about.MANABI
    # 大前提の 3 段（本人の言葉 11-07 夜「入れる」）: 頁の頭の道の並び（English の道）のすぐ後・CONCEPT の前に、この順で 1 回ずつ
    marks3 = [f'<p class="lead daizen">{esc(t)}</p>' for t in about.PREMISE]
    assert 'class="lead premise"' not in h, (k, "皮の premise の札の見た目を拾わない")
    assert len(about.PREMISE) == 3 and all(h.count(m) == 1 for m in marks3), (k, "大前提の 3 段")
    pos3 = [h.index(m) for m in marks3]
    assert h.index('href="/en">English</a></p>') < pos3[0] < pos3[1] < pos3[2] < h.index(f'<p class="concept">{esc(about.CONCEPT)}</p>'), (k, "大前提の置き場")
    # 4. 見出しとテーマの字
    assert "<h1>うつし</h1>" in h, k
    assert "あなたにしかない深さ" not in h, k

# 5. README の「作る気持ち」と「なぜ紙の型紙か」の節（本人の言葉 11-08「うつしのリードミー、エンジンが合流してぐちゃぐちゃ…優勝できる形にしよう」で、
# 前の「うつしと paper to toy」の節は README から外し、エンジンの話は engine/README.md へつなぐ。思いの核は「作る気持ち」の節（standing-decisions 164 行の言葉だけ）、
# なぜ紙の 2 文は「なぜ紙の型紙か」の節に、序の頁と同じ字で置く。核の後の 2 文は README には置かない（作る気持ちの節は 164 行の言葉だけの決め・統括 11-08）
readme = (ROOT / "README.md").read_text(encoding="utf-8")


def section(head):
    a = readme.index(head + "\n")
    return readme[a:readme.index("\n## ", a + 3)]


feel, kami = section("## 作る気持ち"), section("## なぜ紙の型紙か")
assert f"> {about.CORE}（本人の言葉 11-07）" in feel, "README の思いの核"
assert about.README_KAMI == (about.KAMI[1], about.KAMI[3])
assert f"{about.KAMI_HEAD}: " + "".join(about.README_KAMI) in kami, "README のなぜ紙の 2 文"
assert readme.index("## 作る気持ち") < readme.index("## なぜ紙の型紙か") < readme.index("## 型紙を作るエンジン"), "README の並び"
assert f"## {about.ENGINE_HEAD}" not in readme and "あなたにしかない深さ" not in readme
print("ok このサイトについて の頁（節の並び・思いの核と 2 文・なぜ紙の 4 文・AI の 2 文・見出しはうつし・README の頭の後の節）")
