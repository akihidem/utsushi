"""鍵なしで 4 つのループを一周回す入口（Issue #335 の「一周の入口」）。

本人の決めた 4 つ（11-05）: 1 考えを話す → 紙が生まれる、2 作りながらの工夫 → 型紙の直し、3 エンジンごとの改善、4 上げて残す → ギャラリーと輪。
ここは、それぞれの部品が本当につながるかを、1 つの命令で通して見る道具。人の入力と話した字は、この中の決まった偽の文で済ませる。

判断の芯:
- 部品は別々の枝から入る。まだ無い部品は、その段で「まだ main に無い」と名指しして止まる。入ると通る段が増える。
  部品の有無はその場で調べる（PARTS）。ここに状態を書かないのは、部品の PR ごとにこのファイルを直さずに済ませるため。
- 止まった後ろの段も見たい時は --keep-going。部品を待つ間に、後ろの段の部品が壊れても気づけるようにする。
- 本物の記録に触らない。置き場は毎回まっさらな一時の場所で、環境の値は終わったら元に戻す。--keep は空の場所か新しい場所にだけ書く。
- 鍵を使わない。鍵は環境から外し、Claude を呼ぶ道（words の use_claude・loop_agents）を通らない。作る側が書く道で輪を閉じる。
  鍵のある道は、それぞれの部品の試験（偽の Claude）が見る。
- エンジンは別の repo（paper-to-toy）で、同じ omochae の名前を持つので、別のプロセスで呼ぶ。手元に無い時は飛ばして印を出す。
  エンジンの置き場と版の台帳も一時の場所へ向ける（試しの文を本物の案にしない）。本物の repo の中には何も書かない。
- 効いたかの判定はしない（本人の決まり）。見るのは、つながって紙と束と下書きが出来るかだけ。
- 必須 2 種の今の組の紙には触らない。次の版は一時の場所に刷る。
- ループ4 は、上げた後の字が材料と束へ渡る所までを見る。ギャラリーの頁は開かないので、全部の段が通っても、ギャラリーに字が出るかは分からない。
- ループ1 で作った自分の紙で作る段は、関数でなく本物の頁の受け口を手元の口で通す（1 人の画面と cookie）。部品ごとに通っても頁の道で紙が切れていて、
  関数だけを通すこの命令が気づけなかった事があるため。ほかの段は、頁の道を別の試験が見ているので、関数のまま軽く回す。
- 作る人は 2 人に分ける（印が 2 つ）。ループ1 の紙で作る人と、たたき台で次の版まで進む人。記録を残すと同じ印の作りは区切りが付く決まりなので、1 人では両方の道を通れない。

使い方: PYTHONPATH=src python -m omochae.cycle [--toy <玩具の ID>] [--keep-going] [--keep <置き場>] [--engine-repo <paper-to-toy の場所>]
エンジンの repo は --engine-repo・環境の値 OMOCHAE_ENGINE_REPO・この repo の隣の paper-to-toy の順に探す。
終わりの値: 0 = 全部の段が通った（エンジンを飛ばした時を含む）/ 3 = 部品はあるのに落ちた / 4 = まだ main に無い部品で止まった・呼び方の誤り。
"""
import argparse
import contextlib
import dataclasses
import html
import http.client
import importlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import urllib.parse

from . import engine_bundle, hypotheses, loop, records
from .compose import TEMPLATES, compose
from .metrics import ALLOWED

ROOT = pathlib.Path(__file__).resolve().parents[2]
PASSED, NOT_YET, SKIPPED, FAILED = "通った", "まだ main に無い", "飛ばした", "落ちた"
TOY = "NDL-1187053-R0000005-L"
BY = "一周の試し"
WHO = "cycletest01"  # その場限りの印の形（making_log.WHO）。たたき台で次の版まで進む人
OWN_WHO = "cycletest02"  # ループ1 の紙で作る人
THINK = "札を見て、つまみを押すと扇が開くと思った"
CRAFT = "折り目を先に強くつけると、押した時に引っかからなかった"
OWN_THINK = "もう少し折りを増やすと、大きく開くと思う"
OWN_CRAFT = "自分の紙では、折りを増やした所を先にならすと動いた"
KEEP = "できた後に開いて見せたら、折り目の所で少し止まった"
EXPLAIN, NEXT_IDEA = "押す量が足りず、扇が途中で止まったと思う", "もう少し長く押せる形にする"
INTERPRET = "途中で止まるのは押す量が足りないからと読む"
WHY = "一周の試しで寸法を 1 つ変える"
# 床に当たるはずの字。連絡先の形と名乗りの形。残らない事を、最後の段で全部のファイルから探す
PROBES = ("連絡先は cycle-probe@example.com です", "一周の試しと申します")
PROBE_MARKS = ("cycle-probe@example.com", "と申します")
# 声と映像の置き場になり得る形。話す口は字だけを残す決まり
VOICE_SUFFIXES = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".oga", ".flac", ".webm", ".mp4", ".mov"}


