"""全頁の英語（web.i18n・本人の言葉 11-07「サイトは全てのページを英語で読めるようにする。全頁が対象です」・窓口の決め 130735 の案 B）。

見る事:
- 全部の頁の道（全 83 種の玩具の頁と、玩具に依らない頁と断りの頁）の見える字に、訳の表に無い日本語が 1 つも無い。
  後から他の作りが字を足して表に入れ忘れると、ここで落ちる（名指しで出す）。
- ?lang=en で英語になり、cookie で続き、?lang=ja で戻る。道は日本語の頁と同じ。頭に下書きの札が 1 つ出る。
- 前からの英語の頁（/en・本人が採った英文）は替えない。
- 人が書いた字（記録の感想）は訳さない。表の値は数の印（{0}…）が鍵と同じで、内輪の言葉（data/・.json・OWN-）を入れない。
"""
import json
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

from omochae import records  # noqa: E402
from web import en, i18n  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

G = "NDL-1187053-R0000005-L"
table = i18n.table()
PH = re.compile(r"\{\d+\}")
for k, v in table.items():
    # 値の数の印は鍵の中の物だけ（無い印を作ると頁が落ちる）。玩具の名の「（2つ目）」のように、名の英語が数を言わない物は落としてよい
    assert v == i18n.KEEP or set(PH.findall(v)) <= set(PH.findall(k)), ("鍵に無い数の印", k, v)
    assert not re.search(r"data/|\.json|OWN-\d", v), ("内輪の言葉", k, v)
    assert k == " ".join(k.split()) and not re.search(r"\d", PH.sub("", k)), ("鍵の形（空白 1 つ・数は {n}）でない", k)
# repo に入っている記録（11-04 の試行）の人の字（窓口の決め 135434）: 本人の説明は原文を残して英訳を添え、参加者のつぶやきを含む字は訳さない
said = [k for k in table if k.startswith("人の説明:")]
murmurs = [k for k in table if "つぶやき" in k]
assert said and all(table[k].startswith(k) for k in said), "本人の説明は原文を残す"
assert murmurs and all(table[k] == i18n.KEEP for k in murmurs), "参加者のつぶやきは訳さない"

srv = serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
try:
    printed = i18n.prime(base, sources())  # 作りながら見る頁と手帖は刷った後でしか開かないので、雛形ごとに 1 種を刷ってから回す
    assert len(printed) >= 3, printed
    miss = i18n.collect(base, i18n.routes(sources()))
    assert not miss, ("訳の表に無い日本語（python -m web.i18n collect で書き出して表に足す）", len(miss), list(miss.items())[:8])

    def get(path, cookie=""):
        req = urllib.request.Request(base + path, headers={"Cookie": cookie} if cookie else {})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read().decode("utf-8"), r.headers.get_all("Set-Cookie") or []

    page, cookies = get("/?lang=en")
    assert any(c.startswith("utsushi_lang=en;") for c in cookies), cookies
    # 頭の断り（下書きの札）は出さない（本人の言葉 11-07「これ要らない。Draft translation. A native speaker has not checked it yet.」）
    assert '<html lang="en"' in page and 'class="en-draft"' not in page and "Draft translation" not in page and "native speaker" not in page
    assert 'class="nav-lang" href="?lang=ja" lang="ja">日本語</a>' in page, "英語の頁の切り替えは日本語へ戻る口"
    toy, _ = get(f"/toy/{G}", "utsushi_lang=en")
    assert "Goraigo" in toy and "御来迎の図" not in toy
    ja, cookies = get(f"/toy/{G}?lang=ja", "utsushi_lang=en")
    assert '<html lang="ja"' in ja and "en-draft" not in ja and any(c.startswith("utsushi_lang=ja;") for c in cookies)
    assert '<a class="nav-lang" href="?lang=en" lang="en">English</a>' in get("/about")[0], "日本語の頁の切り替えは今の頁の英語へ"
    # 前からの英語の頁は替えない（本人が採った英文）。前からの頁も頭の断りを出さない
    plain, _ = get("/en")
    assert get("/en", "utsushi_lang=en")[0] == plain and "Draft translation" not in plain
    # 人が書いた字は訳さない（機械で訳した他人の言葉を出さない）。札の字は英語になる
    records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた", "impression": "すっと開いた"})
    mine, _ = get(f"/toy/{G}", "utsushi_lang=en")
    assert "すっと開いた" in mine
finally:
    srv.shutdown()
    srv.server_close()
print("ok 全頁の英語: 表に無い日本語 0・切り替え・前からの英語の頁・人の字")
