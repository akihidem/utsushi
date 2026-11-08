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
from omochae import hypotheses  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
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
        return urllib.request.urlopen(r).status
    except urllib.error.HTTPError as e:
        return e.code


def card(page, rid):
    """手帖の記録の頁のその記録の札（錨は記録の番号・次の札の頭まで）。つくるの頁から記録の札を外した（本人の言葉 11-08「復元の記録などはすべて
    もちよるに統合する。」）ので、札の釦と字は手帖の記録の頁の札で見る"""
    rest = page.split(f'id="{rid}"', 1)[1]
    return rest.split('<div class="item" id="R-', 1)[0]


assert post(f"/toy/{G}/print", {"hypothesis": GS}) in (200, 303)
written = {"first_moved": "外筒の先", "stuck": "折りの向き", "what_if": "折りの幅", "idea": "糊を減らす", "note": "紙が厚かった"}
base_form = {"hypothesis": GS, "result": "動いた"}
assert post(f"/toy/{G}/record", {**base_form, **written}) in (200, 303)
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない"}) in (200, 303)

# 書いた欄（最初に動いた所・引っかかった所・変えると違いが出そうな所・思いついた事）は、もちよる の記録の札の畳み「のこした記録」に出る（#653）。
# つくるの頁には出さない。メモ（ひとこと）は もちよる に出さず、その画面の手帖の記録の札にだけ出る（統括の答え 11-08 の C・tests/test_mochiyoru_record_details.py が見る）。
# 書いていない記録（R-0002）に欄の名前は出さない（どの欄も もちよる の頁の全体で 1 回だけ）
toy_page = get(f"/toy/{G}")
shared = get("/gallery")
for label, value in (("最初に動いた所", "外筒の先"), ("引っかかった所", "折りの向き"), ("変えると違いが出そうな所", "折りの幅"), ("思いついた事", "糊を減らす")):
    assert shared.count(f"{label}: {value}") == 1 and shared.count(f"{label}: ") == 1, label
    assert label not in toy_page, (label, "つくるの頁に記録の欄が残った")
assert "紙が厚かった" not in shared and "紙が厚かった" not in toy_page, "メモは もちよる と つくるの頁に出さない"
# 記録の番号と紙と結果は、手帖の記録の札の頭の 1 行（成功・失敗の言葉を足さない。L-07: 動かない記録も同じ形で並ぶ）
kiroku = get(f"/toy/{G}/techo/kiroku")
full, bare = card(kiroku, "R-0001"), card(kiroku, "R-0002")
# 紙の名（「C の紙」）は仮説の表記をそろえる直し（本人の言葉 452）で替わるので、形だけを見る
assert re.search(r"R-0001　[^　<]+の紙　動いた", full) and re.search(r"R-0002　[^　<]+の紙　動かない", bare), (full[:200], bare[:200])
assert "成功" not in full + bare and "失敗" not in full + bare

# 前は図鑑の行も同じ書き方かを見ていた。図鑑の頁は外した（本人の言葉 11-08「図鑑のページ要らない」）

# 押しても進めない釦は出さず、1 行の文にする
assert loop.save_explanation("R-0001", "大人", "折りが固い", "幅を変える") == []  # 次の記録が残った後なので、作る側の道で足す
keep = ask._key_present
try:
    ask._key_present = lambda: False
    full = card(get(f"/toy/{G}/techo/kiroku"), "R-0001")
    assert "Claude に聞く" not in full and "動画を見てもらう" not in full, "鍵が無い時は押しても断りが返るだけ"
    assert "AI の返事は、この場では使えません" in full and "鍵" not in full
    ask._key_present = lambda: True
    full = card(get(f"/toy/{G}/techo/kiroku"), "R-0001")
    assert "Claude に聞く" in full and "動画を見てもらう" not in full, "動画が無い時は見てもらう物が無い"
    assert "動画を上げると、Claude が見えた事を返します" in full
    folder = techo_site.media_dir("R-0001")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "m1.mp4").write_bytes(b"\0")
    # 確認の前の動画は、上げた本人の画面にだけ AI の口を出す（tests/test_video_owner_ai.py）。ここは釦の出し方を見るので、人が物だけと確かめた動画として置く
    (folder / "review.json").write_text('{"m1.mp4": {"shows": "object"}}', encoding="utf-8")
    __import__('omochae.media_review', fromlist=['bind_legacy']).bind_legacy()  # 名だけの確認は通さない（安全の事項 2 の続き）ので、試験の置き場の確認も今の中身に結び直す
    full = card(get(f"/toy/{G}/techo/kiroku"), "R-0001")
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
# 手帖の記録の札も同じ順（記録の 1 行 → 説明の字 → AI → 次の版）。手帖の札は説明の字に「説明: 」の札を付けず、段の箱（class="step"）も持たない（techo_site.feedback）
assert full.index("R-0001") < full.index("折りが固い") < full.index("Claude に聞く") < full.index("次の版を作る")

server.shutdown()
print("ok")
