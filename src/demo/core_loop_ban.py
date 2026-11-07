"""場面 15（core_loop）の別版の試作: 4 つの輪の図の代わりに、御来迎の型紙の版 v10 → v14 の紙が 1 枚ずつ左から並んでいく。

使い方: python -m demo.build … --swap core_loop=core_loop_ban（本線の台本 demo.script は触らない。差し替えの設定だけで入れ替わる）
exit: 0 = 書き出せた / 4 = 書き出せない（demo.flip.render と同じ）

決めた事と理由:
- 本人の言葉（11-07 朝）「ワークショップ2回や型紙の試作を繰り返し、型紙のが改善されたことは面白いと思う。バージョンをサイトで明示したい。
  デモ動画でもこのことをはなして、型紙はもちろんエンジンも改善する仕組みになっていることを言いたいし示したい」の「示す」所の試作。
  窓口の決め方（11-07）「デモは版が変わる場面ひとつの別版」「本線の台本は触らない・差し替えの設定で」「完成した形で1回見せる」。
- 変えるのは絵だけ。秒（DURATION）と字幕（つなぎ 2 と「いま作っているところです」）と合図（CUES）は core_loop の物をそのまま使う
  （写さずに同じ物を読む。曲の拍合わせが core_loop の合図を動かすと、この別版も一緒に動く）。公的調査の数の 1 行も同じ下の帯に出す。
- 並べるのは御来迎の v10 → v14 の 5 枚だけ（窓口の決定 11-07。虎はこの場面に入れない）。1 枚ずつ左から、版の順に現れる。
  最後の v14 は 3 つ目の字幕「次の型紙を少しずつよくしていきます。」が出る所で現れる（字幕の言う事と絵を合わせる）。
- 紙の下の札は「型紙の版」と数だけ（窓口の決定 11-07: 型紙の版とエンジンの版を言い分ける。紙の題に刷る数と同じ）。
- エンジンの版の数は、out/demo/ban/engine.json（{"engine_version": N}）がある時だけ出す。数はエンジンが出す改善の歴史の表から
  人が置く（ここで数を作らない）。無い時は何も出さない。
- 実物の写真は入れない（どの写真が何の版の物かを、台帳と記録で人が確かめてから。窓口の決め 11-07）。
- 窓口が採った字幕「ワークショップを 2 回して、型紙の版を重ねた。」は、どこから約 4.4 秒を持ってくるかが決まっていないので、
  EXTRA_LINE を空のままにして出さない（決まったら EXTRA_LINE に字を入れ、秒の出所を台本で決める）。
- 紙の絵は demo.ban_take_in が out/demo/ban/ に置く（git の外）。無い版は点線の枠と札だけにして、書き出しは止めない（試験で見る）。
- 案内役 B の歩き（demo.guide の core_loop の計画）は、書き出しの道の名が core_loop のままなので、そのまま重なる（紙の列の下を歩く）。
"""
import argparse
import json
import pathlib

from PIL import Image, ImageDraw

from demo import core
from demo.ban_take_in import BAN_DIR, SOURCES
from demo.flip import H, PAPER, SHU, SUMI, W, contact_sheet, ease, fade, render, text
from demo.words import chunk_alpha, chunks_of, draw_chunk, draw_stat

NAME = "core_loop"                  # 差し替える場面。字幕・数の行・案内役・後入れの札はこの名前で引く
BASE = core.scene_module(NAME)
CUES = BASE.CUES                    # 同じ物（写さない）。拍合わせの書き込みが両方に効く
DURATION = BASE.DURATION
CHUNKS = chunks_of(NAME)
VERSIONS = tuple((name, int(name.rsplit("-v", 1)[1])) for name, _ in SOURCES)   # (置き場の名前, 型紙の版)
LABEL = "型紙の版 {n}"
ENGINE_LABEL = "エンジンの版 {n}"
ENGINE_FILE = BAN_DIR / "engine.json"
EXTRA_LINE = ""                     # 窓口が採った字幕の置き場（秒の出所が決まるまで空）

# 紙の並び。5 枚を 1 段に大きく。字幕（上 111〜290）と数の行の帯（下 988〜）と案内役の歩く所（下 814〜994）の間に収める。
# 札の字が案内役の頭に近づかないよう、段の頭を 318 から 296 に上げた（11-07 にコマで見た）。
SHEET_W, SHEET_H, GAP = 300, 424, 60
ROW_TOP = 296
ROW_X0 = (W - (len(VERSIONS) * SHEET_W + (len(VERSIONS) - 1) * GAP)) // 2
LABEL_Y = ROW_TOP + SHEET_H + 22
ENGINE_Y = LABEL_Y + 52
APPEAR = 0.8                        # 1 枚が現れる秒
RISE = 18                           # 現れる時に下から上がる量（px）。入口のせり上がりと同じ静かな動き


