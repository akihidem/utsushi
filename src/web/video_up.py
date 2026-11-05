"""動画を上げる専用の口（本人の指示 11-05、#337）。

本人の指示: 『江都二色』の再現の経験がある大人の教え子から、作った時の動画を受け取る。合言葉付きのリンクで開く専用の頁で、ブラウザから複数上げる。
自動で撮影情報を外し、試行の動画の入口（omochae.trial_video。札とコマ読み）を通して、各玩具のたたき台の改善の輪へ回す。上げた人に受け取りが見える。
もう 1 つの形（本人の指示 20:35「作る前の型紙のレビューを、江戸二色を再現したことのある教え子にしてもらった動画の入り口も作って」）: 同じ仕組みの別の口（--kind review）。
レビューは話が本体なので、声を非公開で残し、この機械の中で字にする（omochae.asr_worker）。字を作る側のセッションが読んで札の案を書き、人が確かめる（本物の API はまだ動かしていない）。
声は整理が終わったら消す（drop-voice）。声も字も動画も頁に出さない。

判断の芯:
- サイトの道に足さず、小さなサーバを別に立てる。リンクを渡した相手に、記録や写真の頁を見せる道を作らないため。合言葉が無いと立たない。
- 大きな動画はトンネルの 1 回の送信の上限（100MB）を越えるので、小分けで受ける。切れても、同じ動画を選び直せば続きから送れる。
- 受け取りの返事の後で処理する。つなぐ・読むに数分かかり、トンネルの待ち時間（100 秒）を越えるため。1 本ずつ順に回す。止まっても次に立てた時に続ける。
- 動画でない物は記録にしない。入れ物の頭を見て MP4 と MOV だけを通し、形を決め打って読む。当て推量で読ませると、動画に見せた再生リストの中の道を ffmpeg が開く。
- 残すのは受付に要る物だけ。ファイルの名前・番地・機器は残さない。ログも書かない（URL に合言葉が入る）。
- 札は付けない。止まった候補とコマの一覧までが機械で、札は読みの案として人か Claude が付け、人が確かめる（J-029）。顔と声の確かめも人がする。
- 上げた人の文は感想でなく note の欄に入れる。感想はギャラリーに出るので、「頁に出さない」の約束に反する。記録は records.UPLOADED の印で学ぶ人の頁と束から外す。

終了: 0 = 通る / 3 = 落ちる（理由を出す）/ 4 = 呼び方の誤り・確かめられない。
"""
import argparse
import hmac
import json
import os
import pathlib
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from omochae import hypotheses, loop, making_log, records, store, trial_video
from omochae.contrib import MAX_BODY, check_pii
from omochae.hypotheses import ROOT
from omochae.model import Failure
from omochae.store import SID

from . import skin as skinmod
from .play_server import TUNNEL_HOST
from .skin import esc
from .toys import sources

