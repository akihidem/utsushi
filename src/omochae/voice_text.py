"""上げた動画の声を、この機械の中で字にしてから消す（本人の言葉 11-08「全部残していいことにしたい。」・本人の言葉 11-07「音声は文字化してから落とさないと価値が減る」）。

決まり: 字にしたら元の音は消す。字にできなければ 72 時間で消す（本人の決め 11-08）。字は作る側だけが読み、頁・束・AI に見せる口には出さない（決定 B）。
手帖の上げ口（web.techo_site・web.play_server）と動画の専用の口（web.video_up）が同じ置き場を使うので、ここに字にする所と掃除をまとめる。

判断の芯:
- 置き場は記録の写真と動画の箱の下の voice/（箱 0700・ファイル 0600・git の外）。頁へ返す道（techo_site.media_of）は箱の直下の m*.* だけを拾うので、
  voice/ は頁にも AI に見せる口（api.observe）にも出ない。取り下げ（records.withdraw）は箱ごと消すので、音も字も消える。
- 名は 2 つある。手帖は 1 本ずつ m<n>.mka（動画 m<n>.<ext> と同じ番号）、動画の専用の口は記録に 1 本の voice.mka（#388 から）。字は
  m<n>.transcript.json と transcript.json。どちらも同じ関数で扱い、字の在る音は 2 度字にしない。
- 字は残す前に、話す口と同じ入口の床（talk_log.blocked・連絡先と名乗りと学校の名の形）を区切りごとに通し、当たった区切りの字は伏せる
  （字にした事と、伏せた数だけを残す）。声から字にした文には、名前や学校の名が入りうるため。
- 順は 字を書く → 音を消す。間で止まっても、字の無いまま音が消える事は無い。書く前と書いた後に「まだ要るか」を聞き、取り下げと重なっても
  字を残さない（#492 と同じ守り）。
- 72 時間の掃除は、字にする道具の無い機械でも回す。道具が無いと字にし直せないので、掃除を道具に結ぶと音が残り続けるため。
- 字にするのは手元のモデルだけ（omochae.asr_worker・ネットへ行かない指定・requirements-asr.txt）。外のサービスへは送らない。

押した時だけ録る短い区切り（本人の言葉 11-08「声も送って解析に使う形にする。カメラの映像は、押した時の短い区切りだけ。」・窓口の決め
「声とカメラそれぞれ 5 つまで」）も同じ置き場に置く。受け口と録る頁は web.play_server（UX の担当の枝）で、ここは境目の関数だけを持つ
（設計は grove の state/voice-clip-names-design-20261108.md。名と引数は UX の担当の案のまま）。
- 声の区切りは t<n>.mka（受けた webm・mp4 から声の流れだけを copy_voice で写す。元の形は置かない）。字にして消す道は手帖の m<n> と同じ。
- カメラの区切りは k<n>.<webm|mp4>（絵の流れだけ・音と撮影の情報を落として入れ物を作り直す）。音が無いので字にする道具に入れず、
  読み（UX の枝の区切りの読み）が字を書けたら clip_done で消し、読めないまま 72 時間を過ぎたら sweep_clips が読まずに消す。
  人が写っていると分かった時は、clip_drop が読まずに今すぐ消す。
- 5 つは記録ごとの通しの数。番号は t<n>.・k<n>. で始まるファイル（音・字・控え・印）が持ち続ける。消した後に番号が空くと、
  6 つ目を受けてしまうため（k は読み終えた時に k<n>.done.json の印を残す）。
"""
import json
import os
import pathlib
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time

from . import records, store

LIMIT = 72 * 3600  # 秒。字にできなかった音を置く長さの上限（本人の決め 11-08）
CLIP_MAX = 5  # 声とカメラの区切りの、記録ごとの数の上限（窓口の決め 11-08。それぞれ 5 つまで）
VOICE_CLIP_BYTES = 2 * 1024 * 1024  # 声の区切り 1 つの上限（設計の 1 節。押して話す間の声）
CAM_CLIP_BYTES = 5 * 1024 * 1024  # カメラの区切り 1 つの上限（押した後の 10 秒・1 Mbps ほどで約 1.3MB）
# 区切りの形ごとの読み手（ffmpeg の -f）と書き手。読み手を決め打ち、中身の形で選ばせない（ほかのファイルや URL を指す一覧を読みに行くため・clean_video と同じ線）
CLIP_FORMATS = {"webm": ("matroska", "webm"), "mp4": ("mov", "mp4")}
RID = re.compile(r"R-\d{4,}")
CAM_NAME = re.compile(r"k(\d+)\.(webm|mp4)")
DROPPED_CLIP = "読まずに消した（72 時間）"
ASR_WORKER = pathlib.Path(__file__).resolve().parent / "asr_worker.py"
ASR_MODEL = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"  # 環境変数 OMOCHAE_ASR_MODEL で替えられる
CHECK_TIMEOUT = 120  # 秒。道具の確かめは読み込みだけ
COPY_TIMEOUT = 600  # 秒。20MB の動画の音を写すのに足りる長さ
HIDDEN = "［伏せた（{0}）］"


