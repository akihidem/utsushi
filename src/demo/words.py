"""言葉の札: 本人の言葉と語りを 1 かたまりずつ紙の地に出す場面と、つなぎの字幕の札と、終わりの字幕の札と、最後の問いの札。

使い方: python -m demo.words <札の名前> --out <repo の外の場所>/word.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 画像が取れない・ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 本人の方針（11-05 20:10）「たくさん見る審査員の認知負荷を減らす方針が1番最初。癒し系で。」。画面の字は 1 度に 1 かたまりだけにし、
  大きめの字で、ゆっくり溶かして替える。足りない時は速めずに文を減らす（RATE、1 秒 5 字以下）。字のそばに動く物を置かない（隅の人物はやめた）。
- 本人の決定（11-05）「哲学よりの動画にして」。軸を機能の説明から本人の言葉へ移した。
- 本人の言葉は docs/process/philosophy.md の字のまま出す。札をつなぐと、記録の引用の 1 行と一字も違わない事を
  床（tests/test_demo_words.py）が見る。行とかたまりの切れ目は置き方だけで、字は足さず引かない。
  短く切った文は本人の言葉と書かない決まりなので、ここには全文だけを置く。
- 語り（本人の言葉 11-05 20:04）は docs/demo/opening-narration.txt の字のまま、文の単位で選ぶ。文の中の字は変えず、途中で切らず、
  つなぐ言葉も足さない。長い文は読点の切れ目で何枚かに分ける（本人の方針 11-05 20:10）。
- 本人の決定（11-05）: つなぎの文は案のまま決まった。字を変えない。本人の言葉の札にはしないので、その印を付けない。
- 本人の決定（11-05）: 初めと終わりの字幕は同じ文。終わりは、この字幕 → 問いの順にする。字は demo.flip の 1 か所から読む（初めと終わりで食い違わないため）。
  本人が決めた字幕で、言葉の記録の引用ではないので、言葉の札の印は付けない。
- 問いの文面は本人の決定（11-05）。説教くさくしないよう、見ている人を問い詰めない形にした。
  本人の言葉の記録の引用ではないので、言葉の札の印（FROM）は付けない。問いの札には考える間に動く物を置かない（音も止める。demo.beat）。
- 出る時刻は CUES にあり、拍に乗る（仮の拍も、曲の拍合わせも CUES だけを読む）。
- frame(t) は時刻だけから 1 コマを描く純関数（場面 1 と同じ）。
"""
import argparse
import math
import pathlib
import sys
import types

from PIL import Image, ImageDraw, ImageFont

from demo.flip import CLOSING, FPS, H, PAPER, ROOT, SERIF, SHU, SUMI, W, contact_sheet, ease, fade, render, text