def _module(name):
    return lambda: importlib.util.find_spec(name) is not None


# 段が要る部品。label は止まった時に名指しする字。入った部品は has が真になり、次の段へ進む
PARTS = {
    "talk_log": {"stage": "話した字", "label": "omochae.talk_log（話す口、#308）", "there": _module("omochae.talk_log")},
    "think_sheet": {"stage": "ループ1 の紙", "label": "web.think_sheet（考えから紙、#335 のループ1）", "there": _module("web.think_sheet")},
    "own_next": {"stage": "自分の紙の記録から次の版", "label": "loop.next_target（自分の紙の記録の次の版、#410）", "there": lambda: hasattr(loop, "next_target")},
    "material": {"stage": "ループ2 の材料", "label": "loop.material（#335 のループ2）", "there": lambda: hasattr(loop, "material")},
    "bundle_talk": {"stage": "ループ3 の束", "label": "束の話した事（#307）", "there": lambda: "craft" in engine_bundle.TEXT_KINDS},
}


def has(part):
    return PARTS[part]["there"]()


class NotYet(Exception):
    """要る部品がまだ無い。"""


class Skipped(Exception):
    """この段を回せる物が手元に無い。"""


class Failed(Exception):
    """部品はあるのに、つながらなかった。"""


def _need(part):
    if not has(part):
        raise NotYet(PARTS[part]["label"])


def _ok(failures, what):
    if failures:
        raise Failed(f"{what}: " + "／".join(f.line() for f in failures))


@dataclasses.dataclass
class Context:
    sid: str
    folder: pathlib.Path
    engine_repo: pathlib.Path = None
    hid: str = None
    source: dict = None
    rid: str = None
    bundle: pathlib.Path = None
    talked: bool = False
    own_id: str = None  # ループ1 で刷った紙（OWN-n）
    own_cookie: str = ""  # その紙を開ける本人の画面の印
    own_rid: str = None


@dataclasses.dataclass
class Stage:
    name: str
    status: str
    detail: str = ""


@dataclasses.dataclass
class Result:
    stages: list
    context: Context

    def stage(self, name):
        return next(s for s in self.stages if s.name == name)

    @property
    def rc(self):
        statuses = {s.status for s in self.stages}
        return 3 if FAILED in statuses else 4 if NOT_YET in statuses else 0


def _one_change(c):
    """紙に組める形で寸法を 1 つ変える案を探す。値に意味は無く、輪が閉じるかだけを見るので、床を通る最初の物でよい。"""
    template = hypotheses.load(c.sid).get("template", "slider_fan")
    params = loop.version_params(c.sid, c.hid, loop.latest_version(c.sid, c.hid))[0]  # 次の版は今の版の上に足す
    current = {**TEMPLATES[template].DEFAULTS, **params}
    for param in sorted(ALLOWED[template]):
        value = current.get(param)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        step = 1 if isinstance(value, int) else max(round(abs(value) * 0.05, 1), 0.5)
        for to in (value + step, value - step):
            if not compose(template, {**params, param: to}, c.source)[2]:
                return {"param": param, "to": to, "why": WHY}
    raise Failed("紙に組める形で変えられる寸法が見つからない")


def stage_first_sheet(c):
    """最初の紙を刷り、刷った組を確定する。画面で刷る時と同じ順で、これが無いと束の群の組が「不明」になる。"""
    if loop.print_version(c.sid, c.hid, 1, hypotheses.play_dir(c.sid)):  # 頁と同じ置き場。頁の道の段が同じ紙を見るため
        raise Failed("最初の紙を刷れない")
    template = hypotheses.load(c.sid).get("template", "slider_fan")
    loop.confirm_sheet(c.sid, c.hid, 1, BY, TEMPLATES[template].SHEET_SET)
    return f"{c.hid} 版 1（{TEMPLATES[template].SHEET_SET}）"