CHUNK = 8 * 1024 * 1024  # 小分けの 1 つ。切れた時のやり直しが少なく、遅い回線でもトンネルの待ち時間に収まる大きさ
MAX_FILE = 5 * 1024 ** 3  # 1 本の上限。長い作成の過程を撮った物が入る大きさ
MIN_FREE = 40 * 1024 ** 3  # 空きがこれを切ったら受けない。ほかの作業の置き場を埋めない
MAX_FORM = 64 * 1024
MAX_STATUS = 200
KEEP_PARTS = 3 * 24 * 3600  # 秒。送りかけで止まった小分けを残す長さ。続きから送れるように数日は残す
COOKIE = "utsushi_up"
UNSURE = records.UNSURE
UPLOAD_ID = re.compile(r"[0-9a-f]{32}")
SLIP = re.compile(r"U-\d{4,}")
BAD_TEXT = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069\ud800-\udfff]")  # 制御の字と、片割れの字。受付に書けず、一覧を読む端末も乱す
TRIES = 3  # 機械の都合で止まった時に回し直す回数
RETRY_WAIT = 30  # 秒。機械の都合の失敗の後に待つ長さ。続く時は倍にしていく
MAX_RETRY_WAIT = 1800  # 秒
SWEEP_EVERY = 3600  # 秒
FINAL = ("done", "failed", "withdrawn")
BOXES = (b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide", b"pnot")  # MP4 と MOV の頭の箱。頁の側の確かめも同じ字を見る
FORMAT = "mov"  # ffmpeg の読み手の名前（MP4 と MOV は同じ読み手）

# 頁の文。本人が採った文（11-05、#337）。一字も変えない。tests/test_video_up.py が文字列で見る。
# 載せる事の 1 文は、本人の決まり（11-05「コマ切りでの写真や語られた言葉で印象的な物は、引用してHPにのせてok」「これからあがるすべての動画も同様」）に合わせて、本人が採った文。
TITLE = "動画を送る"
LEAD = "『江都二色』のおもちゃを作った時の動画を送る頁です。型紙のたたき台を直すために使います。"
PROMISES = (
    "音と、いつ・どこでとったかなどの情報は、受け取る時に自動で消します。",
    "声と動画そのものは、サイトの頁に出しません。切り出した絵（紙と手の所）と、話した言葉の一部を、名前などを除いて、サイトに載せる事があります。載せる前に人が見ます。",
    "動画から切り出した絵を、作る側の人と AI（Claude）が読みます。見るのは、手が止まった所と工夫した所です。",
    "型紙を直すかどうかは、人が決めます。作った人の出来に点は付けません。",
    "取り下げたい時は、受付番号を、リンクを渡した人に伝えてください。動画も切り出した絵も消します。",
)
AGREE_PEOPLE = "とった人と、映っている人の許しをもらっています。"
AGREE_ADULT = "私は 18 歳以上です。子どもは映っていません。"
ASK_NAME = making_log.ASK_NAME_TEXT
KEEP_OPEN = "送っている間は、この頁を開いたままにしてください。途中で切れたら、同じ動画を選んで、もう一度「送る」を押してください。続きから送ります。"
NEED_KEY = "合言葉付きのリンクから開いてください。リンクを渡した人に聞いてください。"
WORDS = {
    "waiting": "順番を待っています。",
    "working": "読み取っています。",
    "done": "受け取りました。音と、いつ・どこでとったかなどの情報を消しました。",
    "failed": "読み取れませんでした。MP4 か MOV の動画か確かめて、もう一度送ってください。",
    "withdrawn": "取り下げました。動画と切り出した絵を消しました。",
}
# レビューの口の文。本人が採った文（11-05）。一字も変えない。tests/test_video_up.py が文字列で見る。
REVIEW_TITLE = "型紙のレビューの動画を送る"
REVIEW_LEAD = "『江都二色』のおもちゃの型紙を、作る前に見て話した動画を送る頁です。型紙のたたき台を直すために使います。"
REVIEW_PROMISES = (
    "いつ・どこでとったかなどの情報は、受け取る時に自動で消します。",
    "声は、字にして整理するために、この機械の中にだけ置きます。整理が終わったら消します。",
    "声と動画そのものは、サイトの頁に出しません。切り出した絵（紙と手の所）と、話した言葉の一部を、名前などを除いて、サイトに載せる事があります。載せる前に人が見ます。",
    "字にした言葉と、動画から切り出した絵を、作る側の人と AI（Claude）が読みます。見るのは、型紙のどこをどう直すとよいかです。",
    "型紙を直すかどうかは、人が決めます。話した人に点は付けません。",
    "取り下げたい時は、受付番号を、リンクを渡した人に伝えてください。動画も声も字も消します。",
)
REVIEW_WORDS = {"done": "受け取りました。いつ・どこでとったかなどの情報を消しました。", "withdrawn": "取り下げました。動画と声と字を消しました。"}
KINDS = {
    "making": {"title": TITLE, "lead": LEAD, "promises": PROMISES, "words": WORDS, "toy_question": "どのおもちゃですか", "made_with": ("sheet", "own"), "keep_voice": False, "video_kind": ""},
    "review": {"title": REVIEW_TITLE, "lead": REVIEW_LEAD, "promises": REVIEW_PROMISES, "words": {**WORDS, **REVIEW_WORDS}, "toy_question": "どのおもちゃの型紙ですか", "made_with": ("review",), "keep_voice": True, "video_kind": "review"},
}
# 紙を見て作ったか。自分のやり方で作った動画は、手順の文の困り事として数えられないので、読む人に分かるように文の頭に残す
MADE_WITH = {"sheet": "", "own": "自分のやり方で作った動画。", "review": "作る前の型紙のレビューの動画。"}
ASR_WORKER = pathlib.Path(__file__).resolve().parents[1] / "omochae" / "asr_worker.py"
ASR_MODEL = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"  # 手元のモデル。環境変数 OMOCHAE_ASR_MODEL で替えられる
MADE_WITH_LABEL = {"sheet": "うつしの型紙", "own": "自分のやり方"}
NOTE_MAX = MAX_BODY - max(len(v) for v in MADE_WITH.values())  # 文の頭に残す字の分を引く。記録の長さの床で、送った後に落とさない
_lock = threading.Lock()


def folder():
    """受付と小分けの置き場。動画は記録に結ぶまでここにあるので、本人だけが読める形にする。"""
    d = records.folder().parent / "video_uploads"
    (d / "tmp").mkdir(parents=True, exist_ok=True)
    d.chmod(0o700)
    return d


class Withdrawn(Exception):
    """処理の間に取り下げられた受付。書き戻すと、消した文と記録の番号が元に戻る。"""


def _save(slip):
    path = folder() / f'{slip["id"]}.json'
    now = store.read_json_or_skip(path)
    if now and now.get("state") == "withdrawn" and slip.get("state") != "withdrawn":
        raise Withdrawn(slip["id"])
    store.write_json(path, slip)


def slips():
    """受付の一覧（番号の順）。読む量が少ないので、毎回読む。"""
    out = [s for p in sorted(folder().glob("U-*.json")) if (s := store.read_json_or_skip(p))]
    return sorted(out, key=lambda s: int(s["id"][2:]))


def sweep():
    """送りかけで止まった古い小分けと、終わった受付の残りを消す。待っている受付の物には触らない。"""
    open_slips = {s["id"] for s in slips() if s["state"] not in FINAL}
    for d in (folder() / "tmp").iterdir():
        if not d.is_dir():
            continue
        if UPLOAD_ID.fullmatch(d.name):
            old = time.time() - d.stat().st_mtime > KEEP_PARTS
        else:
            old = d.name.startswith("job-") and d.name[4:] not in open_slips
        if old:
            shutil.rmtree(d, ignore_errors=True)


def _parts(uid):
    d = folder() / "tmp" / uid
    return sorted(int(p.name) for p in d.iterdir() if p.name.isdigit()) if d.is_dir() else []


def existing(uid, toy):
    """同じ動画を同じおもちゃへ送った受付。同じ物が 2 本に数えられるのを防ぐ（返事が届かなかった時のやり直しも、選び直しも）。読めなかった物と取り下げた物は数えない。"""
    return next((s for s in slips() if s.get("upload") == uid and s.get("source_id") == toy and s["state"] not in ("failed", "withdrawn")), None)


def check_form(body, kind="making"):
    """上げた人の答えを確かめる。Returns 断りの文か None。送る前と受け取りで同じ物を当てる。"""
    toy, made_with = body.get("toy"), body.get("made_with")
    if not (isinstance(toy, str) and toy in sources()):
        return "おもちゃを選んでください。"
    if not (isinstance(made_with, str) and made_with in KINDS[kind]["made_with"]):
        return "何を見て作りましたかを選んでください。"
    if body.get("agree_people") is not True:
        return "とった人と、映っている人の許しを確かめてください。"
    if body.get("agree_adult") is not True:
        return "18 歳以上かどうかを確かめてください。"
    note = body.get("note", "")
    if not isinstance(note, str) or BAD_TEXT.search(note):
        return "伝えたい事の字が読めません。"
    if len(note) > NOTE_MAX:
        return f"文が長すぎます。{NOTE_MAX} 字までにしてください。"
    for f in check_pii({"body": note}):
        kind = re.search("メールアドレス|電話番号|郵便番号", f.message)
        return f"文の中に{kind.group(0) if kind else '住所や電話番号'}の形があります。消してから送ってください。"
    return None


def accept(body, wake=None, kind="making"):
    """小分けがそろった動画を受付にする。Returns (状態の番号, 返事)。ここでは動画を読まない（トンネルの待ち時間を越えないため）。"""
    why = check_form(body, kind)
    if why:
        return 422, {"error": why}
    uid, chunks, size = body.get("id"), body.get("chunks"), body.get("size")
    if not (isinstance(uid, str) and UPLOAD_ID.fullmatch(uid) and type(chunks) is int and type(size) is int and 0 < chunks <= MAX_FILE // CHUNK + 1 and size > 0):
        return 400, {"error": "送り方の形が違います。"}
    if size > MAX_FILE:
        return 413, {"error": _too_big()}
    with _lock:
        same = existing(uid, body["toy"])
        if same:
            return 200, {"receipt": same["id"], "token": same["token"]}
        have = set(_parts(uid))
        missing = [n for n in range(chunks) if n not in have]
        if missing:
            return 409, {"missing": missing}
        d = folder() / "tmp" / uid
        if sum((d / str(n)).stat().st_size for n in range(chunks)) != size:
            return 422, {"error": "大きさが合いません。もう一度送ってください。"}
        # 番号は受付と残った小分けの両方から数える。同じ番号で次の人の受付を止めない
        numbers = [int(s["id"][2:]) for s in slips()] + [int(p.name[6:]) for p in (folder() / "tmp").glob("job-U-*") if p.name[6:].isdigit()]
        slip = {"id": f"U-{max(numbers, default=0) + 1:04d}", "token": secrets.token_hex(16), "upload": uid, "source_id": body["toy"],
                "made_with": body["made_with"], "note": body.get("note", "").strip(), "size": size, "chunks": chunks, "state": "waiting", "at": loop._now(), "agreed": True, "kind": kind}
        # 受付を先に書く。書けなかった時に小分けを動かさない（送り直せる形のまま）。名前を受付の物に変えるのは、同じ動画を別のおもちゃへ送り直す人が、処理の途中の小分けを動かさないように
        path = folder() / f'{slip["id"]}.json'
        store.write_json(path, slip, exclusive=True)
        try:
            os.replace(d, folder() / "tmp" / f'job-{slip["id"]}')
        except OSError:
            path.unlink(missing_ok=True)
            raise
    if wake:
        wake(slip["id"])
    return 200, {"receipt": slip["id"], "token": slip["token"]}


def _too_big():
    return f"大きすぎます。1 本 {MAX_FILE // 1024 ** 3}GB までです。"


def looks_like_video(path):
    with open(path, "rb") as f:
        head = f.read(8)
    return len(head) == 8 and head[4:] in BOXES


def _join(slip, job):
    """小分けを 1 つにつなぐ。途中で止まっても、次に立てた時につなぎ直せる。"""
    joined = job / "joined"
    if joined.exists():
        return joined
    part = job / "joined.part"
    with open(part, "wb") as out:
        for n in range(slip["chunks"]):
            with open(job / str(n), "rb") as f:
                shutil.copyfileobj(f, out, 1024 * 1024)
    os.replace(part, joined)
    for n in range(slip["chunks"]):
        (job / str(n)).unlink(missing_ok=True)
    return joined


def _keep_voice(joined, rid, size):
    """声を非公開で残す（レビューの口）。音の流れだけを写し、撮影情報は写さない。頁へ返す道は無い（media_of は m で始まる物だけを拾う）。Returns 残したか。"""
    probe = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file", "-f", FORMAT, "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(joined)],
                           capture_output=True, text=True, timeout=trial_video.PROBE_TIMEOUT)
    if probe.returncode != 0 or "audio" not in probe.stdout:
        return False
    d = trial_video._base(rid) / "voice"
    d.mkdir(parents=True, exist_ok=True)
    d.chmod(0o700)
    out = d / "voice.mka"
    try:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file", "-f", FORMAT, "-i", str(joined), "-map", "0:a:0", "-c", "copy", "-vn", "-sn", "-dn", "-map_metadata", "-1", "-map_chapters", "-1",
                        "-fflags", "+bitexact", "-fs", str(size + trial_video.ROOM), str(out)], capture_output=True, check=True, timeout=trial_video.TIMEOUT)
    except subprocess.TimeoutExpired as e:
        raise trial_video.Interrupted("声を写す ffmpeg が時間切れ") from e
    except subprocess.CalledProcessError as e:
        if e.returncode < 0:
            raise trial_video.Interrupted("声を写す ffmpeg が止められた") from e
        # 声の形のせいで写せない時も、動画は受け取る
        print(f"{rid}: 声を写せない", file=sys.stderr)
        out.unlink(missing_ok=True)
        return False
    out.chmod(0o600)
    return True


