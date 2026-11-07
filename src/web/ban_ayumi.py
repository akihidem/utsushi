"""玩具の頁の 2 画面目「型紙の版の歩み」の額の並び（本人の指示 11-07「過去の型紙が改善していって、提出の時の今の型紙になっている所が
分かるようにしたい。御来迎と虎のそれぞれで、版の歩みが今の版に行き着くまで見える形にしてください。」）。

設計 0.7 節（UX の担当）の置き場 ①。字の元は改善の歴史の表だけ（omochae.kaizen_history）。頁で版ごとの字を書き足さない。

判断の芯:
- 額は古い版が左、今の版が右（読む順）。並びはサイトが今刷っている組まで（kaizen_history.versions）で、最後の額が今の版。
  今の版の額だけを大きくし、赤い枠と、輪の図と同じ字「いまの型紙」（wa.NOW）の印で示す。印を字でも出すのは、色だけに頼らないため。
- 開いた時は並びの右の端（今の版）が見える所から始め、左へ送ると過去へさかのぼる（設計の担当 11-07）。御来迎のように版が多くても、
  行き着いた今が最初に見える。HTML の並びは古い順のままにし（読み上げも古い順に聞こえる）、始めの位置だけを小さな script で右へ送る。
  script が動かない時は左の端（いちばん古い版）から見える。どちらでも全部の額に届く。
- 額と額の間は「→」の印（SVG。字ではない。読み上げには出さない）。
- 額の中は、その版の刷った紙の 1 枚目を縮めた絵（エンジンが組ごとに出した物。out/history/sheets をサーバが /history/sheets/ から出す）。
  絵を置いていない版は、空の額にする（壊れた絵の印を出さない）。字は絵に焼かず、頁の字で出す。
- 額の下は「型紙の版 N」・エンジンの版の字（表の engine_version_text）・表の line・日付の 4 つだけ。きっかけ（why）と PR は出さない
  （玩具の頁はシンプルに。序の頁の表に出す）。
- 表の最初の版が版 1 でない時は、その前にも版がある事を書く（表の前の版の行がエンジンから届くまでのつなぎ。届けば消える）。
- 節は <section id="ban-ayumi"> の 1 つにまとめる。外からの合格の線が、節ごと外して見られるように（id は変えない）。
- 新しい字（見出し・数の 1 行・日付の形・つなぎの 1 行）は定数にまとめた。5 つとも窓口が推しの字で決めた（11-07。印は輪の図の字を使う）。
"""
import re

from omochae import kaizen_history
from omochae.hypotheses import load

from .skin import esc
from .wa import NOW

# 新しい字（窓口の決め 11-07。直す時はここだけ）
HEAD = "型紙の版の歩み"
COUNT = "版 {first} から版 {last} まで、{n} の版を重ねて今の型紙になった"
SHEET = "型紙の版 {n}"
BEFORE = "この前にも版があります"
DATE = "{m} 月 {d} 日"

SET_NAME = re.compile(r"[a-z]+-v\d{1,3}")
# 今の版の枠と印の朱。デモの絵が枠と数字にだけ使う朱（demo.flip の SHU）と同じにし、動画と頁で今の版の枠をそろえる。
# 皮の --accent は白の展示で茶なので、設計の「赤い枠」にならない。白と黒の両方の皮の上で読める濃さ
SHU = "#be3c28"

STYLE = (".ban-ayumi .ban-count{font-size:14px;letter-spacing:.06em;margin:4px 0 10px}"
         ".ban-ayumi .ban-before{font-size:12px;color:var(--mute);margin:0 0 6px}"
         ".ban{list-style:none;margin:0;padding:6px 2px 12px;display:flex;align-items:flex-start;gap:0;overflow-x:auto;scroll-snap-type:x proximity}"
         ".ban>li{display:flex;align-items:flex-start;flex:0 0 auto;scroll-snap-align:end}"
         ".ban .ban-to{width:24px;height:12px;margin:73px 4px 0;flex:0 0 auto}"
         ".ban .ban-to path{fill:none;stroke:var(--mute);stroke-width:1.6}"
         ".ban figure{margin:0;width:112px}.ban .now figure{width:168px}"
         ".ban .ban-pic{display:block;width:100%;height:auto;aspect-ratio:596/842;object-fit:contain;background:var(--paper);border:1px solid var(--frame)}"
         f".ban .now .ban-pic{{border:3px solid {SHU}}}"
         ".ban figcaption{font-size:12px;line-height:1.6;margin-top:6px;display:flex;flex-direction:column;gap:1px}"
         f".ban figcaption b{{font-weight:600;font-size:13px}}.ban .ban-now{{color:{SHU};font-weight:600;letter-spacing:.08em}}"
         ".ban .ban-eng,.ban time{color:var(--mute)}")
