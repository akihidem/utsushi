"""確かめた写真が、同時の上げや後からの書き込みで別の写真に差し替わらない（安全の事項 2 への対応）。

前の形: 保存（techo_site.save_media）は、変換の前に数えた番号の名（m<数+1>）へそのまま書き、確認（media_review）は名だけに結んでいた。
同じ記録へ 2 つの写真を同時に上げ、片方の変換が遅れる間にもう片方を保存して「物だけ」と確かめると、遅れた方が同じ名に書かれて
確かめた写真が差し替わり、確かめた扱いのまま公開に出た。

見る事:
1. 変換を待たせて順を固定した同時の上げで、2 つは別の名になり、先に確かめた写真の中身は替わらず、公開に出るのは確かめた中身だけ
2. 確かめた後に名の中身が替わった時（置き場へ直に書かれた時）は、公開にも配信にも出さず、確認を待つ物に戻る。確認には中身の要約（sha256）が残る
3. 要約の無い前からの確認（この直しの前に確かめた物）は、前のとおり公開に出る（見た目と挙動を替えない）
4. 名の形と順は前のまま（m1・m2・m3）。同時に 5 つ上げても 3 つまで（1 つの記録の上限）で、名が重ならない
5. 同時の上げで、上げた画面の控え（owners.json）が片方消えない
"""
import io
import json
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import media_review as mr, records  # noqa: E402
from web import techo_site as ts  # noqa: E402


def png(color):
    b = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(b, "PNG")
    return b.getvalue()


def new_record(rid):
    records.folder().mkdir(parents=True, exist_ok=True)
    (records.folder() / f"{rid}.json").write_text("{}", encoding="utf-8")
    return rid


# 1
rid = new_record("R-9902")
slow, fast = png("red"), png("blue")
entered, release = threading.Event(), threading.Event()
clean = ts.clean_photo


def delayed(data, ext):
    if data == slow:
        entered.set()
        assert release.wait(10)
    return clean(data, ext)


with patch.object(ts, "clean_photo", side_effect=delayed):
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(ts.save_media, rid, "image/png", slow)
        assert entered.wait(10)
        first, why = ts.save_media(rid, "image/png", fast)
        assert first and not why, why
        assert mr.record(rid, first, "object", "確かめる人") == []
        release.set()
        second, why = fut.result(timeout=10)
assert second and second != first, ("同じ名に 2 つ目が書かれた", first, second)
assert Image.open(ts.media_dir(rid) / first).convert("RGB").getpixel((0, 0)) == (0, 0, 255), "確かめた写真の中身が替わった"
assert mr.public(rid, ts.media_of(rid)) == [first], ("公開に出るのは確かめた中身だけ", mr.public(rid, ts.media_of(rid)))
assert (rid, second) in mr.waiting(), "遅れた方は確認を待つ物"

# 2
entry = json.loads((mr._folder(rid) / "review.json").read_text(encoding="utf-8"))[first]
assert entry.get("sha256") == mr.digest(ts.media_dir(rid) / first) and entry.get("size") == (ts.media_dir(rid) / first).stat().st_size, entry
(ts.media_dir(rid) / first).write_bytes(png("green"))  # 置き場へ直に書かれた（前の上書きと同じ形）
assert mr.public(rid, [first]) == [] and mr.shown_to(rid, [first]) == [], "中身が替わった物を公開・配信に出した"
assert (rid, first) in mr.waiting(), "中身が替わった物が確認を待つ物に戻らない"

# 3
rid3 = new_record("R-9903")
legacy, _ = ts.save_media(rid3, "image/png", png("yellow"))
(mr._folder(rid3) / "review.json").write_text(json.dumps({legacy: {"shows": "object", "reviewer": "前の人", "at": "2026-11-07T10:00+09:00"}}), encoding="utf-8")
assert mr.public(rid3, [legacy]) == [legacy] and (rid3, legacy) not in mr.waiting(), "前からの確認が頁から消えた"

# 4
rid4 = new_record("R-9904")
colors = ["#100000", "#200000", "#300000", "#400000", "#500000"]
with ThreadPoolExecutor(max_workers=5) as pool:
    got = list(pool.map(lambda c: ts.save_media(rid4, "image/png", png(c)), colors))
names = sorted(n for n, _ in got if n)
assert names == ["m1.png", "m2.png", "m3.png"], names
assert sum(1 for n, why in got if not n and why == "1 つの記録に 3 つまで") == 2, got
assert not [p for p in ts.media_dir(rid4).iterdir() if p.name.startswith(".up-")], "仮の名のファイルが残った"
pixels = {Image.open(ts.media_dir(rid4) / n).convert("RGB").getpixel((0, 0)) for n in names}
assert len(pixels) == 3, ("同じ名に 2 つ書かれた（中身が重なった）", pixels)

# 5
rid5 = new_record("R-9905")
with ThreadPoolExecutor(max_workers=3) as pool:
    saved = list(pool.map(lambda c: ts.save_media(rid5, "image/png", png(c))[0], ("#010101", "#020202", "#030303")))
with ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(lambda n: mr.claim(rid5, n, f"key-{n}"), saved))
owners = json.loads((mr._folder(rid5) / "owners.json").read_text(encoding="utf-8"))
assert sorted(owners) == sorted(saved) and all(mr._mine(rid5, n, f"key-{n}") for n in saved), owners
print("ok 確かめた写真は差し替わらない: 同時の上げは別の名・確認は中身の要約に結び、中身が替われば出さずに待ちへ・前からの確認はそのまま・名は m1〜m3・控えは消えない")
