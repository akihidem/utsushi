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
    valley: list = field(default_factory=list)  # ((x1,y1),(x2,y2))
    mountain: list = field(default_factory=list)
    glue: list = field(default_factory=list)  # 糊代の多角形
    cuts: list = field(default_factory=list)  # 中を切る矩形 (x,y,w,h)
    # 中を切る円 (x,y,r)。虎の次の組（tora-v6）の首の穴（実物の写真は丸い穴、2026-11-06）のように、カッターで切り抜く丸。軸の穴（holes）は
    # 竹串の先であける小さな穴の印なので、大きな丸い切り抜きを holes に入れると「竹串であける」穴と読まれる。そのため別に持つ（型紙エンジンと同じ）
    round_cuts: list = field(default_factory=list)
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
