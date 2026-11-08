"""作業の頁の「聞く」（本人 11-08 539「3D 重ねずに、質問もできるだけにしよう。質問した時のその瞬間の写真を何枚か撮って、音声を文字にして
認識して、クロードが考えて答えを音声で出すようにする。iPhone のカメラと HMD で使えるようにする。記録はここでは取らず、質問のための経路と
割り切る。」）の、サーバの側の試験。本物の API・マイク・カメラ・声を字にする型は使わない（偽の作り手と偽の Claude）。

見る事:
1. 声を字にする常駐の作り手（omochae.asr_serve と asr_worker --serve）: 1 つずつ字にし、入口の床に当たった区切りを伏せる。時間切れ・壊れた中身・
   道具が無い時は種類だけを返す。止めた作り手の箱は掃除し、動いている作り手の箱は残す。声はファイルに残らない
2. 受け口 POST /toy/<印>/kasane/ask: 公開の場は本体を読む前に「この場では聞けません」・同じ出所だけ・鍵が無い場は声を字にする前に断る・
   大きさと形の上限・同じ相手 1 分 6 回と場の全体 1 日の回数・聞き取れない時・道具が無い時・費用の止め・仕組みの問い・語の問い
3. 記録を取らない（539）: making_log・talk_log・records を呼ばず、記録の置き場に何も増えない。失敗の記録と費用の台帳に問いの字が無い
4. Claude に渡す物: 写真は 3 枚まで・今の手順の字（頁と同じ文から番号で引く）・仮説の名前と動き方は渡さず、混ざった答えは断りに替える
5. 玩具ごとの中身: 虎に御来迎の紙の字（筒・扇・蛇腹の絵・色の境）が渡らない。語の表（御来迎の紙の字）は御来迎の時だけ使い、虎の語の問いは
   Claude に虎の紙の凡例で聞く（11-08 に公開デモの虎で「谷折り・山折り」に御来迎の答えが返った・前の口 api.ask の語の表と凡例の字から）
"""
import base64
import contextlib
import html
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = str(pathlib.Path(tempfile.mkdtemp()) / "usage.jsonl")
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("OMOCHAE_ASR_PYTHON", None)

from api import ask, budget, kasane  # noqa: E402
from omochae import asr_serve, hypotheses, making_log, records, talk_log  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402
from web import hmd, play_server  # noqa: E402

G, T = hmd.TOYS
WORKER = ROOT / "src/omochae/asr_worker.py"

# ---- 1. 常駐の作り手
assert asr_serve.BOX_PREFIX in WORKER.read_text(encoding="utf-8") and f'BOX_PREFIX = "{asr_serve.BOX_PREFIX}"' in WORKER.read_text(encoding="utf-8"), \
    "箱の名の頭が作り手と掃除で同じ"
FAKE = r'''
import json, sys, time
out, src = sys.stdout, sys.stdin.buffer
out.write(json.dumps({"ready": True}) + "\n"); out.flush()
while True:
    head = src.read(8)
    if len(head) < 8:
        break
    data = src.read(int.from_bytes(head[:4], "big"))
    if data == b"HANG":
        time.sleep(60)
    elif data == b"BAD":
        out.write(json.dumps({"error": "decode"}) + "\n")
    elif data == b"DIE":
        sys.exit(1)
    else:
        segs = [{"start": 0, "end": 1, "text": t} for t in data.decode().split("|")]
        out.write(json.dumps({"segments": segs, "form": head[4:].decode()}, ensure_ascii=False) + "\n")
    out.flush()
'''
fake_dir = pathlib.Path(tempfile.mkdtemp())
(fake_dir / "fake_worker.py").write_text(FAKE, encoding="utf-8")
L = asr_serve.Listener(cmd=[sys.executable, "-I", str(fake_dir / "fake_worker.py")], timeout=3, start_timeout=20, idle=600)
assert L.text("谷折りは|どこですか".encode(), "webm") == "谷折りはどこですか", "区切りをつないで返す"
pid = L._proc.pid
hid = L.text("山田小学校の田中です|谷折りは".encode(), "mp4")
assert hid.startswith("［伏せた（") and hid.endswith("谷折りは") and "田中" not in hid and "山田" not in hid, ("入口の床に当たった区切りは伏せる", hid)
assert L._proc.pid == pid, "作り手は 1 本のまま（1 回ごとに立てない）"
for data, form, kind in ((b"BAD", "webm", "decode"), (b"x", "ogg", "form")):
    try:
        L.text(data, form)
        raise AssertionError(("字にできない時は種類で返す", kind))
    except asr_serve.Failed as e:
        assert e.kind == kind, (kind, e.kind)
