"""保護者の方へ、ファシリテーターの方への頁（/otona）の試験。本物の API は呼ばない。

本人の決定（11-06）: 道の外に置き、大人向けの説明をここへ集める（声や字の扱い・取り下げ・写真の載せ方・AI（Claude）の役目・場の進め方）。
本人の言葉（11-06）: 全年齢向けで、日本に関心のある海外の人にも使ってほしい。みんなで再現し合う場所を作りたい。
見る事:
1. 2 つの皮で開き、合言葉なしの場でも開く。7 つの節と、どの頁からも来られる道がある
2. 同じ意味の文は、ほかの頁の文のまま（断りの文を 2 通りにしない）
3. 頁が約束した事の裏付けが、今のコードにある（消えたら、ここで気づく）
4. 作る側の内輪の言葉と番号、成績の言葉、順位が出ない
"""
import html
import inspect
import os
import re
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import media_review, records, talk_log  # noqa: E402
from omochae.marks import without_premise  # noqa: E402
from web import about, hanasu, otona, skin, techo_site, toy, tsukuru  # noqa: E402
from web.play_server import serve  # noqa: E402

pages = {k: otona.page(k) for k in ("tenji", "zine")}


def shown(page):
    """画面に見える字。style と script と札の外の属性は見ない。"""
    body = re.sub(r"<(style|script)\b.*?</\1>", "", page, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)))


# 1. 節と道
for look, page in pages.items():
    assert "<title>保護者の方へ、ファシリテーターの方へ" in page and "保護者の方へ、ファシリテーターの方へ" in shown(page.split("</h1>")[0].split("<h1>")[1]).replace(" ", ""), look
    for sec in ("site", "koe", "shashin", "torisage", "ai", "ie", "ba"):
        assert f'id="{sec}"' in page and f'href="#{sec}"' in page, (look, sec)
    assert 'href="/toys"' in page and 'href="/en"' in page, look

about_page = about.page("tenji")
assert 'href="/otona"' in about_page, "序の頁から来られる"
assert 'href="/otona"' in skin.shell("題", "<p>中身</p>"), "どの頁の足からも来られる"
assert 'href="/otona"' not in skin.shell("title", "<p>body</p>", lang="en", foot='<p class="foot">credit</p>'), "英語の頁の足は英語のまま"


def fetch(server, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}", timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


for public_open in (False, True):
    server = serve(0, public_open=public_open)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        status, got = fetch(server, "/otona")
        assert status == 200 and "ファシリテーターの方へ" in got, public_open
    finally:
        server.shutdown()
        server.server_close()

text = shown(pages["tenji"])

# 2. 同じ意味の文は、ほかの頁の文のまま
for w in (hanasu.HOW_BROWSER, tsukuru.CAMERA_PURPOSE):
    assert w in text, w
for w in ("残るのは字だけです。声は録音しません。このサイトは声を受け取りません。残す前に、字を読んで直せます。",
          "名前・学校の名前・住所・電話番号・メールは書かないでください。"):
    assert w in text and w in hanasu.NOTICE, w
gallery_src = inspect.getsource(techo_site)
for w in ("公開のデモでは、写真と動画は上げられません。見た事とひとことは残せます。",
          "フォームは Google のフォームです。写真や動画を添える時は Google に入る必要があり、添えた人の名前とメールがフォームの持ち主に記録されます。送られた物は確かめてから載せます。"):
    assert w in text and w in gallery_src, w
assert "100% で刷り、紙の物差しが 10cm か確かめます。" in text and "100% で刷り、紙の物差しが 10cm か確かめます。" in inspect.getsource(toy)
# 本人が採った文（11-06、AI の名前の書き方）。一字でも変わったら落ちるように、ここに決定の文を書く
assert "残した字は、AI（Claude）が型紙をよくする案を考えるのにも使います。" in text
assert "紙で動いても、昔の作り方が分かったことにはなりません。" in text and "紙で動いても、昔の作り方が分かったことにはなりません。" in about.LOOP

# 3. 約束の裏付け。消えたら、頁の文を直す
assert set(inspect.signature(records.withdraw).parameters) >= {"media_only", "talk_only"}, "記録が理由に使われていても、写真と動画と話した字は消せる"
assert talk_log.drop_for_record and talk_log.set_share, "記録の取り下げで字も消え、作る側がほかの人の頁から外せる"
assert media_review.SHOWS == ("object", "people"), "物だけ / 人や声が入る、の 2 つ"
assert talk_log.blocked("山田小学校の田中です") and talk_log.blocked("電話は 090-1234-5678 です"), "学校の名前と電話番号の形は機械が残さない"
assert not talk_log.blocked("田中さんに教わった"), "名前は機械で全部は見分けられないと書く根拠。ここが変わったら文を直す"

# 4. 内輪の言葉と番号（#135 の表と同じ物）・むずかしい語（#317 の表から）・成績の言葉
for name, shape in (("本人", r"本人"), ("採否", r"採否"), ("仮説の番号", r"(?<![A-Za-z0-9])H-[A-Z0-9]+"), ("記録の番号", r"(?<![A-Za-z0-9])R-\d+"),
                    ("決定の番号", r"(?<![A-Za-z0-9])[JUTW]-\d+"), ("雛形", r"雛形"), ("鍵", r"鍵"), ("見込み", r"見込[みむ]"), ("組の版", r"[a-z_-]+-v\d+"),
                    ("端末", r"端末"), ("版", r"版"), ("連絡先", r"連絡先")):
    for m in re.finditer(shape, text):
        raise AssertionError((name, text[max(0, m.start() - 12):m.end() + 12]))
for w in ("成功", "失敗", "正解", "順位が", "ランキング"):
    assert w not in without_premise(text), w
print("ok 大人の方への頁は 2 つの皮と合言葉なしの場で開き、文はほかの頁の文のままで、約束の裏付けがある")
