"""記録の読み書きの壊れにくさの試験（#153）: 読めない記録は飛ばす・書きかけを作らない・同時に押しても番号が重ならない。

同時の試験は、読んだ直後に待ちを入れて「読む → 足す → 書く」の間に別の要求が入る形を必ず作る。運に任せると、排他が無くても通る事がある。
"""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api import generate  # noqa: E402
from omochae import hypotheses, loop, records  # noqa: E402
from web.play_server import serve  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
T = "NDL-1187053-R0000014-R"
gs = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))


def fresh():
    """試験ごとに別の置き場にする。"""
    d = pathlib.Path(tempfile.mkdtemp())
    os.environ["OMOCHAE_DATA"] = str(d)
    for sub in ("records", "loop", "decisions"):
        (d / sub).mkdir()
    return d


def rec(source=G):
    rid, fs = records.add({"source_id": source, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動かない", "opened_deg": 60, "opener": "紙の力", "fixes": [], "note": "開き切らない"})
    assert not fs, fs
    return rid


def err_of(fn):
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        out = fn()
    return out, buf.getvalue()


@contextlib.contextmanager
def patched(mod, name, value):
    real = getattr(mod, name)
    setattr(mod, name, value)
    try:
        yield real
    finally:
        setattr(mod, name, real)


def slowed(fn, seconds=0.03):
    def wrapped(*a, **k):
        out = fn(*a, **k)
        time.sleep(seconds)
        return out
    return wrapped


def fails(*_a, **_k):
    raise OSError("確定の直前で落ちた")


def run_threads(n, fn):
    """n 本を同時に走らせる。スレッドの中の失敗を握りつぶさず、固まったら落とす。"""
    gate, errors = threading.Barrier(n), []

    def one(i):
        try:
            gate.wait()
            fn(i)
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))

    ts = [threading.Thread(target=one, args=(i,), daemon=True) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    assert not any(t.is_alive() for t in ts), "固まった"
    assert not errors, errors


def check_lists_skip_unreadable():
    d = fresh()
    r1 = rec()
    (d / "records" / "R-9999.json").write_text('{"id": "R-99', encoding="utf-8")
    got, err = err_of(lambda: records.all_records(G))
    assert [r["id"] for r in got] == [r1], got
    assert "R-9999.json" in err, err
    got, err = err_of(lambda: loop.confirmed_records(G))
    assert got == [] and "R-9999.json" in err, (got, err)


def check_side_files_skip_unreadable():
    """記録に添える物（説明・解釈・観察・採った仮説・版・直しの台帳）も、1 つ読めないだけで頁を止めない。"""
    d = fresh()
    rid = rec()
    extra = d / "loop" / f"extra-hypotheses-{G}.json"
    extra.write_text("[{", encoding="utf-8")
    data, err = err_of(lambda: loop.overlay({"source_id": G, "hypotheses": []}))
    assert data["hypotheses"] == [] and extra.name in err, (data, err)
    extra.unlink()
    for name, read in ((f"explanation-{rid}.json", lambda: loop.explanation(rid)), (f"interpretation-{rid}.json", lambda: loop.interpretation(rid))):
        (d / "loop" / name).write_text("{", encoding="utf-8")
        got, err = err_of(read)
        assert got is None and name in err, (name, got, err)
    (d / "loop" / "template-change-0001.json").write_text("{", encoding="utf-8")
    got, err = err_of(loop.template_changes)
    assert got == [] and "template-change-0001.json" in err, (got, err)
    # 壊れた版は無い版として扱う。一番新しい版の番号にも数えない
    (d / "loop" / f"version-{G}-H-A-2.json").write_text("{", encoding="utf-8")
    got, err = err_of(lambda: loop.latest_version(G, "H-A"))
    assert got == 1 and f"version-{G}-H-A-2.json" in err, (got, err)
    got, err = err_of(lambda: loop.version_params(G, "H-A", 2))
    assert got == (None, None), got
    from api import observe
    (d / "loop" / f"observation-{rid}.json").write_text("{", encoding="utf-8")
    got, err = err_of(lambda: observe.observation(rid))
    assert got is None and f"observation-{rid}.json" in err, (got, err)


def check_required_file_names_itself():
    """必ず要る 1 件が壊れている時は、飛ばさず止めて、どのファイルかを言う。"""
    d = fresh()
    (d / "records" / "R-9999.json").write_text("{", encoding="utf-8")
    try:
        loop.record("R-9999")
    except ValueError as e:
        assert "R-9999.json" in str(e), str(e)
    else:
        raise AssertionError("壊れた記録を黙って通した")


def check_pages_open():
    """本文の確かめの形: 書きかけの記録が 1 つあっても頁が 200 で開き、どのファイルかが記録に出る。"""
    d = fresh()
    rec()
    (d / "records" / "R-9999.json").write_text('{"id": "R-99', encoding="utf-8")
    server = serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        for path in (f"/toy/{G}", f"/toy/{T}", f"/toy/{G}/techo", "/gallery", f"/zukan/{G}"):
            def fetch():
                try:
                    with urllib.request.urlopen(base + path) as r:
                        return r.status
                except urllib.error.HTTPError as e:
                    return e.code
            code, err = err_of(fetch)
            assert code == 200, (path, code, err)
            assert "R-9999.json" in err, (path, err)
    finally:
        server.shutdown()


def check_writes_are_atomic():
    """記録・輪・予想の書き込みは全部、一時ファイル → 置き換え を通る。確定の直前で落ちると、前の中身だけが残る。"""
    d = fresh()
    target = d / "loop" / "explanation-R-0001.json"
    loop._write(target, {"v": 1})
    with patched(os, "replace", fails), patched(os, "link", fails):
        for name, write in (("輪", lambda: loop._write(target, {"v": 2})),
                            ("予想", lambda: hypotheses.save_prediction(G, "筒を押すと開く")),
                            ("自分の仮説", lambda: hypotheses.save_own(G, "名", "動かし方", "根拠")),
                            ("記録", rec)):
            try:
                write()
            except OSError:
                continue
            raise AssertionError(f"{name}: 確定を通らずに書いた")
    assert json.loads(target.read_text(encoding="utf-8")) == {"v": 1}
    left = [p.name for sub in ("records", "loop", "decisions") for p in (d / sub).iterdir() if p.name != target.name and p.name != ".lock"]
    assert not left, left


def check_atomic_keeps_private_mode():
    """持ち寄りの置き場の 0600 は変えない。記録の側は今までどおり umask に従う。"""
    from omochae import contrib
    d = fresh()
    contrib._write_atomic(d / "private.json", "{}")
    assert (d / "private.json").stat().st_mode & 0o777 == 0o600
    loop._write(d / "loop" / "x.json", {})
    old = os.umask(0)
    os.umask(old)
    assert (d / "loop" / "x.json").stat().st_mode & 0o777 == 0o666 & ~old


def check_lock_reentrant():
    """同じスレッドが重ねて取っても固まらない（採る処理の中で別の保存を呼ぶ形）。"""
    from omochae import store
    d = fresh()
    done = []

    def nested():
        with store.locked(d), store.locked(d):
            done.append(1)

    t = threading.Thread(target=nested, daemon=True)
    t.start()
    t.join(10)
    assert done == [1], "固まった"


def check_read_add_write():
    fresh()
    with patched(loop, "_read", slowed(loop._read)):
        run_threads(6, lambda i: loop.confirm_sheet(G, "H-A", 1, f"人{i}", "組"))
    assert len(loop.sheet_confirmations(G)[0]["confirmations"]) == 6


def check_own_numbers():
    fresh()
    with patched(hypotheses, "own_paths", slowed(hypotheses.own_paths)):
        run_threads(6, lambda i: hypotheses.save_own(G, f"名{i}", "動かし方", "根拠"))
    assert sorted(h["id"] for h in hypotheses.own_hypotheses(G)) == [f"OWN-{i}" for i in range(1, 7)]


def check_proposal_numbers():
    fresh()
    ids = []
    with patched(loop, "check_proposal", lambda p, s: []), patched(loop, "_now", slowed(loop._now)):
        run_threads(6, lambda i: ids.append(loop.save_proposal({"hypothesis_id": "H-A", "record_ids": ["R-0001"], "changes": []}, gs, "human")[0]))
    assert sorted(ids) == [f"P-{i:04d}" for i in range(1, 7)], ids
    assert len(list(loop.folder().glob("proposal-*.json"))) == 6


def check_generated_numbers():
    fresh()
    ids = []
    with patched(loop, "_now", slowed(loop._now)):
        run_threads(6, lambda i: ids.append(generate._save_draft(G, [], [], {"hypotheses": []}, {"model": "人"})))
    assert sorted(ids) == [f"G-{i:04d}" for i in range(1, 7)], ids


def check_version_numbers():
    """本文の確かめの形: 同時に 2 本の「次の版」を送っても、版の番号が重ならない。"""
    fresh()
    with patched(loop, "check_proposal", lambda p, s: []):
        pids = [loop.save_proposal({"hypothesis_id": "H-A", "record_ids": ["R-0001"], "changes": [{"param": "x", "to": n}]}, gs, "human")[0] for n in (1, 2)]
        made = []
        with patched(loop, "latest_version", slowed(loop.latest_version)):
            run_threads(2, lambda i: made.append(loop.adopt(pids[i], "人", accept_params=("x",))))
    assert sorted(m["version"] for m, fs in made) == [2, 3], made
    assert sorted(json.loads((loop.folder() / f"version-{G}-H-A-{n}.json").read_text(encoding="utf-8"))["proposal"] for n in (2, 3)) == sorted(pids)


def check_adopt_once():
    """同じ提案を 2 台が同時に採っても、採れるのは 1 回だけ。"""
    fresh()
    with patched(loop, "check_proposal", lambda p, s: []):
        pid, _ = loop.save_proposal({"hypothesis_id": "H-A", "record_ids": ["R-0001"], "changes": [{"param": "x", "to": 1}]}, gs, "human")
        made = []
        with patched(loop, "_read", slowed(loop._read)):
            run_threads(2, lambda i: made.append(loop.adopt(pid, f"人{i}", accept_params=("x",))))
    assert sorted(bool(fs) for _, fs in made) == [False, True], made
    assert loop.latest_version(G, "H-A") == 2


CHILD = """
import sys, time
from omochae import loop
real = loop._read
def slow(*a, **k):
    out = real(*a, **k)
    time.sleep(0.03)
    return out
loop._read = slow
for i in range(8):
    assert loop.confirm_sheet(sys.argv[1], "H-A", 1, "人", "組") == []
"""


def check_across_processes():
    """デモは 2 つのサーバが別のプロセスで同じ置き場に書く。プロセスをまたいでも足した分が消えない。"""
    fresh()
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    kids = [subprocess.Popen([sys.executable, "-c", CHILD, G], env=env) for _ in range(3)]
    assert [k.wait(120) for k in kids] == [0, 0, 0]
    assert len(loop.sheet_confirmations(G)[0]["confirmations"]) == 24


CHECKS = [check_lists_skip_unreadable, check_side_files_skip_unreadable, check_required_file_names_itself, check_pages_open,
          check_writes_are_atomic, check_atomic_keeps_private_mode, check_lock_reentrant, check_read_add_write, check_own_numbers,
          check_proposal_numbers, check_generated_numbers, check_version_numbers, check_adopt_once, check_across_processes]
failed = []
for check in CHECKS:
    try:
        check()
    except Exception:  # noqa: BLE001
        failed.append(check.__name__)
        print(f"落ちた: {check.__name__}\n{traceback.format_exc(limit=2)}", file=sys.stderr)
assert not failed, failed