def stage_record(c):
    """試した記録。工夫と思いつきも入れる（束からエンジンの案が起きる材料）。話した字は、画面の記録の口と同じに、ここで記録に結ぶ。"""
    rid, failures = records.add({"source_id": c.sid, "hypothesis_id": c.hid, "sheet_version": 1, "result": records.results_for(c.sid)[0],
                                 "answers": {"what_if": NEXT_IDEA}, "fixes": [{"part": "折り", "change": "折り目を先に強くつけた", "outcome": "引っかからなくなった"}]})
    _ok(failures, "記録")
    c.rid = rid
    if c.talked:
        talk_log = importlib.import_module("omochae.talk_log")
        bound = talk_log.bind(c.sid, c.hid, 1, WHO, rid)
        if bound != (1, 1):
            raise Failed(f"記録に結んだ数が違う（工夫と考えが {bound}）")
        _ok(talk_log.add(c.sid, "keep", KEEP, record_id=rid, who=WHO)[1], "上げた後")
    return rid


def stage_explain(c):
    """人の説明と次の思いつき。作っている人のアイディアより先に AI の原因が出ないよう、輪は人の説明を先に受ける決まり。"""
    _ok(loop.save_explanation(c.rid, BY, EXPLAIN, NEXT_IDEA), "人の説明")


def stage_talk(c):
    """話した字: 2 人の考えと、たたき台で作る人の工夫。床に当たる字は残らない事も見る。上げた後の字は、記録を残す段で足す（記録に結ぶ字なので）。"""
    _need("talk_log")
    talk_log = importlib.import_module("omochae.talk_log")
    _ok(talk_log.add(c.sid, "think", OWN_THINK, hypothesis_id=c.hid, who=OWN_WHO)[1], "ループ1 の考え")
    _ok(talk_log.add(c.sid, "think", THINK, hypothesis_id=c.hid, who=WHO)[1], "考え")
    _ok(talk_log.add(c.sid, "craft", CRAFT, hypothesis_id=c.hid, sheet_version=1, step=1, who=WHO)[1], "工夫")
    for probe in PROBES:
        kept, failures = talk_log.add(c.sid, "craft", probe, hypothesis_id=c.hid, sheet_version=1, step=2, who=WHO)
        if kept is not None or not failures:
            raise Failed("床に当たるはずの字が残った")
    c.talked = True
    return "考えと工夫を残し、床に当たる字は残らなかった"


def stage_think_sheet(c):
    """ループ1: 話した考えから、たたき台を変えたその人の紙。鍵なしは、作る側が寸法を書く道（words の fill）で本人が採る。"""
    _need("talk_log")
    _need("think_sheet")
    think_sheet = importlib.import_module("web.think_sheet")
    words = importlib.import_module("api.words")
    if not think_sheet.ready(c.sid):
        raise Skipped("この玩具には、話した考えから紙を作る節が無い")
    w, note = think_sheet.request(c.sid, OWN_WHO)
    if w is None:
        raise Failed(f"考えから案を作れない: {note}")
    change = _one_change(c)
    params = words.base_of(c.sid)[1]
    w, failures = words.fill_think(w["id"], words.think_result(params, changed={change["param"]: change["to"]}), BY)
    _ok(failures, "作る側の寸法")
    name, note = think_sheet.confirm(c.sid, w["token"])
    if not name:
        raise Failed(f"考えから紙を刷れない: {note}")
    c.own_id = words.by_token(c.sid, w["token"])["own_id"]
    c.own_cookie = f"{think_sheet.COOKIE}{w['id']}={w['token']}"  # 頼んだ時に本人の画面へ渡る印（鍵なしの道なので、受け口を通さずに作る）
    return name


@contextlib.contextmanager
def _page_server():
    """本物の頁を手元の口で開く。置き場は呼ぶ時の環境の値のまま（一時の場所）。"""
    server = importlib.import_module("web.play_server").serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


