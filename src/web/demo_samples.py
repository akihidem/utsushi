"""デモ用の見本（本人の指示、11-04「デモ用の作り物と分かる形で」サイトに出す。11-05「過去の人のギャラリーや職人の声なども、デモなので想定の内容で作っておく」）。
上げた物・寄せられた声・職人の言葉の見本。

判断の芯:
- 本物の記録と混ぜない。見本は記録の置き場（OMOCHAE_DATA）に書かず、このファイルの定数だけから描く。台帳にも数えない。
- 作り物だと一目で分かる。どの見本にも「見本」の札と、架空である事の一文を付ける。実在の人の名前・言葉・写真は使わない（絵は線画）。
- 並びは記録の順の見本（番号の順）で、上下・点・順位を付けない（J-025）。見た事の言葉は雛形の RESULTS の中の物だけ（成功・失敗・正解を使わない）。
- 本番では消せる。OMOCHAE_SAMPLES=0 で出さない。既定で出すのは、11-07 の撮影と見学者の一周で空の頁を見せないため。
"""
import html
import os

NOTE = "デモ用の作り物です。実在の人の投稿・言葉・写真ではありません。"


def enabled():
    return os.environ.get("OMOCHAE_SAMPLES", "1") != "0"


def esc(s):
    return html.escape(str(s))


# 上げた物の見本の絵。写真に見えない線画にして、本物の上げた物と取り違えないようにする。地と線は皮の色で描く。固定の色だと、黒のジンで白い箱が頁から浮いた（#139）。
def _svg(label, inner):
    return f'<svg viewBox="0 0 160 110" role="img" aria-label="見本の線画（{label}）"><rect width="160" height="110" fill="var(--soft)"/>{inner}</svg>'


FAN = _svg("扇", '<path d="M80 92 L28 40 A74 74 0 0 1 132 40 Z" fill="none" stroke="var(--accent)" stroke-width="2"/>'
                 '<path d="M80 92 L54 30 M80 92 L80 20 M80 92 L106 30" stroke="var(--accent)" stroke-width="1.5"/>'
                 '<rect x="66" y="92" width="28" height="12" fill="none" stroke="var(--accent)" stroke-width="2"/>')
TORA = _svg("首振り", '<rect x="40" y="52" width="80" height="34" rx="10" fill="none" stroke="var(--accent)" stroke-width="2"/>'
                     '<circle cx="42" cy="44" r="18" fill="none" stroke="var(--accent)" stroke-width="2"/>'
                     '<path d="M50 86v14M110 86v14M120 60q18 -6 22 -22" fill="none" stroke="var(--accent)" stroke-width="2"/>')
KAZAGURUMA = _svg("風車", '<path d="M80 50 L80 18 L100 34 Z M80 50 L112 50 L96 70 Z M80 50 L80 82 L60 66 Z M80 50 L48 50 L64 30 Z" fill="none" stroke="var(--accent)" stroke-width="2"/>'
                          '<circle cx="80" cy="50" r="3" fill="var(--accent)"/><path d="M80 53v47" stroke="var(--accent)" stroke-width="2"/>')
DENDEN = _svg("でんでん太鼓", '<circle cx="80" cy="44" r="24" fill="none" stroke="var(--accent)" stroke-width="2"/><path d="M80 68v36" stroke="var(--accent)" stroke-width="2"/>'
                             '<path d="M56 44 Q42 54 38 70 M104 44 Q118 54 122 70" fill="none" stroke="var(--accent)" stroke-width="1.5"/>'
                             '<circle cx="38" cy="70" r="4" fill="none" stroke="var(--accent)" stroke-width="2"/><circle cx="122" cy="70" r="4" fill="none" stroke="var(--accent)" stroke-width="2"/>')
OKIAGARI = _svg("起き上がり", '<path d="M80 20 a30 30 0 0 1 0 60 a30 30 0 0 1 0 -60" fill="none" stroke="var(--accent)" stroke-width="2"/>'
                              '<path d="M52 72 a28 14 0 0 0 56 0" fill="none" stroke="var(--accent)" stroke-width="2"/><circle cx="80" cy="36" r="10" fill="none" stroke="var(--accent)" stroke-width="1.5"/>'
                              '<path d="M30 92 h100" stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="3 3"/>')

# 上げた物の見本。見た事の言葉は各雛形の RESULTS の中から選ぶ（本物の記録と同じ言葉で並ぶ形を見せるため）:
# 御来迎 slider_fan（動いた・動かない・わからない）、虎 pivot_counterweight（揺れた・揺れない）、風車 spin_toy（回った・回らない・わからない）、
# でんでん太鼓 den_den（鳴った・鳴らない・わからない）、起き上がり小法師 balance_toy（戻った・戻らない）。並びは番号の順（記録の順の見本）。
UPLOADS = [
    {"no": 1, "toy": "御来迎", "sheet": "A", "result": "動いた", "note": "筒を先に丸めたら、すっと立った", "pic": FAN},
    {"no": 2, "toy": "御来迎", "sheet": "C", "result": "動かない", "note": "蛇腹が開いたまま戻らない。糸を短くしてみたい", "pic": FAN},
    {"no": 3, "toy": "張子の首振り虎", "sheet": "A", "result": "揺れた", "note": "首の重りを一枚足したら長く揺れた", "pic": TORA},
    {"no": 4, "toy": "風車", "sheet": "A", "result": "回った", "note": "息で回った。羽を少し反らせたら止まりにくい", "pic": KAZAGURUMA},
    {"no": 5, "toy": "でんでん太鼓", "sheet": "B", "result": "鳴らない", "note": "玉が皮に届かない。糸をあと 1cm 長くする", "pic": DENDEN},
    {"no": 6, "toy": "起き上がり小法師（頭巾姿）", "sheet": "A", "result": "戻った", "note": "底の重りを真ん中に置くと、ゆっくり戻る", "pic": OKIAGARI},
    {"no": 7, "toy": "御来迎", "sheet": "A", "result": "わからない", "note": "開いたけれど、押した手の力か紙の力か分からない", "pic": FAN},
    {"no": 8, "toy": "張子の首振り虎", "sheet": "B", "result": "揺れない", "note": "首が胴に当たる。口を 2mm 広げて次の版にする", "pic": TORA},
]