def _text_path(rid):
    return trial_video._base(rid) / "voice" / "transcript.json"


def _note_text(slip_id, state, text_file=""):
    """字の様子を受付に書く。Returns False（字はできていない時の返り値に使う）。読み直して書くので、取り下げた受付を元に戻さない。"""
    slip = store.read_json_or_skip(folder() / f"{slip_id}.json")
    if slip and slip.get("state") == "done":
        slip["text"] = state
        if text_file:
            slip["text_file"] = text_file
        _save(slip)
    return False


def transcribe(slip_id):
    """声を字にする。道具が無い時や失敗した時は、受付に残して先へ進む（動画は受け取れている）。Returns 字にできたか。"""
    path = folder() / f"{slip_id}.json"
    slip = store.read_json_or_skip(path)
    if not slip or slip.get("state") != "done" or not slip.get("record"):
        return False
    voice = trial_video._base(slip["record"]) / "voice" / "voice.mka"
    if not voice.exists():
        return _note_text(slip_id, "no-voice")
    python = os.environ.get("OMOCHAE_ASR_PYTHON")
    if not python:
        return _note_text(slip_id, "no-tool")
    try:
        r = subprocess.run([python, "-I", str(ASR_WORKER), str(voice), os.environ.get("OMOCHAE_ASR_MODEL", ASR_MODEL)], capture_output=True, text=True, timeout=4 * trial_video.MAX_SECONDS)
        data = json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        print(f"{slip_id}: 字にできない（{type(e).__name__}）", file=sys.stderr)
        data = None
    if not data:
        return _note_text(slip_id, "failed")
    # 字にしている間に取り下げられていたら、字を書かない
    if (store.read_json_or_skip(path) or {}).get("state") != "done" or not voice.parent.is_dir():
        return False
    store.write_json(_text_path(slip["record"]), data)
    _text_path(slip["record"]).chmod(0o600)
    _note_text(slip_id, "done", str(_text_path(slip["record"])))
    return True