class _Screen:
    """手元の口に開いた 1 人の画面。その人の印（cookie）を持って頁を開き、フォームを送る。"""

    def __init__(self, port, cookie=""):
        self.port, self.cookie = port, cookie

    def _open(self, method, path, body=None):
        headers = {"Cookie": self.cookie} if self.cookie else {}
        if body is not None:
            headers.update({"Content-Type": "application/x-www-form-urlencoded", "Origin": f"http://127.0.0.1:{self.port}"})
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        try:
            conn.request(method, path, body, headers)
            r = conn.getresponse()
            return r.status, r.read().decode("utf-8", "replace")
        finally:
            conn.close()

    def get(self, path):
        return self._open("GET", path)

    def post(self, path, **form):
        return self._open("POST", path, urllib.parse.urlencode(form))


def _walk_own_paper(c, port):
    """作りながら見る → 札 → 工夫 → 記録を、本物の受け口で通す。Returns 記録の番号。"""
    tsukuru = importlib.import_module("web.tsukuru")
    talk_log = importlib.import_module("omochae.talk_log")
    mine, stranger = _Screen(port, c.own_cookie), _Screen(port)
    toy, oid = f"/toy/{c.sid}", c.own_id
    steps = tsukuru.step_texts(c.sid, oid, 1)
    if not steps:
        raise Failed(f"自分の紙 {oid} の手順が無い")
    first, path = html.escape(steps[0], quote=True), f"{toy}/tsukuru?h={oid}&v=1"
    status, page = mine.get(path)
    if status != 200 or first not in page:
        raise Failed(f"自分の紙 {oid} の作りながら見る頁が開かない（{status}）")
    if first in stranger.get(path)[1]:
        raise Failed(f"自分の紙 {oid} が、ほかの人の画面に開いた")
    paper = {"hypothesis": oid, "sheet_version": "1", "who": OWN_WHO}
    status, body = mine.post(f"{toy}/step", step="1", event="start", json="1", **paper)
    if status != 200:
        raise Failed(f"作りながら見る頁の札を受けない（{status}: {body[:80]}）")
    status, body = mine.post(f"{toy}/talk", scene="craft", step="1", text=OWN_CRAFT, json="1", **paper)
    if status != 200:
        raise Failed(f"自分の紙で話した工夫を受けない（{status}: {body[:80]}）")
    if f'value="{oid}" selected' not in mine.get(toy)[1]:
        raise Failed(f"記録の欄に自分の紙 {oid} が選ばれて出ない")
    status, _ = mine.post(f"{toy}/record", result=records.results_for(c.sid)[0], **paper)
    kept = [r for r in records.all_records(c.sid) if r["hypothesis_id"] == oid]
    if status != 303 or len(kept) != 1:
        raise Failed(f"自分の紙の記録を受けない（{status}・{len(kept)} 件）")
    rid = kept[0]["id"]
    said = {t["when"]: t["text"] for t in talk_log.kufu(c.sid, rid)}
    if said.get("making") != OWN_CRAFT or said.get("idea") != OWN_THINK:
        raise Failed(f"工夫と考えの字が、自分の紙の記録に結ばれない（{sorted(said)}）")
    if first in mine.get(path)[1]:
        raise Failed("記録の後も、自分の紙が開いたまま（次の人に見える）")
    return rid


def stage_own_paper(c):
    """ループ1 の紙で作る人の道。工夫の字がその紙の記録に結ばれ、ほかの人の画面に開かず、記録を残すと案が閉じるまで見る。"""
    _need("think_sheet")
    if c.own_id is None:
        raise Skipped("ループ1 の紙がまだ無い")
    with _page_server() as port:
        c.own_rid = _walk_own_paper(c, port)
    return f"{c.own_id} で記録 {c.own_rid}、工夫と考えを結んだ"


