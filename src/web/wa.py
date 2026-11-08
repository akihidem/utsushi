"""型紙がよくなっていく輪を、一目で分かる図にする部品（本人の言葉 11-06「サイトにその仕組みがわかりやすくあるといいよね」）。

その仕組み: 作る人の工夫が戻って、型紙がどんどん良くなっていく輪（統括が本人の言葉を言い直した物）。

判断の芯:
- 置き場は玩具の頁の「すぐ作る」の札（PREMISE_PAGE）のすぐ後。札は輪を字で言っている（ためしの案 → 工夫を記録に書く → 次の型紙をよくする）ので、
  同じ所で図にすると、字と図が並んで一目で分かる。輪の詳しい所（版ごとに変えた寸法と根拠の記録）は頁の下の「型紙の改善の輪」（kaizen.section）に残し、
  図の真ん中からそこへ飛ぶ。頁を増やさない（凍結 11-06: 新しい頁・口・欄は作らない。図は本人の言葉による置き物）。
- 輪の 4 つの字は、頁に既にある字から取る（新しい言い方を増やさない）。PREMISE_PAGE の「ためしの案（仮説）」「どう工夫したかを記録に書いて」
  「次の型紙をよくする」と、「すぐ作る」の頭の文の「切って、折って、組みます」。並べ方と切り方は案なので、本人の確認に回す（PR は確認まで合体しない）。
- 真ん中に出す数は、その玩具の今の型紙の版だけ。報告の数や動いた数は出さない（成績に見える数を出さない。J-025）。
  版は組の番号（goraigo-v14 の 14。set_version）。前は寸法を 1 つ直した刻み（current_version、ループ 2 の版）を出していたが、本人の言葉（11-07）
  「バージョンをサイトで明示したい」と窓口の決定（カード 084426）で、紙の題に刷る数と同じ「型紙の版」を出す。寸法の刻みは版の中の小さな直しとして、
  作る側の版の歩みの頁（/loop/ayumi）に残す（学ぶ人の頁には出さない）。「エンジンの版」は別の数で、ここには出さない（言い分ける。同じ決定）。
- 今動いていない所を、動いているように描かない。輪は人の手で回る所（作る人が工夫を記録し、作る側が寸法を 1 つ変えて次の版にする）だけを描く。
  AI が次の案を出す所は、本物の API がまだ動いていないので描かない（足すなら点線と「いま作っているところです」。本人の決定 11-05 の線）。
- 図は字を持つ SVG（読み上げられるよう、title に輪の順を 1 文で入れる）。色は皮の色（--accent・--frame・--fg）を読むので、白の展示と黒のジンの両方で同じ作り。
"""
from . import en_fig
from .skin import esc

# 輪の字（並びの順）。どれも頁に既にある字から取った（上の判断の芯）。字を直す時はここ 1 か所だけ。
STEPS = ("ためしの案（仮説）", "切って、折って、組む", "どう工夫したかを記録に書く", "次の型紙をよくする")
# 図の中で 2 行に分ける所（字は変えない。置き方だけ）。
LINES = {"どう工夫したかを記録に書く": ("どう工夫したかを", "記録に書く"), "次の型紙をよくする": ("次の型紙を", "よくする"),
         "切って、折って、組む": ("切って、折って、", "組む")}
NOW = "いまの型紙"
VERSION = "版 {n}"

# 図の大きさ。左右の札（幅 BOX_W）が図の中に収まる幅にする（前は 400 で、幅 390 の画面で左右の札の端が切れた。11-06 に実物で見た）。
W, H = 440, 330
CX, CY, R = 220, 165, 110
# 4 つの札の真ん中（上・右・下・左）。時計回りに回る。
SPOTS = ((CX, CY - R), (CX + R + 18, CY), (CX, CY + R), (CX - R - 18, CY))
BOX_W, BOX_H = 132, 50

