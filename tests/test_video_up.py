"""動画を上げる専用の口（本人の指示 11-05、#337）。合言葉付きのリンクから開き、複数の動画を上げると、撮影の情報と音を外し、試行の動画の入口を通して改善の輪へ回す。
上げた人には受付番号と状態が見える。本物の人の動画は使わない（作り物を ffmpeg で作る）。ffmpeg が無い機械では 4（検査できない）で終わる。

見る線: 合言葉なしでは何も見せない／別の出所から送らせない／音と撮影の情報が残らない／動画でない物は記録にしない（再生リストを読ませない）／
上げた動画と文は学ぶ人の頁・ギャラリー・束に出ない／取り下げで動画もコマも札も消える／止まっても小分けから続きができる。
"""
import hashlib
import http.client
import io
import json
import math
import os
import pathlib
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_DATA"] = str(tmp)
os.environ["OMOCHAE_SAMPLES"] = "0"

if not shutil.which("ffmpeg"):  # 確かめられない時は 4（repo の決まり。通った事にしない）
    print("検査できない: ffmpeg が無い", file=sys.stderr)
    sys.exit(4)

from PIL import Image  # noqa: E402

from omochae import asr_worker, engine_bundle, gallery, hypotheses, loop, records, trial_video as tv  # noqa: E402
from web import video_up  # noqa: E402
from web.play_server import serve as site_serve  # noqa: E402
from web.toys import sources  # noqa: E402

KEY = "test-key-0123456789abcdef"
G = "NDL-1187053-R0000005-L"  # 御来迎（札に「わからない」がある）
TORA = "NDL-1187053-R0000014-R"  # 張子の首振り虎（札に「わからない」が無い）
PLACE = "+35.6000+139.7000"
CHUNK = video_up.CHUNK = 64 * 1024  # 試験では小さく分ける
assert "わからない" not in records.results_for(TORA) and "わからない" in records.results_for(G)

# 合言葉が無いサーバは立たない
for bad in ("", None, "short"):
    try:
        video_up.serve(0, bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"合言葉 {bad!r} で立った")

srv = video_up.serve(0, KEY)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]
assert srv.server_address[0] == "127.0.0.1", "口は手元だけ。外からはトンネルだけが入る"
HOST, ORIGIN, JAR = f"127.0.0.1:{port}", f"http://127.0.0.1:{port}", f"{video_up.COOKIE}={KEY}"


SAME = object()


def call(method, path, body=None, cookie=JAR, host=None, origin=SAME, target=None):
    c = http.client.HTTPConnection("127.0.0.1", target or port, timeout=60)
    headers = {"Host": host or HOST}
    origin = ORIGIN if origin is SAME else origin
    if cookie:
        headers["Cookie"] = cookie
    if origin:
        headers["Origin"] = origin
    c.request(method, path, body=body, headers=headers)
    r = c.getresponse()
    data = r.read()
    c.close()
    return r.status, data, dict(r.getheaders())


def post(path, obj, **kw):
    return call("POST", path, body=json.dumps(obj).encode(), **kw)


def form(**kw):
    return {"toy": G, "made_with": "sheet", "note": "", "agree_people": True, "agree_adult": True, **kw}


def send(data, uid=None, chunks=True, **kw):
    """本物の頁と同じ順に送る。Returns (状態の番号, 返事)。"""
    uid = uid or hashlib.sha256(data).hexdigest()[:32]
    count = math.ceil(len(data) / CHUNK)
    if chunks:
        for n in range(count):
            code, body, _ = call("POST", f"/chunk?id={uid}&n={n}", body=data[n * CHUNK:(n + 1) * CHUNK])
            assert code == 200, (code, body)
    code, body, _ = post("/finish", {**form(**kw), "id": uid, "chunks": count, "size": len(data)})
    return code, json.loads(body)


def status(*tokens):
    code, body, _ = call("GET", "/status?t=" + ",".join(tokens))
    assert code == 200, code
    return json.loads(body)


def wait(token):
    """受け取りが終わるまで待つ。今の状態の字を返す。"""
    for _ in range(600):
        now = status(token)[token]
        if now["state"] not in ("waiting", "working"):
            return now
        time.sleep(0.1)
    raise AssertionError(f"終わらない: {now}")


def video(name, audio=True):
    """音と撮影の情報が入った作り物。入っていないと、外した事を確かめられない。"""
    out = tmp / name
    sound = ["-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-c:a", "aac"] if audio else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=5:duration=3", *sound, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-metadata", "title=secret-place", "-metadata", f"comment={name}", "-metadata", f"com.apple.quicktime.location.ISO6709={PLACE}+010.000/", "-metadata", "creation_time=2026-11-04T09:00:00Z",
                    "-metadata:s:v:0", "creation_time=2026-11-04T09:00:00Z", "-movflags", "use_metadata_tags", str(out)], check=True, capture_output=True, timeout=120)
    data = out.read_bytes()
    assert b"secret-place" in data and PLACE.encode() in data, "作り物に撮影の情報が入っていない"
    return data


# 本人が採った文（11-05）。一字も変えない
ADOPTED = (
    "動画を送る",
    "『江都二色』のおもちゃを作った時の動画を送る頁です。型紙のたたき台を直すために使います。",
    "音と、いつ・どこでとったかなどの情報は、受け取る時に自動で消します。",
    "声と動画そのものは、サイトの頁に出しません。切り出した絵（紙と手の所）と、話した言葉の一部を、名前などを除いて、サイトに載せる事があります。載せる前に人が見ます。",
    "動画から切り出した絵を、作る側の人と AI（Claude）が読みます。見るのは、手が止まった所と工夫した所です。",
    "型紙を直すかどうかは、人が決めます。作った人の出来に点は付けません。",
    "取り下げたい時は、受付番号を、リンクを渡した人に伝えてください。動画も切り出した絵も消します。",
    "どのおもちゃですか",
    "何を見て作りましたか",
    "うつしの型紙",
    "自分のやり方",
    "動画（いくつでも選べます）",
    "この動画で伝えたい事（なくてもかまいません）",
    "名前は書かないでください。住所・電話番号・メールも書かないでください。",
    "とった人と、映っている人の許しをもらっています。",
    "私は 18 歳以上です。子どもは映っていません。",
    "送っている間は、この頁を開いたままにしてください。途中で切れたら、同じ動画を選んで、もう一度「送る」を押してください。続きから送ります。",
    "受け取りました。音と、いつ・どこでとったかなどの情報を消しました。",
    "読み取れませんでした。MP4 か MOV の動画か確かめて、もう一度送ってください。",
)