# 矢印（.ban-to）は絵の高さの真ん中あたり（幅 112px の絵の高さ約 158px の半分）に置く。字の行の数が版ごとに違うので、額の真ん中にしない。
# 始めの位置を右の端（今の版）へ送る。並びが幅に収まる時は何も起きない。画面の幅が替わった時（電話の向きを替えた時など）も、
# 人がまだ並びを送っていなければ右の端へ送り直す（前は始めの 1 回だけで、幅が広い時に送った位置のまま狭くなると、今の版が右の外に出た）
SCRIPT = ("<script>(function(){var l=document.querySelectorAll('.ban');function end(){l.forEach(function(e){if(!e.dataset.moved)e.scrollLeft=e.scrollWidth})}"
          "l.forEach(function(e){['pointerdown','wheel','keydown'].forEach(function(k){e.addEventListener(k,function(){e.dataset.moved=1})})});"
          "end();addEventListener('load',end);addEventListener('resize',end)})()</script>")
ARROW = '<svg class="ban-to" viewBox="0 0 24 12" aria-hidden="true" focusable="false"><path d="M1 6H21M15 1l6 5-6 5"/></svg>'


def _date(text):
    m = re.fullmatch(r"\d{4}-(\d{2})-(\d{2})", text or "")
    return DATE.format(m=int(m.group(1)), d=int(m.group(2))) if m else ""


def picture_url(row):
    """額の中の絵の URL。絵を置いていない版は None。"""
    return f"/history/sheets/{row['set']}.png" if kaizen_history.picture(row) else None


def picture_file(name):
    """/history/sheets/<組の名>.png の中身のパス。組の名の形の外・置いていない時は None（サーバは 404 にする）。"""
    if not SET_NAME.fullmatch(name or ""):
        return None
    return kaizen_history.picture({"sheet_image": f"sheets/{name}.png"})


def _frame(row, first):
    n = row["sheet_version"]
    url = picture_url(row)
    pic = (f'<img class="ban-pic" src="{esc(url)}" alt="{esc(SHEET.format(n=n))}" loading="lazy" width="596" height="842">'
           if url else '<span class="ban-pic" aria-hidden="true"></span>')
    now = f'<span class="ban-now">{esc(NOW)}</span>' if row["now"] else ""
    cap = (f"<b>{esc(SHEET.format(n=n))}</b>{now}<span class=\"ban-eng\">{esc(row.get('engine_version_text', ''))}</span>"
           f"<span>{esc(row.get('line', ''))}</span>")
    day = _date(row.get("date"))
    if day:
        cap += f'<time datetime="{esc(row["date"])}">{esc(day)}</time>'
    cls = ' class="now" aria-current="true"' if row["now"] else ""
    return f"<li{cls}>{'' if first else ARROW}<figure>{pic}<figcaption>{cap}</figcaption></figure></li>"


def section(sid):
    """玩具の頁の版の歩みの節。表に無い玩具・今の組の行が表に無い玩具は空（今の版と言えない並びを出さない）。"""
    # 雛形の名の欄が無い記録は御来迎の雛形（記録の古い形。omochae.loop と同じ読み方）。表は玩具ごとの行なので、
    # 同じ雛形の別の玩具が増えても、その頁に必須の玩具の歩みを出さないよう、表の玩具の名と記録の玩具の名が同じ時だけ並べる
    data = load(sid)
    template = data.get("template", "slider_fan")
    if not any(name == data.get("toy") and tpl == template for name, tpl, _ in kaizen_history.toys()):
        return ""
    rows = kaizen_history.versions(template)
    if not rows or not rows[-1]["now"]:
        return ""
    first, last = rows[0]["sheet_version"], rows[-1]["sheet_version"]
    before = f'<p class="ban-before">{esc(BEFORE)}</p>' if first > 1 else ""
    items = "".join(_frame(r, i == 0) for i, r in enumerate(rows))
    return (f'<style>{STYLE}</style><section class="sec ban-ayumi" id="ban-ayumi"><h2>{esc(HEAD)}</h2>'
            f'<p class="ban-count">{esc(COUNT.format(first=first, last=last, n=len(rows)))}</p>{before}'
            f'<ol class="ban">{items}</ol></section>{SCRIPT}')
