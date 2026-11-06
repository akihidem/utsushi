"""ループ1（Issue #335）: 記録を取り下げたら、その人が話した考えから作った案の字も一緒に消える。人の言葉を、取り下げた記録の外に残さないため（#279 と同じ線）。

見る線:
- 結んだ考えから作った案も、その案の紙で試した記録も、取り下げると words の記録・OWN-n・刷った紙・話した字が消える。
- 消えた番号を使い回さない。ほかの人の案と、書いて立てた仮説は消さない。
- 別の記録がまだその案を使っている間は消さない（試した記録が指す先を失わない）。そちらも取り下げると消える。
- 写真と動画だけの取り下げでは消さない。途中で落ちた後の回し直しでも通る。
- 根拠に使われた記録でも、話した字（考え・工夫・上げた後）は消せる（--talk-only）。記録の番号と寸法の根拠は残し、版の根拠は数として読める。字の写しと、字が刷られた紙も消える。
- 人が書いた解釈・案・説明・採った人の字は、話した字の引用を含む文を文ごと消す。番号・寸法・版・案の数と、時刻は残す。一部の引用と、字の幅や空白の違う引用も見る。
- 人が書いた字（ひとこと・感想・答え・思いつき・工夫）と手書きの説明の字も空にする。番号・寸法・説明があった印は残し、人の説明が先の床は壊れない。
- 控えの札は、取り下げた記録の番号を含む札だけを見る。名前・番号・印の欄は、短い話が当たっても消さない。Claude が書いた写しの理由も消す。
- Claude が書いた解釈と案（と、そこから作った版と控えの文）は、引用の有無によらず全部消す。要約は機械で見分けられず、要約で話した字が残るため。
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tmp, "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import words  # noqa: E402
from omochae import engine_bundle, gallery, hypotheses, loop, making_log, records, talk_log  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web import techo_site, techo_step, zukan  # noqa: E402
from web.toy import toy_page  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
SOURCE = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
WHO, OTHER = "abcdefgh12", "zyxwvuts98"


class Fake:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        return NS(content=[NS(type="tool_use", name="submit_result", input=self.script.pop(0), id="t")], stop_reason="tool_use", usage=NS(input_tokens=10, output_tokens=5))


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
# 引用を含む文は文ごと消え、一部の引用も消える。人の引用の無い文と、番号・寸法・版・案の数は残る
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
# Claude が書いた案は、引用の無い文も全部消える（要約で残るため）。寸法と番号は残る
assert p8["next_to_try"]["why"] == "" and p8["next_to_try"]["what_to_measure"] == "" and p8["new_hypothesis"]["how_it_moves"] == "" and p8["new_hypothesis"]["name"] == "" and p8["drafted_by"] == "claude", p8
assert p8["id"] == pid8 and p8["record_ids"] == [rid8] and p8["hypothesis_id"] == hypotheses.sheet_of(G)["id"] and p8["decided_at"], "番号と時刻は残る"
extra = json.loads((loop.folder() / f"extra-hypotheses-{G}.json").read_text(encoding="utf-8"))
assert extra[-1]["id"].startswith("H-N") and extra[-1]["how_it_moves"] == "" and extra[-1]["name"] == "" and extra[-1]["proposal"] == pid8, "Claude の案から入った控えも、番号は残り、文は消える"
assert any(e.get("where") == rid8 for e in extra[-1]["evidence"]), "根拠の番号は残る"
assert extra[-1]["adopted_by"] == "採った人", "採った人の名は Claude の字ではないので残る"
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
# ── Claude が書いた文は、引用の有無によらず全部消す。人の字は引用だけを消す ──
SAID12, SUMMARY = "折り目をもう二回なぞったら開きがよくなった", "折り筋を強く付けると広がりやすいようだ"  # 要約: 話した字の引用ではない
assert not records._quotes(SUMMARY, [records._flat(SAID12)]), "見本は比べ方では拾えない要約（下の確かめが効いている事を見る）"
_, own12 = made(SAID12)
rid12 = record(own12["id"])
assert loop.save_explanation(rid12, "試した人", "紙が開いた。" + SAID12[:8], "折りを増やす") == []
hand = {"record_ids": [rid12], "hypothesis_id": sheet, "next_to_try": {"why": "人が書いた理由", "what_to_measure": "角度"}, "references": []}
loop.save_interpretation_draft(rid12, {"observed": [SUMMARY], "causes": [{"text": SUMMARY, "confidence": "低"}]}, {"model": "試験"})
assert loop.confirm_interpretation(rid12, "確認者") == []  # 人が直さずに確定: Claude の字のまま
pid_c, fs = loop.save_proposal({"record_ids": [rid12], "hypothesis_id": sheet, "changes": [{"param": "fold_width", "to": 8.6, "why": SUMMARY, "metric": "", "direction": ""}], "next_to_try": {"why": SUMMARY, "what_to_measure": SUMMARY}, "references": []}, SOURCE, "claude")
assert pid_c and not fs, fs
made_c, fs = loop.adopt(pid_c, "採った人", accept_params=["fold_width"], source=SOURCE)
assert made_c.get("version") and not fs, (made_c, fs)
pid_h, fs = loop.save_proposal(hand, SOURCE, "human")
assert pid_h and not fs, fs
v_path = loop.folder() / f"version-{G}-{sheet}-{made_c['version']}.json"
assert everywhere(SUMMARY), "消す前は要約が残っている"
gone, fs = records.withdraw(rid12, talk_only=True)
assert not fs, fs
assert everywhere(SUMMARY) == [], ("要約も消える", everywhere(SUMMARY))
i12 = loop.interpretation(rid12)
assert i12["content"]["observed"] == [] and i12["content"]["causes"] == [] and i12["confirmed_by"] == "確認者" and i12["confirmed_at"], "Claude の解釈は全部消え、確定の印は残る"
v12 = json.loads(v_path.read_text(encoding="utf-8"))
assert v12["changes"][0]["param"] == "fold_width" and v12["changes"][0]["to"] == 8.6 and v12["changes"][0]["why"] == "" and v12["params"]["fold_width"] == 8.6 and v12["adopted_at"] and v12["adopted_by"] == "採った人", "Claude の案から作った版は、理由の文だけが消える"
assert json.loads((loop.folder() / f"proposal-{pid_h[2:]}.json").read_text(encoding="utf-8"))["next_to_try"]["why"] == "人が書いた理由", "人が書いた案の、引用の無い文は残す"
told = loop.explanation(rid12)
assert told is not None and told["record_id"] == rid12 and told["at"] and (told["text"], told["next_idea"], told["by"]) == ("", "", ""), "手書きの説明は、説明があった印だけを残して字を空にする"
# 人が書き直した解釈は、人の字として読む（引用だけを消す）
_, own13 = made("筒をもっと細くしたら速く開いた")
rid13 = record(own13["id"])
loop.save_interpretation_draft(rid13, {"observed": ["Claude の文"]}, {"model": "試験"})
assert loop.confirm_interpretation(rid13, "確認者", {"human_text": "人が直した解釈", "quote": "筒をもっと細くしたらと話した"}) == []
assert loop.save_explanation(rid13, "筒をもっと細くしたら", "説明", "思いつき") == []
assert loop.save_proposal({"record_ids": [rid13], "hypothesis_id": sheet, "next_to_try": {"why": "x", "what_to_measure": "y"}, "references": []}, SOURCE, "human")[0]
assert records.withdraw(rid13, talk_only=True)[1] == []
c13 = loop.interpretation(rid13)["content"]
assert c13["human_text"] == "人が直した解釈" and c13["quote"] == "", c13
assert loop.explanation(rid13)["by"] == "", "説明を書いた人の欄も、本人が打った字なので空にする"

# ── 時刻の欄を消さない（話した字「11」が時刻に当たる） ──
assert records._without_quotes({"decided_at": "2026-11-05T11:11:00+09:00", "adopted_at": "2026-11-05T11:11", "confirmed_at": "11", "at": "11", "why": "11 番の案"}, [records._flat("11")]) == {"decided_at": "2026-11-05T11:11:00+09:00", "adopted_at": "2026-11-05T11:11", "confirmed_at": "11", "at": "11", "why": ""}
_, own14 = made("11")
rid14 = record(own14["id"])
assert loop.save_explanation(rid14, "試した人", "説明", "思いつき") == []
assert loop.confirm_interpretation(rid14, "確認者", {"human_text": "x"}) == []
pid14, fs = loop.save_proposal({"record_ids": [rid14], "hypothesis_id": sheet, "next_to_try": {"why": "y", "what_to_measure": "z"}, "references": []}, SOURCE, "human")
made14, fs14 = loop.adopt(pid14, "採った人", source=SOURCE)
assert not fs and not fs14, (fs, fs14)
before14 = json.loads((loop.folder() / f"proposal-{pid14[2:]}.json").read_text(encoding="utf-8"))
assert records.withdraw(rid14, talk_only=True)[1] == []
after14 = json.loads((loop.folder() / f"proposal-{pid14[2:]}.json").read_text(encoding="utf-8"))
assert after14["decided_at"] == before14["decided_at"] and after14["drafted_at"] == before14["drafted_at"] and loop.interpretation(rid14)["confirmed_at"], "時刻は残る"

# ── --talk-only の取りこぼしの 2 つ: 結ばれない工夫と、結ばれていない元の考え ──
SAID15, LOOSE15 = "印の無い記録に結ばれない考え", "ほかの印で話した結ばれない工夫"
_, own15 = made(SAID15, hid="H-C")
assert not talk_log.add(G, "craft", LOOSE15, hypothesis_id=own15["id"], sheet_version=1, step=1, who=OTHER)[1]
rid15 = record(own15["id"], who="")  # 印の無い画面の記録: 考えも工夫も結ばれない
assert talk_log.talks(G, record_id=rid15) == [] and everywhere(SAID15) and everywhere(LOOSE15)
assert records.withdraw(rid15, talk_only=True)[1] == []
talk_texts = [json.loads(p.read_text(encoding="utf-8")).get("text") for p in making_log.folder().glob("talk-*.json")]
assert LOOSE15 not in talk_texts, "結ばれない工夫も消える"
assert SAID15 not in talk_texts, "結ばれていない元の考えも消える"

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

# ── 控えの札は、取り下げた記録の番号を含む札だけを見る。関わりの無い札は 1 字も変えない ──
def keep_card(rid_, by, new):
    """案を作って控えへ採る。Returns (案の番号, 札の番号)。"""
    pid, fs = loop.save_proposal({"record_ids": [rid_], "hypothesis_id": sheet, "next_to_try": {"why": "次の試しの理由", "what_to_measure": "開いた角度"}, "references": [],
                                  "new_hypothesis": {"evidence": [], "against": [], "to_measure": "開いた角度", "params": None, **new}}, SOURCE, by)
    assert pid and not fs, fs
    got, fs = loop.adopt(pid, "採った人", accept_new=True, source=SOURCE)
    assert got.get("new_hypothesis") and not fs, (got, fs)
    return pid, got["new_hypothesis"]


def card(cid):
    return next(e for e in json.loads((loop.folder() / f"extra-hypotheses-{G}.json").read_text(encoding="utf-8")) if e["id"] == cid)


def loop_json(name):
    return json.loads((loop.folder() / name).read_text(encoding="utf-8"))


def short_talk(said, who):
    """短い話を、たたき台の記録に結ぶ。説明と解釈の確定まで済ませる（案を作れる形）。"""
    assert not talk_log.add(G, "think", said, hypothesis_id=sheet, who=who)[1]
    rid_ = record(sheet, who=who)
    assert loop.save_explanation(rid_, "試した人", "紙の説明の文", "次の試しの文") == []
    assert loop.confirm_interpretation(rid_, "確認者", {"human_text": "人が書いた解釈"}) == []
    return rid_


def next_value(rid_, param="fold_width"):
    """今の版から変えられる値。版が進んでも試験が止まらないように、床を通る値を探す。"""
    now = {**TEMPLATES[hypotheses.load(G).get("template", "slider_fan")].DEFAULTS, **(loop.version_params(G, sheet, loop.latest_version(G, sheet))[0] or {})}
    for step in (0.1, -0.1, 0.2, -0.2, 0.3, -0.3, 0.5, -0.5, 1, -1):
        to = round(now[param] + step, 2)
        if not loop.check_proposal({"record_ids": [rid_], "hypothesis_id": sheet, "changes": [{"param": param, "to": to, "why": "x"}]}, SOURCE):
            return to, now
    raise AssertionError(f"{param} の変えられる値が無い")


CLAUDE_TRACE = {"model": "claude-試験", "tool_calls": [], "retries": 0, "input_tokens": 1, "output_tokens": 1}
far = short_talk("別の人の考えは紙を厚くしたい", "abcdefgh31")
FAR_HAND, FAR_CLAUDE = "別の人の控えの案は扇が動いた時の止め方を見る事", "別の記録の Claude の案も扇が動いた時の話"
_, far_hand = keep_card(far, "human", {"name": "別の人の案", "how_it_moves": FAR_HAND})
_, far_claude = keep_card(far, "claude", {"name": "別の記録の Claude の案", "how_it_moves": FAR_CLAUDE})
near = short_talk("動いた", "abcdefgh32")
_, near_hand = keep_card(near, "human", {"name": "人の案の名前", "how_it_moves": "人の案は重りを足す事", "against": ["扇が動いた時は別の見方"]})
_, near_claude = keep_card(near, "claude", {"name": "Claude の案の名前", "how_it_moves": "Claude の案は重りを足す事"})
before_far = card(far_hand), card(far_claude)
assert records.withdraw(near, talk_only=True)[1] == []
assert (card(far_hand), card(far_claude)) == before_far, "番号を含まない札は、人の札も Claude の札も 1 字も変えない"
hand_left, claude_left = card(near_hand), card(near_claude)
assert hand_left["how_it_moves"] == "人の案は重りを足す事" and hand_left["name"] == "人の案の名前" and hand_left["against"] == [], "人の札は引用だけを消す"
assert claude_left["how_it_moves"] == "" and claude_left["name"] == "" and claude_left["to_measure"] == "", "Claude の札は全部消す"
assert any(e.get("where") == near for e in claude_left["evidence"]) and claude_left["adopted_by"] == "採った人", "番号と採った人の名は残す"

# ── 短い話が、名前・番号・印の欄に当たっても消さない ──
for said, who in (("作る人", "abcdefgh33"), ("00", "abcdefgh34"), ("claudeに聞いたら折り方が分かった", "abcdefgh35")):
    rid_, _ = records.add({"source_id": G, "hypothesis_id": sheet, "sheet_version": 1, "result": "わからない"})
    assert not talk_log.add(G, "think", said, hypothesis_id=sheet, who=who)[1]
    talk_log.bind(G, sheet, 1, who, rid_)
    assert loop.save_explanation(rid_, "試した人", "説明の文", "次の文") == []
    loop.save_interpretation_draft(rid_, {"observed": ["読みの文"]}, CLAUDE_TRACE)
    assert loop.confirm_interpretation(rid_, "作る人") == []
    to_, _ = next_value(rid_)
    pid_, fs = loop.save_proposal({"record_ids": [rid_], "hypothesis_id": sheet, "changes": [{"param": "fold_width", "to": to_, "why": "案の理由の文", "metric": "", "direction": ""}],
                                   "next_to_try": {"why": "x", "what_to_measure": "y"}, "references": [], "trace": CLAUDE_TRACE}, SOURCE, "claude")
    assert pid_ and not fs, fs
    got, fs = loop.adopt(pid_, "作る人", accept_params=["fold_width"], source=SOURCE)
    assert got.get("version") and not fs, (got, fs)
    _, cid_ = keep_card(rid_, "human", {"name": "番号の欄の案", "how_it_moves": "番号の欄の案の動き方"})
    assert records.withdraw(rid_, talk_only=True)[1] == []
    i_, p_, v_ = loop.interpretation(rid_), loop_json(f"proposal-{pid_[2:]}.json"), loop_json(f"version-{G}-{sheet}-{got['version']}.json")
    assert i_["confirmed_by"] == "作る人" and i_["drafted_by"] == "claude" and i_["trace"] == CLAUDE_TRACE, (said, i_)
    assert p_["drafted_by"] == "claude" and p_["decided_by"] == "作る人" and p_["trace"] == CLAUDE_TRACE, (said, p_)
    assert v_["adopted_by"] == "作る人" and v_["changes"][0]["why"] == "" and v_["changes"][0]["to"] == to_, (said, v_)
    assert card(cid_)["adopted_by"] == "採った人" and any(e.get("where") == rid_ for e in card(cid_)["evidence"]), (said, card(cid_))
# 字の値の寸法（push_part の stick）と、札の番号と、確かさの札も文でない。番号を含む長い文は文として読む
keep_shape = records._without_quotes({"changes": [{"param": "push_part", "to": "stick", "from": "stick", "why": "stick の話"}], "accepted": {"new_hypothesis": "H-N1"}, "accepted_params": ["stick"],
                                      "evidence": [{"kind": "record", "where": "R-0012", "what": "00 の話", "certainty": "00"}], "where": "00 の棚"}, [records._flat("stick"), records._flat("00"), records._flat("H-N1")])
assert keep_shape == {"changes": [{"param": "push_part", "to": "stick", "from": "stick", "why": ""}], "accepted": {"new_hypothesis": "H-N1"}, "accepted_params": ["stick"],
                      "evidence": [{"kind": "record", "where": "R-0012", "what": "", "certainty": "00"}], "where": ""}, keep_shape

# ── 人の案からの版は消さない。Claude の案を版にした時の案の字（new_case）は消す ──
said16 = short_talk("柄の根元をもっと強く折りたい", "abcdefgh36")
to16, now16 = next_value(said16)
pid_h16, fs = loop.save_proposal({"record_ids": [said16], "hypothesis_id": sheet, "changes": [{"param": "fold_width", "to": to16, "why": "人が書いた版の理由", "metric": "", "direction": ""}],
                                  "next_to_try": {"why": "x", "what_to_measure": "y"}, "references": []}, SOURCE, "human")
assert pid_h16 and not fs, fs
got_h16, fs = loop.adopt(pid_h16, "採った人", accept_params=["fold_width"], source=SOURCE)
assert got_h16.get("version") and not fs, (got_h16, fs)
to16b, now16 = next_value(said16)
pid_c16, fs = loop.save_proposal({"record_ids": [said16], "hypothesis_id": sheet, "next_to_try": {"why": "x", "what_to_measure": "y"}, "references": [],
                                  "new_hypothesis": {"name": "版にした案の名前", "how_it_moves": "版にした案の動き方", "evidence": [], "against": [], "to_measure": "角度", "params": {**now16, "fold_width": to16b}}}, SOURCE, "claude")
assert pid_c16 and not fs, fs
got_c16, fs = loop.adopt(pid_c16, "採った人", accept_new=True, source=SOURCE)
assert got_c16.get("new_hypothesis_as_version") and not fs, (got_c16, fs)
assert records.withdraw(said16, talk_only=True)[1] == []
v_h16, v_c16 = loop_json(f"version-{G}-{sheet}-{got_h16['version']}.json"), loop_json(f"version-{G}-{sheet}-{got_c16['version']}.json")
assert v_h16["changes"][0]["why"] == "人が書いた版の理由", "人の案からの版の理由は消さない"
assert v_c16["new_case"] == {"name": "", "how_it_moves": ""} and v_c16["params"]["fold_width"] == to16b, "Claude の案を版にした時の案の字は消し、寸法は残す"

# ── Claude が書いた写しの理由は、引用の有無によらず消す（考えは Claude の字でない。not_fit と filled_in の why は Claude の字）。作る側の理由は引用だけ ──
SAY17, PARA17 = "箱の形に組み替えて中で歯車を回したい", "内部に回転機構を持つ立方体は今の紙の形では扱えない"
assert not records._quotes(PARA17, [records._flat(SAY17)]), "見本は比べ方では拾えない言い換え"
who17 = "abcdefgh37"
assert not talk_log.add(G, "think", SAY17, hypothesis_id=sheet, who=who17)[1]
talk17, name17 = words.latest_think(G, who17)
w17, fs = words.request_think(SOURCE, talk17, name17, "案", "根拠", client=Fake([{"fits": False, "params": {}, "from_words": [], "filled_in": [], "not_fit": [PARA17]}]), use_claude=True)
assert w17 and not fs and w17["trace"]["model"] and "filled_by" not in w17, (w17, fs)
rid17 = record(sheet, who=who17)
assert everywhere(PARA17), "消す前は言い換えがある"
assert records.withdraw(rid17, talk_only=True)[1] == []
left17 = loop_json(f"words-{w17['id'][2:]}.json")
assert everywhere(PARA17) == [] and left17["result"]["not_fit"] == [] and left17["trace"] == w17["trace"], left17
# 紙にできる案の補った理由も同じ。寸法と、寸法の名前は残す
SAY18, WHY18 = "耳をもっと長くしてゆらゆらさせたい", "揺れを大きくするための値として軸の高さも少し上げた"
w18, own18 = made(SAY18, who="abcdefgh38")
path18 = loop.folder() / f"words-{w18['id'][2:]}.json"
now18 = json.loads(path18.read_text(encoding="utf-8"))
kept18 = now18["result"]["filled_in"][0]["param"]
assert now18["filled_by"] and now18["result"]["filled_in"][0]["why"] == words.KEPT_AS_IS
rid18 = record(own18["id"], who="abcdefgh38")
assert records.withdraw(rid18, talk_only=True)[1] == []
assert json.loads(path18.read_text(encoding="utf-8"))["result"]["filled_in"][0]["why"] == words.KEPT_AS_IS, "作る側が書いた理由は、引用でなければ残す"
SAY19 = "耳をもっと長くしてゆらゆらさせたい二回目"
w19, own19 = made(SAY19, who="abcdefgh39")
path19 = loop.folder() / f"words-{w19['id'][2:]}.json"
now19 = json.loads(path19.read_text(encoding="utf-8"))
wrote19 = {k: v for k, v in now19.items() if k not in ("filled_by", "filled_at")}
wrote19["result"] = {**now19["result"], "filled_in": [{**f, "why": WHY18} for f in now19["result"]["filled_in"]]}
loop._write(path19, {**wrote19, "trace": CLAUDE_TRACE})
rid19 = record(own19["id"], who="abcdefgh39")
assert everywhere(WHY18)
assert records.withdraw(rid19, talk_only=True)[1] == []
left19 = json.loads(path19.read_text(encoding="utf-8"))
assert everywhere(WHY18) == [] and [f["param"] for f in left19["result"]["filled_in"]] == [f["param"] for f in now19["result"]["filled_in"]] and left19["result"]["params"] == now19["result"]["params"], left19

# ── 人が書いた字も空にする（本人の決めた説明文「このサイトの中からは消えます」を本当にする）。番号・寸法・説明があった印は残す ──
NOTE20, FEEL20, FIRST20, STUCK20, IF20, IDEA20 = "ひとことの字はここに残るか", "作ってみた感想の字は楽しかった", "最初に動いた所は持ち手だった", "引っかかった所は軸の穴だった", "変えると違いが出そうなのは糊の量", "思いついたのは紙を二重にする事"
PART20, CHANGE20, OUT20 = "外筒の部品の名前", "太く巻き直した事", "内筒が入りやすくなった"
TOLD20, IDEA_TOLD20, NAME20 = "人が手で書いた説明は筒が短かったという事", "次は人が手で書いた筒を長くする事", "書いた人の名前の字"
rid20, fs = records.add({"source_id": G, "hypothesis_id": sheet, "sheet_version": 1, "result": "わからない", "opened_deg": 40, "minutes_to_try": 12, "note": NOTE20, "impression": FEEL20,
                         "answers": {"first_moved": FIRST20, "stuck": STUCK20, "what_if": IF20}, "ideas": [IDEA20], "fixes": [{"part": PART20, "change": CHANGE20, "outcome": OUT20}]})
assert rid20 and not fs, fs
assert loop.save_explanation(rid20, NAME20, TOLD20, IDEA_TOLD20) == []
WRITTEN20 = (NOTE20, FEEL20, FIRST20, STUCK20, IF20, IDEA20, PART20, CHANGE20, OUT20, TOLD20, IDEA_TOLD20)
# 画面の「次の版」の欄は説明の字が初めから入るので、説明のままの解釈は引用として消える。Claude の読みの見出しも、中身が無ければ出さない
HEAD20 = "Claude の読み（案）"
loop.save_interpretation_draft(rid20, {"observed": ["Claude が書いた読みの文"], "causes": [{"text": "Claude が書いた原因の文", "confidence": "低"}], "unknown": ["Claude が書いた分からない事"]}, CLAUDE_TRACE)
assert loop.confirm_interpretation(rid20, "確認者") == []
to20, _ = next_value(rid20)
pid20, fs = loop.save_proposal({"record_ids": [rid20], "hypothesis_id": sheet, "changes": [{"param": "fold_width", "to": to20, "why": f"「{NOTE20}」と書いてあったから", "metric": "", "direction": ""}],
                                "next_to_try": {"why": "人が書いた次の理由", "what_to_measure": "角度"}, "references": []}, SOURCE, "human")
assert pid20 and not fs, fs
pid20b, fs = loop.save_proposal({"record_ids": [rid20], "hypothesis_id": sheet, "next_to_try": {"why": TOLD20, "what_to_measure": IDEA_TOLD20}, "references": []}, SOURCE, "human")
assert pid20b and not fs, fs
# 手帖の記録の札（説明と Claude の読み）は、作り直した手帖では記録の頁にある（#87）
pages20 = lambda: {"玩具の頁": toy_page(G), "手帖": techo_site.records_page(G), "ギャラリー": gallery.build()}
assert all(x in pages20()["玩具の頁"] for x in (NOTE20, FEEL20, FIRST20, TOLD20, IDEA_TOLD20, HEAD20)), "消す前は頁に字がある（下の確かめが効いている事を見る）"
assert TOLD20 in pages20()["手帖"] and HEAD20 in pages20()["手帖"] and TOLD20 in pages20()["ギャラリー"] and NAME20 in pages20()["ギャラリー"]
heads20 = {k: v.count(HEAD20) for k, v in pages20().items()}
LEFT20 = "説明を残しました。"
open20 = lambda: (toy_page(G, photos=False).count(LEFT20), techo_site.records_page(G, uploads=False).count(LEFT20))
open_before20 = open20()
rec20 = json.loads((records.folder() / f"{rid20}.json").read_text(encoding="utf-8"))
assert records.withdraw(rid20, talk_only=True)[1] == []
for text in (*WRITTEN20, NAME20):
    assert everywhere(text) == [], (text, everywhere(text))
for name, html in pages20().items():
    assert not any(x in html for x in (*WRITTEN20, NAME20)), name
    assert not any(x in html for x in ("<p>説明: </p>", "<p>次の思いつき: </p>", "次の思いつき: </p>", "<b>説明</b>（）", "<p></p>", f"{HEAD20}</p><ul></ul>", "工夫:  /  / ")), (name, "空の欄を並べない")
    assert rid20 in html or name == "手帖", name
assert toy_page(G).count(HEAD20) == heads20["玩具の頁"] - 1 and techo_site.records_page(G).count(HEAD20) == heads20["手帖"] - 1, "中身の無い読みの見出しは出さない"
assert open20() == (open_before20[0] - 1, open_before20[1] - 1), "合言葉なしの場でも、字が消えた説明を残したとは言わない"
left20 = json.loads((records.folder() / f"{rid20}.json").read_text(encoding="utf-8"))
assert left20 == {**rec20, "note": "", "impression": "", "answers": {}, "ideas": [], "fixes": []}, "番号・結果・寸法の欄は 1 つも変わらない"
told20 = loop.explanation(rid20)
assert told20 is not None and told20["record_id"] == rid20 and told20["at"] and (told20["text"], told20["next_idea"], told20["by"]) == ("", "", ""), "説明があった印は残し、中身の字と、本人が打った名前は空にする"
p20 = loop_json(f"proposal-{pid20[2:]}.json")
assert p20["changes"][0]["why"] == "" and p20["changes"][0]["to"] == to20 and p20["next_to_try"]["why"] == "人が書いた次の理由", "書いた字の引用も、話した字と同じに文ごと消す"
assert loop_json(f"proposal-{pid20b[2:]}.json")["next_to_try"] == {"why": "", "what_to_measure": ""}, "説明の字をそのまま写した人の文も消す"
# 人の説明が先の床は壊れない: 説明があった印で、次の案と次の版へ進める。束と材料も読める
assert not loop.check_proposal({"record_ids": [rid20], "hypothesis_id": sheet, "changes": [{"param": "fold_width", "to": to20, "why": "x"}]}, SOURCE), "説明があった印で床を通る"
v20, fs = loop.next_version(rid20, "採った人", {"human_text": "人が書いた解釈"}, {"param": "fold_width", "to": to20, "why": "人が書いた次の版の理由"}, SOURCE, d)
assert v20 and not fs, fs
assert loop.material(rid20)["explanation"]["text"] == "" and rid20 in loop.material_text(rid20)
bundle20 = json.dumps(engine_bundle.build(), ensure_ascii=False)
assert not any(x in bundle20 for x in WRITTEN20)
# 回し直しても何も変わらない。そのままの取り下げは今までどおり断る
snap20 = {p: p.read_bytes() for p in pathlib.Path(tmp).rglob("*.json") if p.name != "api-usage.jsonl"}
assert records.withdraw(rid20, talk_only=True) == ([], [])
assert {p: p.read_bytes() for p in snap20} == snap20
assert records.withdraw(rid20)[1][0].floor == "F4.evidence"
# 説明がまだ無い記録は、今までどおり床で止まる（印を説明があった事と読み違えない）
rid21, _ = records.add({"source_id": G, "hypothesis_id": sheet, "sheet_version": 1, "result": "わからない", "note": "説明の無い記録のひとこと"})
assert records.withdraw(rid21, talk_only=True)[1] == [] and everywhere("説明の無い記録のひとこと") == []
assert loop.explanation(rid21) is None and any(f.floor == "F9.human" for f in loop.check_proposal({"record_ids": [rid21], "hypothesis_id": sheet, "changes": [{"param": "fold_width", "to": to20, "why": "x"}]}, SOURCE)), "説明の印を作らない"
# 字の無い記録の取り下げは何も消さない。Claude の文も、その人の字が無いので消さない
rid22, _ = records.add({"source_id": G, "hypothesis_id": sheet, "sheet_version": 1, "result": "わからない"})
loop.save_interpretation_draft(rid22, {"observed": ["字の無い記録の Claude の読みの文"]}, CLAUDE_TRACE)
assert records.withdraw(rid22, talk_only=True) == ([], []) and everywhere("字の無い記録の Claude の読みの文")
# 「わからない」は欄が勧める字で、その人の言葉ではない。これだけの説明でも Claude の文は消え、人の文は引用と読まない
rid23, _ = records.add({"source_id": G, "hypothesis_id": sheet, "sheet_version": 1, "result": "わからない"})
assert loop.save_explanation(rid23, "試した人", records.UNSURE, records.UNSURE) == []
loop.save_interpretation_draft(rid23, {"observed": ["わからない時の Claude の読みの文"]}, CLAUDE_TRACE)
assert loop.confirm_interpretation(rid23, "確認者") == []
to23, _ = next_value(rid23)
pid23, fs = loop.save_proposal({"record_ids": [rid23], "hypothesis_id": sheet, "changes": [{"param": "fold_width", "to": to23, "why": "動くかわからないので測る", "metric": "", "direction": ""}],
                                "next_to_try": {"why": "x", "what_to_measure": "y"}, "references": []}, SOURCE, "human")
assert pid23 and not fs, fs
assert records.withdraw(rid23, talk_only=True)[1] == []
assert everywhere("わからない時の Claude の読みの文") == [], "「わからない」だけの説明でも、Claude の文は消す"
assert loop_json(f"proposal-{pid23[2:]}.json")["changes"][0]["why"] == "動くかわからないので測る", "人の文を消し過ぎない"

# ── 書いた字は 7 字を超える物だけを比べる。短い答えは部品や寸法の名前になりやすいので、記録から空にするだけ（別の人の文を消す誤りの方が重い） ──
rid24, fs = records.add({"source_id": G, "hypothesis_id": sheet, "sheet_version": 1, "result": "わからない", "note": "ひとことは筒を回すと楽しい",
                         "answers": {"first_moved": "外筒の先", "what_if": "折りの幅"}, "ideas": ["糊を減らす"], "fixes": [{"part": "外筒", "change": "長くした", "outcome": records.FIX_BLANK}]})
assert rid24 and not fs, fs
assert loop.save_explanation(rid24, "作った子", "説明は折りが固かった事", "幅を変える") == []
assert loop.confirm_interpretation(rid24, "確認者", {"human_text": "席の人の読みは軸が低かった"}) == []
ADOPT24 = "外筒の長さを伸ばすと開きが安定するから"
to24, _ = next_value(rid24)
pid24, fs = loop.save_proposal({"record_ids": [rid24], "hypothesis_id": sheet, "changes": [{"param": "fold_width", "to": to24, "why": ADOPT24, "metric": "", "direction": ""}],
                                "next_to_try": {"why": "幅を変えると折り目が揃うと考えたから", "what_to_measure": "ひとことは筒を回すと楽しい"}, "references": []}, SOURCE, "human")
assert pid24 and not fs, fs
got24, fs = loop.adopt(pid24, "採った人", accept_params=["fold_width"], source=SOURCE)
assert got24.get("version") and not fs, (got24, fs)
_, card24 = keep_card(rid24, "human", {"name": "採った人の案", "how_it_moves": ADOPT24, "against": [f"{records.FIX_BLANK}所は見ない"]})
assert records.withdraw(rid24, talk_only=True)[1] == []
left24 = json.loads((records.folder() / f"{rid24}.json").read_text(encoding="utf-8"))
assert (left24["note"], left24["answers"], left24["ideas"], left24["fixes"]) == ("", {}, [], []), "短い答えも記録からは空にする"
p24, v24 = loop_json(f"proposal-{pid24[2:]}.json"), loop_json(f"version-{G}-{sheet}-{got24['version']}.json")
assert v24["changes"][0]["why"] == ADOPT24 and p24["changes"][0]["why"] == ADOPT24, "部品の名前（外筒）を含むだけの、採った人の文は消さない"
assert p24["next_to_try"]["why"] == "幅を変えると折り目が揃うと考えたから", "短い思いつき（幅を変える）は比べない（写した文が残る方を取る）"
assert p24["next_to_try"]["what_to_measure"] == "", "7 字を超える書いた字の引用は消す"
assert card(card24)["how_it_moves"] == ADOPT24 and card(card24)["against"] == [f"{records.FIX_BLANK}所は見ない"], "控えの札も同じ"
assert loop.interpretation(rid24)["content"]["human_text"] == "席の人の読みは軸が低かった", "短い字の頭がそろうだけの人の文は消さない"
# 比べる字の決まり: 話した字は全部、書いた字は 7 字を超える物だけ。欄が勧める決まった字（わからない・書かれていない）は、境を変えても比べない
assert records._compared(["動いた", records.UNSURE], ["1234567", "12345678", "外筒"]) == ["12345678", "動いた"]
assert records.WRITTEN_CHARS == 7
records.WRITTEN_CHARS = 0
assert records._compared([], [records.FIX_BLANK, records.UNSURE, "外筒"]) == ["外筒"], "決まった字は、境を変えても比べない"
records.WRITTEN_CHARS = 7

# ── 説明の字が空になった記録では、Claude を呼ばない（J-013: 人の説明が先）。説明があった印で、次の版の床は通る ──
from api import ask, loop_agents, observe  # noqa: E402


class Never(Fake):
    """呼ばれたら、その場で落とす。返事の尽きた所（IndexError）で落ちると、どの床を見落としたかが読めないため。"""

    def create(self, **kw):
        self.calls.append(kw)
        raise AssertionError("人の説明の字が無いのに Claude を呼んだ")


never = Never([])
assert loop_agents.draft_interpretation(rid24, client=never)[1][0].floor == "F9.human" and never.calls == [], "読みを頼まない"
assert loop_agents.draft_proposal(rid24, SOURCE, client=never)[1][0].floor == "F9.human" and never.calls == [], "案も頼まない"
assert observe.observe(rid24, pathlib.Path(tmp) / "無い動画.mp4", never) == (None, "人の説明が先") and never.calls == [], "動画も見せない"
key_present = ask._key_present
ask._key_present = lambda: True
try:
    assert techo_site.ai_offer(rid24) == (False, False, ""), "Claude の釦を出さない"
    assert techo_site.ai_offer(rid20)[0] is False and techo_site.ai_offer(rid8)[0] is False, "書いた字を消した記録も同じ"
    rid25, _ = records.add({"source_id": G, "hypothesis_id": sheet, "sheet_version": 1, "result": "わからない"})
    assert loop.save_explanation(rid25, "試した人", "まだ取り下げていない説明", "次") == [] and techo_site.ai_offer(rid25)[0] is True, "説明の字がある記録では釦を出す"
    card25 = toy_page(G).split(f'id="{rid24}"', 1)[1].split("</article>", 1)[0]
    assert "Claude に聞く" not in card25 and "動画を見てもらう" not in card25, card25[:300]
finally:
    ask._key_present = key_present
assert loop.explained(rid25) and not loop.explained(rid24) and loop.explanation(rid24) is not None
# 古い頁から押されても、受け口が断る（説明を書く欄へ戻す）
import threading  # noqa: E402
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402

from web.play_server import serve  # noqa: E402

server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
for act in ("ai-interpret", "ai-observe"):
    req = urllib.request.Request(f"{base}/record/{rid24}/{act}", data=b"back=techo", method="POST", headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    try:
        code = urllib.request.urlopen(req).status
    except urllib.error.HTTPError as e:
        code = e.code
    assert code == 422 and never.calls == [], (act, code)
server.shutdown()
print("ok")
