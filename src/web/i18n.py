"""全頁の英語（本人の言葉 11-07「サイトは全てのページを英語で読めるようにする。全頁が対象です」。窓口の決め 130735 の案 B）。

判断の芯:
- 頁ごとに英語の頁を作らない。サーバが返す HTML の見える字（字の節と alt・title・placeholder・aria-label・釦の value）を、
  訳の表（data/i18n/en.json）で英語に置き換える。頁を作る側（他の窓の部品）は日本語のまま作り、英語の為に作りを替えない。
  頁ごとに書くと 30 ほどの頁を窓ごとに直す事になり、提出までに揃わず、後から足した字が黙って日本語のまま残るため（J-035）。
- 英語にするのは cookie の lang=en の時だけ。?lang=en で入り ?lang=ja で戻る（道は日本語の頁と同じ）。前からの英語の頁
  （/en と /en/toy/<印>・web/en.py）は別の作りのまま残す。そこにある本人が採った英文（PREMISE・INTRO・POSITION・ENGINE）は
  もう英語なので、表は触らない（表は日本語の字だけを引く）。
- 表の鍵は字の空白を 1 つにそろえ、数を {0}{1}… に置いた形（「版 14（直し 2）」も「版 7」も 1 つの鍵で引く）。値は英語。
  値が "=" の字は訳さずに日本語のまま出す（lang="ja" を付ける）。本人の言葉の引用は原文を残して英訳を添えた値にする（UX の担当の推し）。
  ただし文の中の引用（「本人の所見「…」」のように、字の一部だけが引用の物）は英訳だけにする。原文＋英訳は、字の全部が引用の独立した引用だけ
  （窓口の決め 11-07 夜・英語の引用 (a)。本人が 17:50 に決めたとおり）。
- 頁の字は、機械の置き場の有る無し（原画の写し out/sources・隣のエンジンの repo）で替わる所がある（「図は手元に無い」など）。表には両方の字を入れる。
  足す時は、手元の木と、まっさらな clone（out/ もエンジンの repo も無い木）の両方で collect を回す（審査する人は repo だけを clone して回す）。
- 人が書いた記録・感想・寄せられた声は訳さない（機械で訳した他人の言葉を出さない。窓口への推し (2)）。表に無い字は日本語のまま出る。
  repo に入っている記録（11-04 の試行）の字は頁に出るので表に入る。本人の説明は原文に英訳を添え、参加者のつぶやきを含む字は "="（日本語のまま）にする
  （窓口の決め 135434）。
  訳し漏れは試験（tests/test_en_all.py）が全部の頁の道を英語で回して止める。人の書いた字は試験の場（空の記録の置き場）には出ない。
- 台本（<script>）と CSS の中の字は替えない（台本の字を置き換えると動きを壊しうる）。台本が後から出す字は日本語のまま（残りの課題）。
- 型紙の PDF は日本語のまま（凍結の床を替えない。web/en.py の JA_ONLY と同じ断り）。
- 訳は作る側（Claude）の下書き（英語を母語とする人はまだ読んでいない）。頁の頭の断りの札は出さない（本人の言葉 11-07「これ要らない。
  Draft translation. A native speaker has not checked it yet.」。前は en.DRAFT の札を頭の帯の後に 1 つ出した。やさしい日本語の「下書きです」と同じ扱い）。

やさしい日本語（3 つ目の言葉・lang=easy。本人の言葉 11-07 夜「サイト、言語でやさしい日本語選べるように。このモードはルビつけてやさしい日本語に
全体の文が変換されるモード」「まだひつようなところは実装しよう」。設計は grove の state/yasashii-mode-20261107.md・UX の担当）:
- 同じ出口の置き換えで、表を data/i18n/yasashii.json に替える（鍵の形は英語と同じ）。値は ｜漢字《よみ》 の形でルビを書き、出口で <ruby> にする
  （実行の時に形態素解析をしない。読みの誤りを表の中で直せるように）。属性（alt など）にはルビを入れられないので、ルビの印を外した字にする
- ルビは全部の漢字に振る（本人の言葉 11-07 夜「ルビも全ての漢字にふる」）。表の値はルビの印の外に漢字を置かない（tests/test_easy_ruby.py が全部の表で見る）。
  要素を入れられない所（<title>・<option>）と、画面に出る placeholder は、ルビの代わりに 漢字（よみ） の形で読みを添える（PAREN）。
  画面に出ない属性（alt・aria-label など。読み上げは漢字のまま読める）と、送る値（value。替えると受け口の字と合わなくなる）は印を外した字のまま
- 表に無い鍵は元の日本語のまま出す（英語と違い、全部がそろわなくても頁は壊れない。表の中身は 3 つの窓が分けて書く・state/yasashii-keys/）
- 頁は日本語なので html の lang="ja" は替えない。替えない所の印は translate="no" だけ（英語の時の lang="ja" は、日本語の頁では頁の全体に付くため）
- 頁の頭の断りの札は出さない（本人の言葉 11-07 夜「下書きです、はとる」。前は「このページのやさしい日本語は、下書きです。」を英語の Draft の札と同じ所に出していた）。
  本人の言葉の引用と人の記録は書き直さず、表でルビだけを振る（字は同じで、ルビの印を足した値。"=" にするとルビが付かない）
"""
import html
import json
import pathlib
import re
from functools import lru_cache