REVIEW_ADOPTED = (
    "型紙のレビューの動画を送る",
    "『江都二色』のおもちゃの型紙を、作る前に見て話した動画を送る頁です。型紙のたたき台を直すために使います。",
    "いつ・どこでとったかなどの情報は、受け取る時に自動で消します。",
    "声は、字にして整理するために、この機械の中にだけ置きます。整理が終わったら消します。",
    "声と動画そのものは、サイトの頁に出しません。切り出した絵（紙と手の所）と、話した言葉の一部を、名前などを除いて、サイトに載せる事があります。載せる前に人が見ます。",
    "字にした言葉と、動画から切り出した絵を、作る側の人と AI（Claude）が読みます。見るのは、型紙のどこをどう直すとよいかです。",
    "型紙を直すかどうかは、人が決めます。話した人に点は付けません。",
    "取り下げたい時は、受付番号を、リンクを渡した人に伝えてください。動画も声も字も消します。",
    "どのおもちゃの型紙ですか",
)

# 門: 合言葉なしでは頁も玩具の名前も見せない。合言葉は Cookie に移して URL から消す
code, body, _ = call("GET", "/", cookie=None)
assert code == 403 and "御来迎".encode() not in body and b"<script" not in body
assert call("GET", "/?k=wrong", cookie=None)[0] == 403
assert call("GET", "/", cookie=f"{video_up.COOKIE}=wrong")[0] == 403
buf, keep = io.StringIO(), sys.stderr
sys.stderr = buf
code, _, headers = call("GET", f"/?k={KEY}", cookie=None)
sys.stderr = keep
assert code == 303 and headers["Location"] == "/" and KEY not in headers["Location"]
assert KEY in headers["Set-Cookie"] and all(w in headers["Set-Cookie"] for w in ("HttpOnly", "Secure", "SameSite=Lax"))
assert KEY not in buf.getvalue() and buf.getvalue() == "", "合言葉も、誰が来たかも記録に残さない"
for method, path in (("POST", "/chunk?id=" + "a" * 32 + "&n=0"), ("POST", "/finish"), ("POST", "/check"), ("GET", "/status?t=" + "a" * 32), ("GET", "/have?id=" + "a" * 32), ("GET", f"/picture/{G}")):
    assert call(method, path, body=b"{}" if method == "POST" else None, cookie=None)[0] == 403, path
assert call("POST", f"/finish?k={KEY}", body=b"{}", cookie=None)[0] == 403, "合言葉は最初の GET でだけ受ける"
assert call("GET", f"//evil.example/?k={KEY}", cookie=None)[2]["Location"] == "/", "飛び先は頁の頭だけ"
# 別の名前・別の出所からは受けない。トンネルの名前は受ける
assert call("GET", "/", host="evil.example")[0] == 403
assert post("/check", form(), origin="https://evil.example")[0] == 403
assert post("/check", form(), origin=None)[0] == 403
assert post("/check", form(), host="evil.example", origin="http://evil.example")[0] == 403, "POST も名前を見る"
tunnel = "abc-def.trycloudflare" + ".com"  # 作り物の名前。門がトンネルの名前の形を落とすので、字の並びを分ける（tests/test_public_open.py と同じ）
assert call("GET", "/", host=tunnel, origin=None)[0] == 200
assert post("/check", form(), host=tunnel, origin=f"https://{tunnel}")[0] == 200
assert post("/check", form(), host=tunnel, origin=f"http://{tunnel}")[0] == 403, "トンネルの先は https だけ"
# サイトのほかの頁は無い
for path in ("/toys", "/gallery", f"/toy/{G}", "/about", f"/record/R-0001/media/m1.jpg", "/../../etc/passwd"):
    assert call("GET", path)[0] == 404, path

# 頁: 選ぶおもちゃ・複数の動画・約束の文・同意の 2 つ
code, body, headers = call("GET", "/", origin=None)
page = body.decode()
assert code == 200 and KEY not in page
for line in ADOPTED[:-2]:
    assert line in page, line
assert video_up.WORDS["done"] == ADOPTED[-2] and video_up.WORDS["failed"] == ADOPTED[-1]
assert page.count("<option") == len(sources()) + 1 and f'value="{G}"' in page and "御来迎" in page and "張子の首振り虎" in page
assert page.index("御来迎") < page.index("竹登り猿"), "並びは、おもちゃの一覧の頁と同じ"
assert 'type="file"' in page and " multiple" in page and 'accept="video/*"' in page
assert f"CHUNK={CHUNK}" in page and "http://" not in page and "https://" not in page, "外の部品を読まない"
assert "no-store" in headers["Cache-Control"] and headers["Referrer-Policy"] == "no-referrer" and headers["X-Content-Type-Options"] == "nosniff"
csp = headers["Content-Security-Policy"]
assert "default-src 'none'" in csp and "frame-ancestors 'none'" in csp and "connect-src 'self'" in csp
nonce = csp.split("script-src 'nonce-")[1].split("'")[0]
assert f'<script nonce="{nonce}">' in page and page.count("<script") == 1
assert nonce not in call("GET", "/", origin=None)[2]["Content-Security-Policy"], "印は毎回変える"
# 図があれば見られる。形の外は読まない
if (video_up.ROOT / "out/sources" / f"{G}.jpg").exists():
    code, body, headers = call("GET", f"/picture/{G}", origin=None)
    assert code == 200 and body[:2] == b"\xff\xd8" and headers["Content-Type"] == "image/jpeg"
assert call("GET", "/picture/..%2F..%2Fsecret", origin=None)[0] == 404 and call("GET", "/picture/NDL-1187053-R9999999-L", origin=None)[0] == 404