def voice_dir(rid):
    return records.folder() / "media" / rid / "voice"


def text_of(voice):
    """音のファイルに対する字のファイル。voice.mka → transcript.json（動画の専用の口の名）、m1.mka → m1.transcript.json。"""
    voice = pathlib.Path(voice)
    return voice.with_name("transcript.json" if voice.stem == "voice" else f"{voice.stem}.transcript.json")


def dropped_of(voice):
    """字にできずに消した印のファイル。"""
    voice = pathlib.Path(voice)
    return voice.with_name(f"{voice.stem}.dropped.json")


def tool_missing():
    """字にする道具が使えるか。Returns 使えない理由（使えれば空の字）。確かめは字にするのと同じ道（同じ python・同じ asr_worker）で回す。"""
    python = os.environ.get("OMOCHAE_ASR_PYTHON")
    if not python:
        return "OMOCHAE_ASR_PYTHON が無い"
    try:
        r = subprocess.run([python, "-I", str(ASR_WORKER), "--check", os.environ.get("OMOCHAE_ASR_MODEL", ASR_MODEL)], capture_output=True, text=True, timeout=CHECK_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as e:
        return f"確かめを回せない（{type(e).__name__}）"
    if r.returncode == 0:
        return ""
    return (r.stderr.strip().splitlines() or [f"確かめに落ちた（rc={r.returncode}）"])[-1][:200]


def copy_voice(src, dst, size, demuxer="mov"):
    """動画の音の流れだけを、撮影情報を外して dst に写す。Returns 写したか（音の無い動画・写せない形は False で、動画の受け取りは止めない）。
    読み手を決め打つ（-f mov）・読むのは置いたファイルだけ（-protocol_whitelist file）・大きさの上限（-fs）は、絵を写す所（techo_site.clean_video）と同じ線。"""
    dst = pathlib.Path(dst)
    probe = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file", "-f", demuxer, "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(src)],
                           capture_output=True, text=True, timeout=CHECK_TIMEOUT)
    if probe.returncode != 0 or "audio" not in probe.stdout:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.parent.chmod(0o700)
    try:
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file", "-f", demuxer, "-i", str(src), "-map", "0:a:0", "-c", "copy", "-vn", "-sn", "-dn",
                            "-map_metadata", "-1", "-map_chapters", "-1", "-fflags", "+bitexact", "-fs", str(size), "-f", "matroska", str(dst)], capture_output=True, timeout=COPY_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        dst.unlink(missing_ok=True)
        return False
    if r.returncode != 0 or not dst.exists():
        dst.unlink(missing_ok=True)
        return False
    dst.chmod(0o600)
    return True


CLIP_ROOM = 64 * 1024  # 写しの大きさの上限（-fs）に足す余り。入れ物の作り直しで、小さい区切りの頭の分だけ大きくなる事があるため


def _now(now=None):
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(time.time() if now is None else now))


def _write_mark(path, obj):
    """控えと印の json を、初めから 0600 で書く。置き場が無い（取り下げが消した）時は FileNotFoundError（置き場を作り直さない）。"""
    store.write_atomic(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n", mode=0o600)


def _write_private(path, data):
    """作る側だけが読めるファイルを、初めから 0600 で書く（書いてから chmod すると、間に読める時がある）。"""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)


def _clip_refused(rid, data, ext, limit):
    """区切りを受ける前の見張り。Returns 断りの字（受けてよければ空）。記録の番号は形を決め打つ（道をたどらせない）。
    頭のバイトは名乗った形と合うかだけを見る（webm は EBML の 1A45DFA3・mp4 は 4〜8 バイト目の ftyp）。中身が読めるかは写す所で見る。"""
    if not isinstance(rid, str) or not RID.fullmatch(rid) or not (records.folder() / f"{rid}.json").exists():
        return "記録が無い"
    if ext not in CLIP_FORMATS:
        return "区切りは webm か mp4 だけ"
    if not isinstance(data, (bytes, bytearray)) or not 0 < len(data) <= limit:
        return f"1 つ {limit // (1024 * 1024)}MB まで"
    if (data[:4] != b"\x1a\x45\xdf\xa3") if ext == "webm" else (data[4:8] != b"ftyp"):
        return "中身が webm か mp4 の形でない"
    return ""


