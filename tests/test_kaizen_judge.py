"""審査用の頁「良くするための一周 ♻︎」（前の名は「改善の一周」・/kaizen。本人の言葉 11-07）の試験。本物の API は呼ばない。

見る事:
1. 合言葉なしの公開の場でも開く。学ぶ人の帯と入口からは道を張らない（審査員の入口は README と序の頁）
2. 本当にあった 3 つの一周（サイトの輪・エンジンの輪・山場）が、段ごとの札で上から順に並ぶ
3. 字の元は repo の中の記録と改善の歴史の表だけ（記録の字・表の字がそのまま出る）
4. 誰がしたかを記録のとおりに分ける: Claude の印は「直しを作る」の段だけ。Claude が記録を読む段の札は無い（この 3 つの一周では使っていない）
5. 本人の名は「このサイトを作った人」と言い、「制作者」「本人」の字と型の名は出さない
6. 合体待ちの版は出さない。流れの文に、まだ入っていない PR が出てくる間は文を出さない。入った後は出し、文の中の PR はエンジンの PR へ張る
7. いま回っている一周（本人の指示 11-07「済んだ 3 つの一周に加えて、今朝 Claude が記録 R-0001 を読んで案を出した 1 件（人の確認待ち）も…状態の違いは正直に分かるように」）:
   済んだ一周と札の字と色で分ける。Claude の読みは写しの字のまま。人が確かめる段と次の版は「まだ」。写しに呼び出しの記録（型の名）は無い
8. 題のすぐ下に紹介の大前提の 2 文（本人の言葉 11-07 夜の「入れる」）。S1（何か）と S3（4 日続けて開けた実証）の字のまま、今の LEAD の前
"""
import copy
import json
import os
import re
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import kaizen_judge as k  # noqa: E402
from web.play_server import serve  # noqa: E402


def text(h):
    h = re.sub(r"<style>.*?</style>|<script>.*?</script>", "", h, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).replace("&amp;", "&").replace("&quot;", '"')


# ---- 1 開く・道を張らない
for opened in (False, True):
    server = serve(0, public_open=opened)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    r = urllib.request.urlopen(base + "/kaizen", timeout=120)
    assert r.status == 200, opened
    page = r.read().decode()
    for path in ("/", "/toys"):
        assert "/kaizen" not in urllib.request.urlopen(base + path, timeout=120).read().decode(), ("学ぶ人の入口には道を張らない", path)
    server.shutdown()

# ---- 2 3 つの一周と段の順
hist = json.loads(k.HISTORY.read_text(encoding="utf-8"))
loops = re.findall(r'<section class="sec kz-loop" id="(\w+)">', page)
assert loops == ["site", "engine", "peak"], loops
assert re.findall(r'<section class="sec kz-loop pending" id="(\w+)">', page) == ["pending"], "いま回っている一周は済んだ一周の後に 1 つ"
def steps(sec):
    part = page[page.index(f'id="{sec}"'):]
    part = part[:part.index("</section>")]
    return re.findall(r'<span class="kz-who (\w+)"[^>]*>[^<]*</span><h3>([^<]*)</h3>', part)
assert steps("site") == [("human", "作った記録"), ("human", "人の説明"), ("human", "直しの案"), ("human", "人が決める"), ("claude", "直しを作る"), ("human", "次の版")], steps("site")
assert steps("engine") == [("human", "作った記録"), ("human", "人の説明"), ("engine", "直しの案"), ("human", "人が決める"), ("claude", "直しを作る"), ("human", "次の版")], steps("engine")
assert steps("peak") == [("engine", "作った記録"), ("human", "人が決める"), ("claude", "直しを作る"), ("human", "次の版")], steps("peak")

