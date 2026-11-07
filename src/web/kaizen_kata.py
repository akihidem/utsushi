"""審査用の頁（/kaizen）の「型紙で改善したおもちゃ」の段（本人の言葉 11-07・窓口の決め 152530）。

本人の言葉: 写真 goraigo-3versions.jpg と tora-3versions.jpg は「型紙で改善したおもちゃ 3 バージョン」— 改善の例として使う。
御来迎が開く動画は「御来迎が開く動画として使う。デモとサイト」。窓口の決め: 置き場は審査用の頁が中心（題の下・ワークショップの節の前）。

判断の芯:
- 写真は作例の部品（web.sakurei.versions() → {玩具の印: 小さい写しの道}・人が確かめた物だけ）から引く。記録の番号で引かない（置き場ごとに番号が変わるため）。
  作例の部品が無い・壊れた時は段を出さない（審査用の頁ごと止めない）。
- 動画は公開の場のデータの置き場（OMOCHAE_DATA/kaizen_video/<名>.mp4）の、横の checked.json に人が確かめた印（checked_by）がある物だけ。
  repo に入れない。音と撮影の情報は、置く担当（作例の担当）が外した写し。/kaizen/video/<名>.mp4 で返す（iPhone の Safari が要る Range も受ける）。
- 動画は動き方そのものを見せる物なので、学ぶ人の道（玩具の頁の頭・手帖の作る手・作例の節）には出さない（J-013・統括の決め 11-07）。
  審査用の頁は学ぶ人の道の外なので、ここに置く。開いただけでは動かさない（押すと動く・音なし）。
- 動画の撮り方を表す字は、頁のどこにも書かない（本人の訂正 11-07）。札は「御来迎が開く所」だけ。
- 写真の版の番号（何の版で作った物か）は本人の確かめ待ちなので、まだ書かない。玩具の名とその玩具の頁への道だけ。
"""
import json
import os
import pathlib
import re

from omochae import hypotheses
from omochae.hypotheses import ROOT

from .skin import esc

HEAD = "型紙で改善したおもちゃ"
OPENS = "御来迎が開く所"
GORAIGO = "NDL-1187053-R0000005-L"
VIDEO = "goraigo-hiraku.mp4"
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}\.mp4")

STYLE = """
.kv-row{display:grid;grid-template-columns:1fr;gap:16px;margin:16px 0 0}
@media (min-width:768px){.kv-row{grid-template-columns:1fr 1fr}}
.kv-row figure{margin:0}.kv-row img,.kv-row video{width:100%;height:auto;display:block}
.kv-row figcaption{font-size:14px;margin:6px 0 0}
"""


def _video_dir():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "kaizen_video"


def video_ok(name):
    """出してよい動画か: 名の形・確かめた印（checked.json の checked_by）・置き場の中のふつうのファイル。"""
    if not NAME.fullmatch(str(name)):
        return False
    box = _video_dir()
    try:
        checked = json.loads((box / "checked.json").read_text(encoding="utf-8"))
        real = (box / name).resolve(strict=True)
    except (OSError, ValueError):
        return False
    row = checked.get(name) if isinstance(checked, dict) else None
    return bool(isinstance(row, dict) and row.get("checked_by")) and real.parent == box.resolve() and real.is_file()


def video_bytes(name):
    """/kaizen/video/<名>.mp4 の中身。出さない物は None（呼ぶ側が 404）。"""
    if not video_ok(name):
        return None
    try:
        return (_video_dir() / name).read_bytes()
    except OSError:
        return None


def _versions():
    try:
        from . import sakurei
        got = sakurei.versions()
        return {k: v for k, v in got.items() if isinstance(v, str) and v.startswith("/record/")} if isinstance(got, dict) else {}
    except Exception:  # 作例の部品は別の PR。無い間・壊れた時に頁を止めない
        return {}


def _toy(sid):
    try:
        return hypotheses.load(sid).get("toy", "")
    except Exception:
        return ""


def section():
    """段の HTML。写真が 1 枚も無ければ空（動画だけでは段を出さない: 改善の例は写真が芯のため）。"""
    photos = _versions()
    if not photos:
        return ""
    figs = ""
    for sid, url in photos.items():
        toy = _toy(sid)
        figs += (f'<figure><img src="{esc(url)}" alt="{esc(toy)}" loading="lazy">'
                 f'<figcaption><a href="/toy/{esc(sid)}">{esc(toy)}</a></figcaption></figure>')
        if sid == GORAIGO and video_ok(VIDEO):
            figs += (f'<figure><video src="/kaizen/video/{esc(VIDEO)}" controls muted playsinline preload="none"></video>'
                     f'<figcaption>{esc(OPENS)}</figcaption></figure>')
    return f'<section class="sec kv" id="versions"><h2>{esc(HEAD)}</h2><div class="kv-row">{figs}</div></section>'