def _free_slot(rid, kind):
    """kind（t か k）の次の空いた番号（1〜CLIP_MAX）。空きが無ければ None。番号は t<n>.・k<n>. で始まるファイル（音・字・控え・印）が持つので、
    字にした後・消した後も番号は空かない（5 つは記録ごとの通しの数）。"""
    d = voice_dir(rid)
    used = {int(m.group(1)) for p in (d.iterdir() if d.is_dir() else []) if (m := re.match(rf"{kind}(\d+)\.", p.name))}
    return next((n for n in range(1, CLIP_MAX + 1) if n not in used), None)


def _claim(tmpfile, rid, kind, ext):
    """置き場の中に書いた一時のファイルに、次の空いた番号の名（<kind><n>.<ext>）を、その名が無い時だけ付ける。Returns 付けた名 or None（空きが無い）。
    空いた番号を見てから置くまでの間に、同じ記録へ同時に届いたほかの区切りが同じ番号を置く事がある（#642 の確かめの気づき 11-08）。
    os.link は名が在れば落ちるので、置く所が 1 つの番号の取り合いの決め手になる（錠を持たずに、別の作業列や別のサーバの間でも効く）。
    落ちたら番号を見直す。1 度落ちるたびに番号が 1 つ埋まるので、CLIP_MAX 回で必ず終わる。"""
    for _ in range(CLIP_MAX):
        n = _free_slot(rid, kind)
        if n is None:
            return None
        dst = tmpfile.with_name(f"{kind}{n}.{ext}")
        try:
            os.link(tmpfile, dst)
        except FileExistsError:
            continue
        return dst.name
    return None


def _scratch(rid, ext):
    """置き場の中の一時のファイル（.tmp- で始まる名・0600）。名を付けるのは _claim の os.link なので、同じ置き場（同じファイルの仕組み）に書く。
    .tmp- の名は、字にする道具の待ち（pending）・番号（_free_slot）・カメラの区切りの並び（clips_waiting）のどれにも入らない。"""
    d = voice_dir(rid)
    d.mkdir(parents=True, exist_ok=True)
    d.chmod(0o700)
    fd, path = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=f".{ext}")
    os.close(fd)
    return pathlib.Path(path)


def put_voice_clip(rid, data, ext):
    """押して話した声の区切り（webm か mp4）を、声の流れだけ voice/t<n>.mka に写す。元の形は置かない（撮影の情報と絵を持ち込まない）。
    字にするのはサーバの作業列（Worker）で、手帖の m<n> と同じ道（pending・transcribe・72 時間の sweep）を通る。Returns (名 or None, 断りの字)。"""
    why = _clip_refused(rid, data, ext, VOICE_CLIP_BYTES)
    if why:
        return None, why
    if _free_slot(rid, "t") is None:
        return None, f"声の区切りは 1 つの記録に {CLIP_MAX} つまで"
    out = _scratch(rid, "mka")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = pathlib.Path(tmp) / "in"
            src.write_bytes(data)
            if not copy_voice(src, out, len(data) + CLIP_ROOM, demuxer=CLIP_FORMATS[ext][0]):
                return None, "声を読めない（声の流れが無いか、読めない形）"
        name = _claim(out, rid, "t", "mka")
    finally:
        out.unlink(missing_ok=True)
    return (name, "") if name else (None, f"声の区切りは 1 つの記録に {CLIP_MAX} つまで")


