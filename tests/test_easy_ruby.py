"""やさしい日本語のルビを全部の漢字に（本人の言葉 11-07 夜「やさしい日本語は全部のページに反映させる。ルビも全ての漢字にふる」「下書きです、はとる」）。

見る事（機械で拾う見張り）:
- 表（data/i18n/yasashii.json と yasashii.d/*.json の全部）の値で、ルビの印 ｜漢字《よみ》 の外に漢字が 1 つも無い。
  値が "="（日本語のまま）の鍵に漢字があると、その字はルビ無しで出るので止める（同じ字にルビを振った値を書く）
- 全部の頁を ?lang=easy で回し、見える字（字の節）でルビの外に残る漢字は、表に鍵が無い字（落ちた字。grove の state/yasashii-gaps の一覧）の物だけ
- 要素を入れられない所（<title>・<option>）と、画面に出る placeholder は、ルビの代わりに 漢字（よみ） の形で読みを添える
- SVG の字（text・tspan）は印を外した字（読みを添えると図の札がはみ出した。#591。読みは図のすぐ上の文が持つ）なので、頁の見張りから外す
- 頁の頭の「下書きです」の札は出ない
"""
import concurrent.futures as cf
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
svg = i18n.page_easy('<html lang="ja"><main><svg><title>御来迎</title><text>御来迎</text></svg></main></html>')
assert "<text>御来迎</text>" in svg and "<title>御来迎（ごらいごう）</title>" in svg, svg

STRIP = re.compile(r"<title[^>]*>.*?</title>|<option[^>]*>.*?</option>|<script.*?</script>|<style.*?</style>|<textarea.*?</textarea>|<text\b[^>]*>.*?</text>|<ruby>.*?</ruby>|<!--.*?-->", re.S)


def check_page(item):
    """1 つの道の日本語の頁を、サーバと同じ出口（i18n.page_easy・play_server の _send）でやさしい日本語にして、
    ルビの外に残る漢字のうち表に鍵が無い字でない物を返す。別の process で回すので、頭の名だけを使う（module の上に置く）。"""
    path, ja = item
    miss = []
    easy = i18n.page_easy(ja, miss)
    missing = {" ".join(html.unescape(t).split()) for t in miss}
    out = [(path, "下書きの札")] if "easy-draft" in easy else []
    body = STRIP.sub("", easy.split("</head>", 1)[-1])
    for node in re.split(r"<[^>]*>", body):
        text = " ".join(html.unescape(node).split())
        if KANJI.search(text) and text not in missing:
            out.append((path, text[:60]))
    return out



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

    # 前は道（約 750）ごとに日本語とやさしい日本語の 2 枚をサーバから 1 つずつ読み、混んだ機械で 5 分を超えて、run_floors の
    # 1 本 300 秒の上限で「検査できない」になった（11-08・#605 の ./run.sh）。サーバのやさしい日本語は日本語の頁に page_easy を
    # 掛けた物（play_server._send・/en の下は掛けない）なので、日本語の頁を 1 枚だけ読み、同じ出口をこちらで掛ける。
    # 読むのは thread で並べ（網の待ち）、変換と照らしは process で並べる（字の処理は 1 つの process の中では並ばない）。
    # 見る事は前と同じ。サーバが出したやさしい日本語の頁そのものの形は test_easy_all が見る
    def fetch(path):
        code, ja, ctype = get(path, "utsushi_lang=ja")
        return (path, ja) if ctype.startswith("text/html") and ja and not re.match(r"/en(?:[/?#]|$)", path) else None

    with cf.ThreadPoolExecutor(8) as ex:
        pages = [x for x in ex.map(fetch, i18n.routes(sources())) if x]
finally:
    srv.shutdown()
    srv.server_close()

# 照らしは別の process で並べる。fork で分けるのは、この試験を __main__ として読み直さないため（spawn・forkserver だと子が
# この file の頭から回し直し、サーバをまた立てる）。サーバと読む thread を止めた後に fork する（thread のある process の fork は危ない）
import multiprocessing  # noqa: E402

with cf.ProcessPoolExecutor(min(8, os.cpu_count() or 2), mp_context=multiprocessing.get_context("fork")) as ex:
    left = [hit for hits in ex.map(check_page, pages, chunksize=16) for hit in hits]
assert len(pages) > 100, len(pages)  # 道を読めていない時に、照らす物が無くて通ってしまわないように
assert not left, left[:10]
print("ok やさしい日本語: 表の値は全部の漢字にルビ・頁でルビの外に残る漢字は表に無い字だけ・下書きの札なし")
