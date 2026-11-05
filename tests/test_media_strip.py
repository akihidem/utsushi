"""手帖で受ける写真と動画に、位置などの撮影情報を残さない。写真・動画でない物を置かない（#156）。

見本の中に印の文字列（位置の値）を入れ、置かれたファイルのバイトに残っていない事を見る。見本に印が入っている事も先に確かめる
（印が最初から無いと、何も外さなくても試験が通るため）。
"""
import io
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image, PngImagePlugin  # noqa: E402

from web import techo_site  # noqa: E402
from web.play_server import serve  # noqa: E402
from web.techo_site import media_dir  # noqa: E402

PLACE = b"+35.6895+139.6917"  # 見本の位置の値（東京の役所の辺り。誰かの家ではない）
STREAM_MARK = b"STREAM-MARK-1187"
SUBTITLE_MARK = b"SUBTITLE-MARK-1187"
G = "NDL-1187053-R0000005-L"
server = serve(0)
base = f"http://127.0.0.1:{server.server_address[1]}"
threading.Thread(target=server.serve_forever, daemon=True).start()
tmp = pathlib.Path(tempfile.mkdtemp())


def req(path, data, ctype="application/x-www-form-urlencoded"):
    r = urllib.request.Request(base + path, data=data, method="POST", headers={"Content-Type": ctype, "Origin": base})
    try:
        x = urllib.request.urlopen(r)
        return x.status, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# 記録の口は、紙を刷った後に開く
assert req(f"/toy/{G}/print", b"hypothesis=H-A")[0] in (200, 303)


def new_record():
    return json.loads(req(f"/toy/{G}/record-json", b"hypothesis=H-A&result=%E3%82%8F%E3%81%8B%E3%82%89%E3%81%AA%E3%81%84")[1])["id"]


def upload(data, ctype):
    """新しい記録に 1 つ上げる。返すのは (状態, 文, 置かれたファイルのバイト or None)。"""
    rid = new_record()
    code, text = req(f"/record/{rid}/media", data, ctype)
    return code, text, ((media_dir(rid) / text).read_bytes() if code == 201 else None)


def make_video(name):
    """音つきの短い動画を作る。位置の値を全体の欄に、別の印を流れの欄と字幕の流れに入れる。"""
    srt = tmp / "place.srt"
    srt.write_text(f"1\n00:00:00,000 --> 00:00:01,000\n{SUBTITLE_MARK.decode()}\n", encoding="utf-8")
    out = tmp / name
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=5:duration=1",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-i", str(srt),
                    "-map", "0", "-map", "1", "-map", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-c:s", "mov_text",
                    "-movflags", "use_metadata_tags",  # 既定の出し方は位置の欄を書かない。スマホの動画と同じく、欄が在る見本にする
                    "-metadata", f"com.apple.quicktime.location.ISO6709={PLACE.decode()}/", "-metadata", "creation_time=2026-11-04T09:00:00Z",
                    "-metadata:s:v", f"title={STREAM_MARK.decode()}", str(out)], check=True)
    data = out.read_bytes()
    for mark in (PLACE, STREAM_MARK, SUBTITLE_MARK):
        assert mark in data, f"見本の {name} に {mark} が入っていない"
    return data


def probe(data, name):
    path = tmp / f"probe-{name}"
    path.write_bytes(data)
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags:stream=codec_type:stream_tags", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def pixels(data):
    with Image.open(io.BytesIO(data)) as im:
        return im.convert("RGBA").tobytes(), im.size


picture = Image.effect_noise((32, 24), 40).convert("RGB")

# 1 PNG: 撮影情報（eXIf）と文の欄（tEXt）を外す。画素は変えない
exif = Image.Exif()
exif[0x010E] = PLACE.decode()  # 画像の説明の欄
info = PngImagePlugin.PngInfo()
info.add_text("Location", PLACE.decode())
buf = io.BytesIO()
picture.save(buf, "PNG", exif=exif, pnginfo=info)
sample = buf.getvalue()
assert PLACE in sample, "見本の PNG に印が入っていない"
code, text, saved = upload(sample, "image/png")
assert code == 201 and text == "m1.png", (code, text)
assert PLACE not in saved, "PNG に撮影情報が残った"
assert pixels(saved) == pixels(sample), "PNG の画素が変わった"
print("ok png")

# 2 JPEG: EXIF・XMP・IPTC・コメント・末尾の 2 枚目（スマホの MPF）を外す。画素は変えない。色の情報（ICC）は残す
exif = Image.Exif()
exif[0x010E] = PLACE.decode()
buf = io.BytesIO()
picture.save(buf, "JPEG", exif=exif, quality=90, icc_profile=b"ICC-KEEP" * 4)
first = buf.getvalue()
marker = lambda m, body: bytes([0xFF, m]) + (len(body) + 2).to_bytes(2, "big") + body  # noqa: E731
sample = (first[:2] + marker(0xED, b"Photoshop 3.0\x00" + PLACE) + marker(0xFE, PLACE) + marker(0xE2, b"MPF\x00" + PLACE)
          + first[2:] + first)  # 末尾に、同じ印の入った 2 枚目を続ける
