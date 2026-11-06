"""保護者の方へ、ファシリテーターの方への頁（/otona）の試験。本物の API は呼ばない。

本人の決定（11-06）「3 点とも推し A。文はこの形で頁へ」と、その訂正（同じ日、6 点とも推し A）。全文は docs/process/research/36-road-and-audience.md の「採られた文」で、一字も変えない。
見る事:
1. 2 つの皮で開き、合言葉なしの場でも開く。序の頁と頁の足から来られる
2. 採られた文が一字も変わらず、この順で出る。中身に、採られた文の外の字が無い（節へ飛ぶ道と、今ある釦の字を除く）
3. 文が書いた約束の裏付けが、今のコードにある（消えたら、ここで気づく）
"""
import html.parser
import inspect
import os
import re
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api import ask, observe  # noqa: E402
from omochae import media_review, records, talk_log  # noqa: E402
from web import about, otona, skin, wording  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402
from web.play_server import serve  # noqa: E402

TITLE = "保護者の方へ、ファシリテーターの方へ"
# 本人が採った文。一字でも変わったら落ちるように、ここに決定の文を書く
ADOPTED = (
    ("1 このサイトでする事",
     ("江戸時代の絵本に、絵と歌だけが残ったおもちゃがあります。どう動いたかは、分かっていません。このサイトでは、そのおもちゃを紙で作って、動きを自分で確かめます。",
      "型紙は、AI が考えた「たたき台」です。正解ではありません。うまく動かない時は、作る人が工夫して直します。動かなくても、失敗ではありません。",
      "子どもから大人まで、どなたでも使えます。")),
    ("2 声と字のあつかい",
     ("声は録音しません。このサイトは声を受け取りません。",
      "声を字にするのは、ブラウザ（ネットを見るアプリ）です。そのとき、声がブラウザの会社に送られることがあります。",
      "聞くのは、ボタンを押した後だけです。「はじめる」を押すと、「つぎ」「もどる」などの操作の言葉を聞きます。質問は「こまった」の後の 1 つだけ受けます。工夫は、マイクを押してから話した事だけを受けます。「こまった」やマイクを押していない間は、まわりの話し声は残りません。押した後は、近くの人の声が字になる事があります。",
      "残るのは字だけです。字は「のこす」を押した時に残ります。残す前に、読んで直せます。",
      "名前・学校の名前・住所・電話番号・メールは、言ったり書いたりしないでください。名乗りや連絡先の形の言葉は、機械が落とします。ただし、全部を見分ける事はできません。",
      "残した工夫の字は、ほかの人も読めます。",
      "質問の字は、案内をよくするために残します。質問に答える時に AI（Claude）に送るのは、質問の字だけです。",
      "残した字は、AI（Claude）が型紙をよくする案を考えるのにも使います。")),
    ("3 写真と動画",
     ("写してよいのは、作った物と、大人の手元だけです。顔、名札、子どもは写さないでください。",
      "写真と動画は、いつ・どこでとったかなどの情報を消してから残します。動画の音は消します。",
      "のせた写真と動画は、人が確かめてから、みんなの頁に出します。確かめる前は、のせた人の画面にだけ出ます。",
      "人や声が入っていた時は、頁には出しません。")),
    ("4 取り下げ（あとから消す）",
     ("残した記録、写真、話した字は、あとから消せます。",
      "消したい時は、場の進行者に、記録の番号を伝えてください。番号は、手帖の記録の頁に出ています（R-0003 のような形です）。",
      "合言葉なしで開く公開の場には、進行者がいません。そこで残した字は、ほかの人の頁には出しません。消してほしい時の伝え先は、まだありません。",
      "記録ごと消す事も、写真だけ、話した字だけを消す事もできます。",
      "型紙を直す理由に使った記録は、記録そのものは残ります。その時も、写真と動画と、話した字は消せます。")),
    ("5 AI（Claude）の役目",
     ("型紙は、AI が絵と歌から考えた案を、決まった検査に通して作っています。",
      "作っている途中の質問に答えます。答えるのは、言葉の意味と手順です。動く仕組みの答えは言いません。確かめるのは作る人です。",
      "記録と、作った人の説明の後で、AI が読みと次の案を出します。採るかどうかは、人が決めます。",
      "「動画を見てもらう」を押した時は、動画から取り出した 3 枚の絵を AI（Claude）が見ます。声は渡しません。",
      "AI は、点数や順位を付けません。",
      "AI を使えない場でも、紙で作って、記録を残せます。")),
    ("6 場の進め方（ファシリテーターの方へ）",
     ("進行する人は、答えを持つ人ではありません。昔の作り方は残っていないので、いっしょに分からない人として立ちます。",
      "はじめに 3 つ約束します。「動かなくても、それは紙の返事です」「壊してかまいません。自分で作った物は直せます」「となりの作り方は、見てよい、まねてよい」。",
      "言う事は、見えた事です（「ここを 3 回折り直したね」）。言わない事は、評価（いいね・おしい・正解）、仕組みの答え、人とのくらべです。",
      "手が止まった人には、まず 1 分見ます。次に、見えた事を返します。問いを小さくします（「今、動かないのはどこ？」）。材料を 1 つ渡します。",
      "場の前に、合言葉付きのリンクで開きます。型紙を 1 度出しておきます。刷った紙の物差しが 10cm かを測ります。自分でも 1 つ作って、詰まる所を知っておきます（答えとしては見せません）。")),
)
BUTTONS = ("おもちゃを選ぶ", "入口へ戻る")