# 送る前の確かめ。同じ確かめが受け取りでも働く。何も残らない
folder = video_up.folder()
for bad, word in ((form(toy="NDL-nope"), "おもちゃ"), (form(made_with="x"), "作りましたか"), (form(agree_people=False), "許し"), (form(agree_adult=False), "18 歳"), (form(agree_adult="yes"), "18 歳"),
                  (form(toy=[]), "おもちゃ"), (form(made_with=[]), "作りましたか"), (form(note="\ud83d"), "伝えたい"), (form(note="\x1b]0;x\x07"), "伝えたい"), (form(note="a\x85b"), "伝えたい"),
                  (form(note="電話は 090-1234-5678 です"), "電話番号"), (form(note="連絡は a@example.com まで"), "メール"), (form(note="字" * (video_up.NOTE_MAX + 1)), "長"), (form(note=5), "伝えたい")):
    code, body, _ = post("/check", bad)
    assert code == 422 and word in json.loads(body)["error"], (bad, body)
    code, body, _ = post("/finish", {**bad, "id": "b" * 32, "chunks": 1, "size": 1})
    assert code == 422 and word in json.loads(body)["error"], (bad, body)
assert post("/check", form())[0] == 200 and call("POST", "/check", body=b"not json")[0] == 400 and call("POST", "/check", body=b"[1]")[0] == 400
assert not list(folder.glob("U-*.json")), "断った物の受付は作らない"
assert stat.S_IMODE(folder.stat().st_mode) == 0o700, "置き場は本人だけが読める"

# 小分けの口: 形の外と大きすぎる物は受けない
uid = "c" * 32
for path in (f"/chunk?id=short&n=0", f"/chunk?id={'g' * 32}&n=0", f"/chunk?id=..%2F..%2Fx&n=0", f"/chunk?id={uid}", f"/chunk?id={uid}&n=-1", f"/chunk?id={uid}&n=x", f"/chunk?id={uid}&n={video_up.MAX_FILE // CHUNK + 1}"):
    assert call("POST", path, body=b"x")[0] == 400, path
assert call("POST", f"/chunk?id={uid}&n=0", body=b"x" * (CHUNK + 1))[0] == 413
assert call("POST", f"/chunk?id={uid}&n=0", body=b"")[0] == 400, "空の小分けを受けない"
# 空きが足りない時は受けない（ほかの作業の置き場を埋めない）
floor, video_up.MIN_FREE = video_up.MIN_FREE, 10 ** 18
code, body, _ = call("POST", f"/chunk?id={uid}&n=0", body=b"x")
video_up.MIN_FREE = floor
assert code == 507 and "error" in json.loads(body)
assert not (folder / "tmp" / uid).exists() or not list((folder / "tmp" / uid).iterdir())

# 途中で切れた小分けは、届いた物に数えない
cut_id = "9" * 32
raw_sock = socket.create_connection(("127.0.0.1", port), timeout=30)
raw_sock.sendall((f"POST /chunk?id={cut_id}&n=0 HTTP/1.1\r\nHost: {HOST}\r\nCookie: {JAR}\r\nOrigin: {ORIGIN}\r\nContent-Length: 100\r\n\r\n").encode() + b"x" * 10)
raw_sock.close()
for _ in range(100):
    if not [p for p in (folder / "tmp" / cut_id).glob("*")] and (folder / "tmp" / cut_id).exists():
        break
    time.sleep(0.05)
assert json.loads(call("GET", f"/have?id={cut_id}", origin=None)[1]) == {"have": []}
assert not list((folder / "tmp" / cut_id).glob("*")), "途中の物を残さない"
(folder / "tmp" / cut_id).rmdir()

# 足りない小分けは番号で答える。受け取りにしない。続きの番号も聞ける
data = video("a.mov")
uid = hashlib.sha256(data).hexdigest()[:32]
count = math.ceil(len(data) / CHUNK)
assert count >= 1 and json.loads(call("GET", f"/have?id={uid}", origin=None)[1]) == {"have": []}
assert call("POST", f"/chunk?id={uid}&n={count - 1}", body=data[(count - 1) * CHUNK:])[0] == 200
assert json.loads(call("GET", f"/have?id={uid}", origin=None)[1]) == {"have": [count - 1]}
if count > 1:
    code, body = send(data, chunks=False)
    assert code == 409 and body["missing"] == list(range(count - 1))
assert call("GET", "/have?id=short", origin=None)[0] == 400
for n in range(count - 1):
    call("POST", f"/chunk?id={uid}&n={n}", body=data[n * CHUNK:(n + 1) * CHUNK])
code, body, _ = post("/finish", {**form(), "id": uid, "chunks": count, "size": len(data) + 1})
assert code == 422 and "大きさ" in json.loads(body)["error"], "大きさが合わない物を受け取りにしない"
code, body, _ = post("/finish", {**form(), "id": uid, "chunks": count, "size": video_up.MAX_FILE + 1})
assert code == 413, "大きすぎる物"
assert post("/finish", {**form(), "id": uid, "chunks": 10 ** 12, "size": 1})[0] == 400, "小分けの数の上限（足りない番号の一覧で機械を止めない）"
assert post("/finish", {**form(), "id": uid, "chunks": True, "size": 1})[0] == 400
assert not list(folder.glob("U-*.json"))

# 1 本目: 音と撮影の情報を外して、記録に結び、コマの一覧を作る。元の小分けは残さない
WORDS = "蛇腹の 3 枚目で手が止まりました"
code, first = send(data, chunks=False, note=WORDS)
assert code == 200 and first["receipt"] == "U-0001" and len(first["token"]) == 32, first
seen = wait(first["token"])
assert seen["state"] == "done" and seen["receipt"] == "U-0001" and seen["word"] == video_up.WORDS["done"], seen
slip = json.loads((folder / "U-0001.json").read_text(encoding="utf-8"))
rid = slip["record"]
assert slip["source_id"] == G and slip["state"] == "done"
assert not ({"name", "filename", "file", "ip", "address", "agent", "user_agent"} & set(slip)), "ファイルの名前と、誰が上げたかを残さない"
assert "a.mov" not in json.dumps(slip)
assert not list((folder / "tmp").iterdir()), "上げた元は消す"
rec = loop.record(rid)
assert rec["via"] == records.UPLOADED and rec["result"] == "わからない" and rec["hypothesis_id"] == hypotheses.sheet_of(G)["id"] and rec["sheet_set"].startswith("goraigo-v")
assert rec["sheet_version"] == 1 and WORDS in rec["note"] and not rec.get("impression"), "上げた人の文は感想の欄に入れない（感想はギャラリーに出る）"
stored = tv._base(rid) / "v1.mp4"
raw = stored.read_bytes()
assert b"secret-place" not in raw and PLACE.encode() not in raw and b"2026-11-04" not in raw
probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(stored)], capture_output=True, text=True, check=True).stdout)
assert {s["codec_type"] for s in probe["streams"]} == {"video"}, "音を落とす"
tags = json.dumps([probe["format"].get("tags", {}), *[s.get("tags", {}) for s in probe["streams"]]])
assert "creation_time" not in tags and "location" not in tags and "secret" not in tags, tags
item = tv.load(rid)["videos"][0]
assert item["file"] == "v1.mp4" and not item["checked_by"], "顔と声の確かめは人がする。受け口は確かめた事にしない"
sheet = tv._base(rid) / "frames" / "sheet-v1.png"
assert sheet.exists() and Image.open(sheet).size[0] > 0, "読むためのコマの一覧"
assert (tv._base(rid) / "frames" / "v1-000000.jpg").exists()

