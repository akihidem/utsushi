"""声とカメラの区切りの受け口と読み（声とカメラの区切りの設計 3 版の 3・5 節。web.play_server._clip_post・api.clip_read・omochae.media_review）。

なぜ: 本人 330・412・415「声も送って解析に使う形にする。カメラの映像は、押した時の短い区切りだけ。」。区切りは見出し X-Utsushi-Clip で渡し、
今の写真と動画の口の照らしを全部通した後で、save_media と claim の前で分ける（統括の決め (3)）。カメラの区切りの読みは人の操作の後に 1 回だけで、
人の言葉が先（のこすの工夫・感想）・鍵・1 日の回数・予算の止めを通る。公開の場は学ぶ人の操作では読まず、進め役が確かめた時だけ読む。
見る事:
1. 受け口の分かれ: 見出し付きは voice/ に置かれ、m<n> と claim の控え（owners.json）が増えない／見出しなしは今のまま／値と型の組に無い物は 422／
   見出し付きでも、外の Origin・記録の鍵なし・公開の場の合計越えは今と同じ断り
2. 合言葉付きの場（公開でない場）: カメラの区切りが届くと読みが 1 回だけ走る。付帯情報（手順・釦）が係へ渡る。答えは「案」で残り、区切りは消える
3. 読みの門: 工夫も感想も無い記録の区切りは読まない（説明待ち）・鍵が無い・1 日の回数・予算の止めで読まず理由を控える・人が写っていたら字を残さず消す
4. 公開の場: 学ぶ人の操作（受け口）では読まない。進め役の命令の道（media_review）に並び、端末の確かめが無いと進まない
終了: 0 = 通る / 1 = 落ちる（assert）/ 4 = ffmpeg が無い（確かめられない）
"""
import http.cookiejar
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

if not shutil.which("ffmpeg"):
    print("検査できない: ffmpeg が無い", file=sys.stderr)
    sys.exit(4)

from PIL import Image  # noqa: E402

from api import ask, budget, clip_read  # noqa: E402
from omochae import hypotheses, media_review, records, voice_text  # noqa: E402
from web import play_server  # noqa: E402


def clip(ext, video=True, seconds=2):
    """作り物の区切り（声は sine・カメラは testsrc）。"""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, f"c.{ext}")
        ins, codecs = [], []
        if video:
            ins += ["-f", "lavfi", "-i", f"testsrc=size=64x48:rate=5:duration={seconds}"]
            codecs += ["-c:v", "libvpx"] if ext == "webm" else ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
        else:
            ins += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]
            codecs += ["-c:a", "libopus"] if ext == "webm" else ["-c:a", "aac"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, *codecs, "-f", ext, out], check=True, capture_output=True, timeout=120)
        return open(out, "rb").read()


class Stay(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kw):
        return None


def site(**kw):
    s = play_server.serve(0, **kw)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


G = "NDL-1187053-R0000005-L"
H = hypotheses.sheet_of(G)["id"]
form = lambda d: urllib.parse.urlencode(d).encode()


class Client:
    """偽の係: 呼ばれた中身を控え、決めた答えを返す。"""

    def __init__(self, answer):
        self.answer, self.seen = answer, []
        self.messages = types.SimpleNamespace(create=self.create)

    def create(self, **kw):
        self.seen.append(kw)
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text=json.dumps(self.answer, ensure_ascii=False))],
                                     usage=types.SimpleNamespace(input_tokens=2000, output_tokens=200))


# 受け口が走らせる読みを、試験では同じ糸で控える（本物の係は呼ばない）
started = []
clip_read.read_later = lambda rid, name, factory: started.append((rid, name))


def session(base):
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), Stay)

    def call(path, body=None, ctype="application/x-www-form-urlencoded", origin=None, headers=None):
        h = {"Origin": origin or base, "Content-Type": ctype, **(headers or {})} if body is not None else {}
        r = urllib.request.Request(base + path, data=body, headers=h)
        try:
            with op.open(r) as x:
                return x.status, x.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
    return call


def new_record(call, impression="扇がよく開いた"):
    assert call(f"/toy/{G}/print", form({"hypothesis": H}))[0] in (200, 303)
    code, body = call(f"/toy/{G}/record-json", form({"hypothesis": H, "result": records.results_for(G)[0], "impression": impression}))
    return json.loads(body)["id"]


# ---- 1・2 合言葉付きの場（公開でない場）の受け口
server, base = site()
call = session(base)
rid = new_record(call)
cam = clip("webm")
code, name = call(f"/record/{rid}/media", cam, "video/webm", headers={"X-Utsushi-Clip": "k", "X-Utsushi-Step": "4", "X-Utsushi-Button": "stuck"})
assert code == 201 and name == "k1.webm", (code, name)
assert started == [(rid, "k1.webm")], "カメラの区切りが届くと、読みが 1 回だけ走る（人の操作＝承認の後）"
code, tname = call(f"/record/{rid}/media", clip("webm", video=False), "audio/webm", headers={"X-Utsushi-Clip": "t"})
assert code == 201 and tname == "t1.mka" and len(started) == 1, (code, tname, "声の区切りは読みを走らせない（この機械の中で字にする）")
media = records.folder() / "media" / rid
assert not list(media.glob("m*.*")) and not (media / "owners.json").exists(), "区切りは m<n> と確かめる前の並び（claim）に入れない"
assert sorted(p.name for p in (media / "voice").glob("[tk]1.*")) == ["k1.webm", "t1.mka"]
for headers, ctype, why in (({"X-Utsushi-Clip": "x"}, "video/webm", "値"), ({"X-Utsushi-Clip": "k"}, "audio/webm", "型"),
                            ({"X-Utsushi-Clip": "t"}, "video/mp4", "型"), ({"X-Utsushi-Clip": "k"}, "image/png", "型")):
    assert call(f"/record/{rid}/media", cam, ctype, headers=headers)[0] == 422, why
