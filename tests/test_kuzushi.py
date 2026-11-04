"""くずし字を読む頁の試験（f14、research/25）。予想が先・書いた読みを残さない・採らなかった読みを出さない・
採点の言葉を出さない・文にはどれも印がある、を見る。

本物の記録を汚さないよう、OMOCHAE_DATA を空の一時の置き場にしてから読み込む。書いた読みが残らない事は、
この置き場が空のままかで確かめる。
"""
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_DATA"] = str(DATA)

from omochae import labels  # noqa: E402
from web import kuzushi  # noqa: E402
from web.play_server import serve, source, sources  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
server = serve(0)
port = server.server_address[1]
base = f"http://127.0.0.1:{port}"
threading.Thread(target=server.serve_forever, daemon=True).start()


def get(path):
    try:
        r = urllib.request.urlopen(base + path)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def post(path, fields, origin=True):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if origin:
        headers["Origin"] = f"http://127.0.0.1:{port}"
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(fields).encode(), headers=headers, method="POST")
    try:
        r = urllib.request.urlopen(req)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def checked(sid):
    return [e for e in source(sid)["transcription"]["entries"] if e.get("checked_by") and not e.get("rejected_by")]


def rejected(sid):
    return [e for e in source(sid)["transcription"]["entries"] if e.get("rejected_by")]


# 採点・順位の言葉。違って読めた所に印を付けるだけで、合否を言わない（J-025、philosophy.md）
SCORE_WORDS = ("正解", "不正解", "成功", "失敗", "順位", "点数", "間違", "正しい", "合っ", "○", "×")


def no_score_words(body, where):
    for w in SCORE_WORDS:
        assert w not in body, (where, w)


def all_labeled(body, where):
    """画面に出た文（li）は、どれも 3 つの印のどれかで始まる。"""
    items = re.findall(r"<li>(.*?)</li>", body, re.S)
    assert items, where
    for it in items:
        m = re.match(r'<span class="lb">(.*?)</span>', it)
        assert m and m.group(1) in labels.LABELS, (where, it)


def files_under(p):
    return sorted(x for x in p.rglob("*") if x.is_file())


# 図鑑の玩具の頁から入れる
for sid in sources():
    assert f'href="/zukan/{sid}/yomi"' in get(f"/zukan/{sid}")[1], sid

# 書く前: 頁は開き、歌の所の絵と書く欄がある。確かめた読みはまだ出さない（予想が先）
for sid in sources():
    code, body = get(f"/zukan/{sid}/yomi")
    assert code == 200, sid
    # 原図の写しは git の外（out/sources）なので、まっさらな clone では絵の代わりに「手元に絵がありません」が出る
    has_pic = (pathlib.Path(__file__).resolve().parents[1] / "out/sources" / f"{sid}.jpg").exists()
    assert (f'src="/picture/{sid}"' in body if has_pic else "手元に絵がありません" in body) and 'name="mine"' in body, sid
    for e in checked(sid):
        assert e["text"] not in body, (sid, "書く前に確かめた読みが出ている")
    for e in rejected(sid):
        assert e["text"] not in body, sid
    assert "怠らし" not in body
    no_score_words(body, sid)
assert get("/zukan/NDL-0-R0000001-L/yomi")[0] == 404

# 書いた後: 書いた読みと、印付きの確かめた読みが並ぶ。採らなかった読みはどこにも出ない
before = files_under(DATA)
mine = "御来迎 おかむにつけて □らじ 朝な夕なに なむあめの鳥"
code, body = post(f"/zukan/{G}/yomi", {"mine": mine})
assert code == 200, body[:300]
assert "御来迎" in body and "おかむにつけて" in body  # 書いた読みが映る（空白は比べる時に外すので、字の並びで見る）
for e in checked(G):
    plain = "".join(e["text"].split())
    shown = re.sub(r"<[^>]+>", "", body)
    assert plain in shown, "確かめた読みが出ていない"
assert "人が確かめた読み" in body and f'<span class="lb">{labels.QUOTE}</span>' in body
assert "ここが違って読めた" in body and '<mark class="d">' in body
assert "怠らじ" in body, "活字の読みが出ていない"
assert "怠らし" not in body
for e in rejected(G):
    assert e["text"] not in body and "".join(e["text"].split()) not in re.sub(r"<[^>]+>", "", body)
no_score_words(body, "post")
all_labeled(body, "post")
# 書いた読みは残さない: 記録の置き場に何も増えない
assert files_under(DATA) == before == [], files_under(DATA)

# 虎: 採らなかった読みの字の並びを出さず、割れた事は誰が決めたかで書く
code, body = post(f"/zukan/{T}/yomi", {"mine": "雲おこす龍はあたりにいぬけれと張子のとらの風にうそふく"})
assert code == 200
shown = re.sub(r"<[^>]+>", "", body)
for e in rejected(T):
    assert "".join(e["text"].split()) not in shown and "おとす" not in shown
assert "同じ字の並び" in body and '<mark class="d">' not in body
no_score_words(body, "tiger")
all_labeled(body, "tiger")

# 書いた読みが「怠らし」でも、それは書いた人の読みとして映すだけ（頁がそれを答えとして出すのではない）
code, body = post(f"/zukan/{G}/yomi", {"mine": "<b>怠らし</b>"})
assert code == 200 and "<b>怠らし</b>" not in body and "&lt;b&gt;" in body  # そのまま HTML にしない

# 空の読みは並べない。別のサイトからの送信は受けない
assert post(f"/zukan/{G}/yomi", {"mine": "  "})[0] == 422
assert post(f"/zukan/{G}/yomi", {"mine": "あ"}, origin=False)[0] == 403
assert files_under(DATA) == []

# 違って読めた字の印: 数や割合を返さず、違った所に印だけ付ける
a, b, d = kuzushi.diff_marks("あいう", "あえう")
assert d and a == 'あ<mark class="d">い</mark>う' and b == 'あ<mark class="d">え</mark>う'
assert kuzushi.diff_marks("あ い", "あい")[2] is False

# 歌の枠は頁の中に収まり、NDL の切り出しの検査も通る
for sid, (x, y, w, h) in kuzushi.SONG_BOX.items():
    assert 0 <= x and x + w <= 100 and 0 <= y and y + h <= 100, sid
    assert kuzushi.zoom_link(source(sid), sid).startswith("https://dl.ndl.go.jp/api/iiif/"), sid
assert set(kuzushi.SONG_BOX) == set(sources())

server.shutdown()
print("ok")