# 同じ物を送り直しても、受付は増えない（返事が届かなかった時のやり直し）。受付番号では状態を読めない。送る前に聞けば、中身を送らずに済む
code, again = send(data, chunks=False, note=WORDS)
assert code == 200 and again == first
assert json.loads(call("GET", f"/have?id={uid}&toy={G}", origin=None)[1]) == {"have": [], **first}
assert json.loads(call("GET", f"/have?id={uid}&toy={TORA}", origin=None)[1]) == {"have": []}
assert call("GET", "/status?t=U-0001")[0] == 400
assert status("d" * 32) == {}
assert len(list(folder.glob("U-*.json"))) == 1 and len(records.all_records(uploads=True)) == 1

# 複数: 2 本目は別の受付・別の記録。札に「わからない」が無い玩具でも受ける。自分のやり方で作った時は、読む人に分かるように文の頭に残す
code, second = send(video("b.mp4"), toy=TORA, made_with="own", note="首の糸を太くしました" + "字" * (video_up.NOTE_MAX - 10))
assert code == 200 and second["receipt"] == "U-0002", second
assert wait(second["token"])["state"] == "done"
r2 = json.loads((folder / "U-0002.json").read_text(encoding="utf-8"))["record"]
rec2 = loop.record(r2)
assert r2 != rid and rec2["source_id"] == TORA and rec2["result"] == "わからない" and rec2["note"].startswith(video_up.MADE_WITH["own"]) and "首の糸を太くしました" in rec2["note"]
assert "moved" not in tv.report(r2, True)[0], "動いたかは決めつけない"
assert not rec["note"].startswith(video_up.MADE_WITH["own"])
# 同じ動画でも、玩具を選び直せば別の受付になる（選び間違いの送り直し）
code, third = send(data, toy=TORA)
assert code == 200 and third["receipt"] == "U-0003"
assert wait(third["token"])["state"] == "done"
got = status(first["token"], second["token"], "e" * 32)
assert set(got) == {first["token"], second["token"]}, "知らない印は答えない"
assert call("GET", "/status?t=" + ",".join(["e" * 32] * 201))[0] == 400, "一度に聞ける数は決めておく"

# 動画でない物: 記録を作らず、断る。元も残さない。再生リストを動画として読ませない（中の道を ffmpeg が開いてしまう）
before = len(records.all_records(uploads=True))
for junk in (b"just text, not a video" * 10, b"#EXTM3U\n#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:1.0,\nfile:///etc/passwd\n#EXT-X-ENDLIST\n", b"ffconcat version 1.0\nfile /etc/passwd\n", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200):
    code, slip_bad = send(junk)
    assert code == 200, slip_bad
    seen = wait(slip_bad["token"])
    assert seen["state"] == "failed" and seen["word"] == video_up.WORDS["failed"], (junk[:20], seen)
assert len(records.all_records(uploads=True)) == before
assert not list((folder / "tmp").iterdir())
# 読めなかった物は送り直せる（受付の番号は新しくなる）
code, retry = send(b"just text, not a video" * 10)
assert code == 200 and retry["receipt"] != slip_bad["receipt"]
wait(retry["token"])

# 学ぶ人の頁・ギャラリー・束には、上げた動画も文も記録も出ない（上げた人への約束）
site = site_serve(0)
threading.Thread(target=site.serve_forever, daemon=True).start()
site_port = site.server_address[1]


def site_get(path):
    code, body, _ = call("GET", path, cookie=None, origin=None, host=f"127.0.0.1:{site_port}", target=site_port)
    return code, body.decode(errors="replace")


for path in (f"/toy/{G}", f"/toy/{TORA}", "/gallery", f"/zukan/{G}", f"/toy/{G}/techo", f"/toy/{TORA}/techo"):
    code, text = site_get(path)
    assert code == 200, path
    for word in ("v1.mp4", WORDS, "首の糸を太くしました", rid, r2):
        assert word not in text, (path, word)
assert site_get(f"/record/{rid}/media/v1.mp4")[0] == 404 and site_get(f"/record/{rid}/media/frames/v1-000000.jpg")[0] == 404
assert records.all_records(G) == [] and {r["id"] for r in records.all_records(G, uploads=True)} == {rid}
assert rid not in gallery.build() and WORDS not in gallery.build()
assert WORDS not in json.dumps(engine_bundle.build(), ensure_ascii=False)
assert tv.effect(G)["H-A"]["reports"], "版の輪の表には数える"

# 上げた記録はサイトの口で触れない。前例の読みにも出ない（上げた人の文を AI の道具に渡さない）
c = http.client.HTTPConnection("127.0.0.1", site_port, timeout=60)
c.request("POST", f"/record/{rid}/explain", body=b"by=x&text=y&next_idea=z", headers={"Host": f"127.0.0.1:{site_port}", "Origin": f"http://127.0.0.1:{site_port}", "Content-Type": "application/x-www-form-urlencoded"})
assert c.getresponse().status == 404 and not loop.explanation(rid)
c.close()
assert loop.confirm_interpretation(rid, "確かめた人", "読み") == [] and loop.confirmed_records(G) == [], "受け口の記録は前例にしない"
loop.interp_path(rid).unlink()
site.shutdown()

