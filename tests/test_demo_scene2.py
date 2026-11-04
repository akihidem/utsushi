"""デモ動画の場面 2（demo.scene2）の床: 出所の記録がそろい、1 コマが時刻だけで決まり、図が止まっている事を見る。

画像は取りに行かない（試験を網につながずに回すため）。見開きの代わりに、黒い四角を置いた紙で描く。
動き方を描かない決まり（F9）は機械で全部は見られない。ここでは (1) 寄り終えた後は図の領域の画素が
変わらない (2) 図の領域に朱（枠や矢印に使う色）が出ない、の 2 つだけを見る。
"""
from PIL import Image, ImageDraw

from demo import scene2
from demo.flip import H, SHU, W

rec, src = scene2.load_record()

# 出所: PDM と所蔵と改変の文が無ければ、動画の隅の札が書けない
for k in ("persistent_id", "iiif", "image_url", "rights", "rights_basis", "attribution", "holding",
          "modification_note", "what", "credit", "page_pct", "figure_pct"):
    assert rec.get(k), k
assert rec["rights"] == "PDM" and "国立国会図書館" in rec["attribution"]
assert rec["image_url"].startswith(rec["iiif"] + "/") and rec["iiif"].startswith("https://dl.ndl.go.jp/api/iiif/")
assert rec["persistent_id"] == src["persistent_id"] and rec["rights"] == src["rights"]
# 映るのは 1931 年の複製。札は元の年だけを書かず、複製の年と版元も書く
assert "1773" in rec["credit"] and "1931" in rec["credit"] and "米山堂" in rec["credit"], rec["credit"]
for pct in (rec["page_pct"], rec["figure_pct"]):
    x, y, w, h = pct
    assert 0 <= x and 0 <= y and w > 0 and h > 0 and x + w <= 100 and y + h <= 100, pct

# 歌は人が確かめ、退けられていない読みだけ
song = scene2.checked_song(src)
assert song and song["checked_by"] and not song.get("rejected_by")
assert scene2.checked_song({"transcription": {"status": "pending", "entries": [song]}}) is None
kami, shimo = scene2.song_lines(song["text"])
assert kami + shimo == song["text"].replace(" ", "") and kami and shimo

# 合図の表は時刻の順で、動画の長さの中
spans = list(scene2.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= scene2.DURATION
assert scene2.Scene2.duration == scene2.DURATION
assert scene2.CUES["song"][1] <= scene2.SONG_OUT[0] and scene2.SONG_OUT[1] <= scene2.CUES["closing"][0]

# 偽の見開き: 図の枠の中に黒い四角（玩具の代わり）、頁の上に細い線（歌の字の代わり）
spread = Image.new("L", (2400, 1992), 255)
d = ImageDraw.Draw(spread)
px, py, px1, py1 = scene2.pct_box(spread.size, rec["page_pct"])
fx, fy, fx1, fy1 = scene2.pct_box((px1 - px, py1 - py), rec["figure_pct"])
d.rectangle((px + fx + 80, py + fy + 80, px + fx1 - 80, py + fy1 - 80), fill=0)
d.line((px + 200, py + 200, px + 200, py + 600), fill=0, width=8)
scene = scene2.Scene2(spread, rec, src)
for t in (0.5, 4.0, 9.0, 15.5, 19.9):
    a, b = scene.frame(t), scene.frame(t)
    assert a.size == (W, H) and a.tobytes() == b.tobytes(), t

# 寄っている間は絵が変わる（寄りが効いている）
assert scene.frame(4.0).tobytes() != scene.frame(6.0).tobytes()
# 寄り終えた後、締めまでは図の領域が 1 画素も変わらない（部品を動かしていない）
region = (0, 0, scene2.FIG_RIGHT, H - 100)
h0, h1 = scene2.HOLD
early, late = scene.frame(h0 + 0.2).crop(region), scene.frame(h1 - 0.1).crop(region)
assert early.tobytes() == late.tobytes(), "止まっている間に図の領域が変わった"
# 図の上で玩具が描かれ、その領域に朱（矢印や枠に使う色）が無い
assert early.convert("L").getextrema()[0] < 80, "図が描かれていない"
for t in (h0 + 0.2, 12.0, h1 - 0.1):
    px_ = scene.frame(t).crop(region).getcolors(W * H)
    assert not any(abs(c[0] - SHU[0]) + abs(c[1] - SHU[1]) + abs(c[2] - SHU[2]) < 40 for _, c in px_), t
print("ok")
