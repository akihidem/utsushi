"""作った実物の立体（ガウシアンスプラッティング）と、エンジンの 3D 組み立てを並べて、同じ向きで一緒に回す部品（本人の決定 11-07）。

本人の言葉: 「splat 御来迎は「3D と組み合わせる」方向で。実物の立体（splat）と、エンジンの 3D 組み立てを組み合わせて見せる形にしてください。置く向きは前からを主にしてよい」
窓口の決め（11-07 125156）: ① 並べて同じ向きで回す形（案 A）を先に ② 置き場は玩具の頁の頭 ④ 描いた絵は repo に入れず公開のサーバに ⑤ 札の字は案のまま。
設計は grove の state/splat-3d-20261107.md。

判断の芯:
- 頁で splat を描く道具（WebGL の表示部品）は入れない。組み立ての 3D の線（kumitate の頭「外の部品を読まない。CSS の立体だけで動かす（学校の網で止まらない）」）を守る。
  実物の立体は、前の向きのまわりを先に GPU で絵にしておき（−20°〜+45° の 14 枚。撮れていない側はにじむので回さない）、頁は角に近い絵に替えるだけ。
- エンジンの側は kumitate.still（できあがりの止まった形・CSS の立体）を使い、見る向きの rotateY に、実物と同じ回す角を足す。形は組み立ての頁と同じ物（絵を別に描かない）。
  向きの 0 はどちらも「前」（実物は札の面、エンジンは組み立ての頁の見る向き）。2 つの前は同じ面とは限らないので、合わせるのは回した量（同じ角だけ回る）。
- 絵の置き場はサーバの記録の置き場（OMOCHAE_DATA/splat/<玩具の印>/。frames.json と t00.jpg〜）。repo には入れない。
  frames.json の checked_by が入った物（人が物だけと確かめた物）だけを出す（公開の場へ出す物は人が確かめた物・統括の知らせ 11-07）。無い間は部品を出さない。
- 絵の道は /toy/<印>/splat/<番号>.jpg の 1 本。一覧の数の外・確かめていない物・置き場の外はどれも 404。
- 新しい字は札の 2 つ（窓口の決め ⑤ で案のまま採られた）と、回す口の名（窓口へ）。
- 札に、それぞれの型紙の版を「型紙の版 N」で書く（2 つは同じ版の物ではない。v を付けない形は本人の言葉 11-07）。写した実物は型紙の版 13 で作った物（本人の言葉 11-07「最終版の一個前」
  「札はその事実に合わせてください」。前の答え「札に版 14 とは書かない事」）。実物の版は絵の一覧（frames.json の sheet_set）から読み、無ければ書かない（推さない）。
  エンジンの側は今の組（雛形の SHEET_SET）の形なので、その版を書く。
"""
import json
import os
import pathlib
import re

from omochae.hypotheses import ROOT

from . import kumitate
from .skin import esc

AI = "AI が組み立てた 3D"
MADE = "作った実物（3D で写した）"
TURN = "向きを変える"   # 回す口の名（新しい字・窓口へ）
W, H = 150, 270   # 1 つの窓の大きさ（縦長の 5:9。幅 390 で 2 つ並ぶ。絵は 300×540 なので 2 倍の画面でも粗くならない）
# 前は 240×270 で、エンジンの側の止まった形の幅が列を押し広げ、実物の側が約 100px に縮んだ（11-07 の画面で見た）

STYLE = """
.sp-pair{display:grid;grid-template-columns:repeat(2,minmax(0,150px));gap:24px;margin:16px 0 0;justify-content:start}
.sp-pair figure{margin:0}.sp-pair figcaption{font-size:13px;margin:6px 0 0}
.sp-pair .sp-made img{width:150px;height:270px;object-fit:contain;display:block;background:#fff}
.sp-pair .rt-still{max-width:100%}
.sp-turn{display:block;width:100%;max-width:324px;margin:12px 0 0;min-height:44px}
"""


def _base(sid):
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "splat" / sid


def _ver(set_name):
    m = re.fullmatch(r"[a-z]+-v(\d+)", str(set_name or ""))
    return f"型紙の版 {int(m.group(1))}" if m else ""  # 「型紙の版 14」の形（本人の言葉 11-07「札の版は「型紙の版 14」「型紙の版 13」の形に」。v を付けない）


def engine_version(sid):
    """エンジンの側（今の組）の版の言い方。"""
    from omochae import hypotheses
    from omochae.compose import TEMPLATES
    tpl = TEMPLATES.get(hypotheses.load(sid).get("template", "slider_fan"))  # 型の名が無い玩具は slider_fan（手帖の data と同じ既定）
    return _ver(getattr(tpl, "SHEET_SET", ""))