# 改善の輪へ回る: 札 → 人の確かめ → 人の説明 → 案。エンジンの報告の形で渡せる。分は整数（エンジンの検査が整数だけを通す）
m1, fails = tv.add_mark(rid, 1, 8, "fold", "蛇腹で手が止まった", "読み手")
assert m1 and not fails, fails
assert not tv.judge_mark(rid, m1, "確かめた人") and not loop.save_explanation(rid, "確かめた人", "折りが多くて固い", "折りを減らす")
fix, fails = tv.propose(rid, [m1], "折りの数を減らす", "作る側", "fold_count", 20)
assert fix and not fails, fails
env = {**os.environ, "PYTHONPATH": "src"}
ROOT = pathlib.Path(__file__).resolve().parents[1]


def cli(*args, module="omochae.trial_video"):
    return subprocess.run([sys.executable, "-m", module, *args], cwd=ROOT, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True, timeout=120)


done = cli("report", rid, "--built", "yes", "--finish", "3", "--minutes", "40")
assert done.returncode == 0, done.stderr
rep = json.loads(done.stdout)
assert rep["minutes"] == 40 and isinstance(rep["minutes"], int) and rep["problems"] == [{"kind": "fold", "step": 8, "note": "蛇腹で手が止まった"}] and WORDS in rep["motion_notes"] and "moved" not in rep
assert cli("report", rid, "--built", "yes", "--minutes", "40.5").returncode == 4

# 作る側の一覧: 届いた物を読む順に出す。文と結び先が見える
listed = cli("list", module="web.video_up")
assert listed.returncode == 0 and "U-0001" in listed.stdout and rid in listed.stdout and str(sheet) in listed.stdout and "a.mov" not in listed.stdout, listed

# 取り下げ: 動画もコマも札も消える。番号は使い回さない。上げた人の頁には取り下げたと出る
assert cli("withdraw", "U-0002", module="web.video_up").returncode == 0
assert not tv._base(r2).exists() and not (loop.folder() / f"video-{r2}.json").exists() and not (records.folder() / f"{r2}.json").exists()
slip2 = json.loads((folder / "U-0002.json").read_text(encoding="utf-8"))
assert slip2["state"] == "withdrawn" and "note" not in slip2 and "source_id" not in slip2 and "首の糸" not in json.dumps(slip2, ensure_ascii=False)
assert status(second["token"])[second["token"]]["word"] == video_up.WORDS["withdrawn"]
assert cli("withdraw", "U-9999", module="web.video_up").returncode == 3 and cli("withdraw", "x", module="web.video_up").returncode == 3
assert cli("withdraw", module="web.video_up").returncode == 4
assert "U-0002" not in cli("list", module="web.video_up").stdout
# 一覧は上げた人の字を 1 行の中に閉じ込める（改行で偽の行を作らせない）
code, multi = send(video("e.mov"), note="1 行目\nU-9999\tdone")
assert code == 200 and wait(multi["token"])["state"] == "done"
lines = cli("list", module="web.video_up").stdout.splitlines()
assert not any(x.startswith("U-9999") for x in lines) and any(multi["receipt"] in x and "1 行目\\nU-9999" in x for x in lines), lines
assert cli("withdraw", multi["receipt"], module="web.video_up").returncode == 0
# 同じ動画を別のおもちゃへ送りかけた小分けも、取り下げで消える
code, half = send(video("f.mov"))
assert code == 200 and wait(half["token"])["state"] == "done"
half_slip = json.loads((folder / f'{half["receipt"]}.json').read_text(encoding="utf-8"))
assert call("POST", f'/chunk?id={half_slip["upload"]}&n=0', body=b"x" * 10)[0] == 200 and (folder / "tmp" / half_slip["upload"]).exists()
assert cli("withdraw", half["receipt"], module="web.video_up").returncode == 0 and not (folder / "tmp" / half_slip["upload"]).exists()
# 案の根拠になった記録は残すが、動画とコマと札は消える（顔や声を根拠の話のために残さない。records.withdraw の media_only）
done = cli("withdraw", "U-0001", module="web.video_up")
assert done.returncode == 0, done.stderr
assert not tv._base(rid).exists() and not (loop.folder() / f"video-{rid}.json").exists(), "動画とコマと札は消す"
assert (records.folder() / f"{rid}.json").exists(), "案の根拠の指す先を残す"
assert WORDS not in (records.folder() / f"{rid}.json").read_text(encoding="utf-8"), "上げた人の文も消す"
# 取り下げた後に同じ動画を送ると、新しい受付になる
code, back = send(data, note="もう一度")
assert code == 200 and back["receipt"] not in ("U-0001", "U-0002") and wait(back["token"])["state"] == "done"

# 止まっても続きができる: 待っていた物も、読んでいる途中だった物も、次に立てた時に回す
srv.shutdown()
srv.server_close()
paused = video_up.serve(0, KEY, worker=False)
threading.Thread(target=paused.serve_forever, daemon=True).start()
port = paused.server_address[1]
HOST, ORIGIN = f"127.0.0.1:{port}", f"http://127.0.0.1:{port}"
code, waiting = send(video("c.mov"), toy=TORA)
assert code == 200 and status(waiting["token"])[waiting["token"]]["state"] == "waiting" and status(waiting["token"])[waiting["token"]]["word"] == video_up.WORDS["waiting"]
code, middle = send(video("d.mov"), toy=TORA)
slip_path = folder / f'{middle["receipt"]}.json'
slip_mid = json.loads(slip_path.read_text(encoding="utf-8"))
slip_path.write_text(json.dumps({**slip_mid, "state": "working"}), encoding="utf-8")
paused.shutdown()
paused.server_close()
again_srv = video_up.serve(0, KEY)
threading.Thread(target=again_srv.serve_forever, daemon=True).start()
port = again_srv.server_address[1]
HOST, ORIGIN = f"127.0.0.1:{port}", f"http://127.0.0.1:{port}"
assert wait(waiting["token"])["state"] == "done" and wait(middle["token"])["state"] == "done"
# 古い小分けは片づける。受け取りの途中の物には触らない
stale, fresh = folder / "tmp" / ("f" * 32), folder / "tmp" / ("1" * 32)
stale.mkdir()
fresh.mkdir()
(stale / "0").write_bytes(b"x")
(fresh / "0").write_bytes(b"x")
old = time.time() - video_up.KEEP_PARTS - 60
os.utime(stale, (old, old))
video_up.sweep()
assert not stale.exists() and fresh.exists()
again_srv.shutdown()

