"""サイトの入口は、新しく開いた時はいつも日本語から始まる（本人の言葉 11-08「サイトトップのデフォルトの表示は日本語で。」）。

なぜ: 言葉の cookie（utsushi_lang）に 1 年の期限（Max-Age）が付いていて、一度 English を押した端末は、次の日に開き直しても英語の入口が出た。
cookie から期限を外し、ブラウザを閉じれば消える形にする。開いている間は、選んだ言葉のまま頁をたどれる（頁ごとに戻らない）。
見る事:
1. ?lang=en・?lang=easy・?lang=ja で返る utsushi_lang の cookie に、期限（Max-Age・Expires）が無い
2. cookie 無しで開いた / は日本語（<html lang="ja">）で、言葉の cookie を渡さない
3. 開いている間（cookie がある間）は、/ もほかの頁も選んだ言葉のまま
"""
import os
import pathlib
import sys
import tempfile
import threading
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
srv = serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"


def get(path, cookie=""):
    req = urllib.request.Request(base + path, headers={"Cookie": cookie} if cookie else {})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8"), [c for c in r.headers.get_all("Set-Cookie") or [] if c.startswith("utsushi_lang=")]


try:
    # 1. cookie に期限が無い（ブラウザを閉じれば消える）
    for lang in ("en", "easy", "ja"):
        _, cookies = get(f"/?lang={lang}")
        assert len(cookies) == 1 and cookies[0].startswith(f"utsushi_lang={lang};"), (lang, cookies)
        attrs = [a.strip().split("=")[0].lower() for a in cookies[0].split(";")[1:]]
        assert "max-age" not in attrs and "expires" not in attrs, (lang, "言葉の cookie に期限がある（閉じても残る）", cookies[0])
        assert "path" in attrs, (lang, "全部の頁で同じ言葉にするため Path=/", cookies[0])
    # 2. cookie 無しの / は日本語
    # （やさしい日本語の頁も html の lang は ja なので、帯の切り替えの口で見分ける。やさしい日本語の頁だけ「日本語」へ戻る口にルビが付く）
    EASY = 'href="?lang=ja" lang="ja"><ruby>日本語<rt>にほんご</rt></ruby>'
    page, cookies = get("/")
    assert '<html lang="ja"' in page and EASY not in page and not cookies, ("cookie 無しの / が日本語でない", page[:200], cookies)
    # 3. 開いている間は選んだ言葉のまま
    for lang, mark in (("en", '<html lang="en"'), ("easy", EASY)):
        page, _ = get("/", f"utsushi_lang={lang}")
        assert mark in page, (lang, "cookie がある間の / が選んだ言葉でない")
    assert '<html lang="en"' in get(f"/toy/{G}", "utsushi_lang=en")[0], "cookie がある間の玩具の頁が英語でない"
finally:
    srv.shutdown()
    srv.server_close()
print("ok 言葉の cookie: 期限なし（閉じれば消える）・cookie 無しの / は日本語・開いている間は選んだ言葉のまま")
