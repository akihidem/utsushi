"""作例の仕分けの段（web.sakurei の sort・toy・place・hold。本人の言葉 11-07「全部一緒にしてしまったので日毎にはしない。ここに上げていく」）。

見る線:
1. 日: 撮影の日時（DateTimeOriginal と時差の欄）を Asia/Tokyo の日で読み、4 回のワークショップの日に振る。ほかの日・日時の無い物は不明。
   直した日時（DateTime）では振らない
2. 撮影の情報: 仕分けの置き場の写しにも帳面にも、日時・位置・機種は残らない（日だけ）。元の folder には書かない
3. 動画は写真と分けて名を挙げるだけ（置き場に置かない）。写真でない物は受けない。同じ写真は 2 度置かない
4. 玩具: 人が決めるまで不明。知らない玩具・4 回でない日・形の違う組は受けない。不明は書いてよい
5. 入れる: 日と玩具の両方が決まった物だけが作例の記録に入り（人の確かめ待ち）、写しは消える。不明の物は残り、hold に出る
6. 命令の終わりの値。別の置き場へ同じ取り込みを回すと、前の決めを写して同じ記録ができる（不明は不明のまま）
"""
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import media_review, records  # noqa: E402
from web import sakurei  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
up = pathlib.Path(tempfile.mkdtemp())  # まとめて上がった folder（Drive の代わり）


def shot(name, when=None, off=None, edited=None, color=(120, 80, 40), fmt="JPEG"):
    """撮影の日時（と時差・直した日時）と位置と機種を持つ写真を、上がった folder に作る。"""
    exif = Image.Exif()
    exif[0x010F] = "iPhone"
    exif[0x8825] = {1: "N", 2: (35.0, 41.0, 0.0), 3: "E", 4: (139.0, 41.0, 0.0)}
    if edited:
        exif[0x0132] = edited
    sub = {}
    if when:
        sub[0x9003] = when
    if off:
        sub[0x9011] = off
    if sub:
        exif[0x8769] = sub
    buf = io.BytesIO()
    Image.new("RGB", (80, 60), color).save(buf, fmt, exif=exif) if fmt == "JPEG" else Image.new("RGB", (80, 60), color).save(buf, fmt)
    (up / name).write_bytes(buf.getvalue())
    return up / name


shot("IMG_0101.jpg", "2026:11:06 14:39:05", "+09:00", color=(200, 10, 10))
shot("IMG_0102.jpg", "2026:11:04 10:30:00", "-05:00", color=(10, 200, 10))   # 時差つき: 東京では 11-05 の 00:30
shot("IMG_0103.jpg", "2026:11:07 09:00:00", None, color=(10, 10, 200))       # 時差の欄なし: 書いてある時のまま
shot("IMG_0104.jpg", "2026:11:08 10:00:00", "+09:00", color=(90, 90, 90))    # 4 回の日でない
shot("IMG_0105.jpg", None, None, edited="2026:11:06 12:00:00", color=(30, 30, 30))  # 直した日時だけ（撮った日時は無い）
shot("IMG_0106.png", fmt="PNG", color=(50, 150, 50))                          # 日時の無い写真
(up / "IMG_0107.MOV").write_bytes(b"\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00" + b"\x00" * 64)
(up / "ichishu.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00" + b"\x00" * 64)
(up / "memo.txt").write_text("写真でない")
(up / ".DS_Store").write_bytes(b"\x00\x01")
before = {p.name: p.read_bytes() for p in up.iterdir()}

# 空の時
assert sakurei._hold_list() == [] and sakurei.place() == ([], [])

# 1〜3. 仕分け
held, videos, skipped, cannot = sakurei.sort(up)
assert cannot is None, cannot
assert sorted(held) == ["IMG_0101.jpg", "IMG_0102.jpg", "IMG_0103.jpg", "IMG_0104.jpg", "IMG_0105.jpg", "IMG_0106.png"], held
assert sorted(videos) == ["IMG_0107.MOV", "ichishu.mp4"], videos
assert skipped == [("memo.txt", "写真（JPEG・PNG・HEIC）として読めない")], skipped
items = {it["name"]: it for it in sakurei._hold_list()}
days = {n: it["day"] for n, it in items.items()}
assert days == {"IMG_0101.jpg": "2026-11-06", "IMG_0102.jpg": "2026-11-05", "IMG_0103.jpg": "2026-11-07", "IMG_0104.jpg": sakurei.UNKNOWN,
                "IMG_0105.jpg": sakurei.UNKNOWN, "IMG_0106.png": sakurei.UNKNOWN}, days
assert all(it["toy"] == sakurei.UNKNOWN for it in items.values()), "玩具を勝手に決めた"
hd = sakurei.hold_dir()
book = (hd / "hold.json").read_text(encoding="utf-8")
for bad in ("14:39", "10:30", "2026:11", "+09:00", "-05:00", "iPhone", "GPS"):
    assert bad not in book, (bad, "帳面に撮影の日時か機種が残った")
for it in items.values():
    data = (hd / f"{it['fp']}.jpg").read_bytes()
    with Image.open(io.BytesIO(data)) as im:
        assert not im.getexif(), (it["name"], "写しに撮影の情報が残った")
    assert b"iPhone" not in data and b"2026:11" not in data, it["name"]
    assert set(it) == {"fp", "name", "day", "toy"}, it
assert not any(p.suffix.lower() in (".mov", ".mp4") for p in hd.iterdir()), "動画を置き場に置いた"
assert {p.name: p.read_bytes() for p in up.iterdir()} == before, "上がった folder に書いた"
# 同じ写真は 2 度置かない
again = sakurei.sort(up)
assert again[0] == [] and len(sakurei._hold_list()) == 6, again

