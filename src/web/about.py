"""序の頁（/about）。本人の指示（11-05）でサイトを一気通貫に作り直す時、入口の前に「何をする所か」を置く（要件 docs/process/site-requirements.md の 7）。

判断の芯:
- 中身は本人の言葉の引用と、確かめた書誌の値だけで組み、作る側の言葉を最小にする。文は本人が採った文（11-05、#329）で、一字も変えない。本人の方針は小学生・中学生にも分かる言葉。
- 書誌は data/sources の御来迎の記録から読む（手で写さない。記録の値が直れば頁も直る）。
- 仕組みの答え・仮説の名前は書かない（序の頁は仕組みを語る所でないため）。成功・失敗・正解の言葉を使わない（philosophy.md）。
- 図は国立国会図書館の頁の写しを額に入れて 1 点だけ。新しい絵は作らない。
- 足には、寄せられた声と職人の言葉の 2 つの節（持ち寄りの入口のフォームを含む）を置く（techo_site.voices_sections）。上の「本人の言葉の引用と書誌の値だけ」は
  序の本文の決まりで、足の 2 つの節は前のギャラリーの節を字を変えずに移した物（本人のサイト体験レビュー 11-07 の言葉 6、直しの設計の D）。
- もう 1 つの例外は「うつしと paper to toy」の節（engine_section）。本人の言葉（11-07）から作る側が書いた字と、型紙エンジンの材料の字で、
  本人の確かめを通してから載せる（引用でも書誌の値でもないので、上の決まりの外）。
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

# うつしの位置づけと、型紙エンジン paper to toy の一つの具体例である事と、エンジンの仕組み（本人の言葉 11-07「このサービスは学校の理科教育や研究活動や
# 博物館などの教育分野で使われることを想定して始めたけど、公開してみんなが使えるようなサービスになるといいなと思ってきた。paper to toy の一つの具体例で
# あるとか、エンジンの仕組みとかはデモとサイトで説明した方がいい」→ 窓口: 概要・サイト・デモの説明に反映する）。
# 字はどれも案で、窓口と本人の確かめ待ち。具体例の 1 文・仕組みの 5 文・段の図は、型紙エンジンの README と版の台帳から作った材料の字
# （統括 11-07。材料の「雛形」は、材料の側で内輪の言葉の見張りに合わせて言い換えた版の字）。見出しだけは、利用者の頁に作る側の言葉
# （「型紙エンジン」。tests/test_reader_words.py の内輪の言葉）を出さない決まりで「うつしと paper to toy」にした。材料の頭の「（utsushi・提出物）」と
# 出所の注・「書かなかった事」は頁に出さない（統括 11-07）。
# 位置づけは本人の言葉を、この頁の言葉にした文（本人の直し 11-07 で、作った物そのものがみんなが使えるサービスという言い方）。
# README も同じ字を使う（頭の後の最初の節。違うのは 2 つだけ: 位置づけの文は README の言葉で別に書く・README の中は「AI」を「Claude」と書く本人の決定 11-06。
# tests/test_about_engine.py が、README と食い違わない事を見る）
ENGINE_HEAD = "うつしと paper to toy"
# 位置づけは本人の直し（11-07）「これからというよりは、みんなが使えるサービスとして作った」による。前の案の「今は、公開して、みんなが使える
# サービスにしたいと考えています」（これからの思いの言い方）を、作った物そのものがみんなが使えるサービス、という言い方にした
# 3 文目は本人の構成の押さえ（11-07「誰でも体験して欲しいことではある」— 核の見方は作った人だけの物、体験そのものはみんなの物）による
# 窓口の決め（11-07 案 2）。本人が直した前の 2 文は替えずに足した。見方が何か（江戸のおもちゃと科学の実験をつなげて見る事）は、
# 作った人の言葉の節の思いの核の後で名指す（同じ頁の別の節。ここで言うと 2 か所になる）
POSITION = ("うつしは、みんなが使えるサービスとして作りました。"
            "学校の理科の授業や研究、博物館など、教育の場で使う事を考えて始めた物です。"
            "もとにある見方は作った人だけの物ですが、紙で作って確かめる体験そのものは、だれにでもしてほしい事です。")
EXAMPLE = ("うつしは、paper to toy のエンジンで江戸の玩具を紙で作って試す、一つの具体例です"
           "（江戸の玩具は最初の題材で、エンジンの部品の出し方・検査・3D の確かめ・改善の輪は題材を選びません）。")
ENGINE_STEPS = (
    "おもちゃの大きさ（寸法）を入れると、エンジンが、紙で作るための型紙（切って、折って、貼る紙の図）を出します。",
    "エンジンは「部品を並べる → 刷る前に確かめる（はみ出し・重なり・ちゃんと動くかの計算）→ 刷る → 刷った紙を読み直して確かめる」の順に進みます。",
    # 3 文目の「（ぶつかりそうな所は…）」は窓口の決め（11-07）で足した。エンジンの 3D 検品は、扇が開く途中の近い板どうしを落ちにせず、
    # 所見として書き残す作りなので、「確かめます」だけでは言い切りが強かった（別の目の確かめの気づき）
    "御来迎と首振り虎の型紙は、コンピューターの中の 3D で折って組み立て、紙どうしがぶつからないか、色のある面が外を向くかを、エンジンが自分で確かめます（ぶつかりそうな所は、人が見るために書き残します）。"
    "組み立ての様子は、段ごとの絵と短い動画にもします。",
    "型紙は正解ではなく、AI が考えた仮説です。作って、動きを確かめて、直していきます。",
    "作った人の報告やワークショップの感想から直しの案が生まれ、人が選んだ案で直すと、型紙の版とエンジンの版が上がります。",
)
FLOWS_HEAD = "エンジンの流れ（段の図）"
FLOWS = (
    ("本の流れ（型紙）", ("入力（玩具の寸法・出典）", "玩具ごとの作り方の決まり（作る側の計算）が部品を出す", "配置", "描く前の検査（寸法の範囲・印字域・重なり・玩具ごとの動きの計算）",
                    "描く（SVG・PDF）", "刷った後の検査（出典と仮説の字を読み直す・貼った画像 0 枚）", "型紙（PDF・PNG）")),
    ("3D の流れ（御来迎と首振り虎）", ("型紙の部品", "3D で折る（折り線ごとの硬い面）", "組み立てる（手順の文と 1 対 1 の段）",
                              "3D 組み立て検品（当たり・はみ出し・色の面の向き）", "作り方の 3D（JSON。サイトの組み立ての頁が描く）と、検品の記録（段ごとの絵・短い動画）")),
    ("改善の輪（版が上がる所）", ("作った人の報告・ワークショップの感想・作る前のレビュー", "束ねる（名前・連絡先は入れない）", "直しの案（機械が起こす）",
                         "人が採る・採らない", "直しが入る", "版を刻む（型紙の版・エンジンの版）", "次の型紙")),
)
# 図の言葉の言い分け（決める側の決定 2026-11-07「型紙の版」と「エンジンの版」を言い分ける）。番号は頁に書かない（版が上がるたびに古くなるため）
FLOW_NOTE = "「型紙の版」は玩具ごとの型紙の組の番号で、紙の題にも刷ります。「エンジンの版」は、型紙を作るエンジンの台帳の番号です。"


def engine_section():
    """うつしと paper to toy の節（序の頁の「なぜ」の後、版の歩みの表の前。表の担当と置き場を合わせた 11-07）。
    段の図は長いので畳む（序の頁は読み物の頁だが、図の 3 本を開いたまま並べると、読む順が埋もれるため）。"""
    steps = "".join(f"<li>{esc(t)}</li>" for t in ENGINE_STEPS)
    flows = "".join(f'<p class="meta">{esc(name)}</p><ol class="flow">' + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ol>"
                    for name, items in FLOWS)
    return (f'<section class="sec" id="engine"><h2>{esc(ENGINE_HEAD)}</h2>'
            f'<p class="lead">{esc(POSITION)}</p><p class="lead">{esc(EXAMPLE)}</p>'
            f'<ol class="engine-steps">{steps}</ol>'
            f'<details class="flows"><summary>{esc(FLOWS_HEAD)}</summary>{flows}<p class="meta">{esc(FLOW_NOTE)}</p></details></section>')


# よむ の頁（段 1）: 狭い幅（1 列に積む）では、題と読み物への道（図鑑・保護者の方へ…・English）を額の絵より先に置く（order:-1）。
# 前は額の絵（約 630px）の後で、幅 390 で道が 882px からと、最初の画面に入らなかった（別の目の確かめ 11-06）。広い幅は 2 列（額 | 題）のまま。
# 注は CSS の中に書かない（頁の字に混ざるため）
STYLE = """
.about .hero{align-items:center}
@media (max-width:820px){.about .hero>div:last-child{order:-1}}
.about .concept{font-size:clamp(18px,2vw,24px);letter-spacing:.2em;line-height:2;margin:14px 0 0}
.about blockquote{margin:12px 0;padding:0 0 0 16px;border-left:1px solid var(--frame);font-size:16px;line-height:2.1;letter-spacing:.06em}
.about .sec h2{margin-bottom:.4em}
.about .engine-steps{margin:10px 0 0;padding-left:1.4em;line-height:2}
.about .flows{margin:12px 0 0}.about .flows summary{cursor:pointer;min-height:44px;display:flex;align-items:center}
.about .flow{margin:4px 0 12px;padding-left:1.4em;line-height:1.9}
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
    from . import hokusai, techo_site, toys  # techo_site は寄せられた声と職人の言葉の節（循環を避けて、ここで読む）

    src = _source()
    quotes = "".join(f"<blockquote>「{esc(w)}」</blockquote>" for w in WORDS)
    body = (f'<div class="about"><section class="hero sec"><div>{skin.frame(SID, caption=src.get("holding", ""))}</div>'
            # 道の外の読み物の入口（段 1、帯の「よむ」はこの頁）。前は頭の帯にあった 図鑑・English と、保護者の方へ、ファシリテーターの方へ の頁を、今の名前のまま並べる
            f'<div><h1>うつし</h1><p class="links yomu"><a href="/zukan">図鑑</a><a href="/otona">保護者の方へ、ファシリテーターの方へ</a><a href="/en">English</a></p>'
            f'<p class="concept">{esc(CONCEPT)}</p>{book_paragraph(src)}<p class="lead">{esc(LOOP)}</p></div></section>'
            # 北斎漫画（本人の決定 11-05）。案 1 は白の展示の序の頁、案 3 は両方のサイトの序の頁。黒のジンの案 2 は入口の章の頭（looks.py）。
            # 白の案 2（縦読み）は、入口でなく帯の「よむ」の先のこの頁に置く（統括の決め 11-06。地図の「読み物は道の外へ」）
            + (hokusai.flip_section() + hokusai.scroll_section("tenji") if skin_name == "tenji" else "") + hokusai.mechanism_section() +
            f'<section class="sec"><h2>作った人の言葉</h2>{quotes}<p class="meta">{esc(WORD_NOTE)}</p></section>'
            f'<section class="sec"><h2>なぜ</h2><p class="lead">{esc(WHY)}</p><p class="lead">{esc(DEFINITION)}</p>'
            '<p class="meta">本の情報は、国立国会図書館の記録から取っています。</p></section>'
            # うつしと paper to toy の節（本人の言葉 11-07。この後に、版の歩みの表の節が 1 行で続く置き場。表の担当と合わせた）
            + engine_section()
            # えらぶ の頭にあった断りの段（窓口の決定 11-07 の ②「よむ へ移す」）。字は変えずに、おもちゃを選ぶ釦のすぐ前に置く
            + toys.yomu_section() +
            # 寄せられた声と職人の言葉（持ち寄りの入口のフォームを含む）。前はギャラリーにあったが、のこす（作った記録を残す）と分けるためにここへ移した
            # （本人のサイト体験レビュー 11-07 の言葉 6、直しの設計の D。techo_site.voices_sections）
            f'<section class="sec">{techo_site.voices_sections()}</section>'
            '<section class="sec"><p class="links"><a class="btn" href="/toys">おもちゃを選ぶ</a><a class="btn quiet" href="/">入口へ戻る</a><a href="/otona">保護者の方へ、ファシリテーターの方へ</a></p></section></div>')
    return skin.shell("うつし · 序", body, skin_name, current="/about", path=path, extra_style=STYLE + techo_site.VOICES_STYLE)
