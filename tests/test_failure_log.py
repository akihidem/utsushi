"""画面の操作で失敗した時、作る側が読む記録に、後から原因を引ける物が残る。学ぶ人の書いた文と合言葉は残らない。本物の API は呼ばない。

なぜ要るか: サーバの記録は例外の型と文の 1 行だけで、どの道か・どの行かが無かった。Claude を呼ぶ所は例外を全部「今は AI に聞けません」に
替えて、何も残さなかった。本物の API はまだ 1 回も呼んでいないので、最初の本番でモデル名・引数・鍵のどれで落ちても見分けられなかった。
逆に、例外の文をそのまま出すと、int(form["x"]) の ValueError のように送った値が記録に入る。
"""
import contextlib
import io
import json
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api import ask, budget  # noqa: E402
from omochae import hypotheses, records  # noqa: E402
from web import play_server  # noqa: E402

KEY = "k" * 8 + "aikotoba" + "k" * 8  # 合言葉（16 字以上）
WRITTEN = "だれにも見せない予想の文"
G = "NDL-1187053-R0000005-L"

server = play_server.serve(0, public_key=KEY)
base = f"http://127.0.0.1:{server.server_address[1]}"
threading.Thread(target=server.serve_forever, daemon=True).start()
opener = urllib.request.build_opener(type("N", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))


def call(path, form=None):
    """要求を送り、(番号, 本文, その間に stderr へ出た物) を返す。合言葉は Cookie で渡す。GET は道の ?k= でも渡す（記録に出ない事を見る）。POST は ? つきの道を受けない。"""
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    query = f"?k={KEY}" if form is None else ""
    headers = {"Cookie": f"utsushi_k={KEY}", "Origin": base}
    if data:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    log = io.StringIO()
    with contextlib.redirect_stderr(log):
        try:
            r = opener.open(urllib.request.Request(f"{base}{path}{query}", data=data, headers=headers), timeout=30)
            code, body = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            code, body = e.code, e.read().decode()
    return code, body, log.getvalue()


def clean(log):
    """どの記録にも、学ぶ人の書いた文と合言葉が入らない。"""
    assert WRITTEN not in log, ("書いた文が記録に出た", log)
    assert KEY not in log and "?k=" not in log, ("合言葉が記録に出た", log)


assert call(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303


# 1. 例外を起こした POST: 時刻・メソッド・道・型・トレースバックが出て、例外の文に入った送った文は出ない。画面の文は前と同じ
def boom_add(rec):
    raise ValueError(f"読めない値: {rec['note']}")  # 送った値が例外の文に入る形（int(form["x"]) と同じ）


keep_add = records.add
records.add = boom_add
code, body, log = call(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "note": WRITTEN})
records.add = keep_add
assert code == 500 and "受け付けられませんでした" in body, (code, body)
clean(log)
assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", log), ("時刻が無い", log)
assert f"POST /toy/{G}/record-json" in log, ("メソッドと道が無い", log)
assert "ValueError" in log and "boom_add" in log and "line " in log, ("型とトレースバックが無い", log)


# 2. 例外を起こした GET も同じ
def boom_page(sid, **kw):
    raise KeyError(WRITTEN)


keep_page = play_server.toy_page
play_server.toy_page = boom_page
code, body, log = call(f"/toy/{G}")
play_server.toy_page = keep_page
assert code == 500 and "うまく表示できませんでした" in body, (code, body)
clean(log)
assert f"GET /toy/{G}" in log and "KeyError" in log and "boom_page" in log, log


# 3. Claude の呼び出しの失敗: 役と型と文が出る。画面の文は前のまま（理由は画面に出さない）
def api_error(name, text):
    """SDK の例外の形。文に質問と鍵らしい物が混じっても、記録では伏せる。"""
    return type(name, (Exception,), {"__module__": "anthropic"})(text)


keep_answer, keep_present = ask.answer, ask._key_present
ask._key_present = lambda: True
key_like = "sk-" + "ant-" + "x" * 24  # 試験の作り物。本物の鍵の形をそのまま書くと、push の門が止める


def fail_with(e):
    def f(*a, **k):
        raise e
    ask.answer = f