# ---- 3 字の元は記録と表だけ
t = text(page)
ex = json.loads(k.SITE_EXPL.read_text(encoding="utf-8")); ch = json.loads(k.SITE_CHANGE.read_text(encoding="utf-8"))
assert ex["text"] in t and all(c in t for c in ch["changes"]), "サイトの輪は記録の字のまま"
v4 = k._version(hist, "虎", "tora-v4"); v7 = k._version(hist, "虎", "tora-v7")
assert all(c.replace("制作者", k.MAKER) in t for c in v4["changed"] + v7["changed"]), "エンジンの輪と山場は表の字のまま"
assert "型紙の版 v3 → v4・エンジンの版 2" in t and "型紙の版 v6 → v7・エンジンの版 7" in t
# 1 周目の次の版も「型紙の版」で言う。番号は表の行から（表の出し直し 11-07 11:42 で改善の輪より前の版の行が足された）。行の無い写しでは組の名のまま
if k._version(hist, "御来迎", "goraigo-v8"):
    assert "型紙の版 v7 → v8" in t and "goraigo-v8" not in t, "1 周目もほかの一周と同じ言い方"
else:
    assert "goraigo-v7 → goraigo-v8" in t
row = {"toys": [{"toy": "御来迎", "versions": [{"set": "goraigo-v8", "sheet_version": "8"}]}]}
assert "型紙の版 v7 → v8" in text(k.site_loop(row)) and "goraigo-v7 → goraigo-v8" in text(k.site_loop({})), "表の行があれば番号、無ければ組の名"
assert "エンジンの版" not in text(k.site_loop(row)), "この版にエンジンの版は無いので言わない"
# 同じ頁の中で版の言い方をそろえる（作った記録の「刷った」版も、いま回っている一周も。別の目の気づき 11-07）
if k._version(hist, "御来迎", "goraigo-v7"):
    assert "goraigo-v7" not in t and t.count("刷った型紙の版 v7") == 2, "1 周目といま回っている一周の、刷った版の言い方"
else:
    assert t.count("刷った組 goraigo-v7") == 2
row7 = {"toys": [{"toy": "御来迎", "versions": [{"set": "goraigo-v7", "sheet_version": "7"}, {"set": "goraigo-v8", "sheet_version": "8"}]}]}
assert "刷った型紙の版 v7" in text(k.site_loop(row7)) and "刷った型紙の版 v7" in text(k.pending_loop(row7)) and "刷った組 goraigo-v7" in text(k.pending_loop({}))
assert f'/utsushi/commit/{ch["commit"]}' in page and "/paper-to-toy/pull/106" in page and "/paper-to-toy/pull/138" in page, "直しを作った commit と PR へ行ける"

# ---- 4 済んだ一周の Claude の印は直しを作る段だけ。読む段の札は済んだ一周には無い
claude_steps = [s for sec in loops for s in steps(sec) if s[0] == "claude"]
assert claude_steps and all(h == "直しを作る" for _, h in claude_steps)
assert "読み" not in "".join(h for sec in loops for _, h in steps(sec)) and k.NOT_YET in t

# ---- 7 いま回っている一周: Claude が記録を読んだ案（人の確認待ち）
assert steps("pending") == [("human", "作った記録"), ("human", "人の説明"), ("claude", "Claude の読み"), ("human", "人が確かめる"), ("human", "次の版")], steps("pending")
pend = json.loads(k.PENDING.read_text(encoding="utf-8"))
assert pend["status"] == "pending_human" and pend["drafted_by"] == "claude" and "trace" not in pend, "写しは確認待ちの Claude の案で、呼び出しの記録を持たない"
assert all(c["text"] in t for c in pend["content"]["causes"]), "Claude の読みは写しの字のまま"
assert k.PENDING_STATE in t and k.DONE in t and k.WAIT in t and k.NOT_CHANGED in t, "状態の違いを字で分ける"
assert t.count(k.DONE) == 3 and t.count(k.PENDING_STATE) == 1
assert ".kz-loop.pending{border:2px dashed" in page, "札の色と線でも分ける"
assert "U-32" not in t and "R-0001" in t and "記録の番号 R-0001" in t, "内輪の番号は出さず、記録の番号は字の表の言い方で"

# ---- 5 名の言い方
for word in ("制作者", "本人", "Opus", "opus", "Sonnet", "Haiku", "Fable"):
    assert word not in t, word
assert k.MAKER in t

