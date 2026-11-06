"""書き込みの口（話す口・記録の口・説明の口・聞く口）と段の口に、同じ相手からの短い間の数の上限を置く（公開の前の点検の 9、統括の頼み 11-06）。

なぜ: 合言葉なしの場は誰でも書けて、書き込みの回数に上限が無かった。上限を超えたら、今ある字「少し待って、もう一度送ってください」で 429 を返す。
合言葉付きの場で 5 人が同じ網（同じ番地）から同時に一周しても止まらない数にする。
段の口は書き込みの口と別に数え（手順を押す数で記録や話す口を断らない）、超えても作りながら見る頁を止めない（統括の決め）。
相手はトンネル（cloudflared）が付ける見出しの番地で見分ける。手元から直に来た物（試験と手元の確かめ）は数えない。
"""
import http.client
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
STEP_LIMIT = 120  # 段の口の数（書き込みと別）。5 人が手順を全部同じ 1 分で押しても断らない
DONE_NOTE = "組み上がった事を残しました。動かしてみて、この頁で記録を残してください。"  # 組み上がりの後に記録の欄で出る今ある字


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


def form_step(base, ip, n, event):
    """フォームの段の送り（JS の無い頁と、組み上がりの札）。行き先を見るので、303 を追わない。"""
    host = base.split("//", 1)[1]
    c = http.client.HTTPConnection(host, timeout=60)
    body = urllib.parse.urlencode({"hypothesis": "H-A", "sheet_version": "1", "step": str(n), "event": event, "who": "formwhoaaa"})
    c.request("POST", f"/toy/{G}/step", body, {"Host": host, "Origin": base, "Content-Type": "application/x-www-form-urlencoded", "Cf-Connecting-Ip": ip})
    r = c.getresponse()
    out = (r.status, urllib.parse.unquote(r.getheader("Location") or ""), r.read().decode())
    c.close()
    return out


def loop_of(p, n, out):
    """1 人の一周。書き込み 12 回（考え 1・工夫 6・聞く 1・手帖の記録 1・上げた後 1・説明 1・記録の欄 1）と、
    段の札（開く・次の手順へを最後まで。書き込みとは別に数える）。"""
    codes = [p.talk("think", f"{n}人目の考え")[0]]
    codes += [p.talk("craft", f"{n}人目の工夫{i}", sheet_version="1", step=str(i + 1))[0] for i in range(6)]
    codes.append(p.post(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": f"{n}人目の問い"})[0])
    st, body, _ = p.post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "who": p.who})
    codes.append(st)
    rid = json.loads(body).get("id")
    codes.append(p.talk("keep", f"{n}人目の上げた後", record=rid)[0])
    codes.append(p.post(f"/record/{rid}/explain", {"text": f"{n}人目の説明", "next_idea": "幅を変える", "by": "作った人"})[0])
    codes.append(p.post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた", "who": p.who})[0])
    steps = [step(p, 1, "start")[0]] + [step(p, i, "next")[0] for i in range(1, TOTAL)]
    out[n] = (codes, steps)


server, base = start()
assert Person(base).post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 200
from web import tsukuru  # noqa: E402

TOTAL = tsukuru.count(G, "H-A", 1)
assert 5 * TOTAL <= STEP_LIMIT, TOTAL

# 1. 合言葉付きの場で、同じ網の 5 人が同時に一周しても止まらない（書き込みは 5 × 12 = 上限ちょうど。段は別に数える）
people = [Person(base, ROOM, f"room{n}whoaa") for n in range(5)]
out = {}
threads = [threading.Thread(target=loop_of, args=(p, n, out)) for n, p in enumerate(people)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert all(len(c) == 12 and all(x in (200, 201) for x in c) and all(x == 200 for x in s) for c, s in out.values()), out

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
# 段の口は別に数えるので、書き込みが上限でも手順を押す札は止まらない
assert step(people[2], 2, "next")[0] == 200

# 段の口の上限: 置き場へ書かない。頁は止めない（JSON の札には次の手順を添えて 429、フォームは成功と同じ行き先へ 303）
making = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "making"
busy = Person(base, "198.51.100.60", "busywhoaaa")
codes = [step(busy, 1, "back")[0] for _ in range(STEP_LIMIT)]
assert codes.count(200) == STEP_LIMIT, codes[-3:]
before = sorted(making.rglob("*"))
st, body, headers = step(busy, 2, "next")
assert st == 429 and json.loads(body) == {"error": BUSY, "step": 3} and int(headers["Retry-After"]) >= 1, (st, body[:200])
st, where, _ = form_step(base, "198.51.100.60", 2, "next")
assert st == 303 and where == f"/toy/{G}/tsukuru?h=H-A&v=1&n=3", (st, where)
st, where, _ = form_step(base, "198.51.100.60", 2, "stuck")
assert st == 303 and where == f"/toy/{G}/tsukuru?h=H-A&v=1&n=2&ev=stuck", (st, where)
st, where, _ = form_step(base, "198.51.100.60", TOTAL, "done")
assert st == 303 and where.startswith(f"/toy/{G}?msg={DONE_NOTE}&at=kiroku&see=H-A&kind=sheet&v=1"), ("組み上がりは記録の欄へ", st, where)
after = sorted(making.rglob("*"))
assert before and before == after, ("断った段は置き場へ書かない（前に書いた段は在る）", len(before), len(after))
# 段の口が上限でも、同じ番地の書き込みは止まらない
assert busy.talk("think", "段の後の字")[0] == 200

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

assert play_server.BUSY == BUSY and play_server.WRITE_LIMIT == WRITE_LIMIT and play_server.WRITE_WINDOW == 60 and play_server.STEP_LIMIT == STEP_LIMIT
assert tsukuru.DONE_NOTE == DONE_NOTE
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
print("ok: 書き込みの口と段の口に、同じ相手からの短い間の数の上限")
