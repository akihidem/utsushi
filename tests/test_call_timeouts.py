"""Claude の呼び出しと ffmpeg が返らない時も、画面の頁は決まった時間で戻る。本物の API は呼ばない。

なぜ要るか: 画面の要求の中で Claude を呼ぶのに、時間切れを渡していなかった（入れてある SDK の既定は 10 分・やり直し 2 回）。
動画の ffprobe と ffmpeg にも時間切れが無く、壊れた動画で止まると、その要求は戻らない。

なぜ手元に口を立てるか: 偽の client では、SDK に時間切れが届いている事を確かめられない。本物の SDK を、つなげても何も返さない
手元の口へ向ける（外の網には出ない）。時間は短く置き換えて、試験を速く回す。
"""
import json
import os
import pathlib
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from types import SimpleNamespace as NS

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["ANTHROPIC_API_KEY"] = "dummy"  # 手元の口にしか送らない
os.environ["NO_PROXY"] = "127.0.0.1"

import anthropic  # noqa: E402

from api import agent, ask, config, observe  # noqa: E402
from omochae import hypotheses, loop, records  # noqa: E402
from web import techo_site  # noqa: E402
from web.play_server import serve  # noqa: E402

# 1. 画面から呼ぶ役は、config の時間切れとやり直しの回数で client を作る。命令から呼ぶ役は、待てるので SDK の既定のまま
assert set(config.SCREEN_TIMEOUT) == {"ask", "observe", "interpret"}, config.SCREEN_TIMEOUT
for role, limit in config.SCREEN_TIMEOUT.items():
    c = agent.default_client(role)
    assert c.timeout == limit and c.max_retries == config.SCREEN_RETRIES, (role, c.timeout, c.max_retries)
    assert limit <= 120 and config.SCREEN_RETRIES <= 1, role  # SDK の既定（10 分・2 回）へ戻さない
for c in (agent.default_client(), agent.default_client("generate")):
    assert c.timeout == anthropic.DEFAULT_TIMEOUT and c.max_retries == anthropic.DEFAULT_MAX_RETRIES, (c.timeout, c.max_retries)


class Silent:
    """つなげても何も返さない口。つないだ数を数える（やり直しの回数が SDK に届いている事を見る）。"""

    def __init__(self):
        self.sock, self.conns = socket.create_server(("127.0.0.1", 0)), []
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            self.conns.append(self.sock.accept()[0])  # 閉じずに持つ。閉じると、すぐ失敗して時間切れにならない

    @property
    def url(self):
        return f"http://127.0.0.1:{self.sock.getsockname()[1]}"


silent = Silent()
os.environ["ANTHROPIC_BASE_URL"] = silent.url
assert str(agent.default_client("ask").base_url).startswith(silent.url), "手元の口だけに送る"
config.SCREEN_TIMEOUT = {"ask": 0.5, "observe": 0.5, "interpret": 0.5}
config.SCREEN_RETRIES = 1
# 0.5 秒 × 2 回に、やり直しの間（SDK の既定で 1 秒まで）を足した見込み。遅い機械でも越えない幅を取る。SDK の既定なら 10 分なので紛れない
BOUND = 6.0

G = "NDL-1187053-R0000005-L"
server = serve(0)
base = f"http://127.0.0.1:{server.server_address[1]}"
threading.Thread(target=server.serve_forever, daemon=True).start()


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    op = urllib.request.build_opener(type("N", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))
    try:
        x = op.open(r, timeout=60)
        return x.status, x.headers.get("Location", ""), x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", ""), e.read().decode()


def timed(path, data):
    """送って、返った物・かかった秒・手元の口へつないだ数を返す。"""
    n, t = len(silent.conns), time.monotonic()
    code, loc, body = post(path, data)
    return code, loc, body, time.monotonic() - t, len(silent.conns) - n


video = os.path.join(tempfile.mkdtemp(), "v.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10", "-pix_fmt", "yuv420p", video], check=True)
hypotheses.save_prediction(G, "押すと開く")
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303
rid, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
assert not loop.save_explanation(rid, "本人", "開いた", "速く押す")
techo_site.media_dir(rid).mkdir(parents=True, exist_ok=True)
shutil.copy(video, techo_site.media_dir(rid) / "m1.mp4")
ask._key_present = lambda: True  # 鍵がある時の道を通す。送る先は手元の口だけ

