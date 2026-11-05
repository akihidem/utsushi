"""作成の過程の動画を記録に結び、止まった所 → 直しの案 → 型紙の版まで回す（本人の指示 11-05、Issue #216、J-029）。本物の API は呼ばない。

見る線: 音と撮影情報が落ちる／学ぶ人の頁とギャラリーと合言葉なしの場に映像が出ない／顔と声の確かめの前は作る側の頁にも出ない／
人が確かめていない札は根拠にならない／人の説明の前に案を作れない／採った案が版になり、作る側の頁で 1 本につながって見える。
必須 2 種の今の版の紙は tests/test_floor_pin.py が見る（この試験は版 2 を足すだけで、版 1 を変えない）。
動画は ffmpeg で作り物を作る（人も部屋も写らない）。ffmpeg が無い機械では、この試験は確かめずに終わる。
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA

if not shutil.which("ffmpeg"):
    print("ok: ffmpeg が無いので確かめなかった")
    sys.exit(0)

from omochae import hypotheses, loop, trial_video as tv  # noqa: E402
from web import techo_site  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
work = pathlib.Path(tempfile.mkdtemp())
src = work / "take.mov"
# 動く 8 秒 + 止まった 30 秒 + 動く 4 秒。音と、位置の撮影情報を付ける（落ちる事を見るため）
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=8", "-f", "lavfi", "-i", "color=c=gray:size=160x120:rate=5:duration=30",
                "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=4", "-f", "lavfi", "-i", "sine=frequency=440:duration=42",
                "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1[v]", "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-metadata", "location=+35.6000+139.7000/", "-metadata", "title=secret-place", str(src)], check=True, capture_output=True, timeout=120)

# 記録を作って結ぶ。刷った組が残る
rid, fails = tv.new_record(G, "H-A", "動かない", tried_on="2026-11-05", note="作成の過程の動画の試行")
assert rid and not fails, fails
rec = loop.record(rid)
assert rec["sheet_set"].startswith("goraigo-v") and rec["via"] == "video"
item, fails = tv.attach(rid, src)
assert item and not fails, fails
stored = tv._base(rid) / "v1.mp4"
assert stored.exists() and src.exists(), "元のファイルには触らない"
probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(stored)], capture_output=True, text=True, check=True).stdout)
assert {s["codec_type"] for s in probe["streams"]} == {"video"}, "音を落とす"
tags = json.dumps(probe["format"].get("tags", {}), ensure_ascii=False)
assert "35.6" not in tags and "secret-place" not in tags, tags
# 止まった候補: 止まった 30 秒の辺りを 1 つだけ拾う
assert len(item["still"]) == 1 and 6 <= item["still"][0][0] <= 10 and 36 <= item["still"][0][1] <= 40, item["still"]
assert tv.attach("R-9999", src)[1] and tv.attach(rid, work / "none.mov")[1]
(work / "bad.mov").write_bytes(b"not a video")
assert tv.attach(rid, work / "bad.mov")[1], "動画として読めない物は結ばない"

# 札: 決まりの外は落とす。連絡先の形も落とす
assert tv.add_mark(rid, 10, 8, "fold", "", "読み手")[1], "一言が要る"
assert tv.add_mark(rid, 9999, 8, "fold", "x", "読み手")[1], "長さの外"
assert tv.add_mark(rid, 10, 99, "fold", "x", "読み手")[1], "手順の外"
assert tv.add_mark(rid, 10, 8, "nope", "x", "読み手")[1], "種類の外"
assert tv.add_mark(rid, 10, 8, "fold", "電話は 090-1234-5678", "読み手")[1], "連絡先"
m1, fails = tv.add_mark(rid, 12, 8, "fold", "蛇腹の 3 枚目で手が止まった", "Claude Code のセッション")
m2, _ = tv.add_mark(rid, 30, 8, "fit", "糸を通す穴が見つからない", "Claude Code のセッション")
assert m1 == "M1" and m2 == "M2" and not fails
assert (tv._base(rid) / "frames/v1-000012.jpg").exists(), "札のコマ"

# 確かめていない札は根拠にならない。人の説明の前に案を作れない。版ごとの止まり方にも数えない
assert tv.effect(G)["H-A"]["rows"] == {}, "案の札を数えない"
assert tv.propose(rid, ["M1"], "折りの数を減らす", "作る側", "fold_count", 20)[1]
assert not tv.judge_mark(rid, "M1", "本人") and tv.judge_mark(rid, "M1", "") and tv.judge_mark(rid, "M9", "本人")
assert tv.propose(rid, ["M1"], "折りの数を減らす", "作る側", "fold_count", 20)[1], "説明が先"
assert not loop.save_explanation(rid, "本人", "折りが多くて固い", "折りを減らす")
assert tv.propose(rid, ["M2"], "x", "作る側")[1], "確かめていない札"
assert not tv.judge_mark(rid, "M2", "本人", accept=False), "外した札は根拠にならない"
assert tv.propose(rid, ["M2"], "x", "作る側")[1]
col = (rec["sheet_set"], 1)
assert tv.effect(G)["H-A"]["rows"] == {8: {col: {"video": 1, "tap": 0}}}

# 案を採ると版になる。検査（F7）に落ちる寸法は版にならない。採る前は版が増えない
d1, fails = tv.propose(rid, ["M1"], "折りの数を減らして、畳んだ厚さを薄くする", "作る側", "fold_count", 20)
assert d1 == "D-0001" and not fails, fails
assert loop.latest_version(G, "H-A") == 1
printed = []
assert tv.adopt(d1, "", printer=lambda *a: printed.append(a) or 0)[1], "採った人が要る"
made, fails = tv.adopt(d1, "本人", printer=lambda *a: printed.append(a) or 0)
assert made == {"version": 2, "printed": True} and not fails and printed == [(G, "H-A", 2)], (made, fails)
assert tv.adopt(d1, "本人")[1], "同じ案を 2 回採らない"
assert loop.version_params(G, "H-A", 2)[0]["fold_count"] == 20
d2, _ = tv.propose(rid, ["M1"], "折り数をありえない値にする", "作る側", "fold_count", 9999)
assert tv.adopt(d2, "本人")[1], "範囲の外は版にならない"
assert not tv.reject(d2, "本人") and tv.adopt(d2, "本人")[1]
# 形や手順の文の案: 雛形の直しの記録（T-）になる。直した組と commit が無いと、直した事にしない
d3, _ = tv.propose(rid, ["M1"], "手順 8 に蛇腹を半分ずつ折る図を足す", "作る側")
assert tv.adopt(d3, "本人")[1], "組と commit が要る"
made, fails = tv.adopt(d3, "本人", sheet_set="goraigo-v11", commit="abc1234", decided_in="カード")
assert made and made["template_change"].startswith("T-") and not fails, fails

# 次の版の試行: 版ごとの止まり方が並ぶ
r2, _ = tv.new_record(G, "H-A", "動いた", version=2, tried_on="2026-11-06")
assert tv.attach(r2, src)[1] == []
tv.add_mark(r2, 20, 3, "cut", "溝を切る所で少し迷った", "本人")
tv.judge_mark(r2, "M1", "本人")
eff = tv.effect(G)["H-A"]
col2 = (rec["sheet_set"], 2)
assert eff["columns"] == [col, col2] and eff["rows"][8] == {col: {"video": 1, "tap": 0}} and eff["rows"][3] == {col2: {"video": 1, "tap": 0}}
assert eff["reports"] == {col: 1, col2: 1}

# エンジンの報告の形に書き出す。確かめた札だけが困り事になる。欄はエンジンの決まりの中だけ
rep, fails = tv.report(rid, True, finish=3, minutes=40)
assert not fails and rep["template"] == "slider_fan" and rep["form"] == "tab" and rep["moved"] == "not" and rep["built"] is True and rep["finish"] == 3
assert rep["problems"] == [{"kind": "fold", "step": 8, "note": "蛇腹の 3 枚目で手が止まった"}] and rep["stuck_step"] == 8
assert set(rep) <= {"template", "form", "params", "source_id", "built", "moved", "finish", "motion_notes", "finish_notes", "problems", "reported_at", "stuck_step", "gave_up", "minutes"}

# 画面: サーバを立てる
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path, headers=None):
    try:
        r = urllib.request.urlopen(urllib.request.Request(base + path, headers=headers or {}))
        return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


# 顔と声の確かめの前: 札の字は出るが、映像とコマは出ない。口も閉じている
page = get(f"/loop/{G}")[1].decode()
assert 'id="k0"' in page and "蛇腹の 3 枚目で手が止まった" in page and "確かめ待ち" in page and "<video" not in page and "/loop/frame/" not in page
assert get(f"/loop/video/{rid}/v1.mp4")[0] == 404 and get(f"/loop/frame/{rid}/v1-000012.jpg")[0] == 404
# 1 本につながる: 動画 → 札 → 案 → 版 → 版ごとの止まり方。採らなかった案もそう書く
for w in (rid, "M1", "D-0001", "版 2 になった", "採らない", "goraigo-v11 になった", "版ごとの止まり方", "動画 1・画面 0", "動きの少なかった区間: "):
    assert w in page, w
for w in ("成功", "失敗", "正解", "順位", "点数"):
    assert w not in page.split("<main>")[1].split("</main")[0], w
# 確かめた後: 映像とコマが出る。部分取得で返す
assert tv.confirm_shown(rid, "") and not tv.confirm_shown(rid, "本人")
page = get(f"/loop/{G}")[1].decode()
assert f'<video src="/loop/video/{rid}/v1.mp4"' in page and f"/loop/frame/{rid}/v1-000012.jpg" in page and f'/loop/video/{rid}/v1.mp4#t=12' in page
code, body, headers = get(f"/loop/video/{rid}/v1.mp4", {"Range": "bytes=0-99"})
assert code == 206 and len(body) == 100 and headers["Content-Range"].startswith("bytes 0-99/") and headers["Content-Type"] == "video/mp4"
assert get(f"/loop/video/{rid}/v1.mp4", {"Range": "bytes=999999999-"})[0] == 416
code, body, _ = get(f"/loop/video/{rid}/v1.mp4")
assert code == 200 and len(body) == stored.stat().st_size
assert get(f"/loop/frame/{rid}/v1-000012.jpg")[0] == 200
assert get(f"/loop/video/{rid}/../../secret")[0] == 404 and get(f"/loop/video/{rid}/m1.mp4")[0] == 404
# 学ぶ人の頁とギャラリーには、確かめた後も出ない。上げた物の一覧にも入らない
assert techo_site.media_of(rid) == []
hypotheses.save_prediction(G, "扇が開くと思う")
toy = get(f"/toy/{G}")[1].decode()
assert "v1.mp4" not in toy and "/loop/" not in toy and "/loop/" not in get("/gallery")[1].decode()
assert get(f"/record/{rid}/media/v1.mp4")[0] == 404
# 学ぶ人の頁の輪の節: 版と、雛形の直しが見える。札の字と動画は出ない
kz = toy.split('id="kaizen"')[1]
assert "仮説 A 版 2" in kz and "雛形の直し T-" in kz and "蛇腹の 3 枚目" not in kz
# 人の判断は頁のフォームから。名前が無ければ落ちる。確かめ・案の採否が同じ床を通る
def post(path, data, origin=None):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": origin or base})
    opener = urllib.request.build_opener(type("N", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))
    try:
        r = opener.open(req)
        return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)


r3, _ = tv.new_record(G, "H-B", "動かない", tried_on="2026-11-05")
assert tv.attach(r3, src)[1] == []
tv.add_mark(r3, 15, 2, "cut", "最初の切り込みで手が止まった", "Claude Code のセッション")
page = get(f"/loop/{G}")[1].decode()
assert f'action="/loop/{G}/judge"' in page and f'action="/loop/{G}/shown"' in page and f'action="/record/{r3}/explain"' in page
assert post(f"/loop/{G}/judge", {"record": r3, "mark": "M1", "action": "confirm", "by": ""})[0] == 422
assert post(f"/loop/{G}/judge", {"record": r3, "mark": "M1", "action": "confirm", "by": "本人"}, origin="http://evil.example")[0] == 403
assert not tv.load(r3)["marks"][0]["confirmed_by"], "別の出所からは確かめられない"
code, _, h = post(f"/loop/{G}/judge", {"record": r3, "mark": "M1", "action": "confirm", "by": "本人"})
assert code == 303 and f"/loop/{G}?msg=" in h["Location"] and tv.load(r3)["marks"][0]["confirmed_by"] == "本人"
code, _, h = post(f"/record/{r3}/explain", {"text": "切り込みの位置が分からない", "next_idea": "印を足す", "by": "本人", "back": "loop"})
assert code == 303 and f"/loop/{G}" in h["Location"] and loop.explanation(r3)
assert post(f"/loop/{G}/shown", {"record": r3, "by": "本人"})[0] == 303 and tv.load(r3)["checked_by"] == "本人"
d4, fails = tv.propose(r3, ["M1"], "折りの数を減らす", "作る側", "fold_count", 20)
assert d4 and not fails, fails
assert post(f"/loop/{G}/fix", {"fix": d4, "action": "adopt", "by": ""})[0] == 422
code, _, h = post(f"/loop/{G}/fix", {"fix": d4, "action": "adopt", "by": "本人"})
assert code == 303, code
assert (pathlib.Path(DATA) / "play" / G / "H-B_v2.pdf").exists(), "採った版が刷られる"
assert "版 2 を刷りました" in urllib.parse.unquote(h["Location"])
d5, _ = tv.propose(r3, ["M1"], "手順 2 の図を足す", "作る側")
assert post(f"/loop/{G}/fix", {"fix": d5, "action": "adopt", "by": "本人"})[0] == 422, "組と commit が要る"
assert post(f"/loop/{G}/fix", {"fix": d5, "action": "reject", "by": "本人"})[0] == 303

# 命令の側は、端末で人が打った時だけ進む（AI や自動の処理が「本人」と名乗って確かめない）。端末の無い所では落ちる
tv.add_mark(r3, 20, 2, "cut", "二つ目の札", "Claude Code のセッション")
env = {**os.environ, "PYTHONPATH": "src"}
for args in (["confirm", r3, "M2", "--by", "本人"], ["drop", r3, "M2", "--by", "本人"], ["show-ok", r2, "--by", "本人"], ["adopt", d2, "--by", "本人"], ["reject", d2, "--by", "本人"]):
    done = subprocess.run([sys.executable, "-m", "omochae.trial_video", *args], cwd=pathlib.Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True, start_new_session=True, timeout=60)
    assert done.returncode == 3 and "端末での人の確認" in done.stderr, (args, done.returncode, done.stderr[-200:])
assert not tv.load(r3)["marks"][1]["confirmed_by"] and not tv.load(r2)["checked_by"]

# 合言葉なしの場には出さない
open_srv = serve(0, public_open=False)
assert not getattr(open_srv, "public_open", False)
open_srv.server_close()
from api import ask  # noqa: E402

ask._key_present = lambda: False
pub = serve(0, public_open=True)
threading.Thread(target=pub.serve_forever, daemon=True).start()
pb = f"http://127.0.0.1:{pub.server_address[1]}"
for path in (f"/loop/video/{rid}/v1.mp4", f"/loop/frame/{rid}/v1-000012.jpg", f"/loop/{G}"):
    try:
        code = urllib.request.urlopen(pb + path).status
    except urllib.error.HTTPError as e:
        code = e.code
    assert code == 404, path
req = urllib.request.Request(pb + f"/loop/{G}/judge", data=b"record=x&mark=M1&by=x", method="POST", headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": pb})
try:
    code = urllib.request.urlopen(req).status
except urllib.error.HTTPError as e:
    code = e.code
assert code == 404, "合言葉なしの場では人の判断の口も閉じる"
print("ok: 動画から版まで")