def _walk_own_next(c, port):
    """自分の紙の記録 → 説明 → 次の版 → 次の人が刷る、を本物の受け口で通す。Returns 変えた寸法の字。"""
    base, oid, rid = c.hid, c.own_id, c.own_rid
    toy = f"/toy/{c.sid}"
    mine, next_person = _Screen(port, c.own_cookie), _Screen(port)
    before = loop.version_params(c.sid, base, 1)[0]
    status, _ = mine.post(f"/record/{rid}/explain", text=EXPLAIN, next_idea=NEXT_IDEA, by=BY)
    if status != 303:
        raise Failed(f"自分の紙の記録の説明を受けない（{status}）")
    if f"/record/{rid}/next" not in mine.get(toy)[1]:
        raise Failed("自分の紙の記録に、次の版の欄が出ない")
    change = _one_change(c)
    status, _ = mine.post(f"/record/{rid}/next", interpretation=INTERPRET, param=change["param"], to=str(change["to"]), why=WHY, by=BY)
    if status != 303:
        raise Failed(f"自分の紙の記録から次の版を受けない（{status}）")
    # たたき台の版 2 になる。足すのは選んだ寸法だけで、根拠は自分の紙の記録のまま。自分の紙には版を足さない
    if loop.adopted_versions(c.sid, oid):
        raise Failed(f"自分の紙 {oid} に版が足された")
    if loop.latest_version(c.sid, base) != 2:
        raise Failed(f"たたき台 {base} が版 2 にならない（{loop.latest_version(c.sid, base)}）")
    params, made = loop.version_params(c.sid, base, 2)
    if params != {**before, change["param"]: change["to"]}:
        raise Failed("たたき台の版 2 に、選んだ寸法のほかの違いが入った")
    if rid not in (made or {}).get("record_ids", []):
        raise Failed("たたき台の版 2 の根拠が、自分の紙の記録でない")
    # 次の人（別の画面）が、最新の版を刷る。前の版の紙は残る
    if next_person.post(f"{toy}/print", hypothesis=base)[0] != 303:
        raise Failed("次の人が紙を刷れない")
    printed = [x for x in loop.sheet_confirmations(c.sid) if x["hypothesis_id"] == base and x["version"] == 2]
    if len(printed) != 1 or len(printed[0]["confirmations"]) != 2:
        raise Failed("次の人が刷った紙が、たたき台の版 2 でない")
    for version in (2, 1):
        if next_person.get(f"/sheet/{c.sid}/{base}_v{version}.pdf")[0] != 200:
            raise Failed(f"次の人の画面で、たたき台の版 {version} の紙が開かない")
    return f"{change['param']} を {change['to']:g} に"


def stage_own_next(c):
    """自分の紙の記録から作る次の版は、たたき台の版になり（根拠は自分の紙の記録のまま）、次の人がそれを刷る（型紙は玩具ごとに 1 枚、最新版が次の人の型紙）。"""
    _need("think_sheet")
    _need("own_next")
    if c.own_rid is None:
        raise Skipped("自分の紙の記録がまだ無い")
    with _page_server() as port:
        changed = _walk_own_next(c, port)
    return f"たたき台 {c.hid} の版 2（{changed}）を次の人が刷った"


def stage_material(c):
    """ループ2: 工夫の字が、輪の解釈と案の材料に入る。考えはループ1 の材料なのでここに入らない。"""
    _need("talk_log")
    _need("material")
    m = loop.material(c.rid)
    said = [t["text"] for t in m["maker_talk"]["items"]]
    if CRAFT not in said or KEEP not in said:
        raise Failed(f"工夫と上げた後の字が材料に無い（{len(said)} 件）")
    if THINK in said:
        raise Failed("考えの字が直しの材料に入った")
    if not m["explanation"]:
        raise Failed("人の説明が材料に無い")
    if c.own_rid and OWN_CRAFT not in [t["text"] for t in loop.material(c.own_rid)["maker_talk"]["items"]]:
        raise Failed("自分の紙で話した工夫が材料に無い")
    return f"話した字 {len(said)} 件"


def stage_next(c):
    """人の解釈と案から次の版の紙まで。画面の「次の版を作る」と同じ 1 操作。前の版は消えず、最新の版が次の人の型紙になる。"""
    before, _ = loop.version_params(c.sid, c.hid, 1)
    latest = loop.latest_version(c.sid, c.hid)
    change = _one_change(c)
    sheets = hypotheses.play_dir(c.sid)
    version, failures = loop.next_version(c.rid, BY, INTERPRET, change, c.source, sheets)
    _ok(failures, "次の版")
    if version != latest + 1 or loop.latest_version(c.sid, c.hid) != version:
        raise Failed(f"版が {latest + 1} にならない（{version}）")
    if not (sheets / f"{c.hid}_v{version}.pdf").exists():
        raise Failed("次の版の紙が無い")
    if loop.version_params(c.sid, c.hid, 1)[0] != before or not (sheets / f"{c.hid}_v1.pdf").exists():
        raise Failed("前の版の寸法か紙が変わった")
    return f"版 {version}（{change['param']} を {change['to']:g} に）"


