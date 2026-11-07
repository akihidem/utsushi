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

SCALE = 0.75         # 英語の大きさ（日本語の大きさに掛ける）。本人の言葉（11-07）「英語の字幕が小さいかもしれない」で 0.6 から上げた（帯の英語 29px → 36px）
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
    # 3 talk_lost（声 A3。職人の 1 文は本人の言葉 11-07 の (2) の決着の字）
    "しかし、その多くは、": "But most of those toys",  # 案
    "職人も少なくなり、": "Craftsmen grew few,",  # 案（日本語は本人の字）
    # 4 scene2（声 A4）
    # 5 flip・18 close（決まった字）
    # 6 word_touch（名前の無い字の札・案。窓口の決め 11-07 の (3)）
    # 7 scene3
    # 8 core_make
    # 9 scene5
    "4 回のワークショップで、たくさんの人と紙で作りました。": "Over four workshops, many people built them in paper.",  # 案（窓口の確かめ待ち）
    "コードは Claude に任せ、紙と人に向かう時間を長く取りました。": "Claude wrote the code, so we spent most of our time with paper and people.",  # 案（同）
    "4 日間": "4 days",
    # 10 core_keep
    "できた物の写真と、": "Add a photo of what you made,",  # 案
    # 11 core_gallery
    # 12 border
    # 13 talk_physics（声 A5）
    "手で扱える小さな模型を自分で作り、": "build a small model you can hold,",  # 案
    # 14 talk_claude（声 A6）
    # 15 core_loop（つなぎ 2・いま作っているところです）
    "作ったものを持ちよると、": "When people share what they made,",  # 案
    "Claude もそれを見て、": "Claude looks at it too,",  # 案
    "次の型紙を少しずつよくしていきます。": "and improves the next pattern, bit by bit.",  # 案
    "いま作っているところです": "(Still being built)",  # 案
    # 16 word_ai（名前の無い字の札・案）
    # つなぎ 1（今の台本では外した札。words.ALL に残るので英語も置く）
    "むかしの子どもも、今の子どもも、": "Children long ago and children today",  # 案
    "もらったおもちゃより、": "often skip the toy they got",  # 案
    "それを包んでいた紙やリボンのひもで": "and play with the paper and ribbon",  # 案
    "遊んでしまうことがあります。": "it came wrapped in.",  # 案
    # 17 scene7
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
    out += [(x, "scene5") for x in scene5.WORKSHOP_LINES]  # ワークショップの写真の場面（11-07。2 かたまり）
    out += [(scene5.ALL_DAYS, "scene5")]  # 4 日間の 2 枚の札（英語は場面が渡す）
    out += [(scene7.CAPTION, "scene7")]
    out += [(words.ASK, "ask")]  # 本人の言葉の印（words.FROM）は、一般的な言い方にした（11-07）ので描かない
    for name, (line, src) in words.STATS.items():
        out += [(line, name), (src, name)]
    out += [(LABEL_CLAUDE, "later"), (LABEL_VOICE, "later")]
    for name in ("core_make", "core_keep", "core_gallery"):
        for s in core.screen_lines(name):
            out.append((s, name))
    # 場面「エンジンの仕組み」（demo.engine・案）。台本に入れる前から英語をそろえておく（台本に入れるかは demo.script の ENGINE_SCENE）
    from demo import engine
    out += [(s, "engine") for s in engine.drawn()]
    return out


# 場面「エンジンの仕組み」（demo.engine・案）の字。本人の言葉（11-07）「paper to toy の一つの具体例であるとか、エンジンの仕組みとかは
# デモとサイトで説明した方がいい」。英語は grove の state/engine-explain-20261107.md の (3) を元にした案。台本の字の表（上の EN）と
# 別の所に置く（同じ時に台本の字を直す枝と取り合わないため）
EN.update({
    "型紙の流れ": "Pattern flow",  # 案
    "入力（寸法・出典）": "Input (sizes, source)",  # 案
    "部品を並べる": "Lay out parts",  # 案
    "刷る前の検査": "Check before print",  # 案
    "描く": "Draw",  # 案
    "刷った後の検査": "Check after print",  # 案
    "型紙": "Pattern",  # 案
    "3D の流れ（御来迎・首振り虎）": "3D flow (Goraigo, nodding tiger)",  # 案
    "型紙の部品": "Pattern parts",  # 案
    "3D で折る": "Fold in 3D",  # 案
    "組み立てる": "Assemble",  # 案
    "3D 組み立て検品": "3D assembly check",  # 案
    "作り方の 3D": "Build steps in 3D",  # 案
    "改善の輪": "Improvement loop",  # 案
    "作った人の報告・感想": "Makers' reports",  # 案
    "直しの案": "Fix proposals",  # 案
    "人が採る": "People choose",  # 案
    "版を刻む": "New versions",  # 案
    "型紙の版・エンジンの版": "pattern / engine",  # 案
    "次の型紙": "Next pattern",  # 案
})