def put_cam_clip(rid, data, ext):
    """カメラの区切り（押した後の 10 秒）を voice/k<n>.<webm|mp4> に置く。絵の流れだけを写し、音と撮影の情報を落として入れ物を作り直す
    （絵は再符号化しない・techo_site.clean_video と同じ線）。端末は音なしで録るが、受け口に音や位置の入った物が来ても残さないため。
    頁へ返す道（techo_site.media_of）は箱の直下だけを拾うので、voice/ の区切りは頁にも束にも出ない。Returns (名 or None, 断りの字)。"""
    why = _clip_refused(rid, data, ext, CAM_CLIP_BYTES)
    if why:
        return None, why
    if _free_slot(rid, "k") is None:
        return None, f"カメラの区切りは 1 つの記録に {CLIP_MAX} つまで"
    reader, writer = CLIP_FORMATS[ext]
    with tempfile.TemporaryDirectory() as tmp:
        src, out = pathlib.Path(tmp) / "in", pathlib.Path(tmp) / f"out.{ext}"
        src.write_bytes(data)
        limit = len(data) + CLIP_ROOM
        try:
            r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file", "-f", reader, "-i", str(src),
                                "-map", "0:V", "-an", "-sn", "-dn", "-map_metadata", "-1", "-map_metadata:s", "-1", "-map_chapters", "-1", "-fflags", "+bitexact",
                                "-c", "copy", "-fs", str(limit), "-f", writer, str(out)], capture_output=True, timeout=COPY_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired):
            return None, "映像を読めない"
        # -fs は越えても 0 で終わるので、書けた大きさを後で比べる（途中で切れた物を置かない）
        if r.returncode != 0 or not out.exists() or not 0 < out.stat().st_size < limit:
            return None, "映像を読めない"
        scratch = _scratch(rid, ext)
        try:
            _write_private(scratch, out.read_bytes())
            name = _claim(scratch, rid, "k", ext)
        finally:
            scratch.unlink(missing_ok=True)
    return (name, "") if name else (None, f"カメラの区切りは 1 つの記録に {CLIP_MAX} つまで")


def _cam_path(rid, name):
    """記録の番号と区切りの名の形を決め打って、カメラの区切りの道を返す（形が違えば None）。"""
    if not isinstance(rid, str) or not isinstance(name, str) or not RID.fullmatch(rid) or not CAM_NAME.fullmatch(name):
        return None
    return voice_dir(rid) / name


def clips_waiting(rid):
    """まだ読んでいないカメラの区切りの名（k<n>.<ext>）の並び。番号の順。"""
    d = voice_dir(rid) if isinstance(rid, str) and RID.fullmatch(rid) else None
    if d is None or not d.is_dir():
        return []
    return sorted((p.name for p in d.iterdir() if CAM_NAME.fullmatch(p.name)), key=lambda x: int(CAM_NAME.fullmatch(x).group(1)))


def clip_wait(rid, name, why):
    """読めなかった理由（今日の上限・人の確かめ待ち・説明待ちなど）を k<n>.wait.json に控える。最後の理由で上書きする。
    72 時間を過ぎて読まずに消す時に、この理由を印へ移す。Returns 控えたか。"""
    p = _cam_path(rid, name)
    if p is None or not p.exists() or not isinstance(why, str) or not why.strip():
        return False
    try:
        _write_mark(p.with_name(f"{p.stem}.wait.json"), {"why": why.strip()[:80], "at": _now()})
    except FileNotFoundError:
        return False  # 控える間に取り下げが置き場を消した
    return True


def clip_done(rid, name):
    """読みの字が書けたカメラの区切りを消し、控えも消して、読み終えた印 k<n>.done.json を残す（番号を持ち続け、6 つ目を受けないため）。
    Returns 消したか（無い物・形の違う名は False）。"""
    p = _cam_path(rid, name)
    if p is None or not p.exists():
        return False
    p.unlink(missing_ok=True)
    p.with_name(f"{p.stem}.wait.json").unlink(missing_ok=True)
    try:
        _write_mark(p.with_name(f"{p.stem}.done.json"), {"at": _now()})
    except FileNotFoundError:
        pass  # 取り下げが置き場を消した。区切りは消えている
    return True


def clip_drop(rid, name, why):
    """読まずに今すぐカメラの区切りを消し、控えも消して、k<n>.dropped.json に why・at を残す（72 時間を待たない）。
    受け口の枝が、進め役が「人が写っている」と確かめた時と、Claude の答えに人が写っていると出た時（字を残さず区切りごと消す床）に呼ぶ。
    先に区切りを消してから印を書く（印が書けなくても区切りは残さない）。番号は印が持ち続ける。Returns 消したか（無い物・形の違う名・空の理由は False）。"""
    p = _cam_path(rid, name)
    if p is None or not p.exists() or not isinstance(why, str) or not why.strip():
        return False
    p.unlink(missing_ok=True)
    p.with_name(f"{p.stem}.wait.json").unlink(missing_ok=True)
    try:
        _write_mark(p.with_name(f"{p.stem}.dropped.json"), {"why": why.strip()[:80], "at": _now()})
    except FileNotFoundError:
        pass  # 取り下げが置き場を消した。区切りは消えている
    return True


