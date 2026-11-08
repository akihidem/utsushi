"""改善の輪がサイトで回る（本人の方針 11-05 朝「作ったものの感想と動きを報告してもらったら、サイト側もループを回し、型紙の改善をする。
そうすることでより良いおもちゃの型紙を提供できる」）。本物の API は呼ばない。

見る線: 報告に感想の欄がある → 説明 → 寸法を 1 つ変えて次の版 → 次に刷る人は直した版を受け取る → 玩具の頁と /loop に、どの報告がどの版を変えたかが出る。
成績に見える言葉と数は出さない（J-025）。感想にも連絡先の形を残さない（F3）。
"""
import json
import os
import pathlib
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA

from omochae import hypotheses  # noqa: E402
from omochae.marks import without_premise  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台の仮説（次の組は H-C の柄を下から押し上げる形・前の組は H-A。本人の決定 2026-11-06。hypotheses.sheet_id）
GS = hypotheses.sheet_of(G)["id"]
GL = hypotheses.SHOWN  # 頁と紙のたたき台の呼び名。11-08 から印（A・C）は出さない（本人の答え 11-08「そろえる。」・hypotheses.SHOWN）
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


# 1 つのブラウザとして動く（記録を残した画面の鍵の cookie を持つ。説明と字を足す口は、その画面にだけ開く）
opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor())


def get(path):
    try:
        r = opener.open(base + path)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def post(path, data):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    try:
        r = opener.open(req)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] == 303
page = get(f"/toy/{G}")[1]
# 報告の欄に感想がある。輪の節は、報告が無い時もその旨を出す
# 玩具の頁には記録の欄が無く、のこす（記録の頁）への道が 1 本（本人の答え 11-07 夕の Q3 で、玩具の頁の記録の欄は のこす へ寄せた。受け口は残る）
assert 'name="impression"' not in page and f'href="/toy/{G}/techo/kiroku"' in page and 'id="kaizen"' not in page
# 輪の節は作る側の様子の頁にある（本人の答え 11-07 夕の Q5 で、玩具の頁の足の「型紙の改善の輪」は外し、作る側の様子の頁 /loop/<印> へ移した）
assert 'id="kaizen"' in get(f"/loop/{G}")[1] and "報告はまだありません" in get(f"/loop/{G}")[1]
# 感想にも連絡先の形は残さない
code, body = post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない", "impression": "電話は 090-1234-5678 です"})
assert code == 422, code
# 報告: 動き（結果）と感想
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない", "opener": "紙の力", "stuck": "3 枚目の折り目", "impression": "折るのは楽しかったが、扇が半分で止まった"})[0] == 303
rec = json.loads((pathlib.Path(DATA) / "records/R-0001.json").read_text(encoding="utf-8"))
assert rec["impression"] == "折るのは楽しかったが、扇が半分で止まった" and rec["sheet_version"] == 1
page = get(f"/toy/{G}")[1]
# 記録の札は玩具の頁に無く、手帖の記録の頁と もちよる に出る（本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。
# 復元の記録などはすべてもちよるに統合する。」）
assert "折るのは楽しかったが、扇が半分で止まった" not in page and 'id="R-0001"' not in page, "玩具の頁に記録の札が残った"
assert "R-0001" in get(f"/toy/{G}/techo/kiroku")[1] and "<p>折るのは楽しかったが、扇が半分で止まった</p>" in get("/gallery")[1]
# 説明の前は「説明を待つ報告」。説明の後は「次の版を待つ報告」（輪の節は作る側の様子の頁。本人の答え Q5）
loop_page = get(f"/loop/{G}")[1]
assert "説明を待つ報告 1 件" in loop_page and "次の版を待つ報告" not in loop_page
# 待つ報告から、手帖の記録の頁の記録の並びへ行ける（前は玩具の頁の記録の札 #R-0001 へ。札は玩具の頁から外した・本人の言葉 11-08）
assert f'href="/toy/{G}/techo/kiroku#mine"' in loop_page and f'href="/toy/{G}#R-0001"' not in loop_page, "待つ報告から記録の頁へ行けない"
assert post("/record/R-0001/explain", {"text": "折りが固くて戻る力が足りない", "next_idea": "折りを減らす", "by": "作った人"})[0] in (200, 303)
loop_page = get(f"/loop/{G}")[1]
assert "次の版を待つ報告 1 件" in loop_page and "報告から直した版はまだありません" in loop_page
# 輪を回す: 寸法を 1 つ変えて次の版
code, body = post("/record/R-0001/next", {"interpretation": "折りが固い", "param": "fold_count", "to": "24", "why": "開きを見る", "by": "サイトの係"})
assert code in (200, 303), body[:300]
kz = get(f"/loop/{G}")[1].split('id="kaizen"')[1]  # 輪の節は作る側の様子の頁（本人の答え 11-07 夕の Q5 で、玩具の頁の足の「型紙の改善の輪」は外し、作る側の様子の頁 /loop/<印> へ移した）
assert f"{GL} 版 2" in kz and "折りの数" in kz and "R-0001" in kz and "次の版を待つ報告" not in kz
assert "サイトの係" not in kz, "採った人の名前は出さない（自由な文で、名前を書かない線）"
# 次に作る人: 刷ると直した版（版 2）が出る。窓も最新の版
out = pathlib.Path(DATA) / "play" / G
(out / f"{GS}_v2.pdf").unlink()
(out / f"{GS}_v2.png").unlink()
assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] == 303
assert (out / f"{GS}_v2.pdf").exists(), "刷るのは一番新しい版"
page = get(f"/toy/{G}")[1]
# 版の呼び方は組の番号（窓口の決定 11-07・#513 の (a)）。組の中の直しの版 2 は「版 <組の番号>（直し 2）」
assert f'<img src="/sheet/{G}/{GS}_v2.png"' in page and f"<b>{hypotheses.label_of(hypotheses.current_set(hypotheses.load(G)), 2)}</b>" in page
# その版への報告は、版 2 への返事として残る
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた", "impression": "前より開いた"})[0] == 303
assert json.loads((pathlib.Path(DATA) / "records/R-0002.json").read_text(encoding="utf-8"))["sheet_version"] == 2
assert post(f"/toy/{G}/step", {"hypothesis": GS, "step": "2", "event": "stuck"})[0] == 303
section = get(f"/loop/{G}")[1].split('id="kaizen"')[1].split("</section>")[0]
# サイト側の一覧: 報告のある玩具・版・待っている報告
code, lp = get("/loop")
assert code == 200 and "改善の輪" in lp and "御来迎" in lp and f'href="/toy/{G}"' in lp and "#kaizen" not in lp
for w in ("成功", "失敗", "正解", "順位", "点数"):
    assert w not in without_premise(lp) and w not in without_premise(kz), w
