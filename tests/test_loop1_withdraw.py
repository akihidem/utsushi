"""ループ1（Issue #335）: 記録を取り下げたら、その人が話した考えから作った案の字も一緒に消える。人の言葉を、取り下げた記録の外に残さないため（#279 と同じ線）。

見る線:
- 結んだ考えから作った案も、その案の紙で試した記録も、取り下げると words の記録・OWN-n・刷った紙・話した字が消える。
- 消えた番号を使い回さない。ほかの人の案と、書いて立てた仮説は消さない。
- 別の記録がまだその案を使っている間は消さない（試した記録が指す先を失わない）。そちらも取り下げると消える。
- 写真と動画だけの取り下げでは消さない。途中で落ちた後の回し直しでも通る。
"""
import json
import os
import pathlib
import tempfile

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tmp, "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import words  # noqa: E402
from omochae import hypotheses, records, talk_log  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
SOURCE = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
WHO, OTHER = "abcdefgh12", "zyxwvuts98"


def made(text, who=WHO, hid=None):
    """考えを残し、案を作り、採って紙を刷る。Returns (words の記録, OWN の記録)。"""
    talk_log.add(G, "think", text, hypothesis_id=hid, who=who)
    talk, name = words.latest_think(G, who)
    w, fs = words.request_think(SOURCE, talk, name, "案", "根拠")
    assert w and not fs, fs
    assert not words.fill_think(w["id"], words.think_result(w["base_params"], {"push_part": "stick", "pusher_height": 84}), "作る側")[1]
    own, fs = words.adopt_words(w["id"], "本人")
    assert own and not fs, fs
    d = hypotheses.play_dir(G)
    d.mkdir(parents=True, exist_ok=True)
    assert hypotheses.print_own(G, own["id"], str(d / f"{own['id']}_v1")) == 0
    return w, own


def record(hid, who=WHO):
    rid, fs = records.add({"source_id": G, "hypothesis_id": hid, "sheet_version": 1, "result": "わからない"})
    assert rid and not fs, fs
    if who:
        talk_log.bind(G, hid, 1, who, rid)
    return rid


def everywhere(text):
    """置き場の JSON のどれかに、その字があるか（刷った紙は printed で別に見る）。"""
    return [str(p.relative_to(tmp)) for p in pathlib.Path(tmp).rglob("*.json") if text in p.read_text(encoding="utf-8")]


def printed(oid):
    return sorted(p.name for p in hypotheses.play_dir(G).glob(f"{oid}_v*"))


# ── 結んだ考えから作った案 ──
SAID = "割り箸の柄で押したら大きく開くと思う"
w, own = made(SAID)
assert printed(own["id"]), "刷ってある"
rid = record("H-A")
assert everywhere(SAID), "取り下げる前は残っている"
gone, fs = records.withdraw(rid)
assert not fs, fs
assert everywhere(SAID) == [], f"話した字がどこにも残らない: {everywhere(SAID)}"
assert own["id"] not in {h["id"] for h in hypotheses.own_hypotheses(G)}, "OWN-n も消える"
assert printed(own["id"]) == [], "刷った紙も消える（字が刷られた手順の紙を含む）"
assert words.by_token(G, w["token"]) is None, "本人の印からも開かない"
assert any(own["id"] in g for g in gone) and any(w["id"].replace("W-", "words-") in g for g in gone), gone
# 消えた番号を使い回さない（古いリンクが別の人の紙を開かないように）
w2, own2 = made("柄を長くしたい", who=OTHER)
assert own2["id"] != own["id"], own2["id"]

# ── ほかの人の案と、書いて立てた仮説は消さない ──
typed, fs = hypotheses.save_own(G, "書いた案", "書いて立てた動かし方", "右の図")
assert typed and not fs
made("つまみを下に付けたい")
assert records.withdraw(record("H-A"))[1] == []
assert everywhere("つまみを下に付けたい") == []
assert everywhere("柄を長くしたい"), "ほかの人の字は消さない"
assert everywhere("書いて立てた動かし方"), "書いて立てた仮説は消さない"

# ── その案の紙で試した記録を取り下げる（考えが記録に結ばれていなくても） ──
SAID4 = "扇の折りを増やしたい"
_, own4 = made(SAID4, hid="H-C")
talk_log.add(G, "craft", "その紙に付いた工夫", hypothesis_id=own4["id"], sheet_version=1, step=1, who=OTHER)  # ほかの印の字。記録には結ばれない
rid4 = record(own4["id"], who="")  # 印の無い画面の記録。何も結ばれない
assert talk_log.talks(G, record_id=rid4) == [], "この形では考えが記録に結ばれない"
assert records.withdraw(rid4)[1] == []
assert everywhere(SAID4) == [], "その案の紙の記録を取り下げると、元の考えの字も消える"
assert everywhere("その紙に付いた工夫") == [], "消えた紙を指す工夫の字も残さない"
assert printed(own4["id"]) == []
# 同じ印の記録なら、考えはその案の紙の記録に結ばれる（考えはたたき台に付いていても）
SAID4B = "折りを減らしたい"
_, own4b = made(SAID4B, hid="H-C")
rid4b = record(own4b["id"])
assert [t["text"] for t in talk_log.talks(G, record_id=rid4b)] == [SAID4B], "元の考えが結ばれる"
assert records.withdraw(rid4b)[1] == [] and everywhere(SAID4B) == []

# ── 別の記録がまだ使っている間は消さない ──
SAID5 = "柄を太くしたい"
_, own5 = made(SAID5, hid="H-C")
a, b = record(own5["id"]), record(own5["id"])
assert records.withdraw(a)[1] == []
assert everywhere(SAID5) and printed(own5["id"]), "もう 1 件の記録が指す先を失わない"
assert records.withdraw(b)[1] == []
assert everywhere(SAID5) == [] and printed(own5["id"]) == [], "最後の記録を取り下げると消える"

# ── 写真と動画だけの取り下げでは消さない ──
SAID6 = "軸を上にしたい"
_, own6 = made(SAID6)
rid6 = record("H-A")
assert records.withdraw(rid6, media_only=True)[1] == []
assert everywhere(SAID6) and printed(own6["id"]), "写真と動画だけの時は残す"
# 本当に取り下げると消え、もう一度回しても落ちない（途中で落ちた後の回し直し）
assert records.withdraw(rid6)[1] == []
assert everywhere(SAID6) == []
assert records.withdraw(rid6)[1] == []

# ── 頼んだだけ（採る前）の案も消える ──
SAID7 = "筒を短くしたい"
talk_log.add(G, "think", SAID7, who=WHO)
talk, name = words.latest_think(G, WHO)
w7, _ = words.request_think(SOURCE, talk, name, "案", "根拠")
assert records.withdraw(record("H-A"))[1] == []
assert everywhere(SAID7) == [] and words.by_token(G, w7["token"]) is None
print("ok")
