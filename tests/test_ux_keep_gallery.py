"""のこした後は持ち寄る駅（ギャラリー）に着き、今残した 1 つが頭に出る（窓口の決定 11-06 夜・案 A。地図 state/journey-map.md の 2 の 4・5 の行）。

見る事:
1. 手帖の作る頁の「のこす」の後（新しい記録・足した記録の両方）は /gallery?msg=…#ageta へ移る。記録の頁へは移らない
2. ギャラリーは、記録を残した画面（記録の鍵）にだけ、返事の文と今残した 1 つを「他の人が作った物」の頭に出す。並びの中には重ねない
3. 今残した 1 つの札から、記録の頁（説明と AI の札。地図の 4）へ、記録の番号で行ける。写真か言葉が無い記録も札にする
4. 別の画面・鍵の無い画面・合言葉なしの場には、今残した 1 つの札を出さない（記録の鍵の線、#441）。合言葉なしの場は、記録を残した同じ画面でも出さない（J-028）
5. 本物を先に、見本は畳む（地図の 5）: 今残した 1 つだけでも見本は「見本」の畳みに入る
"""
import http.cookiejar
import json
import os
import re
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import demo_samples, play_server, techo_step  # noqa: E402

G = "NDL-1187053-R0000005-L"
from omochae import hypotheses  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]

# ---- 1 移る先
moves = re.findall(r"location\.assign\(`([^`]+)`\)", techo_step.SCRIPT)
assert moves and all(m == "/gallery?msg=${encodeURIComponent(done)}#ageta" for m in moves), ("のこした後はギャラリーへ", moves)
assert "techo/kiroku?msg=" not in techo_step.SCRIPT, "記録の頁へは移らない"

server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def screen():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def post(op, path, data):
    q = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    with op.open(q, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def get(op, path):
    with op.open(base + path, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


a, b = screen(), screen()
post(a, f"/toy/{G}/print", {"hypothesis": GS})
other = json.loads(post(b, f"/toy/{G}/record-json", {"hypothesis": GS, "result": "動いた", "sheet_version": "1", "impression": "ほかの人の感想"}))["id"]
mine = json.loads(post(a, f"/toy/{G}/record-json", {"hypothesis": GS, "result": "わからない", "sheet_version": "1"}))["id"]

# ---- 2・3 記録を残した画面
g = get(a, "/gallery?msg=" + urllib.parse.quote("記録を残しました"))
# 他の人が作った物の節の終わりまで（寄せられた声と職人の言葉の節は序の頁へ移したので、次の節は無い。本人のサイト体験レビュー 11-07 の言葉 6）
ageta = g[g.index('id="ageta"'):g.index("</section>", g.index('id="ageta"'))]
assert ageta.index('<p id="msg">記録を残しました</p>') < ageta.index('id="own"'), "返事の文のすぐ後に今残した 1 つ"
own = re.search(r'<div class="item mine" id="own">.*?</div>', ageta, re.S).group(0)
assert f'<a href="/toy/{G}/techo/kiroku#mine">記録の番号 {mine}</a>' in own, "札の記録の番号から記録の頁へ（地図の 4）"
assert "ほかの人の感想" in ageta and ageta.index('id="own"') < ageta.index("ほかの人の感想"), "今残した 1 つが頭、ほかの人の物はその後"
assert ageta.count(f"記録の番号 {mine}") == 1, "並びの中に重ねて出さない"
assert "まだ作った物の記録はありません" not in ageta
if demo_samples.uploads_html():
    assert '<details class="samples-fold"><summary>見本</summary>' in ageta, "本物を先に、見本は畳む（地図の 5）"

# ---- 4 別の画面・鍵の無い画面
head_b = re.search(r'<div class="item mine" id="own">.*?</div>', get(b, "/gallery"), re.S).group(0)
assert f"記録の番号 {other}" in head_b and f"記録の番号 {mine}" not in head_b, "別の画面の頭は、その画面が残した 1 つ（この画面の 1 つは頭に出さない）"
assert 'id="own"' not in get(screen(), "/gallery"), "鍵の無い画面には出さない"
server.shutdown()
opened = play_server.serve(0, public_open=True)
threading.Thread(target=opened.serve_forever, daemon=True).start()
at = f"http://127.0.0.1:{opened.server_address[1]}"
assert 'id="own"' not in urllib.request.urlopen(f"{at}/gallery", timeout=120).read().decode(), "合言葉なしの場には出さない"
# 合言葉なしの場で、記録を残した同じ画面でも出さない（J-028: 公開の場では人の書いた字と記録の番号を出さない）。
# 外の人はトンネルの名前（https）で開くので、その Host と出所で送る。鍵の cookie は Set-Cookie から手で読んで送り返す
# （https の画面は Secure の cookie も送り返す。手元の http で CookieJar を使うと Secure の物を落とし、鍵の無い画面を見るだけになる）
TUNNEL = "made-up-name.trycloudflare" + ".com"  # 作り物の名前。門がトンネルの名前の形を落とすので、字の並びを分けて書く（test_public_open と同じ）
q = urllib.request.Request(f"{at}/toy/{G}/record-json", headers={"Host": TUNNEL, "Origin": f"https://{TUNNEL}"},
                           data=urllib.parse.urlencode({"hypothesis": GS, "result": "動いた", "sheet_version": "1", "impression": "公開の場で書いた感想"}).encode())
with urllib.request.urlopen(q, timeout=120) as r:
    left = json.loads(r.read().decode())["id"]
    rec = [c.split(";")[0] for c in r.headers.get_all("Set-Cookie") or [] if c.startswith("utsushi_rec=")]
assert rec and rec[0] != "utsushi_rec=", ("公開の場でも、記録を残した画面は鍵を持つ（この試験の前提）", rec)
q = urllib.request.Request(f"{at}/gallery?msg=" + urllib.parse.quote("記録を残しました"), headers={"Host": TUNNEL, "Cookie": rec[0]})
with urllib.request.urlopen(q, timeout=120) as r:
    seen = r.read().decode()
assert 'id="ageta"' in seen and 'id="own"' not in seen, "合言葉なしの場では、記録を残した画面にも今残した 1 つを出さない"
assert f"記録の番号 {left}" not in seen and "公開の場で書いた感想" not in seen, "記録の番号と感想の字を出さない"
opened.shutdown()
print("ok のこした後は持ち寄る駅に着き、今残した 1 つが頭に出て、その札から記録の頁へ行ける（地図の 4・5）")