# 輪の節と一覧に、結果を数えた数を出さない（動いた・止まったの数は成績に見える。J-025）。数えられる記録と札を置いてから見る
for w in ("動いた", "動かない", "止まった"):  # 一覧は画面に出る所だけを見る（頁の頭の CSS の注に同じ字がある）
    assert w not in without_premise(section) and w not in without_premise(lp.rsplit("</style>", 1)[-1]), w
# 学ぶ人の頁からは道を置かない（集計は学ぶ人の画面に出さない線。道を知っている作る側が開く）
for path in ("/about", "/toys", "/", f"/toy/{G}"):
    assert 'href="/loop' not in get(path)[1], path

# 検品の指摘の再発の見張り: 窓は刷ってある版だけを出し、版を言わなければ一番新しい版
page = get(f"/toy/{G}")[1]
assert f'see={GS}&kind=sheet&v=2#win" aria-current' in page and f'see={GS}&kind=sheet&v=1#win" aria-current' not in page, "仮説の札は一番新しい版へ"
(out / f"{GS}_v1.pdf").unlink()
(out / f"{GS}_v1.png").unlink()
only2 = get(f"/toy/{G}")[1]
# 組の番号の呼び方（#513 の (a)）。版 1 は「版 14」で、型紙の窓の頭の輪の図の真ん中（型紙の版）と同じ字になるので、版の札は札の道（v=1）で見分ける
ban = lambda n: hypotheses.label_of(hypotheses.current_set(hypotheses.load(G)), n)
assert f"/sheet/{G}/{GS}_v1.png" not in only2 and f"<b>{ban(2)}</b>" in only2 and f'v=1#win">{ban(1)}</a>' not in only2.split('id="win"')[1].split('id="kiroku"')[0], "刷っていない版を出さない"
assert get(f"/toy/{G}?see={GS}&kind=sheet&v=1")[0] == 200 and f'<img src="/sheet/{G}/{GS}_v2.png"' in get(f"/toy/{G}?see={GS}&kind=sheet&v=1")[1], "無い版を言われても一番新しい版へ"
assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] == 303  # 元に戻す（版 2 を刷り直す。版 1 は無いまま）
# 報告の版: 版が 2 つある時は、どの版の紙かを聞き、言われた版の報告として残す（版 1 で作っていた人の報告が版 2 の記録にならない）
# 御来迎の今の組で刷れるのは、たたき台（GS）だけ（本人の決定 11-05、J-032）。頁の札の直しは後の PR で、今は刷る所で断る。
assert post(f"/toy/{G}/print", {"hypothesis": "H-B"})[0] == 422
from omochae import hypotheses  # noqa: E402

hypotheses.print_sheet(G, GS, str(out / f"{GS}_v1"), 1)
page = get(f"/toy/{G}")[1]
assert 'id="record"' not in page, "玩具の頁に記録の欄は無い（版の番号は受け口へ送る値で残る）"
assert post(f"/toy/{G}/record", {"hypothesis": GS, "sheet_version": "1", "result": "動かない", "impression": "版 1 で作っていた"})[0] == 303
assert json.loads((pathlib.Path(DATA) / "records/R-0003.json").read_text(encoding="utf-8"))["sheet_version"] == 1
assert post(f"/toy/{G}/record", {"hypothesis": GS, "sheet_version": "9", "result": "動いた"})[0] == 303
assert json.loads((pathlib.Path(DATA) / "records/R-0004.json").read_text(encoding="utf-8"))["sheet_version"] == 2, "刷っていない版を言われたら一番新しい版"
# 一番新しい版が検査に落ちる時は、1 つ前の版を刷る（その仮説の紙が誰にも刷れなくならない）
real = hypotheses.print_sheet
hypotheses.print_sheet = lambda s, h, o, v=1, pending=None: 3 if v == 2 else real(s, h, o, v)
(out / f"{GS}_v1.pdf").unlink()
assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] == 303 and (out / f"{GS}_v1.pdf").exists()
hypotheses.print_sheet = real
print("ok: 改善の輪")