def sweep_clips(now=None):
    """72 時間を過ぎたカメラの区切りを読まずに消し、k<n>.dropped.json に why・at（sweep の印と同じ形）と、最後に控えた理由 wait を残す。
    字にする道具の有無に関わらず回す（sweep と同じ）。読み終えた印と字には触らない。Returns 消した区切りの一覧。"""
    now = time.time() if now is None else now
    root = records.folder() / "media"
    if not root.exists():
        return []
    gone = []
    # 置く途中で止まって残った一時のファイル（_scratch）も、72 時間を過ぎたら消す（数にも頁にも入らないが、置き場を埋めないため）
    for t in root.glob("R-*/voice/.tmp-*"):
        try:
            if now - t.stat().st_mtime > LIMIT:
                t.unlink(missing_ok=True)
        except FileNotFoundError:
            continue
    for k in sorted(p for p in root.glob("R-*/voice/k*.*") if CAM_NAME.fullmatch(p.name)):
        try:
            age = now - k.stat().st_mtime
        except FileNotFoundError:
            continue
        if age <= LIMIT:
            continue
        wait = k.with_name(f"{k.stem}.wait.json")
        last = (store.read_json_or_skip(wait) or {}).get("why")
        k.unlink(missing_ok=True)
        try:
            _write_mark(k.with_name(f"{k.stem}.dropped.json"), {"why": DROPPED_CLIP, "at": _now(now), "wait": last})
        except FileNotFoundError:
            continue  # 取り下げと重なった。置き場ごと消えている
        wait.unlink(missing_ok=True)
        gone.append(k)
    return gone


def mask(data):
    """字の区切りごとに入口の床を通し、当たった区切りの字を伏せる。Returns (字, 伏せた数)。"""
    from . import talk_log

    hidden = 0
    for seg in data.get("segments", []):
        hit = talk_log.blocked(seg.get("text", ""))
        if hit:
            seg["text"] = HIDDEN.format(hit)
            hidden += 1
    return data, hidden


def transcribe(voice, still=lambda: True):
    """1 本の音を字にし、字を書けたら音を消す。still は「まだ要るか」（取り下げられていないか）を返す関数。
    Returns "done"（字がある）・"no-tool"（道具が無い。音は残り、掃除が 72 時間で消す）・"failed"（字にできない。同じ）・"gone"（もう要らない）。"""
    voice = pathlib.Path(voice)
    text = text_of(voice)
    if text.exists():
        voice.unlink(missing_ok=True)  # 字の在る音は 2 度字にしない。止まって残った音だけを消す
        return "done"
    if not voice.exists():
        return "gone"
    python = os.environ.get("OMOCHAE_ASR_PYTHON")
    if not python:
        return "no-tool"
    try:
        r = subprocess.run([python, "-I", str(ASR_WORKER), str(voice), os.environ.get("OMOCHAE_ASR_MODEL", ASR_MODEL)], capture_output=True, text=True, timeout=4 * 3600)
        data = json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        print(f"{voice.parent.parent.name}: 字にできない（{type(e).__name__}）", file=sys.stderr)
        data = None
    if not isinstance(data, dict):
        return "failed"
    if not still():
        return "gone"
    data, hidden = mask(data)
    data["hidden"] = hidden
    try:
        store.write_json(text, data)
        text.chmod(0o600)
    except FileNotFoundError:
        # 書く直前に取り下げが置き場を消した。消えた置き場を作り直して字を残さない
        return "gone"
    voice.unlink(missing_ok=True)
    if not still():
        text.unlink(missing_ok=True)
        return "gone"
    return "done"


def pending():
    """字にする前の音（字の無い音）。"""
    root = records.folder() / "media"
    if not root.exists():
        return []
    # 名は 3 つ: 動画の専用の口の voice・手帖の m<n>・声の区切りの t<n>（カメラの区切り k<n> は .mka でないので、ここに入らない）
    return sorted(v for v in root.glob("R-*/voice/*.mka") if re.fullmatch(r"voice|[mt]\d+", v.stem) and not text_of(v).exists())