def frames(sid):
    """確かめた絵の一覧（{"angles": [...], "files": [...], "version": 実物の版の言い方}）。無い・確かめていない・数が合わない時は None。"""
    base = _base(sid)
    try:
        meta = json.loads((base / "frames.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    angles = meta.get("angles")
    if not meta.get("checked_by") or not isinstance(angles, list) or not angles:
        return None
    # 角は数で、小さい順に並んでいる物だけ受ける（別の目の気づき 11-07: 数でない値で頁ごと 500 になり、順が逆だと回す口の向きが逆になった）
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in angles) or any(b <= a for a, b in zip(angles, angles[1:])):
        return None
    files = [f"t{i:02d}.jpg" for i in range(len(angles))]
    box = base.resolve()
    for f in files:
        try:
            real = (base / f).resolve(strict=True)
        except OSError:
            return None
        if real.parent != box or not real.is_file():
            return None
    return {"angles": [float(a) for a in angles], "files": files, "version": _ver(meta.get("sheet_set"))}


def frame_bytes(sid, i):
    """/toy/<印>/splat/<番号>.jpg の中身。出さない物は None（呼ぶ側が 404）。"""
    fr = frames(sid)
    if not fr or not (0 <= i < len(fr["files"])):
        return None
    try:
        return (_base(sid) / fr["files"][i]).read_bytes()
    except OSError:
        return None


def _turnable_still(sid):
    """kumitate.still の見る向きの rotateY に、回す角（CSS の変数 --sp-turn）を足した片。形が見つからなければ空（部品を出さない）。"""
    h = kumitate.still(sid, W, H)
    new, n = re.subn(r'(class="rt-scene" style="transform:[^"]*?)rotateY\((-?[\d.]+)deg\)',
                     lambda m: f'{m.group(1)}rotateY(calc({m.group(2)}deg + var(--sp-turn,0deg)))', h, count=1)
    return new if n == 1 else ""


def _ver_line(v):
    return f'<br><span class="sp-ver">{esc(v)}</span>' if v else ""


def section(sid):
    """並べて一緒に回す部品の HTML。確かめた絵と組み立ての形の両方がある玩具だけ。無ければ空。"""
    fr = frames(sid)
    still = _turnable_still(sid) if fr else ""
    if not (fr and still):
        return ""
    a = fr["angles"]
    zero = min(range(len(a)), key=lambda i: abs(a[i]))
    data = json.dumps({"a": a, "src": [f"/toy/{sid}/splat/{i}.jpg" for i in range(len(a))]})
    return (f'<style>{STYLE}</style><div class="sp" data-sp=\'{esc(data)}\'>'
            f'<div class="sp-pair"><figure class="sp-ai">{still}<figcaption>{esc(AI)}{_ver_line(engine_version(sid))}</figcaption></figure>'
            f'<figure class="sp-made"><img src="/toy/{esc(sid)}/splat/{zero}.jpg" alt="{esc(MADE)}" width="{W}" height="{H}">'
            f'<figcaption>{esc(MADE)}{_ver_line(fr["version"])}</figcaption></figure></div>'
            f'<input class="sp-turn" type="range" min="{a[0]:g}" max="{a[-1]:g}" step="1" value="0" aria-label="{esc(TURN)}">'
            "<script>(()=>{const s=document.currentScript.parentElement,d=JSON.parse(s.dataset.sp),r=s.querySelector('.sp-turn'),"
            "img=s.querySelector('.sp-made img'),sc=s.querySelector('.sp-ai .rt-scene');"
            "const go=v=>{v=+v;let k=0;d.a.forEach((x,i)=>{if(Math.abs(x-v)<Math.abs(d.a[k]-v))k=i});img.src=d.src[k];"
            # 実物の絵は、カメラを +v 回した所から見た形（物は −v 回って見える）。エンジンの形も同じ向きに見えるよう、物を −v 回す
            "if(sc)sc.style.setProperty('--sp-turn',(-v)+'deg')};"
            "r.addEventListener('input',()=>go(r.value));"
            "d.src.forEach(u=>{const i=new Image();i.src=u})})()</script></div>")


def page(sid, look=None, path=None):
    """並べて一緒に回す頁（玩具の頁の頭の「作ってみた実物」から開く口。置き場の決め ② の、玩具の頁が落ち着くまでの単独の頁）。部品が無い玩具は空。"""
    from omochae import hypotheses

    from . import skin
    sec = section(sid)
    if not sec:
        return ""
    toy = hypotheses.load(sid).get("toy", "")
    body = (f'<section class="sec"><h1>{esc(toy)}</h1>{sec}</section>'
            f'<section class="sec"><p class="links"><a href="/toy/{esc(sid)}">{esc(toy)}の頁へもどる</a></p></section>')
    return skin.shell(f"{toy}: {MADE}", body, look or skin.DEFAULT, path=path or f"/toy/{sid}/splat")