assert call(f"/record/{rid}/media", cam, "video/webm", origin="https://example.com", headers={"X-Utsushi-Clip": "k"})[0] == 403, "外の Origin"
other = session(base)
assert other(f"/record/{rid}/media", cam, "video/webm", headers={"X-Utsushi-Clip": "k"})[0] == 403, "記録の鍵の無い画面からは受けない"
buf = io.BytesIO()
Image.effect_noise((32, 24), 40).convert("RGB").save(buf, "PNG")
code, m1 = call(f"/record/{rid}/media", buf.getvalue(), "image/png")
assert code == 201 and m1 == "m1.png" and (media / "owners.json").exists(), "見出しなしは今のまま（写真の口）"
meta = json.loads((clip_read.loop.folder() / f"clip-meta-{rid}.json").read_text(encoding="utf-8"))
assert meta == {"k1.webm": {"step": 4, "button": "stuck"}}, meta
server.shutdown()

# ---- 2・3 読みの段（偽の係で）
ask._key_present = lambda: True
ok = Client({"observed": ["左手で 2 の受けを持ち、扇の端が貼れずに浮いている"], "unclear": ["のりの量"], "person": False})
result, why = clip_read.read(rid, "k1.webm", ok)
assert result and why == "" and len(ok.seen) == 1, why
sent = ok.seen[0]["messages"][0]["content"]
assert sum(1 for c in sent if c["type"] == "image") == 3 and "手順 4 で押した区切り" in sent[-1]["text"], "3 コマと付帯情報"
assert "k1.webm" not in voice_text.clips_waiting(rid) and not (media / "voice" / "k1.webm").exists(), "読んだら区切りは消える"
obs = clip_read.observations(rid)
assert obs[0]["clip"] == "k1.webm" and obs[0]["step"] == 4 and "案" in obs[0]["label"], obs
assert clip_read.count_today() == 1, "台帳の role clip で数える"

# 工夫も感想も無い記録の区切りは読まない（説明待ち）
plain = records.add({"source_id": G, "hypothesis_id": H, "sheet_version": 1, "result": records.results_for(G)[0]})[0]
assert voice_text.put_cam_clip(plain, cam, "webm")[0] == "k1.webm"
never = Client({"observed": [], "unclear": [], "person": False})
assert clip_read.read(plain, "k1.webm", never) == (None, "説明待ち") and not never.seen and "k1.webm" in voice_text.clips_waiting(plain)
# 鍵が無い・1 日の回数
ask._key_present = lambda: False
assert clip_read.read(rid, voice_text.put_cam_clip(rid, cam, "webm")[0], never)[1] == "鍵が無い" and not never.seen
ask._key_present = lambda: True
keep_daily = clip_read.CLIP_DAILY
clip_read.CLIP_DAILY = 1
assert clip_read.read(rid, "k2.webm", never)[1] == "今日の上限" and not never.seen, "区切りの読みだけの 1 日の回数の止め"
clip_read.CLIP_DAILY = keep_daily
# 予算の止め（日割りに当たると読まずに待つ）
keep_check = budget.check
budget.check = lambda *a: (_ for _ in ()).throw(budget.BudgetStop("止め", "day"))
assert clip_read.read(rid, "k2.webm", never)[1] == budget.BudgetStop.NOTES["day"] and not never.seen
budget.check = keep_check
# 人が写っていたら、字を残さず区切りごと消す
seen_person = Client({"observed": ["顔が見える"], "unclear": [], "person": True})
assert clip_read.read(rid, "k2.webm", seen_person) == (None, "人が写っていた")
assert "k2.webm" not in voice_text.clips_waiting(rid) and len(clip_read.observations(rid)) == 1, "字を残さない"
# 成否の言葉の入った答えは出さない
bad = Client({"observed": ["失敗している"], "unclear": [], "person": False})
assert clip_read.read(rid, voice_text.put_cam_clip(rid, cam, "webm")[0], bad)[1] == "成否や点の言葉が入っていた"

# ---- 4 公開の場: 受け口では読まず、命令の道に並ぶ
started.clear()
pub, pbase = site(public_open=True)
pcall = session(pbase)
prid = new_record(pcall)
code, pname = pcall(f"/record/{prid}/media", cam, "video/webm", headers={"X-Utsushi-Clip": "k"})
assert code == 201 and started == [], "公開の場は学ぶ人の操作では読まない（J-028）"
assert pcall(f"/record/{prid}/media", clip("mp4", video=False), "audio/mp4", headers={"X-Utsushi-Clip": "t"})[0] == 201, "公開の場でも声を録る（本人 11-08）"
pub.shutdown()
waiting = media_review.clips_waiting()
assert (prid, f"voice/{pname}", "") in waiting, waiting
assert media_review.main(["approve", prid, f"voice/{pname}", "--shows", "object", "--reviewer", "進め役"]) == 3, "端末の人の確かめが無いと進まない"
assert pname in voice_text.clips_waiting(prid)
assert media_review.main(["frames", prid, f"voice/{pname}"]) == 0
assert media_review.main(["approve", prid, "voice/k9.webm", "--shows", "object", "--reviewer", "進め役"]) == 3, "無い区切りは断る"
print("ok: 区切りは見出しで受け、照らしの後で分ける・読みは人の操作の後に 1 回・人の言葉が先・止めで待つ・公開の場は進め役の確かめの後")
