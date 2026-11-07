"""英語字幕（本人の言葉 11-07「英語字幕を入れよう」）。日本語の字幕・札の 1 かたまりの下に、英語を小さく 1 組で出す。

使い方: 字幕を描く所は words.draw_chunk か、ここの text_en を通す（日本語を描いて、その下に英語を描く）。英語は EN の表から引く。
exit: このモジュールは命令を持たない。英語の無いかたまりを描こうとすると MissingEnglish で止まる（黙って英語を落とさない）。

決めた事と理由:
- 表は 1 か所（EN）。鍵は日本語のかたまりの字そのもの（行の並びは "" でつないだ物）。日本語の字を変えたら、ここも変えないと書き出しが止まる。
  なぜ: 語りの 5 文と本人の言葉の札 2 つは、一般的な言い方に替えるかを窓口が決めている所（grove の state/demo-general-words-20261107.md）。
  替わった時に、英語の差し替えがこの表の 1 か所で済むようにする。
- 本人の言葉の引用の所（語り 5・札 2・印）の英語は、上の文書の「一般的な言い方の案」の英語（案）を、今の日本語のかたまりの数に分けて置いた。
  日本語はまだ今の字のまま。案なので、決まったら差し替える（印 # 案: 引用 を付けた）。
- ほかの決まった字の英語も同じ文書の案（# 案）。事実（TIMSS の数・出典・国立国会図書館の図・「紙で動いても…証明にはならない」・
  「型紙は正解ではなく…仮説」）は意味を変えずに訳した。
- 置き方: 日本語のすぐ下に、日本語の 6 割の大きさで、同じ濃さ（同じ溶け）で出す。日本語が無い時に英語だけを出さない（1 組で出す）。
  英語は置き場の幅に入るよう語の切れ目で折る（日本語の行の切り方は変えない）。
- 字の大きさの下限は 18px（数の出所の行など、日本語が小さい所でも読める大きさ）。
- 英語を出さない字（EXEMPT）: 作品の名前「utsushi」（英字のまま）と、クレジットの役と名（10 行。英語の行を足すと画面に入らないので、
  英語の役の名は README と提出の書類に書く）。
"""
from PIL import ImageFont

from demo.flip import SERIF, text

SCALE = 0.6          # 英語の大きさ（日本語の大きさに掛ける）
MIN_SIZE = 18        # 英語の字の大きさの下限（px）
LEAD = 1.35          # 英語の行送り（英語の大きさに掛ける）
GAP = 0.35           # 日本語の下の端から英語の上の端までの空き（日本語の大きさに掛ける）
MARGIN = 80          # 画面の端からの余白（px）。日本語の置き場の余白と同じ


class MissingEnglish(KeyError):
    """英語の無いかたまりを描こうとした。表（EN）に足すまで書き出しを止める。"""