t0 = time.monotonic()
try:
    L.text(b"HANG", "webm")
    raise AssertionError("時間切れで返らない")
except asr_serve.Failed as e:
    assert e.kind == "timeout" and time.monotonic() - t0 < 10, e.kind
assert L._proc is None, "時間切れの作り手は捨てる"
assert L.text("もう一度".encode(), "webm") == "もう一度", "次に頼まれた時に立て直す"
try:
    L.text(b"DIE", "webm")
    raise AssertionError("止まった作り手で返らない")
except asr_serve.Failed as e:
    assert e.kind == "broken", e.kind
L.stop()
try:
    asr_serve.Listener(python="").text(b"x", "webm")
    raise AssertionError("道具が無い時に断らない")
except asr_serve.Missing:
    pass
assert not asr_serve.Listener(python="").available()
# 使わない間が過ぎたら止める（型のメモリを持ち続けない）
idle = asr_serve.Listener(cmd=[sys.executable, "-I", str(fake_dir / "fake_worker.py")], timeout=3, start_timeout=20, idle=1)
idle.start()
for _ in range(40):
    if idle._proc is None:
        break
    time.sleep(.25)
assert idle._proc is None, "使わない間が過ぎたら作り手を止める"
# 箱の掃除: 止まった作り手の番号の箱は消し、動いている番号の箱は残す（別のサーバの作り手の箱を消さない）
shm = pathlib.Path(tempfile.mkdtemp())
dead = subprocess.Popen([sys.executable, "-c", "pass"])
dead.wait()
(shm / f"{asr_serve.BOX_PREFIX}{dead.pid}-x").mkdir()
(shm / f"{asr_serve.BOX_PREFIX}{dead.pid}-x" / "left").write_bytes(b"voice")
(shm / f"{asr_serve.BOX_PREFIX}{os.getpid()}-y").mkdir()
assert asr_serve.sweep(shm) == 1 and not (shm / f"{asr_serve.BOX_PREFIX}{dead.pid}-x").exists() and (shm / f"{asr_serve.BOX_PREFIX}{os.getpid()}-y").exists()

# 本物の作り手の頼みの形（型だけを偽にする）: ffmpeg で読める声は字の道へ、壊れた中身は decode。声は箱にも残らない
ffmpeg_note = ""
if shutil.which("ffmpeg"):
    voice = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-c:a", "libopus", "-f", "webm", "pipe:1"],
                           capture_output=True, timeout=60).stdout
    fake_model = fake_dir / "faster_whisper.py"
    fake_model.write_text("class WhisperModel:\n    def __init__(self, *a, **k):\n        pass\n"
                          "    def transcribe(self, voice, **k):\n        import types\n"
                          "        return iter([types.SimpleNamespace(start=0.0, end=0.5, text=' 長さ %d ' % len(voice))]), None\n", encoding="utf-8")
    runner = fake_dir / "run_worker.py"
    runner.write_text(f"import sys\nsys.path[:0] = [{str(fake_dir)!r}, {str(WORKER.parent)!r}]\nimport asr_worker\nasr_worker.serve('fake')\n", encoding="utf-8")
    real = asr_serve.Listener(cmd=[sys.executable, "-I", str(runner)], timeout=30, start_timeout=30)
    try:
        assert voice and real.text(voice, "webm") == "長さ 16000", "1 秒の声を 16kHz で読み、字の道へ渡す"
        try:
            real.text(b"\x1a\x45\xdf\xa3 not a voice", "webm")
            raise AssertionError("壊れた中身で返らない")
        except asr_serve.Failed as e:
            assert e.kind == "decode", e.kind
        boxes = [p for p in pathlib.Path("/dev/shm").glob(f"{asr_serve.BOX_PREFIX}{real._proc.pid}-*")] if pathlib.Path("/dev/shm").is_dir() else []
        assert all(not any(b.iterdir()) for b in boxes), ("管から読めなかった時の控えの箱に、声が残らない", boxes)
    finally:
        real.stop()
