"""学ぶ人の画面に、作る側の内輪の言葉と裸の番号が出ない（#135）。本物の API は呼ばない。

なぜ頁を開いて見るか: 字は data/hypotheses の欄・雛形の値・頁の作りの 3 か所から来るので、どれか 1 か所の字を見ても漏れる。
見るのは画面に見える字（alt・aria-label・title・placeholder を含む）で、リンクの先と隠した値は見ない。そこの番号は作る側の道具が使う。
/loop は作る側の頁なので見ない（kaizen.py）。人が書いた文の中の字は見本に入れない。替えを掛けない所なので。
"""
import html.parser
import os
import pathlib
import re
import shutil
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")
os.environ.pop("ANTHROPIC_API_KEY", None)

ROOT = pathlib.Path(__file__).resolve().parents[1]
# 本物の記録と版を置き場へ写す。R-0001 の札と版 2 の根拠まで開くため。本物の data/ には書かない
for part in ("records", "loop"):
    shutil.copytree(ROOT / "data" / part, os.path.join(DATA, part))

from api import ask  # noqa: E402
from omochae import hypotheses, labels, loop, records  # noqa: E402
from web import zukan  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

ask._key_present = lambda: False  # 手元に鍵があっても呼ばない。鍵が無い時の文も見る

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
# 御来迎のたたき台の仮説（次の組は H-C の柄を下から押し上げる形・前の組は H-A。本人の決定 2026-11-06。hypotheses.sheet_id）
GS = hypotheses.sheet_of(G)["id"]
INSIDE = (
    ("本人", r"本人"),
    ("採否待ち", r"採否"),
    ("仮説の番号", r"(?<![A-Za-z0-9])H-[A-Z0-9]+"),
    ("記録の番号", r"(?<![A-Za-z0-9])R-\d+"),
    ("自分の仮説の番号", r"(?<![A-Za-z0-9])OWN-\d+"),
    ("決定の番号", r"(?<![A-Za-z0-9])[JUTW]-\d+"),
    ("調べの番号", r"research"),
    ("ファイルの道", r"data/|docs/|\.json"),
    ("API の URL", r"wp-json"),
    ("箱の座標", r"pct:"),
    ("棚卸し", r"棚卸し"),
    ("雛形", r"雛形"),
    ("型紙エンジン", r"型紙エンジン"),
    ("内部の名前", r"[a-z]*_[a-z_]+|[A-Z]+_[A-Z]+"),
    ("セッション", r"Claude Code|セッション"),
    ("組の版", r"[a-z_-]+-v\d+"),
    ("国会図書館の略", r"NDL"),
    ("手元の複写", r"手元の複写|複写 [AB]"),
    ("鍵", r"鍵"),
    ("床", r"床を通"),
    ("コマ", r"コマ \d"),
    ("見込み", r"見込[みむ]"),
)
# 言い換えが前にある番号はよい。番号は作る側が札を引くのと、紙の字と照らすのに使う
TOLD = r"記録の番号 R-\d+|組の番号 \S+"


class Visible(html.parser.HTMLParser):
    """画面に見える字だけを集める。"""

    def __init__(self):
        super().__init__()
        self.out, self.skip, self.paper = [], 0, 0

    def handle_starttag(self, tag, attrs):
        # 組み立ての頁の紙の絵（svg.rt-paper）は刷る紙そのものの絵で、中の字は紙の字。紙の字は頁で替えない（必須 2 種の指紋）。ほかの svg は飛ばさない
        if self.paper or (tag == "svg" and "rt-paper" in (dict(attrs).get("class") or "").split()):
            self.paper += tag == "svg"
            return
        self.skip += tag in ("style", "script")
        self.out += [v for k, v in attrs if k in ("alt", "aria-label", "title", "placeholder") and v]

    def handle_endtag(self, tag):
        if self.paper:
            self.paper -= tag == "svg"
            return
        self.skip -= tag in ("style", "script")

    def handle_data(self, data):
        if not self.skip and not self.paper and data.strip():
            self.out.append(data.strip())


def visible(page):
    v = Visible()
    v.feed(page)
    return v.out


# 飛ばすのは紙の絵の中だけ。入れ子の後も閉じた所から数え直し、ほかの svg の字は見る
assert visible('<svg class="rt-paper"><text>紙の字</text><svg><text>紙</text></svg><text>紙</text></svg><p>見える</p><svg><text>絵の字</text></svg>') == ["見える", "絵の字"]

# 1 つのブラウザとして動く（記録を残した画面の鍵の cookie を持つ。説明と字を足す口は、その画面にだけ開くので、その字もここで見る）
urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPCookieProcessor()))


