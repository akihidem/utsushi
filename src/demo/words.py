"""言葉の札: 本人の言葉を紙の地に出す場面と、つなぎの字幕の札と、終わりの字幕の札と、最後の問いの札。

使い方: python -m demo.words <札の名前> --out <repo の外の場所>/word.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 画像が取れない・ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 本人の決定（11-05）「哲学よりの動画にして」。軸を機能の説明から本人の言葉へ移した。
- 本人の言葉（11-05 夕）で順番が決まった。手で作る楽しさに気づく事が最初で、AI が良くなるのは後。札 word_touch をその言葉の全文にした。
  前の札（word_make・word_fix・word_who と、同じ日の少し前の言葉）は台本から外した。外したのは動画の札だけで、記録の言葉は消していない（過程の記録として残す）。
- 本人の言葉は docs/process/philosophy.md の字のまま出す。札の行をつなぐと、記録の引用の 1 行と一字も違わない事を
  床（tests/test_demo_words.py）が見る。行の切れ目は読みやすさのためで、字は足さず引かない（括弧も足さない）。
  短く切った文は本人の言葉と書かない決まりなので、ここには全文だけを置く。
- 問いの文面は本人の決定（11-05）。説教くさくしないよう、見ている人を問い詰めない形にした。
  本人の言葉の記録の引用ではないので、言葉の札の印（FROM）は付けない。
- 本人の決定（11-05）: つなぎ 1 の文は案のまま決まった。字を変えず、図と歌の場面の次、本人の言葉の札の前に出す。本人の言葉の札にはしないので、その印を付けない。
- 本人の決定（11-05）: 初めと終わりの字幕は同じ文。終わりは、この字幕 → 問いの順にする。字と置き場は demo.flip の 1 か所から読む（初めと終わりで食い違わないため）。
  本人が決めた字幕で、言葉の記録の引用ではないので、言葉の札の印は付けない。
- 隅で北斎の人物を重ねて動かす。「絵は動きを止めて残した」で始まる筋を字の間も続けるため。薄くして字を先に読ませる。
  問いの札には置かない。考える間に動く物を置かない（音も止める。demo.beat）。
- 行は順に現れる。出る時刻は CUES にあり、拍に乗る（仮の拍も、曲の拍合わせも CUES だけを読む）。
- frame(t) は時刻だけから 1 コマを描く純関数（場面 1 と同じ）。
"""
import argparse
import pathlib
import sys
import types

from PIL import Image, ImageDraw, ImageFont

from demo.flip import CLOSING, H, PAPER, ROOT, SERIF_BOLD, SHU, SUMI, W, Scene, contact_sheet, draw_closing, ease, fade, ink_layer, load_page, render, text

PHILOSOPHY = ROOT / "docs/process/philosophy.md"
# 問いの文面。本人の決定（11-05、docs/demo/plan.md の 4）。
ASK = "あなたなら、何を作りますか。"
FROM = "本人の言葉（11-05）"
# 札ごとの (行, 長さの秒, 行の間の秒)。長さは字を 1 秒に 5 字で読む見当に、最後に止めて読む間を足して決めた。
CARDS = {
    "word_touch": (("AIが良くなるのは副次的なもので、", "みんなが手で実際に作ること", "その楽しさに気づくことが最初。"), 11.0, 3.0),
    "word_ai": (("型紙は不完全でうまく動かないけど", "それを人間が工夫で乗り切る過程を", "AIにフィードバックして", "型紙が改善される"), 11.0, 1.6),
}
ASK_SECONDS = 7.0
CLOSE_SECONDS = 5.0                    # 30 字。場面 1 で 1 度見た字なので、1 秒に 5 字の見当より少し短い
# つなぎ 1（本人の決定 11-05）。字は変えない。行の切れ目だけで分ける。
BRIDGE = ("むかしの子どもも、今の子どもも、", "もらったおもちゃより、", "それを包んでいた紙やリボンのひもで", "遊んでしまうことがあります。")
BRIDGE_SECONDS, BRIDGE_STEP, BRIDGE_LEADING = 12.0, 2.6, 96   # 58 字を 1 秒に 5 字で読む見当
# 核の一周の 3 段（本人の言葉 11-05「今話してるこの部分が今回のハッカソンの核になる！！」の中身を窓口が整理した文）。本人の言葉の印は付けない。
STEPS = (("①", "仮説を見ながら、自分の考えを話す"), ("②", "作りながら、工夫を話す"), ("③", "できた物を上げて、工夫と考えを残す"))
SIZE, LEADING, LEFT = 66, 112, 230     # 字の大きさ・行の間（px）・字の左端
ASK_SIZE = 72
FIG_FPS = 3                            # 隅の人物を替える速さ。場面 1 の半分にして、字を読むのを邪魔しない
FIG_TALL, FIG_X, FIG_BASE, FIG_INK = 230, W - 230, H - 90, 0.55
MODIFICATION = "改変: 頁から人物を 1 人ずつ切り出して順に重ねた。絵の線は描き直していない"


def step_badge(draw, n, alpha=1.0):
    """右上の段の印。場面が替わっても今どの段かが分かるように、画面の場面にも同じ形で置く。n は 1〜3。"""
    mark, words = STEPS[n - 1]
    text(draw, (W - 80, 70), f"{mark} {words}", 32, fade(SHU, alpha), True, "ra")


def record_lines(path=PHILOSOPHY):
    """記録の中の、本人の言葉の引用の行（> で始まる行）。"""
    return [line[2:].strip() for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("> ")]


def in_record(lines, path=PHILOSOPHY):
    """札の行をつないだ文が、記録の引用の 1 行と一字も違わないか。部分一致にしない（切った文を本人の言葉にしないため）。"""
    return "".join(lines) in record_lines(path)