else:
    ffmpeg_note = "。測れない: ffmpeg が無いので、本物の作り手の読みは見ていない"

# ---- 2〜4. 受け口
CALLED = []


def refuse(name):
    def f(*a, **k):
        CALLED.append(name)
        raise AssertionError(f"作業の頁の聞く口が {name} を呼んだ（539: 記録はここでは取らない）")
    return f


for mod, name in ((making_log, "add_ask"), (making_log, "add"), (talk_log, "add"), (records, "add")):
    if hasattr(mod, name):
        setattr(mod, name, refuse(f"{mod.__name__}.{name}"))


class FakeListener:
    def __init__(self):
        self.reply, self.calls, self.warmed = "谷折りはどこを折りますか", [], 0

    def warm(self):
        self.warmed += 1

    def text(self, data, form):
        self.calls.append((len(data), form))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


class Block:
    def __init__(self, text):
        self.type, self.text = "text", text


class FakeClient:
    def __init__(self):
        self.calls, self.answer, self.error = [], "破線の所を、手前にへこむように折ってください。", None
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        if self.error:
            raise self.error
        return type("R", (), {"content": [Block(self.answer)], "usage": type("U", (), {"input_tokens": 1200, "output_tokens": 60})()})()


JPEG = b"\xff\xd8\xff\xe0" + b"j" * 2000
VOICE = b"\x1a\x45\xdf\xa3" + b"v" * 3000


def body(step=3, frames=3, voice=VOICE, kind="audio/webm", jpeg=JPEG):
    return json.dumps({"step": step, "type": kind, "voice": base64.b64encode(voice).decode(), "frames": [base64.b64encode(jpeg).decode()] * frames}).encode()


