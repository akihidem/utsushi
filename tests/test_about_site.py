"""序の頁を「このサイトについて」の頁にする（本人のサイトレビュー 11-07 午後の 1・2・3、窓口の決め、本人「案のままでよい」）。

見る事:
1. 節の並び: 作った人の言葉 → なぜ → なぜ紙の型紙なのか → AI がしている事 → うつしと paper to toy（どれも 1 回）。前からの節は並べ替えない
2. 作った人の言葉の節の 1 つ目が思いの核の引用で、その後に 2 文が順に続き、前からの引用（WORDS）はその後
3. なぜ紙の型紙なのか の 4 文と、AI がしている事 の 2 文が、それぞれの節の中に順に出る。その間に学びの輪の段（見出しなし・本人の言葉 11-07 夕）が 1 回
4. 頁の見出しは「うつし」のまま。「あなたにしかない深さ」の字を出さない（窓口の決め）
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
    manabi = f'<section class="sec" id="manabi"><p class="lead">{esc(about.MANABI)}</p></section>'
    assert h.count(manabi) == 1 and at[2] < h.index(manabi) < at[3], (k, "学びの輪の段の置き場")
    assert about.MANABI.startswith("作って、確かめて、ふり返って、次を考える。") and about.MANABI.endswith("進め役の役目は、型紙と記録の形の中に残っています。"), about.MANABI
    # 4. 見出しとテーマの字
    assert "<h1>うつし</h1>" in h, k
    assert "あなたにしかない深さ" not in h, k

# 5. README の頭の後の最初の節
readme = (ROOT / "README.md").read_text(encoding="utf-8")
a = readme.index(f"## {about.ENGINE_HEAD}")
sec = readme[a:readme.index("\n## ", a + 3)]
assert f"> {about.CORE}（本人の言葉 11-07）" in sec, "README の思いの核"
assert "".join(about.CORE_AFTER) in sec, "README の思いの核の後の 2 文"
assert about.README_KAMI == (about.KAMI[1], about.KAMI[3])
assert f"{about.KAMI_HEAD}: " + "".join(about.README_KAMI) in sec, "README のなぜ紙の 2 文"
assert sec.index(about.CORE) < sec.index(about.KAMI_HEAD) < sec.index("型紙を作るエンジンの仕組み:"), "README の並び"
assert "あなたにしかない深さ" not in sec
print("ok このサイトについて の頁（節の並び・思いの核と 2 文・なぜ紙の 4 文・AI の 2 文・見出しはうつし・README の頭の後の節）")