def drop_voice(slip_id):
    """整理が終わった声を消す。字と動画は残る。Returns 失敗の一覧。"""
    if not (isinstance(slip_id, str) and SLIP.fullmatch(slip_id)):
        return [Failure("F8.references", str(slip_id), "受付番号の形が違う")]
    slip = store.read_json_or_skip(folder() / f"{slip_id}.json")
    if slip is None or not slip.get("record"):
        return [Failure("F8.references", slip_id, "その受付に記録が無い")]
    (trial_video._base(slip["record"]) / "voice" / "voice.mka").unlink(missing_ok=True)
    slip["voice_dropped"] = loop._now()
    _save(slip)
    return []


def _take_in(slip, job):
    """1 本を記録に結ぶ。Returns 受け取れたか。動画と読めない物には記録を作らない。機械の都合で止まった時は例外（動画のせいにしない）。"""
    sid, rid = slip["source_id"], slip.get("record")
    if not rid:
        # 記録を作った直後に止まった時は、その記録を使う。同じ動画の記録を 2 つ作らない
        rid = next((r["id"] for r in records.all_records(sid, uploads=True) if r.get("upload") == slip["id"]), None)
        if rid:
            slip["record"] = rid
    if not (rid and (trial_video.load(rid) or {}).get("videos")):
        # もう結んだ動画は、つなぎ直さない（止まった後の回し直し）
        if not job.is_dir():
            return False  # 元が無いので、待っても読めない
        if shutil.disk_usage(folder()).free < 2 * slip["size"] + CHUNK:
            raise trial_video.Interrupted("読み取る場所が足りない")
        joined = _join(slip, job)
        if not looks_like_video(joined) or trial_video._probe(joined, FORMAT)[0] is None:
            return False
        if not rid:
            # その玩具のたたき台の紙（J-032）。版は次の人の型紙になる最新の版
            hid = hypotheses.sheet_of(sid)["id"]
            rid, failures = trial_video.new_record(sid, hid, UNSURE, loop.latest_version(sid, hid), note=MADE_WITH[slip["made_with"]] + slip["note"], via=records.UPLOADED, upload=slip["id"],
                                                   video_kind=KINDS[slip.get("kind", "making")]["video_kind"])
            if failures:
                print(f'{slip["id"]}: 記録を作れない: {failures[0].line()}', file=sys.stderr)
                return False
            slip["record"] = rid
            _save(slip)
        _, failures = trial_video.attach(rid, joined, FORMAT)
        if failures:
            print(f'{slip["id"]}: 結べない: {failures[0].message}', file=sys.stderr)
            return False
    # 声は元のファイルにしか無いので、元を消す前に写す（結んだ後に止まった時も、元があれば写す）
    if KINDS[slip.get("kind", "making")]["keep_voice"] and "voice" not in slip and (job / "joined").exists():
        slip["voice"] = _keep_voice(job / "joined", rid, slip["size"])
    item = trial_video.load(rid)["videos"][0]
    slip["sheet"] = trial_video.make_sheet(rid)  # 読む人の手間を減らす物で、作れなくても動画の受け取りは止めない
    return True


def _forget(rid):
    """受け取れなかった動画の記録を片づける。動画も文も残さない。案の根拠になっていれば、動画と札と文だけを消す。"""
    _, failures = records.withdraw(rid)
    if failures:
        records.withdraw(rid, media_only=True)
        rec = store.read_json_or_skip(records.folder() / f"{rid}.json")
        if rec:
            store.write_json(records.folder() / f"{rid}.json", {**rec, "note": ""})


def process(slip_id):
    """受付を 1 つ処理する。Returns もう一度回すまでの秒（回さない時は 0）。上げた元は、終わったら残さない。
    機械の都合（道具が止められた・時間切れ・場所が足りない）で止まった時は、回数で諦めない。元を残して待ち、次に立てた時も続ける。相手のファイルのせいにしない。
    回数で止めて元を消すのは、それ以外の失敗（作りの誤り）だけ。読めないと分かった動画は、その場で断る。"""
    path = folder() / f"{slip_id}.json"
    slip = store.read_json_or_skip(path)
    if not slip or slip.get("state") not in ("waiting", "working"):
        return 0
    job = folder() / "tmp" / f"job-{slip_id}"
    try:
        slip["state"] = "working"
        _save(slip)
        if not job.exists() and (folder() / "tmp" / slip["upload"]).is_dir():
            os.replace(folder() / "tmp" / slip["upload"], job)  # 受付を書いた直後に止まった時
        try:
            made = _take_in(slip, job)
        except Withdrawn:
            raise
        except OSError as e:  # trial_video.Interrupted もここ
            print(f"{slip_id}: 待つ（{type(e).__name__}: {e}）", file=sys.stderr)
            slip["waits"] = slip.get("waits", 0) + 1
            slip["state"] = "waiting"
            _save(slip)
            return min(RETRY_WAIT * 2 ** (slip["waits"] - 1), MAX_RETRY_WAIT)
        except Exception as e:
            print(f"{slip_id}: 受け取れない（{type(e).__name__}: {e}）", file=sys.stderr)
            slip["tries"] = slip.get("tries", 0) + 1
            if slip["tries"] < TRIES:
                slip["state"] = "waiting"
                _save(slip)
                return RETRY_WAIT
            made = False
        if made:
            slip["state"] = "done"
        else:
            if slip.get("record"):
                _forget(slip["record"])
            for key in ("record", "note", "sheet"):
                slip.pop(key, None)
            slip["state"] = "failed"
        # 状態を書いてから元を消す。逆だと、間で止まった時に、受け取った物を受け取れなかった事にしてしまう
        _save(slip)
    except Withdrawn:  # 読んでいる間に取り下げられた。動画も文も残さない
        if slip.get("record"):
            _forget(slip["record"])
    shutil.rmtree(job, ignore_errors=True)
    return 0