PHILOSOPHY = ROOT / "docs/process/philosophy.md"
NARRATION = ROOT / "docs/demo/opening-narration.txt"
# 問いの文面。本人の決定（11-05、docs/demo/plan.md の 4）。
ASK = "あなたなら、何を作りますか。"
FROM = "本人の言葉（11-05）"
RATE, MIN_CHUNK = 5.0, 2.0     # 1 秒に読ませる字の上限と、短いかたまりでも置く秒
LEAD, TAIL = 0.4, 0.2          # 場面の頭と終わりの余り（場面の溶けと重なる所）
DISSOLVE = 0.5                 # かたまりが消える・現れる秒。前が消えてから次が現れるので、替わり目は 1 秒
EPS = 1e-9                     # 小数の誤差で切り上げが 0.1 秒増えないようにする
# 字の札（全画面の題の札）。本人の言葉（11-07）「デモ動画は、僕の言葉の引用ではなく、一般的な言い方にしたい」と窓口の決め（11-07 の (1) A・(3)）で、
# 本人の言葉の引用の札を、名前の無い字の札にした。字は state の demo-general-words の案（本人の確かめ待ち）。前は哲学の記録の引用と一字も違わない事を見ていた
CARDS = {
    "word_touch": (("まず大事なのは、",), ("手で作る楽しさに気づくこと。",), ("AI がよくなるのは、その後。",)),
    "word_ai": (("型紙は完全ではない。",), ("うまく動かない所を、人が工夫で乗り切る。",), ("その過程を AI に返すと、",), ("次の型紙が直る。",)),
}
# 語り（一般的な言い方・案）。合成の声（grove の state/demo-voice-aivis-general）が同じ字を読む。かたまりの切れ目は読点。
# talk_lost の職人の 1 文は、本人の決定（11-07 の (2) B）で前の語りのまま「職人ももうほとんど残っていない」の言い方を残した
TALKS = {
    "talk_toys": (("江戸時代のおもちゃは、",), ("紙と木と竹と糸でできていた。",), ("子どもが壊しても、自分で直せた。",), ("そこに、遊ぶ喜びがあった。",)),
    "talk_lost": (("しかし、その多くは、",), ("もう残っていない。",), ("それを作る職人も、", "もうほとんど残っていない。")),
    "scene2": (("残っているのは、",), ("『江都二色』（1773）という一冊の本。",), ("おもちゃの絵と、", "遊び方にちなんだ狂歌が載っている。"),
               ("けれども、どう遊ぶのか、",), ("何でできていたのかは、", "書かれていない。")),
    "talk_physics": (("物理には「トイモデル」という", "考え方がある。"), ("手で扱える小さな模型を", "自分で作り、"), ("動かしながら、", "手のひらで考える。")),
    "talk_claude": (("その横で、Claude が手伝う。",),),
}
# つなぎの文（本人の決定 11-05）。つなぎ 1 は今の台本から外してある（demo.script の LEFT_OUT）。つなぎ 2 は core_loop に出す。
BRIDGE = (("むかしの子どもも、今の子どもも、",), ("もらったおもちゃより、",), ("それを包んでいた紙や", "リボンのひもで"), ("遊んでしまうことがあります。",))
BRIDGE2 = (("作ったものを持ちよると、",), ("Claude もそれを見て、",), ("次の型紙を少しずつ", "よくしていきます。"))
NOW_LINE = "いま作っているところです"      # AI はまだ動いていないので、つなぎ 2 と一緒に出す（本人の決定 11-05）
# 表と裏の境目の札（本人の決定 11-06、カード 125217）。字を変えない。本人の言葉の記録の引用ではないので、言葉の札の印は付けない。
BORDER = (("ここからは、裏のしくみ。",),)
# 場面 15 の字幕（窓口の決定 11-07 の 084919 の ③「言う所は字幕（案 1）」）。秒は場面 4 の語りが短くなって空いた分（窓口の決め 11-07 の (1) A）
VERSIONS_LINE = "ワークショップを 2 回して、型紙の版を重ねた。"
ALL = {**CARDS, **TALKS, "bridge": BRIDGE, "close": ((CLOSING[0],), (CLOSING[1],)), "core_loop": (*BRIDGE2, (VERSIONS_LINE,), (NOW_LINE,)), "border": BORDER}
MARKED = ()                    # 本人の言葉の印を付ける札。一般的な言い方にした（11-07）ので、印を付ける札は無い
# 場面の秒の下限（決まった秒）。字が短くなっても、手の映像の長さと場面の秒を前のままにする（本人の決定 11-06 の手の映像の秒）。
# 字が終わった後は、手と絵だけを見せる（ファイナリストから借りた点「作っている所は語りを止める」。state の demo-rebuild）。
# scene2 は語りが短くなった分を場面 15 の字幕へ回したので、合計の秒（178.90）が前と同じになる秒にした
HOLD = {"talk_toys": 11.8, "talk_lost": 12.2, "talk_physics": 16.0, "talk_claude": 4.4, "word_touch": 9.4, "word_ai": 11.2, "scene2": 19.5}
# デモと外に出す文で使わない言い方（本人の決定 11-05）。継承を軸にし、「復活」を「昔の作り方を取り戻した」の意味で使わない。
# 前からの線「失われた技術を取り戻すとは書かない」を残す。語りの全文には「復活」の文があるが、札に選ばない。
NOT_SAID = ("復活", "取り戻")
ASK_SECONDS = 5.0
ASK_SIZE = 72
# 札ごとの置き方。図を右に置く札は、字を左に寄せて小さくする。ink は図の濃さ（始め, 終わり）。
# talk_lost の図は、語りの「失われていて」の間に薄くする（今の決定の形）。11-06 夜に一度「薄くせず止める」にしたが、
# 見せ方の議論（本人の答え: 19:53 の考えは議論中で、今の決定は生きている）が決まるまで入れないと統括が決め、戻した。
STYLES = {"talk_toys": {"size": 60, "cx": 640, "ink": (0.85, 0.85)}, "talk_lost": {"size": 60, "cx": 640, "ink": (0.85, 0.12)},
          "talk_physics": {"size": 64}, "close": {"size": 64}, "bridge": {"size": 64}}
