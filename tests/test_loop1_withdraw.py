"""ループ1（Issue #335）: 記録を取り下げたら、その人が話した考えから作った案の字も一緒に消える。人の言葉を、取り下げた記録の外に残さないため（#279 と同じ線）。

見る線:
- 結んだ考えから作った案も、その案の紙で試した記録も、取り下げると words の記録・OWN-n・刷った紙・話した字が消える。
- 消えた番号を使い回さない。ほかの人の案と、書いて立てた仮説は消さない。
- 別の記録がまだその案を使っている間は消さない（試した記録が指す先を失わない）。そちらも取り下げると消える。
- 写真と動画だけの取り下げでは消さない。途中で落ちた後の回し直しでも通る。
- 根拠に使われた記録でも、話した字（考え・工夫・上げた後）は消せる（--talk-only）。記録の番号と寸法の根拠は残し、版の根拠は数として読める。字の写しと、字が刷られた紙も消える。
- 解釈と案と版の文に話した字の引用が残ると取り下げにならないので、引用を含む文は文ごと消す。番号・寸法・版・案の数は残す。一部の引用と、字の幅や空白の違う引用も見る。
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tmp, "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import words  # noqa: E402
from omochae import hypotheses, loop, making_log, records, talk_log  # noqa: E402
from web import techo_site, techo_step, zukan  # noqa: E402
from web.toy import toy_page  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
SOURCE = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
WHO, OTHER = "abcdefgh12", "zyxwvuts98"


def made(text, who=WHO, hid=None, not_fit=None):
    """考えを残し、案を作り、採って紙を刷る。Returns (words の記録, OWN の記録)。"""
    talk_log.add(G, "think", text, hypothesis_id=hid, who=who)
    talk, name = words.latest_think(G, who)
    w, fs = words.request_think(SOURCE, talk, name, "案", "根拠")
    assert w and not fs, fs
    assert not words.fill_think(w["id"], words.think_result(w["base_params"], {"push_part": "stick", "pusher_height": 84}, not_fit), "作る側")[1]
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
# ── 根拠に使われた記録でも、話した字は消せる ──
def pdf_text(p):
    return "".join(subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True).stdout.split())


SAID8, CRAFT8, KEEP8 = "割り箸の柄で大きく開くと思う", "柄の先に紙を巻いた", "上げた後に思った事"
w8, own8 = made(SAID8)
assert not talk_log.add(G, "craft", CRAFT8, hypothesis_id=own8["id"], sheet_version=1, step=1, who=WHO)[1]
rid8 = record(own8["id"])
assert not talk_log.add(G, "keep", KEEP8, record_id=rid8, who=WHO)[1]
assert {x["text"] for x in talk_log.kufu(G, rid8)} == {SAID8, CRAFT8, KEEP8}
assert loop.save_explanation(rid8, "試した人", "柄で押すと開いた", "折りを増やす") == []
d = hypotheses.play_dir(G)
# Claude と人の文に、話した字の引用が入った形（全部の引用・一部の引用・字の幅と空白の違う引用）。引用の無い文は残る
PART_CRAFT, PART_KEEP = "柄の先に紙を巻い", "げた後に思った事"  # 話した字の 8 字だけ。全部は写っていない
SAID8_SPACED = SAID8[:4] + " " + SAID8[4:]
reading = {"observed": [f"「{CRAFT8}」と話していた", "紙が開いた"], "causes": [{"text": f"{SAID8_SPACED}と考えた", "confidence": "低"}, {"text": "柄が長い", "confidence": "中"}], "unknown": [f"あ{PART_KEEP}の意味"], "human_text": "説明のとおり"}
version, fs = loop.next_version(rid8, "採った人", reading, {"param": "fold_count", "to": 27, "why": f"「{CRAFT8}」から"}, SOURCE, d)
assert version and not fs, fs
sheet_paper = d / f"{hypotheses.sheet_of(G)['id']}_v{version}.pdf"
assert "".join(CRAFT8.split()) not in pdf_text(sheet_paper) and "".join(CRAFT8.split()) not in pdf_text(d / f"{hypotheses.sheet_of(G)['id']}_v{version}_tejun.pdf"), "版の紙に理由の文は刷られない"
draft = {"record_ids": [rid8], "hypothesis_id": hypotheses.sheet_of(G)["id"], "changes": [{"param": "fold_width", "to": 8.4, "why": f"{PART_CRAFT}て押したから"}],
         "next_to_try": {"why": f"{KEEP8}と言っていた", "what_to_measure": "開いた角度"}, "references": [],
         "new_hypothesis": {"name": "控えの案", "how_it_moves": f"{SAID8}という考え", "evidence": [{"kind": "record", "where": rid8, "what": "試した記録", "certainty": "記録"}], "against": [], "to_measure": "開いた角度", "params": None}}
pid8, fs = loop.save_proposal(draft, SOURCE, "claude")
assert pid8 and not fs, fs
kept_new, fs = loop.adopt(pid8, "採った人", accept_params=[], accept_new=True, source=SOURCE)
assert kept_new.get("new_hypothesis") and not fs, (kept_new, fs)
assert everywhere(f"{PART_CRAFT}て押した") and everywhere(f"あ{PART_KEEP}"), "取り下げる前は引用がある（下の確かめが効いている事を見る）"
assert CRAFT8 not in f"{PART_CRAFT}て押したから" and KEEP8 not in f"あ{PART_KEEP}の意味", "試験の文は一部の引用（全部の引用になっていない）"
# 作る側か Claude が、words の記録の理由の欄に話した字を引いた形。寸法と、変えた寸法の名前は残す
w8_path = loop.folder() / f"words-{w8['id'][2:]}.json"
w8_now = json.loads(w8_path.read_text(encoding="utf-8"))
w8_result = {**w8_now["result"], "filled_in": w8_now["result"]["filled_in"] + [{"param": "tube_side", "why": f"「{SAID8}」から"}], "not_fit": [f"「{SAID8}」の一部は雛形に無い"]}
loop._write(w8_path, {**w8_now, "result": w8_result})
proposals_before = len(list(loop.folder().glob("proposal-*.json")))
sheet = hypotheses.sheet_of(G)["id"]
# そのままの取り下げは今までどおり断り、消せる道を言う。断った時は何も消さない
gone, fs = records.withdraw(rid8)
assert gone == [] and fs[0].floor == "F4.evidence" and "--media-only" in fs[0].message and "--talk-only" in fs[0].message, fs
assert everywhere(SAID8) and everywhere(CRAFT8) and everywhere(KEEP8)
# 写真と動画だけの取り下げでは、話した字は残る
assert records.withdraw(rid8, media_only=True)[1] == [] and everywhere(SAID8) and everywhere(CRAFT8)
tejun = d / f"{own8['id']}_v1_tejun.pdf"
assert "".join(SAID8.split()) in pdf_text(tejun), "消す前は手順の紙に字が刷られている（下の確かめが効いている事を見る）"
# 話した字だけを消す
env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
r = subprocess.run([sys.executable, "-m", "omochae.records", "withdraw", rid8, "--talk-only"], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
assert r.returncode == 0 and "話した字" in r.stdout, r.stdout + r.stderr
for text in (SAID8, CRAFT8, KEEP8):
    assert everywhere(text) == [], (text, everywhere(text))
# 引用を含む文は文ごと消え、一部の引用も消える。引用の無い文と、番号・寸法・版・案の数は残る
for part in (f"{PART_CRAFT}て押した", f"あ{PART_KEEP}", SAID8_SPACED, SAID8[:8]):
    assert everywhere(part) == [], (part, everywhere(part))
w8_left = json.loads(w8_path.read_text(encoding="utf-8"))
assert w8_left["how_it_moves"] == "" and w8_left["result"]["not_fit"] == [] and w8_left["result"]["params"]["push_part"] == "stick" and w8_left["result"]["from_words"] == w8_result["from_words"], w8_left["result"]
assert [f for f in w8_left["result"]["filled_in"] if f["param"] == "tube_side"][0]["why"] == "", "理由の文は消え、寸法の名前は残る"
assert w8_left["base_params"] == w8_now["base_params"] and w8_left["id"] == w8["id"], "元の寸法と番号は残す"
i8 = loop.interpretation(rid8)
assert i8["status"] == "confirmed" and i8["content"]["observed"] == ["紙が開いた"], i8
assert [c["text"] for c in i8["content"]["causes"]] == ["柄が長い"] and i8["content"]["unknown"] == [] and i8["content"]["human_text"] == "説明のとおり", i8
v8 = json.loads((loop.folder() / f"version-{G}-{hypotheses.sheet_of(G)['id']}-{version}.json").read_text(encoding="utf-8"))
assert v8["changes"][0]["param"] == "fold_count" and v8["changes"][0]["to"] == 27 and v8["changes"][0]["why"] == "" and v8["record_ids"] == [rid8] and v8["params"]["fold_count"] == 27, v8
p8 = json.loads((loop.folder() / f"proposal-{pid8[2:]}.json").read_text(encoding="utf-8"))
assert len(list(loop.folder().glob("proposal-*.json"))) == proposals_before and p8["changes"][0]["param"] == "fold_width" and p8["changes"][0]["to"] == 8.4 and p8["changes"][0]["why"] == "", p8
assert p8["next_to_try"]["why"] == "" and p8["next_to_try"]["what_to_measure"] == "開いた角度" and p8["new_hypothesis"]["how_it_moves"] == "" and p8["new_hypothesis"]["name"] == "控えの案", p8
extra = json.loads((loop.folder() / f"extra-hypotheses-{G}.json").read_text(encoding="utf-8"))
assert extra[-1]["id"].startswith("H-N") and extra[-1]["how_it_moves"] == "" and extra[-1]["name"] == "控えの案", "控えも番号と名前は残り、文だけが消える"
left = sorted(p.name for p in d.glob(f"{own8['id']}_v*"))
assert f"{own8['id']}_v1.pdf" in left and f"{own8['id']}_v1_after.pdf" in left and not [n for n in left if "_tejun" in n or "_free" in n], left
for p in d.glob(f"{own8['id']}_v*.pdf"):
    flat = pdf_text(p)
    assert not any("".join(x.split()) in flat for x in (SAID8, CRAFT8, KEEP8)), p.name
# 記録の番号と寸法の根拠は残り、版の根拠は数として読める
assert any(x["id"] == rid8 for x in records.all_records(G)), "記録は残る"
assert rid8 in json.loads((loop.folder() / f"version-{G}-{sheet}-{version}.json").read_text(encoding="utf-8"))["record_ids"], "版の根拠は残る"
assert records.used_by(rid8), "根拠として読める"
own_left = next(x for x in hypotheses.own_hypotheses(G) if x["id"] == own8["id"])
assert own_left["how_it_moves"] == "" and own_left["params"]["push_part"] == "stick" and own_left["name"], "寸法は残り、字だけが消える"
assert own8["id"] in words.spoken_own_ids(G), "話した考えから作った案のままなので、札に出ず、紙は本人の画面の外に開かない"
assert not words.key_open(words.by_token(G, w8["token"])), "鍵も閉じる"
assert talk_log.kufu(G, rid8) == [] and loop.maker_talk(rid8)["items"] == [], "札と輪の材料からも消える"
# 消した後も、記録の札と頁が開く。字は出ない
for html in (toy_page(G), techo_step.page(G, [sheet]), techo_site.records_page(G), json.dumps(zukan.lines_for(G), ensure_ascii=False)):
    assert not any(x in html for x in (SAID8, CRAFT8, KEEP8)), html[:200]
assert rid8 in toy_page(G), "記録の札は残る"
# 話した字だけの時は、写真と動画を消さない（字と写真は別の用事）
photo = records.folder() / "media" / rid8
photo.mkdir(parents=True, exist_ok=True)
(photo / "a.jpg").write_bytes(b"x")
assert records.withdraw(rid8, talk_only=True)[1] == [] and (photo / "a.jpg").exists(), "写真は残る"
(photo / "a.jpg").unlink()
photo.rmdir()
# 回し直しても落ちない。そのままの取り下げは今までどおり断る
assert records.withdraw(rid8, talk_only=True) == ([], [])
assert records.withdraw(rid8)[1][0].floor == "F4.evidence"
# ほかの人の字は消さない（この案の紙に付いた字は消す）
assert everywhere("柄を長くしたい"), "ほかの人の字は残る"
# 引用の見分け方: 話した字が短い時は全部が写っている時だけ。無関係な文は消さない
assert records._quotes("短い考えと書いてある", [records._flat("短い考え")]) and not records._quotes("短い話です", [records._flat("短い考え")])
assert records._quotes("ＡＢＣＤ　ＥＦＧＨと話した", [records._flat("ABCDEFGH")]), "字の幅と空白をそろえて比べる"
assert not records._quotes("紙が開いた", [records._flat("紙")]), "1 字は引用と読まない"
shape = records._without_quotes({"id": "柄の先", "why": "柄の先です", "to": 3, "params": {"push_part": "柄の先"}, "list": ["柄の先です", "別の文"], "causes": [{"text": "柄の先です"}, {"text": "別の文"}]}, [records._flat("柄の先")])
assert shape == {"id": "柄の先", "why": "", "to": 3, "params": {"push_part": "柄の先"}, "list": ["別の文"], "causes": [{"text": "別の文"}]}, shape  # 番号と寸法の欄と数は残し、文だけを消す
# 元の考えのファイルが先に無くなった形（途中で落ちた後の回し直し）でも、words の写しから字を読んで、引用を消す
SAID11 = "途中で落ちた後にも消える考え"
w11, own11 = made(SAID11)
rid11 = record(own11["id"])
assert loop.save_explanation(rid11, "試した人", "説明", "思いつき") == []
assert loop.confirm_interpretation(rid11, "確認者", {"human_text": "説明のとおり"}) == []
pid11, fs = loop.save_proposal({"record_ids": [rid11], "hypothesis_id": hypotheses.sheet_of(G)["id"], "next_to_try": {"why": f"「{SAID11}」から", "what_to_measure": "角度"}, "references": []}, SOURCE, "claude")
assert pid11 and not fs, fs
for p in (making_log.folder()).glob("talk-*.json"):
    if json.loads(p.read_text(encoding="utf-8")).get("text") == SAID11:
        p.unlink()
assert everywhere(SAID11)
assert records.withdraw(rid11, talk_only=True)[1] == [] and everywhere(SAID11) == [], everywhere(SAID11)
# 型紙なしの紙は、紙ごと字が刷られているので消える
SAID9 = "水の重さで開くのかも"
_, own9 = made(SAID9, not_fit=[f"「{SAID9}」は雛形に無い"])
rid9 = record(own9["id"])
assert (d / f"{own9['id']}_v1_free.pdf").exists() and "".join(SAID9.split()) in pdf_text(d / f"{own9['id']}_v1_free.pdf")
assert records.withdraw(rid9, talk_only=True)[1] == []
assert everywhere(SAID9) == [] and not list(d.glob(f"{own9['id']}_v1_free*"))
# 写真と動画と一緒に消せる。記録のほかの欄は残る
media = records.folder() / "media" / rid9
media.mkdir(parents=True, exist_ok=True)
(media / "a.jpg").write_bytes(b"x")
assert records.withdraw(rid9, media_only=True, talk_only=True)[1] == [] and not media.exists() and any(x["id"] == rid9 for x in records.all_records(G))
# 考えが記録に結ばれただけの案（たたき台の記録）でも、字は消える
SAID10 = "たたき台の記録に結ばれる考え"
talk_log.add(G, "think", SAID10, who="abcdefgh77")
talk, name = words.latest_think(G, "abcdefgh77")
words.request_think(SOURCE, talk, name, "案", "根拠")
rid10 = record(sheet, who="abcdefgh77")
assert everywhere(SAID10) and records.withdraw(rid10, talk_only=True)[1] == [] and everywhere(SAID10) == []
print("ok")