class Worker(threading.Thread):
    """1 本ずつ順に回す。同時に回すと、長い動画の間に機械のほかの作業を止めるため。"""

    def __init__(self):
        super().__init__(daemon=True)
        self.jobs = queue.Queue()

    def run(self):
        while True:
            try:
                slip_id = self.jobs.get(timeout=SWEEP_EVERY)
            except queue.Empty:
                sweep()
                continue
            try:
                if slip_id.startswith("text:"):
                    transcribe(slip_id[5:])
                elif wait := process(slip_id):
                    # 待つ間も、後ろの動画は止めない
                    timer = threading.Timer(wait, self.jobs.put, [slip_id])
                    timer.daemon = True
                    timer.start()
                elif (store.read_json_or_skip(folder() / f"{slip_id}.json") or {}).get("voice"):
                    self.jobs.put(f"text:{slip_id}")  # 字にするのは受け取りの後。上げた人を待たせない
            except Withdrawn:
                pass
            except Exception as e:  # 1 本の失敗で、後の動画を止めない。受付は読み取り中のまま残り、次に立てた時に続く
                print(f"{slip_id}: 処理できない（{type(e).__name__}: {e}）", file=sys.stderr)


def withdraw(slip_id, force=False):
    """取り下げ。Returns 失敗の一覧。受付は番号と「取り下げた」だけを残す（番号を使い回さず、上げた人の頁にそう出す）。
    force はサーバを止めてから使う（止まった時に読み取り中のまま残った受付のため）。"""
    if not (isinstance(slip_id, str) and SLIP.fullmatch(slip_id)):
        return [Failure("F8.references", str(slip_id), "受付番号の形が違う")]
    slip = store.read_json_or_skip(folder() / f"{slip_id}.json")
    if slip is None:
        return [Failure("F8.references", slip_id, "その受付は無い")]
    if slip["state"] == "working" and not force:
        return [Failure("F8.references", slip_id, "読み取りの途中。終わってからもう一度（サーバが止まっているなら --force）")]
    rid = slip.get("record")
    if rid:
        # 案の根拠になった記録は、指す先を失わないように残す。動画とコマと札は消す。上げた人の文も、約束どおり消す
        _forget(rid)
    shutil.rmtree(folder() / "tmp" / f"job-{slip_id}", ignore_errors=True)
    # 同じ動画を別のおもちゃへ送りかけた小分けも消す。撮影情報の付いた元なので残さない
    if slip.get("upload"):
        shutil.rmtree(folder() / "tmp" / slip["upload"], ignore_errors=True)
    _save({"id": slip_id, "token": slip["token"], "state": "withdrawn", "at": loop._now()})
    return []


def _options():
    """おもちゃの選び肢。並びはおもちゃの一覧の頁と同じで、上下は付けない（J-025）。"""
    sids = sources()
    ordered = [s for s in sids if hypotheses.stage(s) == "必須"] + [s for s in sids if hypotheses.stage(s) != "必須"]
    return "".join(f'<option value="{esc(s)}">{esc(hypotheses.load(s)["toy"])}</option>' for s in ordered)


def _skeleton(title, body):
    s = skinmod.SKINS[skinmod.DEFAULT]
    root = ";".join(f"--{k}:{v}" for k, v in s.items() if k != "name")
    return (f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">'
            f"<title>{esc(title)}</title><style>:root{{{root}}}{skinmod.BASE}{skinmod.TAP_FLOOR}{STYLE}</style><body><main>{body}</main></body></html>")


STYLE = """
main{max-width:640px;margin:0 auto;padding:6vh 16px 12vh}
h1{font-weight:400;letter-spacing:.2em}
.lead{line-height:2}
ul.promise{padding-left:1.2em;line-height:1.9;font-size:15px}
form{margin-top:32px}
fieldset{border:0;padding:0;margin:0 0 24px}
legend,label.head{display:block;padding:0;margin-bottom:6px;letter-spacing:.08em}
.hint{font-size:13px;color:var(--mute);margin:4px 0 0}
.pick{display:block;margin:6px 0;line-height:1.7}
input[type=file]{display:block;width:100%;font:inherit;font-size:16px}
#pic{display:block;max-width:100%;max-height:320px;margin-top:10px;border:1px solid var(--frame)}
#pic[hidden]{display:none}
#err{color:var(--accent);min-height:1.5em;margin:10px 0}
#rows{list-style:none;padding:0;margin:10px 0 0}
#rows li{border-top:1px solid var(--frame);padding:12px 0;overflow-wrap:anywhere}
#rows b{font-weight:400;letter-spacing:.06em}
#rows progress{display:block;width:100%;margin:6px 0}
#rows .state{font-size:14px}
#sent[hidden]{display:none}
"""