class Text(html.parser.HTMLParser):
    """<main> の中の字を順に集める。"""

    def __init__(self):
        super().__init__()
        self.out, self.inside = [], 0

    def handle_starttag(self, tag, attrs):
        self.inside += tag == "main"

    def handle_endtag(self, tag):
        self.inside -= tag == "main"

    def handle_data(self, data):
        if self.inside and data.strip():
            self.out.append(data.strip())


def main_text(page):
    t = Text()
    t.feed(page)
    return "".join(t.out)




def recorded():
    """決定の記録（research/36 の「採られた文」）から、見出しと文を読む。頁の字と記録の字がずれたら落とすため。"""
    doc = (ROOT / "docs/process/research/36-road-and-audience.md").read_text(encoding="utf-8")
    body = doc.split("## 採られた文: 保護者の方へ、ファシリテーターの方へ（本人の決定、11-06）", 1)[1]
    body = body.split(f"**{TITLE}**", 1)[1].split("この文と作りの対応:", 1)[0]
    out = []
    for line in filter(None, (x.rstrip() for x in body.splitlines())):
        m = re.fullmatch(r"\*\*(\d .+)\*\*", line)
        if m:
            out.append((m.group(1), []))
        else:
            out[-1][1].append(line.removeprefix("- "))
    return tuple((h, tuple(lines)) for h, lines in out)


# 採られた後に外した行（11-06 夜の決め直し。公開の場でも写真と動画を上げられる形にしたため）。記録の採られた文の節は書き換えず、
# 節の末にこの行を外した事を書いた。記録から外した行を除いた字が、頁と一字も違わない事を見る
REMOVED = {"3 写真と動画": ("合言葉なしで開く公開の場では、写真と動画はのせられません。",)}
_r36 = (ROOT / "docs/process/research/36-road-and-audience.md").read_text(encoding="utf-8")
assert "3 の 5 行目「合言葉なしで開く公開の場では、写真と動画はのせられません。」は、11-06 夜の決め直しで外した" in _r36, "外した事の記録が無い"
kept = tuple((h, tuple(x for x in lines if x not in REMOVED.get(h, ()))) for h, lines in recorded())
assert all(set(REMOVED[h]) <= set(lines) for h, lines in recorded() if h in REMOVED), "外した行が採られた文に無い（記録が変わった）"
assert kept == ADOPTED, "決定の記録の字と、この試験の字が違う。記録が直ったなら、頁と試験を記録から抜き直す"
heads = [h for h, _ in ADOPTED]
assert len(heads) == 6 and sum(len(lines) for _, lines in ADOPTED) == 31, "題と見出しと合わせて 38 行（採られた 39 行から 1 行を外した）"
expected = TITLE + "".join(heads) + "".join(h + "".join(lines) for h, lines in ADOPTED) + "".join(BUTTONS)

# 1. 2 つの皮で、採られた文のまま（2 も同じ所で見る）
for look in ("tenji", "zine"):
    page = otona.page(look)
    assert f"<title>{TITLE}" in page, look
    assert main_text(page) == expected, (look, "採られた文と字が違う、または外の字がある")
    assert page.count('<section class="sec" id=') == 6 and page.count('<a href="#') == 6, look
    assert 'href="/toys"' in page and 'href="/"' in page, look

# どこから来るか。帯に「よむ」が入る時に置き場を合わせる
assert 'href="/otona"' in about.page("tenji"), "序の頁から来られる"
assert 'href="/otona"' in skin.shell("題", "<p>中身</p>"), "どの頁の足からも来られる"
assert 'href="/otona"' not in skin.shell("title", "<p>body</p>", lang="en", foot='<p class="foot">credit</p>'), "英語の頁の足は英語のまま（英語の文はまだ無い）"


def fetch(server, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}", timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


for public_open in (False, True):
    server = serve(0, public_open=public_open)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        status, got = fetch(server, "/otona")
        assert status == 200 and main_text(got) == expected, public_open
        # 前はここで、3 の 5 行目「合言葉なしで開く公開の場では、写真と動画はのせられません」の裏付けとして受け口の 403 を見ていた。
        # 本人の決定（11-06）で公開の場でも上げられる形にし、その行は外した。公開の場で受けて、確かめた物を出す形は test_public_open が見る
    finally:
        server.shutdown()
        server.server_close()

# 3. 約束の裏付け。消えたら、文を本人に確かめ直す
assert set(inspect.signature(records.withdraw).parameters) >= {"media_only", "talk_only"}, "記録ごと・写真だけ・話した字だけを消せる"
assert talk_log.drop_for_record, "記録を消すと話した字も消える"
assert "used_by(rid)" in inspect.getsource(records.withdraw), "型紙を直す理由に使った記録は、記録そのものは残る"
assert re.fullmatch(r"記録の番号 R-0003", wording.record_no("R-0003")), "番号は手帖の記録の頁に、この形で出る"
assert media_review.SHOWS == ("object", "people"), "物だけ / 人や声が入る、を人が確かめる"
assert talk_log.blocked("山田小学校の田中です") and talk_log.blocked("電話は 090-1234-5678 です"), "名乗りや連絡先の形の言葉は機械が落とす"
assert not talk_log.blocked("田中さんに教わった"), "全部を見分ける事はできない、と書く根拠。ここが変わったら文を確かめ直す"
assert ask.REFUSE and ask.MECHANISM_WORDS, "動く仕組みの答えは言わない"
assert "この 3 コマ" in inspect.getsource(observe) and "声は渡さない" in inspect.getsource(observe), "動画を見てもらう時は 3 枚の絵だけを渡す"
print("ok 大人の方への頁は採られた文のままで、2 つの皮と合言葉なしの場で開き、約束の裏付けがある")
