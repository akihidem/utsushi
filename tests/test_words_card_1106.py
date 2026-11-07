"""読めない字の一覧（本人の確認 11-06「全部案でよい」）のうち、学ぶ人の頁の 1〜8 と英語の序の頁の 16 を、案の字のまま入れた事を見る。

字は本人が確かめた物なので、一字でも変わったら落ちるように、ここに字そのものを書く。前の字が残っていない事も見る。

見る事（番号は一覧の番号）:
1. 入口・一覧・玩具の頁の下の本文の「玩具」を「おもちゃ」に（上の帯と入口の題は前のまま）
2. 玩具の頁の「考えを話す」の箱の見出しを消し、節の見出しだけにする（ほかの箱の見出しは残す）
3. 話す箱の断りの最後の「このサイトは声を受け取りません。」を消す（同じ文は前の断りに 1 回残る）
4. 話す箱で名前のような言葉を断った時の返事
5. 聞く口の断りに、聞いた言葉を AI（Claude）に使う事を足す。Claude を呼ぶ場（鍵がある・合言葉なしの場でない）だけに出す
6. 紙を作った後の返事
7. 作りながら見る頁で「できた」を押した後の返事（一覧の 7 の字は、後から決まった #321 の字と食い違うので、main の #321 の字に譲り、本人に返した。ここでは前の字が戻っていない事だけを見る）
8. ギャラリーと手帖の記録の札で、自分の仮説の紙の名前が空にならない（#427 が決めた字「自分の仮説の紙」）
16. 英語の序の頁の 2 段落目
"""
import http.cookiejar
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
from omochae import hypotheses, records  # noqa: E402
from web import hanasu, tsukuru  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

ask._key_present = lambda: False  # 鍵の有無は試験の中で替える。合言葉なしの場は鍵のある所で立たないので、先に立てる
G = "NDL-1187053-R0000005-L"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a):
        return None