def cues_of(name):
    """札の合図の表。行ごとに 0.7 秒で現れる。"""
    if name in ("ask", "close"):
        return {"in": (0.0, 1.4)}
    lines, step = (BRIDGE, BRIDGE_STEP) if name == "bridge" else (CARDS[name][0], CARDS[name][2])
    return {"page": (0.0, 0.3), **{f"line{i}": (0.3 + i * step, 1.0 + i * step) for i in range(len(lines))}}


def seconds_of(name):
    return {"ask": ASK_SECONDS, "close": CLOSE_SECONDS, "bridge": BRIDGE_SECONDS}[name] if name in ("ask", "close", "bridge") else CARDS[name][1]


def _ink(layer, v):
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda a: round(a * v)))
    return out


class Card:
    """本人の言葉の札。隅の人物は頁から切り出す（場面 1 と同じ 18 人・同じ順）。"""

    def __init__(self, name, cues, page=None, rec=None):
        self.name, self.cues, self.rec = name, cues, rec
        self.lines = CARDS[name][0]
        self.duration = seconds_of(name)
        self.figs = []
        if page is not None:
            base = Scene(page, rec)
            figs = dict(base.figs)
            k = FIG_TALL / max(g.height for g in figs.values())
            self.figs = [ink_layer(figs[fid], k) for fid in base.order]
        self.first = sorted(CARDS).index(name) * 5  # 札ごとに違う人物から始める

    def _alpha(self, t, cue):
        a, b = self.cues[cue]
        return ease((t - a) / (b - a))

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        if self.figs:
            lay = self.figs[(self.first + int(t * FIG_FPS)) % len(self.figs)]
            lay = _ink(lay, FIG_INK)
            img.paste(lay, (FIG_X - lay.width // 2, FIG_BASE - lay.height), lay)
        n = len(self.lines)
        top = (H - 120 - n * LEADING) // 2
        ink = self._alpha(t, "line0")
        draw.rectangle((LEFT - 40, top + 8, LEFT - 32, top + n * LEADING - 30), fill=fade(SHU, ink))
        for i, line in enumerate(self.lines):
            v = self._alpha(t, f"line{i}")
            if v > 0:
                text(draw, (LEFT, top + i * LEADING), line, SIZE, fade(SUMI, v), True)
        last = self._alpha(t, f"line{n - 1}")
        text(draw, (LEFT, top + n * LEADING + 8), FROM, 30, fade(SHU, last), True)
        if self.rec:
            text(draw, (80, H - 50), f'図 {self.rec["title"]}（{self.rec["publication"]}）国立国会図書館（PDM）　{MODIFICATION}', 22, fade(SUMI, 0.7))
        return img


class BridgeCard:
    """つなぎの字幕。紙の地に字だけで、行は順に現れる。本人の言葉の札と見分けが付くよう、朱の線と印を付けない。"""

    def __init__(self, cues):
        self.cues = cues
        self.duration = BRIDGE_SECONDS

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        top = (H - len(BRIDGE) * BRIDGE_LEADING) // 2 - 30
        for i, line in enumerate(BRIDGE):
            a, b = self.cues[f"line{i}"]
            v = ease((t - a) / (b - a))
            if v > 0:
                text(draw, (W // 2, top + i * BRIDGE_LEADING), line, 58, fade(SUMI, v), True, "ma")
        return img


class CloseCard:
    """終わりの字幕。場面 1 の締めと同じ字を、紙の地に字だけで出す。問いの前に、初めの言葉へ戻すため。"""

    def __init__(self, cues):
        self.cues = cues
        self.duration = CLOSE_SECONDS

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        a, b = self.cues["in"]
        v = ease((t - a) / (b - a))
        if v > 0:
            draw_closing(ImageDraw.Draw(img), v)
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
            text(ImageDraw.Draw(img), (W // 2, H // 2 - 60), ASK, ASK_SIZE, fade(SUMI, v), True, "ma")
        return img


def fits():
    """札の字が動画の幅に収まるか（名前 → 右端の余り px）。試験と書き出しの前の確かめに使う。"""
    f = ImageFont.truetype(SERIF_BOLD, SIZE)
    out = {name: W - 80 - LEFT - max(f.getlength(s) for s in CARDS[name][0]) for name in CARDS}
    out["ask"] = W - 160 - ImageFont.truetype(SERIF_BOLD, ASK_SIZE).getlength(ASK)
    out["close"] = W - 160 - max(ImageFont.truetype(SERIF_BOLD, 58).getlength(s) for s in CLOSING)
    out["bridge"] = W - 160 - max(ImageFont.truetype(SERIF_BOLD, 58).getlength(s) for s in BRIDGE)
    return out


def _render(name, cues, argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    a = ap.parse_args(argv)
    if name in ("ask", "close", "bridge"):
        scene = {"ask": AskCard, "close": CloseCard, "bridge": BridgeCard}[name](cues)
    else:
        if not in_record(CARDS[name][0]):
            print(f"検査できない: 札 {name} の字が記録（philosophy.md）と違う", file=sys.stderr)
            return 4
        page, rec = load_page(pathlib.Path(a.cache))
        if page is None:
            return 4
        scene = Card(name, cues, page, rec)
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
    if len(sys.argv) < 2 or (sys.argv[1] not in CARDS and sys.argv[1] not in ("ask", "close", "bridge")):
        print(f"検査できない: 札の名前は {'・'.join([*CARDS, 'bridge', 'close', 'ask'])}", file=sys.stderr)
        sys.exit(4)
    sys.exit(scene_module(sys.argv[1]).main(sys.argv[2:]))