EN = {
    # 1 opening
    "こんなおもちゃを知っていますか？": "Have you ever seen a toy like this?",  # 案
    "（ここに職人のおもちゃの動画が入ります）": "(A craftsman's toy video will go here)",  # 案
    # 2 talk_toys（声 A1・A2。一般的な言い方・案。窓口の決め 11-07 の (1) A）
    "江戸時代のおもちゃは、": "Toys in the Edo period",  # 案
    "紙と木と竹と糸でできていた。": "were made of paper, wood, bamboo, string.",  # 案
    "子どもが壊しても、自分で直せた。": "Children who broke them could mend them.",  # 案
    "そこに、遊ぶ喜びがあった。": "That was part of the joy.",  # 案
    # 3 talk_lost（声 A3。職人の 1 文は本人の言葉 11-07 の (2) の決着の字）
    "しかし、その多くは、": "But most of those toys",  # 案
    "もう残っていない。": "are gone.",  # 案
    "職人も少なくなり、": "Craftsmen grew few,",  # 案（日本語は本人の字）
    "子供が簡単に手に入り遊べるおもちゃではなくなった。": "and they stopped being toys children could easily get and play with.",  # 案（日本語は本人の字）
    "知らない大人がほとんどだ。": "Most adults have never seen them.",  # 案（日本語は本人の字）
    # 4 scene2（声 A4）
    "残っているのは、": "What survives",  # 案
    "『江都二色』（1773）という一冊の本。": "is one picture book, Edo Nishiki (1773).",  # 案
    "おもちゃの絵と、遊び方にちなんだ狂歌が載っている。": "It shows each toy with a comic poem about how it was played.",  # 案
    "けれども、どう遊ぶのか、": "But it never says how to play them,",  # 案
    "何でできていたのかは、書かれていない。": "or what they were made of.",  # 案
    # 5 flip・18 close（決まった字）
    "絵は動きを止めて残した。": "The pictures froze the motion.",  # 案
    "どう動いたかは、紙で作って確かめる。": "To learn how it moved, build it in paper.",  # 案
    # 6 word_touch（名前の無い字の札・案。窓口の決め 11-07 の (3)）
    "まず大事なのは、": "What matters first",  # 案
    "手で作る楽しさに気づくこと。": "is finding the joy of making by hand.",  # 案
    "AI がよくなるのは、その後。": "Better AI comes after that.",  # 案
    # 7 scene3
    "型紙は正解ではなく、Claude が考えた仮説": "The pattern is not the answer. It is Claude's hypothesis.",  # 案
    "開いたら、すぐ作る。": "Open it and start building.",  # 案
    # 8 core_make
    "手順を見ながら作る。": "Build it step by step.",  # 案
    "止まったら、そのまま声か字で聞ける": "Stuck? Ask by voice or text.",  # 案
    # 9 scene5
    "紙で作って、動いた。": "Built in paper, and it moved.",  # 案
    # 10 core_keep
    "できた物の写真と、": "Add a photo of what you made,",  # 案
    "工夫した所を記録に添える": "and note what you changed.",  # 案
    # 11 core_gallery
    "作った物を、持ちよる。": "Bring what you made together.",  # 案
    # 12 border
    "ここからは、裏のしくみ。": "Now, behind the scenes.",  # 案
    # 13 talk_physics（声 A5）
    "物理には「トイモデル」という考え方がある。": 'Physics has an idea called the "toy model":',  # 案
    "手で扱える小さな模型を自分で作り、": "build a small model you can hold,",  # 案
    "動かしながら、手のひらで考える。": "and think it through in your own hands.",  # 案
    # 14 talk_claude（声 A6）
    "その横で、Claude が手伝う。": "And Claude is there to help.",  # 案
    # 15 core_loop（つなぎ 2・いま作っているところです）
    "作ったものを持ちよると、": "When people share what they made,",  # 案
    "Claude もそれを見て、": "Claude looks at it too,",  # 案
    "次の型紙を少しずつよくしていきます。": "and improves the next pattern, bit by bit.",  # 案
    "ワークショップを 2 回して、型紙の版を重ねた。": "Two workshops, and the pattern went through new versions.",  # 案（窓口の決定 084919 の ③ 案 1）
    "いま作っているところです": "(Still being built)",  # 案
    # 16 word_ai（名前の無い字の札・案）
    "型紙は完全ではない。": "The patterns are not perfect.",  # 案
    "うまく動かない所を、人が工夫で乗り切る。": "People work around what fails.",  # 案
    "その過程を AI に返すと、": "It goes back to the AI,",  # 案
    "次の型紙が直る。": "and the next pattern improves.",  # 案
    # つなぎ 1（今の台本では外した札。words.ALL に残るので英語も置く）
    "むかしの子どもも、今の子どもも、": "Children long ago and children today",  # 案
    "もらったおもちゃより、": "often skip the toy they got",  # 案
    "それを包んでいた紙やリボンのひもで": "and play with the paper and ribbon",  # 案
    "遊んでしまうことがあります。": "it came wrapped in.",  # 案
    # 17 scene7
    "紙で動いても、昔の作り方の証明にはならない": "Working in paper does not prove how it was made back then.",  # 案
    # 19 ask
    "あなたなら、何を作りますか。": "What would you make?",  # 案
    # 数の 1 行と出所（13・15・16。数と出典の名は原典のまま訳した）
    "理科の実験が週 1 回以上ある小学 4 年生　日本 59.6％・国際平均 31.5％":
        "4th graders with science experiments at least weekly: Japan 59.6% / international avg. 31.5%",  # 案
    "理科を使う職業につきたい中学 2 年生　日本 27％・国際平均 58％":
        "8th graders who want a job that uses science: Japan 27% / international avg. 58%",  # 案
    "学校の外でハンドクラフト・DIY・模型制作をした高校生　日本 13.5％（米中と 20 ポイント以上の差）":
        "High schoolers who did crafts, DIY or model-making outside school: Japan 13.5% (20+ points below the US and China)",  # 案
    "出典: 文部科学省・国立教育政策研究所「TIMSS2023 のポイント」（2024）": 'Source: MEXT / NIER, "TIMSS 2023 Highlights" (2024)',  # 案
    "出典: 国立青少年教育振興機構「高校生の文化に関する意識調査報告書」（2026）":
        "Source: NIYE, survey on high school students' culture (2026)",  # 案（出所の行は日本語と 1 行に並べるので、機構の英語の略称 NIYE にした）
    # 後入れの札（demo.later）
    "本物の Claude の返事は後入れ": "Real Claude reply: to be added",  # 案
    "本人の声は後入れ": "Maker's voice: to be added",  # 案
}

