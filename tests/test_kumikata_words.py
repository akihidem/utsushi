"""聞く口・手帖・作りながら見る頁の字を、組み方の呼び名にそろえる試験（文章のプリント廃止の設計の PR 3）。

なぜ: 本人の決まり（11-06）「文章のプリントは廃止。組み立て用のページだけでいい。」で、手順の紙は刷る口から外れる。
聞く口や頁の字が「手順の紙の絵を見てください」のままだと、刷らない紙を見に行かせる。呼び名は 1 つにそろえる
（手順ごとの文と絵の節は「組み方」、その絵は「組み方の絵」。「組み立て」の語は 3D の方だけ）。字は本人の確認済み（11-06）。
ここで見るのは、設計メモの字の表のうち、聞く口・play_server・手帖・作りながら見る頁の行だけ（組み立ての頁と刷る口の字は別の PR）。"""
import os
import pathlib
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api import ask  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def src(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


# 1. 聞く口（鍵が無い時）と、Claude へ渡す頼みの文
assert ask.NO_KEY == "AI の答えは、この場では使えません。型紙の凡例と、組み方の絵を見てください。", ask.NO_KEY
assert "分からない時は「組み方の絵を見てください」と言います。" in ask.SYSTEM and "手順の紙" not in ask.SYSTEM, ask.SYSTEM
# 語の表の蛇腹（蛇腹・ジャバラの 2 つ）は、組み方の絵の「蛇腹（横から）」を指す。ほかの語の答えに手順の紙は出ない
for word in ("蛇腹", "ジャバラ"):
    assert "組み方の絵の「蛇腹（横から）」で、" in ask.GLOSSARY[word], (word, ask.GLOSSARY[word])
for word, answer in ask.GLOSSARY.items():
    assert "手順の紙" not in answer, word

# 2. 聞く口（画面の道、play_server）: 鍵が無い時の字
server = src("src/web/play_server.py")
assert '"今は AI に聞けません。型紙の凡例と、組み方の絵を見てください"' in server
assert "型紙の凡例と手順の紙の絵を見てください" not in server

# 3. 手帖: 答えが空の時の字
techo = src("src/web/techo_page.html")
assert '"組み方の絵を見てください。"' in techo and "手順の紙の絵を見てください" not in techo

# 4. 作りながら見る頁: 手順の文が無い時の案内と、絵の alt
tsukuru = src("src/web/tsukuru.py")
assert "組み方の絵を見て、番号の順に進めます。" in tsukuru and "手順の紙の絵を見て、番号の順に進めます。" not in tsukuru
assert 'alt="組み方の絵（{esc(_label(h))} の紙・版 {v}）"' in tsukuru and 'alt="手順の紙（' not in tsukuru
print("ok")
