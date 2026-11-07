"""後入れの枠（本人の指示 11-07「本人の声の6文と、本物の Claude の返事の場面は後入れで空けておくこと」）。

決めた事と理由:
- 後入れの所は、秒を変えずにそのまま残し、画面の右上に小さな札を重ねて「後入れ」と分かるようにする（仮の地）。字幕と場面の作りは変えない
- 本物の Claude の返事は、場面 8（core_make）の「止まったら、そのまま声か字で聞ける」の段（合図 ask から場面の終わり）に札を出す
  （入れる場面の推しは 8 のこの所。本物が来たら --clip で差し替え、この札は消える）
- 語りの 6 文（A1〜A6）は、声の置き場に何も無い時だけ「本人の声は後入れ」の札を出す。読み上げは合成（AivisSpeech）のまま本番にする
  （本人の決定 11-07「読み上げは合成のまま。合成であることの書き置きは動画の外（提出の書類か README）です」）ので、声が入っていれば札は出さない。
  前は仮の読み上げの印（VOICE_PROVISIONAL）で「仮の読み上げ」の札を出していた
- 札の字は作る側の仮の字で、本番の動画には残さない（本人の声と本物の返事が入れば出なくなる）。案内役と同じく、書き出しの通り道（flip.render）で重ねる
"""
import pathlib

from PIL import ImageDraw

from demo.flip import ROOT, SUMI, W, text

LABEL_CLAUDE = "本物の Claude の返事は後入れ"
LABEL_VOICE = "本人の声は後入れ"
SIZE, PAD = 22, 10


def _voice_label(name, root=ROOT):
    from demo import script

    voices = script.SLOTS.get(name, {}).get("voice", ())
    if not voices:
        return None
    slot = pathlib.Path(root) / script.SLOT_DIR
    if not all((slot / f"{v}{script.VOICE_EXT}").exists() for v in voices):
        return LABEL_VOICE
    return None


def label(name, t, root=ROOT):
    """場面 name の時刻 t に出す札の字。出さない時は None。"""
    if name == "core_make":
        from demo import core

        if t >= core.CUES_ALL["core_make"]["ask"][0]:
            return LABEL_CLAUDE
        return None
    return _voice_label(name, root)


def overlay(img, name, t, root=ROOT):
    word = label(name, t, root)
    if not word:
        return img
    out = img.copy()
    d = ImageDraw.Draw(out)
    from PIL import ImageFont

    from demo.flip import SERIF

    from demo import english

    en_word = english.en(word)   # 英語字幕（札も日本語と英語を 1 組で。demo.english）
    en_size = english.size_of(SIZE)
    w = max(ImageFont.truetype(SERIF, SIZE).getlength(word), ImageFont.truetype(SERIF, en_size).getlength(en_word))
    x1, y0 = W - 28, 24
    x0, y1 = round(x1 - w - PAD * 2), y0 + SIZE + en_size + 6 + PAD * 2
    # 点線の枠（仮の地。字の札と見分ける）
    for x in range(x0, x1, 12):
        d.line((x, y0, min(x + 6, x1), y0), fill=SUMI, width=2)
        d.line((x, y1, min(x + 6, x1), y1), fill=SUMI, width=2)
    for y in range(y0, y1, 12):
        d.line((x0, y, x0, min(y + 6, y1)), fill=SUMI, width=2)
        d.line((x1, y, x1, min(y + 6, y1)), fill=SUMI, width=2)
    text(d, (x0 + PAD, y0 + PAD), word, SIZE, SUMI, False)
    text(d, (x0 + PAD, y0 + PAD + SIZE + 6), en_word, en_size, SUMI, False)
    return out


class Later:
    """場面に後入れの札を重ねる包み（demo.guide.Guided と同じ形）。"""

    def __init__(self, scene, name):
        self.scene, self.name = scene, name

    def frame(self, t):
        return overlay(self.scene.frame(t), self.name, t)

    def __getattr__(self, k):
        return getattr(self.scene, k)
