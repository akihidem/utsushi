"""自分の仮説を残す口に、記録と同じ床を当てる（#336 の続き。J-028 の「連絡先の形は床で落とす」）。本物の API は呼ばない。

なぜ: 自分の仮説の文は紙に刷られ、図鑑にも出る。save_own には床が無く、作る側の命令からも、話した字から作る道の採る所からも、
メールや電話番号の形がそのまま残った。入口の床（draft_words・talk_log）を通らずに置かれた字も、残す所で止める。

見る線: 3 つの欄のどれに連絡先の形があっても残さず、番号も使わない。寸法や日付の数字は断らない。上限を越えた文は検査の前に断る。
命令は rc 3 で理由を言う。話した字の道は採れず、案は採る前のまま残り、紙も作らない。
"""
import os
import subprocess
import sys
import tempfile

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import words  # noqa: E402
from omochae import contrib, hypotheses, loop  # noqa: E402
from web import think_sheet  # noqa: E402
from web.play_server import out_dir  # noqa: E402

G = "NDL-1187053-R0000005-L"
SHAPES = ("taro@example.com", "taro at example dot com", "090-1234-5678", "０９０－１２３４－５６７８", "〒123-4567")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def saved():
    return [h["id"] for h in hypotheses.own_hypotheses(G)]


# 3 つの欄のどれにあっても残さない。理由は記録と同じ床の印で、どの欄かを言う
for shape in SHAPES:
    for where, args in (("name", (f"案 {shape}", "押す", "図の棒")), ("how", ("案", f"押す {shape}", "図の棒")), ("evidence", ("案", "押す", f"図の棒 {shape}"))):
        rec, fails = hypotheses.save_own(G, *args)
        assert rec is None and {(f.floor, f.where) for f in fails} == {("F10.pii", where)}, (shape, where, rec, fails)
assert saved() == [], "断った文を残さない"

# 空の時は今までどおり「空」と言う
fails = hypotheses.save_own(G, "", "押す", "図の棒")[1]
assert {f.floor for f in fails} == {"F9.own"} and "空" in fails[0].message, fails

# 上限を越えた文は、検査に入る前に断る（#161 の線）
seen = []
real = contrib.check_pii
contrib.check_pii = lambda c: seen.append(c) or real(c)
try:
    for args in (("a" * (contrib.MAX_BODY + 1), "押す", "図の棒"), ("案", "a" * (contrib.MAX_BODY + 1), "図の棒"), ("案", "押す", "a" * (contrib.MAX_BODY + 1))):
        rec, fails = hypotheses.save_own(G, *args)
        assert rec is None and "超える" in fails[0].message, fails
    assert seen == [], "上限を越えた文を検査に回した"
finally:
    contrib.check_pii = real
assert saved() == []

# 寸法や日付の数字は断らない。断った分で番号を使わない
rec, fails = hypotheses.save_own(G, "筒を 30mm にした案", "折りを 24 回にして 2026-11-05 に 3 回試した", "コマ 5 の左頁、高さ 120mm")
assert not fails and rec["id"] == "OWN-1", (rec, fails)

# 作る側の命令: 理由を言って rc 3。残さない。通る文は今までどおり残す
env = {**os.environ, "PYTHONPATH": os.path.join(ROOT, "src")}
run = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "--source", G, "own", "案", "--how", "連絡は taro@example.com へ", "--evidence", "図の棒"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
assert run.returncode == 3 and "F10.pii" in run.stderr, (run.returncode, run.stderr[-300:])
assert saved() == ["OWN-1"]
run = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "--source", G, "own", "糸で引く案", "--how", "糸を引く", "--evidence", "図の棒"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
assert run.returncode == 0, (run.returncode, run.stderr[-300:])
assert saved() == ["OWN-1", "OWN-2"]


# 話した字から作る道: 入口の床より前に残った字や、手で置いた字が案に入っていても、採る所で止める
def waiting(text, token):
    rec = {"source_id": G, "status": "pending_human", "name": "仮説 A から変えた案", "how_it_moves": text, "evidence": "仮説 A の紙を見て話した考え", "typed_by": words.THINK_BY,
           "base": "H-A", "base_params": {}, "token": token, "result": {"fits": False, "params": {}, "not_fit": ["雛形に無い"]}}
    return loop.save_numbered("words", "W", lambda wid: {"id": wid, **rec})


wid = waiting("電話は 090-1234-5678 です", "own-pii-token")
rec, fails = words.adopt_words(wid, "画面で本人")
assert rec is None and {f.floor for f in fails} == {"F10.pii"}, (rec, fails)
assert words.by_token(G, "own-pii-token")["status"] == "pending_human" and saved() == ["OWN-1", "OWN-2"], "案は採る前のまま、仮説は増えない"
# 画面の「この紙にする」も、紙を作らずに断る。話した字を返事の文に出さない
paper, says = think_sheet.confirm(G, "own-pii-token")
assert paper is None and says == think_sheet.FAILED and "090" not in says
assert saved() == ["OWN-1", "OWN-2"] and not list(out_dir(G).glob("OWN-3*"))
# 床に当たらない字は同じ道で採れる
ok = waiting("割り箸の柄で押すと大きく開くと思う", "own-pii-token-2")
rec, fails = words.adopt_words(ok, "画面で本人")
assert not fails and rec["id"] == "OWN-3", (rec, fails)
print("ok: 自分の仮説を残す口に、記録と同じ床がある")