fail_with(api_error("BadRequestError", f"Error code: 400 model: claude-nothing-5 not found / {WRITTEN} / {key_like}"))
code, body, log = call(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": WRITTEN})
got = json.loads(body)
assert code == 200 and got["from"] == "error" and "今は AI に聞けません" in got["text"], got
clean(log)
assert key_like not in log, ("鍵らしい物が記録に出た", log)
assert "ask" in log and "BadRequestError" in log and "claude-nothing-5" in log, ("役と型と文が無い", log)
assert f"POST /toy/{G}/ask-json" in log, log
code, body, log = call(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": WRITTEN})  # 玩具の頁の口も同じ
assert code == 200 and "今は AI に聞けません" in body and "claude-nothing-5" not in body, code
clean(log)
assert "ask" in log and "BadRequestError" in log and "claude-nothing-5" in log, log

# 引数の間違いの TypeError は、文に名前だけが入るので出す（最初の本番で落ちそうな所）
fail_with(TypeError("create() got an unexpected keyword argument 'fallbacks'"))
log = call(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": WRITTEN})[2]
clean(log)
assert "TypeError" in log and "fallbacks" in log, log

# 文に値が入り得る例外は、型とトレースバックだけ
fail_with(ValueError(f"読めない値: {WRITTEN}"))
log = call(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": "別の問い"})[2]
clean(log)
assert "ValueError" in log and "読めない値" not in log, log

# 予算で止めた時は、画面では短い文だけ、記録には額まで残る（手帖では理由の文を捨てていた）
fail_with(budget.BudgetStop("今日の見積もり $49.90 と次の 1 回の最大 $0.50 で日割りの上限 $50 に達する。本人の承認が要る", "day"))
code, body, log = call(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": WRITTEN})
assert "$" not in json.loads(body)["text"] and json.loads(body)["from"] == "stop", body
clean(log)
assert "ask" in log and "BudgetStop" in log and "$49.90" in log, log
ask.answer = keep_answer

# 4. 手帖の Claude の返事の口（interpret・observe）も、役が分かる
from api import agent, loop_agents  # noqa: E402
from omochae import loop  # noqa: E402
from web import techo_site  # noqa: E402

rid, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
assert not loop.save_explanation(rid, "本人", "開いた", "速く押す")
techo_site.media_dir(rid).mkdir(parents=True, exist_ok=True)
(techo_site.media_dir(rid) / "m1.mp4").write_bytes(b"not a video")
agent.default_client = lambda role=None: (_ for _ in ()).throw(api_error("AuthenticationError", f"invalid x-api-key {key_like}"))
keep_interpret = loop_agents.draft_interpretation
for act, role in (("ai-interpret", "interpret"), ("ai-observe", "observe")):
    code, _, log = call(f"/record/{rid}/{act}", {"back": "techo"})
    assert code == 303, code
    clean(log)
    assert key_like not in log and role in log and "AuthenticationError" in log and "invalid x-api-key" in log, (role, log)
    assert f"POST /record/{rid}/{act}" in log, log


# 5. 輪が止めた理由は、前の方の決まった文だけ（後ろには案の中身が入り得る）
def stopped(*a, **k):
    raise agent.AgentStopped(f"検査に落ち続けた: {WRITTEN}")


agent.default_client = lambda role=None: None
loop_agents.draft_interpretation = stopped
log = call(f"/record/{rid}/ai-interpret", {"back": "techo"})[2]
clean(log)
assert "interpret" in log and "AgentStopped" in log and "検査に落ち続けた" in log, log
loop_agents.draft_interpretation = keep_interpret
server.shutdown()

# 6. 型ごとの出し方。ファイルの失敗はどのファイルかまで。読めない JSON は文の中身を出さない。長すぎる名前は送られた値かも知れないので出さない
from web import failure_log  # noqa: E402

assert failure_log.safe_text(ValueError(WRITTEN)) == "" and failure_log.safe_text(KeyError(WRITTEN)) == ""
assert failure_log.safe_text(RuntimeError(WRITTEN)) == ""
try:
    json.loads('{"note": "' + WRITTEN)
except json.JSONDecodeError as e:
    text = failure_log.safe_text(e)
    assert WRITTEN not in text and "Unterminated" in text and "行" in text, text
text = failure_log.safe_text(FileNotFoundError(2, "No such file or directory", "out/R-0001.json"))
assert "out/R-0001.json" in text and "No such file" in text, text
text = failure_log.safe_text(OSError(36, "File name too long", WRITTEN * 40))
assert WRITTEN not in text and "File name too long" in text, text
# 道の ? より後ろは、どの形でも出さない
log = io.StringIO()
with contextlib.redirect_stderr(log):
    failure_log.request_failed("POST", f"/toy/{G}/ask?k={KEY}&note={WRITTEN}", ValueError("x"))
clean(log.getvalue())
assert f"POST /toy/{G}/ask の失敗" in log.getvalue(), log.getvalue()
print("ok")