# ---- 6b 表の spoiler の印の付いた字（動き方を明かす字）は出さない
sp = copy.deepcopy(hist)
for toy in sp["toys"]:
    for v in toy["versions"]:
        if v.get("set") in ("tora-v4", "tora-v7"):
            v["why"] = [dict(w, text="動き方を明かす字のしるし", spoiler=True) for w in v["why"]]
assert "動き方を明かす字のしるし" not in text(k.engine_loop(sp) + k.peak_loop(sp)), "spoiler の印の付いた字は出さない"

# ---- 6 合体待ち
# 写しの表が #139 を合体待ちとしている間は流れの文を出さず、入った後（表の出し直し 11-07 11:42）は出す。どちらの写しでも同じ試験で見る
waiting = any("合体待ち" in str(c.get("status", "")) and f'#{c["pr"]}' in hist.get("story", "") for c in hist.get("engine_changes", []))
assert "合体待ち" not in t, "合体待ちの字は頁に出さない"
assert ("見つかった事から直る" in t) == (not waiting), "まだ入っていない PR が出てくる間だけ、流れの文を出さない"
held = copy.deepcopy(hist)
for toy in held["toys"]:
    for v in toy["versions"]:
        if v.get("set") == "tora-v7":
            v["status"] = "合体待ち"
assert k.peak_loop(held) == "", "合体待ちの版は出さない"
told = copy.deepcopy(hist); told["story"] = "3D で当たりが見つかる → v7 に直す → エンジンが自分で検品する（#139）。見つかった事から直る"
told["engine_changes"] = [dict(c, status="合体待ち（決める人の承認）") if c.get("pr") == 139 else c for c in told["engine_changes"]]
assert "#139" not in k.peak_loop(told) and "見つかった事から直る" not in text(k.peak_loop(told)), "まだ入っていない PR を済んだ事として言わない"
told["engine_changes"] = [{k2: v2 for k2, v2 in c.items() if k2 != "status"} for c in told["engine_changes"]]
done = k.peak_loop(told)
assert "見つかった事から直る" in text(done) and '/paper-to-toy/pull/139">#139</a>' in done, "入った後は文を出し、文の中の PR はエンジンの PR へ張る"
# 確認待ちの写しが確かめられたら（status が替わったら）、いま回っている一周は出さない（済んだ一周として取り直す）
# ---- 8 紹介の大前提（本人の言葉 11-07 夜「入れる」）: 題 → S1 → S3 → LEAD の順。字は本人が確かめたまま
assert k.PREMISE == ("うつしは、学校や博物館などで使える、ワークショップを支えるサービスです。",
                     "11 月 4 日から 7 日まで、4 日続けてワークショップを開けたのは、紙と、はさみと、のりで作れる手軽さがあったからです。")
_top = k.page()
# 題は本人の言葉 11-08「良くするための一周 ♻︎」。♻ の後ろに字の形の印（U+FE0E）を付けて、機械ごとの絵文字の揺れを無くす
assert k.TITLE == "良くするための一周 \u267b\ufe0e" and k.TITLE.endswith("\u267b\ufe0e"), repr(k.TITLE)
_at = [_top.index(x) for x in (f"<h1>{k.TITLE}</h1>", *(f'<p class="lead">{t}</p>' for t in k.PREMISE), f'<p class="lead">{k.LEAD}</p>')]
assert _at == sorted(_at) and _at[1] - _at[0] == len(f"<h1>{k.TITLE}</h1>"), "題のすぐ下に S1・S3、その後に LEAD"
assert all(_top.count(t) == 1 for t in k.PREMISE)

import unittest.mock as mock  # noqa: E402
with mock.patch.object(k, "_load", side_effect=lambda p: (dict(json.loads(k.PENDING.read_text(encoding="utf-8")), status="confirmed") if p == k.PENDING else json.loads(p.read_text(encoding="utf-8")))):
    assert k.pending_loop() == ""
print("ok 審査用の頁: 済んだ 3 つの一周と、Claude が読んだ確認待ちの 1 件を、札の字と色で分けて並べる。字は記録と表と写しだけ。合体待ちは出さない")