# 頁の動き。外の部品は読まない。ファイルの名前はこの機器の中にだけ置き、サーバへは送らない（印は名前と大きさと頭から作る片道の字）。
SCRIPT = r"""
(()=>{
const CHUNK=__CHUNK__,MAX=__MAX__,BOXES=['ftyp','moov','mdat','free','skip','wide','pnot'],TRIES=8,MINE='utsushi-up-sent',FINAL=['done','failed','withdrawn'];
const SAY=__SAY__;
const $=id=>document.getElementById(id);
const form=$('up'),rows=$('rows'),err=$('err'),go=$('go'),files=$('files'),toy=$('toy'),pic=$('pic'),note=$('note');
let busy=false,lock=null,timer=null;
const read=()=>{try{return JSON.parse(localStorage.getItem(MINE))||[]}catch(e){return []}};
const write=a=>{try{localStorage.setItem(MINE,JSON.stringify(a))}catch(e){}};
let sent=read();
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
class Refused extends Error{constructor(code,body){super(body.error||SAY.refused);this.code=code;this.body=body}}
async function call(path,opt){
  for(let i=0;;i++){
    let r=null;
    try{r=await fetch(path,opt)}catch(e){}
    if(r&&r.ok)return r.json();
    if(r&&((r.status<500&&r.status!==408&&r.status!==429)||r.status===507)){
      let body={};
      try{body=await r.json()}catch(e){}
      throw new Refused(r.status,body);
    }
    if(i>=TRIES)throw new Error('net');
    await sleep(Math.min(30000,1000*2**i));
  }
}
async function mark(file){
  const head=await file.slice(0,1048576).arrayBuffer(),tag=new TextEncoder().encode(file.name+'|'+file.size+'|'),all=new Uint8Array(tag.length+head.byteLength);
  all.set(tag);all.set(new Uint8Array(head),tag.length);
  const d=await crypto.subtle.digest('SHA-256',all);
  return [...new Uint8Array(d)].slice(0,16).map(x=>x.toString(16).padStart(2,'0')).join('');
}
async function isVideo(file){
  const b=new Uint8Array(await file.slice(4,8).arrayBuffer());
  return BOXES.includes(String.fromCharCode(...b));
}
function row(name){
  const li=document.createElement('li'),b=document.createElement('b'),bar=document.createElement('progress'),state=document.createElement('div');
  b.textContent=name;bar.max=100;bar.value=0;state.className='state';state.setAttribute('role','status');
  li.append(b,bar,state);rows.prepend(li);$('sent').hidden=false;
  return {li,b,bar,state};
}
function show(r,item){
  r.b.textContent=`${item.receipt}　${item.name}　${item.toy}`;
  r.bar.remove();
  r.state.textContent=item.word||SAY.waiting;
}
async function send(file,base,r,name){
  if(!file.size||file.size>MAX){r.bar.remove();r.state.textContent=file.size?SAY.big:SAY.notvideo;return}
  if(!await isVideo(file)){r.bar.remove();r.state.textContent=SAY.notvideo;return}
  const id=await mark(file),count=Math.ceil(file.size/CHUNK),got=await call(`/have?id=${id}&toy=${base.toy}`),have=new Set(got.have);
  const part=async n=>{
    await call(`/chunk?id=${id}&n=${n}`,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file.slice(n*CHUNK,(n+1)*CHUNK)});
    have.add(n);r.bar.value=Math.floor(100*have.size/count);
  };
  r.bar.value=Math.floor(100*have.size/count);
  r.state.textContent=SAY.sending;
  let made=got.receipt?got:null;
  if(!made)for(let n=0;n<count;n++)if(!have.has(n))await part(n);
  for(let i=0;!made;i++){
    try{made=await call('/finish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...base,id,chunks:count,size:file.size})})}
    catch(e){
      if(!(e instanceof Refused)||e.code!==409||i>2)throw e;
      for(const n of e.body.missing)await part(n);
    }
  }
  const item={token:made.token,receipt:made.receipt,name:file.name,toy:name,word:SAY.waiting,state:'waiting'};
  sent=sent.filter(x=>x.token!==item.token).concat(item);
  write(sent);
  [...rows.children].filter(li=>li.dataset.token===item.token).forEach(li=>li.remove());
  r.li.dataset.token=item.token;
  show(r,item);
  watch();
}
async function poll(){
  timer=null;
  const open=sent.filter(x=>!FINAL.includes(x.state));
  if(!open.length)return;
  try{
    const r=await fetch('/status?t='+open.map(x=>x.token).join(','));
    if(r.ok){
      const got=await r.json();
      for(const x of sent){
        const now=got[x.token];
        if(!now)continue;
        x.state=now.state;x.word=now.word;
        const li=[...rows.children].find(y=>y.dataset.token===x.token);
        if(li)li.querySelector('.state').textContent=x.word;
      }
      write(sent);
    }
  }catch(e){}
  watch();
}
function watch(){if(!timer&&sent.some(x=>!FINAL.includes(x.state)))timer=setTimeout(poll,4000)}
async function awake(){try{if(busy&&navigator.wakeLock)lock=await navigator.wakeLock.request('screen')}catch(e){}}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')awake()});
window.addEventListener('beforeunload',e=>{if(busy){e.preventDefault();e.returnValue=''}});
toy.addEventListener('change',()=>{if(toy.value){pic.hidden=false;pic.src='/picture/'+toy.value}else{pic.hidden=true;pic.removeAttribute('src')}});
pic.addEventListener('error',()=>{pic.hidden=true});
form.addEventListener('submit',async ev=>{
  ev.preventDefault();
  err.textContent='';
  const picked=[...files.files];
  if(!picked.length){err.textContent=SAY.pick;return}
  const base={toy:toy.value,made_with:form.elements.made_with.value,note:note.value,agree_people:$('a1').checked,agree_adult:$('a2').checked},name=toy.options[toy.selectedIndex].text;
  busy=true;go.disabled=true;await awake();
  const made=picked.map(f=>row(f.name));
  try{
    await call('/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(base)});
    for(let i=0;i<picked.length;i++)await send(picked[i],base,made[i],name);
    files.value='';note.value='';
  }catch(e){
    err.textContent=e instanceof Refused?e.message:SAY.net;
    made.filter(r=>!r.li.dataset.token&&r.bar.isConnected).forEach(r=>r.li.remove());
    if(!rows.children.length)$('sent').hidden=true;
  }
  busy=false;go.disabled=false;
  if(lock){lock.release().catch(()=>{});lock=null}
});
for(const x of sent){const r=row('');r.li.dataset.token=x.token;show(r,x)}
if(sent.length)poll();
})();
"""


