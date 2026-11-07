"""ワークショップで作られたおもちゃ（作例）の受け口（web.sakurei。本人の言葉 11-07「サイトにワークショップで作られたおもちゃを掲載したい。
写真データはこれから上げる」）。

見る線:
1. 空の時: 作例が無い時は、出す物も日も無い（写真が来る前の形）
2. 取り込み: 撮影の情報（JPEG の EXIF の位置・PNG の字の欄）が落ちる。記録は via="workshop"・作った日・結果は「わからない」・作った人の名と
   感想を持たない。記録の既定の一覧（束・輪の数・ギャラリー）と、前例を引く所から外れる
3. 人の確かめ: 確かめる前は出さない。「物だけ」と確かめた物だけが出て、その日が days() に入る。「人が入る」と確かめた物は出さない
4. 断る: 同じ写真の 2 度目・知らない玩具・読めない日・写真でない物・形の違う型紙の組。HEIC を読む部品が無い時は「検査できない」
5. 命令: add・list・jpeg の終わりの値
"""
import io
import os
import subprocess
import sys
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import hypotheses, loop, media_review, records  # noqa: E402
from web import sakurei, techo_site  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
tmp = tempfile.mkdtemp()


def jpeg_with_gps(name, color=(200, 120, 40)):
    """位置の情報（GPS）を持つ JPEG を、置き場の外に作る。"""
    im = Image.new("RGB", (64, 48), color)
    exif = Image.Exif()
    exif[0x8825] = {1: "N", 2: (35.0, 41.0, 0.0), 3: "E", 4: (139.0, 41.0, 0.0)}  # GPS の欄
    exif[0x010F] = "iPhone"  # 機種
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif)
    path = os.path.join(tmp, name)
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return path


def png_with_text(name):
    from PIL import PngImagePlugin

    info = PngImagePlugin.PngInfo()
    info.add_text("Comment", "撮った場所")
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 20, 30)).save(buf, "PNG", pnginfo=info)
    path = os.path.join(tmp, name)
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return path


# 1. 空の時
assert sakurei.examples() == [] and sakurei.days() == set() and sakurei.workshop_records() == []

# 2. 取り込み
a, b, c = jpeg_with_gps("IMG_0001.jpg"), jpeg_with_gps("IMG_0002.jpg", (40, 120, 200)), png_with_text("IMG_0003.png")
done, refused, cannot = sakurei.add([a, b], G, "2026-11-06", sheet_set="goraigo-v10")
assert cannot is None and refused == [] and len(done) == 2, (done, refused, cannot)
(r1, n1, _), (r2, n2, _) = done
done_png, refused_png, _ = sakurei.add([c], T, "2026-11-04")
assert refused_png == [] and len(done_png) == 1, refused_png
(r3, n3, _), = done_png
for rid, name in ((r1, n1), (r2, n2)):
    stored = (techo_site.media_dir(rid) / name).read_bytes()
    with Image.open(io.BytesIO(stored)) as im:
        assert not im.getexif(), (rid, "撮影の情報が残った")
    assert b"Exif" not in stored and b"iPhone" not in stored, rid
stored_png = (techo_site.media_dir(r3) / n3).read_bytes()
assert "撮った場所".encode() not in stored_png and b"tEXt" not in stored_png and b"iTXt" not in stored_png, "PNG の字の欄が残った"
rec = next(r for r in sakurei.workshop_records() if r["id"] == r1)
assert rec["via"] == records.WORKSHOP and rec["made_on"] == "2026-11-06" and rec["result"] == records.UNSURE and rec["sheet_set"] == "goraigo-v10"
assert rec["source_id"] == G and rec["hypothesis_id"] == hypotheses.sheet_of(G)["id"]
assert not any(k in rec for k in ("note", "impression", "who", "name", "answers")), "作った人の名と感想は持たない"
assert "sheet_set" not in next(r for r in sakurei.workshop_records() if r["id"] == r3), "組が分からない日は持たない"
# 記録の既定の一覧と前例から外れる（束・輪の数・ギャラリーの「他の人が作った物」に混ぜない）
assert not any(r["id"] in (r1, r2, r3) for r in records.all_records()) and not any(r["id"] in (r1, r2, r3) for r in records.all_records(uploads=True))
assert {r["id"] for r in records.all_records(workshop=True)} >= {r1, r2, r3}
# 解釈を人が確定しても、作例の記録は前例に入らない
assert loop.confirm_interpretation(r1, "確認者", "見本") == [] and loop.confirmed(r1)
assert not any(r["id"] == r1 for r in loop.confirmed_records(G)), "作例の記録が前例に混ざる"
html = techo_site.gallery_page([G, T])
assert r1 not in html and r3 not in html, "作例の記録がギャラリーの「他の人が作った物」に混ざる"

