"""小学生・中学生の目で、頁と紙の文を数える道具（#317）。

なぜ: 本人の方針（11-05）「20歳より下、中学生以下、小学生も取り組む可能性がある」。確認に出た文の外に何が残るかを、本物の頁から数えて見えるようにする。
頁の字は変えない。文は本人の確認が要るので、この道具は数えて一覧を出すだけにする。

表の言いかえ（plain）に入れるのは本人が採った字（#318）だけ。まだ採られていない語は None のまま置き、案は Issue で本人に見てもらう。
code に案を持つと、確かめる前の字が頁へ流れる道ができるため。
作る側の内輪の言葉（本人・棚卸し・雛形・複写など）は #135 の表（wording.py）の受け持ちで、ここには書かない。同じ語を 2 つの表に書くと、言いかえが割れるため。数える時は、その表を読んで 1 つに並べる。

使い方: PYTHONPATH=src python -m web.plain_words [--toy <玩具の ID>]... [--walk] [--sheets <PDF の置き場>] [--out <結果の紙>] [--strict]
終わりの値: 0 数えた / 3 --strict で語・です・ますでない文・並ばない「仮説」が残っている / 4 数えられない。
"""
import argparse
import html.parser
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

from . import wording

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _w(word, plain=None, pattern=None):
    return {"word": word, "plain": plain, "pattern": re.compile(pattern or re.escape(word))}


TABLE = [
    _w("仮説", "ためしの案（仮説）"),
    _w("正解", "正しい答えではありません"),
    _w("連絡先", "住所・電話番号・メール"),
    _w("上下はありません", "どれがえらい、ということはありません"),
    _w("翻案"), _w("復元"), _w("端末"), _w("検討"), _w("原文の引用"), _w("見立て"),
    _w("二次資料"), _w("解釈"), _w("推測"), _w("要約"), _w("寸法"), _w("行程"),
    # 「印刷」「刷り上がり」の形に当てない。「刷る」の活用だけを見る
    _w("刷る", pattern=r"(?<!印)刷(?:る|って|った|り(?!上)|ら|れ)"),
    # 「出版」「版画」「版本」「図版」は別の語なので当てない
    _w("版", pattern=r"(?<![出図])版(?![画本])"),
    _w("本文"), _w("翻刻"), _w("見込み"), _w("未確認"), _w("推定"), _w("通例"), _w("趣旨"), _w("確度"),
    _w("糊代"), _w("蛇腹"), _w("角筒"), _w("外筒"), _w("内筒"), _w("錘"), _w("楊枝"),
]
OWN_WORDS = {w["word"] for w in TABLE}
TABLE += [_w(row.pattern, None, row.pattern) for row, _ in wording.TABLE]  # 言いかえは向こうの表が持つ。ここには書かない
# 語を数えない所。「仮説」は語の数ではなく、頁の最初の 1 つで並ぶかを別に見る（消さずに並べる決まりなので、語としては残ってよい）
NOT_A_WORD_HIT = {"仮説"}

POLITE = re.compile(r"(です|ます|ました|でした|ません|でしょう|でしょうか|ください|ましょう|ですか|ますか|ませんか)[」』）)]*$")
LONG = 40
OPENING, CLOSING, ENDS = "（(「『", "）)」』", "。！？"
# です・ますをそろえる頁（#317 のゴールの要件）。序・図鑑・改善の輪は書誌や作る側の字が多いので、一覧には出すが床にしない
POLITE_PAGES = re.compile(r"/(toys|toy/[^/（]+(/tsukuru|/techo(/kiroku)?)?)?(（.*）)?")
SKIP_TAGS = {"style", "blockquote", "noscript", "svg"}
# 引用・歌・見本の声は、書いた人の言葉なので言いかえの相手にしない。足（foot）は書誌なので見ない
SKIP_CLASSES = {"songs", "samples", "sample", "foot"}
BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "dl", "dt", "dd", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "aside",
              "header", "footer", "nav", "main", "figure", "figcaption", "table", "tr", "td", "th", "form", "label", "summary",
              "details", "button", "option", "select", "title", "br", "hr", "body", "head", "html", "textarea"}
VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"}
SHOWN_ATTRS = ("placeholder", "aria-label", "title", "alt")
# 画面に出す JS の字: コメントを除いた、仮名を含む 1 行の文字列だけを見る
JS_COMMENT = re.compile(r"(?<![:'\"`])//[^\n]*|/\*.*?\*/", re.S)
JS_TEXT = re.compile(r"""'([^'\n]*[ぁ-ん][^'\n]*)'|"([^"\n]*[ぁ-ん][^"\n]*)"|`([^`\n]*[ぁ-ん][^`\n]*)`""")