# 4. 玩具
assert sakurei.set_toy(["IMG_0101.jpg"], "NDL-0000000-R0000000-L")[1], "知らない玩具を受けた"
assert sakurei.set_toy(["IMG_0104.jpg"], G, day="2026-11-08")[1], "4 回でない日を受けた"
assert sakurei.set_toy(["IMG_0101.jpg"], G, sheet_set="v14")[1], "形の違う組を受けた"
assert sakurei.set_toy(["nai.jpg"], G)[1], "無い物を受けた"
assert sakurei.set_toy(["IMG_0101.jpg"], G, sheet_set="goraigo-v14") == ([items["IMG_0101.jpg"]["fp"]], [])
assert sakurei.set_toy([items["IMG_0102.jpg"]["fp"]], T)[0], "指紋で選べない"
assert sakurei.set_toy(["IMG_0103.jpg"], sakurei.UNKNOWN)[0], "不明を書けない"
assert sakurei.set_toy(["IMG_0105.jpg"], T)[0]  # 玩具は分かったが日が不明のまま
assert sakurei.set_toy(["IMG_0106.png"], G, day="2026-11-04")[0], "人が決めた日を書けない"

# 5. 入れる: 日と玩具の両方が決まった物だけ
done, refused = sakurei.place()
assert refused == [] and sorted(n for _, n in done) == ["IMG_0101.jpg", "IMG_0102.jpg", "IMG_0106.png"], (done, refused)
recs = {r["id"]: r for r in sakurei.workshop_records()}
by = {n: recs[rid] for rid, n in done}
assert (by["IMG_0101.jpg"]["source_id"], by["IMG_0101.jpg"]["made_on"], by["IMG_0101.jpg"]["sheet_set"]) == (G, "2026-11-06", "goraigo-v14")
assert (by["IMG_0102.jpg"]["source_id"], by["IMG_0102.jpg"]["made_on"]) == (T, "2026-11-05") and "sheet_set" not in by["IMG_0102.jpg"]
assert by["IMG_0106.png"]["made_on"] == "2026-11-04"
assert all(r["via"] == records.WORKSHOP for r in recs.values()) and len(recs) == 3
assert sakurei.examples() == [], "人の確かめの前に出た"
assert all((rid, name) in media_review.waiting() for rid in recs for name in __import__("web.techo_site", fromlist=["x"]).media_of(rid))
left = [it for it in sakurei._hold_list() if not it.get("rid")]
assert sorted(it["name"] for it in left) == ["IMG_0103.jpg", "IMG_0104.jpg", "IMG_0105.jpg"], left
assert all((hd / f"{it['fp']}.jpg").exists() for it in left), "残る物の写しが消えた"
assert not any((hd / f"{it['fp']}.jpg").exists() for it in sakurei._hold_list() if it.get("rid")), "入れた物の写しが残った"
assert sakurei.place() == ([], []), "2 度入れた"
assert sakurei.sort(up)[0] == [], "入れた後に同じ写真をまた置いた"

# 6. 命令
cli = [sys.executable, "-m", "web.sakurei"]
run = lambda *x: subprocess.run([*cli, *x], capture_output=True, text=True, env={**os.environ})  # noqa: E731
h = run("hold")
assert h.returncode == 0 and h.stdout.count("\n") == 3 and "IMG_0105.jpg" in h.stdout and "IMG_0101.jpg" not in h.stdout, h
assert run("toy", "IMG_0103.jpg", "--toy", "NDL-0000000-R0000000-L").returncode == 3
assert run("toy", "IMG_0103.jpg", "--toy", G).returncode == 0
p = run("place")
assert p.returncode == 0 and "IMG_0103.jpg" in p.stdout, p
assert run("sort", str(up / "nai")).returncode == 4, "無い folder は 4"
s = run("sort", str(up))
assert s.returncode == 3 and "動画（触らない） IMG_0107.MOV" in s.stdout and "memo.txt" in s.stderr, s
heic = pathlib.Path(tempfile.mkdtemp())
(heic / "IMG_8011.HEIC").write_bytes(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 64)
try:
    import pillow_heif  # noqa: F401
except ImportError:
    assert run("sort", str(heic)).returncode == 4, "HEIC を読めない時は 4"
assert json.loads((hd / "hold.json").read_text(encoding="utf-8")) == sakurei._hold_list()
# 別の置き場（審査の場）へ同じ取り込みを回す: 前の帳面の決め（玩具・人が決めた日・組）を写し、決め直さずに同じ記録ができる
first = hd / "hold.json"
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
assert sakurei._hold_list() == [] and sakurei.workshop_records() == []
r2 = run("sort", str(up), "--like", str(first))
assert r2.returncode == 3, r2  # memo.txt だけ受けない
p2 = run("place")
assert p2.returncode == 0, p2
again_recs = sorted((r["source_id"], r["made_on"], r.get("sheet_set")) for r in sakurei.workshop_records())
assert again_recs == sorted([(G, "2026-11-06", "goraigo-v14"), (T, "2026-11-05", None), (G, "2026-11-04", None), (G, "2026-11-07", None)]), again_recs
assert sorted(it["name"] for it in sakurei._hold_list() if not it.get("rid")) == ["IMG_0104.jpg", "IMG_0105.jpg"], "不明の物が写しで決まった"
assert all(set(it) <= {"fp", "name", "day", "toy", "set", "rid"} for it in sakurei._hold_list()), "前の置き場の記録の番号を写した"
assert run("sort", str(up), "--like", str(up / "nai.json")).returncode == 4, "読めない帳面は 4"
print("ok 作例の仕分け: 撮影の日で 4 回に振る・撮影の情報を残さない・動画を分ける・玩具は人が決める・両方決まった物だけ入れる")