# 3. 人の確かめ: 確かめる前は出さない
assert sakurei.examples() == [] and sakurei.days() == set()
assert (r1, n1) in media_review.waiting() and (r3, n3) in media_review.waiting()
assert media_review.record(r1, n1, "object", "確認者") == [] and media_review.record(r2, n2, "people", "確認者") == []
assert [e["rid"] for e in sakurei.examples()] == [r1] and sakurei.days() == {"1106"}
assert media_review.record(r3, n3, "object", "確認者") == []
ex = sakurei.examples()
assert [e["rid"] for e in ex] == [r3, r1] and [e["day"] for e in ex] == ["2026-11-04", "2026-11-06"], "作った日の順"
assert ex[0]["photos"] == [n3] and ex[0]["set"] is None and ex[1]["set"] == "goraigo-v10"
assert sakurei.days() == {"1104", "1106"}

# 4. 断る
again, refused, _ = sakurei.add([a], G, "2026-11-06")
assert again == [] and refused and "もう取り込んである" in refused[0][1], refused
# ワークショップの日は 11 月 4・5・6・7 日の 4 回（本人の言葉 11-07）。ほかの日は受けない
assert sakurei.WORKSHOP_DAYS == ("2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07")
for args, why in (((a, "NDL-0000000-R0000000-L", "2026-11-06"), "知らない玩具"), ((a, G, "11-06"), "日は"), ((a, G, "2099-01-01"), "ワークショップの日"),
                  ((a, G, "2026-11-08"), "ワークショップの日"), ((a, G, "2026-11-03"), "ワークショップの日")):
    got, refused, _ = sakurei.add([args[0]], args[1], args[2])
    assert got == [] and refused and why in refused[0][1], (args, refused)
_, refused, _ = sakurei.add([a], G, "2026-11-06", sheet_set="v10")
assert refused and "型紙の組" in refused[0][1], refused
text = os.path.join(tmp, "note.txt")
with open(text, "w") as f:
    f.write("写真でない")
got, refused, _ = sakurei.add([text], G, "2026-11-06")
assert got == [] and refused and "写真" in refused[0][1], refused
heic = os.path.join(tmp, "IMG_8011.HEIC")
with open(heic, "wb") as f:
    f.write(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 64)
try:
    import pillow_heif  # noqa: F401
    has_heif = True
except ImportError:
    has_heif = False
if not has_heif:
    got, refused, cannot = sakurei.add([heic], G, "2026-11-06")
    assert got == [] and cannot and "HEIC" in cannot, cannot
assert len(sakurei.workshop_records()) == 3, "断った物の記録が残った"

# 5. 命令
cli = [sys.executable, "-m", "web.sakurei"]
run = lambda *x: subprocess.run([*cli, *x], capture_output=True, text=True, env={**os.environ})  # noqa: E731
listed = run("list")
assert listed.returncode == 0 and r1 in listed.stdout and "物だけ" in listed.stdout and "人が入る" in listed.stdout, listed
d = jpeg_with_gps("IMG_0004.jpg", (1, 2, 3))
added = run("add", d, "--toy", G, "--day", "2026-11-04")
assert added.returncode == 0 and "m1.jpg" in added.stdout, added
assert run("add", d, "--toy", G, "--day", "2026-11-04").returncode == 3, "同じ写真の 2 度目は 3"
assert run("add", d, "--toy", G).returncode == 4, "呼び方の誤りは 4"
if not has_heif:
    assert run("add", heic, "--toy", G, "--day", "2026-11-04").returncode == 4, "HEIC を読めない時は 4"
out = tempfile.mkdtemp()
made = run("jpeg", a, "--out", out)
assert made.returncode == 0 and os.path.exists(os.path.join(out, "IMG_0001.jpg")), made
with Image.open(os.path.join(out, "IMG_0001.jpg")) as im:
    assert not im.getexif() and "icc_profile" not in im.info, "jpeg の段の出力に撮影の情報か色の欄が残った"
print("ok 作例の受け口: 空の時・撮影の情報を落とす・記録の既定から外す・人の確かめ・断る・命令")
