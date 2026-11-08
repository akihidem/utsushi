"""作りながら見るの最後の手順（#321）。手順の最後まで来た人が次にする事を迷わず、途中で押した札が組み上がりとして残らない事を見る。

見る線:
- 最後の手順の一番大きい札は組み上がりの札で、押すと記録の欄へ進む。途中の手順には出さない。札と案内の字は tsukuru の定数で見て、本人が採った文（2026-11-06）と一字ずつ照らす。
- 途中の手順の組み上がりの出来事は受けない（作る様子の集計がずれるため）。
- JS が無くても同じ道を通る。この試験は JS を動かさずに札を送るので、その道そのものを見ている。JS がある時も同じフォームで送る事を、頁の字で見る。
- 祝いの言葉にしない。組み上がりを成績にしない（J-025）。

なぜ確かめを関数に分けて全部回すか: 直す前に落ちる所を 1 回の出力でそろえて見るため（要件ごとに、どれが落ちたかが名前で分かる）。
本物の API は呼ばない。紙の指紋には触らない。
"""
import html
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, making_log  # noqa: E402
from web import naoru, tsukuru  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
WHO = "ab12cd34ef"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def get(path):
    try:
        r = opener.open(base + path)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def post(path, data):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    try:
        r = opener.open(req)
        return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)


def step(n, event, hid=GS, **more):
    return post(f"/toy/{G}/step", {"hypothesis": hid, "step": str(n), "event": event, **more})


def tile(body, value):
    """その札の字と、隠れているかと、一番大きい札か。同じ札は 1 つだけ（前の小さい札が残っていても落ちる）。"""
    found = re.findall(rf'<button name="event" value="{value}"([^>]*)>(.*?)</button>', body, re.S)
    assert len(found) == 1, f"{value} の札が {len(found)} 個"
    attrs, inner = found[0]
    # のこす の札は、中の上の段に本人の字（.ask）、下の段に札の名（.nm）を持つ。札の名は .nm の字（無ければ札の字の全部）
    nm = re.search(r'<span class="nm">([^<]*)</span>', inner)
    label = nm.group(1) if nm else re.sub(r"<[^>]+>", "", inner)
    return label, "hidden" in attrs, 'class="go"' in attrs


def done_events(sid=None):
    return [e for e in making_log.steps(sid or G) if e.get("event") == "done"]


assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] == 303
total = tsukuru.count(G, GS)
assert total >= 3


def big_tile_on_the_last_step():
    body = get(f"/toy/{G}/tsukuru?h={GS}&n={total}")[1]
    assert tile(body, "next")[1], "最後の手順の一番大きい札が「次の手順へ」のまま"
    label, hidden, big = tile(body, "done")
    assert not hidden and big, "最後の手順で組み上がりの札が一番大きい札でない"
    assert label == tsukuru.DONE_LABEL


def not_shown_midway():
    for n in (1, total - 1):
        body = get(f"/toy/{G}/tsukuru?h={GS}&n={n}")[1]
        label, hidden, big = tile(body, "next")
        assert label == "次の手順へ" and not hidden and big, f"手順 {n} の一番大きい札が「次の手順へ」でない"
        assert tile(body, "done")[1], f"途中の手順 {n} に組み上がりの札が出ている"


def midway_leaves_nothing():
    before = len(done_events())
    for n in (1, total - 1):
        for more in ({}, {"json": "1"}):
            code = step(n, "done", **more)[0]
            assert code == 422, f"途中の手順 {n} の組み上がりを受けた（{code}）"
    assert len(done_events()) == before, "途中の手順の組み上がりが残った"


def road_to_the_record():
    # 本人の答え 11-08「B。」・統括の決め (a): 最後の手順の一番大きい札は「のこす」で、押すと組み上がりを残して、のこすの頁（手帖の記録の頁）へ直に行く。
    # 前は玩具の頁の記録の欄（#kiroku）へ送り、そこから のこす へもう 1 押し要った
    code, _, headers = step(total, "done", who=WHO)
    assert code == 303, code
    to = urllib.parse.urlsplit(headers["Location"])
    q = dict(urllib.parse.parse_qsl(to.query))
    # 着く印は記入の節（#kinyu・頁の頭）。前の #mine は頁の一番下の上げる節で、記入の節を飛び越えた（別の目の確かめ 11-08）
    assert to.path == f"/toy/{G}/techo/kiroku" and to.fragment == "kinyu", f"のこすの頁の記入の節へ送っていない: {headers['Location']}"
    assert q.get("msg") == tsukuru.DONE_NOTE and q.get("at") == "kinyu", q
    code, body = get(f"{to.path}?{to.query}")
    assert code == 200, code
    # 組み上がりを残した事の案内は、記入の節のすぐ上に 1 回（上げる節には出さない）
    note = f'<p id="msg">{html.escape(tsukuru.DONE_NOTE)}</p>'
    assert body.count(note) == 1 and body.index(note) < body.index('id="kinyu"') < body.index('id="mine"'), "案内が記入の節の上に無い"


def passes_which_sheet():
    # 頁から刷れるのはたたき台だけ（J-032）。前に刷った別の紙で作っている人の形は、試作の玩具に紙の口で直に刷って見る。
    toy = "NDL-1187053-R0000019-L"
    out_dir(toy).mkdir(parents=True, exist_ok=True)
    assert hypotheses.print_sheet(toy, "H-B", str(out_dir(toy) / "H-B_v1"), 1) == 0
    code, _, headers = post(f"/toy/{toy}/step", {"hypothesis": "H-B", "step": str(tsukuru.count(toy, "H-B")), "event": "done"})
    # のこすの頁へ直に行く形にしたので、行き先に紙の印は渡さない（のこすの頁は紙を選ぶ欄を持たない）。どの紙で組み上がったかは、作る様子の記録に残る
    assert code == 303 and headers["Location"].startswith(f"/toy/{toy}/techo/kiroku"), f"のこすの頁へ送っていない: {headers['Location']}"
    assert any(e.get("hypothesis_id") == "H-B" and e.get("event") == "done" for e in done_events(toy)), "どの紙で組み上がったかが残らない"


