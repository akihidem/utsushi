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

from demo.flip import CLOSING, H, PAPER, ROOT, SERIF, SHU, SUMI, W, contact_sheet, ease, fade, render, text

PHILOSOPHY = ROOT / "docs/process/philosophy.md"
NARRATION = ROOT / "docs/demo/opening-narration.txt"
# 問いの文面。本人の決定（11-05、docs/demo/plan.md の 4）。
ASK = "あなたなら、何を作りますか。"
FROM = "本人の言葉（11-05）"
RATE, MIN_CHUNK = 5.0, 2.0     # 1 秒に読ませる字の上限と、短いかたまりでも置く秒
LEAD, TAIL = 0.4, 0.2          # 場面の頭と終わりの余り（場面の溶けと重なる所）
DISSOLVE = 0.5                 # かたまりが消える・現れる秒。前が消えてから次が現れるので、替わり目は 1 秒
EPS = 1e-9                     # 小数の誤差で切り上げが 0.1 秒増えないようにする
# 本人の言葉の札: (かたまり…)。かたまりは行の並び。つなぐと記録の引用の 1 行になる。
CARDS = {
    "word_touch": (("AIが良くなるのは副次的なもので、",), ("みんなが手で実際に作ること",), ("その楽しさに気づくことが最初。",)),
    "word_ai": (("型紙は不完全でうまく動かないけど",), ("それを人間が工夫で乗り切る過程を",), ("AIにフィードバックして",), ("型紙が改善される",)),
}
# 本人の語り。文の中の字は変えない。かたまりの切れ目は読点（床で見る）。scene2 は図と歌の場面に出す分。
TALKS = {
    "talk_toys": (("江戸時代のおもちゃというものは、",), ("紙と木と竹と糸でできていて、",), ("子供が壊してもすぐ自分で直せる。",), ("そこに喜びがある。",)),
    "talk_lost": (("しかし、その江戸時代のおもちゃは、",), ("もう大半が失われていて、",), ("それを作る職人も", "もうほとんど残っていないという", "問題がある。")),
    "scene2": (("今唯一残ってるのは、", "江都二色という、"), ("おもちゃが狂歌と", "一緒に書かれた書物だけで、"),
               ("そこにはおもちゃの絵と", "そのおもちゃの遊び方にちなんだ", "狂歌が書かれているけれども、"), ("どうやって遊ぶのか、",),
               ("またどんなものでできていたのか", "ってことまではわからない。")),
    "talk_physics": (("物理の世界では、", "トイモデルという風に言って、"), ("自分で扱えるおもちゃを", "こねくり回して、"),
                     ("自分で作って、", "自分の手のひらで考えるという", "やり方が、"), ("考え方がある。",)),
    "talk_claude": (("そしてそこにクロードが", "寄り添っている。"), ("そういうサービスを", "作りたいと思って、"), ("今回のサービスを作った。",)),
}
# つなぎの文（本人の決定 11-05）。つなぎ 1 は今の台本から外してある（demo.script の LEFT_OUT）。つなぎ 2 は core_loop に出す。
BRIDGE = (("むかしの子どもも、今の子どもも、",), ("もらったおもちゃより、",), ("それを包んでいた紙や", "リボンのひもで"), ("遊んでしまうことがあります。",))
BRIDGE2 = (("作ったものを持ちよると、",), ("AI もそれを見て、",), ("次の型紙を少しずつ", "よくしていきます。"))
NOW_LINE = "いま作っているところです"      # AI はまだ動いていないので、つなぎ 2 と一緒に出す（本人の決定 11-05）
ALL = {**CARDS, **TALKS, "bridge": BRIDGE, "close": ((CLOSING[0],), (CLOSING[1],)), "core_loop": (*BRIDGE2, (NOW_LINE,))}
MARKED = (*CARDS, *TALKS)      # 本人の言葉の印を付ける札
# デモと外に出す文で使わない言い方（本人の決定 11-05）。継承を軸にし、「復活」を「昔の作り方を取り戻した」の意味で使わない。
# 前からの線「失われた技術を取り戻すとは書かない」を残す。語りの全文には「復活」の文があるが、札に選ばない。
NOT_SAID = ("復活", "取り戻")
ASK_SECONDS = 5.0
ASK_SIZE = 72
# 札ごとの置き方。図を右に置く札は、字を左に寄せて小さくする。ink は図の濃さ（始め, 終わり）。
STYLES = {"talk_toys": {"size": 60, "cx": 640, "ink": (0.85, 0.85)}, "talk_lost": {"size": 60, "cx": 640, "ink": (0.85, 0.12)},
          "talk_physics": {"size": 64}, "close": {"size": 64}, "bridge": {"size": 64}}
