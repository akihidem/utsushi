"""作成の過程の動画を試行の記録に結び、止まった所 → 直しの案 → 型紙の版まで回す（本人の指示 2026-11-05、Issue #216、J-029）。

本人の言葉（窓口経由）: 作成の過程を動画で撮っている。それをフィードバックの仕組みに入れて、実際に型紙が改善するかを見たい。

判断の芯:
- 動画は git の外（記録の置き場の media/<記録>/v1.mp4）に置き、記録と番号で結ぶ。音と撮影情報は落とす（声なしの決まり J-022、位置情報を残さない）。
  H.264 と HEVC は絵を作り直さず、映像の流れの中の付帯情報（SEI）も落とす。ほかの形は流れの中の情報を落とせないので作り直す（MJPEG はコマごとに EXIF を持てる）。
- 学ぶ人の頁とギャラリーには出さない。名前を v で始めて、上げた物の一覧（techo_site.media_of の m*）に拾わせない。
  作る側の頁でも、人が動画ごとに「顔と声が入っていない」と確かめるまで、映像とコマを出さない（子どもの写真と声を扱わない決まり。仕様書 I2・J-021）。
  顔や声が入った動画は確かめないまま置き、札の字だけで回す（本人の決定 11-05）。
- コマを読むのは Claude でもよい。読むのは切り出したコマだけで、動画そのものは置き場から動かさない（同じ決定。J-022 の観察の補助）。
- 止まった候補は、機械が動きの少なさから拾うだけで、意味を付けない。作業の中で手を止める事はいくらでもあるので、止まったとは言わない。
- 札（何秒・どの手順・どんな困り事）は読みの案で、人が確かめた札だけを根拠に数える（F9。Claude の読みも人の読みも同じ床）。
- 直しの案は確かめた札を根拠に持ち、人の説明の後で、人が採るまで版にならない（J-013）。寸法は今の輪（loop の提案。F7 の向きの検査）、
  形や手順の文は雛形の直し（T-）。どちらも今の版の紙は変えない（凍結の床。tests/test_floor_pin.py）。
- 効いたかは、版ごとの止まった札を手順ごとに並べるだけにする。数件で「効いた」と判定しない。読むのは人。成績にしない（J-025）。
- 困り事の種類はエンジンの報告の言葉にそろえ、確かめた札をエンジンの報告の形で書き出せるようにする（入口と道具はエンジンの側。J-026）。

終了: 0 = 通る / 3 = 落ちる（理由を出す）/ 4 = 確かめられない（ffmpeg が無い・読めない）。
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time

from . import hypotheses, instructions, loop, making_log, records, store
from .compose import TEMPLATES
from .contrib import _human_confirm, check_pii
from .hypotheses import ROOT
from .model import Failure
from .store import SID as STORE_SID

# 困り事の種類。エンジンの報告（omochae.feedback の KINDS）と同じ言葉にして、そのまま渡せるようにする。型紙の外の 3 つ（案内・答え・サイト）も同じ。
KINDS = {"cut": "切る", "fold": "折る", "glue": "貼る", "fit": "はまり", "motion": "動き", "mark": "印や字", "material": "材料",
         "finish": "仕上がり", "guide": "案内", "answer": "聞く口の答え", "site": "サイト", "kufu": "人の工夫", "other": "そのほか"}
# 人の工夫の札。本人の言葉（11-05）「型紙は不完全でうまく動かないけどそれを人間が工夫で乗り切る過程をAIにフィードバックして型紙が改善される」
# 「カメラで見るのはそういうとこだよ」。カメラで見るのはこの過程で、人の出来を測るためではない。
# エンジンの報告の種類には無いので、報告では「そのほか」に文の頭の印を付けて渡す（エンジンの形を勝手に変えない）。止まった手順には数えない。
KUFU = "kufu"
TIMEOUT = 900  # 秒。長い動画を読む時の上限（返らなくても手順を止めない）
PROBE_TIMEOUT = 120  # 秒。頭を読むだけの上限
FRAME_TIMEOUT = 120  # 秒。一覧の 1 コマの上限
MAX_SECONDS = 6 * 3600  # 1 本の長さの上限。入れ物の欄は偽れるので、処理の前に断る
ROOM = 64 * 1024 * 1024  # 写す時に元より増えてよい量。同じコマを何度も指す小さな動画で、置き場を埋めさせない
RECORD_ID = re.compile(r"R-\d{4,}")
SEI = {"h264": "filter_units=remove_types=6", "hevc": "filter_units=remove_types=39|40"}  # コマの絵は変わらない
MIN_STILL = 20  # 秒。これより短い手の止まりは、候補に挙げない（持ち替えや確かめで普通に起きる）
FLOOR = 0.5  # 動きの少なさの下限。センサーの揺れを動きと読まないため


class Interrupted(OSError):
    """道具が止められた・時間切れ・場所が足りない。動画のせいではない（受け口は動画を消さずにやり直す）。"""


def _base(rid):
    return records.folder() / "media" / rid


def _path(rid):
    return loop.folder() / f"video-{rid}.json"


def load(rid):
    return store.read_json_or_skip(_path(rid))


def _save(rid, data):
    loop.folder().mkdir(parents=True, exist_ok=True)
    store.write_json(_path(rid), data)


def all_for(sid=None):
    """動画を結んだ記録の一覧（記録の番号の順）。sid があればその玩具だけ。"""
    out = []
    for p in sorted(loop.folder().glob("video-R-*.json")):
        d = store.read_json_or_skip(p)
        if d and (sid is None or d.get("source_id") == sid):
            out.append(d)
    return out


def _probe(path, demuxer=None):
    """(長さの秒, 映像の種類)。読めなければ (None, None)。demuxer は入れ物の形を決め打つ時（受け口）。形を当て推量で読ませると、
    動画に見せた再生リストの中の道を開いてしまう。長さは映像の流れの物（音だけ長い動画を、映像が欠けたと読まない）。"""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file", *(["-f", demuxer] if demuxer else []), "-select_streams", "V:0", "-show_entries", "stream=codec_name,duration:format=duration",
                            "-of", "json", str(path)], capture_output=True, text=True, timeout=PROBE_TIMEOUT)
    except subprocess.TimeoutExpired as e:
        raise Interrupted("ffprobe が時間切れ") from e
    except OSError:
        return None, None
    if r.returncode < 0:
        raise Interrupted("ffprobe が止められた")
    try:
        j = json.loads(r.stdout) if r.returncode == 0 else {}
        return float(j["streams"][0].get("duration") or j["format"]["duration"]), j["streams"][0]["codec_name"]
    except (ValueError, KeyError, IndexError):
        return None, None


def _span(path):
    """写した物の本当の中身 (映像のコマ数, 長さの秒)。入れ物の欄を信じず、数える。読めなければ (0, 0)。"""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file", "-count_packets", "-select_streams", "V:0", "-show_entries", "stream=nb_read_packets:format=duration",
                            "-of", "json", str(path)], capture_output=True, text=True, check=True, timeout=TIMEOUT)
        j = json.loads(r.stdout)
        return int(j["streams"][0]["nb_read_packets"]), float(j["format"]["duration"])
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError):
        return 0, 0.0


def still_spans(path, min_sec=MIN_STILL):
    """動きの少ない区間 [[始め, 終わり], …]（秒）。1 秒に 1 コマを小さな灰色にして、隣のコマとの差を見るだけ。映像は外へ出さない。
    手が止まった候補にすぎない。考えている時も、カメラの外で作業している時も同じに見える。"""
    w, h = 64, 36
    size = w * h
    try:
        p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vf", f"fps=1,scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return []
    # 全部をメモリに溜めない。1 つ前のコマだけを持つ（長さを偽った小さな動画で、機械のメモリを埋めさせない）。
    timer = threading.Timer(TIMEOUT, p.kill)
    timer.start()
    diffs, last = [], None
    try:
        while len(cur := p.stdout.read(size)) == size:
            if last is not None:
                diffs.append(sum(abs(a - b) for a, b in zip(last, cur)) / size)
            last = cur
    finally:
        p.stdout.close()
        finished = p.wait() == 0
        timer.cancel()
    if not (finished and diffs):
        return []
    # 物差しは上から 1/4 の所の動き。中央の値にすると、止まっている時間が長い動画で物差しごと下がり、止まりを見逃す。
    line = max(FLOOR, 0.35 * statistics.quantiles(diffs, n=4)[2]) if len(diffs) >= 4 else FLOOR
    spans, start = [], None
    for i, d in enumerate(diffs + [line + 1]):  # 終わりで必ず閉じる
        if d < line and start is None:
            start = i
        elif d >= line and start is not None:
            if i - start >= min_sec:
                spans.append([start, i])
            start = None
    return spans


def steps_of(sid, hid, version=1):
    """その版の手順の文。手順の紙と同じ雛形の steps。作れない時は空（札の手順の番号の検査をしない）。"""
    data = hypotheses.load(sid)
    h = next((x for x in data["hypotheses"] if x["id"] == hid), None)
    if h is None:
        return []
    try:
        params, _ = loop.version_params(sid, hid, version)
        template = h.get("template") or data.get("template", "slider_fan")
        return [str(s) for s in instructions.steps({**TEMPLATES[template].DEFAULTS, **(params or h.get("params") or {})}, template)]
    except Exception:
        return []


def new_record(sid, hid, result, version=1, tried_on="", note="", via="video", upload="", video_kind=""):
    """動画を結ぶ試行の記録を作る。刷った組（goraigo-v10 など）を一緒に残す: 版が上がった後に、どの紙の試行かが分かるように。"""
    data = hypotheses.load(sid)
    h = next((x for x in data["hypotheses"] if x["id"] == hid), None)
    template = (h or {}).get("template") or data.get("template", "slider_fan")
    return records.add({"source_id": sid, "hypothesis_id": hid, "sheet_version": version, "result": result, "sheet_set": TEMPLATES[template].SHEET_SET,
                        **({"tried_on": tried_on} if tried_on else {}), "note": note, "fixes": [], "via": via, **({"upload": upload} if upload else {}), **({"video_kind": video_kind} if video_kind else {})})


def attach(rid, src, demuxer=None):
    """動画を記録に結ぶ。音と撮影情報を落として置き場へ写し、止まった候補を拾う。元のファイルには触らない。返り値は (動画の項目, 失敗の list)。"""
    try:
        loop.record(rid)
    except ValueError as e:
        return None, [Failure("F8.references", rid, str(e))]
    src = pathlib.Path(src)
    if not src.is_file():
        return None, [Failure("F8.references", str(src.name), "動画のファイルが無い")]
    dur, codec = _probe(src, demuxer)
    if dur is None:
        return None, [Failure("F3.result", src.name, "動画として読めない（ffmpeg が無い時も）")]
    if dur > MAX_SECONDS:
        return None, [Failure("F3.result", src.name, f"長すぎる（{MAX_SECONDS // 3600} 時間まで）")]
    d = _base(rid)
    d.mkdir(parents=True, exist_ok=True)
    # H.264 と HEVC は作り直さない（-c copy）。-tag:v hvc1 は iPhone の HEVC を Safari で再生するため。音・字幕・撮影情報（位置など）は写さない。
    # ほかの形は作り直す（流れの中の情報を落とせない。ProRes は MP4 に入らない）。どちらも大きさの上限を付ける。-fs は超えても 0 で終わるので、後で比べる。
    size = src.stat().st_size
    limit = size + ROOM if codec in SEI else max(2 * size, 256 * 1024 * 1024)
    video = ["-c", "copy", "-bsf:v", SEI[codec]] if codec in SEI else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"]
    tag = ["-tag:v", "hvc1"] if codec == "hevc" else []
    # 重い所（写す・候補を拾う）は排他の外で行い、数分かかる動画の間も頁の確かめの口を止めない。名前を決めて置くのは _register の排他の中。
    with tempfile.TemporaryDirectory(dir=d) as tmp:
        out = pathlib.Path(tmp) / "take.mp4"
        try:
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file", *(["-f", demuxer] if demuxer else []), "-i", str(src), "-map", "0:V:0", *video, "-an", "-sn", "-dn", "-map_metadata", "-1",
                            "-map_chapters", "-1", "-fs", str(limit), "-movflags", "+faststart", *tag, str(out)], capture_output=True, check=True, timeout=TIMEOUT if codec in SEI else 4 * TIMEOUT)
        except subprocess.TimeoutExpired as e:
            raise Interrupted("ffmpeg が時間切れ") from e
        except subprocess.CalledProcessError as e:
            if e.returncode < 0:
                raise Interrupted("ffmpeg が止められた") from e
            return None, [Failure("F3.result", src.name, "音と撮影情報を落とせなかった（動画の形を確かめる）")]
        except OSError:
            return None, [Failure("F3.result", src.name, "音と撮影情報を落とせなかった（ffmpeg が無い時も）")]
        if out.stat().st_size >= limit:
            return None, [Failure("F3.result", src.name, "写すと元より大きくなりすぎる（同じ所を何度も指す動画かもしれない）")]
        # 入れ物の欄の長さと、本当に写せた中身を比べる。中身の無い動画や後ろの欠けた動画を、受け取った事にしない。
        packets, seconds = _span(out)
        if not packets or seconds < 0.9 * dur:
            return None, [Failure("F3.result", src.name, "動画の中身が足りない（外を指す動画か、後ろが欠けた動画かもしれない）")]
        return _register(rid, out, round(seconds, 1), still_spans(out)), []


@loop.exclusive
def _register(rid, out, duration, still):
    rec = loop.record(rid)
    cur = load(rid) or {"record_id": rid, "source_id": rec["source_id"], "hypothesis_id": rec["hypothesis_id"], "sheet_version": rec.get("sheet_version", 1),
                        "sheet_set": rec.get("sheet_set", ""), "videos": [], "marks": []}
    name = f"v{len(cur['videos']) + 1}.mp4"
    shutil.move(str(out), _base(rid) / name)
    item = {"file": name, "duration": duration, "still": still, "attached_at": loop._now(), "checked_by": None}
    cur["videos"].append(item)
    _save(rid, cur)
    return item


def frame(rid, video, at, timeout=TIMEOUT):
    """動画の at 秒のコマを切り出して置き場に残す。読む時と作る側の頁で使う。写真は git に入らない（置き場は media の下）。"""
    f = _base(rid) / "frames" / f"{pathlib.Path(video).stem}-{int(at):06d}.jpg"
    if f.exists():
        return f
    f.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", str(_base(rid) / video), "-frames:v", "1", "-vf", "scale=640:-1", "-q:v", "4", str(f)],
                       capture_output=True, check=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return f if f.exists() else None


def contact(rid, video, every, out):
    """読むための一覧の 1 枚（every 秒ごとのコマに時刻を書いて並べる）。札を付ける人や Claude が、全部を再生せずに流れを追うため。"""
    from PIL import Image, ImageDraw

    d = load(rid)
    item = next(v for v in d["videos"] if v["file"] == video)
    # 読むのを助ける物なので、全体の時間を決める。1 本で後ろの動画を長く止めない。
    end = time.monotonic() + TIMEOUT
    cells = []
    for t in range(0, int(item["duration"]) + 1, every):
        if time.monotonic() > end:
            break
        f = frame(rid, video, t, FRAME_TIMEOUT)
        if f:
            cells.append((t, f))
    cols, w, h = 5, 320, 200
    sheet = Image.new("RGB", (cols * w, ((len(cells) + cols - 1) // cols) * h), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)
    for i, (t, f) in enumerate(cells):
        im = Image.open(f).convert("RGB")
        im.thumbnail((w - 6, h - 24))
        x, y = (i % cols) * w + 3, (i // cols) * h + 3
        sheet.paste(im, (x, y))
        draw.text((x + 2, y + h - 22), f"{t // 60:02d}:{t % 60:02d}", fill=(255, 255, 255))
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return len(cells)


@loop.exclusive
def add_mark(rid, at, step, kind, note, read_by, video="v1.mp4"):
    """札を足す。人が確かめるまでは案で、数えない。返り値は (札の ID, 失敗の list)。"""
    d = load(rid)
    out = []
    if d is None:
        return None, [Failure("F8.references", rid, "動画を結んだ記録が無い")]
    item = next((v for v in d["videos"] if v["file"] == video), None)
    if item is None:
        return None, [Failure("F8.references", video, "その動画は結んでいない")]
    if not 0 <= at <= item["duration"]:
        out.append(Failure("F3.result", "at", f"時刻は 0〜{item['duration']} 秒"))
    total = len(steps_of(d["source_id"], d["hypothesis_id"], d.get("sheet_version", 1)))
    if step is not None and total and not 1 <= step <= total:
        out.append(Failure("F3.result", "step", f"手順は 1〜{total}"))
    if kind not in KINDS:
        out.append(Failure("F3.result", "kind", f"種類は {'・'.join(KINDS)} のどれか"))
    if not (note or "").strip():
        out.append(Failure("F3.result", "note", "何が起きたかの一言が要る"))
    if not (read_by or "").strip():
        out.append(Failure("F9.human", "read_by", "読んだ人（または読んだ道具）の名前が要る"))
    out += [Failure("F3.result", "note", f.message) for f in check_pii({"body": note or ""})]
    if out:
        return None, out
    mid = f"M{len(d['marks']) + 1}"
    d["marks"].append({"id": mid, "video": video, "at": round(at, 1), "step": step, "kind": kind, "note": note.strip(), "read_by": read_by.strip(), "confirmed_by": None, "rejected_by": None})
    _save(rid, d)
    frame(rid, video, at)
    return mid, []


@loop.exclusive
def judge_mark(rid, mid, by, accept=True):
    """人が札を確かめる（または外す）。確かめた札だけが根拠になる。"""
    d = load(rid)
    m = next((x for x in (d or {}).get("marks", []) if x["id"] == mid), None)
    if m is None:
        return [Failure("F8.references", mid, "その札は無い")]
    if not (by or "").strip():
        return [Failure("F9.human", mid, "確かめた人の名前が無い")]
    m["confirmed_by" if accept else "rejected_by"] = by.strip()
    m["rejected_by" if accept else "confirmed_by"] = None
    _save(rid, d)
    return []


@loop.exclusive
def confirm_shown(rid, by, video="v1.mp4"):
    """人が映像を見て、顔と声が入っていないと確かめた印。これが無いと作る側の頁にも映像とコマを出さない。
    動画ごとに持つ: 記録ごとにすると、確かめた後に結んだ 2 本目が、見ないまま出てしまう（検品で再現）。"""
    d = load(rid)
    if d is None:
        return [Failure("F8.references", rid, "動画を結んだ記録が無い")]
    item = next((v for v in d["videos"] if v["file"] == video), None)
    if item is None:
        return [Failure("F8.references", video, "その動画は結んでいない")]
    if not (by or "").strip():
        return [Failure("F9.human", rid, "確かめた人の名前が無い")]
    item["checked_by"] = by.strip()
    _save(rid, d)
    return []


def shown(rid, video):
    """その動画の映像とコマを、作る側の頁に出してよいか（人が確かめた動画だけ）。"""
    d = load(rid)
    return bool(d and any(v["file"] == video and v.get("checked_by") for v in d["videos"]))


def _fix_path(fid):
    return loop.folder() / f"fix-{fid[2:]}.json"


def fixes(sid=None):
    out = [f for p in sorted(loop.folder().glob("fix-*.json")) if (f := store.read_json_or_skip(p))]
    return [f for f in out if sid is None or f.get("source_id") == sid]


@loop.exclusive
def propose(rid, mark_ids, text, drafted_by, param=None, to=None):
    """直しの案。根拠は確かめた札で、人の説明が先（J-013）。param があれば寸法を 1 つ変える案、無ければ形や手順の文の案。"""
    d = load(rid)
    out = []
    if d is None:
        return None, [Failure("F8.references", rid, "動画を結んだ記録が無い")]
    if loop.explanation(rid) is None:
        out.append(Failure("F9.human", rid, "人の説明が先に要る"))
    marks = {m["id"]: m for m in d["marks"]}
    if not mark_ids:
        out.append(Failure("F4.evidence", "marks", "根拠の札が要る"))
    for mid in mark_ids:
        if mid not in marks:
            out.append(Failure("F8.references", mid, "その札は無い"))
        elif not marks[mid].get("confirmed_by"):
            out.append(Failure("F9.human", mid, "人が確かめた札だけが根拠になる"))
    if not (text or "").strip():
        out.append(Failure("F3.result", "text", "何をどう直すかの文が要る"))
    if not (drafted_by or "").strip():
        out.append(Failure("F9.human", "drafted_by", "案を書いた人の名前が要る"))
    if out:
        return None, out
    fid = loop.save_numbered("fix", "D", lambda i: {"id": i, "record_id": rid, "source_id": d["source_id"], "hypothesis_id": d["hypothesis_id"], "mark_ids": list(mark_ids),
                                                     "text": text.strip(), "param": param, "to": to, "drafted_by": drafted_by.strip(), "status": "pending_human", "drafted_at": loop._now()})
    return fid, []


def _finish(fix, **made):
    fix.update(status="adopted", decided_at=loop._now(), **made)
    store.write_json(_fix_path(fix["id"]), fix)


@loop.exclusive
def adopt(fid, by, sheet_set="", commit="", decided_in="", printer=None):
    """人が案を採る。寸法の案は今の輪で次の版を作って刷る（F7 の向きの検査が落とせば版にならない）。形や手順の案は雛形の直し（T-）の記録にする。
    雛形を実際に直すのはエンジンの側の受け持ちなので、T- には直した組と commit を要る物として求める（まだ直していない案を、直した事にしない）。"""
    fix = store.read_json_or_skip(_fix_path(fid))
    if fix is None:
        return None, [Failure("F8.references", fid, "その案は無い")]
    if fix["status"] != "pending_human":
        return None, [Failure("F9.human", fid, f"状態 {fix['status']} の案は採れない")]
    if not (by or "").strip():
        return None, [Failure("F9.human", fid, "採った人の名前が無い")]
    rid, sid, hid = fix["record_id"], fix["source_id"], fix["hypothesis_id"]
    # 案を作った後に札が外された時に備えて、採る時にも床を当てる（loop.adopt と同じ考え）。
    marks = {m["id"]: m for m in (load(rid) or {}).get("marks", [])}
    bad = [mid for mid in fix["mark_ids"] if not (marks.get(mid) or {}).get("confirmed_by")]
    if bad:
        return None, [Failure("F9.human", mid, "根拠の札が、人の確かめた札ではなくなった") for mid in bad]
    if fix.get("param"):
        # 今の輪は、確定した解釈を提案の床に求める。人がもう確定した解釈は上書きしない。無い時だけ案の文で確定し、採れなかったら元へ戻す
        # （前は検査に落ちても、案の文が人の確定した解釈として残った。検品で再現）。
        before = loop.interpretation(rid)
        had = bool(before and before.get("status") == "confirmed")
        def undo():
            if had:
                return
            if before is None:
                loop.interp_path(rid).unlink(missing_ok=True)
            else:
                store.write_json(loop.interp_path(rid), before)
        if not had:
            failures = loop.confirm_interpretation(rid, by, fix["text"])
            if failures:
                return None, failures
        source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
        pid, failures = loop.save_proposal({"record_ids": [rid], "hypothesis_id": hid, "changes": [{"param": fix["param"], "to": fix["to"], "why": fix["text"]}]}, source, "human")
        if failures:
            undo()
            return None, failures
        made, failures = loop.adopt(pid, by, accept_params=[fix["param"]], source=source)
        if failures or "version" not in (made or {}):
            undo()
            return None, failures or [Failure("F7.revision", fid, "次の版ができなかった")]
        version = made["version"]
        # 版の記録はもう残っている。刷れない時（道具が無いなど）も案は採った事にする。止めると、案は採れないまま版だけが増える（検品で再現）。
        # 刷る口は 1 つ前の版へ戻るので、紙が刷れなくなる事は無い。
        try:
            printed = (printer(sid, hid, version) if printer else 0) == 0
        except Exception:
            printed = False
        _finish(fix, decided_by=by.strip(), version=version, proposal=pid, printed=printed)
        return {"version": version, "printed": printed}, []
    tid, failures = loop.save_template_change([rid], sheet_set, commit, [fix["text"]], by, decided_in)
    if failures:
        return None, failures
    _finish(fix, decided_by=by.strip(), template_change=tid, sheet_set=sheet_set, commit=commit)
    return {"template_change": tid}, []


@loop.exclusive
def reject(fid, by):
    fix = store.read_json_or_skip(_fix_path(fid))
    if fix is None:
        return [Failure("F8.references", fid, "その案は無い")]
    if fix["status"] != "pending_human":
        return [Failure("F9.human", fid, f"状態 {fix['status']} の案は変えられない")]  # 版になった案を「採らない」に見せない
    if not (by or "").strip():
        return [Failure("F9.human", fid, "決めた人の名前が無い")]
    fix.update(status="rejected", decided_by=by.strip(), decided_at=loop._now())
    store.write_json(_fix_path(fid), fix)
    return []


def _version_order(col):
    """列の並び: 組の版は数で比べる（文字の順だと goraigo-v10 が goraigo-v9 の前に来る）。組の記録の無い列は先頭。"""
    m = re.fullmatch(r"(.*?)-v(\d+)", col[0] or "")
    return (m.group(1), int(m.group(2)), col[1]) if m else (col[0] or "", -1, col[1])


def effect(sid):
    """版にどう効いたかを読むための表。{仮説: {"columns": [(刷った組, 版)…], "rows": {手順: {列: {"video": 確かめた札, "tap": 画面の札}}}, "reports": {列: 報告の数}}}。
    判定はしない。数件の比べなので、数は読む人の手がかりにすぎない。"""
    raw = {}  # {仮説: [(組, 版, 種類, 手順)]}。先に集めて、組の記録の無い物を後で寄せる

    def note(hid, sheet_set, version, what, step=None):
        raw.setdefault(hid, []).append((sheet_set or "", version, what, step))

    for r in records.all_records(sid, uploads=True):
        note(r["hypothesis_id"], r.get("sheet_set"), r.get("sheet_version", 1), "report")
    for d in all_for(sid):
        for m in d["marks"]:
            if m.get("confirmed_by") and m.get("step") is not None:
                note(d["hypothesis_id"], d.get("sheet_set"), d.get("sheet_version", 1), "video", m["step"])
        note(d["hypothesis_id"], d.get("sheet_set"), d.get("sheet_version", 1), "seen")
    for e in making_log.steps(sid):
        if e.get("event") == "stuck":
            note(e.get("hypothesis_id", ""), e.get("sheet_set"), e.get("sheet_version", 1), "tap", e["step"])
    out = {}
    for hid, items in raw.items():
        # 前の記録には組の欄が無い物がある。同じ版の組が 1 つに決まる時はそこへ寄せる（1 つの版が 2 列に割れて、報告と札が別の列に並ぶのを避ける）。
        named = {}
        for sheet_set, version, _, _ in items:
            if sheet_set:
                named.setdefault(version, set()).add(sheet_set)
        col_of = lambda ss, v: (ss or (next(iter(named[v])) if len(named.get(v, ())) == 1 else ""), v)
        cols, rows, reports = [], {}, {}
        for sheet_set, version, what, step in items:
            col = col_of(sheet_set, version)
            if col not in cols:
                cols.append(col)
            if what == "report":
                reports[col] = reports.get(col, 0) + 1
            elif what in ("video", "tap"):
                cell = rows.setdefault(step, {}).setdefault(col, {"video": 0, "tap": 0})
                cell[what] += 1
        out[hid] = {"columns": sorted(cols, key=_version_order), "rows": dict(sorted(rows.items())), "reports": reports}
    return out


def report(rid, built, finish=None, minutes=None, gave_up=None, finish_notes="", moved=None):
    """確かめた札を、エンジンの報告の形に書き出す（入口と道具はエンジンの側。J-026）。組み上がったか・仕上がりは動画から決めず、人が言う。
    動いたかは記録の見た事から読む。雛形の RESULTS の先頭が動いた側、末尾が動かない側（「わからない」は少し動いた扱いにしない）。
    moved は、記録に書いてない時に人が動画を見て選ぶ値（値を作らない）。"""
    d = load(rid)
    if d is None:
        return None, [Failure("F8.references", rid, "動画を結んだ記録が無い")]
    rec = loop.record(rid)
    data = hypotheses.load(rec["source_id"])
    h = next((x for x in [*data["hypotheses"], *hypotheses.own_hypotheses(rec["source_id"])] if x["id"] == rec["hypothesis_id"]), {})
    template = h.get("template") or data.get("template", "slider_fan")
    # 寸法は、その記録の版の物（版 2 の報告を版 1 の寸法で渡すと、エンジンが別の寸法の困り事と読む）。
    try:
        params = loop.version_params(rec["source_id"], rec["hypothesis_id"], rec.get("sheet_version", 1))[0] or {}
    except ValueError:
        params = h.get("params") or {}
    results = list(records.results_for(rec["source_id"]))
    moved = moved or ("moved" if rec["result"] == results[0] else "partly" if rec["result"] in ("少し動いた", "少し遊べた") else "not" if rec["result"] in ("動かない", "揺れない", "戻らない", "回らない", "鳴らない", "遊べない", "転がらない", "倒れた") else None)
    confirmed = [m for m in d["marks"] if m.get("confirmed_by")]
    # 形の名前はエンジンの雛形の FORM（この repo の雛形の写しには無いので、ここに持つ）。
    form = params.get({"slider_fan": "push_part", "pivot_counterweight": "mount"}.get(template, "form"))
    out = {"template": template, **({"form": form} if form else {}), "source_id": rec["source_id"], "params": params, "built": bool(built), "motion_notes": rec.get("impression") or rec.get("note", ""),
           "finish_notes": finish_notes, "problems": [{"kind": "other", "step": m["step"], "note": "工夫: " + m["note"]} if m["kind"] == KUFU else {"kind": m["kind"], "step": m["step"], "note": m["note"]} for m in confirmed], "reported_at": rec.get("recorded_at", "")}
    if moved:
        out["moved"] = moved
    if finish is not None:
        out["finish"] = finish
    if minutes is not None:
        out["minutes"] = minutes
    if gave_up is not None:
        out["gave_up"] = gave_up
    stuck = sorted({m["step"] for m in confirmed if m.get("step") is not None and m["kind"] != KUFU})
    if stuck:
        out["stuck_step"] = stuck[0]
    return out, []


def make_sheet(rid):
    """読むための一覧の 1 枚を、最初の動画から作る。作れなくても動画の受け取りは止めない。Returns 一覧のファイルの道か空。"""
    item = load(rid)["videos"][0]
    sheet = _base(rid) / "frames" / f"sheet-{pathlib.Path(item['file']).stem}.png"
    try:
        contact(rid, item["file"], max(10, -(-int(item["duration"]) // 60)), sheet)
    except Exception as e:
        print(f"{rid}: コマの一覧を作れない（{type(e).__name__}）", file=sys.stderr)
        return ""
    return str(sheet)


def _taken_path():
    return loop.folder() / "taken-in.json"


def taken_in():
    """もう移した受付の表 {受付: 記録}。"""
    return store.read_json_or_skip(_taken_path()) or {}


def _take_one(place, slip):
    """受付 1 つを移す。Returns (記録の番号か None, 失敗の list)。"""
    sid, bound = slip["sid"], slip.get("record")
    source = place / "data/records/media" / bound / "v1.mp4" if bound else place / "inbox" / slip["receipt"] / "video.mp4"
    if not source.is_file():
        return None, []  # まだ処理の途中か、止まった受付。動画が無い物は移さない
    if bound and not RECORD_ID.fullmatch(bound):
        return None, [Failure("F8.references", slip["receipt"], "結んだ記録の番号の形が違う")]
    # 動いたかは、上げた人か作る側が選んだ時だけ持ってくる。無ければ決めつけない
    result = slip.get("result") if slip.get("result") in records.results_for(sid) else records.UNSURE
    hid = hypotheses.sheet_of(sid)["id"]
    rid, failures = new_record(sid, hid, result, loop.latest_version(sid, hid), note=slip.get("note") or "", via=records.UPLOADED, upload=slip["receipt"])
    if failures:
        return None, failures
    # 写し直す。元の口の写しに残った流れの中の情報も、ここで落ちる
    item, failures = attach(rid, source, "mov")
    if failures:
        records.withdraw(rid)
        return None, failures
    marks = (store.read_json_or_skip(place / "data/loop" / f"video-{bound}.json") or {}).get("marks", []) if bound else slip.get("draft_marks", [])
    out = []
    for m in marks:
        mid, bad = add_mark(rid, m.get("at", 0), m.get("step"), m.get("kind", "other"), m.get("note", ""), m.get("read_by", ""), item["file"])
        out += bad
        if mid and (m.get("confirmed_by") or m.get("rejected_by")):
            out += judge_mark(rid, mid, m.get("confirmed_by") or m.get("rejected_by"), accept=bool(m.get("confirmed_by")))
    make_sheet(rid)
    return rid, out


def take_in(place, dry_run=False):
    """repo の外の受け口が受け取った物（その置き場の受付と動画と札の案）を、この入口の記録へ写す。Returns ([(受付, 記録か "")], 失敗の list)。
    何度回しても同じ受付を 2 回移さない（移した表を持つ）。元の置き場は変えない（受け口は動いたまま、そこの頁が元を読むため）。
    声は移さない。声そのものを残さない決まりで、字にするかは本人の決定を待つ。ファイルの名前も移さない。"""
    place = pathlib.Path(place)
    if not (place / "receipts").is_dir():
        raise FileNotFoundError(f"受付の置き場が無い: {place.name}/receipts")
    done, moved, failures = taken_in(), [], []
    for path in sorted((place / "receipts").glob("V-*.json")):
        slip = store.read_json_or_skip(path)
        if slip is None or slip.get("receipt") != path.stem or path.stem in done or slip.get("stage") == "error":
            continue
        if not re.fullmatch(STORE_SID, slip.get("sid", "")):
            failures.append(Failure("F8.references", path.stem, "玩具の印の形が違う"))
            continue
        if dry_run:
            moved.append((path.stem, ""))
            continue
        rid, bad = _take_one(place, slip)
        failures += [Failure(f.check, f"{path.stem}: {f.where}", f.message) for f in bad]
        if rid:
            done[path.stem] = rid
            loop.folder().mkdir(parents=True, exist_ok=True)
            store.write_json(_taken_path(), done)
            moved.append((path.stem, rid))
    return moved, failures


def _say(failures):
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3


def main(argv=None):
    # 終わりの番号は repo の決まり（0・3・4 だけ）。引数の間違いと、読めない記録は「確かめられない」の 4。
    try:
        return _main(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 4
    except (KeyError, TypeError, ValueError, StopIteration, OSError) as e:
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.trial_video")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("attach", help="動画を記録に結ぶ。--record か、--source と --hypothesis と --result で記録を作る")
    s.add_argument("video")
    for a in ("--record", "--source", "--hypothesis", "--result", "--tried-on", "--note"):
        s.add_argument(a, default="")
    s.add_argument("--version", type=int, default=1)
    s = sub.add_parser("sheet", help="読むための一覧の 1 枚を作る")
    s.add_argument("record")
    s.add_argument("out")
    s.add_argument("--video", default="v1.mp4")
    s.add_argument("--every", type=int, default=30)
    s = sub.add_parser("mark", help="札を足す（案）")
    s.add_argument("record")
    s.add_argument("--at", type=float, required=True)
    s.add_argument("--step", type=int)
    s.add_argument("--kind", required=True)
    s.add_argument("--note", required=True)
    s.add_argument("--read-by", required=True)
    s.add_argument("--video", default="v1.mp4")
    s = sub.add_parser("confirm", help="札を人が確かめる")
    s.add_argument("record")
    s.add_argument("mark")
    s.add_argument("--by", required=True)
    s = sub.add_parser("drop", help="札を人が外す")
    s.add_argument("record")
    s.add_argument("mark")
    s.add_argument("--by", required=True)
    s = sub.add_parser("show-ok", help="顔と声が入っていないと人が確かめた印（動画ごと）")
    s.add_argument("record")
    s.add_argument("--video", default="v1.mp4")
    s.add_argument("--by", required=True)
    s = sub.add_parser("propose", help="直しの案")
    s.add_argument("record")
    s.add_argument("--marks", required=True, help="M1,M2")
    s.add_argument("--text", required=True)
    s.add_argument("--by", required=True)
    s.add_argument("--param")
    s.add_argument("--to", type=float)
    s = sub.add_parser("adopt", help="人が案を採る")
    s.add_argument("fix")
    s.add_argument("--by", required=True)
    s.add_argument("--sheet-set", default="")
    s.add_argument("--commit", default="")
    s.add_argument("--decided-in", default="")
    s = sub.add_parser("reject", help="人が案を採らない")
    s.add_argument("fix")
    s.add_argument("--by", required=True)
    s = sub.add_parser("take-in", help="repo の外の受け口が受け取った物を、この入口の記録へ写す。声と元のファイルの名前は移さない")
    s.add_argument("place", help="受け口の置き場（receipts・inbox・data がある所）")
    s.add_argument("--dry-run", action="store_true", help="移す受付の番号だけを出す")
    s = sub.add_parser("report", help="エンジンの報告の形に書き出す")
    s.add_argument("record")
    s.add_argument("--built", choices=("yes", "no"), required=True)
    s.add_argument("--finish", type=int)
    s.add_argument("--minutes", type=int)  # エンジンの報告の検査は整数だけを通す
    s.add_argument("--moved", choices=("moved", "partly", "not"), help="記録に書いてない時に、人が動画を見て選ぶ")
    s.add_argument("--finish-notes", default="")
    args = ap.parse_args(argv)

    if args.cmd == "attach":
        rid = args.record
        if not shutil.which("ffmpeg"):
            print("検査できない: ffmpeg が無い", file=sys.stderr)
            return 4
        made_here = not rid
        if made_here:
            # 動画を先に確かめる。読めない動画のために記録を作ると、動画の無い報告が残って数を増やす（検品で再現）。
            if _probe(args.video)[0] is None:
                return _say([Failure("F3.result", pathlib.Path(args.video).name, "動画として読めない（無いファイルも）")])
            rid, failures = new_record(args.source, args.hypothesis, args.result, args.version, args.tried_on, args.note)
            if failures:
                return _say(failures)
        item, failures = attach(rid, args.video)
        if failures:
            if made_here:
                (records.folder() / f"{rid}.json").unlink(missing_ok=True)
            return _say(failures)
        print(json.dumps({"record": rid, **item}, ensure_ascii=False))
        return 0
    if args.cmd == "take-in":
        moved, failures = take_in(args.place, args.dry_run)
        for slip, rid in moved:
            print(slip, rid or "（移していない）", load(rid)["videos"][0]["file"] if rid else "")
        return _say(failures) if failures else 0
    if args.cmd == "sheet":
        print(contact(args.record, args.video, args.every, args.out))
        return 0
    if args.cmd == "mark":
        mid, failures = add_mark(args.record, args.at, args.step, args.kind, args.note, args.read_by, args.video)
        if failures:
            return _say(failures)
        print(mid)
        return 0
    # 人の判断の命令は、端末で人が番号を打った時だけ進める（loop の命令と同じ床）。AI や自動の処理が「本人」と名乗って札を確かめ、案を採る事を止める。
    who = {"confirm": "mark", "drop": "mark", "show-ok": "record", "adopt": "fix", "reject": "fix"}.get(args.cmd)
    if who and not _human_confirm(getattr(args, who), {"confirm": "札の確かめ", "drop": "札を外す事", "show-ok": "顔と声の確かめ", "adopt": "採用", "reject": "不採用"}[args.cmd]):
        return _say([Failure("F9.human", getattr(args, who), "端末での人の確認が無い")])
    if args.cmd in ("confirm", "drop"):
        failures = judge_mark(args.record, args.mark, args.by, accept=args.cmd == "confirm")
        return _say(failures) if failures else 0
    if args.cmd == "show-ok":
        failures = confirm_shown(args.record, args.by, args.video)
        return _say(failures) if failures else 0
    if args.cmd == "propose":
        to = args.to
        if to is not None and float(to).is_integer():
            to = int(to)  # 折りの数のような整数の寸法を、小数で渡さない（範囲の検査が落とすため）
        fid, failures = propose(args.record, re.split(r"[,、\s]+", args.marks.strip()), args.text, args.by, args.param, to)
        if failures:
            return _say(failures)
        print(fid)
        return 0
    if args.cmd == "adopt":
        def printer(sid, hid, v):
            # 刷った紙の置き場は画面（play_server.out_dir）と同じ。採った版がすぐ窓に出るように。
            base = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "play" if os.environ.get("OMOCHAE_DATA") else ROOT / "out/play"
            (base / sid).mkdir(parents=True, exist_ok=True)
            return hypotheses.print_sheet(sid, hid, str(base / sid / f"{hid}_v{v}"), v)
        made, failures = adopt(args.fix, args.by, args.sheet_set, args.commit, args.decided_in, printer)
        if failures:
            return _say(failures)
        print(json.dumps(made, ensure_ascii=False))
        return 0
    if args.cmd == "reject":
        failures = reject(args.fix, args.by)
        return _say(failures) if failures else 0
    if args.cmd == "report":
        out, failures = report(args.record, args.built == "yes", args.finish, args.minutes, None, args.finish_notes, args.moved)
        if failures:
            return _say(failures)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        lacking = [k for k in ("moved", "finish") if k not in out]
        if lacking:
            # 人の言葉が無い値は作らない。エンジンの入口が断る事だけを知らせる
            print(f"{'・'.join(lacking)} が無いので、エンジンの報告の検査は通らない。人が動画を見て付けるか、確かめた札を束で渡す", file=sys.stderr)
        return 0
    return 4


if __name__ == "__main__":
    sys.exit(main())