# 壊す試験: 機械の都合と、動画のせいを分ける
broken = video_up.serve(0, KEY, worker=False)
threading.Thread(target=broken.serve_forever, daemon=True).start()
port = broken.server_address[1]
HOST, ORIGIN = f"127.0.0.1:{port}", f"http://127.0.0.1:{port}"
video_up.RETRY_WAIT = 0


def slip_of(name):
    return json.loads((folder / f"{name}.json").read_text(encoding="utf-8"))


# 受付の途中で落ちても、次の人の受付を止めない。小分けは送り直せる形で残る
data_a = video("g.mov")
real_replace = os.replace


def fail_once(src, dst):
    os.replace = real_replace
    raise OSError("置き場の失敗")


uid_a = hashlib.sha256(data_a).hexdigest()[:32]
for n in range(math.ceil(len(data_a) / CHUNK)):
    assert call("POST", f"/chunk?id={uid_a}&n={n}", body=data_a[n * CHUNK:(n + 1) * CHUNK])[0] == 200
before_slips = len(list(folder.glob("U-*.json")))
os.replace = fail_once
try:
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    c.request("POST", "/finish", body=json.dumps({**form(), "id": uid_a, "chunks": math.ceil(len(data_a) / CHUNK), "size": len(data_a)}).encode(), headers={"Host": HOST, "Cookie": JAR, "Origin": ORIGIN})
    c.getresponse()
except (http.client.HTTPException, OSError):
    pass
c.close()
assert len(list(folder.glob("U-*.json"))) == before_slips, "落ちた受付を残さない"
code, again_a = send(data_a, chunks=False)
assert code == 200, again_a
# 道具が止められた時（動画のせいでない）: 元を消さず、回し直して受け取る。相手のファイルのせいにしない
real_probe = trial_video_probe = tv._probe
hits = []


def killed_once(*a, **k):
    hits.append(1)
    tv._probe = real_probe
    raise tv.Interrupted("止められた")


tv._probe = killed_once
assert video_up.process(again_a["receipt"]) == 0 * 1 + video_up.RETRY_WAIT
kept = slip_of(again_a["receipt"])
assert kept["state"] == "waiting" and kept["waits"] == 1 and (folder / "tmp" / f'job-{again_a["receipt"]}').exists() and hits
assert video_up.process(again_a["receipt"]) == 0 and slip_of(again_a["receipt"])["state"] == "done"
assert not (folder / "tmp" / f'job-{again_a["receipt"]}').exists()
# 機械の都合が何度続いても、動画を消さない。文も残して待つ。直ったら受け取る
video_up.RETRY_WAIT = 30
code, patient = send(video("h2.mov"), note="消えない文")
real_attach = tv.attach


def no_room(*a, **k):
    raise tv.Interrupted("止められた")


tv.attach = no_room
waits = [video_up.process(patient["receipt"]) for _ in range(8)]
tv.attach = real_attach
assert waits == [30, 60, 120, 240, 480, 960, 1800, 1800], waits
held = slip_of(patient["receipt"])
assert held["state"] == "waiting" and held["note"] == "消えない文" and (folder / "tmp" / f'job-{patient["receipt"]}').exists()
assert status(patient["token"])[patient["token"]]["word"] == video_up.WORDS["waiting"], "上げた人のせいにしない"
# 場所が足りない時も同じ
real_usage = shutil.disk_usage
video_up.shutil.disk_usage = lambda p: type("U", (), {"free": 0})()
assert video_up.process(patient["receipt"]) > 0 and slip_of(patient["receipt"])["state"] == "waiting"
video_up.shutil.disk_usage = real_usage
assert video_up.process(patient["receipt"]) == 0 and slip_of(patient["receipt"])["state"] == "done"
video_up.RETRY_WAIT = 0
# 作りの誤りは、回数で止める。記録も文も動画も残さない
code, stuck = send(video("h.mov"), note="残らない文")


def always_fail(*a, **k):
    raise ValueError("作りの誤り")


tv.attach = always_fail
recs_before = len(records.all_records(uploads=True))
for _ in range(video_up.TRIES):
    video_up.process(stuck["receipt"])
tv.attach = real_attach
gone = slip_of(stuck["receipt"])
assert gone["state"] == "failed" and "note" not in gone and "record" not in gone
assert len(records.all_records(uploads=True)) == recs_before and "残らない文" not in json.dumps(records.all_records(uploads=True), ensure_ascii=False)
# 読んでいる間に取り下げられたら、元に戻さない。動画も記録も文も残さない
code, mid = send(video("h3.mov"), note="取り下げた文")


def withdraw_then_attach(rid_, src_, kind_=None):
    assert video_up.withdraw(mid["receipt"], force=True) == []
    return real_attach(rid_, src_, kind_)


tv.attach = withdraw_then_attach
recs_now = len(records.all_records(uploads=True))
assert video_up.process(mid["receipt"]) == 0
tv.attach = real_attach
assert slip_of(mid["receipt"])["state"] == "withdrawn" and "note" not in slip_of(mid["receipt"])
assert len(records.all_records(uploads=True)) == recs_now and "取り下げた文" not in json.dumps(records.all_records(uploads=True), ensure_ascii=False)
assert not (folder / "tmp" / f'job-{mid["receipt"]}').exists()
# 記録を作った直後に止まっても、同じ動画の記録を 2 つ作らない
code, twice = send(video("i.mov"), note="二重にしない")
made, _ = tv.new_record(G, hypotheses.sheet_of(G)["id"], records.UNSURE, note="二重にしない", via=records.UPLOADED, upload=twice["receipt"])
assert video_up.process(twice["receipt"]) == 0 and slip_of(twice["receipt"])["record"] == made
assert sum(r.get("upload") == twice["receipt"] for r in records.all_records(uploads=True)) == 1
# 結んだ後に止まっても、読み直して受け取りにする（受け取った物を受け取れなかった事にしない）
slip_twice = slip_of(twice["receipt"])
slip_path = folder / f'{twice["receipt"]}.json'
slip_path.write_text(json.dumps({**slip_twice, "state": "working"}), encoding="utf-8")
assert video_up.process(twice["receipt"]) == 0 and slip_of(twice["receipt"])["state"] == "done"
# 読み取り中のまま残った受付は、サーバを止めてから取り下げられる
slip_path.write_text(json.dumps({**slip_twice, "state": "working"}), encoding="utf-8")
assert cli("withdraw", twice["receipt"], module="web.video_up").returncode == 3
assert cli("withdraw", twice["receipt"], "--force", module="web.video_up").returncode == 0 and slip_of(twice["receipt"])["state"] == "withdrawn"
assert not tv._base(made).exists()
# 終わった受付の残りを片づける。待っている受付の物には触らない
left = folder / "tmp" / f'job-{again_a["receipt"]}'
left.mkdir()
code, wait_slip = send(video("j.mov"))
video_up.sweep()
assert not left.exists() and (folder / "tmp" / f'job-{wait_slip["receipt"]}').exists()
video_up.process(wait_slip["receipt"])

