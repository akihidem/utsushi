"""おもちゃのジャンル（作った後の楽しみ方の 2 段。本人の決定 11-06、docs/process/research/36-road-and-audience.md の「決まった事」）。

判断の芯:
- 83 の玩具に手でジャンルを付けない。玩具の雛形（動き方の族。data/hypotheses の template）から MIDDLE の表で引く。
  雛形を足した時に表を足し忘れると、tests/test_toys_genre.py が落ちる。
- 雛形の表で合わない玩具だけを TOY に置く。置くのは、台帳（data/inventory/edo-nishiki.json）の動きの言葉が 1 つに決まっている物だけ。
  今は凧の 3 本（雛形は糸を引く string_pull だが、台帳は「糸を引いて風で揚げる」）。
  台帳の言葉が「か」で分かれる 7 本（浮き物の 5 本・起き上がりの座り人形・鳥笛の棒）は、決まるまで雛形の表のまま（作る側の見立てで決めない）。
- 大きい側の字と、中の 9 つをどの大きい側に入れるかは BIG の 1 か所だけに置く。字は本人の決定（11-06「ジャンル分けの字は「かざる・あそぶ・うごく」の3つに決めました。」）。
  中の入れ先は research/36 に書いていないので、決まった事の並びの順からの読みで置いた。本人の答えが来たら BIG だけを差し替える。
- 並びは呼ぶ側の並び（記録の印の順）のまま、ジャンルで分けるだけ。順位にしない（J-025）。玩具が 0 の中と大きい側は返さない（頁に見出しを出さない）。
"""
from omochae import hypotheses

# 雛形 → 中。必須の 2 種も同じ表で引く（御来迎は筒を押し引きして扇を開く slider_fan、虎は首が揺れる pivot_counterweight）
MIDDLE = {
    "stand_figure": "かざる",
    "stick_prop": "もって あそぶ",
    "string_pull": "ひく おす",
    "slider_fan": "ひく おす",
    "spin_toy": "まわす",
    "den_den": "ならす",
    "balance_toy": "ゆれる",
    "pivot_counterweight": "ゆれる",
    "wheel_cart": "ころがす",
}

# 雛形の表で合わない玩具だけ（台帳の moves_guess が「糸を引いて風で揚げる」の 3 本）
TOY = {
    "NDL-1187053-R0000024-L": "あげる",  # 雷神の凧
    "NDL-1187053-R0000024-L-2": "あげる",  # 袖凧（丸に十字紋）
    "NDL-1187053-R0000024-L-3": "あげる",  # 木菟の凧
}

# 大きい側 → 中。字は本人の決定（11-06）、中の入れ先は並びの順からの読み（本人の答え待ち）。差し替える時はここだけ
BIG = (
    ("かざる", ("かざる",)),
    ("あそぶ", ("もって あそぶ", "うかべる", "あげる")),
    ("うごく", ("ひく おす", "まわす", "ならす", "ゆれる", "ころがす")),
)


def middle(sid):
    """玩具の中のジャンル。"""
    return TOY.get(sid) or MIDDLE[hypotheses.load(sid).get("template", "slider_fan")]


def groups(sids):
    """[(大きい側の字, [(中の字, [玩具…]), …]), …]。sids の並びを保ち、0 の中と大きい側は入れない。
    BIG のどこにも入らない中がある時は、玩具を黙って一覧から落とさずに ValueError で止める。"""
    by = {}
    for s in sids:
        by.setdefault(middle(s), []).append(s)
    placed = {m for _, mids in BIG for m in mids}
    lost = sorted(set(by) - placed)
    if lost:
        raise ValueError(f"大きい側に入れ先の無いジャンル: {'、'.join(lost)}")
    out = []
    for big, mids in BIG:
        g = [(m, by[m]) for m in mids if by.get(m)]
        if g:
            out.append((big, g))
    return out
