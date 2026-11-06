"""部品と検査結果の型。雛形の族が変わっても共通に使う形だけをここに置く。"""
from dataclasses import dataclass, field


class ToolMissing(Exception):
    """検査そのものができない（exit 4）。落ちた（exit 3）と混ぜないために分ける。"""


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
    # 札を縦に 1 字ずつ積む（textfit.stack）。横書きでは枠に入らない細い部品に、長い名を入れる時だけ（虎の 5 重りの腕、本人の決定 11-07）。
    # label_xy は積んだ札の左上。札の字（label）は横の時と同じ字のまま持つので、札の名を読む所（部品表の試験など）は変わらない。
    label_vertical: bool = False
    valley: list = field(default_factory=list)  # ((x1,y1),(x2,y2))
    mountain: list = field(default_factory=list)
    glue: list = field(default_factory=list)  # 糊代の多角形
    cuts: list = field(default_factory=list)  # 中を切る矩形 (x,y,w,h)
    holes: list = field(default_factory=list)  # 軸の穴 (x,y,r)
    # 描き直しの絵。{"kind": "poly"|"line", "pts": [...], "fill": 色, "stroke": 色, "sw": 太さ}。折り線や糊代をまたがない
    art: list = field(default_factory=list)
    # 見える面の折り線を刷らず、絵の色の境で折る部品（v9、本人の決定 d）。折り線のデータは検査のために持ち続ける。
    hide_folds: bool = False
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