def who_is_kept_so_nobody_counts_as_quit():
    me = "zz12cd34ef"
    assert step(total, "stuck", who=me)[0] == 303
    assert step(total, "done", who=me)[0] == 303
    rec = [e for e in done_events() if e.get("who") == me]
    assert len(rec) == 1 and rec[0]["step"] == total and rec[0]["hypothesis_id"] == GS, rec
    assert making_log.summary(G)["completion"]["quit_steps"].get(GS, {}) == {}, "作り終えた人が途中でやめた人に数えられた"


def js_takes_the_same_road():
    body = get(f"/toy/{G}/tsukuru?h={GS}")[1]
    assert "#tiles button:not([value=done])" in body, "JS が組み上がりの札を横取りしている（JS が無い時と道が分かれる）"
    assert "w.name='who'" in body, "フォームで送る時に、その場限りの印が抜ける"
    assert "goNext.hidden=n>=items.length" in body and "goDone.hidden=n<items.length" in body, "JS で進んだ時に札が替わらない"
    assert "msg-done" not in body, "使わなくなった案内が頁に残っている"


def hidden_tile_stays_hidden_on_narrow_screens():
    # 幅の狭い画面の skin.TAP_FLOOR は button に display を付ける。床の側で止めないと、スマホで 2 つの大きい札が並ぶ（実物のブラウザで見つけた）。
    body = get(f"/toy/{G}/tsukuru?h={GS}")[1]
    assert "[hidden]{display:none!important}" in body, "幅の狭い画面で、隠した札が出る"


def back_is_not_shown_on_the_first_step():
    # 手順 1 の「戻る」は押しても何も起きない（実物のブラウザで見つけた）。#321 の最後の手順の札と同じ形で、出さない。
    assert tile(get(f"/toy/{G}/tsukuru?h={GS}&n=1")[1], "back")[1], "手順 1 に戻るの札が出ている"
    label, hidden, _ = tile(get(f"/toy/{G}/tsukuru?h={GS}&n=2")[1], "back")
    assert label == "戻る" and not hidden, "手順 2 に戻るの札が無い"
    body = get(f"/toy/{G}/tsukuru?h={GS}")[1]
    assert "goBack.hidden=n<=1" in body, "JS で進んだ時に戻るの札が替わらない"


def one_step_when_there_is_no_text():
    # 手順の文が作れない時（頁は手順の紙の絵だけで動く）は 1 段だけなので、その段が最後の手順。
    saved = tsukuru.step_texts
    tsukuru.step_texts = lambda *a, **k: []
    try:
        body = get(f"/toy/{G}/tsukuru?h={GS}")[1]
        assert tile(body, "next")[1] and not tile(body, "done")[1], "文の無い紙で組み上がりの札が出ない"
        assert step(1, "done")[0] == 303
    finally:
        tsukuru.step_texts = saved


def words_are_the_ones_the_person_chose():
    # 定数で見るだけだと、字を誰かが書き換えても通ってしまう。本人が採った文（2026-11-06・本人のカード「直しで出た新しい文 5 つ」の 3）を一字ずつ見る
    # 札の字は「のこす」（本人の答え 11-08「B。」・統括の決め (a)。前は本人が採った「全部できた」）。上に本人の字（naoru.ROUTE_ASK）
    assert tsukuru.DONE_LABEL == "のこす", tsukuru.DONE_LABEL
    assert tsukuru.DONE_NOTE == "組み上がった事を残しました。動かしてみて、ここで記録を残します。", tsukuru.DONE_NOTE
    last = get(f"/toy/{G}/tsukuru?h={GS}&n={total}")[1]
    assert tile(last, "done")[0] == "のこす", "頁の札が のこす でない"
    assert naoru.ROUTE_ASK == "どう工夫したかあとで教えてください。写真や動画でもいいです。", naoru.ROUTE_ASK
    # 本人の字は のこす の札の中の上の段（統括の決め 11-08「札の中の上の段に小さく・読み上げの順は 本人の字 → のこす」）
    btn = re.search(r'<button name="event" value="done"[^>]*>(.*?)</button>', last, re.S).group(1)
    assert btn == f'<span class="ask">{naoru.ROUTE_ASK}</span><span class="nm">のこす</span>', btn
    assert ".tiles .go .ask{display:block;font-size:13px" in last, "本人の字が小さい字でない（札の名が一番大きく読めない）"
    assert "ask-nokosu" not in last, "札の外の前の字の置き場が残っている"


def no_praise():
    for word in ("おめでとう", "すごい", "よくでき", "合格", "成功", "正解", "点数", "順位"):
        assert word not in tsukuru.DONE_LABEL + tsukuru.DONE_NOTE, word


fails = []
for check in (big_tile_on_the_last_step, not_shown_midway, midway_leaves_nothing, road_to_the_record, passes_which_sheet,
              who_is_kept_so_nobody_counts_as_quit, js_takes_the_same_road, hidden_tile_stays_hidden_on_narrow_screens, back_is_not_shown_on_the_first_step, one_step_when_there_is_no_text, words_are_the_ones_the_person_chose, no_praise):
    try:
        check()
    except Exception as e:  # 定数が無い直す前も、ほかの確かめを止めずに名前で出す
        fails.append(f"{check.__name__}: {type(e).__name__}: {e}")
assert not fails, "\n" + "\n".join(fails)
print("ok: 作りながら見るの最後の手順")