class Site:
    def __init__(self, look):
        self.server = serve(0, look=look)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def open(self, path, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        r = urllib.request.Request(self.base + path, data=body, headers={"Origin": self.base})
        try:
            with urllib.request.urlopen(r) as x:
                return x.status, x.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()


white, black = Site("tenji"), Site("zine")
pages = {}


def see(site, path, data=None, name=None):
    code, page = site.open(path, data)
    assert code in (200, 422), (path, code)
    pages[name or path] = visible(page)
    return page


# 1 全部の玩具の頁。data/hypotheses の字はここに出る
for s in sources():
    for path in (f"/toy/{s}", f"/zukan/{s}", f"/toy/{s}/techo", f"/toy/{s}/techo/kiroku"):
        see(white, path)
# 2 頁の作りの字。皮で作りが違う頁は両方を見る
for site, tag in ((white, "白"), (black, "黒")):
    for path in ("/", "/about", "/toys", "/gallery", "/zukan", "/en", f"/toy/{G}", f"/toy/{T}"):
        see(site, path, name=path if site is white else f"{path}（{tag}）")
for s in (G, T):
    see(white, f"/zukan/{s}/yomi", {"mine": "ためしの読み"}, f"/zukan/{s}/yomi（読みの後）")
# 3 番号の出る札まで進める: 紙 → 記録 → 説明 → 次の版 → 窓 → 手帖 → 自分の仮説 → 聞く口
see(white, f"/toy/{G}/print", {"hypothesis": GS}, "紙を作った後")
see(white, f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた", "impression": "すっと開いた"}, "記録の後")
rid = records.all_records(G)[-1]["id"]  # 今残した記録。説明は次の記録が残る前に、残した画面から書く。番号を決め打ちしない
told = see(white, f"/record/{rid}/explain", {"text": "折りが固くて戻る", "next_idea": "厚さを変える", "by": "大人"}, "説明の後")
assert loop.explanation(rid) and "次の版を作る" in told, "説明の後の札まで届いていない"  # 通らないまま進むと、この先の見張りが空になる
see(white, f"/record/{rid}/ai-interpret", {}, "鍵が無い時の AI の口")
see(white, f"/record/{rid}/next", {"interpretation": "折りが固い", "param": "fold_count", "to": "24", "why": "開きを見る", "by": "大人"}, "次の版の後")
assert loop.latest_version(G, GS) == 2, "次の版の後の札まで届いていない"
see(white, f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた", "impression": "もう一度"}, "2 つ目の記録の後")
waiting = see(white, f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた"}, "説明を待つ記録の後")
assert 'name="next_idea"' in waiting, "説明の欄まで届いていない"
see(white, f"/toy/{G}?see={GS}&kind=sheet&v=2", name="版 2 の窓")
see(white, f"/toy/{G}/techo/kiroku", name="記録の後の手帖の記録の頁")
see(white, f"/toy/{G}/tsukuru", name="作りながら見る")
see(white, f"/zukan/{G}", name="記録の後の図鑑")
see(white, "/gallery", name="記録の後のギャラリー")
assert not hypotheses.save_own(G, "糸で引く", "糸で引いて開く", "糸らしい線")[1]  # 前に書かれた仮説の形（頁の書く欄は #409 で外れた）
see(white, f"/toy/{G}", name="自分の仮説の後")
see(white, f"/toy/{G}/record", {"hypothesis": "OWN-1", "result": "動いた", "impression": "開いた"}, "自分の仮説の記録の後")
see(white, f"/zukan/{G}", name="自分の仮説の後の図鑑")
asked = see(white, f"/toy/{G}/ask", {"hypothesis": GS, "question": "紙の端はどこまで切りますか"}, "聞く口の答え")
assert "AI の答えは" in asked, "鍵が無い時の文まで届いていない"

left = {}
for where, words in pages.items():
    for name, rx in INSIDE:
        for text in words:
            if re.search(rx, re.sub(TOLD, "", text)):
                left.setdefault(name, {}).setdefault(text, []).append(where)
if left:
    lines = [f"{name}: {len({w for ws in hits.values() for w in ws})} 頁、{len(hits)} 文。例: {next(iter(hits))[:60]}" for name, hits in left.items()]
    raise AssertionError("内輪の言葉が画面に出ている\n" + "\n".join(lines))

# 表は 1 か所（#135 の要件）。字を直す時に頁を回らなくてよい
from web import wording  # noqa: E402

for p in (ROOT / "src/web").glob("*.py"):
    if p.name != "wording.py":
        text = p.read_text(encoding="utf-8")
        assert wording.MAKER not in text and "記録の番号 {" not in text and "組の番号 {" not in text, f"{p.name} に表の字がある"

# 出所の字の形（data/hypotheses の where にある形）。読む人の字が表のとおりに出る
for raw, reader in {
    "NDL コマ 4 の左頁（棚卸しの箱 pct:17,77,9,6）": "国立国会図書館の本の 4 コマ目の左の頁",
    "NDL コマ 5 の図": "国立国会図書館の本の 5 コマ目の図",
    "data/inventory/edo-nishiki.json": "作る側の一覧",
    "棚卸しの見立て（data/inventory/edo-nishiki.json）": "作る側の考え",
    "棚卸し（data/inventory/edo-nishiki.json）の見立て": "作る側の考え",
    "同じ図と棚卸しの見立て": "同じ図と作る側の考え",
    "棚卸しの見込み: 動かない飾りに見える": "作る側の考え: 動かない飾りに見える",
    "ついばむ動きは棚卸しの見立ての推測": "ついばむ動きは作る側の考え",
    "腰に差したり振って遊ぶ持ち物という見込み": "腰に差したり振って遊ぶ持ち物という考え",
    "本文の注に「立てかけて飾る」とある見込み（棚卸しの見立て）": "本文の注に「立てかけて飾る」とあると考えた（作る側の考え）",
    "すき間が 1.5〜6mm なら出し入れできると見込む。実物では未確認": "すき間が 1.5〜6mm なら出し入れできると考える。実物では未確認",
    "Claude Code のセッションが書いた。人の確認はまだ": "AI（Claude）が書いた下書きです。人はまだ確かめていません",
    "糸で引く仕掛けの読みは、家族の pull_string の見立てから": "糸で引く仕掛けの読みは、糸で引くおもちゃの種類から考えた物",
    "research/03": "作る側の計算",
    "雛形 stick_prop の式（_drop）": "作る側の計算",
    "雛形 stick_prop の床（SLIDE_MIN・SLIDE_MAX）": "作る側の計算",
    "雛形 wheel_cart の床": "作る側の計算",
    "手元の複写 B 頁 78 の解説（要約）": "作る側が読んだ本の解説を、短くまとめた物",
    "手元の複写 B 頁 78 が引く『還魂紙料』（要約。原典は未確認）": "作る側が読んだ本が引く『還魂紙料』を、短くまとめた物。もとの本はまだ確かめていません",
    "手元の複写 A 頁 232 と B 頁 112 の歌": "作る側が読んだ本の歌",
    "https://japan-toy-museum.org/wp-json/wp/v2/monthly/29399": "日本玩具博物館「江戸の手遊び「御来迎」」",
    "型紙は H-C と同じで、動かし方が逆": "型紙は仮説 C と同じで、動かし方が逆",
    "同じ図": "同じ図",
    "読みが割れた事と、決めた事": "読みが分かれた事と、決めた事",
    "本人が 2026-11-03 に、複写 B（頁 78）の読みに決めました。": "このサイトを作った人が 2026-11-03 に、本 B（頁 78）の読みに決めました。",
    "鍵が置かれると、Claude が答えます": "AI の返事は、この場では使えません",
}.items():
    assert wording.plain(raw) == reader, (raw, wording.plain(raw))
# 誰も書いていない字は替えない
assert wording.plain("つるつるの床ほど長く回る") == "つるつるの床ほど長く回る"

# 番号は言い換えと一緒に残る。作る側が札を引けるように
toy = " ".join(pages["次の版の後"])
assert f"記録の番号 {rid}" in toy and "をもとに直しました" in toy, "番号の言い換え"
assert any("作る側が直します" in t for t in pages[f"/toy/{G}"]), "改善の輪の節の固定の文"
gallery = " ".join(pages["/gallery"])
assert "個人情報を確かめてから" in gallery and "（持ち寄りの場）" in gallery, "ギャラリーの固定の文"
assert f"記録の番号 {rid} をもとに直しました" in " ".join(pages["版 2 の窓"])
# 前の手帖の頁は、紙を選ぶ札の下に「紙に印刷してある組の番号」を出していた（#135）。作り直した手帖（#87）は紙を選ぶ札を持たず、作る頁に組の番号を出さない
# （本人の決定 11-05・案 A）。この字はサイトのどこにも出なくなる。出さない事は本人が決めた（11-06 のカード 125158・推し A。PR #395 の本文に書いた）
assert "goraigo-v10" not in " ".join(pages[f"/toy/{G}/techo"]), "作る頁に組の番号を出さない"

# 誰が確かめたか・書いたかの印は残る（J-016）。言葉だけが替わる
zu = pages[f"/zukan/{G}"]
for w in ("原文の引用", "仮説", "観察", f"確かめた人: {wording.MAKER}"):
    assert w in zu, w
tp = pages[f"/toy/{G}"]
assert f"原文の引用。確かめた人: {wording.MAKER}" in tp
assert any(t.startswith("〔観察〕") and "国立国会図書館の本の" in t for t in tp), "根拠の種類の印は消えない"
assert "作る側のたとえ" in tp and any("AI（Claude）が書いた下書きです" in t for t in tp), "たとえの印"
yomi = " ".join(pages[f"/zukan/{G}/yomi（読みの後）"])
assert f"確かめた人: {wording.MAKER}" in yomi and f"{wording.MAKER}が 2026-11-03 に" in yomi, "読みを決めた人の印"
# 作る側が残した試行の控えは文ごと替わる。人が書いた文は替えない（記録のメモも自分の仮説も、書いたとおりに出す）
assert any("見た事は、このサイトを作った人が答えました" in t for t in tp), "試行の控え"
see(white, f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた", "note": f"本人が {GS} の紙で折った"}, "人の文")
assert f"メモ: 本人が {GS} の紙で折った" in pages["人の文"], "人の文を替えない"
# 床は記録の値のままで見る。画面の字を替えても、人が確かめた線は動かない
quotes = zukan.lines_for(G)["quotes"]
assert quotes and quotes[0]["checked_by"] == "本人" and not labels.check(quotes)
print("ok")