# 数の入る札の形（{n} は数）。型紙の版とエンジンの版を言い分ける（窓口の決定 11-07、カード 084426）
FORMATS = {"型紙の版 {n}": "Pattern v{n}", "エンジンの版 {n}": "Engine v{n}"}  # 案

# 英語を出さない字（理由は頭の決めた事）
EXEMPT = ("utsushi",)


def en(ja):
    """日本語のかたまりの英語。無ければ MissingEnglish（書き出しを止める）。"""
    try:
        return EN[ja]
    except KeyError:
        raise MissingEnglish(f"英語字幕が無い: {ja}（demo.english.EN に足す）") from None


def en_format(pattern, **kw):
    """数の入る札の英語（FORMATS）。"""
    try:
        return FORMATS[pattern].format(**kw)
    except KeyError:
        raise MissingEnglish(f"英語字幕が無い: {pattern}（demo.english.FORMATS に足す）") from None


def size_of(size):
    return max(MIN_SIZE, round(size * SCALE))


def font(size):
    return ImageFont.truetype(SERIF, size_of(size))


def wrap(s, size, width):
    """英語を語の切れ目で折る（幅 width px に入る行の並び）。1 語が幅を超える時はその語だけの行にする。"""
    f = font(size)
    lines, cur = [], ""
    for word in s.split(" "):
        trial = f"{cur} {word}".strip()
        if cur and f.getlength(trial) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def room(cx, anchor="m"):
    """英語を置ける幅（px）。真ん中に置く時は左右の近い方の端まで、左寄せ・右寄せの時はその向きの端まで。"""
    from demo.flip import W

    if anchor == "l":
        return W - MARGIN - cx
    if anchor == "r":
        return cx - MARGIN
    return 2 * min(cx, W - cx) - 2 * MARGIN


def block_height(ja_size, en_lines):
    """英語の行の並びが取る高さ（日本語の下の空きを含む）。"""
    return round(ja_size * GAP) + round(len(en_lines) * size_of(ja_size) * LEAD)


def draw_en_lines(draw, x, y, en_lines, ja_size, fill, align="m"):
    """英語の行の並びを、上の端 y から描く。"""
    step = round(size_of(ja_size) * LEAD)
    for j, line in enumerate(en_lines):
        text(draw, (x, y + j * step), line, size_of(ja_size), fill, False, align + "a")


def text_en(draw, xy, ja, size, fill, bold=False, anchor="la", english=None):
    """日本語の 1 行を描き、その下に英語を描く（flip.text と同じ引数）。english を渡すと表を引かずにその字を使う（数の入る札）。
    縦の置き方は anchor の 2 字目で読む: a（上の端）・m（真ん中）。英語の行の上の端の y を返す。"""
    text(draw, xy, ja, size, fill, bold, anchor)
    x, y = xy
    align, vert = anchor[0], anchor[1]
    bottom = y + size if vert == "a" else y + size // 2
    lines = wrap(english if english is not None else en(ja), size, room(x, align))
    top = bottom + round(size * GAP)
    draw_en_lines(draw, x, top, lines, size, fill, align)
    return top


def all_sources():
    """書き出しが描く日本語の字（試験で、どれにも英語がある事を見る）。今の台本の場面の分。"""
    from demo import core, opening, scene3, scene5, scene7, words
    from demo.flip import CLOSING
    from demo.later import LABEL_CLAUDE, LABEL_VOICE

    out = []
    for name, chunks in words.ALL.items():
        for lines in chunks:
            out.append(("".join(lines), name))
    out += [(opening.QUESTION, "opening"), (opening.PLACEHOLDER, "opening")]
    out += [(c, "flip") for c in CLOSING]
    out += [(scene3.TITLE_PREMISE, "scene3"), *[(c, "scene3") for c in scene3.CLOSING]]
    out += [(c, "scene5") for c in scene5.CAPTION]
    out += [(scene7.CAPTION, "scene7")]
    out += [(words.ASK, "ask")]  # 本人の言葉の印（words.FROM）は、一般的な言い方にした（11-07）ので描かない
    for name, (line, src) in words.STATS.items():
        out += [(line, name), (src, name)]
    out += [(LABEL_CLAUDE, "later"), (LABEL_VOICE, "later")]
    for name in ("core_make", "core_keep", "core_gallery"):
        for s in core.screen_lines(name):
            out.append((s, name))
    return out