# 映像の流れの中の情報: H.264 の SEI に入れた字が残らない。コマの絵は同じ
MARK = "SECRET-IN-STREAM"
sei = tmp / "sei.mov"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=5:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-bsf:v", f"h264_metadata=sei_user_data=086f3693b7b34f2c965321492feee5b8+{MARK}", str(sei)], check=True, capture_output=True, timeout=120)
assert MARK.encode() in sei.read_bytes(), "作り物に印が入っていない"
code, sei_slip = send(sei.read_bytes())
video_up.process(sei_slip["receipt"])
sei_rid = slip_of(sei_slip["receipt"])["record"]
assert slip_of(sei_slip["receipt"])["state"] == "done" and MARK.encode() not in (tv._base(sei_rid) / "v1.mp4").read_bytes()
md5 = lambda p: [x.split(",")[-1] for x in subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-map", "0:V:0", "-f", "framemd5", "-"], capture_output=True, text=True).stdout.splitlines() if not x.startswith("#")]  # noqa: E731
assert md5(sei) == md5(tv._base(sei_rid) / "v1.mp4"), "絵は作り直さない"
# H.264 と HEVC でない形（コマごとに EXIF を持てる MJPEG）は作り直す
mjpeg = tmp / "mjpeg.mov"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=5:duration=3", "-c:v", "mjpeg", "-q:v", "5", str(mjpeg)], check=True, capture_output=True, timeout=120)
code, mj_slip = send(mjpeg.read_bytes())
video_up.process(mj_slip["receipt"])
mj_out = tv._base(slip_of(mj_slip["receipt"])["record"]) / "v1.mp4"
assert slip_of(mj_slip["receipt"])["state"] == "done"
assert json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "V:0", "-show_entries", "stream=codec_name", "-of", "json", str(mj_out)], capture_output=True, text=True).stdout)["streams"][0]["codec_name"] == "h264"
# 写すと大きくなりすぎる物（同じ所を何度も指す動画）は止める
data_k = video("k.mov")
room, tv.ROOM = tv.ROOM, 1000 - len(data_k)
code, big = send(data_k)
video_up.process(big["receipt"])
tv.ROOM = room
assert slip_of(big["receipt"])["state"] == "failed" and "record" not in slip_of(big["receipt"])
# 長さの欄が長すぎる物は、読む前に断る
top, tv.MAX_SECONDS = tv.MAX_SECONDS, 1
code, long_slip = send(video("l.mov"))
video_up.process(long_slip["receipt"])
tv.MAX_SECONDS = top
assert slip_of(long_slip["receipt"])["state"] == "failed"
# 後ろが欠けた動画は、受け取った事にしない（入れ物の欄の長さと、写せた中身を比べる）
whole = tmp / "whole.mov"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=15:duration=20", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(whole)], check=True, capture_output=True, timeout=120)
raw_whole = whole.read_bytes()
code, cut = send(raw_whole[:len(raw_whole) // 3])
video_up.process(cut["receipt"])
assert slip_of(cut["receipt"])["state"] == "failed", "欠けた動画"
broken.shutdown()
broken.server_close()

# もう 1 つの口: 作る前の型紙のレビュー（本人の指示 20:35）。声を非公開で残し、この機械の中で字にする。声も字も頁に出さない
review_data = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_DATA"] = env["OMOCHAE_DATA"] = str(review_data)
folder = video_up.folder()
fake_asr = tmp / "fake_asr.py"
fake_asr.write_text('import json, sys\nassert sys.argv[1].endswith("voice.mka")\njson.dump({"model": sys.argv[2], "language": "ja", "segments": [{"start": 1.0, "end": 2.0, "text": "手順 3 の折り線が薄くて見えません"}]}, sys.stdout, ensure_ascii=False)\n', encoding="utf-8")
video_up.ASR_WORKER = fake_asr
os.environ["OMOCHAE_ASR_PYTHON"] = sys.executable
rev = video_up.serve(0, KEY, kind="review")
threading.Thread(target=rev.serve_forever, daemon=True).start()
port = rev.server_address[1]
HOST, ORIGIN = f"127.0.0.1:{port}", f"http://127.0.0.1:{port}"
code, body, _ = call("GET", "/", origin=None)
page = body.decode()
assert code == 200 and all(line in page for line in REVIEW_ADOPTED), "本人が採った文"
assert video_up.REVIEW_WORDS == {"done": "受け取りました。いつ・どこでとったかなどの情報を消しました。", "withdrawn": "取り下げました。動画と声と字を消しました。"}
assert "何を見て作りましたか" not in page and video_up.PROMISES[0] not in page, "音を消す文を出さない（レビューは声を残す）"
assert 'name="made_with" value="review"' in page and video_up.AGREE_ADULT in page and video_up.AGREE_PEOPLE in page
assert post("/check", form(made_with="sheet"))[0] == 422 and post("/check", form(made_with="review"))[0] == 200
code, r1 = send(video("rv1.mov"), made_with="review", note="見た感想です")
assert code == 200, r1
now = wait(r1["token"])
assert now["state"] == "done" and now["word"] == video_up.REVIEW_WORDS["done"], now
for _ in range(100):
    slip_r = json.loads((folder / f'{r1["receipt"]}.json').read_text(encoding="utf-8"))
    if slip_r.get("text"):
        break
    time.sleep(0.1)
assert slip_r["text"] == "done" and slip_r["voice"] is True, slip_r
rid_r = slip_r["record"]
rec_r = loop.record(rid_r)
assert rec_r["video_kind"] == "review" and rec_r["via"] == records.UPLOADED and rec_r["note"].startswith(video_up.MADE_WITH["review"]) and "見た感想です" in rec_r["note"]
voice = tv._base(rid_r) / "voice" / "voice.mka"
assert stat.S_IMODE(voice.stat().st_mode) == 0o600 and stat.S_IMODE(voice.parent.stat().st_mode) == 0o700
kinds = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(voice)], capture_output=True, text=True, check=True).stdout)
assert [s["codec_type"] for s in kinds["streams"]] == ["audio"], "声だけ"
assert b"secret-place" not in voice.read_bytes() and PLACE.encode() not in voice.read_bytes(), "声の写しにも撮影情報を残さない"
stored_r = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(tv._base(rid_r) / "v1.mp4")], capture_output=True, text=True, check=True).stdout)
assert [s["codec_type"] for s in stored_r["streams"]] == ["video"], "動画の方に音を残さない"
text_file = tv._base(rid_r) / "voice" / "transcript.json"
assert stat.S_IMODE(text_file.stat().st_mode) == 0o600 and "折り線" in text_file.read_text(encoding="utf-8")
assert str(text_file) in cli("list", module="web.video_up").stdout
# 札はふつうの札の形で足せる。人が確かめるまで案のまま
mr, fails = tv.add_mark(rid_r, 1, 3, "mark", "手順 3 の折り線が薄い（レビューの字から）", "Claude Code のセッション")
assert mr and not fails and not tv.load(rid_r)["marks"][0]["confirmed_by"], fails
# 音の長さを超えた字は、道具が作った字なので残さない（本物の 1 本目で見た形）
assert asr_worker.inside([{"start": 109.5, "text": "以上です"}, {"start": 118.6, "text": "以上です"}, {"start": 124.7, "text": "ご視聴ありがとうございました"}], 110.1) == [{"start": 109.5, "text": "以上です"}]
# 頁に出ない。声とコマの道は開かない
site2 = site_serve(0)
threading.Thread(target=site2.serve_forever, daemon=True).start()
site_port = site2.server_address[1]
for path in (f"/toy/{G}", "/gallery", f"/zukan/{G}", f"/toy/{G}/techo"):
    # 探す字は、ほかの枝が頁に足す字に当たらない長さにする（「voice」「transcript」「折り線」は話す口と手順の文に出る）
    assert "折り線が薄くて見えません" not in site_get(path)[1] and "voice.mka" not in site_get(path)[1] and "transcript.json" not in site_get(path)[1] and rid_r not in site_get(path)[1], path