def up(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"


opened, base = up(public_open=True), up()
# 説明は記録を残した画面からだけ書ける（記録の印は cookie）。同じ画面の形にするため、送りは 1 つの cookie の入れ物で行う
opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def get(path, at=None):
    try:
        return urllib.request.urlopen((at or base) + path, timeout=120).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


def post(path, form):
    req = urllib.request.Request(base + path, urllib.parse.urlencode(form).encode(), {"Origin": base, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        r = opener.open(req, timeout=120)
        return r.status, urllib.parse.unquote(r.headers.get("Location", "")), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, urllib.parse.unquote(e.headers.get("Location", "")), e.read().decode()


# 1. 「玩具」を「おもちゃ」に
for look in ("tenji", "zine"):
    entrance = get("/", at=up(look=look))
    assert "83 のおもちゃから、1 つ選ぶ" in entrance and "の玩具から、1 つ選ぶ" not in entrance, look
toys = get("/toys")
# 「83 のおもちゃです。」の段は序の頁（よむ）へ移した（窓口の決定 11-07 の ②）。字はそのまま
yomu = get("/about")
assert "83 のおもちゃです。" in yomu and "83 の玩具。" not in yomu and "83 の玩具。" not in toys
assert "紙 1 枚で作れるおもちゃだけを見る" in toys and "紙 1 枚で作れる玩具だけを見る" not in toys
page = get(f"/toy/{G}")
assert "全部のおもちゃの、作った物を見る" in page and "全部の玩具の、作った物を見る" not in page

# 2. 「考えを話す」の箱の見出しを消す。節の見出しは残し、作りながら見る頁の「工夫を話す」の箱の見出しも残す
think = page.split('id="hanasu"', 1)[1].split("</section>", 1)[0]
assert "<h2>考えを話す</h2>" in think and 'class="hanasu-head"' not in think, "箱の見出し"

# 3. 話す箱の断り
assert hanasu.HOW_BROWSER == "「話す」を押すと、ブラウザ（ネットを見るアプリ）が声を字にします。そのとき、声がブラウザの会社に送られることがあります。"
told = think.split('<p class="meta">', 1)[1].split("</p>", 1)[0]
assert "そのとき、声がブラウザの会社に送られることがあります。</span>" in told and told.count("このサイトは声を受け取りません。") == 1, told

# 4. 名前のような言葉を断った時の返事
code, _, body = post(f"/toy/{G}/talk", {"scene": "think", "hypothesis": hypotheses.sheet_of(G)["id"], "text": "電話は 090-1234-5678 です"})
assert "名前・学校の名前・住所・電話番号・メールのような言葉が入っていたので、残しませんでした。その言葉を消して、もう一度「残す」を押してください。" in body, (code, body[:200])
assert "名前や学校の名前のような言葉" not in body

# 6. 紙を作った後の返事
code, at, _ = post(f"/toy/{G}/print", {"hypothesis": "H-A"})
assert code == 303 and "紙を作りました。下の窓で絵を見てください。印刷する時は、PDF の大きさを 100% にしてください。" in at, at
assert "PDF を 100% で" not in at

# 5. 聞く口の断り（鍵が無い所: 前のまま。鍵がある所: 1 文を足す。合言葉なしの場: 鍵があっても足さない）
KEEP = "聞いた言葉は、名前や連絡先を除いて、案内を良くするために残します。"
AI = "聞いた言葉は、AI（Claude）が答えを考えるのにも使います。"
REST = "声と映像は残しません。"
pages = {"玩具の頁": f"/toy/{G}", "作りながら見る頁": f"/toy/{G}/tsukuru", "手帖": f"/toy/{G}/techo"}
keyless = {k: get(p) for k, p in pages.items()}
assert KEEP + REST + "名前は書かないでください。" in keyless["玩具の頁"]
assert KEEP + REST + "名前は言わないでください。" in keyless["作りながら見る頁"]
assert not [k for k, v in keyless.items() if AI in v], "鍵の無い所では Claude を呼ばない"
assert '<p class="hanasu-head">工夫を話す</p>' in keyless["作りながら見る頁"], "2: ほかの箱の見出しは残す"
ask._key_present = lambda: True
keyed = {k: get(p) for k, p in pages.items()}
assert KEEP + AI + REST + "名前は書かないでください。" in keyed["玩具の頁"]
assert KEEP + AI + REST + "名前は言わないでください。" in keyed["作りながら見る頁"]
assert AI + "名前は言わないでください。" in keyed["手帖"]
assert AI not in get(f"/toy/{G}", at=opened) and AI not in get(f"/toy/{G}/techo", at=opened), "合言葉なしの場は Claude を呼ばない"
# 作りながら見る頁も合言葉なしの場で開ける（紙は上の 6 で刷った）。頁が開いた事を断りの前半で確かめてから、1 文が無い事を見る
opened_tsukuru = get(f"/toy/{G}/tsukuru", at=opened)
assert KEEP + REST in opened_tsukuru and AI not in opened_tsukuru, "合言葉なしの場の作りながら見る頁"
ask._key_present = lambda: False

# 7. 「できた」の後の返事（字は #321 の物。11-06 昼の本人の決定「全部このまま」が一覧の 7 より後なので、そちらを残した）
assert tsukuru.DONE_NOTE.startswith("組み上がった事を残しました。") and "玩具の頁" not in tsukuru.DONE_NOTE
total = len(re.findall(r"<li", get(f"/toy/{G}/tsukuru").split('id="steps"', 1)[1].split("</ol>", 1)[0]))
code, at, _ = post(f"/toy/{G}/step", {"hypothesis": "H-A", "step": str(total), "event": "done", "sheet_version": "1"})
assert code == 303 and tsukuru.DONE_NOTE in at and "玩具の頁で記録を残します" not in at, at

# 6 の続き: 次の版の紙を作った後の返事
code, at, _ = post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた"})
rid = re.search(r"#(R-\d+)", at).group(1)
assert post(f"/record/{rid}/explain", {"text": "説明", "next_idea": "次", "by": "書いた人"})[0] == 303
code, at, _ = post(f"/record/{rid}/next", {"interpretation": "読み", "param": "fold_height", "to": "47.5", "why": "試す", "by": "書いた人"})
assert code == 303 and "版 2 の紙を作りました。印刷する時は、PDF の大きさを 100% にしてください。" in at, at
# 刷り直し（#158）の返事も同じ字。ここだけ別の道（_reprint）で字を持つので、別に見る
code, at, _ = post(f"/toy/{G}/reprint", {"hypothesis": "H-A", "version": "2"})
assert code == 303 and "版 2 の紙を作りました。印刷する時は、PDF の大きさを 100% にしてください。" in at and "PDF を 100% で" not in at, (code, at)

# 8. 自分の仮説の記録の札の紙の名前（ギャラリーと手帖）
own, failures = hypotheses.save_own(G, "前に書いた案", "動かし方", "図の所")
assert not failures
assert hypotheses.print_own(G, own["id"], str(out_dir(G) / f'{own["id"]}_v1')) == 0
oid_rid, failures = records.add({"source_id": G, "hypothesis_id": own["id"], "sheet_version": 1, "result": "動いた", "impression": "前の感想"})
assert oid_rid, failures
gallery = re.sub(r"<[^>]+>", "", get("/gallery"))
assert f"御来迎　自分の仮説の紙　動いた　記録の番号 {oid_rid}" in gallery, "ギャラリーの札"
# 手帖の札は、作り直した手帖では記録の頁にある（#87）
techo = re.sub(r"<[^>]+>", "", get(f"/toy/{G}/techo/kiroku"))
assert f"記録の番号 {oid_rid}　自分の仮説の紙　動いた" in techo, "手帖の札"
assert "御来迎　　動いた" not in gallery and "　　動いた" not in techo

# 16. 英語の序の頁
en = get("/en")
assert "Each toy has one template to start from. It is not the answer." in en
assert "Each idea has its own template, and none of them is the answer." not in en

print("ok: 読めない字の 1〜8 と 16 は、本人が確かめた字のまま頁に出る")
