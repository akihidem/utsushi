"""書き込みの口（話す口・記録の口・説明の口・聞く口・段の口）に、同じ相手からの短い間の数の上限を置く（公開の前の点検の 9、統括の頼み 11-06）。

なぜ: 合言葉なしの場は誰でも書けて、書き込みの回数に上限が無かった。上限を超えたら、今ある字「少し待って、もう一度送ってください」で 429 を返す。
合言葉付きの場で 5 人が同じ網（同じ番地）から同時に一周しても止まらない数にする。
相手はトンネル（cloudflared）が付ける見出しの番地で見分ける。手元から直に来た物（試験と手元の確かめ）は数えない。
"""
import json
import os
import pathlib
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
ROOM = "203.0.113.5"  # 5 人が同じ網から来る時の番地（例の番地）
BUSY = "受け付けられませんでした。少し待って、もう一度送ってください。"  # 今ある字（全体の受け皿の断りと同じ）
WRITE_LIMIT = 60  # 同じ相手から 1 分に受ける書き込みの数。5 人 × 12 回


def start(public=False):
    s = serve(0, public_open=public)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


class Person:
    """1 つのブラウザ。cookie を持ち、トンネル越しなら番地の見出しを付けて送る。"""

    def __init__(self, base, ip=None, who="", header="Cf-Connecting-Ip"):
        self.base, self.ip, self.who, self.header = base, ip, who, header
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

    def post(self, path, data):
        h = {"Origin": self.base} | ({self.header: self.ip} if self.ip else {})
        r = urllib.request.Request(self.base + path, data=urllib.parse.urlencode(data).encode(), headers=h)
        try:
            with self.op.open(r) as res:
                return res.status, res.read().decode(), res.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(), e.headers

    def talk(self, scene, text, **more):
        return self.post(f"/toy/{G}/talk", {"scene": scene, "hypothesis": "H-A", "text": text, "who": self.who, "json": "1", **more})


def step(p, n, event, as_json=True):
    return p.post(f"/toy/{G}/step", {"hypothesis": "H-A", "sheet_version": "1", "step": str(n), "event": event, "who": p.who} | ({"json": "1"} if as_json else {}))


def loop_of(p, n, out):
    """1 人の一周の書き込み 12 回: 考え 1・作る頁を開く 1・次の手順へ 4・工夫 2・聞く 1・手帖の記録 1・上げた後 1・説明 1。"""
    codes = [p.talk("think", f"{n}人目の考え")[0], step(p, 1, "start")[0]]
    codes += [step(p, i + 1, "next")[0] for i in range(4)]
    codes += [p.talk("craft", f"{n}人目の工夫{i}", sheet_version="1", step=str(i + 1))[0] for i in range(2)]
    codes.append(p.post(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": f"{n}人目の問い"})[0])
    st, body, _ = p.post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "who": p.who})
    codes.append(st)
    rid = json.loads(body).get("id")
    codes.append(p.talk("keep", f"{n}人目の上げた後", record=rid)[0])
    codes.append(p.post(f"/record/{rid}/explain", {"text": f"{n}人目の説明", "next_idea": "幅を変える", "by": "作った人"})[0])
    out[n] = codes


server, base = start()
assert Person(base).post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 200

