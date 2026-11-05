"""英語の頁（J-030 の段 1）。本人の言葉（2026-11-05）「いろんな国の人に知って欲しい」「実装までやって」。

判断の芯:
- 頁を丸ごと 2 言語にしない。入口（/en）と玩具の頁（/en/toy/<id>）だけを足す。全部訳すと質が揃わず、断りの文を落とす危険が大きい（J-030 の比べた案）。
- 紙は日本語のまま。凍結の床（必須 2 種の今の版の紙）を変えないので、刷る口は同じ物を使い、紙が日本語である事を断る。
- 開いたらすぐ作れる形は日本語の頁と同じ（本人の決定 11-05、#242）。予想の段は置かない。
- 型紙は正解でなく AI が考えた仮説である事と、紙で動いても昔の作り方の証明にならない事を、短くする時にも落とさない（J-030 の方針 3）。
- 聞く口と記録の口は置かない。聞く口は日本語の語の表で動き、英語の問いは「仕組みには答えない」の門を素通りする。
  記録と写真は国ごとの決まりの同意の形を決めてから（J-030 の方針 7・段 3）。
- 札の文と紹介の頭は本人が採った（11-05、#318）。英語を母語とする人に読んでもらうまで draft の印を付ける。玩具の名前は図の見立てで、確かめていない。
"""
import json

from omochae import hypotheses, ways
from omochae.compose import TEMPLATES
from omochae.hypotheses import ROOT

from . import skin
from .play_server import esc, sources

DRAFT = "Draft translation. A native speaker has not checked it yet."
# J-030 の少し長い紹介と同じ文。文を変える時は J-030 も直す。本人の方針（11-05）の書き方: 短い文・やさしい語（#318）。
INTRO = (
    "In 1773, the artist Kitao Shigemasa made a book of toys in Edo, which is now Tokyo. The book is called <i>Edo nishiki</i>. It shows more than 80 toys with short poems, but it does not say how the toys worked.",
    "With utsushi, you can test ideas with your hands. Pick a toy and print a paper template right away. Each idea has its own template, and none of them is the answer. Cut, fold, glue, and try it. If it does not move, that is a result too. Write down what happened, change one thing, and print the next version.",
    "Two toys have full templates, in Japanese only. One is the Goraigo (roughly, \"welcoming descent\"), a tube with a fan. The other is a tiger based on old papier-mâché toys. An earlier Goraigo moved in one trial with adults. No one has finished the tiger yet. The other toys are untested drafts, and their names are our guesses.",
    "A paper model that moves does not prove how the original was made. These models are for trying things out. They are not exact copies of the old toys.",
)
# 本人が採った文（11-05、#318）。一字も変えない。
PREMISE = "This template is not the answer. It is a guess made by an AI. Some parts may not work. Tell us how you fixed them. That helps us make the next version better."
JA_ONLY = "The templates print in Japanese only. Part numbers, line styles, and the steps here are what you need to follow them."
CREDIT = "Pictures: 1931 facsimile of the 1773 book, National Diet Library, Japan (public domain). The drawings on the templates are redrawn."
FOOT = f'<p class="foot">{CREDIT} A paper model that moves does not prove how the original was made.</p>'
GLOSSARY = (
    ("Solid line", "Cut here."),
    ("Valley fold", "Fold toward you, so the crease sinks like a valley."),
    ("Mountain fold", "Fold away from you, so the crease stands up like a ridge."),
    ("Glue tab", "A small flap that gets glue and hides inside."),
    ("10 cm scale", "A line printed on the sheet. Put a ruler on it before you cut. If it does not measure 10 cm, the parts will not fit."),
    ("Print at 100%", "Use A4 paper if you can. On US Letter the edges may be cut off, and \"fit to page\" shrinks it to about 94%, so the scale will not match. We have not tried printing on Letter."),
    ("Materials", "Card stock about 150 g/m². A bamboo skewer can be any thin stick, kite string any thin string, and modeling clay any small weight."),
)
# 作り方の印の英語。判定は日本語の札と同じ omochae.ways（#261）。上下を付けない。
WAY_EN = {"紙一枚": "One sheet", "折るだけ": "Fold only", "当時の材料": "Edo materials"}
WAYS_NOTE = "One sheet, Fold only, and Edo materials show different ways to make a toy. No mark is better than another."


def _load(name):
    return json.loads((ROOT / "data/en" / name).read_text(encoding="utf-8"))


def toy_text(sid):
    return _load("toys.json")["toys"].get(sid, {"name": "Untitled toy", "intro": ""})


def steps_for(sid, h, data=None):
    """手順の英語。原文の文を鍵に引く。無ければ紙の番号へ案内する（勝手に作らない）。"""
    data = data or hypotheses.load(sid)
    tpl = TEMPLATES[h.get("template") or data.get("template", "slider_fan")]
    table = _load("required.json")["steps"]
    return [table.get(s, f"See step {i} on the sheet.") for i, s in enumerate(tpl.steps({**tpl.DEFAULTS, **h["params"]}), 1)]


def _picture(sid):
    """日本語の頁と同じ額（玩具の所へ寄せる位置を共有する）。読み上げの札だけ英語にする。"""
    return skin.frame(sid).replace('aria-label="図"', 'aria-label="Picture from the book"')


