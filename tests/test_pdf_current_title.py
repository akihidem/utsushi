"""玩具の頁の「PDF を開いて印刷する」は、今の題（今の版の字）で刷った紙だけを開く（11-08 に見つかった食い違い: 公開のサイトの虎の頁の
PDF を開くと、紙の頭の字が「…仮説 A「首を胴の穴に入れ、中の重りで揺らす」版 1」だった。作りながら見る頁と札の版は「版 7」）。

なぜ起きたか: 紙の置き場の名前（H-A_v1.pdf）は仮説と版の数だけで決まり、紙の題の決まり（版は組の番号・仮説の印を出さない。11-07〜11-08）が
替わっても、前に刷った紙の名前は同じままだった。窓は名前で紙を探すので、前の題で刷った紙をそのまま出していた。
刷った組（loop.confirm_sheet の台帳）は今の組（tora-v7）と同じなので、組の照らし（toy.make_go）では拾えなかった。

見る事:
1. 前の題で刷った紙（紙の SVG の頭の字が今の題と違う）がある時、型紙の窓はその紙の PDF と絵を出さず、紙を刷る「つくる」を出す
2. 「つくる」で刷り直すと、窓の PDF は今の題で刷った紙になる（紙の頭の字が今の題）
3. 今の題で刷った紙は、そのまま出す（刷り直しの口を出さない）。御来迎と虎で
"""
import html
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses, loop  # noqa: E402
from web import toy  # noqa: E402
from web.play_server import out_dir, print_latest  # noqa: E402

TIGER = "NDL-1187053-R0000014-R"
TOYS = ("NDL-1187053-R0000005-L", TIGER)


def win(page):
    a = page.index('<section class="sec" id="win">')
    return page[a:page.index('id="kiroku"', a)]


def title_of(sid, hid, v):
    """刷った紙の頭の字（SVG の字の節をつなげた物）。"""
    svg = (out_dir(sid) / f"{hid}_v{v}.svg").read_text(encoding="utf-8")
    return html.unescape(re.sub(r"<[^>]+>", "", svg))


# 3. 今の題で刷った紙は、そのまま出す
for sid in TOYS:
    hid = hypotheses.sheet_of(sid)["id"]
    v = print_latest(sid, hid)
    assert v is not None, (sid, "紙を作れない")
    data = hypotheses.load(sid)
    # 今の題の決まり: 版は組の番号（paper_label）・仮説の印（A・C）を出さない（hypotheses.SHOWN）
    got = title_of(sid, hid, v)
    assert f"{data['toy']} 型紙 {hypotheses.SHOWN}「" in got and hypotheses.paper_label(data, v) in got, (sid, "刷った紙の頭の字が今の題でない", got[:120])
    w = win(toy.toy_page(sid))
    assert f'href="/sheet/{sid}/{hid}_v{v}.pdf"' in w and f'action="/toy/{sid}/print' not in w, (sid, "今の題の紙を出さないか、刷り直しの口が出た")

# 1. 前の題で刷った紙（公開のサイトで見つかった形: 仮説の印つき・版は版の数）に置き替える
hid = hypotheses.sheet_of(TIGER)["id"]
v = loop.latest_version(TIGER, hid)
data = hypotheses.load(TIGER)
svg = out_dir(TIGER) / f"{hid}_v{v}.svg"
text = svg.read_text(encoding="utf-8")
# 今の題は、今刷った紙の頭の字から読む（題を作る部品に頼らず、刷られた物を見る）
now = html.unescape(re.search(re.escape(data["toy"]) + r" 型紙[^<]*", text).group(0))
old = now.replace("仮説「", f"仮説 {hypotheses.letter(hypotheses.sheet_of(TIGER))}「").replace(hypotheses.paper_label(data, v), f"版 {v}")
assert old != now, "前の題の形が作れない"
svg.write_text(text.replace(html.escape(now, quote=False), html.escape(old, quote=False)).replace(now, old), encoding="utf-8")
w = win(toy.toy_page(TIGER))
assert f'href="/sheet/{TIGER}/{hid}_v{v}.pdf"' not in w and '<figure class="sheet">' not in w, "前の題で刷った紙の PDF か絵を出した"
assert re.search(rf'<form method="post" action="/toy/{TIGER}/print#win"[^>]*>.*?つくる</button></form>', w, re.S), "前の題の紙の時に、刷り直す つくる が無い"

# 2. 刷り直すと、窓の PDF は今の題の紙
assert print_latest(TIGER, hid) == v
assert re.sub(r"\s", "", now) in re.sub(r"\s", "", title_of(TIGER, hid, v)) and old not in title_of(TIGER, hid, v), "刷り直した紙が今の題でない"
w = win(toy.toy_page(TIGER))
assert f'href="/sheet/{TIGER}/{hid}_v{v}.pdf"' in w and f'action="/toy/{TIGER}/print' not in w, "刷り直した後に今の紙を出さない"
print("ok 型紙の窓の PDF は今の題で刷った紙だけ: 前の題の紙は出さずに刷り直しの つくる、刷り直すと今の紙。今の題の紙はそのまま（御来迎・虎）")
