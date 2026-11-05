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

from omochae import loop, trial_video as tv  # noqa: E402
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
v_now = loop.latest_version(G, "H-A")
assert tv.adopt(d_drop, "本人")[1] and loop.latest_version(G, "H-A") == v_now, "外した札を根拠に版を作らない"
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
r2, _ = tv.new_record(G, "H-A", "動いた", version=2, tried_on="2026-11-06")
assert tv.attach(r2, src)[1] == []
tv.add_mark(r2, 20, 3, "cut", "溝を切る所で少し迷った", "本人")
tv.judge_mark(r2, "M1", "本人")
eff = tv.effect(G)["H-A"]
col2 = (rec["sheet_set"], 2)
assert eff["columns"] == [col, col2] and eff["rows"][8] == {col: {"video": 1, "tap": 0}} and eff["rows"][3] == {col2: {"video": 1, "tap": 0}}
assert eff["reports"] == {col: 1, col2: 1}
# 組の記録の無い前の記録は、同じ版の組へ寄せる（1 つの版が 2 列に割れない）。画面の札も同じ表に入る。組の版は数の順
from omochae import making_log, records  # noqa: E402

r_old, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた", "fixes": []})
making_log.add_step(G, "H-A", 1, 8, "stuck", who="")
eff = tv.effect(G)["H-A"]
assert eff["columns"] == [col, col2] and eff["reports"][col] == 2 and eff["rows"][8][col] == {"video": 1, "tap": 1}, eff
assert sorted([("goraigo-v10", 1), ("goraigo-v9", 1), ("", 1)], key=tv._version_order) == [("", 1), ("goraigo-v9", 1), ("goraigo-v10", 1)]

# エンジンの報告の形に書き出す。確かめた札だけが困り事になる。欄はエンジンの決まりの中だけ
rep, fails = tv.report(rid, True, finish=3, minutes=40)
assert not fails and rep["template"] == "slider_fan" and rep["form"] == "tab" and rep["moved"] == "not" and rep["built"] is True and rep["finish"] == 3
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
done = cli("attach", str(work / "none.mov"), "--source", G, "--hypothesis", "H-A", "--result", "動かない")
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
assert records.UNSURE not in records.results_for(TORA)
assert tv.new_record(TORA, "H-A", records.UNSURE)[1], "手で結ぶ記録は札の言葉だけ"
up, fails = tv.new_record(TORA, "H-A", records.UNSURE, note="上げた人の文", via=records.UPLOADED)
assert up and not fails, fails
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
print("ok: 動画から版まで")