assert sample.count(PLACE) >= 4, "見本の JPEG に印が入っていない"
code, text, saved = upload(sample, "image/jpeg")
assert code == 201 and text == "m1.jpg", (code, text)
assert PLACE not in saved and b"MPF\x00" not in saved, "JPEG に撮影情報が残った"
assert pixels(saved) == pixels(first), "JPEG の画素が変わった"
assert b"ICC-KEEP" in saved, "色の情報まで外した"
# 向きの欄は EXIF の中にある。外すと縦に撮った写真が横倒しになるので、先に向きを画素へ移す
exif = Image.Exif()
exif[0x0112] = 6  # 右へ 90 度
exif[0x010E] = PLACE.decode()
buf = io.BytesIO()
Image.effect_noise((40, 20), 40).convert("RGB").save(buf, "JPEG", exif=exif)
code, text, saved = upload(buf.getvalue(), "image/jpeg")
assert code == 201, (code, text)
assert PLACE not in saved, "向きのある JPEG に撮影情報が残った"
with Image.open(io.BytesIO(saved)) as im:
    assert im.size == (20, 40) and im.getexif().get(0x0112, 1) == 1, (im.size, dict(im.getexif()))
print("ok jpeg")

# 3 動画: MP4 と MOV。位置の欄・流れの欄・字幕の流れを落とし、絵と音は残す
for ctype, ext in (("video/mp4", "mp4"), ("video/quicktime", "mov")):
    code, text, saved = upload(make_video(f"sample.{ext}"), ctype)
    assert code == 201 and text == f"m1.{ext}", (code, text)
    for mark in (PLACE, STREAM_MARK, SUBTITLE_MARK):
        assert mark not in saved, f"{ext} に {mark} が残った"
    got = probe(saved, ext)
    assert sorted(s["codec_type"] for s in got["streams"]) == ["audio", "video"], got["streams"]
    tags = {**got.get("format", {}).get("tags", {}), **{k: v for s in got["streams"] for k, v in s.get("tags", {}).items()}}
    assert "creation_time" not in tags and not any("location" in k for k in tags), tags
print("ok video")

# 4 中身が型と合わない物は 422 で、何も置かない
real_png = io.BytesIO()
picture.save(real_png, "PNG")
real_jpeg = io.BytesIO()
picture.save(real_jpeg, "JPEG")
html = b"<!doctype html><script>alert(1)</script>"
for label, data, ctype in (
    ("HTML を動画と言う", html, "video/mp4"),
    ("HTML を写真と言う", html, "image/jpeg"),
    ("HTML を PNG と言う", html, "image/png"),
    ("PNG を JPEG と言う", real_png.getvalue(), "image/jpeg"),
    ("JPEG を PNG と言う", real_jpeg.getvalue(), "image/png"),
    ("JPEG を動画と言う", real_jpeg.getvalue(), "video/mp4"),
    ("頭だけ動画で中身の無い物", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200, "video/mp4"),
    ("頭だけ JPEG で中身の無い物", b"\xff\xd8\xff" + b"\x00" * 200, "image/jpeg"),
    ("頭だけ PNG で中身の無い物", b"\x89PNG\r\n\x1a\n" + b"\x00" * 200, "image/png"),
    ("ほかのファイルを指す一覧を動画と言う", b"#EXTM3U\n#EXT-X-ENDLIST\n", "video/mp4"),
):
    rid = new_record()
    code, text = req(f"/record/{rid}/media", data, ctype)
    assert code == 422, (label, code, text)
    assert not list(media_dir(rid).glob("*")) if media_dir(rid).exists() else True, (label, "ファイルが残った")
print("ok mismatch")

# 5 ffmpeg が無い機械: 動画は外せないので受けず、理由を言う。写真は受ける（外すのに ffmpeg が要らない）
sample_mp4 = make_video("again.mp4")
path = os.environ["PATH"]
os.environ["PATH"] = ""
try:
    code, text = req(f"/record/{new_record()}/media", sample_mp4, "video/mp4")
    assert code == 422 and "動画" in text and "ffmpeg" in text, (code, text)
    assert req(f"/record/{new_record()}/media", real_jpeg.getvalue(), "image/jpeg")[0] == 201
finally:
    os.environ["PATH"] = path
print("ok no ffmpeg")

# 6 外す作業で置き場を汚さない。数の上限も、動画の時に今までどおり効く
rid = new_record()
for i in range(techo_site.MAX_PER_RECORD):
    assert req(f"/record/{rid}/media", sample_mp4, "video/mp4")[0] == 201
assert sorted(p.name for p in media_dir(rid).iterdir()) == ["m1.mp4", "m2.mp4", "m3.mp4"], "作業のファイルが残った"
assert req(f"/record/{rid}/media", sample_mp4, "video/mp4")[0] == 422, "数の上限"
print("ok tidy")

server.shutdown()
shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(os.environ["OMOCHAE_DATA"], ignore_errors=True)
print("ok")