STYLE = (".wa{margin:14px auto 6px;max-width:440px}.wa svg{display:block;width:100%;height:auto}"
         ".wa .wa-box{fill:var(--paper);stroke:var(--frame);stroke-width:1.2}.wa .wa-t{fill:var(--fg);font-size:14px;letter-spacing:.04em}"
         ".wa .wa-arc{fill:none;stroke:var(--accent);stroke-width:2}.wa .wa-head{fill:var(--accent)}"
         ".wa .wa-now{fill:var(--mute);font-size:12px;letter-spacing:.08em}.wa .wa-v{fill:var(--accent);font-size:26px}"
         ".wa a:focus .wa-c{stroke:var(--accent);stroke-width:2}.wa .wa-c{fill:var(--soft);stroke:var(--frame)}"
         # 英語の図（ring の en-fig）の字の色。大きさは SVG の中の字の大きさ（EN_FS）で持つ（下の EN_FS の注）
         ".wa .wa-te{fill:var(--fg)}.wa .wa-nowe{fill:var(--mute)}.wa .wa-ve{fill:var(--accent)}")


# 英語の図の字の大きさ（viewBox の中の値。統括の割り振り 11-08・重なりの見回り state/no-overlap-20261108.md の 1）。英語は日本語より長く、
# 札（幅 132）と真ん中の丸（直径 88）に入らず、「Make the next template」が真ん中の「Current template」に、「Version N」が左右の札に重なった。
# 前は英語の頁の CSS（font-size の px）で替えたが、押す所と字の大きさの床（tests/test_tap_size.py の 12px）に当たり main が落ちたので（11-08）、
# 英語の図を別の SVG にし、大きさは SVG の中で持つ。日本語の図は替えない。画面に出る大きさを 10px 以上にする並べ方は次の直し
EN_FS = {"step": 10.5, "now": 9.5, "version": 15}


def _arc(a, b):
    """札 a から札 b へ、輪の円に沿った矢印（時計回り）。札に重ならないよう、両端を円の上で少し縮める。"""
    import math

    def ang(p):
        return math.atan2(p[1] - CY, p[0] - CX)

    a0, a1 = ang(a), ang(b)
    if a1 <= a0:
        a1 += 2 * math.pi
    gap = 0.42  # 札の幅の分だけ、円の上で避ける（ラジアン）
    s, e = a0 + gap, a1 - gap
    p = lambda t: (CX + R * math.cos(t), CY + R * math.sin(t))  # noqa: E731
    (x0, y0), (x1, y1) = p(s), p(e)
    # 矢じり: 終わりの点で、円の向き（接線）に三角を置く
    tx, ty = -math.sin(e), math.cos(e)
    nx, ny = math.cos(e), math.sin(e)
    head = [(x1 + tx * 7, y1 + ty * 7), (x1 - tx * 3 + nx * 6, y1 - ty * 3 + ny * 6), (x1 - tx * 3 - nx * 6, y1 - ty * 3 - ny * 6)]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in head)
    return (f'<path class="wa-arc" d="M{x0:.1f},{y0:.1f} A{R},{R} 0 0 1 {x1:.1f},{y1:.1f}"/>'
            f'<polygon class="wa-head" points="{pts}"/>')


def _box(x, y, label, lang="ja"):
    lines = LINES.get(label, (label,))
    top = y - (len(lines) - 1) * 9
    if lang == "en":  # 英語の図: 訳の表の英語を、英語の時の大きさで（並べ方は日本語の図と同じ）
        texts = "".join(f'<text class="wa-te" x="{x}" y="{top + i * 18 + 5}" text-anchor="middle" font-size="{EN_FS["step"]}">{esc(en_fig.en(s))}</text>'
                        for i, s in enumerate(lines))
    else:
        texts = "".join(f'<text class="wa-t" x="{x}" y="{top + i * 18 + 5}" text-anchor="middle">{esc(s)}</text>' for i, s in enumerate(lines))
    return f'<rect class="wa-box" x="{x - BOX_W / 2}" y="{y - BOX_H / 2}" width="{BOX_W}" height="{BOX_H}" rx="8"/>{texts}'