def sweep(now=None):
    """72 時間を過ぎた字の無い音を消し、字にできずに消した事を残す。道具の有無に関わらず回す。Returns 消した音の一覧。"""
    now = time.time() if now is None else now
    gone = []
    for v in pending():
        try:
            age = now - v.stat().st_mtime
        except FileNotFoundError:
            continue
        if age <= LIMIT:
            continue
        v.unlink(missing_ok=True)
        mark = dropped_of(v)
        store.write_json(mark, {"why": "字にできずに消した（72 時間）", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now))})
        mark.chmod(0o600)
        gone.append(v)
    return gone


def still_wanted(voice):
    """その音の記録が、まだ取り下げられていないか（記録の json と、写真と動画の箱が在るか）。"""
    voice = pathlib.Path(voice)
    return (records.folder() / f"{voice.parent.parent.name}.json").exists() and voice.parent.is_dir()


QUEUE_MAX = 32  # 字にする前の声の待ち行列の長さ（web.load_guard.VOICE_QUEUE_MAX と同じ値）


def enqueue(worker, path):
    """作業列に声を入れる。満ちている時は入れずに False（声は置き場に残り、次に立てた時に回し直す）。"""
    try:
        worker.jobs.put_nowait(path)
        return True
    except queue.Full:
        return False


class Worker(threading.Thread):
    """1 本ずつ順に字にする作業列と、1 時間ごとの掃除。同時に字にすると、長い字にする間に機械のほかの作業を止めるため 1 本ずつ。
    字にする道具が無い時（tool=False）も、掃除だけは回す。立てた時に、前に止まって残った字の無い音を回し直す。
    掃除は音（sweep）とカメラの区切り（sweep_clips）の両方。受け口の枝が掃除を呼ばなくてよいように、ここで並べて回す。"""

    def __init__(self, tool, every=3600):
        super().__init__(daemon=True)
        self.tool, self.every = tool, every
        # 待ち行列の長さに上限（安全の事項 4 への対応・web.load_guard.VOICE_QUEUE_MAX と同じ値）。満ちた時に入れない声は置き場に残り、
        # 次に立てた時（pending）に回し直す。前は長さの上限が無く、上げ続けると覚えの量が増え続けた
        self.jobs = queue.Queue(maxsize=QUEUE_MAX)

    def sweeps(self):
        for fn in (sweep, sweep_clips):
            try:
                fn()
            except Exception as e:  # 片方の掃除が止まっても、もう片方と作業列を止めない（次の 1 時間で回し直す）
                print(f"掃除で止まった（{fn.__name__}・{type(e).__name__}）", file=sys.stderr)

    def run(self):
        self.sweeps()
        if self.tool:
            for v in pending():
                if not enqueue(self, v):
                    break  # 満ちた分は置き場に残る（次に立てた時に回し直す）
        while True:
            try:
                v = self.jobs.get(timeout=self.every)
            except queue.Empty:
                self.sweeps()
                continue
            try:
                if self.tool:
                    transcribe(v, still=lambda v=v: still_wanted(v))
            except Exception as e:  # 1 本の失敗で後の音を止めない。字の無い音は掃除が 72 時間で消す
                print(f"{pathlib.Path(v).parent.parent.name}: 字にする所で止まった（{type(e).__name__}）", file=sys.stderr)


def main(argv=None):
    """作る側が字を読む入口（頁は無い）。list: 字のある記録・字にする前の音・字にできずに消した数と、カメラの区切りの読む前の物・読まずに消した数。
    前からある 3 つの行の形は替えない（声の数え方は音の印だけにする。カメラの区切りの印は別の行で数える）。Returns 終わりの値（0 / 4 = 呼び方の誤り）。"""
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] != ["list"]:
        print("使い方: python -m omochae.voice_text list", file=sys.stderr)
        return 4
    root = records.folder() / "media"
    for t in sorted(root.glob("R-*/voice/*transcript.json")) if root.exists() else []:
        print(f"字\t{t.parent.parent.name}\t{t}")
    for v in pending():
        print(f"字にする前\t{v.parent.parent.name}\t{v.name}")
    marks = list(root.glob("R-*/voice/*.dropped.json")) if root.exists() else []
    cam = [m for m in marks if re.fullmatch(r"k\d+\.dropped\.json", m.name)]
    print(f"字にできずに消した\t{len(marks) - len(cam)}")
    for d in sorted(root.glob("R-*/voice")) if root.exists() else []:
        for name in clips_waiting(d.parent.name):
            print(f"区切り（読む前）\t{d.parent.name}\t{name}")
    print(f"読まずに消した\t{len(cam)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