def page(nonce, kind="making"):
    conf = KINDS[kind]
    say = {"waiting": conf["words"]["waiting"], "sending": "送っています。", "big": _too_big(), "notvideo": "MP4 か MOV の動画を選んでください。", "pick": "動画を選んでください。",
           "net": "つながりません。つながる所で、同じ動画を選んで、もう一度「送る」を押してください。続きから送ります。", "refused": "受け取れませんでした。"}
    script = SCRIPT.replace("__CHUNK__", str(CHUNK)).replace("__MAX__", str(MAX_FILE)).replace("__SAY__", json.dumps(say, ensure_ascii=False))
    promises = "".join(f"<li>{esc(p)}</li>" for p in conf["promises"])
    made = "".join(f'<label class="pick"><input type="radio" name="made_with" value="{k}" required> {esc(MADE_WITH_LABEL[k])}</label>' for k in conf["made_with"] if k in MADE_WITH_LABEL)
    question = esc(conf["toy_question"])
    made = f"<fieldset><legend>何を見て作りましたか</legend>{made}</fieldset>" if made else '<input type="hidden" name="made_with" value="review">'
    body = (f"<h1>{esc(conf['title'])}</h1><p class=\"lead\">{esc(conf['lead'])}</p><ul class=\"promise\">{promises}</ul>"
            '<form id="up">'
            f'<fieldset><label class="head" for="toy">{question}</label><select id="toy" required><option value="">選んでください</option>{_options()}</select><img id="pic" hidden alt="選んだおもちゃの図"></fieldset>'
            f"{made}"
            f'<fieldset><label class="head" for="files">動画（いくつでも選べます）</label><input id="files" type="file" accept="video/*" multiple required><p class="hint">MP4 か MOV。1 本 {MAX_FILE // 1024 ** 3}GB までです。</p></fieldset>'
            f'<fieldset><label class="head" for="note">この動画で伝えたい事（なくてもかまいません）</label><textarea id="note" rows="4" maxlength="{NOTE_MAX}"></textarea><p class="hint">{esc(ASK_NAME)}住所・電話番号・メールも書かないでください。</p></fieldset>'
            f'<fieldset><label class="pick"><input type="checkbox" id="a1" required> {esc(AGREE_PEOPLE)}</label><label class="pick"><input type="checkbox" id="a2" required> {esc(AGREE_ADULT)}</label></fieldset>'
            f'<p class="hint">{esc(KEEP_OPEN)}</p><div id="err" role="alert"></div><button id="go">送る</button></form>'
            '<section id="sent" hidden><h2 style="font-weight:400;letter-spacing:.1em;margin-top:40px">送った動画</h2><p class="hint">受付番号は、取り下げる時に使います。</p><ul id="rows"></ul></section>'
            f'<script nonce="{nonce}">{script}</script>')
    return _skeleton(f"うつし · {conf['title']}", body)


