"""おもちゃの一覧の頁（/toys。本人の指示 2026-11-05、要件 docs/process/site-requirements.md の L-02・2「選ぶ」）。

判断の芯:
- 全部の玩具（仮説の記録がある物）を 1 頁で選べる。必須の 2 種を大きく、試作を小さな札で。並びは記録の印（コマ）の順で、順位ではない。
  試作はジャンルの棚（genre.py の大きい側の 3 つ）の見出しで分け、棚の中は同じ中の玩具を隣り合わせて記録の印の順（本人の依頼 11-06）。
- 一覧には仮説の名前と動き方を出さない（選ぶ頁を軽くするため）。出すのは玩具の名前・コマ・図だけ。
- 試作の写し（out/sources）は棚卸しの箱で切り出した物なので、そのまま敷く。必須の 2 種は頁の半分の写しなので、綴じの影の反対側へ寄せる（looks.framed_pos と同じ）。
  写しが無い玩具は名前だけにし、国立国会図書館への道を添える（入口と同じ線。写しの有無で玩具が消えると選べなくなるため）。
- 見た目は骨と皮（skin.shell）に任せ、この頁は皮を知らない。play_server と looks は読み込まない（道の登録で循環しないため）。
- 並び（作り直し 11-07。本人の言葉「サイト、絵が並び、タップすると絵から3Dイメージが立ち上がる。…基本構造はシンプルがいい。」、
  UX の設計 state の rebuild-design の 0.1 の「並ぶ」と 6 の 2「えらぶ の札を絵と名前だけにする」）:
  - 棚の中は原画の敷き詰め（高さの揃わない列）。CSS の列（columns）だけで作り、JS も外の部品も使わない。絵は切り抜きの縦横のまま
    （前は 3:4 の箱に contain で入れ、縦長・横長の絵のまわりに空きが出ていた）。縦横は img の width・height に書き、読み込みで並びが跳ねないようにする。
  - 札は絵と名前だけ。作り方の印（ways）は玩具の頁に在るので、札の下からは外した（窓口の決定 11-07「札の下の作り方の印は外したまま」。
    地図の工程 2「要る物が先に分かる」とは食い違い、要る物は玩具の頁に入ってから分かる）。
  - 頭は「{n} のおもちゃから、1 つ選ぶ」の 1 行だけ（窓口の決定 11-07 の ②）。前の頭の断りの段（LEAD・NOTE・ways.NOTE）は、字を変えずに
    序の頁（よむ）へ移した（yomu_section）。型紙が仮説である事は、玩具の頁の頭の前提の段（toy.PREMISE_PAGE）が作る所で言う。
  - 絵と絵の間（--ma）は案 A の 16px（設計の推し「間を残した敷き詰め」。窓口の決定 11-07「絵の間は 16px のまま」）。替える時は skin.BASE の 1 か所。
  - 列の数は幅で決まる（skin.BASE の .narabi。1 列 96px 以上で 7 列まで。参考の頁の幅 1280 の 7 列に合わせた）。幅 390 は 3 列
    （2 列だと 81 枚で 10 画面を超える）。設計の目当て「えらぶ 5 画面以下」には届かない（3 列・名前 1 行で 7.2 画面。名前 2 行は 7.6、
    4 列は 5.3 画面だが絵が幅 70px ほどになり、絵を見て選べない。11-07 に Chromium で測った）。窓口の決定 11-07「幅 390 で 3 列のまま」。
  - 頭の 1 行は題の大きさにしない（題の大きさだと幅 390 で「1 つ選ぶ」の間で折れた）。
  - skin.BASE の CSS の注は全部の頁の HTML に入るので、判断の理由はここに書き、CSS の注は短くする（序の頁の試験が頁に「本人」の字が無い事を見る）。
"""
import functools
import json

from omochae import hypotheses, ways
from omochae.hypotheses import ROOT

from . import genre
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


@functools.lru_cache(maxsize=None)
def _size(path, mtime):
    """切り抜きの縦横（px）。img に書いて、絵が読み込まれる前から列の高さを決める。mtime は写しを替えた時に読み直すための鍵。"""
    from PIL import Image
    with Image.open(path) as im:
        return im.size


SMALL_W = 400  # 敷き詰めの絵の幅（px）。幅 390 の 3 列（1 枚 103px）を 3 倍の画面で見ても粗くならない幅


@functools.lru_cache(maxsize=None)
def _small(path, mtime):
    from PIL import Image
    import io
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((SMALL_W, SMALL_W * 8))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=82, optimize=True)
    return buf.getvalue()


def small_picture(sid):
    """敷き詰めの 1 枚の小さい写し（/picture/<印>/small）。切り抜きは幅 1600px で 83 枚 35MB あり、iPhone で えらぶ を開くたびに全部を読むと重い。
    小さくした写しは一度作ったら覚えておく（写しを替えた時は mtime で作り直す）。写しが無ければ None。"""
    path = ROOT / "out/sources" / f"{sid}.jpg"
    return _small(str(path), path.stat().st_mtime) if path.exists() else None


def _tile(sid):
    """敷き詰めの 1 枚: 切り抜きの縦横のままの絵。写しが無ければ前と同じ空の箱（_pic）。"""
    path = ROOT / "out/sources" / f"{sid}.jpg"
    if not path.exists():
        return _pic(sid, False)
    w, h = _size(str(path), path.stat().st_mtime)
    # 縦横の比は style にも書く。皮の .toys .pic の aspect-ratio:3/4 が width・height からの比を上書きし、読み込む前の高さが 0 になって
    # 並びが跳ねた（11-07 に幅 390 で測った: 読み込む前 4428px・後 6441px）
    return (f'<img class="pic" src="/picture/{esc(sid)}/small" width="{w}" height="{h}" style="aspect-ratio:{w}/{h}" '
            'loading="lazy" decoding="async" alt="図">')