# 輪の図の真ん中を押した時の行き先。説明の頁（序の頁）の改善の歴史の節の錨（web.kaizen_rekishi）。前は玩具の頁の足の「型紙の改善の輪」（#kaizen）で、
# 本人の答え（11-07 夕の Q5）「型紙の改善の輪は外して、説明の頁と のこす だけにする」で節を外したので、行き先を替えた（輪の図は残す。窓口の決め 11-07）
HREF = "/about#kaizen-rekishi"


def ring(version=1, href=HREF):
    """輪の図の HTML。version は真ん中に出す今の型紙の版。href は真ん中を押した時の行き先（説明の頁の改善の歴史）。"""
    arcs = "".join(_arc(SPOTS[i], SPOTS[(i + 1) % len(SPOTS)]) for i in range(len(SPOTS)))
    boxes = "".join(_box(x, y, s) for (x, y), s in zip(SPOTS, STEPS))
    said = " → ".join((*STEPS, STEPS[0]))
    v = esc(VERSION.format(n=int(version)))
    center = (f'<a href="{esc(href)}" aria-label="{esc(NOW)} {v}"><circle class="wa-c" cx="{CX}" cy="{CY}" r="44"/>'
              f'<text class="wa-now" x="{CX}" y="{CY - 8}" text-anchor="middle">{esc(NOW)}</text>'
              f'<text class="wa-v" x="{CX}" y="{CY + 22}" text-anchor="middle">{v}</text></a>')
    # 英語の図（英語の頁でだけ見える。en_fig.TOGGLE）。並べ方は日本語の図と同じで、字は訳の表の英語・大きさは EN_FS
    boxes_en = "".join(_box(x, y, s, "en") for (x, y), s in zip(SPOTS, STEPS))
    now_en, v_en = esc(en_fig.en(NOW)), esc(en_fig.en(VERSION.format(n=int(version))))
    said_en = " → ".join(en_fig.phrase(LINES.get(s, (s,))) for s in (*STEPS, STEPS[0]))
    center_en = (f'<a href="{esc(href)}" aria-label="{now_en} {v_en}"><circle class="wa-c" cx="{CX}" cy="{CY}" r="44"/>'
                 f'<text class="wa-nowe" x="{CX}" y="{CY - 8}" text-anchor="middle" font-size="{EN_FS["now"]}">{now_en}</text>'
                 f'<text class="wa-ve" x="{CX}" y="{CY + 22}" text-anchor="middle" font-size="{EN_FS["version"]}">{v_en}</text></a>')
    return (f'<style>{STYLE}{en_fig.TOGGLE}</style><figure class="wa" id="wa"><svg class="ja-fig" viewBox="0 0 {W} {H}" role="img" aria-labelledby="wa-title">'
            f'<title id="wa-title">{esc(said)}</title>{arcs}{boxes}{center}</svg>'
            f'<svg class="en-fig" viewBox="0 0 {W} {H}" role="img" aria-labelledby="wa-title-en">'
            f'<title id="wa-title-en">{esc(said_en)}</title>{arcs}{boxes_en}{center_en}</svg></figure>')


def set_version(sid, data=None):
    """その玩具の今の型紙の版（組の番号。紙の題に刷る数と同じ）。輪の真ん中と型紙の札の脇に出す。"""
    from omochae import hypotheses

    return hypotheses.set_number(data or hypotheses.load(sid))


def current_version(sid, data):
    """その玩具の今の型紙の版（たたき台の、人が採った一番新しい版。無ければ版 1）。"""
    from omochae import hypotheses

    from . import kaizen

    h = hypotheses.sheet_of(sid)
    got = [v["version"] for v in kaizen.versions(sid, h["id"])]
    return max(got) if got else 1
