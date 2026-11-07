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
    """表に載っていて、置き場に在る写真か（道を返す前の見張り）。表は 2 つ: 写真 → 玩具の表（rows）と、もちよるの頁の写真の分けの表（kind_of）。
    分けの表は 43 枚から 11-06 の p28 だけを外した 42 枚なので、道で返すのも公開の決めが済んだ写真だけのまま（p28 は返さない）。"""
    return FILE.fullmatch(file) is not None and (any(r["file"] == file for r in rows()) or kind_of(file) in SHOWN) and (PHOTOS / file).exists()


def small(file):
    from .made import small_photo

    return small_photo(PHOTOS / file) if known(file) else None


def made_photos(sid):
    """その玩具の作例の写真（本人が上げたワークショップの作った物の写真）の小さい写しの道。人が「物だけ」と確かめた物だけ・記録の順。
    玩具の札（sakurei.examples）と、事例の写真（3 バージョン・改善ループの例・参加者の工夫）の両方。ワークショップ全体の写真（玩具が 1 つに決まらない）は入れない。
    本人の言葉 11-08「つくる、虎のこれまでの復元の写真が少ない。」: 前は試行の写真の表だけを読み、作例は作った物の頁の作例の節にしか出なかった。"""
    from . import sakurei

    out = [f"/record/{e['rid']}/media/{name}/small" for e in sakurei.examples() if e["sid"] == sid for name in e["photos"]]
    out += [c["url"] for kind in sakurei.KINDS for c in sakurei.cases(kind) if c["sid"] == sid]
    return out


def strip(sid):
    """「これまでの記録」の頭に置く写真の並び。試行の写真（表の順）の後ろに、その玩具の作例の写真を置く。写真が無い玩具は空（節に場所を取らない）。
    字は前からある alt「作った物の写真」だけ（新しい字を足さない）。どちらも小さい写しで出す。"""
    thumbs = "".join(f'<img src="/workshop/{esc(f)}/small" alt="作った物の写真" loading="lazy" decoding="async">' for f in files(sid))
    thumbs += "".join(f'<img src="{esc(u)}" alt="作った物の写真" loading="lazy" decoding="async">' for u in made_photos(sid))
    return f'<div class="strip workshop">{thumbs}</div>' if thumbs else ""


def gallery(sids):
    """作った物の頁（/gallery）の「他の人が作った物」の節に置く札（本人の見直し 11-07 夜の ⑦「ワークショップで作られたもの、は
    他の人が作ったものなのでそちらにも掲載して」）。玩具ごとに 1 枚の札で、写真の小さい写しと玩具の名（玩具の頁へ）。並びは玩具の並びの順。
    札の形は作例の札（techo_site.sakurei_section の .sakurei-row の figure）にそろえる（同じ頁の中で、写真の板の見え方を 1 つにするため。
    名は .workshop-row で、作例の節の有無を見る試験と混ぜない。見た目の CSS は techo_site の GALLERY_STYLE で .sakurei-row と同じ規則を掛ける）。
    字は玩具の名と、前からある alt「作った物の写真」だけ（感想の字は出さない）。"""
    from omochae import hypotheses

    cards = ""
    for sid in sids:
        fs = files(sid)
        if not fs:
            continue
        imgs = "".join(f'<img src="/workshop/{esc(f)}/small" alt="作った物の写真" loading="lazy" decoding="async">' for f in fs)
        cards += f'<figure class="workshop">{imgs}<figcaption><a href="/toy/{esc(sid)}">{esc(hypotheses.load(sid)["toy"])}</a></figcaption></figure>'
    return f'<div class="workshop-row">{cards}</div>' if cards else ""


# ── もちよるの頁（/gallery）の 2 つの節（本人の言葉 11-08「もちよる、ワークショップの様子、として作っている様子をあげるのと、
# できたおもちゃはギャラリーの形で並べる。感想も見れるように」）。写真 → 玩具は上の表（data/workshop_photos.json）のまま使い、
# 作っている途中とできた物の分けは data/workshop_photo_kinds.json（各日の review.md の「写っている物」の字から分けた表・統括の決め 11-08）。
# 感想 → 玩具は声の担当の表（demo_samples.VOICE_TOYS）と札（demo_samples.workshop_for）をそのまま呼ぶ（同じ表を 2 つ作らない）。
# 置き場と名は本人の言葉（11-08）「冒頭におもちゃが並べてある写真一枚。みんながつくったおもちゃに、おもちゃの単体の写真。つくっている様子に、
# ワークショップの様子。日付毎にしなくていい。」による（前の案の名「ワークショップでできたおもちゃ」「作っている様子の写真」は本人の字に替えた）。
# 差し替えられるようにここの定数に置く。TOP は頭に出す 1 枚の案（並べた写真 5 枚のうち、いちばん多くの種のおもちゃが机に広く並ぶ 1 枚）
SCENE_HEAD = "つくっている様子"
MADE_HEAD = "みんながつくったおもちゃ"
SCENE_ALT = "つくっている様子"
TOP_ALT = "おもちゃが並べてある写真"
MADE_ALT = "作った物の写真"  # 前からある字（玩具の頁の写真と同じ）
OPEN_VOICES = "感想を見る"  # 案（本人の確かめ待ち）
TOP = "20261106/p33.jpg"
SHOWN = ("lineup", "single", "making")  # none（どれにも入らない写真）は出さない
KINDS = ROOT / "data/workshop_photo_kinds.json"


