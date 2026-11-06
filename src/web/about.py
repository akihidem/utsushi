"""序の頁（/about）。本人の指示（11-05）でサイトを一気通貫に作り直す時、入口の前に「何をする所か」を置く（要件 docs/process/site-requirements.md の 7）。

判断の芯:
- 中身は本人の言葉の引用と、確かめた書誌の値だけで組み、作る側の言葉を最小にする。文は本人が採った文（11-05、#329）で、一字も変えない。本人の方針は小学生・中学生にも分かる言葉。
- 書誌は data/sources の御来迎の記録から読む（手で写さない。記録の値が直れば頁も直る）。
- 仕組みの答え・仮説の名前は書かない（序の頁は仕組みを語る所でないため）。成功・失敗・正解の言葉を使わない（philosophy.md）。
- 図は国立国会図書館の頁の写しを額に入れて 1 点だけ。新しい絵は作らない。
"""
import json

from omochae.hypotheses import ROOT

from . import skin
from .skin import esc

SID = "NDL-1187053-R0000005-L"
CONCEPT = "なくなったおもちゃの動きを、紙で実験してたしかめる道具"
# 本人の言葉（philosophy.md）。鉤括弧の中は届いた文のまま。
WORDS = ("科学の面白さを伝える。自然とのコールアンドレスポンス。おもちゃで遊び続ける。",
         "AI は鏡。江戸の絵を映すことはできるが、映すだけでは遊べない。")
# 「コールアンドレスポンス」は本人の言葉のまま引くので、下に言葉の説明を添える（本人が採った文）。
WORD_NOTE = "コールアンドレスポンスは、呼びかけると返事がくる、というやりとりのことです。"
# 数と作った人の印象を分けて書く（元は README の要約の文。U-16）。
WHY = ("日本の生徒は、ほかの国とくらべて、実験をとても多くしています。それでも、中学 2 年生で「理科を使う仕事につきたい」と答えた人は 27%です。"
       "調査に参加した国の平均は 58%で、その半分もありません（TIMSS 2023 という国際調査です）。"
       "作った人は、理科と探究の授業や進路の相談の中で、生徒が科学を自分の手の届く物と思っていないと感じてきました。")
# 玩具の定義（philosophy.md、本人が採った U-15 を、この頁の言葉にした文）。
DEFINITION = "ここで言うおもちゃは、手で動かしてたしかめられる形（トイ＝モデル）のことです。買ってもらう完成品でも、本物そっくりに作った物でもありません。"
LOOP = ("ここでは、おもちゃを選ぶと、すぐに紙の型紙を作れます。紙と糸で作って、動くかたしかめます。型紙は、正しい答えではありません。"
        "AI が「こうかな？」と考えた、ためしの案（仮説）です。まず紙が返事をします。動かなかった時の記録も、紙の返事の 1 つです。"
        "どう工夫したかを記録に書いてください。次の型紙をよくするヒントになります。自分の考えを書いた後で、AI（Claude）からも返事をもらえます。"
        "紙で動いても、昔の作り方が分かったことにはなりません。昔の物をそのまま作り直した物ではなく、ためしに作るための案です。")

STYLE = """
.about .hero{align-items:center}
.about .concept{font-size:clamp(18px,2vw,24px);letter-spacing:.2em;line-height:2;margin:14px 0 0}
.about blockquote{margin:12px 0;padding:0 0 0 16px;border-left:1px solid var(--frame);font-size:16px;line-height:2.1;letter-spacing:.06em}
.about .sec h2{margin-bottom:.4em}
"""


def _source():
    return json.loads((ROOT / "data/sources" / f"{SID}.json").read_text(encoding="utf-8"))


def book_paragraph(src):
    """『江都二色』の段落。値は出典の記録から（題・責任表示・原本の刊年・永続 ID・複製の出版者と年・権利）。"""
    who = esc(src.get("creator_as_cataloged", "").replace("||", "・"))
    when = esc((src.get("original_publication") or {}).get("value", ""))
    rights = "パブリック・ドメイン" if src.get("rights") == "PDM" else esc(src.get("rights", ""))
    copy = f'{esc(src.get("publisher", ""))}・{esc(src.get("publication", ""))} 年の複製'
    return (f'<p class="lead">江戸時代の絵本『{esc(src.get("title", ""))}』（{when}。{who}。国立国会図書館デジタルコレクション {esc(src.get("persistent_id", ""))}、'
            f'{copy}、{rights}）には、おもちゃの絵と歌だけが残っています。どう動いたかは、書かれていません。</p>')


def page(skin_name, path="/about"):
    from . import hokusai

    src = _source()
    quotes = "".join(f"<blockquote>「{esc(w)}」</blockquote>" for w in WORDS)
    body = (f'<div class="about"><section class="hero sec"><div>{skin.frame(SID, caption=src.get("holding", ""))}</div>'
            f'<div><h1>うつし</h1><p class="concept">{esc(CONCEPT)}</p>{book_paragraph(src)}<p class="lead">{esc(LOOP)}</p></div></section>'
            # 北斎漫画（本人の決定 11-05）。案 1 は白の展示の序の頁、案 3 は両方のサイトの序の頁。黒のジンの案 2 は入口の章の頭（looks.py）。
            + (hokusai.flip_section() if skin_name == "tenji" else "") + hokusai.mechanism_section() +
            f'<section class="sec"><h2>作った人の言葉</h2>{quotes}<p class="meta">{esc(WORD_NOTE)}</p></section>'
            f'<section class="sec"><h2>なぜ</h2><p class="lead">{esc(WHY)}</p><p class="lead">{esc(DEFINITION)}</p>'
            '<p class="meta">本の情報は、国立国会図書館の記録から取っています。</p></section>'
            '<section class="sec"><p class="links"><a class="btn" href="/toys">おもちゃを選ぶ</a><a class="btn quiet" href="/">入口へ戻る</a><a href="/otona">保護者の方へ、ファシリテーターの方へ</a></p></section></div>')
    return skin.shell("うつし · 序", body, skin_name, current="/about", path=path, extra_style=STYLE)
