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
SCENE_ALT = "ワークショップの様子"  # 本人の言葉「つくっている様子に、ワークショップの様子」の写真の言い方（本人の答え 11-08「後の言葉にそろえる。」）
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


# 玩具の札に寄せる事例の写真の種類（改善ループの例・型紙で改善したおもちゃ 3 バージョン）。前は玩具の頁の「これまでの復元」にだけ出た
# （本人の言葉 11-07 午後 193「改善ループの例として使って欲しい」の写真もその 1 つ）。玩具の頁から外すので、ここへ寄せる（本人の言葉 11-08 477）。
# 参加者の工夫（kufu）は作例の節の工夫の段に残す（本人の言葉の引用と組で出しているため・同じ写真を 2 度出さない）
CARD_CASES = ("loop", "versions")


def _cases(sid, photos=True):
    """その玩具の事例の写真の小さい写しの道（人が「物だけ」と確かめた物）。photos=False（写真を出さない前の開いた場の形）は出さない
    （作例の節 sakurei_section と同じ線。ワークショップの試行の写真と違い、人が上げた写真なので）。"""
    if not photos:
        return []
    from . import sakurei

    return [c["url"] for kind in CARD_CASES for c in sakurei.cases(kind) if c["sid"] == sid]


def has_card(sid, photos=True):
    """もちよるの「みんながつくったおもちゃ」に、その玩具の札（錨 toy-<印>）が出るか。made と同じ線で見る。"""
    from omochae import hypotheses

    from . import sakurei
    from .demo_samples import workshop_for

    return bool((photos and any(e["sid"] == sid for e in sakurei.examples())) or _cases(sid, photos) or workshop_for(sid, hypotheses.load(sid)["toy"]))


def made(sids, photos=True):
    """「みんながつくったおもちゃ」の節。作例の記録の札（本人が上げた、玩具の名と写真が結ばれた写真・作例の節にあった札）を、そのままの組み合わせと形で並べる。
    本人の言葉 11-08「みんなが作ったおもちゃの方は、おもちゃの名前と写真が合っていない。ワークショップで作られたものの方は写真と名前が一致しているので、
    こちらの組み合わせと表示を採用して、みんなが作ったおもちゃの方に置く。」:
    - 前の札（試行の写真の表の単体の写真を玩具に結んだ物）は使わない（名と写真が合っていなかった）。作例の節（techo_site.sakurei_section）の
      玩具ごとの札はこの節へ移した（同じ物を 2 度出さない）。作例の節には顔の写真・報告の段・参加者の工夫が残る
    - 札は 1 つの記録に 1 枚（作例の節と同じ形: 写真の小さい写し・玩具の名（玩具の頁へ）・刷った組が分かる時だけ型紙の版）。玩具の並びは sids の順、同じ玩具の中は記録の順
    - 玩具の頁にだけあった事例の写真（CARD_CASES・改善ループの例と 3 バージョン）も、同じ形の札で、その玩具の作例の札の後ろに置く
    - 感想と言葉（workshop_for）は、その玩具の最初の札の「感想を見る」の畳み。作例も事例も無い玩具は、名と感想だけの札
    - その玩具の最初の札が錨 id="toy-<印>" を持つ（玩具の頁の「この玩具の作った物を もちよる で見る」の道の行き先・#646）
    - 83 の外の玩具（猫と鼠の箱など）の作例の札は後ろに、棚卸しの名で、道と錨を付けずに置く（玩具の頁が無い。前の作例の節と同じ）
    - 出すのは人が「物だけ」と確かめた写真だけ（examples・cases が確かめた物だけを返す）。photos=False（写真を出さない前の開いた場の形）は写真を出さない
    - どれも無い時は節ごと出さない"""
    from omochae import hypotheses, records

    from . import sakurei
    from .demo_samples import workshop_for
    from .techo_site import _ban

    order = {sid: i for i, sid in enumerate(sids)}
    examples = sorted(sakurei.examples() if photos else [], key=lambda e: (order.get(e["sid"], len(order)), e["sid"], e["rid"]))
    img = lambda url: f'<img src="{esc(url)}" alt="{esc(MADE_ALT)}" loading="lazy" decoding="async">'  # noqa: E731
    cards = ""
    for sid in sids:
        name = hypotheses.load(sid)["toy"]
        voices = workshop_for(sid, name)
        shots = [("".join(img(f"/record/{e['rid']}/media/{f}/small") for f in e["photos"]), _ban(e["set"])) for e in examples if e["sid"] == sid]
        shots += [(img(u), "") for u in _cases(sid, photos)]
        if not (shots or voices):
            continue
        fold = f'<details class="voices-fold"><summary>{esc(OPEN_VOICES)}</summary>{voices}</details>' if voices else ""
        anchor = f' id="toy-{esc(sid)}"'
        for n, (pic, ban) in enumerate(shots or [("", "")]):
            cards += (f'<figure class="workshop"{anchor if n == 0 else ""}>{pic}'
                      f'<figcaption><a href="/toy/{esc(sid)}">{esc(name)}</a>{ban}</figcaption>{fold if n == 0 else ""}</figure>')
    for e in examples:
        if e["sid"] not in order and records.outside_toy(e["sid"]):
            pic = "".join(img(f"/record/{e['rid']}/media/{f}/small") for f in e["photos"])
            cards += f'<figure class="workshop">{pic}<figcaption>{esc(sakurei.toy_name(e["sid"]))}{_ban(e["set"])}</figcaption></figure>'
    if not cards:
        return ""
    return f'<section class="panel" id="dekita"><h2 class="mark">{esc(MADE_HEAD)}</h2><div class="workshop-row tiles">{cards}</div></section>'
