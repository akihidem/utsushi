"""送った後の返事と通らない理由を、着いた場所で読める（#121）。

なぜ試験にするか: 返事の文は予想の節の頭にだけ出ていて、着く場所は記録の節か型紙の窓なので、文は画面の外にあった。
通らない時は頁の頭に戻り、書いた中身も消えていた。どの節に文が入るかは字の位置で見られる（押した後の画面の見え方は別に、ブラウザで見た）。
"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from api import ask  # noqa: E402
from web.play_server import serve  # noqa: E402
from web.toy import reply_note  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class Stay(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(Stay)


def call(path, data=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    r = urllib.request.Request(base + path, data=body, method="POST" if data is not None else "GET",
                               headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    try:
        x = opener.open(r)
        return x.status, "", x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", ""), e.read().decode()


def landed(where, anchor):
    """送った後の 303 を辿る。着く先の錨が anchor で、頁の中に返事の文がある事を見る。"""
    code, at, _ = where
    assert code == 303 and at.endswith(f"#{anchor}"), (code, at, anchor)
    return call(at)[2]


def note_at(page, anchor, role):
    """文は 1 つで、役の印があり、錨の直後（節や札の頭）にある。"""
    assert page.count('id="msg"') == 1, page.count('id="msg"')
    assert f'id="{anchor}"' in page, anchor
    start = page.index(f'id="{anchor}"')
    pos = page.index('id="msg"')
    assert start < pos < start + 200, (anchor, pos - start, page[start:start + 240])
    assert f'role="{role}"' in page[max(pos - 40, 0):pos + 40], page[max(pos - 40, 0):pos + 60]
    return page[pos:page.index("</p>", pos)]


# 予想の前に手帖を開く: 理由の文と予想の欄が見える。
page = landed(call(f"/toy/{G}/techo"), "yosou")
assert "先に予想を書くと、手帖が開きます" in note_at(page, "yosou", "status") and 'name="text"' in page

# 予想: 通らないと予想の欄に、書いた中身つきで戻る。通ると次の段の頭に文が出る。
code, _, page = call(f"/toy/{G}/own", {"name": "筒の<仮説>", "how": "", "evidence": "右の図"})
assert code == 422 and note_at(page, "yosou", "alert")
assert 'value="筒の&lt;仮説&gt;"' in page and 'value="右の図"' in page, "書いた中身を欄に戻す（字は esc）"
assert "筒の<仮説>" not in page
page = landed(call(f"/toy/{G}/predict", {"text": "筒を押すと扇が開く"}), "kasetsu")
assert "予想を残しました" in note_at(page, "kasetsu", "status")

# 自分の仮説: 予想の後は欄が畳まれているので、通らない時は開いて戻す。
code, _, page = call(f"/toy/{G}/own", {"name": "筒の案", "how": "", "evidence": "右の図"})
assert code == 422 and note_at(page, "yosou", "alert")
assert '<details open><summary>自分の仮説を立てる' in page and 'value="筒の案"' in page
page = landed(call(f"/toy/{G}/own", {"name": "筒の案", "how": "押す", "evidence": "右の図"}), "own-OWN-1")
assert "仮説を残しました" in note_at(page, "own-OWN-1", "status")

# 刷る: 通らないと仮説の節に、通ると型紙の窓に文が出る。
code, _, page = call(f"/toy/{G}/print", {"hypothesis": "H-ZZ"})
assert code == 422 and "仮説 H-ZZ は無い" in note_at(page, "kasetsu", "alert")
page = landed(call(f"/toy/{G}/print", {"hypothesis": "H-A"}), "win")
assert "紙を作りました" in note_at(page, "win", "status")

# 聞く: 通らない時も、答えの時も、聞く欄に着く。
code, _, page = call(f"/toy/{G}/ask", {"hypothesis": "H-B", "question": "谷折りって？"})
assert code == 422 and note_at(page, "ask", "alert") and 'value="谷折りって？"' in page

# 記録: 通らないと欄の上に理由が出て、中身が戻る。通ると、今残した記録の札に着く。
bad = {"hypothesis": "H-A", "note": "3 枚目で<止まった>", "first_moved": "筒", "opener": "糸"}
code, _, page = call(f"/toy/{G}/record", bad)
assert code == 422 and note_at(page, "kiroku", "alert")
assert "3 枚目で&lt;止まった&gt;</textarea>" in page and 'name="first_moved" value="筒"' in page
assert re.search(r"<option selected>糸</option>", page) and '<option value="H-A" selected>' in page
good = bad | {"result": "動かない", "note": "3 枚目で止まった"}
code, _, page = call(f"/toy/{G}/record", good | {"result": "ない結果"})
assert code == 422 and '" checked' not in page[page.index('id="record"'):page.index("</form>", page.index('id="record"'))], "無い値に印を付けない"
where = call(f"/toy/{G}/record", good)
rid = re.search(r"R-\d{4}", where[1]).group(0)
page = landed(where, rid)
assert "記録を残しました" in note_at(page, rid, "status")
start = page.index(f'id="{rid}"')
assert 'name="next_idea"' in page[start:start + 3000], "札の中に次の欄（説明）がある"

# 説明: 札の中に戻る。AI の返事の文も札に出る。
code, _, page = call(f"/record/{rid}/explain", {"by": "", "text": "筒が<支えた>", "next_idea": "折りを増やす"})
assert code == 422 and note_at(page, rid, "alert")
assert "筒が&lt;支えた&gt;</textarea>" in page and 'value="折りを増やす"' in page
page = landed(call(f"/record/{rid}/explain", {"by": "本人", "text": "筒が支えた", "next_idea": "折りを増やす"}), rid)
assert "説明を残しました" in note_at(page, rid, "status")
page = landed(call(f"/record/{rid}/ai-interpret", {}), rid)
assert "Claude が答えます" in note_at(page, rid, "status")
page = landed(call(f"/record/{rid}/ai-observe", {}), rid)
assert note_at(page, rid, "status")

# 次の版: 欄を開いて、その上に理由を出し、書いた中身を戻す。手帖から来た印も保つ。
form = {"interpretation": "折りが<多い>", "param": "fold_count", "why": "口に当たる", "by": "本人", "back": "techo"}
for to, says in (("29", "筒の口の角に当たって"), ("abc", "新しい値は数で書く")):
    code, _, page = call(f"/record/{rid}/next", form | {"to": to})
    assert code == 422 and says in note_at(page, f"next-{rid}", "alert"), (to, code)
    box = page[page.index(f'id="next-{rid}"'):]
    assert "<details open>" in box[:400] and "折りが&lt;多い&gt;</textarea>" in box
    assert f'name="to" inputmode="decimal" required value="{to}"' in box and 'value="口に当たる"' in box and 'value="本人"' in box
    assert '<option value="fold_count" selected>' in box and 'name="back" value="techo"' in box
code, _, page = call(f"/record/{rid}/next", form | {"to": "29", "why": " ", "by": " "})
assert code == 422 and page.count('id="msg"') == 1
two = reply_note(["理由 1", "理由 <2>"], "")
assert two.count("id=") == 1 and "理由 1" in two and "理由 &lt;2&gt;" in two, "理由が何個でも id は 1 つ"
page = landed(call(f"/record/{rid}/next", {k: v for k, v in form.items() if k != "back"} | {"to": "26"}), "win")
assert "版 2 の紙を作りました" in note_at(page, "win", "status")

# 手帖に戻る時は、手帖の頁に文が出る。
page = landed(call(f"/record/{rid}/ai-interpret", {"back": "techo"}), "mine")
assert "Claude が答えます" in note_at(page, "mine", "status")

# 通らなかった時に錨へ着くよう、欄の送り先に錨がある。
page = call(f"/toy/{G}")[2]
for want in (f"/toy/{G}/predict#yosou", f"/toy/{G}/own#yosou", f"/toy/{G}/print#kasetsu", f"/toy/{G}/print-own#own-OWN-1", f"/toy/{G}/ask#ask",
             f"/toy/{G}/record#kiroku", f"/record/{rid}/next#next-{rid}"):
    assert f'action="{want}"' in page, want
# AI の釦は鍵のある時だけ出る。呼ばずに釦の送り先だけを見る。
ask._key_present = lambda: True
page = call(f"/toy/{G}")[2]
ask._key_present = lambda: False
assert f'action="/record/{rid}/ai-interpret#{rid}"' in page
rid2 = re.search(r"R-\d{4}", call(f"/toy/{G}/record", good)[1]).group(0)
assert f'action="/record/{rid2}/explain#{rid2}"' in call(f"/toy/{G}")[2]

# 外から渡した印は、字の位置にしか使わない。
assert "<script>mark" not in call(f"/toy/{G}?msg=%3Cscript%3Emark&at=%22%3E%3Cscript%3Emark")[2]
page = call(f"/toy/{G}?msg=x&at=no-such")[2]
assert note_at(page, "yosou", "status"), "知らない印の時も文を落とさない"
server.shutdown()
print("ok")
