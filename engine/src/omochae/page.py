"""頁の大きさと印字域。A4 と B4 のどちらも同じ計算で扱えるよう、寸法を決め打ちにしない。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    name: str
    w: float
    h: float
    # 家庭のプリンタの余白の余裕を見た値。下はフチの送りで欠けやすいので少し広い。
    left: float = 10
    right: float = 10
    top: float = 10
    bottom: float = 12

    @property
    def x0(self):
        return self.left

    @property
    def x1(self):
        return self.w - self.right

    @property
    def y0(self):
        return self.top

    @property
    def y1(self):
        return self.h - self.bottom


PAGES = {"A4": Page("A4", 210, 297), "B4": Page("B4", 257, 364)}
