"""本人のサイトの見直し（11-07 22:16）の ⑤「ここに輪の説明ある方がいいよね。」と、本人の決め「輪の説明は のこす の頁に置く」。

見る事: のこす の頁（手帖の記録の頁）に、学びの輪の文（本人が採った字・loop_figure.ADOPTED）がそのまま 1 回出て、その後に学びの輪の図
（説明の頁と同じ部品 loop_figure.svg()）が続く。置き場は頭の「のこすと型紙が直る事の枠」の後で、上げる節より前。新しい字を書かない
（節の字は ADOPTED だけ）。公開の場（合言葉なし）でも同じ。英語の頁では ADOPTED の英語が出る（日本語が残らない事の全体は test_en_all が見る）。
"""
import html
import os
import pathlib
import re
import sys
import tempfile
import threading
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import loop_figure, naoru  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
ADOPTED = html.escape(loop_figure.ADOPTED, quote=False)


def check(page, where):
    sec = re.search(r'<section class="panel manabi" id="manabi">(.*?)</section>', page, re.S)
    assert sec, f"{where}: 学びの輪の節がある"
    body = sec.group(1)
    # 字は本人が採った文だけ（図の字は部品の WORDS で、ADOPTED から切り出した物。tests/test_loop_figure が見る）
    text = re.sub(r"<svg.*?</svg>", "", body, flags=re.S)
    assert re.sub(r"<[^>]+>", "", text).strip() == html.unescape(ADOPTED), f"{where}: 節の字は ADOPTED だけ"
    assert body.index(ADOPTED) < body.index('class="loop-fig"'), f"{where}: 文の後に図"
    at = page.index('id="manabi"')
    assert page.index(naoru.LINES[0]) < at < page.index('aria-label="上げる"'), f"{where}: 枠の後・上げる節の前"
    # 図の読み上げ（aria-label）にも同じ文が入るので（説明の頁と同じ部品の作り）、数えるのは頁に見える字だけ
    assert re.sub(r"<[^>]+>", "", page).count(ADOPTED) == 1, f"{where}: 文は 1 回"


srv = serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
pub = serve(0, look="tenji", public_open=True)
threading.Thread(target=pub.serve_forever, daemon=True).start()
pbase = f"http://127.0.0.1:{pub.server_address[1]}"
try:
    def get(b, path):
        with urllib.request.urlopen(b + path, timeout=120) as r:
            return r.read().decode("utf-8")

    check(get(base, f"/toy/{G}/techo/kiroku"), "合言葉付きの場")
    check(get(pbase, f"/toy/{G}/techo/kiroku"), "公開の場")
    en = get(base, f"/toy/{G}/techo/kiroku?lang=en")
    assert "experiential learning cycle" in en and ADOPTED not in en, "英語の頁は英語の文"
finally:
    for s in (srv, pub):
        s.shutdown()
        s.server_close()
print("ok のこす の頁に学びの輪の文と図（本人の見直し 22:16 の ⑤）")
