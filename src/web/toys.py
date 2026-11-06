"""おもちゃの一覧の頁（/toys。本人の指示 2026-11-05、要件 docs/process/site-requirements.md の L-02・2「選ぶ」）。

判断の芯:
- 全部の玩具（仮説の記録がある物）を 1 頁で選べる。必須の 2 種を大きく、試作を小さな札で。並びは記録の印（コマ）の順で、順位ではない。
- 一覧には仮説の名前と動き方を出さない（選ぶ頁を軽くするため）。出すのは玩具の名前・コマ・図だけ。
- 試作の写し（out/sources）は棚卸しの箱で切り出した物なので、そのまま敷く。必須の 2 種は頁の半分の写しなので、綴じの影の反対側へ寄せる（looks.framed_pos と同じ）。
  写しが無い玩具は名前だけにし、国立国会図書館への道を添える（入口と同じ線。写しの有無で玩具が消えると選べなくなるため）。
- 見た目は骨と皮（skin.shell）に任せ、この頁は皮を知らない。play_server と looks は読み込まない（道の登録で循環しないため）。
"""
import json

from omochae import hypotheses, ways
from omochae.hypotheses import ROOT

from . import skin as skinmod
from .skin import esc

LEAD = "どれも図と歌だけが残った玩具です。選ぶと、すぐ型紙を刷って作れます。型紙は正解ではなく、AI が考えた仮説です。"
NOTE = "先頭の {n} つのほかは、全部を型紙にする途中の試作です。名前は作る側の見立てで、まだ確かめていません。"


def sources():
    return sorted(p.stem for p in (ROOT / "data/hypotheses").glob("NDL-*.json"))


def _source(sid):
    return json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))


def _pic(sid, main):
    if not (ROOT / "out/sources" / f"{sid}.jpg").exists():
        return '<div class="pic nopic" role="img" aria-label="図は手元に無い"></div>'
    # 必須の 2 種は半頁の写しなので額の敷き方（112%・綴じの反対側）。試作は箱の切り出しで、札と縦横が違うので contain（cover だと切れて、何の玩具か分からない札が出る）。皮の .toys .pic の 300% を上書きする
    pos = ("15% 50%" if _source(sid).get("side") == "R" else "85% 50%") if main else "50% 50%"
    size = "112% 112%" if main else "contain"
    return f'<div class="pic" style="background-image:url(/picture/{esc(sid)});background-position:{pos};background-size:{size}" role="img" aria-label="図"></div>'


def way_tags(names):
    """作り方の印の札。並べ替えや点数にしない（J-025）。"""
    tags = "".join(f'<span class="lb">{esc(n)}</span>' for n in names)
    return f'<p class="ways">{tags}</p>' if names else ""


def card(sid):
    data, src = hypotheses.load(sid), _source(sid)
    main = hypotheses.stage(sid) == "必須"
    has = (ROOT / "out/sources" / f"{sid}.jpg").exists()
    more = "" if has else f'<p class="meta"><a href="{esc(src.get("image_url", ""))}">図を見る（国立国会図書館）</a></p>'
    big = ' class="big"' if main else ""
    return f'<li{big}><a href="/toy/{esc(sid)}">{_pic(sid, main)}<span class="nm">{esc(data["toy"])}</span></a>{way_tags(ways.toy_labels(sid))}{more}</li>'


def paper_only_sids(sids):
    """たたき台が紙 1 枚で作れる玩具（J-032。紙一枚は必須の条件でなく、必須の 2 種は入らない）。札の印と同じ ways の「紙一枚」で絞る（#255 の頃は別の判定を持っていたが、
    main の ways（#261、エンジンとそろえた物）と二重になり、札と絞り込みが食い違いうるので ways に寄せた）。"""
    return [s for s in sids if "紙一枚" in ways.toy_labels(s)]


def page(skin, path="/toys", paper=False):
    """全部の玩具を選ぶ頁。skin は皮の名前（skin.SKINS の鍵）。paper は紙 1 枚で作れる玩具だけに絞る（本人の言葉 11-05「一枚の紙から作る選択肢もある」）。"""
    sids = sources()
    if paper:
        sids = paper_only_sids(sids)
    main = [s for s in sids if hypotheses.stage(s) == "必須"]
    rest = [s for s in sids if hypotheses.stage(s) != "必須"]
    body = (f'<section class="sec"><h1>おもちゃ</h1><p class="lead">{esc(LEAD)}</p>'
            f'<p class="meta">{len(sids)} のおもちゃです。{esc(NOTE.format(n=len(main)) if main else NOTE.split("ほかは、", 1)[1])}</p><p class="meta">{esc(ways.NOTE)}</p>'
            + ('<p class="links"><a href="/toys">全部の玩具を見る</a></p>' if paper else '<p class="links"><a href="/toys?paper=1">紙 1 枚で作れるおもちゃだけを見る</a></p>') +
            f'<ul class="toys" style="list-style:none;padding:0;margin:4vh 0 0">{"".join(card(s) for s in main + rest)}</ul></section>')
    return skinmod.shell("うつし · おもちゃ", body, skin, current="/toys", path=path)