def start(public_open=False):
    server = play_server.serve(0, public_open=public_open)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    server.listener = FakeListener()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def post(base, data, origin=True, sid=G, who=None):
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = base
    if who:
        headers["Cf-Connecting-Ip"] = who
    req = urllib.request.Request(f"{base}/toy/{sid}/kasane/ask", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw.decode("utf-8", "replace")


# 見るのはファイル（記録・字・声・写真）。空の置き場の箱は、刷った版を読む所（loop.folder）が読むだけで作るので数えない
def files():
    return sorted(p.relative_to(os.environ["OMOCHAE_DATA"]) for p in pathlib.Path(os.environ["OMOCHAE_DATA"]).rglob("*") if p.is_file())


before = files()

# 公開の場: 本体を読む前に断る。声は字にしない
pub, pbase = start(public_open=True)
try:
    assert post(pbase, body()) == (403, {"text": hmd.ASK_PUBLIC, "from": "public"}), "公開の場は「この場では聞けません」"
    assert pub.listener.calls == [], "公開の場では声を字にしない"
    # 公開の場の頁は開いた時から「この場では聞けません」を出し、「聞く」もカメラも映像も置かない（押して送ってから断られる形にしない・別の目の止め 11-08）
    for path in (f"/toy/{G}/kasane", f"/toy/{G}/kasane/hmd"):
        page = urllib.request.urlopen(f"{pbase}{path}", timeout=60).read().decode()
        assert hmd.ASK_PUBLIC in page and 'id="hmd-ask"' not in page and 'id="hmd-camera"' not in page and "<video" not in page, ("公開の場は聞けない頁", path)
        assert hmd.CAM_NOTE not in page and hmd.HMD_NOTE not in page and html.escape(hmd.steps(G)[0]) in page, ("送る物の断りは置かず、手順は見られる", path)
    assert pub.listener.warmed == 0, "公開の場では作り手を立てない"
finally:
    pub.shutdown()
    pub.server_close()

server, base = start()
try:
    # 頁を開くと、作り手を裏で立て始める
    urllib.request.urlopen(f"{base}/toy/{G}/kasane/hmd", timeout=60).read()
    assert server.listener.warmed == 1, "作業の頁を開いた時に作り手を立て始める"
    # 鍵が無い場: 声を字にする前に断る
    assert post(base, body()) == (200, {"text": ask.NO_KEY, "from": "no_key"}) and server.listener.calls == [], "鍵が無い場では声を扱わない"
    client = FakeClient()
    server.ask_client = client
    # 同じ出所だけ
    assert post(base, body(), origin=False)[0] == 403 and server.listener.calls == []
    # 答える
    status, got = post(base, body(step=3))
    assert status == 200 and got == {"text": client.answer, "from": "ai"}, got
    sent = client.calls[-1]
    content = sent["messages"][0]["content"]
    assert [c["type"] for c in content] == ["image", "image", "image", "text"], "写真 3 枚と字"
    texts = hmd.steps(G)
    words = content[-1]["text"]
    assert f"今の手順: 3. {texts[2]}" in words and f"前の手順: 2. {texts[1]}" in words and f"次の手順: 4. {texts[3]}" in words, "今の手順の字は頁と同じ文から番号で引く"
    assert "質問: 谷折りはどこを折りますか" in words
    h = hypotheses.sheet_of(G)
    assert h.get("name") not in words and (not h.get("how_it_moves") or h["how_it_moves"] not in words), "仮説の名前と動き方は渡さない"
    assert sent["model"] == "claude-opus-5-5" and sent["system"] == kasane.SYSTEM and "手元だけを写してください" in kasane.SYSTEM, "型は J017・人が写った時の断りは答えの決まりに"
    assert server.listener.calls[-1][1] == "webm"
    # 写真の無い問い（前のカメラ・HMD の道）は字だけ
    post(base, body(frames=0, kind="audio/mp4"))
    assert [c["type"] for c in client.calls[-1]["messages"][0]["content"]] == ["text"] and server.listener.calls[-1][1] == "mp4"
    # 手順の外の番号は手順の字を付けない
    post(base, body(step=999))
    assert "今の手順" not in client.calls[-1]["messages"][0]["content"][-1]["text"]
    # 形と大きさの上限（声を字にする前に断る）
    n = len(server.listener.calls)
    for bad in (body(frames=4), body(jpeg=b"\x89PNG" + b"p" * 100), body(jpeg=b"\xff\xd8\xff" + b"j" * (play_server.ASK_FRAME_BYTES + 1)),
                body(kind="audio/ogg"), body(voice=b""), b"{not json", json.dumps({"step": 1, "type": "audio/webm", "voice": "@@@"}).encode()):
        assert post(base, bad)[0] == 422, bad[:60]
    assert post(base, body(voice=b"v" * (play_server.ASK_VOICE_BYTES + 1)))[0] in (413, 422)
    assert len(server.listener.calls) == n, "形の違う物は字にしない"
    # 聞き取れない・道具が無い・時間切れ
    for reply, want in (("", hmd.ASK_NOHEARD), (asr_serve.Failed("decode"), hmd.ASK_NOHEARD), (asr_serve.Missing("x"), hmd.ASK_DOWN), (asr_serve.Failed("timeout"), hmd.ASK_DOWN)):
        server.listener.reply = reply
        assert post(base, body())[1]["text"] == want, (reply, want)
    server.listener.reply = "谷折りはどこを折りますか"
    # 仕組みの問いと語の問いは Claude を呼ばない
    k = len(client.calls)
    server.listener.reply = "これはどういう仕組みで動くの"
    assert post(base, body()) == (200, {"text": ask.REFUSE, "from": "refuse"})
    server.listener.reply = "谷折りって何"
    assert post(base, body())[1]["from"] == "glossary"
    assert len(client.calls) == k, "仕組みの問いと語の問いは Claude を呼ばない"
    server.listener.reply = "谷折りはどこを折りますか"
    # 5. 玩具ごとの中身: 虎の語の問いは語の表（御来迎の紙の字）で答えず、虎の紙の凡例で Claude に聞く。虎に渡す字に、御来迎の部品と絵の字が無い
    k = len(client.calls)
    server.listener.reply = "谷折り・山折り"
    status, got = post(base, body(), sid=T)
    assert status == 200 and got["from"] == "ai" and len(client.calls) == k + 1, ("虎の語の問いは語の表で答えない", got)
    tora = client.calls[-1]["messages"][0]["content"][-1]["text"]
    for word in ("筒と扇", "外筒", "扇", "蛇腹（横から）", "色の境"):  # 「筒」だけは虎の手順にもある（脚を角筒に）ので、御来迎の部品の名で見る
        assert word not in tora, ("虎に御来迎の紙の字が渡った", word)
    assert f"凡例: {kasane.legend(T)}" in tora and kasane.template_of(T) != kasane.FAN
    goraigo_words = kasane.context_of(G)[0]
    assert "色の境" in kasane.legend(G) and "色の境" not in kasane.legend(T) and goraigo_words.count("凡例: ") == 1, "色の境で折る事は扇の紙だけ"
    from omochae import compose  # noqa: E402
    for sid in (G, T):
        tpl = compose.TEMPLATES[kasane.template_of(sid)]
        valley = (compose.FOLD_WORDS if compose.new_fold_words(tpl) else compose._OLD_SHEET_FOLD_WORDS)[0]
        assert valley in kasane.legend(sid), ("凡例はその紙が刷る谷と山の言い方", sid)
        # 位置の印は、その紙に印がある時だけ凡例に入る（compose が凡例に足すのと同じ見分け・別の目の気づき 11-08）
        hs = hypotheses.sheet_of(sid)
        marks = any(i["kind"] == "mark" for q in tpl.parts({**tpl.DEFAULTS, **(hs.get("params") or {})}) for i in q.art)
        assert ("位置の印（切らない・折らない）" in kasane.legend(sid)) is marks, ("位置の印の有り無しが紙と同じ", sid, marks)
    server.listener.reply = "谷折りって何"
    assert post(base, body(), sid=G)[1]["from"] == "glossary", "御来迎の語の問いは前のとおり語の表で答える"
    server.listener.reply = "谷折りはどこを折りますか"
    # 仮説の名前が混ざった答えは断りに替える
    client.answer = f"これは {h.get('name') or '仮説'} です"
    assert post(base, body()) == (200, {"text": ask.REFUSE, "from": "refuse"})
    client.answer = "破線の所を、手前にへこむように折ってください。"
    # 失敗の記録に問いの字が無い（API の文に問いが混ざっても伏せる）
    client.error = RuntimeError("谷折りはどこを折りますか")
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert post(base, body())[1] == {"text": "今は AI に聞けません", "from": "error"}
    assert "谷折り" not in err.getvalue() and "kasane" in err.getvalue(), err.getvalue()
    client.error = None
    # 費用の止め
    real_check = budget.check
    budget.check = lambda *a, **k: (_ for _ in ()).throw(budget.BudgetStop("止め", "day"))
    try:
        assert post(base, body())[1] == {"text": f"今は AI に聞けません（{budget.BudgetStop.NOTES['day']}）", "from": "stop"}
    finally:
        budget.check = real_check
    # 同じ相手から 1 分に 6 回まで（手元から直に来た物は数えない決まりなので、トンネルの見出しで相手を名乗る）
    codes = [post(base, body(), who="203.0.113.7")[0] for _ in range(play_server.ASK_LIMIT + 1)]
    assert codes[:play_server.ASK_LIMIT] == [200] * play_server.ASK_LIMIT and codes[-1] == 429, codes
    assert post(base, body(), who="203.0.113.8")[0] == 200, "ほかの相手は数えが別"
    # 場の全体の 1 日の数。形の悪い送り物は数えない（形を確かめた後に数える・別の目の気づき 11-08）
    server.ask_day = play_server.DayCount(limit=1)
    assert post(base, body(frames=4))[0] == 422 and post(base, b"{not json")[0] == 422, "形の悪い送り物は断る"
    assert post(base, body())[0] == 200, "形の悪い送り物で 1 日の数を使っていない"
    assert post(base, body()) == (429, {"text": play_server.BUSY, "from": "busy"})
    # 3. 記録を取らない
    assert CALLED == [], CALLED
    after = files()
    assert after == before, ("記録の置き場に何も増えない", set(after) - set(before))
    ledger = pathlib.Path(os.environ["OMOCHAE_USAGE_LEDGER"]).read_text(encoding="utf-8")
    assert '"role": "kasane"' in ledger and "谷折り" not in ledger and "破線" not in ledger, "費用の台帳は数と額だけ"
finally:
    server.shutdown()
    server.server_close()
print(f"ok 作業の頁の聞く口: 声はこのサーバの中で字にし、写真 3 枚までと今の手順の字で答え、何も残さない{ffmpeg_note}")