class Handler(BaseHTTPRequestHandler):
    timeout = 300  # 秒。遅い回線の 1 つの小分けが届く長さ。止まった接続を抱え続けない
    server_version = "utsushi"
    sys_version = ""

    def log_message(self, *a):
        """何も書かない。URL に合言葉が入り、誰がいつ来たかも残さない決まりのため。"""

    def _send(self, code, data, ctype="text/html; charset=utf-8", headers=(), csp=None):
        payload = data if isinstance(data, bytes) else data.encode("utf-8")
        self.send_response(code)
        for k, v in (("Content-Type", ctype), ("Content-Length", str(len(payload))), ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer"), ("X-Content-Type-Options", "nosniff"),
                     ("Content-Security-Policy", csp or "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"), *headers):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, code, obj):
        self._drain()
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def _drain(self):
        """読まなかった本文を読み捨てる。残したまま閉じると、返事が相手に届く前に接続が切れる事がある。"""
        left = min(self._left, 2 * CHUNK + MAX_FORM)
        while left > 0:
            got = self.rfile.read(min(left, 1024 * 1024))
            if not got:
                break
            left -= len(got)
        self._left = 0

    def _refuse(self):
        self._drain()
        self._send(403, _skeleton("合言葉が要ります", f"<h1>合言葉が要ります</h1><p>{esc(NEED_KEY)}</p>"))

    def _host_ok(self):
        # DNS rebinding で外のサイトから読ませないため、手元の名前とトンネルの名前だけを受ける。
        host, port = self.headers.get("Host", ""), self.server.server_address[1]
        return host in (f"127.0.0.1:{port}", f"localhost:{port}") or bool(re.fullmatch(TUNNEL_HOST, host))

    def _origin_ok(self):
        # 同じ頁から来た物だけを受ける。トンネルの先は https だけ。
        host = self.headers.get("Host", "")
        return self.headers.get("Origin") == (f"https://{host}" if re.fullmatch(TUNNEL_HOST, host) else f"http://{host}")

    def _key_ok(self):
        jar = {}
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            jar[k] = v
        return hmac.compare_digest(jar.get(COOKIE, "").encode(), self.server.key.encode())

    def do_GET(self):
        self._left = 0
        try:
            self._get()
        except (OSError, ValueError):
            self.close_connection = True

    def do_POST(self):
        try:
            self._left = int(self.headers.get("Content-Length", ""))
            if self._left < 0:
                raise ValueError
        except ValueError:
            self._left = 0
            return self._json(411, {"error": "送り方の形が違います。"})
        try:
            self._post()
        except (OSError, ValueError) as e:
            print(f"受け口: {type(e).__name__}", file=sys.stderr)
            self.close_connection = True
        except Exception as e:  # 頁には回し直せる失敗として返す。理由はこちらに残す（文と合言葉は出さない）
            print(f"受け口: {type(e).__name__}", file=sys.stderr)
            self._json(500, {"error": "受け取れませんでした。"})

    def _get(self):
        path, _, query = self.path.partition("?")
        params = urllib.parse.parse_qs(query)
        if not self._host_ok():
            return self._refuse()
        # 合言葉は最初の 1 回だけ URL で受け、Cookie に移して URL から消す（play_server の門と同じ）
        given = params.get("k", [""])[0]
        if given and hmac.compare_digest(given.encode(), self.server.key.encode()):
            return self._send(303, "", headers=[("Location", "/"), ("Set-Cookie", f"{COOKIE}={self.server.key}; Max-Age=604800; Path=/; HttpOnly; Secure; SameSite=Lax")])
        if not self._key_ok():
            return self._refuse()
        if path == "/":
            nonce = secrets.token_urlsafe(16)
            csp = f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
            return self._send(200, page(nonce, self.server.kind), csp=csp)
        if path == "/have":
            uid = params.get("id", [""])[0]
            if not UPLOAD_ID.fullmatch(uid):
                return self._json(400, {"error": "形が違います。"})
            same = existing(uid, params.get("toy", [""])[0])
            return self._json(200, {"have": [], "receipt": same["id"], "token": same["token"]} if same else {"have": _parts(uid)})
        if path == "/status":
            tokens = [t for t in params.get("t", [""])[0].split(",") if t]
            if len(tokens) > MAX_STATUS or not all(UPLOAD_ID.fullmatch(t) for t in tokens):
                return self._json(400, {"error": "形が違います。"})
            # 受付番号では答えない。番号は順に数えられるので、ほかの人の受付が読めてしまう
            wanted = set(tokens)
            return self._json(200, {s["token"]: {"receipt": s["id"], "state": s["state"], "word": KINDS[self.server.kind]["words"][s["state"]]} for s in slips() if s["token"] in wanted})
        m = re.fullmatch(rf"/picture/({SID})", path)
        if m and m.group(1) in sources() and (ROOT / "out/sources" / f"{m.group(1)}.jpg").is_file():
            return self._send(200, (ROOT / "out/sources" / f"{m.group(1)}.jpg").read_bytes(), "image/jpeg")
        return self._send(404, _skeleton("見つかりません", "<h1>見つかりません</h1>"))

    def _post(self):
        path, _, query = self.path.partition("?")
        if not (self._host_ok() and self._origin_ok() and self._key_ok()):
            return self._refuse()
        if path == "/chunk":
            return self._chunk(urllib.parse.parse_qs(query))
        if path in ("/check", "/finish"):
            if self._left > MAX_FORM:
                return self._json(413, {"error": "文が長すぎます。"})
            raw = self.rfile.read(self._left)
            self._left = 0
            try:
                body = json.loads(raw)
            except ValueError:
                return self._json(400, {"error": "送り方の形が違います。"})
            if not isinstance(body, dict):
                return self._json(400, {"error": "送り方の形が違います。"})
            if path == "/check":
                why = check_form(body, self.server.kind)
                return self._json(422, {"error": why}) if why else self._json(200, {"ok": True})
            worker = self.server.worker
            code, out = accept(body, worker.jobs.put if worker else None, self.server.kind)
            sweep()
            return self._json(code, out)
        return self._json(404, {"error": "見つかりません。"})

    def _chunk(self, params):
        uid, num = params.get("id", [""])[0], params.get("n", [""])[0]
        if not (UPLOAD_ID.fullmatch(uid) and num.isascii() and num.isdigit() and int(num) <= MAX_FILE // CHUNK):
            return self._json(400, {"error": "形が違います。"})
        if self._left > CHUNK:
            return self._json(413, {"error": _too_big()})
        if self._left == 0:
            return self._json(400, {"error": "形が違います。"})
        if shutil.disk_usage(folder()).free < MIN_FREE + CHUNK:
            return self._json(507, {"error": "今は受け取る場所が足りません。リンクを渡した人に知らせてください。"})
        d = folder() / "tmp" / uid
        d.mkdir(exist_ok=True)
        # 届ききった時だけ番号の名前にする。途中で切れた分を、届いた物に数えない
        tmp = d / f"{int(num)}.{threading.get_ident()}.part"
        try:
            with open(tmp, "wb") as f:
                while self._left > 0:
                    got = self.rfile.read(min(self._left, 1024 * 1024))
                    if not got:
                        raise ConnectionError("途中で切れた")
                    f.write(got)
                    self._left -= len(got)
            os.replace(tmp, d / str(int(num)))
        finally:
            tmp.unlink(missing_ok=True)
        return self._json(200, {"ok": True})


def serve(port=8794, key=None, worker=True, kind="making"):
    """口は手元だけに開く。外からはトンネルだけが入る。合言葉が無いと立たない（リンクを渡した人だけが開く口のため）。"""
    if not (isinstance(key, str) and len(key) >= 16):
        raise ValueError("合言葉が要る（16 字以上）")
    folder()
    sweep()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.key = key
    server.kind = kind
    server.worker = Worker() if worker else None
    if server.worker:
        server.worker.start()
        # 待っていた物と、読んでいる途中で止まった物を続ける
        for s in slips():
            if s["state"] in ("waiting", "working"):
                server.worker.jobs.put(s["id"])
            elif s["state"] == "done" and s.get("voice") and s.get("text") not in ("done", "no-voice"):
                server.worker.jobs.put(f'text:{s["id"]}')  # 字にする前に止まった物
    return server


def main(argv=None):
    ap = argparse.ArgumentParser(prog="web.video_up", description="動画を上げる専用の口（#337）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="口を立てる。外へはトンネルで開く")
    s.add_argument("--port", type=int, default=8794)
    s.add_argument("--key-file", required=True, help="合言葉を書いたファイル（repo の外）")
    s.add_argument("--kind", choices=tuple(KINDS), default="making", help="making: 作った時の動画 / review: 作る前の型紙のレビューの動画（声を非公開で残して字にする）")
    sub.add_parser("list", help="届いた物を読む順に出す")
    w = sub.add_parser("withdraw", help="取り下げ。動画もコマも札も消す")
    w.add_argument("slip")
    w.add_argument("--force", action="store_true", help="サーバを止めてから、読み取り中のまま残った受付に使う")
    t = sub.add_parser("transcribe", help="声を字にし直す（レビューの口）")
    t.add_argument("slip")
    v = sub.add_parser("drop-voice", help="整理が終わった声を消す（字と動画は残る）")
    v.add_argument("slip")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 4
    if args.cmd == "serve":
        try:
            server = serve(args.port, pathlib.Path(args.key_file).read_text(encoding="utf-8").strip(), kind=args.kind)
        except (OSError, ValueError) as e:
            print(f"立てられない: {e}", file=sys.stderr)
            return 4
        print(f"http://127.0.0.1:{server.server_address[1]}/ で待っています（合言葉はリンクで渡す）", flush=True)
        server.serve_forever()
        return 0
    if args.cmd == "list":
        for slip in slips():
            if slip["state"] != "withdrawn":
                # 文は上げた人の字なので、そのまま端末に出さない（1 行の中に閉じ込める）
                print("\t".join(str(x) for x in (slip["id"], slip["state"], slip.get("record", "-"), slip.get("source_id", "-"), slip.get("sheet", "-"), slip.get("text_file", slip.get("text", "-")), json.dumps(slip.get("note", ""), ensure_ascii=False))))
        return 0
    if args.cmd == "transcribe":
        return 0 if transcribe(args.slip) else 3
    if args.cmd == "drop-voice":
        failures = drop_voice(args.slip)
    else:
        failures = withdraw(args.slip, args.force)
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