def _marks(data, h):
    """作り方の印を英語で。中身は日本語の札と同じ関数から取る（食い違わせない）。寸法の無い仮説には印を出さない（日本語の札と同じ）。"""
    names = ways.labels(ways.of_hypothesis(data, h)) if h.get("params") is not None else []
    tags = "".join('<span class="lb">' + esc(WAY_EN[n]) + "</span>" for n in names)
    return f'<p class="ways">{tags}</p>' if tags else ""


def index_page(look=skin.DEFAULT, path="/en"):
    cards = ""
    for sid in sources():
        t = toy_text(sid)
        tag = "" if hypotheses.stage(sid) == "必須" else '<span class="lb">Untested draft</span>'
        cards += (f'<article class="card"><a href="/en/toy/{esc(sid)}">{_picture(sid)}<h3>{esc(t["name"])}</h3></a>{tag}<p class="meta">{esc(t["intro"])}</p></article>')
    intro = "".join(f"<p>{x}</p>" for x in INTRO)
    body = (f'<section class="sec"><h1>utsushi</h1><p class="meta">{esc(DRAFT)}</p>{intro}<p class="meta">{esc(CREDIT)}</p>'
            '<p class="links"><a href="/">日本語の頁へ</a></p></section>'
            f'<section class="sec" id="toys"><h2>Pick a toy</h2><div class="plates">{cards}</div></section>')
    return skin.shell("utsushi", body, look, "/en", path, lang="en", foot=FOOT)


def toy_page(sid, look=skin.DEFAULT, path=None, printed=""):
    from .toy import versions_of

    data = hypotheses.load(sid)
    t = toy_text(sid)
    req = _load("required.json")["toys"].get(sid, {}).get("hypotheses", {})
    note = '<p class="meta">Printed. Open the PDF and print it at 100%.</p>' if printed else ""
    cards = ""
    for h in data["hypotheses"]:
        letter = hypotheses.letter(h)
        en = req.get(h["id"])
        head = f'Idea {esc(letter)}: {esc(en["name"])}' if en else f'Idea {esc(letter)}'
        how = f'<p>{esc(en["how"])}</p>' if en else '<p class="meta">This idea is described in Japanese on the sheet.</p>'
        last = versions_of(sid, h["id"], printed_only=True)
        links = ""
        if last:
            links = (f'<p class="links"><a href="/sheet/{esc(sid)}/{esc(h["id"])}_v{last[-1]}.pdf" target="_blank" rel="noopener">Template (PDF, Japanese)</a>'
                     f'<a href="/sheet/{esc(sid)}/{esc(h["id"])}_v{last[-1]}_tejun.pdf" target="_blank" rel="noopener">Instruction sheet (PDF, Japanese)</a></p>')
        steps = "".join(f"<li>{esc(s)}</li>" for s in steps_for(sid, h, data)) if en else ""
        steps = f'<details><summary>Steps</summary><ol>{steps}</ol></details>' if steps else ""
        cards += (f'<div class="plate"><div class="letter">{esc(letter)}</div><h3>{head}</h3>{how}{_marks(data, h)}{steps}<div class="acts">'
                  f'<form method="post" action="/en/toy/{esc(sid)}/print"><input type="hidden" name="hypothesis" value="{esc(h["id"])}"><button class="quiet" data-busy>Print sheets</button></form>{links}</div></div>')
    gloss = "".join(f"<dt>{esc(a)}</dt><dd>{esc(b)}</dd>" for a, b in GLOSSARY)
    tag = "" if hypotheses.stage(sid) == "必須" else '<p class="meta"><span class="lb">Untested draft</span> The name is our guess from the picture. No one has built this one.</p>'
    body = (f'<section class="hero">{_picture(sid)}<div><h1>{esc(t["name"])}</h1>{tag}<p class="lead">{esc(t["intro"])}</p>'
            f'<p class="meta"><span lang="ja">{esc(data["toy"])}</span>. {esc(DRAFT)} {esc(CREDIT)}</p>'
            f'<p class="links"><a href="/toy/{esc(sid)}">日本語の頁へ</a><a href="/en#toys">Other toys</a></p></div></section>'
            f'<section class="sec" id="ideas">{note}<h2>Make it now</h2><p class="premise" id="premise">{esc(PREMISE)}</p><p class="meta">{esc(JA_ONLY)} {esc(WAYS_NOTE)}</p>'
            f'<div class="plates">{cards}</div></section>'
            f'<section class="sec" id="words"><h2>Words on the sheet</h2><dl>{gloss}</dl></section>')
    return skin.shell(t["name"], body, look, "/en", path or f"/en/toy/{sid}", lang="en", foot=FOOT)


def band(sid):
    """日本語の玩具の頁に出す、英語の短い紹介の帯（本人の指示「おもちゃの頁に英語の短い紹介」）。"""
    t = toy_text(sid)
    return (f'<section class="sec" id="english" lang="en"><p class="meta"><span class="lb">English</span> <b>{esc(t["name"])}</b>. {esc(t["intro"])} '
            f'<a href="/en/toy/{esc(sid)}">Read and print in English</a>（英語の文は案です）</p></section>')