# フォーム（持ち寄りの入口、J-021）に寄せられる情報提供の見本。項目は form_import が受ける形（種類・題・本文・権利）に合わせる。
# slot のある物は「職人の言葉」の枠に入る（枠は 3 つ、本人の設計 11-04）。slot の無い物は「寄せられた声」に並ぶ。
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
VOICES = [
    {"who": "見本の紙の問屋の人（架空）", "kind": "材料の知恵",
     "title": "蛇腹には薄くて腰のある紙", "text": "コピー用紙より少し薄く、折り目が戻りにくい紙だと、扇が畳んだまま筒に入る。和紙なら楮の薄い物。",
     "rights": "自分の言葉（公開してよい）"},
    {"who": "見本の郷土玩具の資料館の人（架空）", "kind": "文献の手がかり",
     "title": "似た玩具の図が別の本にもある", "text": "御来迎に似た「せり上がる扇」の図を、別の絵本でも見た覚えがあります。書名を確かめてから改めて送ります。",
     "rights": "確かめ待ち（書名が分かるまで載せない）"},
    {"who": "見本の保護者（架空）", "kind": "家で試した事",
     "title": "子どもと虎を作った", "text": "首が揺れるまでに 2 回作り直した。2 回目は耳を短くした。どこを変えたかを書く欄があって助かった。",
     "rights": "自分の言葉（公開してよい）。写真は送らない"},
    {"who": "見本の理科の先生（架空）", "kind": "授業で使った事",
     "title": "1 コマで作るから記録まで", "text": "5 人の班で、作る 30 分・記録 15 分で回った。谷折りと山折りの絵があると最初の一歩が早い。",
     "rights": "自分の言葉（公開してよい）。生徒の名前は書かない"},
]


def badge():
    return '<span class="sample">見本</span>'


def uploads_html():
    if not enabled():
        return ""
    items = "".join(f'<div class="item is-sample"><p class="meta">{badge()} 見本 {u["no"]:02d}　{esc(u["toy"])}　{esc(u["sheet"])} の紙　{esc(u["result"])}</p>'
                    f'<div class="row">{u["pic"]}</div><p>{esc(u["note"])}</p></div>' for u in UPLOADS)
    return f'<div class="samples"><p class="meta">{badge()} {esc(NOTE)}</p>{items}</div>'


def uploads_for(toy):
    """玩具の頁に出す、その玩具の見本の記録（本人の指摘 11-05「制作した記録とおもちゃのページが関連してない。同じページで見れると良い」）。
    見本の無い玩具と、見本を切った時は空。札と架空である事の一文は、ギャラリーと同じに付ける。"""
    mine = [u for u in UPLOADS if u["toy"] == toy] if enabled() else []
    if not mine:
        return ""
    items = "".join(f'<div class="item is-sample"><p class="meta">{badge()} 見本 {u["no"]:02d}　{esc(u["sheet"])} の紙　{esc(u["result"])}</p>'
                    f'<div class="row">{u["pic"]}</div><p>{esc(u["note"])}</p></div>' for u in mine)
    return f'<div class="samples"><h3>見本の記録</h3><p class="meta">{badge()} {esc(NOTE)}</p>{items}</div>'


def voice_html(slot):
    """職人の言葉の 1 枠。見本が無い枠や見本を切った時は、今までどおり（準備中）。"""
    c = next((c for c in CONTRIBUTIONS if c["slot"] == slot), None) if enabled() else None
    if c is None:
        return f'<div class="item"><p class="meta">{esc(slot)}</p><p>（準備中）</p></div>'
    return (f'<div class="item is-sample"><p class="meta">{badge()} {esc(slot)}　{esc(c["who"])}　{esc(c["kind"])}</p>'
            f'<p><b>{esc(c["title"])}</b></p><p>{esc(c["text"])}</p><p class="meta">権利: {esc(c["rights"])}</p></div>')


def voices_html():
    """寄せられた声（持ち寄りの入口から来た物の見本）。見本を切った時は空の文だけ。架空である事の一文を先頭に置く。"""
    if not enabled():
        return '<p class="meta">まだ寄せられた声はありません。</p>'
    items = "".join(f'<div class="item is-sample"><p class="meta">{badge()} {esc(v["who"])}　{esc(v["kind"])}</p>'
                    f'<p><b>{esc(v["title"])}</b></p><p>{esc(v["text"])}</p><p class="meta">権利: {esc(v["rights"])}</p></div>' for v in VOICES)
    return f'<div class="samples"><p class="meta">{badge()} {esc(NOTE)}</p>{items}</div>'
