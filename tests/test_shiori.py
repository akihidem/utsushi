"""手帖の鍵の「しおり」の台帳（omochae.shiori・本人の決め 11-08）の試験。数は設計の 2‴ の 6・7 と別の目の推しのとおりに固める。

見る事:
1. 決まった番地が無い・https でない・替わる番地（一時のトンネル）の時は、しおりを作らない（NoBase）
2. 印は 22 字のでたらめ。道は <決まった番地>/s/<印>。置き場のどのファイルにも、印そのものと押す順と相手の番地が無い（ハッシュと HMAC だけ）
3. 正しい順で開く・違う順では開かない・順はしおりごとに違いうる・秘密の値が無いと照らせない（別の置き場では unknown）
4. 止め: 同じしおりに 10 分で 5 回まで（6 回目は busy で数えない・10 分たてば戻る）／同じ相手の外れの合計 10 回で使えなくなる／
   別々の相手の外れでは使えなくならない／しおりごとの外れの合計 20 回（本人 11-08「外れ 20 回で止める。」）で止まり、進め役への知らせが 1 つ出る
5. 開いた画面の印（しおりの開く道の設計 7.3・別の目の止め S2）: 当たった時だけ作り、画面の値は「しおりの印.開いた画面の印」。
   しおりの印だけでは開かない・開き直すと前の画面は効かない・とじる・使えなくする・止めるで、すぐ効かなくなる。さわらない 20 分で切れる。
   最後に使った時刻の書き直しは 1 分に 1 回まで。開いていない画面からは記録を足せない
5b. 押した順が数でない・形が違う時は、落とさずに外れとして数える（#611 の別の目の気づき (2)）
6. 取り下げ: 記録を取り下げると、しおりの並びから消える。進め役の道（記録の番号）と印から使えなくでき、使えなくした印は二度と開かない
7. 名前・学校・連絡先の欄が無い
"""
import json
import os
import pathlib
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("OMOCHAE_SHIORI_BASE", None)

from omochae import shiori  # noqa: E402

# ---- 1 番地
for bad in ("", "http://example.org", "https://abc-def.trycloudflare.com", "https://tenmoto:8767", "https://example.org/x"):
    os.environ[shiori.BASE_ENV] = bad
    try:
        shiori.make()
        raise AssertionError(("作ってしまった", bad))
    except shiori.NoBase:
        pass
os.environ[shiori.BASE_ENV] = "https://utsushi.example.org"

# ---- 2 印と置き場
s = shiori.make(records=["R-1001"], now=1000.0)
assert shiori.TOKEN.fullmatch(s["token"]) and s["url"] == "https://utsushi.example.org/s/" + s["token"]
assert len(s["order"]) == 3 and len(set(s["order"])) == 3 and all(0 <= i < 9 for i in s["order"])
blob = "".join(p.read_text(encoding="utf-8", errors="replace") for p in shiori.folder().glob("*.json"))
assert s["token"] not in blob and json.dumps(list(s["order"])) not in blob and "peer-one" not in blob
assert (shiori.folder() / ".secret").stat().st_mode & 0o077 == 0, "秘密の値は持ち主だけが読める"

# ---- 3 照らし
other = tuple(i for i in range(9) if i not in s["order"])[:3]
assert shiori.check(s["token"], other, "peer-one", now=1001) == "wrong"
assert shiori.check(s["token"], s["order"], "peer-one", now=1002) == "ok"
assert shiori.check("x" * 22, s["order"], "peer-one") == "unknown" and shiori.check("bad/../x", s["order"], "p") == "unknown"
assert "peer-one" not in "".join(p.read_text(encoding="utf-8") for p in shiori.folder().glob("*.json")), "相手の番地はハッシュで持つ"
orders = {tuple(shiori.make(now=1.0)["order"]) for _ in range(30)}
assert len(orders) > 1, "順はしおりごとに違いうる"

# ---- 4 止め
t = shiori.make(now=0.0)
wrong = tuple(i for i in range(9) if i not in t["order"])[:3]
assert [shiori.check(t["token"], wrong, "a", now=10 + i) for i in range(5)] == ["wrong"] * 5
assert shiori.check(t["token"], t["order"], "a", now=20) == "busy", "10 分に 5 回まで（止めの間は正しい順でも開かない）"
assert shiori.check(t["token"], t["order"], "a", now=10 + 600) == "ok", "10 分たてば戻る"
u = shiori.make(now=0.0)
wu = tuple(i for i in range(9) if i not in u["order"])[:3]
res = [shiori.check(u["token"], wu, "same", now=1000.0 * k) for k in range(10)]
assert res == ["wrong"] * 10 and shiori.check(u["token"], u["order"], "same", now=20000) == "revoked", "同じ相手の外れ 10 回で使えなくなる"
v = shiori.make(now=0.0)
wv = tuple(i for i in range(9) if i not in v["order"])[:3]
assert shiori.TOTAL_FAILS == 20, "本人 11-08「外れ 20 回で止める。」"
for k in range(shiori.TOTAL_FAILS - 1):
    assert shiori.check(v["token"], wv, f"peer-{k}", now=1000.0 * k) == "wrong"
