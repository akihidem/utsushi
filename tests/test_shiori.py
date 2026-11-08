"""手帖の鍵の「しおり」の台帳（omochae.shiori・本人の決め 11-08）の試験。数は設計の 2‴ の 6・7 と別の目の推しのとおりに固める。

見る事:
1. 決まった番地が無い・https でない・替わる番地（一時のトンネル）の時は、しおりを作らない（NoBase）
2. 印は 22 字のでたらめ。道は <決まった番地>/s/<印>。置き場のどのファイルにも、印そのものと押す順と相手の番地が無い（ハッシュと HMAC だけ）
3. 正しい順で開く・違う順では開かない・順はしおりごとに違いうる・秘密の値が無いと照らせない（別の置き場では unknown）
4. 止め: 同じしおりに 10 分で 5 回まで（6 回目は busy で数えない・10 分たてば戻る）／同じ相手の外れの合計 10 回で使えなくなる／
   別々の相手の外れでは使えなくならない／しおりごとの外れの合計 20 回（本人 11-08「外れ 20 回で止める。」）で止まり、進め役への知らせが 1 つ出る
5. 開いた後、さわらない 20 分で切れる（fresh）。開いていないしおりには記録を足せない
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

# ---- 5 さわらない 20 分
w = shiori.make(records=["R-2001"], now=0.0)
assert not shiori.fresh(w["token"], now=1) and not shiori.add_record(w["token"], "R-2002"), "開く前は足せない"
assert shiori.check(w["token"], w["order"], "a", now=100) == "ok" and shiori.fresh(w["token"], now=100 + 1199)
assert not shiori.fresh(w["token"], now=100 + 1200), "20 分さわらないと切れる"

# ---- 6 取り下げと使えなくする
x = shiori.make(records=["R-3001", "R-3002"], now=0.0)
assert shiori.drop_record("R-3001") == 1 and shiori.records_of(x["token"]) == ["R-3002"]
assert shiori.revoke_by_record("R-3002") == 1 and shiori.check(x["token"], x["order"], "a", now=5) == "revoked"
y = shiori.make(now=0.0)
assert shiori.revoke(y["token"]) and not shiori.revoke(y["token"]) and shiori.check(y["token"], y["order"], "a", now=5) == "revoked"

# ---- 7 名前の欄が無い
for p in shiori.folder().glob("*.json"):
    e = json.loads(p.read_text(encoding="utf-8"))
    assert not ({"name", "school", "email", "phone", "address", "token", "order", "peer"} & set(e)), p.name

# 秘密の値の無い別の置き場では照らせない
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
assert shiori.check(s["token"], s["order"], "a") == "unknown"
print("ok しおりの台帳: 決まった番地の無い時は作らない・印と順は残さない・3 つの止め（10 分 5 回・同じ相手 10 回・しおりごと 20 回）・20 分・取り下げと使えなくする")
