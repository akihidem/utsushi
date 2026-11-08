"""本人のサイトの見直し（11-07 22:16）の ⑤「ここに輪の説明ある方がいいよね。」と、本人の決め「輪の説明は のこす の頁に置く」。

見る事: のこす の頁（手帖の記録の頁）に、学びの輪の文（本人が採った字・loop_figure.ADOPTED）がそのまま 1 回出て、その後に学びの輪の図
（説明の頁と同じ部品 loop_figure.svg()）が続く。置き場は頭の「のこすと型紙が直る事の枠」の後で、上げる節より前。
11-08 から、節の頭に 1 本の輪の名の見出し「うつしの輪」、図の下に正直な 1 行（loop_figure.HONEST）が入る（本人の決め「この案で組み直す」）。公開の場（合言葉なし）でも同じ。英語の頁では ADOPTED の英語が出る（日本語が残らない事の全体は test_en_all が見る）。
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
    # 11-08 の組み直し（本人の決め「この案で組み直す」）: 節は 見出し「うつしの輪」→ 本人が採った文（ADOPTED・一字も替えない）→ 1 本の輪の図 →
    # 図の下の正直な 1 行（HONEST）。図の中の字は部品の字で、tests/test_loop_figure が見る
    text = re.sub(r"<svg.*?</svg>", "", body, flags=re.S)
    plain = re.sub(r"<[^>]+>", "", text).strip()
    assert plain == loop_figure.NAME + html.unescape(ADOPTED) + loop_figure.HONEST, f"{where}: 節の字は 見出し・ADOPTED・正直な 1 行だけ"
    assert body.index(f"<h2>{loop_figure.NAME}</h2>") < body.index(ADOPTED) < body.index('class="loop-fig"') < body.index(loop_figure.HONEST), f"{where}: 見出し → 文 → 図 → 1 行"
    at = page.index('id="manabi"')
    # 記入の節のすぐ下（本人の言葉 11-08「のこすのうつしの輪は、記入欄の下にする。」）。直った例の集（naoru の枠）はその下
    assert page.index('id="kinyu"') < at < page.index(naoru.LINES[0]) < page.index('aria-label="上げる"'), f"{where}: 記入の節の後・直った例の集の前"
    between = page[page.index('id="kinyu"'):at]
    assert 'class="naoru"' not in between and "手帖をひらく" not in between, f"{where}: 記入の節と輪の節の間に、ほかの節が入らない"
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
    assert "The template is a guess the AI came up with." in en and ADOPTED not in en, "英語の頁は英語の文"
finally:
    for s in (srv, pub):
        s.shutdown()
        s.server_close()
print("ok のこす の頁に学びの輪の文と図（本人の見直し 22:16 の ⑤）")
