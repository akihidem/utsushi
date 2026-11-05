"""序の頁（/about）。本人の指示（11-05）でサイトを一気通貫に作り直す時、入口の前に「何をする所か」を置く（要件 docs/process/site-requirements.md の 7）。

判断の芯:
- 中身は本人の言葉の引用と、確かめた書誌の値だけで組み、作る側の言葉を最小にする。文面の採否は本人（窓口のカード）。採るまでは「採否待ち」の一行を添える。
- 書誌は data/sources の御来迎の記録から読む（手で写さない。記録の値が直れば頁も直る）。
- 仕組みの答え・仮説の名前は書かない（予想が先、F9.prediction）。成功・失敗・正解の言葉を使わない（philosophy.md）。
- 図は国立国会図書館の頁の写しを額に入れて 1 点だけ。新しい絵は作らない。
"""
import json

from omochae.hypotheses import ROOT

from . import skin
from .skin import esc

SID = "NDL-1187053-R0000005-L"
CONCEPT = "失われた玩具の動きを、紙で実験して確かめる道具"
# 本人の言葉（philosophy.md）。鉤括弧の中は届いた文のまま。
WORDS = ("科学の面白さを伝える。自然とのコールアンドレスポンス。おもちゃで遊び続ける。",
         "AI は鏡。江戸の絵を映すことはできるが、映すだけでは遊べない。")
# README の 30 秒の要約の文（U-16 で本人が採った言い方）。数と本人の印象を分けて書く。
WHY = ("日本の生徒は実験を国際的にとても多くしている。それでも中学 2 年で「理科を使う職業につきたい」は 27%で、国際平均 58%の半分に満たない（TIMSS 2023）。"
       "本人は理科と探究の授業、進路指導の場で、生徒が科学を自分の手の届く物と思っていないと感じてきた。")
# 玩具の定義（philosophy.md、本人が採った U-15）。
DEFINITION = "玩具とは、手で動かして確かめられる型（トイ＝モデル）です。買ってもらう完成品でも、精巧なレプリカでもありません。"
LOOP = ("ここでは、図を見て先に予想を書き、仮説ごとの紙の型紙を刷り、紙と糸で作って確かめます。まず紙が返事をします。"
        "動かなかった記録も、そのまま紙の返事です。自分の説明を書いた後で、AI からも返事をもらえます。"
        "紙で動いても、昔の作り方の証明にはなりません。復元ではなく、試すための翻案です。")

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
    return (f'<p class="lead">江戸の絵本『{esc(src.get("title", ""))}』（{when}。{who}。国立国会図書館デジタルコレクション {esc(src.get("persistent_id", ""))}、'
            f'{copy}、{rights}）には、玩具の図と歌だけが残っています。どう動いたかは、書かれていません。</p>')


def page(skin_name, path="/about"):
    src = _source()
    quotes = "".join(f"<blockquote>「{esc(w)}」</blockquote>" for w in WORDS)
    body = (f'<div class="about"><section class="hero sec"><div>{skin.frame(SID, caption=src.get("holding", ""))}</div>'
            f'<div><h1>うつし</h1><p class="concept">{esc(CONCEPT)}</p>{book_paragraph(src)}<p class="lead">{esc(LOOP)}</p></div></section>'
            f'<section class="sec"><h2>本人の言葉</h2>{quotes}</section>'
            f'<section class="sec"><h2>なぜ</h2><p class="lead">{esc(WHY)}</p><p class="lead">{esc(DEFINITION)}</p>'
            '<p class="meta">文面は本人の採否待ち。本人の言葉の引用と、国立国会図書館の書誌の値だけで組んでいます。</p></section>'
            '<section class="sec"><p class="links"><a class="btn" href="/toys">おもちゃを選ぶ</a><a href="/loop">改善の輪</a><a href="/">入口</a></p></section></div>')
    return skin.shell("うつし · 序", body, skin_name, current="/about", path=path, extra_style=STYLE)