PICTURED = ("talk_toys", "talk_lost")     # 図（場面 2 と同じ御来迎の頁）を右に置く札。職人の動画が来るまで、作り物で埋めない
PIC_H, PIC_X = 860, 1470                  # 図の高さと真ん中
# 手だけの映像を敷く札の置き方（本人の決定 11-06「手だけを撮って、語りの場面の後ろに敷く」）。撮る物の一覧で、手は画面の右 3 分の 2、
# 左 3 分の 1 は空けた机にしてもらう。字はその左に寄せ、図を右に置く札と同じ大きさにする（読む所を札ごとに動かさない）。
# 左は紙の色を薄く掛けて字を読めるようにし（WASH）、右へ向けて消す。手の映像は紙の地から溶けて現れ、紙の地へ溶けて消える
# （場面の替わり目と同じ紙の地を挟む形。癒し系の本人の方針 11-05 20:10）。映像の音は使わない。
HANDS_STYLE = {"size": 60, "cx": 640}
# 公的調査の数（本人の決定 11-06: 使う数は 3 つ・カード 125857。置き場は A「秒は増やさず、裏の部の場面に小さく 1 行ずつ重ねる」）。
# 数と出所は原典で確かめた物だけ（grove の state/survey-research-20261106 の 01・02。原典の頁つき）。GitHub に上げてよいのは公的調査だけ。
# 原典で言い切れない事（紙工作の学習の効果・郷土玩具の担い手の減り方）は言わない。出典の 1 行（調べた所と年）を小さく添える。
# 並べ方（どの場面にどの数か）と字は、本人が確かめた（11-06「デモの公的調査の数3つは、その置き場と字でよい。」）。字を変える時は本人に聞く。
# 順は「実験は多い → それでも理科を使う職業につきたいは少ない →
# 学校の外で手を動かして作る高校生は少ない」で、手で作る話（物理のトイモデルの語り）・輪・本人の言葉の札に 1 つずつ重ねる。
# 原典の値: TIMSS2023 小 4 の実験「少なくとも週 1 回」日本 59.6%・国際平均 31.5%（資料の頁 16）、中 2「理科を使うことが含まれる職業につきたい」
# 日本 27%・国際平均 58%（資料の頁 12）。国立青少年教育振興機構 文化 2026 の「ハンドクラフト・DIY・模型制作」13.5%（全体版 紙面 37 図 4-1。
# 回答者全体の値。第 3 章の 15.0% は分母が違うので混ぜない）・「米中とは 20 ポイント以上の差」（同じ所の本文）。
# 数の行は、場面の中で読める秒（1 秒 5 字）に入る長さにする。「米国・中国」と書くと本人の言葉の札で 0.2 秒あふれたので、本文の言い方の「米中」にした。
TIMSS = "出典: 文部科学省・国立教育政策研究所「TIMSS2023 のポイント」（2024）"
STATS = {
    "talk_physics": ("理科の実験が週 1 回以上ある小学 4 年生　日本 59.6％・国際平均 31.5％", TIMSS),
    "core_loop": ("理科を使う職業につきたい中学 2 年生　日本 27％・国際平均 58％", TIMSS),
    "word_ai": ("学校の外でハンドクラフト・DIY・模型制作をした高校生　日本 13.5％（米中と 20 ポイント以上の差）",
                "出典: 国立青少年教育振興機構「高校生の文化に関する意識調査報告書」（2026）"),
}
# 置き場は帯（上か下）。本人の言葉の印（下から 130）のある札（語りと本人の言葉の札）は上の帯にする: 下に置くと、印のすぐ下に数が来て、
# 数まで本人の言葉に見えた（11-06 に絵で見た）。印の無い札（輪の図）は下の帯。字は読める大きさの下限として 30（出所は 22）。
STAT_SIZE, SRC_SIZE = 30, 22
# 英語字幕を入れた形（11-07）: 数の行（日本語）→ 数の行（英語）→ 出所（日本語と英語を 1 行に）。下の帯は前の数の行の上の端（H-78）より
# 上へ広げない: 輪の場面の案内役は足もとを H-86 に置いて帯の上を歩くため（11-06 に絵で見た）
# 出所の行は日本語と英語を 1 行に並べ、大きさは前の下限の 22 のまま。
BANDS = {"bottom": (H - 86, H - 28, H - 96, H), "top": (36, 92, 0, 124)}   # 数の行・出所の行の上の端、帯の上と下
EN_Y = {"bottom": H - 54, "top": 68}                                      # 数の英語の行の上の端
EN_STAT_SIZE = 21                                                         # 数の英語の行の大きさ
STAT_IN = (0.4, 1.4)        # 場面の頭で現れて、その後は動かさない（字のそばに動く物を置かない線）
STRIP_INK = 0.88            # 手の映像を敷く時だけ、帯に紙の色を掛ける濃さ