assert shiori.check(v["token"], v["order"], "owner", now=60000) == "ok", "別々の相手の外れでは使えなくならない"
assert shiori.check(v["token"], wv, "peer-x", now=70000) == "wrong"
assert shiori.check(v["token"], v["order"], "owner", now=80000) == "stopped", "しおりごとの外れ 20 回で止まる"
notices = (shiori.folder() / "notices.jsonl").read_text(encoding="utf-8").strip().splitlines()
assert len(notices) == 1 and "止めた" in notices[0] and v["token"] not in notices[0], "進め役への知らせが 1 つ（印は書かない）"

# ---- 5 開いた画面の印と、さわらない 20 分
import secrets  # noqa: E402

w = shiori.make(records=["R-2001"], now=0.0)
one, two = secrets.token_urlsafe(16), secrets.token_urlsafe(16)
screen = f'{w["token"]}.{one}'
assert not shiori.fresh(screen, now=1) and not shiori.add_record(screen, "R-2002", now=1), "開く前は足せない"
assert shiori.check(w["token"], w["order"], "a", now=100, screen=one) == "ok" and shiori.fresh(screen, now=100 + 1199)
assert not shiori.fresh(w["token"], now=101) and not shiori.fresh(f'{w["token"]}.{two}', now=101), "しおりの印だけ・別の画面の印では開かない"
assert not shiori.fresh(screen, now=100 + 1200), "20 分さわらないと切れる"
stored = json.dumps([json.loads(q.read_text(encoding="utf-8")) for q in shiori.folder().glob("*.json")])
assert one not in stored, "開いた画面の印そのものは台帳に無い（ハッシュだけ）"
# 1 分に 1 回だけ書き直す
assert shiori.check(w["token"], w["order"], "a", now=5000, screen=one) == "ok"
shiori.touch(screen, now=5030)
assert not shiori.fresh(screen, now=5000 + 1200), "1 分たたない touch では書き直さない"
assert shiori.check(w["token"], w["order"], "a", now=9000, screen=one) == "ok"
shiori.touch(screen, now=9061)
assert shiori.fresh(screen, now=9000 + 1250), "1 分を過ぎた touch で数え直す"
assert shiori.add_record(screen, "R-2002", now=9100) and shiori.records_of(screen, now=9100) == ["R-2001", "R-2002"]
# 開き直すと前の画面は効かない（1 つのしおりに開いた画面は 1 つ）
assert shiori.check(w["token"], w["order"], "b", now=9200, screen=two) == "ok"
assert not shiori.fresh(screen, now=9201) and shiori.fresh(f'{w["token"]}.{two}', now=9201)
# とじると、写した値でも開かない
assert shiori.close(f'{w["token"]}.{two}') and not shiori.fresh(f'{w["token"]}.{two}', now=9202) and not shiori.close(f'{w["token"]}.{two}')
assert not shiori.close("bad") and not shiori.close(w["token"])

# ---- 5b 数でない・形の違う順は、落とさずに外れとして数える
z = shiori.make(now=0.0)
for k, bad in enumerate((["a", "b", "c"], [1, 1, 2], [0, 1, 9], [0, 1], "012", None)):
    assert shiori.check(z["token"], bad, "odd", now=1000.0 * k) == "wrong", bad
assert json.loads((shiori.folder() / shiori._name(z["token"])).read_text(encoding="utf-8"))["fails"] == 6, "6 つとも外れとして数えた"
assert shiori.check(z["token"], [str(i) for i in z["order"]], "odd", now=9000.0) == "ok", "数の字で送られた正しい順は開く"

# ---- 6 取り下げと使えなくする
import time  # noqa: E402

x = shiori.make(records=["R-3001", "R-3002"], now=0.0)
xs = secrets.token_urlsafe(16)
assert shiori.check(x["token"], x["order"], "a", now=time.time(), screen=xs) == "ok"
assert shiori.drop_record("R-3001") == 1 and shiori.records_of(f'{x["token"]}.{xs}') == ["R-3002"]
assert shiori.revoke_by_record("R-3002") == 1 and shiori.check(x["token"], x["order"], "a", now=5) == "revoked"
assert not shiori.fresh(f'{x["token"]}.{xs}'), "使えなくすると、開いていた画面もすぐ効かなくなる"
y = shiori.make(now=0.0)
ys = secrets.token_urlsafe(16)
assert shiori.check(y["token"], y["order"], "a", now=time.time(), screen=ys) == "ok" and shiori.fresh(f'{y["token"]}.{ys}')
assert shiori.revoke(y["token"]) and not shiori.revoke(y["token"]) and shiori.check(y["token"], y["order"], "a", now=5) == "revoked"
assert not shiori.fresh(f'{y["token"]}.{ys}')

# ---- 7 名前の欄が無い
for p in shiori.folder().glob("*.json"):
    e = json.loads(p.read_text(encoding="utf-8"))
    assert not ({"name", "school", "email", "phone", "address", "token", "order", "peer"} & set(e)), p.name
    assert e.get("screen") is None or len(e["screen"]) == 64, "開いた画面の印はハッシュだけ"

# 秘密の値の無い別の置き場では照らせない
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
assert shiori.check(s["token"], s["order"], "a") == "unknown"
print("ok しおりの台帳: 決まった番地の無い時は作らない・印と順は残さない・3 つの止め（10 分 5 回・同じ相手 10 回・しおりごと 20 回）・20 分・取り下げと使えなくする")
