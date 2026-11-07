"""玩具の頁の「これまでの記録」に、ワークショップで作られた物の写真を出す（本人の言葉 11-07 夜
「おもちゃ毎のつくるにあるこれまでの記録にはワークショップで作られた写真を載せて欲しい」）。

- どの写真をどの玩具に出すかは data/workshop_photos.json の表で決める。写真の写りから機械で決めない（読みの弱い写真を
  ほかの玩具の頁に出さないため。表に入れたのは確かめ表の「写っている物」と答えの名で照らせた物だけ）
- 写真は repo の docs/process/trials/photos（本人の決定で全部を公開してよい・顔なし・撮影の情報は外し済み）。
  合言葉なしの公開の場にも出す（本人の直の指示。人が上げた記録の写真とは違い、公開の決めが済んだ物）
- 頁には小さい写し（web.made.small_photo・1 枚 100KB 以下の線）だけを出す。元の写真（300〜660KB）は読ませない
- 人の書いた字（感想の文）は出さない。字は前からある alt「作った物の写真」だけ（新しい字を足さない）
"""
import functools
import json
import re
from html import escape as esc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "data/workshop_photos.json"
PHOTOS = ROOT / "docs/process/trials/photos"
FILE = re.compile(r"\d{8}/p\d{2}\.jpg")  # 表の道の形（日の置き場/p番号.jpg）。表の外の道は返さない


@functools.lru_cache(maxsize=1)
def _rows(mtime=None):
    return json.loads(TABLE.read_text(encoding="utf-8")).get("photos", [])


def rows():
    return _rows(TABLE.stat().st_mtime) if TABLE.exists() else []


def files(sid):
    """その玩具に出す写真の道（表の順）。"""
    return [r["file"] for r in rows() if r["toy"] == sid and FILE.fullmatch(r["file"]) and (PHOTOS / r["file"]).exists()]


def known(file):
    """表に載っていて、置き場に在る写真か（道を返す前の見張り）。"""
    return FILE.fullmatch(file) is not None and any(r["file"] == file for r in rows()) and (PHOTOS / file).exists()


def small(file):
    from .made import small_photo

    return small_photo(PHOTOS / file) if known(file) else None


def strip(sid):
    """「これまでの記録」の頭に置く写真の並び。写真が無い玩具は空（節に場所を取らない）。"""
    thumbs = "".join(f'<img src="/workshop/{esc(f)}/small" alt="作った物の写真" loading="lazy" decoding="async">' for f in files(sid))
    return f'<div class="strip workshop">{thumbs}</div>' if thumbs else ""
