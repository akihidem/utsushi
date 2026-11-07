"""やさしい日本語（3 つ目の言葉・lang=easy。web.i18n の頭の注・本人の言葉 11-07 夜「サイト、言語でやさしい日本語選べるように。
このモードはルビつけてやさしい日本語に全体の文が変換されるモード」）の土台。

見る事:
- 全部の頁の道（雛形ごとに 1 種を刷った後の作りながら見る頁・手帖も）が、やさしい日本語で 200 で開く。表に無い字は元の日本語のまま
  （全部そろわなくても壊れない）
- 表の値の ｜漢字《よみ》 が、字の節では <ruby>漢字<rt>よみ</rt></ruby> に、属性ではルビの印を外した字になる。ルビの形が崩れない
- ?lang=easy で cookie が付き、頁は日本語のまま（html の lang="ja"）、頭に「このページのやさしい日本語は、下書きです。」の札が 1 つ、帯の やさしい が 日本語 へ戻る口に替わる。
  ?lang=ja で戻る。英語の頁では やさしい の切り替えは訳さずにそのまま出る
- 表の形: 鍵は空白 1 つ・数は {n}、値の数の印は鍵の中の物だけ、ルビの印は ｜ と《》がそろう
"""
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import i18n  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

G = "NDL-1187053-R0000005-L"
PH = re.compile(r"\{\d+\}")
easy = i18n.table("easy")
for k, v in easy.items():
    assert k == " ".join(k.split()) and not re.search(r"\d", PH.sub("", k)), ("鍵の形", k)
    assert set(PH.findall(v)) <= set(PH.findall(k)), ("鍵に無い数の印", k, v)
    plain = i18n.RUBY.sub("", v)
    assert "｜" not in plain and "《" not in plain and "》" not in plain, ("ルビの印が崩れている", k, v)

# ルビの形（字の節は <ruby>、属性は印を外す）
assert i18n.ruby_html("｜型紙《かたがみ》を刷る") == "<ruby>型紙<rt>かたがみ</rt></ruby>を刷る"
assert i18n.ruby_plain("｜型紙《かたがみ》を刷る") == "型紙を刷る"
sample = '<!doctype html><html lang="ja"><main><p title="御来迎">御来迎</p><p>表に無い字</p><script>"御来迎"</script></main></html>'
out = i18n.page_easy(sample)
assert '<p title="御来迎"><ruby>御来迎<rt>ごらいごう</rt></ruby></p>' in out, out
assert "<p>表に無い字</p>" in out and '<script>"御来迎"</script>' in out and '<html lang="ja">' in out
# <title> と <option> の中は要素を入れられないので、ルビの印を外した字（タブの題に <ruby> が字のまま出ないように）
titled = i18n.page_easy('<html lang="ja"><head><title>御来迎</title></head><main><select><option>御来迎</option></select><p>御来迎</p></main></html>')
assert "<title>御来迎</title>" in titled and "<option>御来迎</option>" in titled, titled
assert "<p><ruby>御来迎<rt>ごらいごう</rt></ruby></p>" in titled, "字の節にはルビ"
assert out.count('class="easy-draft"') == 1 and "このページのやさしい<ruby>日本語<rt>にほんご</rt></ruby>は、<ruby>下書<rt>したが</rt></ruby>きです。" in out

srv = serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
try:
    i18n.prime(base, sources())

    def get(path, cookie=""):
        req = urllib.request.Request(base + path, headers={"Cookie": cookie} if cookie else {})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, r.read().decode("utf-8", "replace"), r.headers.get_all("Set-Cookie") or [], r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), [], e.headers.get("Content-Type", "")

    bad = []
    for path in i18n.routes(sources()):
        code, body, _, ctype = get(path, "utsushi_lang=easy")
        ja_code = get(path)[0]
        if code != ja_code:  # 日本語で開ける頁は、やさしい日本語でも同じに開く（日本語で 404 の道は 404 のまま）
            bad.append((path, code, ja_code))
            continue
        if code == 200 and ctype.startswith("text/html"):
            head = body.split("</title>")[0] if "</title>" in body else ""
            if "<ruby>" in head or body.count('class="easy-draft"') != 1 or "<ruby><ruby>" in body or "｜" in re.sub(r"<script.*?</script>|<textarea.*?</textarea>", "", body, flags=re.S):
                bad.append((path, "ルビか札の形"))
    assert not bad, bad[:8]
    code, top, cookies, _ = get("/?lang=easy")
    assert code == 200 and any(c.startswith("utsushi_lang=easy;") for c in cookies)
    assert '<html lang="ja"' in top and top.count('class="easy-draft"') == 1
    assert '<ruby>御来迎<rt>ごらいごう</rt></ruby>' in top, "入口の札の玩具の名にルビ"
    assert 'class="nav-lang nav-easy" href="?lang=ja" lang="ja">日本語</a>' in top and '<a class="nav-lang" href="?lang=en" lang="en">English</a>' in top
    code, ja, cookies, _ = get("/?lang=ja", "utsushi_lang=easy")
    assert "easy-draft" not in ja and "<ruby>御来迎" not in ja and any(c.startswith("utsushi_lang=ja;") for c in cookies)
    assert i18n.EASY_LINK in ja, "日本語の頁の帯に やさしい の切り替え"
    code, en_page, _, _ = get("/?lang=en")
    assert i18n.EASY_LINK in en_page and "easy-draft" not in en_page, "英語の頁では やさしい の切り替えは訳さずに出す"
finally:
    srv.shutdown()
    srv.server_close()
print("ok やさしい日本語の土台: 全部の頁が開く・ルビの形・切り替えと cookie・英語の頁は替えない")