def card(sid):
    """札は絵と名前だけ（作り直し 11-07）。必須の 2 種は前と同じ額の敷き方の大きい札、ほかは敷き詰めの 1 枚。
    写しの無い玩具は名前と国立国会図書館への道（写しの有無で玩具が消えると選べなくなるため。前のまま）。"""
    data, src = hypotheses.load(sid), _source(sid)
    main = hypotheses.stage(sid) == "必須"
    has = (ROOT / "out/sources" / f"{sid}.jpg").exists()
    more = "" if has else f'<p class="meta"><a href="{esc(src.get("image_url", ""))}">図を見る（国立国会図書館）</a></p>'
    big = ' class="big"' if main else ""
    pic = _pic(sid, True) if main else _tile(sid)
    return f'<li{big}><a href="/toy/{esc(sid)}">{pic}<span class="nm">{esc(data["toy"])}</span></a>{more}</li>'


def paper_only_sids(sids):
    """たたき台が紙 1 枚で作れる玩具（J-032。紙一枚は必須の条件でなく、必須の 2 種は入らない）。札の印と同じ ways の「紙一枚」で絞る（#255 の頃は別の判定を持っていたが、
    main の ways（#261、エンジンとそろえた物）と二重になり、札と絞り込みが食い違いうるので ways に寄せた）。"""
    return [s for s in sids if "紙一枚" in ways.toy_labels(s)]


def _list(sids, margin, narabi=False):
    cls = "toys narabi" if narabi else "toys"
    return f'<ul class="{cls}" style="list-style:none;padding:0;margin:{margin}">{"".join(card(s) for s in sids)}</ul>'


def by_genre(sids):
    """試作の玩具を、ジャンルの棚（大きい側の 3 つ）の見出しで分けて並べる（本人の依頼 11-06「ジャンル分けしたい」、research/36 の決まった事）。
    見出しは大きい側だけ（11-06 の決定、案 a「棚の見出しは大きい3つだけ」。本人の決め直し「棚は かざる・あそぶ・うごく の3つです。」の読み）。
    中（もって あそぶ・ひく おす など）は頁に出さず、棚の中の並びにだけ使う: 同じ中の玩具を隣り合わせ、中の中は記録の印の順のまま。
    中の順は genre.BIG の並びで、順位ではない（J-025）。字は棚の字だけで、説明の 1 行は添えない（決まった事「頁に断りの 1 行は添えない」）。
    見出しの間合いは字の大きさ（em）と px で決める。vh だと窓の高さで間が変わり、縦に長い窓で見出しと札が離れすぎた（11-06 に縦 9000 で撮って見た）。"""
    out = []
    for big, mids in genre.groups(sids):
        out.append(f'<h2 style="margin:2.4em 0 0">{esc(big)}</h2>')
        out.append(_list([s for _, ss in mids for s in ss], "14px 0 0", narabi=True))
    return "".join(out)


def counts():
    """玩具の数と、必須の数（頭の 1 行と、よむ へ移した断りの段の数）。"""
    sids = sources()
    return sids, [s for s in sids if hypotheses.stage(s) == "必須"]


def yomu_section():
    """前は えらぶ の頭にあった断りの段（LEAD・数・NOTE・ways.NOTE）。窓口の決定 11-07 の ② で、字を変えずに序の頁（よむ）へ移した。"""
    sids, main = counts()
    return (f'<section class="sec"><p class="lead">{esc(LEAD)}</p>'
            f'<p class="meta">{len(sids)} のおもちゃです。{esc(NOTE.format(n=len(main)) if main else NOTE.split("ほかは、", 1)[1])}</p>'
            f'<p class="meta">{esc(ways.NOTE)}</p></section>')


def page(skin, path="/toys", paper=False):
    """全部の玩具を選ぶ頁。skin は皮の名前（skin.SKINS の鍵）。paper は紙 1 枚で作れる玩具だけに絞る（本人の言葉 11-05「一枚の紙から作る選択肢もある」）。
    必須の 2 種は今までどおり先頭に大きく置き、ジャンルの見出しには入れない（玩具は 1 度だけ出す）。棚の中は原画の敷き詰め。
    頭は 1 行だけ（窓口の決定 11-07 の ②）なので、紙 1 枚の絞り込みの道は並びの後ろに置く（本人の言葉の口なので外さない）。
    頭の 1 行の字は入口の全部の玩具の節の見出しと同じ（looks.all_toys。採られた字）。数は絞った後の数。"""
    sids = sources()
    if paper:
        sids = paper_only_sids(sids)
    main = [s for s in sids if hypotheses.stage(s) == "必須"]
    rest = [s for s in sids if hypotheses.stage(s) != "必須"]
    link = '<p class="links"><a href="/toys">全部の玩具を見る</a></p>' if paper else '<p class="links"><a href="/toys?paper=1">紙 1 枚で作れるおもちゃだけを見る</a></p>'
    body = (f'<section class="sec erabu"><h1>{len(sids)} のおもちゃから、1 つ選ぶ</h1>'
            + (_list(main, "4vh 0 0") if main else "") + by_genre(rest) + link + '</section>')
    return skinmod.shell("うつし · おもちゃ", body, skin, current="/toys", path=path)
