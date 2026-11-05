"""撮る日の前の日の下ごしらえ: 要る道具を名前で確かめ、場面が取り寄せる絵を全部置き、控え（manifest.json）を残す。

使い方: python -m demo.prepare [--cache DIR] [--sources DIR] [--check] [--refresh]
  何も付けない = 道具を確かめ、足りない絵を取り寄せ、控えを書く（網が要る。前の日にこれだけ網のある所で回す）
  --check     = 網に出ず、控えと置いてある絵を照らす（撮る日の朝の確かめ）
  --refresh   = 置いてある絵を捨てて取り直す
exit: 0 = 道具がそろい、絵が全部ある / 4 = 道具が無い・絵が取れない・--check で控えと合わない（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 取り寄せる絵の置き場の名前は、場面が読むのと同じ（flip・scene2・scene4 は cache、scene3 は out/sources）。
  ここで置いた物を場面がそのまま見つけ、網に出ない。名前を二重に持たず、場面の定数から引く。
- 控えに大きさとハッシュを残す。撮る日に写しが壊れていたり、別の絵に替わっていたりしたら、書き出しの前に名指しで分かる。
- 網を切って書き出す間（offline）は、外への取り寄せを止めて URL を言う。手元の口（場面 3 が立てる画面）は通す。
"""
import argparse
import contextlib
import hashlib
import http.client
import json
import pathlib
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_CACHE = ROOT / "out/demo/cache"
DEFAULT_SOURCES = ROOT / "out/sources"
MANIFEST = "manifest.json"
FONT = "Noto Serif CJK JP"
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


def missing_tools(which=shutil.which, fonts=None):
    """書き出しに要る道具のうち、無い物の名前を返す。場面ごとに最初に落ちるより前に、全部を一度に言うため。
    fonts は fc-list の出力（試験で差し替える）。"""
    out = [t for t in ("ffmpeg", "ffprobe", "pdftoppm") if not which(t)]
    if not (which("google-chrome") or which("chromium")):
        out.append("google-chrome か chromium")
    if fonts is None:
        try:
            fonts = subprocess.run(["fc-list"], capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.TimeoutExpired):
            fonts = ""
            out.append("fc-list")
    if FONT not in fonts:
        out.append(f"字 {FONT}")
    return out


def wanted(cache, sources):
    """取り寄せる絵を [{label, url, path}] で返す。場面 1・2・4 の頁は cache、場面 3 の図は sources の下。"""
    # 場面はここで読む。demo.build が読み込むだけで落ちず、無い場面を 4 で言う・--partial で飛ばす道を残すため。
    from demo import flip, scene2, scene3, scene4
    cache, sources = pathlib.Path(cache), pathlib.Path(sources)
    rows = []

    def add(label, url, path):
        rows.append({"label": label, "url": url, "path": path})

    rec = json.loads(flip.FIGURES.read_text(encoding="utf-8"))["pages"][flip.PAGE]
    add(f"cache/{flip.PAGE}.jpg", f'{rec["iiif"]}/full/full/0/default.jpg', cache / f"{flip.PAGE}.jpg")
    rec2, _ = scene2.load_record()
    add("cache/1187053-R0000005-2400.jpg", rec2["image_url"], cache / "1187053-R0000005-2400.jpg")
    for pid, r in scene4.load_records()["pages"].items():
        add(f"cache/{pid}.jpg", f'{r["iiif"]}/full/full/0/default.jpg', cache / f"{pid}.jpg")
    src = json.loads((ROOT / "data/sources" / f"{scene3.SID}.json").read_text(encoding="utf-8"))
    add(f"sources/{scene3.SID}.jpg", src["image_url"], sources / f"{scene3.SID}.jpg")
    return rows