class _Text(html.parser.HTMLParser):
    """頁を、人が読む字のかたまりに分ける。隠す所の中は読まない。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = [""]
        self.stack = []
        self.skip = 0
        self.script = False

    def _break(self):
        if self.parts[-1]:
            self.parts.append("")

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        hide = tag in SKIP_TAGS or bool(SKIP_CLASSES & set((a.get("class") or "").split()))
        if tag not in VOID_TAGS:
            self.stack.append((tag, hide))
            self.skip += hide
        if tag == "script":
            self.script = True
        if tag in BLOCK_TAGS or tag in VOID_TAGS:
            self._break()
        if not self.skip:
            for k in SHOWN_ATTRS:
                if a.get(k):
                    self._break()
                    self.parts[-1] = a[k]
                    self._break()

    def handle_endtag(self, tag):
        if tag == "script":
            self.script = False
        # 閉じ忘れの <p> や <li> があっても隠す数がずれないよう、同じ名前まで戻す
        if tag not in VOID_TAGS and any(t == tag for t, _ in self.stack):
            while True:
                t, hide = self.stack.pop()
                self.skip -= hide
                if t == tag:
                    break
        if tag in BLOCK_TAGS:
            self._break()

    def handle_data(self, data):
        if self.skip:
            return
        if self.script:
            self._break()
            for m in JS_TEXT.finditer(JS_COMMENT.sub("", data)):
                self.parts[-1] = next(g for g in m.groups() if g)
                self._break()
            return
        self.parts[-1] += data


def blocks(page):
    p = _Text()
    p.feed(page)
    return [" ".join(x.split()) for x in p.parts if x.strip()]


def _sentences(block):
    # 「。」で閉じた文だけを文と数える。見出し・釦・書誌は「。」で閉じないので入らない。かっこの中の句点では切らない
    out, cur, depth = [], "", 0
    for ch in block:
        cur += ch
        depth = depth + 1 if ch in OPENING else max(0, depth - 1) if ch in CLOSING else depth
        if not depth and (ch in ENDS or (ch in CLOSING and cur[-2:-1] in tuple(ENDS))):
            out.append(cur.strip())
            cur = ""
    return [s for s in out if s.strip(ENDS + CLOSING + OPENING + " ")]


def _is_polite(sentence):
    # 末尾のかっこ書き（「残しました（手順 1）。」）は文の終わりでない
    return bool(POLITE.search(re.sub(r"(?<=.)（[^（）]*）$", "", re.sub(r"[。！？]", "", sentence))))


def census(pages, sheets=None):
    """pages は {道: HTML}、sheets は {紙の名: 字}。紙は語だけを見る: 手順の言い切りをそろえるかは決める点なので、文には数えない。"""
    counts = {}
    seen = {"not_polite": {}, "long": {}}
    sentences = 0
    alone = []
    texts = [(where, blocks(h)) for where, h in pages.items()] + [(where, [t]) for where, t in (sheets or {}).items()]
    for where, parts in texts:
        joined = "\n".join(parts)
        for e in TABLE:
            n = len(e["pattern"].findall(joined))
            if n and e["word"] not in NOT_A_WORD_HIT:
                counts[(e["word"], where)] = n
        if where not in (sheets or {}):
            m = re.search("仮説", joined)
            if m and "ためしの案" not in joined[max(0, m.start() - 12):m.end() + 12]:
                alone.append(where)
            for part in parts:
                for s in _sentences(part):
                    sentences += 1
                    if not _is_polite(s):
                        seen["not_polite"].setdefault(s, []).append(where)
                    if len(s) > LONG:
                        seen["long"].setdefault(s, []).append(where)
    per = {}
    for (word, where), n in counts.items():
        per.setdefault(word, []).append((where, n))
    words = [{"word": w, "where": where, "count": n} for w, rows in per.items() for where, n in rows]
    # 同じ文が多くの頁に出ても 1 つと数える。直す手間は文ごとなので
    listed = {k: [{"text": s, "where": v} for s, v in rows.items()] for k, rows in seen.items()}
    return {"words": words, "sentences": sentences, "hypothesis_alone": alone, "sheets": len(sheets or {}), **listed}


def strict_failed(r):
    """文の入れ替えが済んだ後の床。40 字を超える文は「人が見る」要件なので落とさない。"""
    impolite = any(POLITE_PAGES.fullmatch(w) for s in r["not_polite"] for w in s["where"])
    return bool(r["words"] or impolite or r["hypothesis_alone"])


def _sids():
    return sorted(p.stem for p in (ROOT / "data/hypotheses").glob("*.json"))


def collect(sids=None, walk=False):
    """本物の頁を手元の口で開く。設定が本物の置き場を指していても混ぜないよう、置き場は必ず一時の場所にして、終わったら戻す。
    walk は玩具ごとに先頭の案を刷って記録してから、もう一度開く。紙の窓と記録の札の字は、作っている間にしか出ないため。"""
    keep = os.environ.get("OMOCHAE_DATA")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["OMOCHAE_DATA"] = tmp
        try:
            return _open_pages(sids or _sids(), walk)
        finally:
            if keep is None:
                del os.environ["OMOCHAE_DATA"]
            else:
                os.environ["OMOCHAE_DATA"] = keep


def _open_pages(sids, walk):
    from omochae import hypotheses, records
    from web import play_server
    server = play_server.serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    # /toys は入口へ送るので、残る絞り込みの頁（紙 1 枚で作れる物だけ）を見る
    paths = ["/", "/about", "/otona", "/toys?paper=1", "/gallery", "/loop", "/loop/ayumi"]
    for sid in sids:
        paths += [f"/toy/{sid}", f"/toy/{sid}/tsukuru", f"/toy/{sid}/techo", f"/toy/{sid}/techo/kiroku", f"/loop/{sid}"]

    def fetch(p):
        with urllib.request.urlopen(base + p, timeout=120) as r:
            return r.read().decode("utf-8", "replace")

    def send(p, **data):
        req = urllib.request.Request(base + p, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
        urllib.request.urlopen(req, timeout=180).close()

    try:
        pages = {p: fetch(p) for p in paths}
        for sid in sids if walk else ():
            hid = hypotheses.sheet_of(sid)["id"]
            send(f"/toy/{sid}/print", hypothesis=hid)
            send(f"/toy/{sid}/record", hypothesis=hid, result=records.results_for(sid)[0])
            pages[f"/toy/{sid}（記録の後）"] = fetch(f"/toy/{sid}?see={hid}&kind=after&v=1")
            for tail in ("tsukuru", "techo", "techo/kiroku"):
                pages[f"/toy/{sid}/{tail}（記録の後）"] = fetch(f"/toy/{sid}/{tail}")
    finally:
        server.shutdown()
        server.server_close()
    return pages


def read_sheets(folder):
    """刷った PDF の字を読む。頁の字と同じ語の表で見るため。-layout は行で字が切れるので使わない。"""
    # 鍵は置き場からの道にする。玩具ごとの置き場に同じ名前の紙があるので、名前だけだと 1 枚に潰れる
    return {p.relative_to(folder).as_posix(): subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True, check=True, timeout=120).stdout
            for p in sorted(pathlib.Path(folder).rglob("*.pdf"))}


def _places(rows):
    return "・".join(rows[:3]) + (f" ほか {len(rows) - 3} 頁" if len(rows) > 3 else "")


def report(r):
    per = {}
    for h in r["words"]:
        row = per.setdefault(h["word"], {"total": 0, "where": []})
        row["total"] += h["count"]
        row["where"].append(h["where"])
    plain = {e["word"]: e["plain"] for e in TABLE}
    lines = ["# 小学生・中学生の目で数えた残り", "",
             f"紙 {r['sheets']} 枚（語だけを見る）。文 {r['sentences']}（「。」で閉じた物）。です・ますでない文 {len(r['not_polite'])}。{LONG} 字を超える文 {len(r['long'])}。"
             f"最初の「仮説」に「ためしの案」が並ばない頁 {len(r['hypothesis_alone'])}。", "", "## 語", "",
             "| 語 | 回数 | 頁の数 | 本人が採った言いかえ | 出ている所 |", "|---|---|---|---|---|"]
    for w, row in sorted(per.items(), key=lambda kv: -kv[1]["total"]):
        lines.append(f"| {w} | {row['total']} | {len(row['where'])} | {plain.get(w) or '（まだ）'} | {_places(row['where'])} |")
    for title, key in (("## です・ますでない文", "not_polite"), (f"## {LONG} 字を超える文", "long")):
        lines += ["", title, ""] + [f"- {s['text']}（{_places(s['where'])}）" for s in r[key]]
    lines += ["", "## 最初の「仮説」に「ためしの案」が並ばない頁", ""] + [f"- {p}" for p in r["hypothesis_alone"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--toy", action="append", help="玩具の ID。省くと全部の玩具")
    ap.add_argument("--walk", action="store_true", help="玩具ごとに先頭の案を刷って記録した後の頁も数える")
    ap.add_argument("--sheets", help="刷った PDF の置き場。語だけを見る")
    ap.add_argument("--out", default=str(ROOT / "out/plain-words.md"))
    ap.add_argument("--strict", action="store_true", help="語・です・ますでない文・並ばない「仮説」が残っていれば 3 で終える（文の入れ替えが済んだ後の床）")
    a = ap.parse_args(argv)
    try:
        sheets = read_sheets(a.sheets) if a.sheets else None
        if a.sheets and not sheets:
            print(f"数えられない: 紙が無い: {a.sheets}", file=sys.stderr)
            return 4
        r = census(collect(a.toy, walk=a.walk), sheets)
    except (OSError, urllib.error.URLError, subprocess.SubprocessError) as e:
        print(f"数えられない: {e}", file=sys.stderr)
        return 4
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report(r), encoding="utf-8")
    print(f"語 {len({h['word'] for h in r['words']})} 種。紙 {r['sheets']} 枚。文 {r['sentences']}。です・ますでない文 {len(r['not_polite'])}。{LONG} 字を超える文 {len(r['long'])}。"
          f"「仮説」が並ばない頁 {len(r['hypothesis_alone'])}。結果: {out}")
    return 3 if a.strict and strict_failed(r) else 0


if __name__ == "__main__":
    sys.exit(main())
