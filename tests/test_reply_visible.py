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
from omochae.contrib import MAX_BODY  # noqa: E402
from web import play_server  # noqa: E402
from web.play_server import serve  # noqa: E402
from web.toy import reply_note  # noqa: E402

G = "NDL-1187053-R0000005-L"
from omochae import hypotheses, records  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class Stay(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


# 1 つのブラウザとして動く（記録を残した画面の鍵の cookie を持つ。説明と字を足す口は、その画面にだけ開く）
opener = urllib.request.build_opener(Stay, urllib.request.HTTPCookieProcessor())


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


# 予想の段は #266 で外した（本人の決定 11-05）。手帖は予想なしでそのまま開く。
assert call(f"/toy/{G}/techo")[0] == 200

# 作りながら見る: 刷る前は開かず、仮説の節に着いて理由を読める（#289）。文は頁の頭より 1 画面下にあった。
page = landed(call(f"/toy/{G}/tsukuru"), "kasetsu")
assert "先に紙を作ると、作りながら見る頁が開きます" in note_at(page, "kasetsu", "status")


# 刷る: 通らないと仮説の節に、通ると型紙の窓に文が出る。
code, _, page = call(f"/toy/{G}/print", {"hypothesis": "H-ZZ"})
# 無い仮説の断りは、内部の番号（H-ZZ）を出さない（本人の答え 11-08「そろえる。」・統括の決め）
alert = note_at(page, "kasetsu", "alert")
assert code == 422 and "H-ZZ" not in alert, ("無い仮説の断りに内部の番号が出る", alert)
assert alert and getattr(play_server, "NO_HYPOTHESIS", None) and play_server.NO_HYPOTHESIS in alert, alert
page = landed(call(f"/toy/{G}/print", {"hypothesis": GS}), "win")
assert "紙を作りました" in note_at(page, "win", "status")
# 別の仮説の紙がある時でも、頼んだ仮説の紙が無ければ同じ所に着く。
page = landed(call(f"/toy/{G}/tsukuru?h=H-B"), "kasetsu")
assert "先に紙を作ると、作りながら見る頁が開きます" in note_at(page, "kasetsu", "status")

# 聞く: つくるの頁の聞く欄は外した（設計の問い 4 の答え「推しのとおり。」・本人の言葉 11-08 477）。JS の無い聞く口は作りながら見る頁にあり、その答えと
# 通らない時の文は、つくるの頁の型紙の窓の頭に出る（toy_page の answer）。紙を作る前は作りながら見る頁が開かないので、通らない時は直に送った時だけ。
# 欄が無いので書いた字は戻さない
code, _, page = call(f"/toy/{G}/ask", {"hypothesis": "H-B", "question": "谷折りって？"})
assert code == 422 and note_at(page, "win", "alert") and 'id="ask"' not in page

# 記録: 受け口は残る（玩具の頁の記録の欄は、本人の答え 11-07 夕の Q3 で のこす へ寄せた）。通らないと #kiroku の節に理由が出る。
# 欄が無いので書いた字は戻らない（字を書く所は手帖の のこす で、通らなかった時の扱いは tests/test_techo_step.py が見る）。通ると、今残した記録の札に着く。
bad = {"hypothesis": GS, "note": "3 枚目で<止まった>", "first_moved": "筒", "opener": "糸"}
code, _, page = call(f"/toy/{G}/record", bad)
assert code == 422 and note_at(page, "kiroku", "alert")
assert 'id="record"' not in page and "3 枚目で&lt;止まった&gt;" not in page, "玩具の頁に記録の欄は無い"
good = bad | {"result": "動かない", "note": "3 枚目で止まった"}
code, _, page = call(f"/toy/{G}/record", good | {"result": "ない結果"})
assert code == 422 and note_at(page, "kiroku", "alert"), "無い値は受けない"
# 記録の札は手帖の記録の頁にある（つくるの頁から記録の札を外した・本人の言葉 11-08「復元の記録などはすべてもちよるに統合する。」）。
# 記録を残した後と、札への返事は、手帖の記録の頁の記録の並び（#mine）に着く。通らない時の理由は、その頁のその札の頭（錨は記録の番号）に出る
where = call(f"/toy/{G}/record", good)
rid = records.all_records(G)[-1]["id"]
page = landed(where, "mine")
assert "記録を残しました" in note_at(page, "mine", "status")
start = page.index(f'id="{rid}"')
assert 'name="next_idea"' in page[start:start + 3000], "札の中に次の欄（説明）がある"

# 説明: 札の中に戻る。AI の返事の文も札に出る。
# 断りの形は、長すぎる次の思いつきで見る（書いた人は書かなくてもよい欄になった。本人の決定 11-06）
too = "折りを増やす" + "あ" * MAX_BODY
code, _, page = call(f"/record/{rid}/explain", {"by": "", "text": "筒が<支えた>", "next_idea": too})
assert code == 422 and note_at(page, rid, "alert")
# 手帖の記録の頁の説明の欄は 1 行の欄（textarea でない）なので、書いた字は value に戻る
assert 'value="筒が&lt;支えた&gt;"' in page and f'value="{too}"' in page
page = landed(call(f"/record/{rid}/explain", {"by": "本人", "text": "筒が支えた", "next_idea": "折りを増やす"}), "mine")
assert "説明を残しました" in note_at(page, "mine", "status")
page = landed(call(f"/record/{rid}/ai-interpret", {}), "mine")
assert "AI の返事は、この場では使えません" in note_at(page, "mine", "status")
page = landed(call(f"/record/{rid}/ai-observe", {}), "mine")
assert note_at(page, "mine", "status")

# 次の版: 欄を開いて、その上に理由を出し、書いた中身を戻す。手帖から来た印も保つ。
form = {"interpretation": "折りが<多い>", "param": "fold_count", "why": "口に当たる", "by": "本人", "back": "techo"}
for to, says in (("46", "筒の口の角に当たって"), ("abc", "新しい値は数で書く")):
    code, _, page = call(f"/record/{rid}/next", form | {"to": to})
    assert code == 422 and says in note_at(page, f"next-{rid}", "alert"), (to, code)
    box = page[page.index(f'id="next-{rid}"'):]
    assert "<details open>" in box[:400] and "折りが&lt;多い&gt;</textarea>" in box
    assert f'name="to" inputmode="decimal" required value="{to}"' in box and 'value="口に当たる"' in box and 'value="本人"' in box
    assert '<option value="fold_count" selected>' in box and 'name="back" value="techo"' in box
code, _, page = call(f"/record/{rid}/next", form | {"to": "46", "why": " ", "by": " "})
assert code == 422 and page.count('id="msg"') == 1
two = reply_note(["理由 1", "理由 <2>"], "")
assert two.count("id=") == 1 and "理由 1" in two and "理由 &lt;2&gt;" in two, "理由が何個でも id は 1 つ"
page = landed(call(f"/record/{rid}/next", {k: v for k, v in form.items() if k != "back"} | {"to": "45"}), "win")
# 版の字は組の番号の呼び方（窓口の決定 11-07・#513 の (a)。同じ画面の窓の札と同じ字）
assert f"{hypotheses.label_of(hypotheses.current_set(hypotheses.load(G)), 2)} の紙を作りました" in note_at(page, "win", "status")

# 手帖に戻る時は、手帖の頁に文が出る。
page = landed(call(f"/record/{rid}/ai-interpret", {"back": "techo"}), "mine")
assert "AI の返事は、この場では使えません" in note_at(page, "mine", "status")

# 通らなかった時に錨へ着くよう、欄の送り先に錨がある。
page = call(f"/toy/{G}")[2]
# 刷る口は頭の「つくる」1 つで、紙がある今は窓の紙へ行くリンクなので、刷る欄はここには無い（本人のサイト体験レビュー 11-07 の 3。前は札の「型紙を見る」の
# #kasetsu）。作れなかった時の文を窓の錨で読む事は tests/test_sheet_window.py が見る
assert f'action="/toy/{G}/print#kasetsu"' not in page
# 記録の欄は のこす へ寄せた（本人の答え 11-07 夕の Q3）ので、玩具の頁に /record の送り先は無い（受け口は残り、返事は #kiroku に出る。上で見た）
# 記録の札の欄（次の版・説明・AI）は手帖の記録の頁にある（つくるの頁から記録の札を外した・本人の言葉 11-08「復元の記録などはすべてもちよるに統合する。」）
kiroku = call(f"/toy/{G}/techo/kiroku")[2]
assert f'action="/toy/{G}/ask#ask"' not in page and f'action="/record/{rid}/next#next-{rid}"' not in page, "つくるの頁に聞く欄か次の版の欄が残った"
assert f'action="/record/{rid}/next#next-{rid}"' in kiroku, "手帖の記録の頁に次の版の欄が無い"
assert f'action="/toy/{G}/record#kiroku"' not in page
# AI の釦は鍵のある時だけ出る。呼ばずに釦の送り先だけを見る。
ask._key_present = lambda: True
page = call(f"/toy/{G}/techo/kiroku")[2]
ask._key_present = lambda: False
assert f'action="/record/{rid}/ai-interpret#{rid}"' in page
# 記録を残した後の戻り先は手帖の記録の頁（#mine）なので、記録の番号は戻り先でなく記録の置き場から読む
call(f"/toy/{G}/record", good)
rid2 = records.all_records(G)[-1]["id"]
assert f'action="/record/{rid2}/explain#{rid2}"' in call(f"/toy/{G}/techo/kiroku")[2] and f'/record/{rid2}/explain' not in call(f"/toy/{G}")[2]

# 外から渡した印は、字の位置にしか使わない。
assert "<script>mark" not in call(f"/toy/{G}?msg=%3Cscript%3Emark&at=%22%3E%3Cscript%3Emark")[2]
page = call(f"/toy/{G}?msg=x&at=no-such")[2]
assert note_at(page, "kasetsu", "status"), "知らない印の時も文を落とさない"
server.shutdown()
print("ok")
