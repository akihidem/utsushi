"""スマホと iPad で押し間違えない床（#137）。押す所の高さ 44px 以上、字は 12px 以上。ブラウザなしで、配る頁の CSS を見る。

なぜ CSS を見るか: ./run.sh はブラウザなしで動く決まり。本当の高さは tests/measure_tap.py が手元の Chrome で測る（手で回す）。
ここは、床の CSS がどの頁にも届いている事と、小さい字の指定が戻っていない事を見る。
字の欄と選ぶ欄は名前の下で箱の幅いっぱいに出す（#290）。本当の幅は measure_tap.py が測り、ここは配る頁の label の形と床の行を照らす。
"""
import html.parser
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import records  # noqa: E402
from web import skin  # noqa: E402
from web.play_server import serve  # noqa: E402

MIN_FONT = 12
G = "NDL-1187053-R0000005-L"
records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
# kazasu と tsukuru の頁は入れていない。#242 の枝で形が変わるので、床はそこで入れる
PAGES = ["/", "/about", "/toys", f"/toy/{G}", f"/toy/{G}/techo", f"/toy/{G}/tsukuru", "/en", f"/en/toy/{G}", "/zukan", f"/zukan/{G}", f"/zukan/{G}/yomi", "/gallery", "/loop", f"/loop/{G}"]
# BASE が全幅にする組。床の inline-flex が掛かると、名前の横に細く並ぶ（#290）。これだけを block に戻す
WIDE = {"input[type=text]", "input[type=number]", "textarea", "select"}
# 札と隠した入力は今の形のまま。ここに無い形が label に入ったら、どちらかを決める
KEEP = {"input[type=radio]", "input[type=checkbox]", "input[type=file]", "input[type=range]", "input[type=hidden]"}


class LabelFields(html.parser.HTMLParser):
    """label の中の入力の形と、label の直下かどうかを集める。床の :has(>…) は直下にしか当たらないので。"""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.open_tags, self.found = [], []

    def handle_starttag(self, tag, attrs):
        if tag in ("input", "select", "textarea") and "label" in self.open_tags:
            kind = f"input[type={dict(attrs).get('type')}]" if tag == "input" else tag
            self.found.append((kind, self.open_tags[-1] == "label"))
        if tag not in self.VOID:
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if tag in self.open_tags:
            while self.open_tags.pop() != tag:
                pass


# 床は机の幅の見た目を変えない。スマホと iPad の幅か、指で触る機器の時だけ効く
assert "(max-width:1100px)" in skin.TAP_FLOOR and "(pointer:coarse)" in skin.TAP_FLOOR, skin.TAP_FLOOR[:80]
assert "min-height:44px" in skin.TAP_FLOOR
for selector in (".nav a", ".tabs a", ".links a", ".notice-back a", "summary", "button", "select", "label"):
    assert selector in skin.TAP_FLOOR, selector
# 床は button に display を付ける。止めないと、hidden にした釦（鏡を出す・声で聞く・扇の釦・作りながら見るの札）が狭い幅で出たままになる（#321）
assert "[hidden]{display:none!important}" in skin.TAP_FLOOR, "幅の狭い画面で、hidden にした釦が隠れない"
# label:not(.sr) と頭をそろえ、後に置かないと効かない（label:has(>textarea) は詳細度で負ける）。select は床で inline-flex になるので、これも戻す
back = re.search(r"([^{}]*)\{display:block\}", skin.TAP_FLOOR)
assert back, "字の欄を持つ label を block に戻す行が無い"
assert skin.TAP_FLOOR.index("label:not(.sr){display:inline-flex") < back.start(), "inline-flex の後に置く"
targets = [s.strip() for s in back.group(1).split(",")]
assert sorted(targets) == sorted([f"label:not(.sr):has(>{kind})" for kind in WIDE] + ["label:not(.sr)>select"]), targets

printed = False
seen = set()
for look in ("tenji", "zine"):
    # 皮はサーバごとに 1 つ（本人の決定 11-05）。?look= は効かない
    server = serve(0, look=look)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if not printed:
        urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/print", data=b"hypothesis=H-A", headers={"Origin": base}), timeout=120)
        # 説明まで残した記録に「次の版」の欄が出る（畳んであっても頁には入っている）
        rid, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
        told = urllib.parse.urlencode({"text": "途中で止まった", "next_idea": "軸を長くする", "by": "試験"}).encode()
        urllib.request.urlopen(urllib.request.Request(f"{base}/record/{rid}/explain", data=told, headers={"Origin": base}), timeout=60)
        printed = True
    for path in PAGES:
        page = urllib.request.urlopen(f"{base}{path}", timeout=60).read().decode()
        where = (look, path)
        assert skin.TAP_FLOOR in page, ("床の CSS が届いていない", where)
        small = [float(x) for x in re.findall(r"font-size:\s*([\d.]+)px", page) if float(x) < MIN_FONT]
        assert not small, ("小さい字の指定", where, sorted(set(small)))
        ems = re.findall(r"font-size:\s*(0?\.\d+)r?em", page)
        assert all(float(x) >= .75 for x in ems), ("小さい字の指定（em）", where, ems)
        fields = LabelFields()
        fields.feed(page)
        for kind, direct in fields.found:
            assert kind in WIDE | KEEP, ("label の中の入力の形が表に無い", where, kind)
            assert direct or kind not in WIDE, ("label の直下でない字の欄。床の行が当たらず細いまま", where, kind)
            seen.add(kind)
    # 断りの頁（404）にも床が届く（#136）
    try:
        urllib.request.urlopen(f"{base}/no-such-page", timeout=60)
        raise AssertionError("404 のはず")
    except urllib.error.HTTPError as e:
        assert e.code == 404 and skin.TAP_FLOOR in e.read().decode(), e.code
    server.shutdown()
assert WIDE <= seen, ("空振り: 字の欄と選ぶ欄を見ていない", sorted(seen))

# 皮なしの形（画面からは通らず、頁を直に作る時の形）にも床が届く
from web import kuzushi, zukan  # noqa: E402

for maker in (zukan._page, kuzushi._page):
    assert skin.TAP_FLOOR in maker("題", "<p>本文</p>"), maker.__module__
print("ok")
