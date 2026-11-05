"""予想の段を無くして、開いたらすぐ作る形（本人の決定 2026-11-05、#242）を試験で見る。

本人の言葉: 「予想の段を無くして、すぐ作る形にする」「他の人の作ったものギャラリーは作る」。

見る事:
- 予想を書かずに、玩具の頁に仮説の札と刷る口が出て、刷れる。手帖と作りながら見る頁も開く。
- 画面に予想の入力と「あなたの予想」が無い。予想の口は閉じている。
- 型紙は正解でなく AI が考えた仮説である事が、作る節の頭に出る。
- 他の人が作った物が、玩具の頁とギャラリーの両方で見られる。写真の無い記録も言葉で並ぶ。順位の語は無い。
- 工夫の欄が記録に残り、札とギャラリーと工作の様子に出る（本人の言葉 11-05「工夫で乗り切る過程」）。
- #208 の形（誰かの文が別の人の画面に「あなたの予想」と出る）が起きようがない。
- 合言葉なしで開いた場では、ギャラリーにも写真を出さない（J-028）。
"""
import json
import os
import pathlib
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
tmp = tempfile.TemporaryDirectory()
os.environ["OMOCHAE_DATA"] = f"{tmp.name}/data"
os.environ["OMOCHAE_SAMPLES"] = "0"
os.chdir(tmp.name)

from omochae import hypotheses, making_log, records  # noqa: E402
from web.play_server import serve  # noqa: E402
from web import techo_site  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def get(path):
    return urllib.request.urlopen(base + path, timeout=30).read().decode("utf-8")


def post(path, form):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(form).encode(), headers={"Origin": base, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        return urllib.request.build_opener(NoRedirect).open(req, timeout=120).status
    except urllib.error.HTTPError as e:
        return e.code


page = get(f"/toy/{G}")
# すぐ作れる
assert 'id="kasetsu"' in page and "すぐ作る" in page
for h in hypotheses.load(G)["hypotheses"]:
    assert f'value="{h["id"]}"' in page and h["name"] in page
assert f'action="/toy/{G}/print"' in page
# 予想の段が無い
assert "/predict" not in page and "あなたの予想" not in page and "先に、予想を書く" not in page and "kazasu" not in page
assert post(f"/toy/{G}/predict", {"text": "x"}) == 404
assert post(f"/toy/{G}/predict-choice", {"choice": "x"}) == 404
try:
    get(f"/toy/{G}/kazasu")
    raise AssertionError("かざして選ぶ頁は外した")
except urllib.error.HTTPError as e:
    assert e.code == 404
assert not hasattr(hypotheses, "need_prediction") and not hasattr(hypotheses, "save_prediction")
# 前提の明示。頭の札が仮説の札より前にある
assert 'id="premise"' in page and "AI が考えた仮説" in page and "正解ではありません" in page
assert page.index('id="premise"') < page.index('class="plates"')
# 自分の仮説の道は残す（J-008）
assert f'action="/toy/{G}/own"' in page
# 手帖は予想なしで開く
assert "手帖" in get(f"/toy/{G}/techo")
# 刷れて、作りながら見る頁が開く
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"}) == 303
assert "H-A" in get(f"/toy/{G}/tsukuru") or "作りながら" in get(f"/toy/{G}/tsukuru")
# 他の人の作った物。写真が無くても言葉で並ぶ
assert "他の人が作った物" in get(f"/toy/{G}")
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動かない", "impression": "扇が引っかかった", "fix_part": "扇", "fix_change": "折り目を深くした", "fix_outcome": "少し開いた"}) == 303
page = get(f"/toy/{G}")
assert "工夫: 扇 / 折り目を深くした / 少し開いた" in page and "扇が引っかかった" in page
assert page.index('id="minna"') < page.index('id="kaizen"')
gallery = get("/gallery")
assert "他の人が作った物" in gallery and "扇が引っかかった" in gallery and "折り目を深くした" in gallery
for word in ("順位", "1 位", "人気", "ランキング", "予想"):
    assert word not in gallery, word
# 工作の様子にも工夫が届く（輪の材料）
fixes = making_log.summary(G, hypotheses.load(G).get("template", "slider_fan"))["fixes"] if making_log.summary.__code__.co_argcount == 2 else making_log.summary(G)["fixes"]
assert any(f["change"] == "折り目を深くした" for f in fixes)
# 3 欄そろわない工夫は床で落ちる（部品も結果も無い工夫は次の版の材料にならない）
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動かない", "fix_change": "直した"}) == 422
# 言葉の無い記録は、ギャラリーに札だけで並ばない
rid = records.all_records(G)[-1]["id"]
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた"}) == 303
quiet = records.all_records(G)[-1]["id"]
assert rid != quiet and quiet not in get("/gallery")
# 写真を出さない場では、ギャラリーに画像の道が無い
d = techo_site.media_dir(rid)
d.mkdir(parents=True, exist_ok=True)
(d / "m1.jpg").write_bytes(b"\xff\xd8\xff")
assert f"/record/{rid}/media/" in techo_site.gallery_page([G], photos=True)
closed = techo_site.gallery_page([G], photos=False)
assert f"/record/{rid}/media/" not in closed and "扇が引っかかった" in closed
print("ok")
