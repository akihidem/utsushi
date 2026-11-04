"""デモ用の見本（本人の指示、11-04「デモ用の作り物と分かる形で」サイトに出す）。上げた物と、フォームに寄せられた情報提供の見本。

判断の芯:
- 本物の記録と混ぜない。見本は記録の置き場（OMOCHAE_DATA）に書かず、このファイルの定数だけから描く。台帳にも数えない。
- 作り物だと一目で分かる。どの見本にも「見本」の札と、架空である事の一文を付ける。実在の人の名前・言葉・写真は使わない（絵は線画）。
- 本番では消せる。OMOCHAE_SAMPLES=0 で出さない。既定で出すのは、11-07 の撮影と見学者の一周で空の頁を見せないため。
"""
import html
import os

NOTE = "デモ用の作り物です。実在の人の投稿・言葉・写真ではありません。"


def enabled():
    return os.environ.get("OMOCHAE_SAMPLES", "1") != "0"


def esc(s):
    return html.escape(str(s))


# 上げた物の見本の絵。写真に見えない線画にして、本物の上げた物と取り違えないようにする。
FAN = ('<svg viewBox="0 0 160 110" role="img" aria-label="見本の線画（扇）"><rect width="160" height="110" fill="#f4efe3"/>'
       '<path d="M80 92 L28 40 A74 74 0 0 1 132 40 Z" fill="none" stroke="#7a3b1d" stroke-width="2"/>'
       '<path d="M80 92 L54 30 M80 92 L80 20 M80 92 L106 30" stroke="#7a3b1d" stroke-width="1.5"/>'
       '<rect x="66" y="92" width="28" height="12" fill="none" stroke="#7a3b1d" stroke-width="2"/></svg>')
TORA = ('<svg viewBox="0 0 160 110" role="img" aria-label="見本の線画（首振り）"><rect width="160" height="110" fill="#f4efe3"/>'
        '<rect x="40" y="52" width="80" height="34" rx="10" fill="none" stroke="#7a3b1d" stroke-width="2"/>'
        '<circle cx="42" cy="44" r="18" fill="none" stroke="#7a3b1d" stroke-width="2"/>'
        '<path d="M50 86v14M110 86v14M120 60q18 -6 22 -22" fill="none" stroke="#7a3b1d" stroke-width="2"/></svg>')

# 結果の言葉は各雛形の RESULTS の中から選ぶ（本物の記録と同じ言葉で並ぶ形を見せるため）。
UPLOADS = [
    {"toy": "御来迎", "sheet": "A", "result": "動いた", "note": "筒を先に丸めたら、すっと立った", "pic": FAN},
    {"toy": "御来迎", "sheet": "C", "result": "動かない", "note": "蛇腹が開いたまま戻らない", "pic": FAN},
    {"toy": "張子の首振り虎", "sheet": "A", "result": "揺れた", "note": "首の重りを一枚足したら長く揺れた", "pic": TORA},
]

# フォーム（持ち寄りの入口、J-021）に寄せられる情報提供の見本。項目は form_import が受ける形（種類・題・本文・権利）に合わせる。
CONTRIBUTIONS = [
    {"who": "見本の職人 甲（架空）", "slot": "紙と折りの職人", "kind": "作り方の知恵",
     "title": "筒の糊しろは内側へ", "text": "糊しろを内に折り込むと、外から継ぎ目が見えず、丸めた時の段差も出にくい。",
     "rights": "自分の言葉（公開してよい）"},
    {"who": "見本の職人 乙（架空）", "slot": "からくりの職人", "kind": "仕掛けの見方",
     "title": "首振りは重さの釣り合い", "text": "首の付け根を少し後ろにずらすと、揺れが長く続く。重りより支点の位置が先。",
     "rights": "自分の言葉（公開してよい）"},
    {"who": "見本の作り手 丙（架空）", "slot": "郷土玩具の作り手", "kind": "写真の添付",
     "title": "手元の古い扇の玩具", "text": "家にある古い玩具の写真を添えます（見本なので写真はありません）。",
     "rights": "権利の確かめ待ち（確かめるまで載せない）"},
]


def badge():
    return '<span class="sample">見本</span>'


def uploads_html():
    if not enabled():
        return ""
    items = "".join(f'<div class="item is-sample"><p class="meta">{badge()} {esc(u["toy"])}　{esc(u["sheet"])} の紙　{esc(u["result"])}</p>'
                    f'<div class="row">{u["pic"]}</div><p>{esc(u["note"])}</p></div>' for u in UPLOADS)
    return f'<div class="samples"><p class="meta">{badge()} {esc(NOTE)}</p>{items}</div>'


def voice_html(slot):
    """職人の言葉の 1 枠。見本が無い枠や見本を切った時は、今までどおり（準備中）。"""
    c = next((c for c in CONTRIBUTIONS if c["slot"] == slot), None) if enabled() else None
    if c is None:
        return f'<div class="item"><p class="meta">{esc(slot)}</p><p>（準備中）</p></div>'
    return (f'<div class="item is-sample"><p class="meta">{badge()} {esc(slot)}　{esc(c["who"])}　{esc(c["kind"])}</p>'
            f'<p><b>{esc(c["title"])}</b></p><p>{esc(c["text"])}</p><p class="meta">権利: {esc(c["rights"])}</p></div>')


STYLE = """
.techo .sample{display:inline-block;background:#7a3b1d;color:#fff;font-size:11px;letter-spacing:.2em;padding:1px 8px;border-radius:9px;margin-right:4px}
.techo .is-sample{border-top:1px dashed #b8a27c;background:repeating-linear-gradient(135deg,#fff 0 10px,#fbf6ea 10px 20px);padding:10px;border-radius:10px}
.techo .is-sample svg{height:110px;width:auto;border:1px dashed #b8a27c;border-radius:8px}
.techo .samples{display:grid;gap:10px}
"""
