"""上げた写真と動画を、人の確認を通してから出す（本人の決定 11-05、#314）。
物だけが写った物は公開する。人や声が入る物は字だけにする。確かめるのは人だけで、機械は見分けない。
動画の音は取り込みで落とす（本人の決定の文「声は字にして、声そのものは残しません」）。"""
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_DATA"] = str(tmp)
os.environ["OMOCHAE_SAMPLES"] = "0"

from PIL import Image  # noqa: E402

from omochae import media_review, records  # noqa: E402
from web import techo_site, toy  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
PLACE = "GPS35.7148N139.7967E_home"


def jpeg():
    """位置の印の入った写真。印が最初から無いと、何も外さなくても試験が通るので、先に入っている事を見る。"""
    exif = Image.Exif()
    exif[0x010e] = PLACE
    buf = io.BytesIO()
    Image.effect_noise((32, 24), 40).convert("RGB").save(buf, "JPEG", exif=exif)
    data = buf.getvalue()
    assert PLACE.encode() in data
    return data


def video(tail="mp4", audio=True):
    """音つきの短い動画。音が最初から無いと、音を落とす事を確かめられない。"""
    out = tmp / f"sample.{tail}"
    sound = ["-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-c:a", "aac"] if audio else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=5:duration=1", *sound,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-metadata", "creation_time=2026-11-04T09:00:00Z", str(out)], check=True)
    assert streams(out.read_bytes()) == (["audio", "video"] if audio else ["video"])
    return out.read_bytes()


def streams(data):
    path = tmp / "probe.mp4"
    path.write_bytes(data)
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return sorted(s["codec_type"] for s in json.loads(r.stdout)["streams"])


def new_record(words="首が長く揺れた"):
    rid, failures = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "わからない", "impression": words, "fixes": []})
    assert rid and not failures, failures
    return rid


def gallery(**kw):
    return techo_site.gallery_page([G], **kw)


srv = serve(0)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()


