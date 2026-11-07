"""部品と検査結果の型。雛形の族が変わっても共通に使う形だけをここに置く。"""
import re
from dataclasses import dataclass, field

SAFE_NAME = re.compile(r"[A-Za-z0-9_-]{1,80}")


class ToolMissing(Exception):
    """検査そのものができない（exit 4）。落ちた（exit 3）と混ぜないために分ける。"""


def check_name(value, what):
    """値をパスにつなぐ前に、決まった形かを確かめる。点も斜線も通さないので、決めた置き場の外を指せない（#30）。
    つないだ後のパスを比べる形より、理由の文が読みやすく、シンボリックリンクの解き方にも左右されない。"""
    if not (isinstance(value, str) and SAFE_NAME.fullmatch(value)):
        raise ToolMissing(f"{what} の形が違う（英数字と - と _ で 80 字まで）: {str(value)[:80]!r}")
    return value


@dataclass
class Failure:
    floor: str
    where: str
    message: str

    def line(self):
        return f"FAIL {self.floor} [{self.where}] {self.message}"


@dataclass
class Part:
    """部品 1 つ。座標は部品の左上を原点にした mm。"""
    number: int
    key: str
    name: str
    outline: list  # 外形の頂点。切る線
    label_xy: tuple = (2, 2)
    label: str = ""
    # 札を何行かに分けて刷る時の [(字, x, y), ...]（部品の左上からの mm）。空なら label を label_xy に 1 行で刷る（今までと同じ）。
    # 細い部品に長い名を縦に並べるため（虎の 5 重りの腕は幅 8mm で、名が 1 行に入らない。制作者の決定 2026-11-06「5 重りの腕」にそろえる）。
    # label は部品の名の札の字として持ち続ける（試験と知らせが読む）
    label_lines: list = field(default_factory=list)
    valley: list = field(default_factory=list)  # ((x1,y1),(x2,y2))
    mountain: list = field(default_factory=list)
    glue: list = field(default_factory=list)  # 糊代の多角形
    cuts: list = field(default_factory=list)  # 中を切る矩形 (x,y,w,h)
    # 中を切る円 (x,y,r)。虎の首の穴（実物の写真は丸い穴、2026-11-06）のように、カッターで切り抜く丸。軸の穴（holes）は竹串の先であける
    # 小さな穴の印なので、大きな丸い切り抜きを holes に入れると「竹串であける」穴と読まれる。そのため別に持つ
    round_cuts: list = field(default_factory=list)
    holes: list = field(default_factory=list)  # 軸の穴 (x,y,r)
    # 描き直しの絵。{"kind": "poly"|"line", "pts": [...], "fill": 色, "stroke": 色, "sw": 太さ}。折り線や糊代をまたがない。
    # {"kind": "mark", "pts": [...], "closed": 真偽} は組み立ての位置の印で、色と線の形は描く所が決める（切る線・折る線と紛れない形）
    art: list = field(default_factory=list)
    # 見える面の折り線を刷らず、絵の色の境で折る部品（v9）。折り線のデータは検査のために持ち続ける。
    hide_folds: bool = False
    # hide_folds でも刷る折り線。隠れる所（糊代の境など）で、色の境が無く、線が無いと折る所が分からない物だけ。
    print_folds: list = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0

    @property
    def width(self):
        return max(p[0] for p in self.outline) - min(p[0] for p in self.outline)

    @property
    def height(self):
        return max(p[1] for p in self.outline) - min(p[1] for p in self.outline)


@dataclass
class TextBox:
    """置いた文字 1 行、または物差しのような文字扱いの塊（text が None）。"""
    x: float
    y: float
    w: float
    h: float
    text: str | None
    size: float = 3.0
    owner: str | None = None  # 部品の中のラベルなら部品の key