def stage_bundle(c):
    """ループ3: エンジンへ渡す束。読むだけの口で、書く先は一時の場所。話した字が入るかは #307 の部品が持つ。"""
    bundle = engine_bundle.build()
    path = engine_bundle.out_path(c.folder / "bundle.json")
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    c.bundle = path
    group = [g for g in bundle["groups"] if c.rid in g["record_ids"]]
    if len(group) != 1:
        raise Failed(f"記録 {c.rid} が束の 1 つの群に入らない（{len(group)}）")
    if not group[0]["sheet_set"]:
        raise Failed("束の群の刷った組が不明")
    _need("bundle_talk")
    if c.talked and not {CRAFT, KEEP} <= {t["text"] for t in group[0]["texts"]}:
        raise Failed("話した字が束に無い")
    if c.own_rid and OWN_CRAFT not in {t["text"] for g in bundle["groups"] for t in g["texts"]}:
        raise Failed("自分の紙で話した工夫が束に無い")
    return f"群 {len(bundle['groups'])}・文 {sum(len(g['texts']) for g in bundle['groups'])}"


def find_engine_repo(given=None):
    """エンジンの repo の場所。渡された時はそこだけを見る（渡した場所が無いのに隣の repo を呼ばないため）。"""
    places = [given] if given else [os.environ.get("OMOCHAE_ENGINE_REPO"), ROOT.parent / "paper-to-toy"]
    for place in places:
        if place and (pathlib.Path(place) / "src/omochae/engine_loop.py").exists():
            return pathlib.Path(place)
    return None