PICTURED = ("talk_toys", "talk_lost")     # 図（場面 2 と同じ御来迎の頁）を右に置く札。職人の動画が来るまで、作り物で埋めない
PIC_H, PIC_X = 860, 1470                  # 図の高さと真ん中


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


def chunk_seconds(lines):
    """1 かたまりの秒。1 秒 5 字以下。替わり目の溶けもこの中に入る。"""
    return max(MIN_CHUNK, len("".join(lines)) / RATE)


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
    return math.ceil((LEAD + sum(chunk_seconds(c) for c in chunks_of(name)) + TAIL) * 10 - EPS) / 10


def chunk_alpha(cues, n, i, t):
    """i 番目のかたまりの濃さ。前のかたまりが消えてから次が現れる（字を重ねない）。最後のかたまりは場面の溶けで消える。"""
    v = ease((t - cues[f"c{i}"][0]) / DISSOLVE)
    if i + 1 < n:
        end = cues[f"c{i + 1}"][0]
        v *= 1 - ease((t - (end - DISSOLVE)) / DISSOLVE)
    return v


def draw_chunk(draw, lines, cx, cy, size, v):
    """1 かたまりを、cy を真ん中にして行ごとに描く。"""
    lead = round(size * 1.6)
    top = cy - (len(lines) * lead) // 2
    for j, line in enumerate(lines):
        text(draw, (cx, top + j * lead), line, size, fade(SUMI, v), False, "ma")


def draw_from(draw, cx):
    """本人の言葉の印。札の下に静かに置く。"""
    text(draw, (cx, H - 130), FROM, 30, fade(SHU, 0.75), False, "ma")


def _ink(layer, v):
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda a: round(a * v)))
    return out


def picture(layer):
    """右に置く図を、決めた高さにする。"""
    return layer.resize((round(layer.width * PIC_H / layer.height), PIC_H), Image.LANCZOS)


class ChunkCard:
    """紙の地に字を 1 かたまりずつ出す札。pic を渡すと右に図を置く。"""

    def __init__(self, name, cues, pic=None):
        self.name, self.cues, self.pic = name, cues, pic
        self.chunks = chunks_of(name)
        self.duration = seconds_of(name)
        style = STYLES.get(name, {})
        self.size, self.cx, self.ink = style.get("size", 72), style.get("cx", W // 2), style.get("ink", (1.0, 1.0))

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        if self.pic is not None:
            a, b = self.ink
            lay = _ink(self.pic, a + (b - a) * ease(t / self.duration))
            img.paste(lay, (PIC_X - lay.width // 2, (H - lay.height) // 2), lay)
        draw = ImageDraw.Draw(img)
        for i, lines in enumerate(self.chunks):
            v = chunk_alpha(self.cues, len(self.chunks), i, t)
            if v > 0:
                draw_chunk(draw, lines, self.cx, H // 2 - 30, self.size, v)
        if self.name in MARKED:
            draw_from(draw, self.cx)
        return img


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
            text(ImageDraw.Draw(img), (W // 2, H // 2 - 60), ASK, ASK_SIZE, fade(SUMI, v), False, "ma")
        return img


def fits():
    """札の字が置き場に収まるか（名前 → 右端の余り px）。試験と書き出しの前の確かめに使う。"""
    out = {"ask": W - 160 - ImageFont.truetype(SERIF, ASK_SIZE).getlength(ASK)}
    for name in ALL:
        style = STYLES.get(name, {})
        f = ImageFont.truetype(SERIF, style.get("size", 72))
        room = 2 * style["cx"] - 160 if "cx" in style else W - 160
        out[name] = room - max(f.getlength(s) for lines in chunks_of(name) for s in lines)
    return out


def _render(name, cues, argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    a = ap.parse_args(argv)
    if name == "ask":
        scene = AskCard(cues)
    else:
        if name in CARDS and not in_record((flat(CARDS[name]),)):
            print(f"検査できない: 札 {name} の字が記録（philosophy.md）と違う", file=sys.stderr)
            return 4
        if name in TALKS and not in_narration(TALKS[name]):
            print(f"検査できない: 札 {name} の字が語りの全文（opening-narration.txt）と違う", file=sys.stderr)
            return 4
        if name in ALL and says_restored(ALL[name]):
            print(f"検査できない: 札 {name} に使わない言い方がある（{'・'.join(NOT_SAID)}）", file=sys.stderr)
            return 4
        pic = None
        if name in PICTURED:
            from demo import scene2  # 場面 2 がこの札の字を読むので、ここで読む

            rec, _ = scene2.load_record()
            spread = scene2.load_page(pathlib.Path(a.cache), rec)
            if spread is None:
                return 4
            pic = picture(scene2.page_layer(spread, rec))
        scene = ChunkCard(name, cues, pic)
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
