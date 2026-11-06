"""言葉の口と試した後の紙の試験。Claude の応答は記録した形の偽物で、本物の API は呼ばない。"""
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

from api import words
from omochae import hypotheses
from omochae.instructions import compose_after

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
gs = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
ts = json.loads((ROOT / "data/sources" / f"{T}.json").read_text(encoding="utf-8"))


class Fake:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        return NS(content=[NS(type="tool_use", name="submit_result", input=self.script.pop(0), id="t")], stop_reason="tool_use", usage=NS(input_tokens=10, output_tokens=5))


def floors(fs):
    return {f.floor for f in fs}


ok = {"fits": True, "params": {"push_part": "stick", "hub": "axle", "pusher_height": 84}, "from_words": ["push_part"], "filled_in": [{"param": "hub", "why": "文に無い"}, {"param": "pusher_height", "why": "筒の高さに合わせた"}], "not_fit": []}
# 検査で落とす: 隠れた補い、乗らないのに寸法、理由なしの不適合
assert floors(words.check_result({**ok, "filled_in": []}, gs)) == {"F9.own"}, "隠れた補いを通さない"
assert floors(words.check_result({"fits": False, "params": {"hub": "axle"}, "from_words": [], "filled_in": [], "not_fit": ["x"]}, gs)) == {"F5.range"}
assert floors(words.check_result({"fits": False, "params": {}, "from_words": [], "filled_in": [], "not_fit": []}, gs)) == {"F9.own"}
assert words.check_result(ok, gs) == []
# 個人の情報の形があれば Claude を呼ばない。打った大人が要る
never = Fake([])
assert floors(words.draft_words(gs, "連絡先 a@example.com", "案", "図の棒", "大人", never)[1]) == {"F10.pii"} and never.calls == []
assert floors(words.draft_words(gs, "棒で押す", "案", "図の棒", " ", never)[1]) == {"F9.own"} and never.calls == []
# 人の文はそのまま残り、採るまで一覧に入らない
client = Fake([ok])
wid, fs = words.draft_words(gs, "側面の棒で押し上げる", "棒の案", "図の棒", "大人", client)
assert not fs and hypotheses.own_hypotheses(G) == []
assert "<data>" in client.calls[0]["messages"][0]["content"]
assert floors(words.adopt_words(wid, " ")[1]) == {"F9.human"}
rec, fs = words.adopt_words(wid, "大人")
assert not fs and rec["how_it_moves"] == "側面の棒で押し上げる" and rec["params"] == ok["params"]
assert floors(words.adopt_words(wid, "大人")[1]) == {"F9.human"}, "同じ案を 2 度採らない"
# 乗らない仮説は寸法なしの記録として残る
no = {"fits": False, "params": {}, "from_words": [], "filled_in": [], "not_fit": ["水で動かす機構は雛形に無い"]}
wid2, fs = words.draft_words(gs, "水の重さで開く", "水の案", "図の筒", "大人", Fake([no]))
assert not fs and words.adopt_words(wid2, "大人")[0]["params"] is None
# CLI: 端末で人が打たないと採れない
out = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "adopt-words", "W-0001", "--by", "Claude"], capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
assert out.returncode == 3 and "F9.human" in out.stderr
# 試した後の紙: 対比が札より上、札は折り線より下で、折り上げる帯に文字が無い
for source, sid in ((gs, G), (ts, T)):
    after = hypotheses.load(sid)["after_try"]
    layout, fs = compose_after(source, "試し", after)
    assert not fs, [f.line() for f in fs]
    fold = next(s["y1"] for s in layout["shapes"] if s.get("dash"))
    card = [t for t in layout["texts"] if t.y >= fold]
    above = [t for t in layout["texts"] if t.y < fold]
    assert any(t.text and t.text.startswith("札") for t in card) and len(after["contrasts"]) == 3
    height = max(t.y + t.h for t in card) - fold
    assert not any(t.y + t.h > fold - height for t in above), "折り上げた札が上の文字に重なる"
    assert not any(t.text and "昔の職人" in t.text for t in above), "説明を札の外に出さない"
    assert "昔の職人" in " ".join(after["card"]), "歴史の問いを札で閉じない"
stem = pathlib.Path(tmp) / "a"
out = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "print", "H-A", "--out", str(stem)], capture_output=True, text=True)
# 刷るのは型紙だけ（窓口の決定 推し A・11-06）。試した後の紙は、前に配った道で開く時に作る口（print_after）が残り、そこで作れる
assert out.returncode == 0 and (pathlib.Path(tmp) / "a.pdf").exists() and not (pathlib.Path(tmp) / "a_after.pdf").exists(), out.stderr
from omochae import hypotheses as _hyp  # noqa: E402

assert _hyp.print_after("NDL-1187053-R0000005-L", "H-A", str(stem)) == 0 and (pathlib.Path(tmp) / "a_after.pdf").exists()