def stage_engine(c):
    """エンジンの入口: 束を受け、案と Issue の下書きが置き場に起きるまで（engine_loop の take が propose まで回す）。立てるのは人なので、ここまで。"""
    if c.engine_repo is None:
        raise Skipped("エンジンの repo が手元に無い（--engine-repo か OMOCHAE_ENGINE_REPO で向ける）")
    if c.bundle is None:
        raise Skipped("渡す束がまだ無い")
    repo = c.engine_repo
    python = repo / ".venv/bin/python"
    env = {**os.environ, "PYTHONPATH": str(repo / "src"), "OMOCHAE_ENGINE_LOOP": str(c.folder / "engine-loop"),
           "OMOCHAE_ENGINE_LEDGER": str(c.folder / "engine-ledger" / "versions.json")}
    env.pop("ANTHROPIC_API_KEY", None)
    try:
        r = subprocess.run([str(python) if python.exists() else sys.executable, "-m", "omochae.engine_loop", "take", str(c.bundle)],
                           cwd=repo, env=env, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        raise Failed(f"エンジンの入口を呼べない（{type(e).__name__}）")
    if r.returncode != 0:
        # エンジンの断りの理由だけを出す。作った人の文は標準出力にも出ない決まり（engine_loop の list と同じ）
        raise Failed(f"エンジンの入口が rc {r.returncode}: {r.stderr.strip()[-300:]}")
    drafts = sorted((c.folder / "engine-loop" / "issues").glob("*"))
    if not drafts:
        raise Failed("束から案と Issue の下書きが起きない")
    return f"案と下書き {len(drafts)} 件"


def stage_floor(c):
    """話した字は床を通った物だけが輪へ渡る。声そのものは残らない。この一周で出来た全部のファイルを見る。"""
    if not c.talked:
        raise Skipped("話した字がまだ無い")
    seen = 0
    for p in c.folder.rglob("*"):
        if not p.is_file():
            continue
        seen += 1
        if p.suffix.lower() in VOICE_SUFFIXES:
            raise Failed(f"声か映像の形のファイルが残った: {p.name}")
        data = p.read_bytes()
        if any(mark.encode() in data for mark in PROBE_MARKS):
            raise Failed(f"床に当たるはずの字が残った: {p.name}")
    return f"{seen} ファイルを見た"


# 段の順は作る人の順（紙を刷る → 話す → 考えから紙 → 作って記録 → 説明 → 直し）。考えを記録に結ぶと、その人の作りは区切りが付く（api.words の決まり）ので、
# ループ1 の紙は記録より先に置く。
STAGES = (("最初の紙", stage_first_sheet), ("話した字", stage_talk), ("ループ1 の紙", stage_think_sheet), ("自分の紙で作って記録", stage_own_paper),
          ("自分の紙の記録から次の版", stage_own_next),
          ("記録", stage_record), ("人の説明", stage_explain),
          ("ループ2 の材料", stage_material), ("人の解釈と次の版の紙", stage_next), ("ループ3 の束", stage_bundle),
          ("エンジンの入口と下書き", stage_engine), ("床と声", stage_floor))


@contextlib.contextmanager
def _sandbox(keep):
    """本物の置き場に触らず、鍵を外した環境で動かす。終わったら環境の値を元に戻す。"""
    names = ("OMOCHAE_DATA", "OMOCHAE_USAGE_LEDGER", "ANTHROPIC_API_KEY")
    saved = {k: os.environ.get(k) for k in names}
    with tempfile.TemporaryDirectory(prefix="omochae-cycle-") as tmp:
        folder = pathlib.Path(keep) if keep else pathlib.Path(tmp)
        if keep:
            engine_bundle.out_path(folder / "bundle.json")  # repo の中は out/ の下だけ（作った人の文を repo に入れない決まりと同じ）
            folder.mkdir(parents=True, exist_ok=True)
            if any(folder.iterdir()):
                raise ValueError("--keep は空の場所か新しい場所にだけ書く")
        os.environ["OMOCHAE_DATA"] = str(folder / "data")
        os.environ["OMOCHAE_USAGE_LEDGER"] = str(folder / "data" / "api-usage.jsonl")
        os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            yield folder
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def run(toy=TOY, keep_going=False, keep=None, engine_repo=None):
    """段を順に回す。Returns Result。部品の無い段で止まる（keep_going なら後ろの段も回す）。落ちた段では必ず止まる（後ろの段が前の結果を使うため）。"""
    if not (ROOT / "data/hypotheses" / f"{toy}.json").is_file():
        raise ValueError(f"その玩具は無い: {toy}")
    stages = []
    with _sandbox(keep) as folder:
        data = hypotheses.load(toy)
        c = Context(sid=toy, folder=folder, engine_repo=find_engine_repo(engine_repo), hid=data.get("sheet") or data["hypotheses"][0]["id"],
                    source=json.loads((ROOT / "data/sources" / f"{toy}.json").read_text(encoding="utf-8")))
        for name, fn in STAGES:
            try:
                with contextlib.redirect_stdout(io.StringIO()):  # 刷る道は紙の場所を標準出力に出す
                    stages.append(Stage(name, PASSED, fn(c) or ""))
            except NotYet as e:
                stages.append(Stage(name, NOT_YET, str(e)))
                if not keep_going:
                    break
            except Skipped as e:
                stages.append(Stage(name, SKIPPED, str(e)))
            except Failed as e:
                stages.append(Stage(name, FAILED, str(e)))
                break
            except Exception as e:  # 部品の形が変わった時など。段の名前と一緒に知らせて、止める
                stages.append(Stage(name, FAILED, f"{type(e).__name__}: {e}"))
                break
    return Result(stages, c)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.cycle", description="鍵なしで 4 つのループを一周回す入口。部品の無い段で名指しして止まる")
    ap.add_argument("--toy", default=TOY, help="玩具の ID（既定は御来迎）")
    ap.add_argument("--keep-going", action="store_true", help="部品の無い段の後ろも回す")
    ap.add_argument("--keep", default=None, help="出来た物を残す場所（空か新しい場所）。既定は残さない")
    ap.add_argument("--engine-repo", default=None, help="paper-to-toy の場所")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4  # 呼び方の誤りは 4。argparse の既定の 2 は使わない決まり
    try:
        res = run(args.toy, args.keep_going, args.keep, args.engine_repo)
    except (OSError, ValueError) as e:
        print(f"できない: {e}", file=sys.stderr)
        return 4
    for i, s in enumerate(res.stages, 1):
        print(f"段 {i} {s.name}: {s.status}" + (f"（{s.detail}）" if s.detail else ""))
    if len(res.stages) < len(STAGES):
        print(f"ここで止めた（全部で {len(STAGES)} 段）。--keep-going で後ろの段も見る" if res.rc == 4 else f"ここで止めた（全部で {len(STAGES)} 段）")
    count = {st: sum(s.status == st for s in res.stages) for st in (PASSED, SKIPPED, NOT_YET, FAILED)}
    print("、".join(f"{st} {n} 段" for st, n in count.items()))
    return res.rc


if __name__ == "__main__":
    sys.exit(main())