from omochae.hypotheses import ROOT

TABLE = ROOT / "data/i18n/en.json"
TABLES = {"en": TABLE, "easy": ROOT / "data/i18n/yasashii.json"}
# やさしい日本語の表は 3 つの窓が並べて書くので、窓ごとの置き場（yasashii.d/<分け>.json・同じ {"note", "strings"} の形）も読んで重ねる。
# 1 つのファイルを 3 つの PR が書き足すと、1 本入るたびに残りが衝突するため（関門の帳面の gate-trial.d と同じ考え）
EXTRA = {"easy": ROOT / "data/i18n/yasashii.d"}
RUBY = re.compile(r"｜([^｜《》]+)《([^《》]+)》")
PLAIN_ONLY = {"title", "option"}  # 中に要素を入れられない要素（やさしい日本語は 漢字（よみ） の形で読みを添える。PAREN）
PAREN_ATTRS = {"placeholder"}  # 画面に出る属性のうち、やさしい日本語で 漢字（よみ） にする物（value は送る値なので替えない）
# SVG の字（text・tspan・textPath。TAG は名を小さい字にそろえる）。中に <ruby> を入れるとブラウザが SVG の外へ追い出し、学びの輪の図の字が
# 図の下に縦に並んだ（別の目が のこす の頁で撮って確かめた・11-07 夜）。ルビの印を外した字にする（<title>・<option> の 漢字（よみ） にはしない）。読みを 漢字（よみ） で添える形も撮って見たが、
# 図の札が図の外へはみ出し、札どうしが重なった（grove の state/easy-svg-text-20261107/）。図の字の読みは、図のすぐ上の文（同じ言葉にルビ）が持つ
SVG_TEXT = {"text", "tspan", "textpath"}
KEEP = "="           # 訳さずに日本語のまま出す印
CJK = re.compile(r"[぀-ヿ㐀-鿿＀-￯　-〿]")
NUM = re.compile(r"\d+(?:\.\d+)?")
TOKEN = re.compile(r"<!--.*?-->|<[^>]*>|[^<]+", re.S)
TAG = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9-]*)")
ATTR = re.compile(r'(\s(?:alt|title|placeholder|aria-label|value|content)=")([^"]*)(")')
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "path", "rect", "circle",
        "line", "polyline", "polygon", "ellipse", "use", "stop"}
RAW = {"script", "style", "textarea"}  # 中の字を替えない（台本・CSS・人が書く欄）
NO = re.compile(r'\stranslate="no"|\slang="ja"')
NO_EASY = re.compile(r'\stranslate="no"')
EASY_LINK = '<a class="nav-lang nav-easy" href="?lang=easy" lang="ja">やさしい</a>'  # 頭の帯の やさしい の切り替え（web.skin.nav）


def key_of(text):
    """表の鍵と、置いた数の並び。空白は 1 つに、数は {0}{1}…。"""
    nums = []

    def put(m):
        nums.append(m.group(0))
        return "{" + str(len(nums) - 1) + "}"

    return NUM.sub(put, " ".join(text.split())), nums


@lru_cache(maxsize=4)
def _table(path=None, mtime=None):
    path = pathlib.Path(path) if path else TABLE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("strings", {})


def table(lang="en"):
    path = TABLES[lang]
    out = _table(str(path), path.stat().st_mtime if path.exists() else None)
    extra = EXTRA.get(lang)
    if extra is not None and extra.is_dir():
        out = dict(out)
        for f in sorted(extra.glob("*.json")):
            out.update(_table(str(f), f.stat().st_mtime))
    return out


def ruby_html(escaped):
    """字の節の値（html.escape 済み）の ｜漢字《よみ》 を <ruby>漢字<rt>よみ</rt></ruby> にする。"""
    return RUBY.sub(r"<ruby>\1<rt>\2</rt></ruby>", escaped)


def ruby_paren(text):
    """ルビを入れられない所の字。｜漢字《よみ》 を 漢字（よみ） にする（全部の漢字に読みを添える。本人の言葉 11-07 夜）。"""
    return RUBY.sub("\\1（\\2）", text)


def ruby_plain(text):
    """属性に入れる字。ルビの印を外して漢字だけにする（属性に要素は入らない）。"""
    return RUBY.sub(r"\1", text)


