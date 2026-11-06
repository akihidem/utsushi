"""記録の札を、後から自分や次の人が読める形にする（#130）。

なぜ: 札の見出しは作る側の番号と ISO の時刻で、書いた欄の一部は札に出なかった。押しても断りが返るだけの釦も同じ強さで並んでいた。
"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from api import ask  # noqa: E402
from omochae import loop  # noqa: E402
from web import techo_site  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
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
        return urllib.request.urlopen(r).status
    except urllib.error.HTTPError as e:
        return e.code


def card(page, rid):
    return page.split(f'id="{rid}"', 1)[1].split("</article>", 1)[0]


assert post(f"/toy/{G}/print", {"hypothesis": "H-A"}) in (200, 303)
written = {"first_moved": "外筒の先", "stuck": "折りの向き", "what_if": "折りの幅", "idea": "糊を減らす", "note": "紙が厚かった"}
base_form = {"hypothesis": "H-A", "result": "動いた"}
assert post(f"/toy/{G}/record", {**base_form, **written}) in (200, 303)
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動かない"}) in (200, 303)

page = get(f"/toy/{G}")
full, bare = card(page, "R-0001"), card(page, "R-0002")
# 見出しは学ぶ人の言葉。番号は見出しの外の小さな字。日付は読める形
assert "<h3>仮説 A の紙・動いた</h3>" in full and "R-0001 H-A" not in full, full[:300]
meta = re.search(r'<p class="meta">([^<]*R-0001[^<]*)</p>', full)
assert meta and re.search(r"\d+ 月 \d+ 日", meta.group(1)) and "T" not in meta.group(1), full[:300]
# 書いた欄は全部読める。書いていない欄の名前は出さない
for label, value in (("最初に動いた所", "外筒の先"), ("引っかかった所", "折りの向き"), ("変えると違いが出そうな所", "折りの幅"), ("思いついた事", "糊を減らす"), ("メモ", "紙が厚かった")):
    assert f"{label}: {value}" in full, label
    assert label not in bare, label
# 動かない記録も同じ大きさの見出しで並ぶ（L-07）。成功・失敗の言葉を足さない
assert "<h3>仮説 A の紙・動かない</h3>" in bare
assert "成功" not in full + bare and "失敗" not in full + bare

# 図鑑の行も同じ書き方
assert "仮説 A の紙・動いた（" in get(f"/zukan/{G}"), "図鑑の見出しの書き方"

# 押しても進めない釦は出さず、1 行の文にする
assert loop.save_explanation("R-0001", "大人", "折りが固い", "幅を変える") == []  # 次の記録が残った後なので、作る側の道で足す
keep = ask._key_present
try:
    ask._key_present = lambda: False
    full = card(get(f"/toy/{G}"), "R-0001")
    assert "Claude に聞く" not in full and "動画を見てもらう" not in full, "鍵が無い時は押しても断りが返るだけ"
    assert "AI の返事は、この場では使えません" in full and "鍵" not in full
    ask._key_present = lambda: True
    full = card(get(f"/toy/{G}"), "R-0001")
    assert "Claude に聞く" in full and "動画を見てもらう" not in full, "動画が無い時は見てもらう物が無い"
    assert "動画を上げると、Claude が見えた事を返します" in full
    folder = techo_site.media_dir("R-0001")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "m1.mp4").write_bytes(b"\0")
    # 確認の前の動画は、上げた本人の画面にだけ AI の口を出す（tests/test_video_owner_ai.py）。ここは釦の出し方を見るので、人が物だけと確かめた動画として置く
    (folder / "review.json").write_text('{"m1.mp4": {"shows": "object"}}', encoding="utf-8")
    full = card(get(f"/toy/{G}"), "R-0001")
    assert "Claude に聞く" in full and "動画を見てもらう" in full
    (folder / "m1.mp4").unlink()
    (folder / "review.json").unlink()
    # 手帖の札も同じ
    techo = get(f"/toy/{G}/techo/kiroku")
    assert "Claude に聞く" in techo and "動画を上げると、Claude が見えた事を返します" in techo and "動画を見てもらう" not in techo
    ask._key_present = lambda: False
    techo = get(f"/toy/{G}/techo/kiroku")
    assert "Claude に聞く" not in techo and "AI の返事は、この場では使えません" in techo
finally:
    ask._key_present = keep
# 札の中は 紙の返事（記録そのもの） → 自分の説明 → AI → 次の版 の順に区切る。試した後の紙は 11-06 から刷らないので札に道を出さない
assert "試した後の紙" not in full
assert full.index("・版 ") < full.index("説明: 折りが固い") < full.index("Claude に聞く") < full.index("次の版を作る")
assert full.count('class="step"') == 3, full.count('class="step"')

server.shutdown()
print("ok")
