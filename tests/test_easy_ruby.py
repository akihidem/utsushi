"""やさしい日本語のルビを全部の漢字に（本人の言葉 11-07 夜「やさしい日本語は全部のページに反映させる。ルビも全ての漢字にふる」「下書きです、はとる」）。

見る事（機械で拾う見張り）:
- 表（data/i18n/yasashii.json と yasashii.d/*.json の全部）の値で、ルビの印 ｜漢字《よみ》 の外に漢字が 1 つも無い。
  値が "="（日本語のまま）の鍵に漢字があると、その字はルビ無しで出るので止める（同じ字にルビを振った値を書く）
- 全部の頁を ?lang=easy で回し、見える字（字の節）でルビの外に残る漢字は、表に鍵が無い字（落ちた字。grove の state/yasashii-gaps の一覧）の物だけ
- 要素を入れられない所（<title>・<option>）と、画面に出る placeholder は、ルビの代わりに 漢字（よみ） の形で読みを添える
- 頁の頭の「下書きです」の札は出ない
"""
import html
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

KANJI = re.compile(r"[㐀-䶿一-鿿豈-﫿々〆ヶ]")

# 表の値: ルビの外に漢字が無い・"=" の鍵に漢字が無い
bad = []
files = [ROOT / "data/i18n/yasashii.json", *sorted((ROOT / "data/i18n/yasashii.d").glob("*.json"))]
for f in files:
    for k, v in json.loads(f.read_text(encoding="utf-8"))["strings"].items():
        if v == i18n.KEEP:
            if KANJI.search(k):
                bad.append((f.name, "日本語のまま（=）の鍵に漢字", k))
        elif KANJI.search(i18n.RUBY.sub("", v)):
            bad.append((f.name, "ルビの外の漢字", "".join(KANJI.findall(i18n.RUBY.sub("", v))), k))
assert not bad, bad[:10]

# 要素を入れられない所と placeholder は 漢字（よみ）
out = i18n.page_easy('<html lang="ja"><head><title>御来迎</title></head><main><select><option>御来迎</option></select>'
                     '<input placeholder="御来迎" alt="御来迎"><p>御来迎</p></main></html>')
assert "<title>御来迎（ごらいごう）</title>" in out and "<option>御来迎（ごらいごう）</option>" in out, out
assert 'placeholder="御来迎（ごらいごう）"' in out and 'alt="御来迎"' in out, out
assert "<p><ruby>御来迎<rt>ごらいごう</rt></ruby></p>" in out and "easy-draft" not in out and "下書" not in out, out

STRIP = re.compile(r"<title[^>]*>.*?</title>|<option[^>]*>.*?</option>|<script.*?</script>|<style.*?</style>|<textarea.*?</textarea>|<ruby>.*?</ruby>|<!--.*?-->", re.S)

srv = serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
try:
    i18n.prime(base, sources())

    def get(path, cookie):
        req = urllib.request.Request(base + path, headers={"Cookie": cookie})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, r.read().decode("utf-8", "replace"), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), e.headers.get("Content-Type", "")

    left = []
    for path in i18n.routes(sources()):
        code, ja, ctype = get(path, "utsushi_lang=ja")
        if not ctype.startswith("text/html") or not ja:
            continue
        miss = []
        i18n.to_en(ja, miss, lang="easy")
        missing = {" ".join(html.unescape(t).split()) for t in miss}
        _, easy, _ = get(path, "utsushi_lang=easy")
        assert "easy-draft" not in easy, (path, "下書きの札")
        body = STRIP.sub("", easy.split("</head>", 1)[-1])
        for node in re.split(r"<[^>]*>", body):
            text = " ".join(html.unescape(node).split())
            if KANJI.search(text) and text not in missing:
                left.append((path, text[:60]))
    assert not left, left[:10]
finally:
    srv.shutdown()
    srv.server_close()
print("ok やさしい日本語: 表の値は全部の漢字にルビ・頁でルビの外に残る漢字は表に無い字だけ・下書きの札なし")
