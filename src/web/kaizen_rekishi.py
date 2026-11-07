"""序の頁（よむ）の「型紙とエンジンの改善の歴史」（設計 0.7 節の置き場 ③。本人の言葉 11-07「どう改善が進むかは山場なのでデモにも載せたいところ。
サイトにも記載したい」）。

判断の芯:
- 字の元は改善の歴史の表だけ（omochae.kaizen_history）。題・見出し（「エンジンの版」「エンジンそのものの直し」）・「刷った型紙の組」も、
  表の作り手が表の .md で使った字を使い、頁で新しく作らない。版ごとの字も書き足さない。
- 表の作り手の言い方「制作者」「本人」は、序の頁では wording.MAKER の字に替える（窓口の決め 11-07。審査用の頁と同じ替え方）。
- 出すのは、全部の玩具に効く物だけ: 山場の流れ・エンジンの版（刷った型紙の組つき）・エンジンそのものの直し（PR つき）。
  玩具ごとの型紙の版の歩みは、玩具の頁の版の歩み（ban_ayumi）が持つ。序の頁には「仕組みの答えと仮説の名前を書かない」決まりがあり
  （紙で確かめる前に答えを見せない。tests/test_about.py）、型紙の版の行には御来迎の内筒・つまみ・仮説の名が入るため（窓口へ確かめ中の推し A 11-07）。
- 頭に表の山場の流れ（story）の 1 段。表の「言葉」の欄（terms）は作る側の言葉（台帳のパス・撮影の事情）なので出さない。
- 版の数が多い（エンジン 7・直し 9）ので、まとまりごとに畳む（details）。開くと版ごとの小さな段で、
  幅の狭い画面でも読めるよう、表の形（table）にしない。
- PR は型紙エンジン（paper-to-toy）の PR で、番号から GitHub へ飛ぶ（審査用の頁と同じ道）。エンジンの版に付く採った案の番号の並び（proposals）は
  作る側の番号なので並べない（きっかけの字の中に案の番号が入っている所は、表の字のまま）。
- 節は <section class="sec" id="kaizen-rekishi"> の 1 つ。序の頁の「なぜ」とエンジンの仕組みの節の後に、部品を呼ぶ 1 行で置く。
"""
from omochae import kaizen_history

from .ban_ayumi import SHEET, _date
from .skin import esc
from .wording import MAKER

REPO = "https://github.com/akihidem/paper-to-toy/pull/{n}"
# 表の .md の見出しの字（表の作り手の字。頁で作らない）
ENGINE_HEAD = "エンジンの版"
CHANGES_HEAD = "エンジンそのものの直し"
SETS = "刷った型紙の組: {sets}"
ENGINE = "エンジンの版 {n}"

STYLE = (".kaizen-rekishi details{margin:10px 0;border-top:1px solid var(--rule)}.kaizen-rekishi summary{cursor:pointer;padding:8px 0}"
         ".kaizen-rekishi summary h3{display:inline;font-size:16px;margin:0}"
         ".kr-list{list-style:none;margin:0;padding:0}.kr-list>li{padding:8px 0 10px;border-bottom:1px dashed var(--rule)}"
         ".kr-list p,.kr-list ul{margin:4px 0}.kr-list ul{padding-left:1.2em}.kr-h b{font-weight:600}"
         ".kr-h time,.kr-eng{color:var(--mute);font-size:13px;margin-left:.6em}.kr-why,.kr-pr{font-size:13px;color:var(--mute)}")


def _maker(text):
    return str(text).replace("制作者", MAKER).replace("本人", MAKER)


def _prs(prs):
    links = "・".join(f'<a href="{REPO.format(n=int(n))}">#{int(n)}</a>' for n in prs or [])
    return f'<p class="kr-pr">PR {links}</p>' if links else ""


def _engine(data):
    items = ""
    for e in data.get("engine_versions", []):
        sets = "・".join(f"{toy} {SHEET.format(n=kaizen_history.set_no(s))}" for toy, s in (e.get("sets") or {}).items())
        day = _date(e.get("date"))
        items += (f'<li><p class="kr-h"><b>{esc(ENGINE.format(n=e["engine_version"]))}</b>'
                  + (f'<time datetime="{esc(e["date"])}">{esc(day)}</time>' if day else "")
                  + (f'<span class="kr-eng">{esc(SETS.format(sets=sets))}</span>' if sets else "")
                  + f'</p><p>{esc(_maker(e.get("line", "")))}</p>{_prs([e["pr"]] if e.get("pr") else [])}</li>')
    return f'<details><summary><h3>{esc(ENGINE_HEAD)}</h3></summary><ol class="kr-list">{items}</ol></details>' if items else ""


def _changes(data):
    items = ""
    for c in data.get("engine_changes", []):
        day = _date(c.get("date"))
        why = f'<p class="kr-why">{esc(_maker(c["why"]))}</p>' if c.get("why") else ""
        items += (f'<li><p class="kr-h">' + (f'<time datetime="{esc(c["date"])}">{esc(day)}</time>' if day else "")
                  + f'</p><p>{esc(_maker(c.get("line", "")))}</p>{why}{_prs([c["pr"]] if c.get("pr") else [])}</li>')
    return f'<details><summary><h3>{esc(CHANGES_HEAD)}</h3></summary><ol class="kr-list">{items}</ol></details>' if items else ""


def section():
    """序の頁の改善の歴史の節。表が読めない時は空（序の頁はほかの節だけで開く）。"""
    try:
        data = kaizen_history.load()
    except (OSError, ValueError):
        return ""
    story = f'<p class="lead">{esc(_maker(data["story"]))}</p>' if data.get("story") else ""
    return (f'<style>{STYLE}</style><section class="sec kaizen-rekishi" id="kaizen-rekishi"><h2>{esc(data.get("title", ""))}</h2>'
            f"{story}{_engine(data)}{_changes(data)}</section>")
