"""「次の版を作る」で、何をどれだけ変えられるかが欄で分かり、通らない時に次の一手が読める（#129）。

なぜ: 欄に今の値も幅も無く、通らない時は検査の座標がそのまま出た。6 つの値を試して通ったのは 1 つだけだった。
"""
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")

from omochae import hypotheses, loop  # noqa: E402
from omochae.templates import slider_fan  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台の仮説（次の組は H-C の柄を下から押し上げる形・前の組は H-A。本人の決定 2026-11-06。hypotheses.sheet_id）
GS = hypotheses.sheet_of(G)["id"]
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


# 1 つのブラウザとして動く（記録を残した画面の鍵の cookie を持つ。説明と字を足す口は、その画面にだけ開く）
urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPCookieProcessor()))


def get(path):
    return urllib.request.urlopen(base + path).read().decode()


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    try:
        x = urllib.request.urlopen(r)
        return x.status, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] in (200, 303)
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた"})[0] in (200, 303)
assert post("/record/R-0001/explain", {"text": "折りが固くて戻る", "next_idea": "厚さを変える", "by": "大人"})[0] in (200, 303)
now = {**slider_fan.DEFAULTS, **loop.version_params(G, GS, 1)[0]}


def form_of(page):
    return page.split('action="/record/R-0001/next#next-R-0001"', 1)[1].split("</form>", 1)[0]


def option(page, key):
    return re.search(rf'<option value="{key}">([^<]*)</option>', form_of(page)).group(1)


# 本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などはすべてもちよるに統合する。」で、つくるの頁から記録の札を外した。
# 記録の札の操作（次の版を作る）は手帖の記録の頁にあるので、そこで見る。つくるの頁に次の版の欄が残っていない事も見る
assert 'action="/record/R-0001/next' not in get(f"/toy/{G}"), "つくるの頁に次の版の欄が残った"
page = get(f"/toy/{G}/techo/kiroku")
# 選ぶ項目に、今の値と変えてよい幅が並ぶ（JS なし）
lo, hi = slider_fan.RANGES["fold_width"]
assert option(page, "fold_width") == f"折りの幅（mm）: 今 {now['fold_width']:g}（{lo:g}〜{hi:g}）", option(page, "fold_width")
assert "紙に組める値は、この幅より狭い事があります" in form_of(page)
# 解釈の欄に、上で書いた説明が初めから入っている。同じ問いを 2 度書かせない
assert '<textarea name="interpretation" required>折りが固くて戻る</textarea>' in form_of(page)

form = {"interpretation": "折りが固い", "why": "開きを見る", "by": "大人"}
before = sorted(p.name for p in pathlib.Path(DATA).rglob("*") if p.is_file() and f"{GS}_v" in p.name)
# はみ出す値: 検査の言葉と座標を出さず、学ぶ人の言葉と今の値を出す
code, page = post("/record/R-0001/next", {**form, "param": "fold_width", "to": str(hi)})
assert code == 422, code
assert "A4 からはみ出します" in page and "印字域" not in page and not re.search(r"\(\d+\.\d, ", page), page[:600]
assert f"折りの幅（mm）は今 {now['fold_width']:g} です" in page
# 幅の外の値: 書いてよい幅を言う
code, page = post("/record/R-0001/next", {**form, "param": "fold_width", "to": "99"})
assert code == 422 and f"折りの幅（mm）は {lo:g}〜{hi:g} の間で書いてください" in page and "の外" not in page, page[:600]
# 畳んだ扇が隠れない値: 式の内訳を出さない
code, page = post("/record/R-0001/next", {**form, "param": "push_amount", "to": "30"})
assert code == 422 and "畳んだ扇が筒に隠れません" in page and "を超え" not in page, page[:600]
# 床に落ちたら刷らない（S-07 の線はそのまま）
assert loop.latest_version(G, GS) == 1
assert sorted(p.name for p in pathlib.Path(DATA).rglob("*") if p.is_file() and f"{GS}_v" in p.name) == before
# 通る値は今までどおり刷れて、次の欄の「今」は新しい版の値になる
code, page = post("/record/R-0001/next", {**form, "param": "paper_thickness", "to": "0.2"})
assert code in (200, 303), (code, page[:300])
assert loop.latest_version(G, GS) == 2
assert ": 今 0.2（" in option(get(f"/toy/{G}/techo/kiroku"), "paper_thickness")  # 手帖の記録の頁の欄（上と同じ理由）

server.shutdown()
print("ok")