def fetch(path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# 確認の前は、ギャラリーと玩具の頁の「他の人が作った物」に出ない。字は出る。手帖には上げた本人の画面にだけ出る（上げた人が受け取りを確かめる所）。
rid = new_record()
assert techo_site.save_media(rid, "image/jpeg", jpeg())[0] == "m1.jpg"
assert media_review.waiting() == [(rid, "m1.jpg")]
url = f"/record/{rid}/media/m1.jpg"
assert url not in gallery(), "確認の前の写真をギャラリーに出さない"
assert "首が長く揺れた" in gallery(), "字は出る"
assert url not in toy.toy_page(G), "確認の前の写真を玩具の頁に出さない"
assert url not in techo_site.records_page(G), "別の人の手帖の記録の頁に確認の前の写真を出さない"
media_review.claim(rid, "m1.jpg", "上げた画面の鍵")
assert url in techo_site.records_page(G, up_key="上げた画面の鍵"), "上げた本人の手帖の記録の頁には出る（受け取りを確かめる）"
assert url not in techo_site.records_page(G, up_key="別の鍵"), "別の鍵では出ない"

# 物だけと確かめた物は出る。撮影の情報は外れている。
assert media_review.record(rid, "m1.jpg", "object", "確認者") == []
assert media_review.waiting() == []
# 本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などはすべてもちよるに統合する。」で、つくるの頁から記録の札を外した。
# 確かめた写真は、もちよる（ギャラリー）と手帖の記録の頁に出る。つくるの頁には出ない
assert url in gallery() and url in techo_site.records_page(G) and url not in toy.toy_page(G)
code, served = fetch(url)
assert code == 200 and PLACE.encode() not in served, "撮影の情報を外した物が出る"
# 合言葉なしで開いた場は、確かめた物でも出さない（J-028 を変えない）
closed = gallery(photos=False)
assert url not in closed and "首が長く揺れた" not in closed

# 確認を取り消すと消える
assert media_review.revoke(rid, "m1.jpg") == []
assert url not in gallery() and media_review.waiting() == [(rid, "m1.jpg")]

# 人や声が入るとされた物は、映像を出さず字だけ。返す道も返さない。手帖にも出さない。
assert media_review.record(rid, "m1.jpg", "people", "確認者") == []
assert url not in gallery() and "首が長く揺れた" in gallery()
assert url not in toy.toy_page(G) and url not in techo_site.records_page(G)
assert fetch(url)[0] == 404
assert media_review.waiting() == [], "確かめ終わった物は待ちに残らない"

# 間違った確認は通らず、何も残さない
other = new_record("別の記録")
assert techo_site.save_media(other, "image/jpeg", jpeg())[0] == "m1.jpg"
for bad in ((other, "m2.jpg", "object", "確認者"), (other, "m1.jpg", "maybe", "確認者"), (other, "m1.jpg", "object", " "), ("R-9999", "m1.jpg", "object", "確認者"), (other, "../m1.jpg", "object", "確認者")):
    assert media_review.record(*bad), bad
assert media_review.waiting() == [(other, "m1.jpg")]

# 読めない確認の記録は、出さない方へ倒す
review = techo_site.media_dir(other) / "review.json"
review.write_text("{", encoding="utf-8")
assert media_review.public(other, ["m1.jpg"]) == []
review.unlink()

# 動画: 取り込みで音を落とす（MP4 と MOV）。確認の後は物だけが出る。
vid = new_record("動画の記録")
name = techo_site.save_media(vid, "video/mp4", video())[0]
assert name == "m1.mp4" and streams((techo_site.media_dir(vid) / name).read_bytes()) == ["video"], "音が残った"
mov = techo_site.save_media(vid, "video/quicktime", video("mov"))[0]
assert mov == "m2.mov" and streams((techo_site.media_dir(vid) / mov).read_bytes()) == ["video"], "音が残った"
assert media_review.record(vid, name, "object", "確認者") == []
assert f"/record/{vid}/media/{name}" in gallery() and f"/record/{vid}/media/{mov}" not in gallery()

# 前から置いてある音つきの動画は、物だけと確かめた時に音を落とす（前の取り込みは音を残していた）
old = new_record("前の動画")
d = techo_site.media_dir(old)
d.mkdir(parents=True, exist_ok=True)
(d / "m1.mp4").write_bytes(video())
assert media_review.record(old, "m1.mp4", "object", "確認者") == []
assert streams((d / "m1.mp4").read_bytes()) == ["video"], "前の動画に音が残った"

# 人の確認: 端末で人が打たないと通らない（AI と自動の処理を止める。持ち寄りと同じ形）
waiting = new_record("確認待ち")
assert techo_site.save_media(waiting, "image/jpeg", jpeg())[0] == "m1.jpg"
cli = [sys.executable, "-m", "omochae.media_review"]
run = lambda *a: subprocess.run([*cli, *a], capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)  # noqa: E731
listed = run("list")
assert listed.returncode == 0 and waiting in listed.stdout and "m1.jpg" in listed.stdout, listed
refused = run("approve", waiting, "m1.jpg", "--shows", "object", "--reviewer", "Claude")
assert refused.returncode == 3 and "端末" in refused.stderr, refused
assert media_review.public(waiting, ["m1.jpg"]) == [], "端末で打たないと確認にならない"
assert run("approve", waiting, "m1.jpg", "--shows", "nope", "--reviewer", "x").returncode == 4, "呼び方の誤りは 4"
assert media_review.record(waiting, "m1.jpg", "object", "確認者") == []
assert run("revoke", waiting, "m1.jpg").returncode == 0 and media_review.public(waiting, ["m1.jpg"]) == []
assert run("revoke", "R-9999", "m1.jpg").returncode == 3

# 記録の取り下げで、確認の記録も一緒に消える
assert media_review.record(waiting, "m1.jpg", "object", "確認者") == []
gone, failures = records.withdraw(waiting)
assert not failures and not techo_site.media_dir(waiting).exists(), failures
assert waiting not in gallery()

# 順位の形を出さない（J-025）
# 頁の作りの字に順位や点を出さない（J-025）。人が話した字・書いた字の引用（感想と話された言葉の札 .voices-real と、職人の言葉の節）は
# 回答のまま出す決め（本人の決め 11-07「寄せられた声…回答のまま」・11-08 職人の言葉はレビュー 10 本の言葉）で、「パーツ点数」のような字があるので、外して見る
_g = gallery()
_g = re.sub(r'<div class="voices-real">.*?</details>', "", _g, flags=re.S)
_g = _g[:_g.index('id="shokunin"')] if 'id="shokunin"' in _g else _g
assert not re.search(r"順位|ランキング|人気|点数|\d+ 位|いいね", _g), re.search(r".{20}(順位|ランキング|人気|点数|\d+ 位|いいね).{10}", _g)
srv.shutdown()
print("ok")