def engine_version(path=None):
    """エンジンの版の数。置いた表が無い・読めない時は None（数を作らない）。"""
    p = pathlib.Path(path or ENGINE_FILE)
    try:
        n = json.loads(p.read_text(encoding="utf-8")).get("engine_version")
    except (OSError, ValueError, AttributeError):
        return None
    return n if isinstance(n, int) and n > 0 else None


def _load(name, folder=None):
    p = pathlib.Path(folder or BAN_DIR) / f"{name}.png"
    if not p.exists():
        return None
    with Image.open(p) as im:
        im = im.convert("RGB")
        im.thumbnail((SHEET_W, SHEET_H))
        return im.copy()


def _dashed_rect(d, box, color, dash=12):
    l, t, r, b = box
    for x in range(l, r, dash * 2):
        d.line((x, t, min(x + dash, r), t), fill=color, width=2)
        d.line((x, b, min(x + dash, r), b), fill=color, width=2)
    for y in range(t, b, dash * 2):
        d.line((l, y, l, min(y + dash, b)), fill=color, width=2)
        d.line((r, y, r, min(y + dash, b)), fill=color, width=2)


class BanCard:
    """御来迎の型紙の版が左から並んでいく絵。字幕は core_loop の LoopCard と同じ置き方で出す。"""

    def __init__(self, cues, folder=None, engine=None):
        self.cues = cues
        self.duration = DURATION
        self.chunks = CHUNKS
        self.sheets = [_load(name, folder) for name, _ in VERSIONS]
        self.engine = engine_version(engine) if engine is not None else engine_version()

    def appear_at(self, i):
        """i 枚目が現れ始める秒。1 枚目は輪が現れていた合図（rings）の頭、最後は 3 つ目の字幕の頭。合図を読むので拍に乗る。"""
        first = self.cues["rings"][0]
        last = self.cues[f"c{min(2, len(self.chunks) - 1)}"][0]
        n = len(VERSIONS)
        return first + (last - first) * i / max(1, n - 1)

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        n = len(self.chunks)
        for i, lines in enumerate(self.chunks):
            v = chunk_alpha(self.cues, n, i, t)
            if v > 0:
                draw_chunk(d, lines, W // 2, 200, 56, v)
        shown = [ease((t - self.appear_at(i)) / APPEAR) for i in range(len(VERSIONS))]
        newest = max((i for i, v in enumerate(shown) if v > 0), default=None)
        for i, ((name, ban), sheet) in enumerate(zip(VERSIONS, self.sheets)):
            v = shown[i]
            if v <= 0:
                continue
            x = ROW_X0 + i * (SHEET_W + GAP)
            y = ROW_TOP + round(RISE * (1 - v))
            if sheet is None:
                _dashed_rect(d, (x, y, x + SHEET_W, y + SHEET_H), fade(SUMI, 0.4 * v))
            else:
                ox, oy = x + (SHEET_W - sheet.width) // 2, y + (SHEET_H - sheet.height)
                img.paste(Image.blend(Image.new("RGB", sheet.size, PAPER), sheet, v), (ox, oy))
                # 一番新しく現れた紙だけ朱の細い枠。前の紙は墨の薄い枠に戻る（どれが今の版かを絵で分ける）
                frame_color = fade(SHU, 0.8 * v) if i == newest else fade(SUMI, 0.3 * v)
                d.rectangle((ox - 1, oy - 1, ox + sheet.width, oy + sheet.height), outline=frame_color, width=2 if i == newest else 1)
            text(d, (x + SHEET_W // 2, LABEL_Y), LABEL.format(n=ban), 30, fade(SHU if i == newest else SUMI, v), False, "ma")
        last = shown[-1]
        if self.engine and last > 0:
            text(d, (ROW_X0 + len(VERSIONS) * SHEET_W + (len(VERSIONS) - 1) * GAP, ENGINE_Y), ENGINE_LABEL.format(n=self.engine),
                 28, fade(SHU, 0.85 * last), False, "ra")
        if EXTRA_LINE and last > 0:
            text(d, (W // 2, ENGINE_Y), EXTRA_LINE, 34, fade(SUMI, last), False, "ma")
        return draw_stat(img, NAME, t)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）。名前は core_loop.mp4（案内役と後入れの札を同じ名で引くため）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", help="使わない（core の場面と同じ引数を受けるため）")
    a = ap.parse_args(argv)
    scene = BanCard(CUES)
    if a.sheet:
        d = scene.duration
        contact_sheet(scene, a.sheet, tuple(round(d * k, 2) for k in (0.05, 0.15, 0.3, 0.42, 0.55, 0.65, 0.75, 0.88, 0.99)))
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    import sys

    sys.exit(main())