# 11-07 昼の組み直し（本人の直しの (1) ですます調・(4) コンセプト・(6) つなぎ・(8) 締め・本人の決定「引く候補 5 つ全部でよい（179.3 秒）」・
# 窓口の決め 120530・120643）で替えた字の英語。全部 案。日本語が替わった所だけを足し、前の字の英語は前の字のまま残す（外した場面の字も試験が読むため）
EN.update({
    "作るのは人の手です。": "People make them, by hand.",  # 案
    "その記録から、Claude が次の型紙を直します。": "From those records, Claude fixes the next pattern.",  # 案
    "型紙は完全ではありません。": "The patterns are not perfect.",  # 案
    "うまく動かない所を、人が工夫で乗り切ります。": "People find ways around what does not work.",  # 案
    "その過程を Claude に返すと、": "When that goes back to Claude,",  # 案
    "次の型紙が直ります。": "the next pattern gets better.",  # 案
    "紙と木と竹と糸でできていました。": "were made of paper, wood, bamboo, and string.",  # 案
    "子どもが壊しても、自分で直せました。": "If children broke them, they could fix them.",  # 案
    "そこに、遊ぶ喜びがありました。": "That was part of the joy of play.",  # 案
    "もう残っていません。": "are gone now.",  # 案
    "子供が簡単に手に入り遊べるおもちゃではなくなりました。": "and they are no longer toys children can easily get and play with.",  # 案（日本語は本人の字をですます調にした物）
    "知らない大人がほとんどです。": "Most adults have never seen them.",  # 案（同上）
    "残っているのは、『江都二色』（1773）という一冊の本です。": "What survives is one picture book, Edo Nishiki (1773).",  # 案
    "おもちゃの絵と狂歌は載っていますが、": "It has pictures of the toys and comic poems,",  # 案
    "遊び方と材料は書かれていません。": "but not how to play or what they were made of.",  # 案（1 秒 15 字の内）
    "手で作って考えるやり方は、科学にもあります。": "Science also thinks by making things by hand.",  # 案（(6) つなぎ）
    "物理には「トイモデル」という考え方があります。": 'Physics has an idea called the "toy model":',  # 案
    "動かしながら、手のひらで考えます。": "and think it through in your own hands.",  # 案
    "その横で、Claude が支えます。": "And Claude is there to support it.",  # 案
    "江戸の人は動きを絵に残しました。": "People in Edo kept motion in pictures.",  # 案
    "動きは、紙で作って確かめます。": "We test the motion by building it in paper.",  # 案
    "4 回のワークショップで、型紙の版を重ねました。": "Over four workshops, the patterns went through new versions.",  # 案
    "ここからは、裏のしくみです。": "Now, behind the scenes.",  # 案
    "型紙は正解ではなく、Claude が考えた仮説です。": "The pattern is not the answer. It is Claude's hypothesis.",  # 案
    "開いたら、すぐ作れます。": "Open it and start building right away.",  # 案
    "紙で作って、動きました。": "Built in paper, and it moved.",  # 案
    "作った人の工夫から、Claude が次の型紙を直します。": "From what makers figured out, Claude fixes the next pattern.",  # 案（(8) 締め）
    "3D の手順を見ながら作ります。": "Build it while watching the 3D steps.",  # 案
    "止まったら、そのまま声か字で聞けます。": "Stuck? Ask right there, by voice or text.",  # 案
    "工夫した所を記録に添えます。": "and note what you changed.",  # 案
    "作った物を、持ちよります。": "Bring what you made together.",  # 案
    "型紙は、paper to toy というエンジンが作ります。": "The patterns come from an engine called paper to toy.",  # 案（窓口の決め 120530 の 1 文目から）
    "直すたびに、型紙とエンジンの版が上がります。": "Each fix raises the pattern version and the engine version.",  # 案（同 5 文目から）
    "うつしはその一つの具体例で、みんなが使えるサービスとして作りました。": "utsushi is one example of it, built as a service anyone can use.",  # 案（窓口の決め 120530・120643）
})
