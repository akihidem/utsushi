"""記録の札の「説明」と「字を足す」口は、その記録を残した画面だけに開く（手歩きの確かめ、11-06）。

直す前は、手帖の別の人の画面に前の人の記録の説明の欄が出て、押すと前の人の記録の説明として残り、1 回限りなので本人の欄が閉じた。
合言葉ありの場では、その説明で次の版の欄まで開いた。「工夫した所や、思った事を足す」も全部の記録に出て、別の人の字が前の人の記録に結ばれた。

見る事（合言葉ありの場と、合言葉なしで開いた場の両方）:
- 欄は、記録を残した画面にだけ出る。受け口も印を照らして 403 で断り、何も残さない。
- who は証拠にならない（記録が残ると作り直され、記録にも残さない）。番号は連番なので証拠にならない。
- 同じブラウザで次の記録が残ると、前の記録には書けない（机の端の 1 台を順に使う場）。
- 期限はサーバの時刻で 15 分。作る側の端末から足す道は残る。
"""
import json
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api import ask  # noqa: E402
from omochae import hypotheses, loop, records, talk_log  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
COOKIE = "utsushi_rec"
WHO = "abcdefghij"  # 画面が持つその場限りの印の形
ask._key_present = lambda: False  # 合言葉なしの場は鍵のある所で立たない。鍵のある機械でも同じに動くように


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class Screen:
    """1 つのブラウザ。cookie を自分で持つ（試験の目当てなので、手で見える形にする）。"""

    def __init__(self, base):
        self.base, self.cookies, self.set_cookie = base, {}, []

    def call(self, path, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        headers = {"Origin": self.base}
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if self.cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        req = urllib.request.Request(self.base + path, data=body, headers=headers, method="POST" if body is not None else "GET")
        try:
            r = urllib.request.build_opener(NoRedirect).open(req, timeout=120)
        except urllib.error.HTTPError as e:
            r = e
        self.set_cookie = r.headers.get_all("Set-Cookie") or []
        for line in self.set_cookie:
            name, _, value = line.split(";", 1)[0].partition("=")
            self.cookies[name.strip()] = value.strip()
        return r.getcode(), r.read().decode("utf-8", "replace")

    def forms(self, rid):
        """(玩具の頁の説明の欄, 手帖の説明の欄, 手帖の字を足す口)。"""
        toy, techo = self.call(f"/toy/{G}")[1], self.call(f"/toy/{G}/techo")[1]
        explain = f'action="/record/{rid}/explain'
        return explain in toy, explain in techo, f'name="record" value="{rid}"' in techo

    def explain(self, rid, **more):
        return self.call(f"/record/{rid}/explain", {"text": "折りが固い", "next_idea": "幅を変える", "by": "作った人", **more})[0]

    def keep(self, rid, text, **more):
        return self.call(f"/toy/{G}/talk", {"scene": "keep", "record": rid, "text": text, "json": "1", **more})[0]

    def record(self, **more):
        self.call(f"/toy/{G}/record", {"hypothesis": sheet, "result": "動いた", **more})
        return records.all_records(G)[-1]["id"]


OPEN, SHUT = (True, True, True), (False, False, False)
sheet = hypotheses.sheet_of(G)["id"]

for kw in ({}, {"public_open": True}):
    os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    a, b = Screen(base), Screen(base)
    assert a.call(f"/toy/{G}/print", {"hypothesis": sheet})[0] in (200, 303)

    # 1. 別の人の画面に、前の人の記録の説明の欄と字を足す口が出ない。本人の画面には出る
    first = a.record(who=WHO)
    assert b.forms(first) == SHUT, ("別の人の画面に欄が出ている", kw, b.forms(first))
    assert a.forms(first) == OPEN, ("本人の画面に欄が無い", kw, a.forms(first))

    # 2. 受け口も断る。who を同じにしても、番号を知っていても通らない。断った時は何も残らない
    assert b.explain(first) == 403 and b.explain(first, who=WHO) == 403, kw
    assert loop.explanation(first) is None, "別の人の説明が残った"
    assert b.keep(first, "別の人の字") == 403 and b.keep(first, "別の人の字", who=WHO) == 403, kw
    no_js = b.call(f"/toy/{G}/talk", {"scene": "keep", "record": first, "text": "別の人の字", "who": WHO})
    assert no_js[0] == 403 and "別の人の字" not in no_js[1], kw
    assert talk_log.texts(G, record_id=first) == [], "別の人の字が前の人の記録に結ばれた"
    assert a.forms(first) == OPEN, "別の人が押しても、本人の欄は閉じない"

    # 3. 印の形と置き場。頁から読めない cookie で、ブラウザを閉じれば消える。who は残さない
    line = next(x for x in a.call(f"/toy/{G}/record", {"hypothesis": sheet, "result": "動いた", "who": WHO}) and a.set_cookie if x.startswith(COOKIE))
    assert "HttpOnly" in line and "SameSite=Lax" in line and "Path=/" in line and "Max-Age" not in line and "Expires" not in line, line
    second = records.all_records(G)[-1]["id"]
    token = a.cookies[COOKIE]
    assert len(token) >= 20 and second not in token, a.cookies
    assert token not in a.call(f"/toy/{G}")[1] and token not in a.call(f"/toy/{G}/techo")[1], "印を頁に書かない"
    kept = (records.folder() / f"{second}.json").read_text(encoding="utf-8") + (loop.folder() / f"owner-{second}.json").read_text(encoding="utf-8")
    assert WHO not in kept, "who を残さない"
    assert all("owner" not in k and "token" not in k for k in records.all_records(G)[-1]), "印は記録の中に置かない"

    # 4. 同じブラウザで次の記録が残ると、前の記録には書けない（欄も受け口も）。新しい記録には書ける
    assert a.forms(first) == SHUT, ("次の記録の後も前の記録の欄が出ている", kw)
    assert a.explain(first) == 403 and a.keep(first, "前の記録への字") == 403, kw
    assert loop.explanation(first) is None and talk_log.texts(G, record_id=first) == []
    assert a.forms(second) == OPEN, kw
    # 手帖の口で次の記録を残しても同じ。cookie は 1 つのまま上書きされる
    code, body = a.call(f"/toy/{G}/record-json", {"hypothesis": sheet, "result": "動いた", "who": WHO})
    third = json.loads(body)["id"]
    assert code == 201 and a.cookies[COOKIE] != token and list(a.cookies) == [COOKIE], (code, a.cookies)
    assert a.forms(second) == SHUT and a.explain(second) == 403, kw
    assert a.forms(third) == OPEN, kw
    # 記録が残らなかった時は印を変えない（前の記録に続けて書ける）
    held = a.cookies[COOKIE]
    assert a.call(f"/toy/{G}/record", {"hypothesis": sheet, "result": "無い札"})[0] == 422 and a.set_cookie == [] and a.cookies[COOKIE] == held

    # 5. 本人は書ける。頁の口は 303 で、字を足す口は通常の返事。通らない中身は 422 で、欄に字を戻す
    assert a.keep(third, "本人の工夫") == 200, kw
    assert [t["text"] for t in talk_log.texts(G, record_id=third)] == ["本人の工夫"]
    bad = a.call(f"/record/{third}/explain", {"text": "戻す字", "next_idea": "", "by": "作った人"})
    assert bad[0] == 422 and "戻す字" in bad[1], kw
    assert a.explain(third) == 303 and loop.explanation(third)["text"] == "折りが固い", kw
    assert a.forms(third)[:2] == (False, False), "説明の後は欄が閉じる（今までどおり）"

    # 6. 作り物の印は通らない。形の外の値でも落ちない
    forged = Screen(base)
    fourth = forged.record()
    mine = forged.cookies[COOKIE]
    for value in (a.cookies[COOKIE], fourth, ".", "x", f"../../{mine}", mine[:-1], mine.swapcase(), "é"):
        forged.cookies[COOKIE] = value
        assert forged.explain(fourth) == 403 and forged.forms(fourth) == SHUT, value
    forged.cookies[COOKIE] = mine
    assert forged.forms(fourth) == OPEN

    # 7. 期限はサーバの時刻で数える。cookie が残っていても閉じる。境の少し内は開いている
    path = loop.folder() / f"owner-{fourth}.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    from datetime import datetime, timedelta

    at = datetime.fromisoformat(saved["at"])
    path.write_text(json.dumps({**saved, "at": (at - timedelta(minutes=records.OWNER_MINUTES - 1)).isoformat()}), encoding="utf-8")
    assert forged.forms(fourth) == OPEN, "15 分の内は開く"
    path.write_text(json.dumps({**saved, "at": (at - timedelta(minutes=records.OWNER_MINUTES + 1)).isoformat()}), encoding="utf-8")
    assert forged.forms(fourth) == SHUT and forged.explain(fourth) == 403 and forged.keep(fourth, "遅れた字") == 403, kw
    path.write_text(json.dumps({**saved, "at": "読めない"}), encoding="utf-8")
    assert forged.forms(fourth) == SHUT, "読めない時は閉じる側"

    # 8. 印の無い記録（作る側の端末で残した物、前からある記録）は、どの画面にも開かない。作る側の端末からは足せる
    made, failures = records.add({"source_id": G, "hypothesis_id": sheet, "sheet_version": 1, "result": "動いた"})
    assert made and not failures
    assert a.forms(made) == SHUT and a.explain(made) == 403, kw
    assert loop.save_explanation(made, "作る側", "端末から足した", "次") == []
    # 9. 記録を取り下げると、印も残らない
    gone, failures = records.withdraw(third)
    assert not failures and f"owner-{third}.json" in gone and not (loop.folder() / f"owner-{third}.json").exists(), gone
    # 10. 版の歩みの頁の知見にも、別の人の字は入らない（kaizen_versions.record_words が読む）。本人の字が入る事を対照に見る
    c, d = Screen(base), Screen(base)
    tenth = c.record()
    if kw:
        assert d.call("/loop/ayumi")[0] == 404, "合言葉なしの場には出さない（J-028）"
    else:
        assert d.explain(tenth, text="別の人の説明の印") == 403 and d.keep(tenth, "別の人の字の印") == 403
        assert c.keep(tenth, "本人の字の印") == 200 and c.explain(tenth, text="本人の説明の印") == 303
        assert c.call(f"/record/{tenth}/next", {"interpretation": "折りが固い", "param": "fold_count", "to": "24", "why": "開きやすく", "by": "作る側"})[0] == 303
        ayumi = d.call("/loop/ayumi")[1]
        assert "本人の字の印" in ayumi and "本人の説明の印" in ayumi, "対照: 根拠の記録の字は歩みに出る"
        assert "別の人の説明の印" not in ayumi and "別の人の字の印" not in ayumi, "別の人の字が歩みに入った"
    server.shutdown()

print("ok")