def lookup(text, lang="en"):
    """日本語の字 1 つの訳（英語か、やさしい日本語）。表に無ければ None。KEEP は KEEP のまま返す。"""
    k, nums = key_of(text)
    en = table(lang).get(k)
    if en is None or en == KEEP:
        return en
    try:
        return en.format(*nums)
    except (IndexError, KeyError, ValueError):
        return None


def _swap_text(raw, miss, lang="en", plain=False, svg=False):
    text = html.unescape(raw)
    if not CJK.search(text):
        return raw
    en = lookup(text, lang)
    if en is None:
        miss.append(" ".join(text.split()))
        return raw
    lead = raw[: len(raw) - len(raw.lstrip())]
    tail = raw[len(raw.rstrip()):]
    if en == KEEP:
        return f'{lead}<span lang="ja">{raw.strip()}</span>{tail}' if lang == "en" else raw
    if lang == "easy":
        # 要素を入れられない所（<title>・<option>）では、属性と同じくルビの印を外した字にする（タブの題に <ruby> が字のまま出たため・別の窓の指摘）
        # SVG の字は印を外した字（読みを添えると図の札がはみ出す・SVG_TEXT の注）。<title>・<option> は 漢字（よみ）。ほかの字の節は <ruby>
        if svg:
            return lead + html.escape(ruby_plain(en), quote=False) + tail
        return lead + (html.escape(ruby_paren(en), quote=False) if plain else ruby_html(html.escape(en, quote=False))) + tail
    return lead + html.escape(en, quote=False) + tail


def _swap_attrs(tag, miss, lang="en"):
    def one(m):
        text = html.unescape(m.group(2))
        if not CJK.search(text):
            return m.group(0)
        en = lookup(text, lang)
        if en is not None and en != KEEP and lang == "easy":
            en = ruby_paren(en) if m.group(1).strip()[:-2] in PAREN_ATTRS else ruby_plain(en)
        if en is None:
            miss.append(" ".join(text.split()))
            return m.group(0)
        return m.group(1) + (m.group(2) if en == KEEP else html.escape(en, quote=True)) + m.group(3)

    return ATTR.sub(one, tag)


def to_en(page, miss=None, lang="en"):
    """日本語の頁の HTML を英語（lang="easy" ならやさしい日本語）にする。miss に表に無かった字を足す（試験と collect が使う）。
    translate="no" か lang="ja" の付いた要素の中と、script・style・textarea の中は替えない（やさしい日本語では translate="no" だけ）。"""
    miss = [] if miss is None else miss
    frozen_mark = NO if lang == "en" else NO_EASY
    out, stack = [], []   # stack: (要素の名, この要素から下を替えないか)
    for m in TOKEN.finditer(page):
        tok = m.group(0)
        if tok.startswith("<!--") or tok.startswith("<!") or tok.startswith("<?"):
            out.append(tok)
            continue
        if tok.startswith("<"):
            t = TAG.match(tok)
            if not t:
                out.append(tok)
                continue
            closing, name = t.group(1) == "/", t.group(2).lower()
            frozen = any(f for _, f in stack)
            if closing:
                while stack:
                    top, _ = stack.pop()
                    if top == name:
                        break
                out.append(tok)
                continue
            if name == "html":
                if lang == "en":
                    tok = re.sub(r'\slang="ja"', ' lang="en"', tok, count=1)
            elif not frozen:
                tok = _swap_attrs(tok, miss, lang)
            if name not in VOID and not tok.rstrip().endswith("/>"):
                stack.append((name, name in RAW or (name != "html" and bool(frozen_mark.search(tok)))))
            out.append(tok)
            continue
        out.append(tok if any(f for _, f in stack) else _swap_text(tok, miss, lang, plain=bool(stack) and stack[-1][0] in PLAIN_ONLY, svg=bool(stack) and stack[-1][0] in SVG_TEXT))
    return "".join(out)


def page_easy(page, miss=None):
    """頁をやさしい日本語にする（表に無い字は元のまま）。やさしい の切り替えは日本語へ戻る口にする。
    頭の下書きの札は出さない（本人の言葉 11-07 夜「下書きです、はとる」）。戻る口の 日本語 にもルビを振る（全部の漢字に。同じ言葉）"""
    page = to_en(page, miss, lang="easy")
    return page.replace(EASY_LINK, '<a class="nav-lang nav-easy" href="?lang=ja" lang="ja"><ruby>日本語<rt>にほんご</rt></ruby></a>')


def page_en(page, miss=None):
    """頁を英語にする。言語の切り替えは日本語へ戻る口にする。頭の下書きの札は出さない（本人の言葉 11-07「これ要らない」）。"""
    page = to_en(page, miss)
    return page.replace('<a class="nav-lang" href="?lang=en" lang="en">English</a>', '<a class="nav-lang" href="?lang=ja" lang="ja">日本語</a>')