def _digest(path):
    return {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def fetch_all(cache, sources, fetch=None, force=False):
    """絵を全部置き、控えを書く。1 枚でも取れなければ、取れなかった物を全部名指しして 4（控えは書き直さない）。"""
    try:
        rows, bad = wanted(cache, sources), []
        if fetch is None:
            from demo.flip import fetch_image as fetch
    except ImportError as e:
        print(f"検査できない: 場面が読み込めない（{e}）", file=sys.stderr)
        return 4
    for w in rows:
        try:
            if force:
                tmp = w["path"].with_name(w["path"].name + ".new")  # 取り直しが失敗しても、今ある写しを失わない
                tmp.unlink(missing_ok=True)
                w["path"].parent.mkdir(parents=True, exist_ok=True)
                fetch(w["url"], tmp)
                tmp.replace(w["path"])
            else:
                w["path"].parent.mkdir(parents=True, exist_ok=True)
                fetch(w["url"], w["path"])
        except (OSError, http.client.HTTPException) as e:  # 途中で切れた通信は OSError にならない
            bad.append(f"検査できない: 絵が取れない（{w['label']}: {w['url']}: {e}）")
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 4
    files = {w["label"]: {"url": w["url"], **_digest(w["path"])} for w in rows}
    cache = pathlib.Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    (cache / MANIFEST).write_text(json.dumps({"files": files}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


def verify(cache, sources):
    """網に出ず、控えと置いてある絵を照らす。合わない所を名指しした文で返す。空なら合っている。"""
    path = pathlib.Path(cache) / MANIFEST
    try:
        files = json.loads(path.read_text(encoding="utf-8"))["files"]
    except (OSError, ValueError, KeyError, TypeError):
        return [f"絵の控え（{MANIFEST}）が無いか読めない。網のある所で python -m demo.prepare を先に回す"]
    try:
        rows = wanted(cache, sources)
    except ImportError as e:
        return [f"場面が読み込めない（{e}）"]
    out = []
    for w in rows:
        want = files.get(w["label"])
        if want is None:
            out.append(f"控えに無い: {w['label']}")
        elif not w["path"].exists():
            out.append(f"写しが無い: {w['label']}")
        else:
            got = _digest(w["path"])
            if (got["bytes"], got["sha256"]) != (want.get("bytes"), want.get("sha256")):
                out.append(f"控えと変わった: {w['label']}")
    return out


@contextlib.contextmanager
def offline():
    """この間だけ、外への取り寄せ（urllib）を止める。手元の口は通す。止めた時は URL を OSError で言う。"""
    real = urllib.request.urlopen

    def guarded(url, *a, **k):
        target = getattr(url, "full_url", url)
        if urllib.parse.urlparse(str(target)).hostname not in LOCAL_HOSTS:
            raise OSError(f"網を切っている（--offline）のに外へ取りに行った: {target}")
        return real(url, *a, **k)

    urllib.request.urlopen = guarded
    try:
        yield
    finally:
        urllib.request.urlopen = real


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(DEFAULT_CACHE))
    ap.add_argument("--sources", default=str(DEFAULT_SOURCES))
    ap.add_argument("--check", action="store_true", help="網に出ず、控えと置いてある絵を照らす")
    ap.add_argument("--refresh", action="store_true", help="置いてある絵を捨てて取り直す")
    a = ap.parse_args(argv)
    miss = missing_tools()
    if miss:
        print(f"検査できない: 足りない物: {'、'.join(miss)}（README の「デモ動画を作る」）", file=sys.stderr)
        return 4
    if a.check:
        wrong = verify(a.cache, a.sources)
        for line in wrong:
            print(f"検査できない: {line}", file=sys.stderr)
        if not wrong:
            print("下ごしらえ: 絵は控えと合っている。網を切って書き出せる（demo.build --offline）")
        return 4 if wrong else 0
    rc = fetch_all(pathlib.Path(a.cache), pathlib.Path(a.sources), force=a.refresh)
    if rc == 0:
        print(f"下ごしらえ: 絵 {len(wanted(a.cache, a.sources))} 枚がそろい、控えを {a.cache}/{MANIFEST} に書いた")
    return rc


if __name__ == "__main__":
    sys.exit(main())
