"""序の頁の試験。本人の言葉と書誌の値が出て、仮説の名前と成績の言葉が出ない事、2 つの皮で変数が違う事を見る。"""
import html
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae.marks import without_premise  # noqa: E402
from web import about  # noqa: E402

pages = {k: about.page(k) for k in ("tenji", "zine")}
for k, h in pages.items():
    for w in ("『江都二色』", "1773", "北尾重政", "AI は鏡", "info:ndljp/pid/1187053", "TIMSS 2023", 'href="/"'):
        assert w in h, (k, w)
    assert 'href="/toys"' not in h, (k, "/toys へ向く道は置かない" + '（本人のサイト体験レビュー 11-07 の 3「同じ物が何回も出る」。/toys は入口へ送るので、/toys へ向く道は置かない）')
    # 本人が採った文（11-05、#329）。一字でも変わったら落ちるように、ここに決定の文を書く
    for w in ("なくなったおもちゃの動きを、紙で実験してたしかめる道具",
              "江戸時代の絵本『江都二色』",
              "には、おもちゃの絵と歌だけが残っています。どう動いたかは、書かれていません。",
              "ここでは、おもちゃを選ぶと、すぐに紙の型紙を作れます。紙と糸で作って、動くかたしかめます。型紙は、正しい答えではありません。AI が「こうかな？」と考えた、ためしの案（仮説）です。まず紙が返事をします。動かなかった時の記録も、紙の返事の 1 つです。どう工夫したかを記録に書いてください。次の型紙をよくするヒントになります。自分の考えを書いた後で、AI（Claude）からも返事をもらえます。紙で動いても、昔の作り方が分かったことにはなりません。昔の物をそのまま作り直した物ではなく、ためしに作るための案です。",
              "<h2>作った人の言葉</h2>",
              "コールアンドレスポンスは、呼びかけると返事がくる、というやりとりのことです。",
              "日本の生徒は、ほかの国とくらべて、実験をとても多くしています。それでも、中学 2 年生で「理科を使う仕事につきたい」と答えた人は 27%です。調査に参加した国の平均は 58%で、その半分もありません（TIMSS 2023 という国際調査です）。作った人は、理科と探究の授業や進路の相談の中で、生徒が科学を自分の手の届く物と思っていないと感じてきました。",
              "ここで言うおもちゃは、手で動かしてたしかめられる形（トイ＝モデル）のことです。買ってもらう完成品でも、本物そっくりに作った物でもありません。",
              "本の情報は、国立国会図書館の記録から取っています。"):
        assert html.escape(w, quote=False) in h or w in h, (k, w)
    assert "採否待ち" not in h and "本人" not in h, k
    # 仕組みの答えと仮説の名前を書かない。成績の言葉を使わない
    for w in ("成功", "失敗", "正解", "仮説 A", "H-A", "つまみ", "内筒"):
        assert w not in without_premise(h), (k, w)
    assert "IntersectionObserver" not in h and "<blockquote>" in h, k
# 末尾は入口へ戻る釦の 1 つ（前は「おもちゃを選ぶ」と 2 つで、同じ所へ行く対だった（本人のサイト体験レビュー 11-07 の 3「同じ物が何回も出る」。/toys は入口へ送るので、/toys へ向く道は置かない））。釦の形にする: 字のリンクを並べると、
# 並びの高さに伸びて縦長の押す所になり、下線が字から離れる（#141）
for k, h in pages.items():
    assert '<p class="links"><a class="btn" href="/">入口へ戻る</a><a href="/otona">' in h and "おもちゃを選ぶ</a>" not in h, k
roots = [re.search(r":root\{([^}]*)\}", h).group(1) for h in pages.values()]
assert roots[0] != roots[1] and "--bg:#fcfcfa" in roots[0] and "--bg:#0b0a09" in roots[1]
print("ok")