# 2. 画面の 4 つの口が、Claude が返らなくても決めた秒数の中で戻り、「今は AI に聞けません」と言う。つないだ数が 2 なら、やり直しの回数も届いている
code, _, body, took, tries = timed(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": "竹串はいつ通すの？"})
got = json.loads(body)
assert code == 200 and "今は AI に聞けません" in got["text"] and got["from"] == "error", (code, got)
assert took < BOUND and tries == 2, ("ask-json", took, tries)

code, _, page, took, tries = timed(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "竹串はいつ通すの？"})
assert code == 200 and "今は AI に聞けません" in page, code
assert took < BOUND and tries == 2, ("ask", took, tries)

for act in ("ai-interpret", "ai-observe"):
    code, loc, _, took, tries = timed(f"/record/{rid}/{act}", {"back": "techo"})
    assert code == 303 and urllib.parse.quote("今は AI に聞けません") in loc, (act, code, loc)
    assert took < BOUND and tries == 2, (act, took, tries)
server.shutdown()

# 3. 動画の外の命令が返らない時、observe は時間切れで「動画のコマを取り出せない」と戻り、Claude を呼ばない
fake = pathlib.Path(tempfile.mkdtemp())


def tool(name, body):
    p = fake / name
    p.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    p.chmod(0o755)


class Never:
    """呼ばれたら落とす client。動画のコマが無い時は Claude を呼ばない事を見る。"""

    @property
    def messages(self):
        raise AssertionError("コマが無いのに Claude を呼んだ")


def frames_of(video_path):
    t = time.monotonic()
    out = observe.frames(video_path)
    return out, time.monotonic() - t


config.VIDEO_TIMEOUT = 0.5
keep_path = os.environ["PATH"]
assert len(observe.frames(video)) == 3, "本物の命令なら 3 コマ取れる（時間切れで前の動きを壊していない）"
os.environ["PATH"] = f"{fake}{os.pathsep}{keep_path}"
tool("ffprobe", "exec sleep 30")  # 長さを見る所で止まる
out, took = frames_of(video)
assert out == [] and took < 5, (out, took)
assert observe.observe(rid, video, Never()) == (None, "動画のコマを取り出せない")
tool("ffprobe", "echo 2.0")
tool("ffmpeg", "exec sleep 30")  # コマを取る所で止まる
out, took = frames_of(video)
assert out == [] and took < 5, (out, took)
assert observe.observe(rid, video, Never()) == (None, "動画のコマを取り出せない")
# ffprobe はあるが ffmpeg が無い機械でも、頁を落とさず空で戻す（docstring の約束。前は OSError が抜けた）
(fake / "ffmpeg").unlink()
os.environ["PATH"] = str(fake)
assert observe.frames(video) == []
os.environ["PATH"] = keep_path


# 4. 画面の役の輪は、全部の時間にも上限がある（1 回ごとの時間切れだけだと、往復の数だけ長くなる）。命令から呼ぶ役は待てるので上限なし
def tool_use(name, input, i):
    return NS(type="tool_use", name=name, input=input, id=f"{i}-{name}")


class Slow:
    """1 回ごとに待ってから、台本どおりに返す偽の client。"""

    def __init__(self, script, wait):
        self.script, self.calls, self.wait = list(script), [], wait
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        time.sleep(self.wait)
        return NS(content=self.script.pop(0), stop_reason="tool_use", usage=NS(input_tokens=10, output_tokens=5))


SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}
ECHO = [{"name": "echo", "description": "", "input_schema": {"type": "object"}}]
script = lambda: [[tool_use("echo", {}, "a")], [tool_use("submit_result", {"answer": "x"}, "b")]]  # noqa: E731
assert set(config.RUN_TIME_LIMIT) == {"interpret"}, config.RUN_TIME_LIMIT
assert config.RUN_TIME_LIMIT["interpret"] >= config.SCREEN_TIMEOUT["interpret"]
config.RUN_TIME_LIMIT = {"interpret": 0.2}
slow = Slow(script(), 0.3)
try:
    agent.run("interpret", "指示", "問い", ECHO, SCHEMA, lambda n, i: "", client=slow)
    raise AssertionError("時間切れで止まるはず")
except agent.AgentStopped as e:
    assert "時間切れ" in str(e), e
assert len(slow.calls) == 1, "上限を越えたら次を呼ばない"
slow = Slow(script(), 0.3)
assert agent.run("generate", "指示", "問い", ECHO, SCHEMA, lambda n, i: "", client=slow)[0] == {"answer": "x"}
assert len(slow.calls) == 2, "命令から呼ぶ役は止めない"
print("ok")