@functools.lru_cache(maxsize=1)
def _kinds(mtime=None):
    return {r["file"]: r["kind"] for r in json.loads(KINDS.read_text(encoding="utf-8")).get("photos", [])}


def kind_of(file):
    """並べた（lineup）か、単体（single）か、作っている様子（making）か、どれにも入らない（none）か。表に無い写真（p28）は None。"""
    return (_kinds(KINDS.stat().st_mtime) if KINDS.exists() else {}).get(file)


def _ok(file):
    return FILE.fullmatch(file) is not None and (PHOTOS / file).exists()


def _img(file, alt):
    return f'<img src="/workshop/{esc(file)}/small" alt="{esc(alt)}" loading="lazy" decoding="async">'


def top():
    """頭の 1 枚（おもちゃが並べてある写真）。TOP が並べた写真の分け（lineup）で、置き場に在る時だけ出す。玩具を言わない（何人分もの作品が写るので）。"""
    if kind_of(TOP) != "lineup" or not _ok(TOP):
        return ""
    return f'<figure class="workshop-top" id="narabe">{_img(TOP, TOP_ALT)}</figure>'


def scene():
    """「つくっている様子」の節（ワークショップの様子）。作っている途中の写真を、撮った順に敷き詰める（日付ごとに分けない・上下は付けない）。写真が無い時は節ごと出さない。
    写真の道は、作っている途中の写真の分け（kind_of）だけで決める（どの玩具かの表は使わない。様子の写真は玩具を言わないので）。"""
    files = [f for f in sorted(_kinds(KINDS.stat().st_mtime) if KINDS.exists() else {}) if kind_of(f) == "making" and _ok(f)]
    if not files:
        return ""
    return (f'<section class="panel" id="yousu"><h2 class="mark">{esc(SCENE_HEAD)}</h2>'
            f'<div class="workshop-row tiles">{"".join(f"<figure>{_img(f, SCENE_ALT)}</figure>" for f in files)}</div></section>')


def made(sids):
    """「みんながつくったおもちゃ」の節（おもちゃの単体の写真）。玩具ごとに 1 枚の札（その玩具の単体の写真の全部・玩具の名・押すと開く感想）を、頁の玩具の並びの順に敷き詰める。
    - できた物の写真は札に全部入れる（本人の決め 11-07「ワークショップの写真は 復元・記録・ギャラリーの全部の置き場に置く」。1 枚目だけにすると残りがどこにも出ない）
    - 札に出す玩具は、できた物の写真が表で結ばれた玩具と、感想か話された言葉が結ばれた玩具（demo_samples.workshop_for が空でない玩具）
    - 感想は workshop_for の札のまま（回答のまま・名前や番号なし・動かなかった声と注文も並べる。本人の決め 11-07「寄せられた声…置き方は案のとおり」）
    - どの玩具とも結ばれていない単体の写真は、玩具の名を付けない札で頭に置く（玩具を勝手に決めない）。並べた写真はこの節に出さない（頭の 1 枚・top）
    - 写真の無い玩具の札は、名と感想だけ（絵を作らない）。どれも無い時は節ごと出さない"""
    from omochae import hypotheses

    from .demo_samples import workshop_for

    by_toy = {r["file"]: r["toy"] for r in rows()}
    loose = [f for f in sorted(_kinds(KINDS.stat().st_mtime) if KINDS.exists() else {}) if kind_of(f) == "single" and _ok(f) and f not in by_toy]
    cards = "".join(f'<figure class="workshop">{_img(f, MADE_ALT)}</figure>' for f in loose)
    for sid in sids:
        name = hypotheses.load(sid)["toy"]
        photos = [f for f in files(sid) if kind_of(f) == "single"]
        voices = workshop_for(sid, name)
        if not (photos or voices):
            continue
        pic = "".join(_img(f, MADE_ALT) for f in photos)
        fold = f'<details class="voices-fold"><summary>{esc(OPEN_VOICES)}</summary>{voices}</details>' if voices else ""
        cards += f'<figure class="workshop">{pic}<figcaption><a href="/toy/{esc(sid)}">{esc(name)}</a></figcaption>{fold}</figure>'
    if not cards:
        return ""
    return f'<section class="panel" id="dekita"><h2 class="mark">{esc(MADE_HEAD)}</h2><div class="workshop-row tiles">{cards}</div></section>'