# 1. 合言葉付きの場で、同じ網の 5 人が同時に一周しても止まらない（5 × 12 = 上限ちょうど）
people = [Person(base, ROOM, f"room{n}whoaa") for n in range(5)]
out = {}
threads = [threading.Thread(target=loop_of, args=(p, n, out)) for n, p in enumerate(people)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert all(len(c) == 12 and all(x in (200, 201) for x in c) for c in out.values()), out

# 2. 上限を超えた次の書き込みは 429。字は今ある物で、口の形で返す
for _ in range(WRITE_LIMIT - 5 * 12):
    assert people[0].talk("think", "上限までの字")[0] == 200
st, body, headers = people[0].talk("think", "上限を超えた字")
assert st == 429 and json.loads(body) == {"kept": False, "why": BUSY}, (st, body[:200])
assert int(headers["Retry-After"]) >= 1, headers["Retry-After"]
st, body, _ = people[1].post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "who": people[1].who})
assert st == 429 and json.loads(body) == {"error": BUSY}, (st, body[:200])
st, body, _ = people[2].post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた", "who": people[2].who})
assert st == 429 and BUSY in body, (st, body[-300:])
st, body, _ = people[3].post("/record/R-0001/explain", {"text": "説明", "next_idea": "次", "by": "人"})
assert st == 429 and BUSY in body, (st, body[-300:])
st, body, _ = people[4].post(f"/toy/{G}/talk", {"scene": "think", "hypothesis": "H-A", "text": "頁から送った字", "who": people[4].who})
assert st == 429 and BUSY in body, ("話す口の頁の形", st)
st, body, _ = people[0].post(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": "谷折りって？"})
assert st == 429 and json.loads(body) == {"text": BUSY, "from": "busy"}, ("聞く口は答えの欄の形", st, body[:200])
st, body, _ = people[1].post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "谷折りって？"})
assert st == 429 and BUSY in body, ("聞く口の頁の形", st)
# 段の口: 置き場へ書かずに断り、頁を読み直さない札が止まらないよう、次に見せる手順を添える
making = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "making"
before = sorted(making.rglob("*")) if making.exists() else []
st, body, _ = step(people[2], 2, "next")
assert st == 429 and json.loads(body) == {"error": BUSY, "step": 3}, (st, body[:200])
st, body, _ = step(people[3], 2, "next", as_json=False)
assert st == 429 and BUSY in body, ("段の口の頁の形", st)
after = sorted(making.rglob("*")) if making.exists() else []
assert before and before == after, ("断った段は置き場へ書かない（前に書いた段は在る）", len(before), len(after))

# 3. 別の網の人は止まらない。数えない口（刷る口）は同じ網でも止まらない
other = Person(base, "198.51.100.20", "otherwhoaa")
assert other.talk("think", "別の網の字")[0] == 200 and step(other, 1, "next")[0] == 200
assert people[0].post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 200

# 4. 手元から直に来た物（見出しの無い 127.0.0.1）は数えない
local = Person(base, who="localwhoaaa")
assert all(local.talk("think", f"手元の字{i}")[0] == 200 for i in range(WRITE_LIMIT + 5))

# 5. Cf-Connecting-Ip が無い時は X-Forwarded-For の最初の番地で数える
xff = Person(base, "198.51.100.30, 198.51.100.99", "xffwhoaaaa", header="X-Forwarded-For")
codes = [xff.talk("think", f"XFF の字{i}")[0] for i in range(WRITE_LIMIT + 1)]
assert codes.count(200) == WRITE_LIMIT and codes[-1] == 429, codes[-3:]
server.shutdown()

from web import play_server  # noqa: E402

assert play_server.BUSY == BUSY and play_server.WRITE_LIMIT == WRITE_LIMIT and play_server.WRITE_WINDOW == 60
WriteLimit, writer = play_server.WriteLimit, play_server.writer

# 6. 見出しを信じるのは手元から来た時だけ（家の網の機器が見出しを変えて数を逃れない）
assert writer("203.0.113.20", {"Cf-Connecting-Ip": "198.51.100.40"}) == "203.0.113.20"  # 家の網から直に来た機器（手元でない番地）
assert writer("127.0.0.1", {"Cf-Connecting-Ip": "198.51.100.40"}) == "198.51.100.40"
assert writer("::1", {"X-Forwarded-For": "198.51.100.41, 198.51.100.98"}) == "198.51.100.41"
assert writer("127.0.0.1", {}) is None and writer("::1", {}) is None

# 7. 短い間が過ぎれば、また書ける。覚える相手の数には限りがある
lim = WriteLimit(limit=2, window=0.3, keys=3)
assert [lim.wait("a") for _ in range(3)][:2] == [0, 0] and lim.wait("a") >= 1
time.sleep(0.35)
assert lim.wait("a") == 0
for k in range(10):
    lim.wait(f"k{k}")
time.sleep(0.35)
lim.wait("last")
assert len(lim.times) <= 4, len(lim.times)

# 8. 合言葉なしの場でも同じ上限
server, base = start(public=True)
p = Person(base, "203.0.113.50", "openwhoaaa")
codes = [p.talk("think", f"開いた場の字{i}")[0] for i in range(WRITE_LIMIT + 1)]
assert codes.count(200) == WRITE_LIMIT and codes[-1] == 429, codes[-3:]
server.shutdown()
print("ok: 書き込みの口に、同じ相手からの短い間の数の上限")