def routes(sids):
    """英語で回す頁の道（試験と collect が使う）。全部の玩具の頁と、玩具に依らない頁。POST の後の知らせは、別に流して見る。"""
    out = ["/", "/about", "/otona", "/loop", "/loop/ayumi", "/toys?paper=1", "/gallery", "/kaizen", "/no-such-page"]
    for s in sids:
        out += [f"/loop/{s}", f"/zukan/{s}/yomi", f"/toy/{s}", f"/toy/{s}/kumitate", f"/toy/{s}/tsukuru",
                f"/toy/{s}/techo", f"/toy/{s}/techo/kiroku", f"/toy/{s}/kasane", f"/toy/{s}/kasane/hmd"]
    return out


def prime(base, sids):
    """作りながら見る頁と手帖は、紙を刷った後でしか開かない（刷る前は玩具の頁へ戻す）。英語で回す前に、必須の 2 種と、
    雛形ごとに 1 種の、たたき台の紙を刷っておく（雛形ごとに手順の文が違う。全 83 種を刷ると数分かかる）。刷った玩具の道を返す。"""
    import urllib.parse
    import urllib.request

    from omochae import hypotheses

    picked, seen = [], set()
    for sid in sids:
        data = hypotheses.load(sid)
        tpl = data.get("template", "slider_fan")
        if hypotheses.stage(sid) == "必須" or tpl not in seen:
            seen.add(tpl)
            picked.append(sid)
    for sid in picked:
        body = urllib.parse.urlencode({"hypothesis": hypotheses.sheet_of(sid)["id"]}).encode()
        req = urllib.request.Request(f"{base}/toy/{sid}/print", data=body, headers={"Origin": base})
        try:
            urllib.request.urlopen(req, timeout=300).read()
        except Exception:  # 刷れない玩具は、その頁を回さないだけ（訳し漏れの試験は刷れた頁で見る）
            pass
    return picked


def collect(base, paths, cookie="utsushi_lang=ja", workers=6, lang="en", pages=None):
    """道ごとに日本語の頁を読んで英語に通し、表に無かった日本語の字を {字: 初めに出た道} で返す。404 の頁（断りの頁）も読む。
    英語の頁をもう一度通すと、原文を残した値（本人の言葉の引用）の日本語も拾ってしまうので、日本語の頁を通す。
    lang="easy" はやさしい日本語の表で引く。pages に dict を渡すと {道: [表に無かった字…]} も入れる（やさしい日本語の落ちた字を
    頁ごとに数える一覧の材料。本人の言葉 11-07 夜「やさしい日本語は全部のページに反映させる」）"""
    import concurrent.futures as cf
    import urllib.error
    import urllib.request

    def one(p):
        req = urllib.request.Request(base + p, headers={"Cookie": cookie})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return p, r.status, r.read().decode("utf-8", "replace"), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            return p, e.code, e.read().decode("utf-8", "replace"), e.headers.get("Content-Type", "")

    found = {}
    with cf.ThreadPoolExecutor(workers) as ex:
        for p, code, body, ctype in ex.map(one, paths):
            if code == 404 and not body:
                continue
            if not ctype.startswith("text/html"):
                continue
            miss = []
            to_en(body, miss, lang=lang)
            for t in miss:
                found.setdefault(t, p)
            if pages is not None:
                pages[p] = miss
    return found


def main(argv=None):
    import argparse
    import sys

    ap = argparse.ArgumentParser(prog="web.i18n", description="全頁を英語で読み、表に無い日本語の字を書き出す（訳の表を足す時の材料）")
    ap.add_argument("collect", nargs="?")
    ap.add_argument("--base", required=True, help="回してあるサーバ（http://127.0.0.1:<port>）")
    ap.add_argument("--out", required=True, help="表に無い字の JSON の置き場（repo の外）")
    ap.add_argument("--lang", default="en", choices=sorted(TABLES), help="どの表で引くか（easy はやさしい日本語）")
    ap.add_argument("--pages", help="頁ごとの表に無い字 {道: [字…]} の JSON の置き場（repo の外。やさしい日本語の落ちた字の一覧の材料）")
    a = ap.parse_args(argv)
    from .play_server import sources

    prime(a.base, sources())
    pages = {} if a.pages else None
    found = collect(a.base, routes(sources()), lang=a.lang, pages=pages)
    if pages is not None:
        with open(a.pages, "w", encoding="utf-8") as f:
            json.dump(pages, f, ensure_ascii=False, indent=0)
    keyed = {}
    for t, p in found.items():
        keyed.setdefault(key_of(t)[0], p)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(keyed, f, ensure_ascii=False, indent=0)
    print(f"表に無い字 {len(keyed)}（{sum(len(k) for k in keyed)} 字）→ {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