def stat_band(name):
    # 字幕の帯（下）を使う場面は、数の行を上の帯へ（帯と重ねない）。全画面の題の札は下のまま
    return "bottom" if name in TITLE_CARDS else "top"


def draw_stat(img, name, t, hands=False):
    """場面 name に重ねる数の 1 行と出所の 1 行。無い場面では何もしない。"""
    if name not in STATS:
        return img
    a, b = STAT_IN
    v = ease((t - a) / (b - a))
    if v <= 0:
        return img
    y_line, y_src, b0, b1 = BANDS[stat_band(name)]
    y_en = EN_Y[stat_band(name)]
    if hands:
        band = Image.new("RGB", (W, b1 - b0), PAPER)
        img.paste(Image.blend(img.crop((0, b0, W, b1)), band, STRIP_INK * v), (0, b0))
    line, src = STATS[name]
    from demo.english import en

    draw = ImageDraw.Draw(img)
    text(draw, (W // 2, y_line), line, STAT_SIZE, fade(SUMI, 0.85 * v), False, "ma")
    text(draw, (W // 2, y_en), en(line), EN_STAT_SIZE, fade(SUMI, 0.8 * v), False, "ma")
    text(draw, (W // 2, y_src), f"{src}　{en(src)}", SRC_SIZE, fade(SUMI, 0.6 * v), False, "ma")
    return img
WASH = (0.9, 1000, 1450)                  # 掛ける紙の濃さ、濃いままの右端、消える所


def flat(chunks):
    """かたまりの並びを 1 つの文につなぐ。"""
    return "".join("".join(lines) for lines in chunks)


def record_lines(path=PHILOSOPHY):
    """記録の中の、本人の言葉の引用の行（> で始まる行）。"""
    return [line[2:].strip() for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("> ")]


def in_record(lines, path=PHILOSOPHY):
    """札の行をつないだ文が、記録の引用の 1 行と一字も違わないか。部分一致にしない（切った文を本人の言葉にしないため）。"""
    return "".join(lines) in record_lines(path)


def sentences_of(chunks):
    """かたまりをつないで、文（。で終わる）の並びにする。"""
    return [s + "。" for s in flat(chunks).split("。") if s]


def in_narration(chunks, path=NARRATION):
    """語りのかたまりの文が 1 文ずつ、語りの全文の中にそのままあるか。札の中で文を飛ばしてよいが、文の途中では切らない。"""
    full = path.read_text(encoding="utf-8")
    return flat(chunks).endswith("。") and all(s in full for s in sentences_of(chunks))


def says_restored(chunks):
    """札の字に、使わない言い方があるか。"""
    return any(w in flat(chunks) for w in NOT_SAID)


def chunks_of(name):
    return ALL[name]


def reading_chars(text):
    """読む字の数。半角の字は半分に数える（「Claude」は 6 字の仮名ほど読む手間がかからない）。"""
    return sum(0.5 if ord(c) < 128 else 1.0 for c in text)


def chunk_seconds(lines):
    """1 かたまりの秒。1 秒 5 字以下。替わり目の溶けもこの中に入る。"""
    return max(MIN_CHUNK, reading_chars("".join(lines)) / RATE)


def cues_of(name):
    """札の合図の表。c0, c1… が各かたまりの現れる時刻。"""
    if name == "ask":
        return {"in": (0.0, 1.0)}
    out, t = {"page": (0.0, LEAD)}, LEAD
    for i, lines in enumerate(chunks_of(name)):
        out[f"c{i}"] = (round(t, 3), round(t + DISSOLVE, 3))
        t += chunk_seconds(lines)
    return out


def seconds_of(name):
    if name == "ask":
        return ASK_SECONDS
    need = math.ceil((LEAD + sum(chunk_seconds(c) for c in chunks_of(name)) + TAIL) * 10 - EPS) / 10
    return max(need, HOLD.get(name, 0.0))


def chunk_alpha(cues, n, i, t):
    """i 番目のかたまりの濃さ。前のかたまりが消えてから次が現れる（字を重ねない）。最後のかたまりは場面の溶けで消える。"""
    v = ease((t - cues[f"c{i}"][0]) / DISSOLVE)
    if i + 1 < n:
        end = cues[f"c{i + 1}"][0]
        v *= 1 - ease((t - (end - DISSOLVE)) / DISSOLVE)
    return v


def draw_chunk(draw, lines, cx, cy, size, v):
    """1 かたまりを、cy を真ん中にして行ごとに描く。英語字幕（demo.english）を日本語の下に同じ濃さで 1 組にして描き、
    日本語と英語を合わせた高さの真ん中を cy にする（本人の言葉 11-07「英語字幕を入れよう」）。"""
    from demo import english

    fill = fade(SUMI, v)
    lead = round(size * 1.6)
    en_lines = english.wrap(english.en("".join(lines)), size, english.room(cx))
    total = (len(lines) - 1) * lead + size + english.block_height(size, en_lines)
    top = cy - total // 2
    for j, line in enumerate(lines):
        text(draw, (cx, top + j * lead), line, size, fill, False, "ma")
    english.draw_en_lines(draw, cx, top + (len(lines) - 1) * lead + size + round(size * english.GAP), en_lines, size, fill)


# 字幕の帯（ファイナリストから借りた点 1・2。state の demo-rebuild）: 画面の下の真ん中に暗い帯、白い字の日本語（1〜2 行）、その下に英語を小さく
# 1 かたまり。焼き込み。3 本のファイナリストの型（下の真ん中・黒地に白・大きめ）と、窓口の決め（11-07 の (3)「日本語の下に小さく英語・1 かたまり」）。
# 全画面の題の札（借りた点 6）は帯にせず真ん中に大きく出す: 字の札 2 つ（word_touch・word_ai）と、境目・終わりの問い・締め（close）
BAND_JA = 44                 # 帯の日本語の大きさ（px）
BAND_PAD = (40, 18)          # 帯の中の左右と上下の余白（px）
BAND_BOTTOM = 34             # 画面の下の端から帯の下の端（px）
BAND_INK = 0.66              # 帯の暗さ（v=1 の時の不透明さ）
BAND_COLOR, BAND_JA_INK, BAND_EN_INK = (24, 21, 18), (255, 253, 248), (232, 226, 214)
TITLE_CARDS = ("word_touch", "word_ai", "border", "close")


def band_height(lines, en_lines=None):
    """帯の高さ（px）。案内役や数の行を帯の上へ逃がす時に使う。en_lines を渡さない時は表から引く。"""
    from demo import english

    if en_lines is None:
        en_lines = english.wrap(english.en("".join(lines)), BAND_JA, W - 2 * 240)
    return 2 * BAND_PAD[1] + len(lines) * round(BAND_JA * 1.45) + round(BAND_JA * english.GAP) + len(en_lines) * round(english.size_of(BAND_JA) * english.LEAD)


BAND_TOP = H - BAND_BOTTOM - band_height(("一",), ["one"])    # 日本語 1 行・英語 1 行の帯の上の端（案内役の置き場の目安）


def band(img, lines, v):
    """1 かたまりを字幕の帯に描いた絵を返す（img は替えない）。英語は表（demo.english）から引き、無ければ止まる（MissingEnglish）。"""
    if v <= 0:
        return img
    from demo import english

    en_lines = english.wrap(english.en("".join(lines)), BAND_JA, W - 2 * 240)
    fja, fen = ImageFont.truetype(SERIF, BAND_JA), english.font(english.size_of(BAND_JA))
    probe = ImageDraw.Draw(img)
    wide = max([probe.textlength(x, font=fja) for x in lines] + [probe.textlength(x, font=fen) for x in en_lines])
    h = band_height(lines, en_lines)
    x0, x1 = round(W / 2 - wide / 2 - BAND_PAD[0]), round(W / 2 + wide / 2 + BAND_PAD[0])
    y1 = H - BAND_BOTTOM
    y0 = y1 - h
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((x0, y0, x1, y1), 10, fill=(*BAND_COLOR, round(255 * BAND_INK * v)))
    y = y0 + BAND_PAD[1]
    for line in lines:
        d.text((W // 2, y), line, font=fja, fill=(*BAND_JA_INK, round(255 * v)), anchor="ma")
        y += round(BAND_JA * 1.45)
    y += round(BAND_JA * english.GAP) - round(BAND_JA * 0.45)
    for line in en_lines:
        d.text((W // 2, y), line, font=fen, fill=(*BAND_EN_INK, round(255 * v)), anchor="ma")
        y += round(english.size_of(BAND_JA) * english.LEAD)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def draw_from(draw, cx):
    """本人の言葉の印。札の下に静かに置く。"""
    from demo.english import text_en

    text_en(draw, (cx, H - 136), FROM, 30, fade(SHU, 0.75), False, "ma")


def _ink(layer, v):
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda a: round(a * v)))
    return out


def picture(layer):
    """右に置く図を、決めた高さにする。"""
    return layer.resize((round(layer.width * PIC_H / layer.height), PIC_H), Image.LANCZOS)


def _wash():
    """左に掛ける紙の濃さの面（L）。255 で紙の色、0 で手の映像のまま。"""
    v, keep, gone = WASH
    row = [round(255 * v * (1.0 if x < keep else max(0.0, 1 - (x - keep) / (gone - keep)))) for x in range(W)]
    return Image.frombytes("L", (W, 1), bytes(row)).resize((W, H))


class ChunkCard:
    """紙の地に字を 1 かたまりずつ出す札。pic を渡すと右に図を置く。
    hands を渡すと、その間は手の映像を地に敷く: [(1 秒 FPS 枚に割った絵の道の並び, 始め, 終わり)]。図より手を先にする（手が図の代わり）。"""

    def __init__(self, name, cues, pic=None, hands=()):
        self.name, self.cues, self.pic = name, cues, pic
        self.hands = [(list(f), a, b) for f, a, b in hands if f]
        self.chunks = chunks_of(name)
        self.duration = seconds_of(name)
        style = {**STYLES.get(name, {}), **(HANDS_STYLE if self.hands else {})}
        self.size, self.cx, self.ink = style.get("size", 72), style.get("cx", W // 2), style.get("ink", (1.0, 1.0))
        self._mask = _wash() if self.hands else None

    def _hands(self, t):
        """時刻 t の手の映像の絵と濃さ。敷いていない時は (None, 0)。"""
        for frames, a, b in self.hands:
            if a <= t < b:
                v = min(ease((t - a) / DISSOLVE), ease((b - t) / DISSOLVE))
                with Image.open(frames[min(len(frames) - 1, int((t - a) * FPS))]) as im:
                    return im.convert("RGB").resize((W, H)), v
        return None, 0.0

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。
        題の札（TITLE_CARDS）は前の形（紙の地の真ん中に大きな字）。語りの札は、手の映像を画面いっぱいに敷き（左に紙を掛けない）、
        図は真ん中に置き、字は下の帯の字幕にする（ファイナリストから借りた点 1・3。state の demo-rebuild）。"""
        title = self.name in TITLE_CARDS
        img = Image.new("RGB", (W, H), PAPER)
        shot, hv = self._hands(t) if self.hands else (None, 0.0)
        if shot is not None and hv > 0:
            if title:
                shot = Image.composite(img, shot, self._mask)
            img = Image.blend(img, shot, hv)
        elif self.pic is not None and not self.hands:
            a, b = self.ink
            lay = _ink(self.pic, a + (b - a) * ease(t / self.duration))
            x = PIC_X if title else W // 2
            img.paste(lay, (x - lay.width // 2, (H - lay.height) // 2), lay)
        for i, lines in enumerate(self.chunks):
            v = chunk_alpha(self.cues, len(self.chunks), i, t)
            if v > 0:
                if title:
                    draw_chunk(ImageDraw.Draw(img), lines, self.cx, H // 2 - 30, self.size, v)
                else:
                    img = band(img, lines, v)
        draw = ImageDraw.Draw(img)
        if self.name in MARKED:
            draw_from(draw, self.cx)
        return draw_stat(img, self.name, t, hands=bool(self.hands))


class AskCard:
    """最後の問い。紙の地に字だけ。"""

    def __init__(self, cues):
        self.cues = cues
        self.duration = ASK_SECONDS

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        a, b = self.cues["in"]
        v = ease((t - a) / (b - a))
        if v > 0:
            from demo.english import text_en

            text_en(ImageDraw.Draw(img), (W // 2, H // 2 - 80), ASK, ASK_SIZE, fade(SUMI, v), False, "ma")
        return img


def fits():
    """札の字が置き場に収まるか（名前 → 右端の余り px）。試験と書き出しの前の確かめに使う。"""
    out = {"ask": W - 160 - ImageFont.truetype(SERIF, ASK_SIZE).getlength(ASK)}
    for name in ALL:
        style = STYLES.get(name, {})
        f = ImageFont.truetype(SERIF, style.get("size", 72))
        room = 2 * style["cx"] - 160 if "cx" in style else W - 160
        out[name] = room - max(f.getlength(s) for lines in chunks_of(name) for s in lines)
    from demo import script  # 手を敷く札は HANDS_STYLE の置き方でも収まるか（届いた時に字が切れないため）

    hf = ImageFont.truetype(SERIF, HANDS_STYLE["size"])
    for name in script.SLOTS:
        if script.SLOTS[name].get("hands"):
            out[f"{name}+hands"] = 2 * HANDS_STYLE["cx"] - 160 - max(hf.getlength(s) for lines in chunks_of(name) for s in lines)
    return out


def hands_problem(path, seconds, probe=None):
    """手の映像が決まり（横 16:9・幅 1280 以上・使う秒以上）に合わないなら、その理由。合えば None。"""
    from demo import opening

    got = (probe or opening._probe)(path)
    if got is None:
        return "動画が読めない"
    width, height, secs = got
    if width < opening.MIN_WIDTH:
        return f"動画の幅が {opening.MIN_WIDTH} より小さい（{width}）"
    if abs(width / height - 16 / 9) > 0.02:
        return f"横 16:9 でない（{width}×{height}）"
    if secs < seconds:
        return f"動画が {seconds:g} 秒より短い（{secs:.1f} 秒）"
    return None


def hands_slots(name, root=ROOT):
    """場面に敷く手の映像の置き場の並び [(撮る物の名前, 道, 始め, 終わり)]。届いていない物も並べる（その間は今の地）。"""
    from demo import script

    out, t = [], 0.0
    for shot, secs in script.SLOTS.get(name, {}).get("hands", ()):
        out.append((shot, pathlib.Path(root) / script.SLOT_DIR / f"{shot}{script.HANDS_EXT}", t, round(t + secs, 3)))
        t += secs
    return out


def split_frames(path, seconds, into):
    """手の映像の頭から seconds 秒を、1 秒 FPS 枚の絵に割る。大きさは W×H に切りそろえる（縦横を別々に伸ばさない）。"""
    import subprocess

    into.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-t", f"{seconds}", "-i", str(path), "-an",
                        "-vf", f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "-q:v", "2",
                        f"{into}/%05d.jpg"], capture_output=True, text=True)
    frames = sorted(into.glob("*.jpg"))
    return frames if r.returncode == 0 and frames else None


def _render(name, cues, argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    a = ap.parse_args(argv)
    if name == "ask":
        scene = AskCard(cues)
    else:
        # 前は、札の字が哲学の記録（本人の言葉）と語りの全文に一字も違わない事を見て止めた。一般的な言い方にした（本人の言葉 11-07・
        # 窓口の決め (1) A・(3)）ので、引用の照合は外した。使わない言い方の床（NOT_SAID）はそのまま
        if name in ALL and says_restored(ALL[name]):
            print(f"検査できない: 札 {name} に使わない言い方がある（{'・'.join(NOT_SAID)}）", file=sys.stderr)
            return 4
        pic, hands = None, []
        here = [(shot, path, t0, t1) for shot, path, t0, t1 in hands_slots(name) if path.exists()]
        for shot, path, t0, t1 in here:
            problem = hands_problem(path, t1 - t0)
            if problem:
                print(f"検査できない: 手の映像 {shot}（{name}）: {problem}", file=sys.stderr)
                return 4
        if here:
            import shutil
            import tempfile

            if not shutil.which("ffmpeg"):
                print("検査できない: ffmpeg が無い", file=sys.stderr)
                return 4
            tmp = tempfile.TemporaryDirectory(prefix="hands-")
            for shot, path, t0, t1 in here:
                frames = split_frames(path, t1 - t0, pathlib.Path(tmp.name) / shot)
                if frames is None:
                    print(f"検査できない: 手の映像 {shot}（{name}）を割れない", file=sys.stderr)
                    return 4
                hands.append((frames, t0, t1))
        if name in PICTURED and not hands:
            from demo import scene2  # 場面 2 がこの札の字を読むので、ここで読む

            rec, _ = scene2.load_record()
            spread = scene2.load_page(pathlib.Path(a.cache), rec)
            if spread is None:
                return 4
            pic = picture(scene2.page_layer(spread, rec))
        scene = ChunkCard(name, cues, pic, hands)
    if a.sheet:
        d = scene.duration
        contact_sheet(scene, a.sheet, tuple(round(d * k, 2) for k in (0.1, 0.25, 0.4, 0.55, 0.7, 0.8, 0.9, 0.95, 0.99)))
    return render(scene, pathlib.Path(a.out))


_MODULES = {}


def scene_module(name):
    """他の場面（demo.flip など）と同じ形の入口を返す。CUES は同じ物を返す（曲の拍合わせが中の時刻を動かすため）。"""
    if name not in _MODULES:
        cues = cues_of(name)
        _MODULES[name] = types.SimpleNamespace(CUES=cues, DURATION=seconds_of(name), main=lambda argv=None: _render(name, cues, argv))
    return _MODULES[name]


if __name__ == "__main__":
    names = [n for n in ALL if n not in ("scene2", "core_loop")] + ["ask"]
    if len(sys.argv) < 2 or sys.argv[1] not in names:
        print(f"検査できない: 札の名前は {'・'.join(names)}", file=sys.stderr)
        sys.exit(4)
    sys.exit(scene_module(sys.argv[1]).main(sys.argv[2:]))
