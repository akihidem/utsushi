"""作成の過程の動画を記録に結び、止まった所 → 直しの案 → 型紙の版まで回す（本人の指示 11-05、Issue #216、J-029）。本物の API は呼ばない。

見る線: 音と撮影情報が落ちる／学ぶ人の頁とギャラリーに映像が出ない／顔と声の確かめは動画ごと／
人が確かめていない札は根拠にならない／人の説明の前に案を作れない／採った案が版になる。
必須 2 種の今の版の紙は tests/test_floor_pin.py が見る（この試験は版 2 を足すだけで、版 1 を変えない）。
動画は ffmpeg で作り物を作る（人も部屋も写らない）。ffmpeg が無い機械では 4（検査できない）で終わる。
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
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA

if not shutil.which("ffmpeg"):  # 確かめられない時は 4（repo の決まり。通った事にしない）
    print("検査できない: ffmpeg が無い", file=sys.stderr)
    sys.exit(4)

from omochae import hypotheses, loop, trial_video as tv  # noqa: E402
from web import techo_site  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台の仮説（次の組は H-C の柄を下から押し上げる形・前の組は H-A。本人の決定 2026-11-06。hypotheses.sheet_id）
GS = hypotheses.sheet_of(G)["id"]
work = pathlib.Path(tempfile.mkdtemp())
src = work / "take.mov"
# 動く 8 秒 + 止まった 30 秒 + 動く 4 秒。音と、位置の撮影情報を付ける（落ちる事を見るため）
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=8", "-f", "lavfi", "-i", "color=c=gray:size=160x120:rate=5:duration=30",
                "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=4", "-f", "lavfi", "-i", "sine=frequency=440:duration=42",
                "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1[v]", "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-metadata", "location=+35.6000+139.7000/", "-metadata", "title=secret-place", str(src)], check=True, capture_output=True, timeout=120)

# 記録を作って結ぶ。刷った組が残る
rid, fails = tv.new_record(G, GS, "動かない", tried_on="2026-11-05", note="作成の過程の動画の試行")
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
assert tv.effect(G)[GS]["rows"] == {}, "案の札を数えない"
assert tv.propose(rid, ["M1"], "折りの数を減らす", "作る側", "fold_count", 20)[1]
assert not tv.judge_mark(rid, "M1", "本人") and tv.judge_mark(rid, "M1", "") and tv.judge_mark(rid, "M9", "本人")
assert tv.propose(rid, ["M1"], "折りの数を減らす", "作る側", "fold_count", 20)[1], "説明が先"
assert not loop.save_explanation(rid, "本人", "折りが多くて固い", "折りを減らす")
assert tv.propose(rid, ["M2"], "x", "作る側")[1], "確かめていない札"
assert not tv.judge_mark(rid, "M2", "本人", accept=False), "外した札は根拠にならない"
assert tv.propose(rid, ["M2"], "x", "作る側")[1]
col = (rec["sheet_set"], 1)
assert tv.effect(G)[GS]["rows"] == {8: {col: {"video": 1, "tap": 0}}}

# 案を採ると版になる。検査（F7）に落ちる寸法は版にならない。採る前は版が増えない
d1, fails = tv.propose(rid, ["M1"], "折りの数を減らして、畳んだ厚さを薄くする", "作る側", "fold_count", 20)
assert d1 == "D-0001" and not fails, fails
assert loop.latest_version(G, GS) == 1
printed = []
assert tv.adopt(d1, "", printer=lambda *a: printed.append(a) or 0)[1], "採った人が要る"
made, fails = tv.adopt(d1, "本人", printer=lambda *a: printed.append(a) or 0)
assert made == {"version": 2, "printed": True} and not fails and printed == [(G, GS, 2)], (made, fails)
assert tv.adopt(d1, "本人")[1], "同じ案を 2 回採らない"
assert loop.version_params(G, GS, 2)[0]["fold_count"] == 20
d2, _ = tv.propose(rid, ["M1"], "折り数をありえない値にする", "作る側", "fold_count", 9999)
# 採れなかった案の文を、人の確定した解釈として残さない。確定済みの解釈も上書きしない
before = loop.interpretation(rid)
assert tv.adopt(d2, "本人")[1], "範囲の外は版にならない"
assert loop.interpretation(rid) == before and (before or {}).get("content") != "折り数をありえない値にする"
assert not tv.reject(d2, "本人") and tv.adopt(d2, "本人")[1] and tv.reject(d2, "本人"), "決めた案は変えられない"
assert tv.reject(d1, "本人"), "版になった案を、採らないに変えられない"
# 案の後に札を外したら、採れない
assert tv.add_mark(rid, 14, 8, "fold", "外す札", "本人")[0] == "M3" and not tv.judge_mark(rid, "M3", "本人")
d_drop, fails = tv.propose(rid, ["M3"], "外される札を根拠にする", "作る側", "fold_count", 18)
assert d_drop and not fails, fails
assert not tv.judge_mark(rid, "M3", "本人", accept=False)
v_now = loop.latest_version(G, GS)
assert tv.adopt(d_drop, "本人")[1] and loop.latest_version(G, GS) == v_now, "外した札を根拠に版を作らない"
assert not tv.reject(d_drop, "本人")
# 刷る所で例外が出ても、案は採った事になる（案が採れないまま版だけが増える形にしない）
d_print, _ = tv.propose(rid, ["M1"], "折りを少し戻す", "作る側", "fold_count", 22)


def broken(*a):
    raise OSError("刷る道具が無い")


made, fails = tv.adopt(d_print, "本人", printer=broken)
assert made and made["printed"] is False and not fails, (made, fails)
assert tv.adopt(d_print, "本人")[1], "もう採った案"
# 形や手順の文の案: 雛形の直しの記録（T-）になる。直した組と commit が無いと、直した事にしない
d3, _ = tv.propose(rid, ["M1"], "手順 8 に蛇腹を半分ずつ折る図を足す", "作る側")
assert tv.adopt(d3, "本人")[1], "組と commit が要る"
made, fails = tv.adopt(d3, "本人", sheet_set="goraigo-v11", commit="abc1234", decided_in="本人の決定")
assert made and made["template_change"].startswith("T-") and not fails, fails

# 次の版の試行: 版ごとの止まり方が並ぶ
r2, _ = tv.new_record(G, GS, "動いた", version=2, tried_on="2026-11-06")
assert tv.attach(r2, src)[1] == []
tv.add_mark(r2, 20, 3, "cut", "溝を切る所で少し迷った", "本人")
tv.judge_mark(r2, "M1", "本人")
eff = tv.effect(G)[GS]
col2 = (rec["sheet_set"], 2)
assert eff["columns"] == [col, col2] and eff["rows"][8] == {col: {"video": 1, "tap": 0}} and eff["rows"][3] == {col2: {"video": 1, "tap": 0}}
assert eff["reports"] == {col: 1, col2: 1}
# 組の記録の無い前の記録は、同じ版の組へ寄せる（1 つの版が 2 列に割れない）。画面の札も同じ表に入る。組の版は数の順
from omochae import making_log, records  # noqa: E402

r_old, _ = records.add({"source_id": G, "hypothesis_id": GS, "sheet_version": 1, "result": "動いた", "fixes": []})
making_log.add_step(G, GS, 1, 8, "stuck", who="")
eff = tv.effect(G)[GS]
assert eff["columns"] == [col, col2] and eff["reports"][col] == 2 and eff["rows"][8][col] == {"video": 1, "tap": 1}, eff
assert sorted([("goraigo-v10", 1), ("goraigo-v9", 1), ("", 1)], key=tv._version_order) == [("", 1), ("goraigo-v9", 1), ("goraigo-v10", 1)]

# エンジンの報告の形に書き出す。確かめた札だけが困り事になる。欄はエンジンの決まりの中だけ
rep, fails = tv.report(rid, True, finish=3, minutes=40)
# 形は記録の紙の形（御来迎の今の組 goraigo-v14 のたたき台は内筒を下から押し上げる rise）
assert not fails and rep["template"] == "slider_fan" and rep["form"] == "rise" and rep["moved"] == "not" and rep["built"] is True and rep["finish"] == 3
# 寸法は、その記録の版の物（版 2 の報告に版 2 の寸法）
assert tv.report(r2, True)[0]["params"].get("fold_count") == 20
assert rep["problems"] == [{"kind": "fold", "step": 8, "note": "蛇腹の 3 枚目で手が止まった"}] and rep["stuck_step"] == 8
assert set(rep) <= {"template", "form", "params", "source_id", "built", "moved", "finish", "motion_notes", "finish_notes", "problems", "reported_at", "stuck_step", "gave_up", "minutes"}

# 顔と声の確かめは動画ごと。確かめた後に結んだ 2 本目は、確かめた事にならない
assert tv.confirm_shown(rid, "") and tv.confirm_shown(rid, "本人", "v9.mp4") and not tv.confirm_shown(rid, "本人") and tv.shown(rid, "v1.mp4")
r3, _ = tv.new_record(G, "H-B", "動かない", tried_on="2026-11-05")
assert tv.attach(r3, src)[1] == []
tv.add_mark(r3, 15, 2, "cut", "最初の切り込みで手が止まった", "Claude Code のセッション")
assert not tv.confirm_shown(r3, "本人") and tv.attach(r3, src)[1] == [] and tv.shown(r3, "v1.mp4") and not tv.shown(r3, "v2.mp4")

# 学ぶ人の頁とギャラリーには、確かめた後も出ない。上げた物の一覧にも入らない。動画とコマを返す道が無い
assert techo_site.media_of(rid) == []
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    try:
        with urllib.request.urlopen(base + path) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, ""


for path in (f"/toy/{G}", "/gallery"):
    assert "v1.mp4" not in get(path)[1], path
for path in (f"/record/{rid}/media/v1.mp4", f"/loop/video/{rid}/v1.mp4", f"/loop/frame/{rid}/v1-000012.jpg"):
    assert get(path)[0] == 404, path
server.shutdown()

# 命令の側は、端末で人が打った時だけ進む（AI や自動の処理が「本人」と名乗って確かめない）。端末の無い所では落ちる
tv.add_mark(r3, 20, 2, "cut", "二つ目の札", "Claude Code のセッション")
env = {**os.environ, "PYTHONPATH": "src"}
def cli(*args):
    return subprocess.run([sys.executable, "-m", "omochae.trial_video", *args], cwd=pathlib.Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True, start_new_session=True, timeout=120)


for args in (["confirm", r3, "M2", "--by", "本人"], ["drop", r3, "M2", "--by", "本人"], ["show-ok", r2, "--by", "本人"], ["adopt", d2, "--by", "本人"], ["reject", d2, "--by", "本人"]):
    done = cli(*args)
    assert done.returncode == 3 and "端末での人の確認" in done.stderr, (args, done.returncode, done.stderr[-200:])
assert not tv.load(r3)["marks"][1]["confirmed_by"] and not tv.shown(r2, "v1.mp4")
# 終わりの番号は 0・3・4 だけ（repo の決まり）。読めない動画のために記録を作らない
count = len(list((pathlib.Path(DATA) / "records").glob("R-*.json")))
done = cli("attach", str(work / "none.mov"), "--source", G, "--hypothesis", GS, "--result", "動かない")
assert done.returncode == 3 and len(list((pathlib.Path(DATA) / "records").glob("R-*.json"))) == count, (done.returncode, done.stderr[-200:])
assert cli("attach").returncode == 4, "引数の間違いは 4"
assert cli("sheet", "R-9999", str(work / "x.png")).returncode == 4, "読めない記録は 4"

# 人の工夫の札（本人の言葉 11-05「カメラで見るのはそういうとこだよ」）。報告では止まった手順に数えず、印を付けて渡す
k, _ = tv.add_mark(r2, 40, 5, "kufu", "折り目を深くして乗り切った", "本人")
assert k and not tv.judge_mark(r2, k, "本人")
rep, _ = tv.report(r2, built=True)
assert {"kind": "other", "step": 5, "note": "工夫: 折り目を深くして乗り切った"} in rep["problems"]
assert rep.get("stuck_step") != 5, "工夫の札は止まった手順に数えない"
# 分はエンジンの検査に合わせて整数だけ（小数は引数の誤り）
done = cli("report", rid, "--built", "yes", "--finish", "3", "--minutes", "40")
assert done.returncode == 0 and json.loads(done.stdout)["minutes"] == 40 and isinstance(json.loads(done.stdout)["minutes"], int), done
assert cli("report", rid, "--built", "yes", "--minutes", "40.5").returncode == 4
# 受け口の記録（web/video_up の印）: 学ぶ人の頁と束の読みから外れ、版の輪の表には数える。札に「わからない」が無い雛形でも、受け口の記録だけ受ける
TORA = "NDL-1187053-R0000014-R"
# どの雛形も「わからない」を持つ形にした（#146）ので、札に無い雛形の道は、虎の札から「わからない」を外した形で見る。
# 外すのはこの 4 行の間だけで、後ろの試験は今の札で回す。
from omochae.compose import TEMPLATES  # noqa: E402
_tora_results = TEMPLATES["pivot_counterweight"].RESULTS
TEMPLATES["pivot_counterweight"].RESULTS = tuple(w for w in _tora_results if w != records.UNSURE)
try:
    assert records.UNSURE not in records.results_for(TORA)
    assert tv.new_record(TORA, "H-A", records.UNSURE)[1], "手で結ぶ記録は札の言葉だけ"
    up, fails = tv.new_record(TORA, "H-A", records.UNSURE, note="上げた人の文", via=records.UPLOADED)
    assert up and not fails, fails
finally:
    TEMPLATES["pivot_counterweight"].RESULTS = _tora_results
assert up not in {r["id"] for r in records.all_records()} and up in {r["id"] for r in records.all_records(uploads=True)}
assert up not in {r["id"] for r in records.all_records(TORA)} and tv.effect(TORA)["H-A"]["reports"], "版の輪の表には数える"
assert tv.attach(up, src, "mov")[1] == [], "入れ物を決め打って読める"
# 動いたかが分からない記録: 決めつけない。人が動画を見て選べる。エンジンの入口が断る事を知らせる
assert "moved" not in tv.report(up, True)[0] and tv.report(up, True, moved="partly")[0]["moved"] == "partly"
done = cli("report", up, "--built", "yes")
assert done.returncode == 0 and "moved" not in json.loads(done.stdout) and "moved・finish が無い" in done.stderr, done
done = cli("report", up, "--built", "yes", "--moved", "not", "--finish", "3")
assert done.returncode == 0 and json.loads(done.stdout)["moved"] == "not" and done.stderr == "", done
assert cli("report", up, "--built", "yes", "--moved", "x").returncode == 4
# 再生リストを動画と読ませない: 決め打つと読めず、当て推量のままなら読み手が中の道を開く
(work / "list.mp4").write_text("#EXTM3U\n#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:1.0,\nfile:///etc/passwd\n#EXT-X-ENDLIST\n", encoding="utf-8")
assert tv._probe(work / "list.mp4", "mov") == (None, None) and tv.attach(up, work / "list.mp4", "mov")[1]
# 取り下げ: 動画もコマも札も消える。札の置き場が残っていると、自分の札を根拠と読んで断ってしまう
assert tv.add_mark(up, 5, 1, "cut", "札の文", "読み手")[0]
assert not records.withdraw(up)[1] and not tv._base(up).exists() and tv.load(up) is None
# 案の根拠になった記録は残す。動画とコマと札は消える（顔や声を、根拠の話のために残さない）
assert records.withdraw(rid)[1], "案の根拠の記録は、そのまま消さない"
assert not records.withdraw(rid, media_only=True)[1] and not tv._base(rid).exists() and tv.load(rid) is None and loop.record(rid)
# 映像の流れの中の情報: H.264 の SEI に入れた字が残らない。コマの絵は同じ
MARK = "SECRET-IN-STREAM"
sei = work / "sei.mov"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=5:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-bsf:v", f"h264_metadata=sei_user_data=086f3693b7b34f2c965321492feee5b8+{MARK}", str(sei)], check=True, capture_output=True, timeout=120)
assert MARK.encode() in sei.read_bytes(), "作り物に印が入っていない"
r4, _ = tv.new_record(G, GS, "動いた")
assert tv.attach(r4, sei)[1] == []
out_sei = tv._base(r4) / "v1.mp4"
assert MARK.encode() not in out_sei.read_bytes(), "流れの中の字を落とす"


def md5(path):
    made = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:V:0", "-f", "framemd5", "-"], capture_output=True, text=True, check=True).stdout
    return [x.split(",")[-1] for x in made.splitlines() if not x.startswith("#")]


assert md5(sei) == md5(out_sei), "絵は作り直さない"
# H.264 と HEVC でない形（コマごとに EXIF を持てる MJPEG）は作り直す
mjpeg = work / "mjpeg.mov"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=5:duration=3", "-c:v", "mjpeg", "-q:v", "5", str(mjpeg)], check=True, capture_output=True, timeout=120)
r5, _ = tv.new_record(G, GS, "動いた")
assert tv.attach(r5, mjpeg)[1] == []
codec = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "V:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(tv._base(r5) / "v1.mp4")], capture_output=True, text=True, check=True).stdout.strip()
assert codec == "h264", codec
# 写すと大きくなりすぎる物（同じ所を何度も指す動画）と、長さの欄が長すぎる物は断る
room, tv.ROOM = tv.ROOM, 1000 - src.stat().st_size
assert tv.attach(r5, src)[1], "大きくなりすぎる"
tv.ROOM = room
top, tv.MAX_SECONDS = tv.MAX_SECONDS, 1
assert tv.attach(r5, src)[1], "長すぎる"
tv.MAX_SECONDS = top
# 後ろが欠けた動画は、結んだ事にしない（入れ物の欄の長さと、写せた中身を比べる）
whole = work / "whole.mov"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=15:duration=20", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(whole)], check=True, capture_output=True, timeout=120)
cut = work / "cut.mov"
cut.write_bytes(whole.read_bytes()[:whole.stat().st_size // 3])
assert tv.attach(r5, cut, "mov")[1], "欠けた動画"
# 道具が止められた時は、動画のせいにしない（例外で分ける）
real_run = subprocess.run


def killed(*a, **k):
    subprocess.run = real_run
    return subprocess.CompletedProcess(a[0], -9, "", "")


subprocess.run = killed
try:
    tv._probe(src)
except tv.Interrupted:
    pass
else:
    raise AssertionError("止められた事が分からない")
# 受け口の記録はサイトの口で触れない。前例の読みにも出ない
keep_up, _ = tv.new_record(TORA, "H-A", records.UNSURE, note="上げた人の文その 2", via=records.UPLOADED)
assert loop.confirm_interpretation(keep_up, "確かめた人", "読み") == [] and all(r["id"] != keep_up for r in loop.confirmed_records(TORA))
server2 = serve(0)
threading.Thread(target=server2.serve_forever, daemon=True).start()
req = urllib.request.Request(f"http://127.0.0.1:{server2.server_address[1]}/record/{keep_up}/explain", data=b"by=x&text=y&next_idea=z", method="POST", headers={"Origin": f"http://127.0.0.1:{server2.server_address[1]}", "Content-Type": "application/x-www-form-urlencoded"})
try:
    urllib.request.urlopen(req)
except urllib.error.HTTPError as e:
    assert e.code == 404, e.code
else:
    raise AssertionError("受け口の記録に説明を書けた")
assert not loop.explanation(keep_up)
server2.shutdown()

# 外の受け口の置き場から移す: 作り物の受付（結んだ物・結ぶ前の物・止まった物・途中の物）
place = work / "place"
(place / "receipts").mkdir(parents=True)
(place / "inbox/V-0002").mkdir(parents=True)
(place / "data/records/media/R-0001").mkdir(parents=True)
(place / "data/loop").mkdir(parents=True)
shutil.copy(sei, place / "data/records/media/R-0001/v1.mp4")
(place / "data/loop/video-R-0001.json").write_text(json.dumps({"marks": [{"at": 1.0, "step": 3, "kind": "fold", "note": "折りで止まった", "read_by": "読み手", "confirmed_by": "確かめた人"}, {"at": 2.0, "step": None, "kind": "other", "note": "外した札", "read_by": "機械", "rejected_by": "確かめた人"}]}), encoding="utf-8")
(place / "receipts/V-0001.json").write_text(json.dumps({"receipt": "V-0001", "name": "IMG_0001.MOV", "sid": G, "note": "上げた人の文", "result": "動いた", "record": "R-0001", "stage": "waiting_maker"}), encoding="utf-8")
shutil.copy(sei, place / "inbox/V-0002/video.mp4")
(place / "inbox/V-0002/audio.mka").write_bytes(b"VOICE-PRIVATE")
(place / "receipts/V-0002.json").write_text(json.dumps({"receipt": "V-0002", "name": "IMG_0002.MOV", "sid": TORA, "note": "", "result": "", "stage": "waiting_maker", "draft_marks": [{"at": 1.0, "step": None, "kind": "other", "note": "動きの少ない区間", "read_by": "機械（止まった候補）", "confirmed_by": None}]}), encoding="utf-8")
(place / "receipts/V-0003.json").write_text(json.dumps({"receipt": "V-0003", "name": "x.mov", "sid": G, "stage": "error", "error": "読めない"}), encoding="utf-8")
(place / "receipts/V-0004.json").write_text(json.dumps({"receipt": "V-0004", "name": "y.mov", "sid": G, "stage": "received"}), encoding="utf-8")
(place / "receipts/V-0005.json").write_text(json.dumps({"receipt": "V-0005", "sid": "../../etc", "stage": "waiting_maker"}), encoding="utf-8")
before = len(records.all_records(uploads=True))
dry, fails = tv.take_in(place, dry_run=True)
assert {x for x, _ in dry} == {"V-0001", "V-0002", "V-0004"} and len(fails) == 1 and "形が違う" in fails[0].message and len(records.all_records(uploads=True)) == before, (dry, fails)
done = cli("take-in", str(place))
assert done.returncode == 3 and "V-0005" in done.stderr, (done.returncode, done.stderr[-300:])
moved = tv.taken_in()
assert set(moved) == {"V-0001", "V-0002"}, moved
first, second = loop.record(moved["V-0001"]), loop.record(moved["V-0002"])
assert first["via"] == records.UPLOADED and first["result"] == "動いた" and first["note"] == "上げた人の文" and first["upload"] == "V-0001" and first["source_id"] == G
assert second["result"] == records.UNSURE and second["source_id"] == TORA, "動いたかは決めつけない"
assert "IMG_000" not in json.dumps([first, second]) + json.dumps(moved), "元のファイルの名前を移さない"
marks = tv.load(moved["V-0001"])["marks"]
assert [(m["step"], m["kind"], m["note"], m["confirmed_by"], m["rejected_by"]) for m in marks] == [(3, "fold", "折りで止まった", "確かめた人", None), (None, "other", "外した札", None, "確かめた人")], marks
assert tv.load(moved["V-0002"])["marks"][0]["confirmed_by"] is None, "案は案のまま"
for rid_moved in moved.values():
    base_dir = tv._base(rid_moved)
    assert MARK.encode() not in (base_dir / "v1.mp4").read_bytes() and (base_dir / "frames/sheet-v1.png").exists(), "写し直す"
    assert not list(base_dir.rglob("*.mka")), "声は移さない"
assert (place / "inbox/V-0002/audio.mka").exists() and (place / "inbox/V-0002/video.mp4").exists(), "元の置き場は変えない"
assert rid_moved not in {r["id"] for r in records.all_records()}, "学ぶ人の頁と束に出ない"
# 2 回回しても移さない
count = len(records.all_records(uploads=True))
assert tv.take_in(place)[0] == [] and len(records.all_records(uploads=True)) == count
assert cli("take-in", str(work / "nothing")).returncode == 4, "置き場が無いのは 4"
print("ok: 動画から版まで")