for path in (f"/record/{rid_r}/media/voice.mka", f"/record/{rid_r}/media/voice/voice.mka", f"/record/{rid_r}/media/voice/transcript.json"):
    assert site_get(path)[0] == 404, path
site2.shutdown()
# 音の無い動画は、字にする物が無い
silent = video("rv2.mov", audio=False)
code, r2 = send(silent, made_with="review")
assert code == 200 and wait(r2["token"])["state"] == "done"
slip_s = json.loads((folder / f'{r2["receipt"]}.json').read_text(encoding="utf-8"))
assert slip_s["voice"] is False and not (tv._base(slip_s["record"]) / "voice").exists()
# 道具が無い機械: 動画は受け取り、字にできていない事を残す。後で字にし直せる
del os.environ["OMOCHAE_ASR_PYTHON"]
code, r3 = send(video("rv3.mov"), made_with="review")
assert code == 200 and wait(r3["token"])["state"] == "done"
for _ in range(100):
    slip_n = json.loads((folder / f'{r3["receipt"]}.json').read_text(encoding="utf-8"))
    if slip_n.get("text"):
        break
    time.sleep(0.1)
assert slip_n["text"] == "no-tool", slip_n
os.environ["OMOCHAE_ASR_PYTHON"] = sys.executable
assert video_up.transcribe(r3["receipt"]) is True and json.loads((folder / f'{r3["receipt"]}.json').read_text(encoding="utf-8"))["text"] == "done"
# 字にしている間に取り下げられたら、受付を元に戻さない（道具が落ちる形でも）
code, r4 = send(video("rv4.mov"), made_with="review", note="字にする間に取り下げる文")
assert code == 200 and wait(r4["token"])["state"] == "done"
for _ in range(100):
    if json.loads((folder / f'{r4["receipt"]}.json').read_text(encoding="utf-8")).get("text"):
        break
    time.sleep(0.1)
real_run = video_up.subprocess.run


def withdraw_then_fail(*a, **k):
    video_up.subprocess.run = real_run
    assert video_up.withdraw(r4["receipt"], force=True) == []
    raise OSError("道具が落ちた")


video_up.subprocess.run = withdraw_then_fail
assert video_up.transcribe(r4["receipt"]) is False
video_up.subprocess.run = real_run
slip_w = json.loads((folder / f'{r4["receipt"]}.json').read_text(encoding="utf-8"))
assert slip_w["state"] == "withdrawn" and "note" not in slip_w and "record" not in slip_w, slip_w
assert status(r4["token"])[r4["token"]]["word"] == video_up.REVIEW_WORDS["withdrawn"]
# 整理が終わったら声を消す。字は残る
assert cli("drop-voice", r1["receipt"], module="web.video_up").returncode == 0 and not voice.exists() and text_file.exists()
assert cli("drop-voice", "U-9999", module="web.video_up").returncode == 3
# 取り下げで動画も声も字も札も消える
assert cli("withdraw", r3["receipt"], module="web.video_up").returncode == 0
gone_rid = slip_n["record"]
assert not tv._base(gone_rid).exists() and not (loop.folder() / f"video-{gone_rid}.json").exists()
assert status(r3["token"])[r3["token"]]["word"] == video_up.REVIEW_WORDS["withdrawn"]
rev.shutdown()
rev.server_close()
os.environ["OMOCHAE_DATA"] = env["OMOCHAE_DATA"] = str(tmp)
folder = video_up.folder()
del os.environ["OMOCHAE_ASR_PYTHON"]

# どの玩具でも記録を作れる（83 種で札の言葉が違うので、1 つでも通らないと、選んだ人だけが受け取れない）
for sid in sources():
    made, fails = tv.new_record(sid, hypotheses.sheet_of(sid)["id"], video_up.UNSURE, note="", via=records.UPLOADED)
    assert made and not fails, (sid, fails)
# 手で結ぶ記録は今までどおり札の言葉だけ（受け口の外で「わからない」を増やさない）
assert tv.new_record(TORA, "H-A", "わからない")[1]
print("ok: 動画の受け口")
