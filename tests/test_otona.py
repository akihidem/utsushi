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
from web import about, otona, play_server, skin, techo_site, wording  # noqa: E402
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
     ("話す口では、「話す」を押して話した間の声を録り、のこすで承認した時に受け取ります。声は、この機械の中で字にしてから消します（字にできない時も、3 日で消します）。声は AI（Claude）には送りません。",
      "声を字にするのは、ブラウザ（ネットを見るアプリ）です。そのとき、声がブラウザの会社に送られることがあります。",
      "聞くのは、ボタンを押した後だけです。「はじめる」を押すと、「つぎ」「もどる」などの操作の言葉を聞きます。質問は「こまった」の後の 1 つだけ受けます。工夫は、マイクを押してから話した事だけを受けます。「こまった」やマイクを押していない間は、まわりの話し声は残りません。押した後は、近くの人の声が字になる事があります。作業の頁の「聞く」だけは、押した間の声を受けて、質問として答えます。",
      "残るのは字だけです。字は「のこす」を押した時に残ります。残す前に、読んで直せます。",
      "名前・学校の名前・住所・電話番号・メールは、言ったり書いたりしないでください。名乗りや連絡先の形の言葉は、機械が落とします。ただし、全部を見分ける事はできません。",
      "残した工夫の字は、このサイトを作っている人だけが読みます。ほかの人の頁には、AI（Claude）が短くまとめた字だけを出します。",
      "手帖の「こまった」など、字の欄で聞いた質問の字は、案内をよくするために残します。答える時に AI（Claude）に送るのは、その字だけです。作業の頁の「聞く」で聞いた時は、聞いた字と手元の写真（3 枚まで）を AI（Claude）に送って答え、字も写真も残しません。",
      "残した字は、AI（Claude）が型紙をよくする案を考えるのにも使います。")),
    ("3 写真と動画",
     ("写してよいのは、作った物と、大人の手元だけです。顔、名札、子どもは写さないでください。",
      "写真と動画は、いつ・どこでとったかなどの情報を消してから残します。動画の声は、この機械の中で字にしてから消します。字にできない時も、3 日で消します。字は、このサイトを作っている人だけが読みます。子どもの声は入れないでください。",
      "のせた写真と動画は、人が確かめてから、みんなの頁に出します。確かめる前は、のせた人の画面にだけ出ます。",
      "人や声が入っていた時は、頁には出しません。",
      "作業の頁のカメラは、録りません。「聞く」を押した時だけ、手元の写真を 3 枚まで撮って AI（Claude）に送り、答えた後に消します。写真を撮るのは後ろのカメラの時だけで、HMD の頁では撮りません。")),
    ("4 取り下げ（あとから消す）",
     ("残した記録、写真、話した字は、あとから消せます。",
      "消したい時は、場の進行者に、記録の番号を伝えてください。番号は、手帖の記録の頁に出ています（R-0003 のような形です）。",
      "合言葉なしで開く公開の場には、進行者がいません。そこで残した字は、ほかの人の頁には出しません。消してほしい時の伝え先は、まだありません。",
      "記録ごと消す事も、写真だけ、話した字だけを消す事もできます。",
      "型紙を直す理由に使った記録は、記録そのものは残ります。その時も、写真と動画と、話した字は消せます。",
      "公開の場では、上げた画面の「取り下げる」で消せます。",
      "押せるのは、上げてから2時間の間と、次の記録を残すまでです。")),
    ("5 AI（Claude）の役目",
     ("型紙は、AI が絵と歌から考えた案を、決まった検査に通して作っています。",
      "作っている途中の質問に答えます。答えるのは、言葉の意味と手順です。動く仕組みの答えは言いません。確かめるのは作る人です。",
      "記録と、作った人の説明の後で、AI が読みと次の案を出します。採るかどうかは、人が決めます。",
      "「動画を見てもらう」を押した時は、動画から取り出した 3 枚の絵を AI（Claude）が見ます。声は渡しません。作業の頁で「聞く」を押した時は、聞いた字と手元の写真（3 枚まで）を、その場で AI（Claude・Anthropic の API）に送って答えます。答えた後は、このサイトの側では消します。合言葉なしで開く公開の場では、聞けません。",
      "AI は、点数や順位を付けません。",
      "AI を使えない場でも、紙で作って、記録を残せます。")),
    ("6 場の進め方（ファシリテーターの方へ）",
     ("進行する人は、答えを持つ人ではありません。昔の作り方は残っていないので、いっしょに分からない人として立ちます。",
      "はじめに 3 つ約束します。「動かなくても、それは紙の返事です」「壊してかまいません。自分で作った物は直せます」「となりの作り方は、見てよい、まねてよい」。",
      "言う事は、見えた事です（「ここを 3 回折り直したね」）。言わない事は、評価（いいね・おしい・正解）、仕組みの答え、人とのくらべです。",
      "手が止まった人には、まず 1 分見ます。次に、見えた事を返します。問いを小さくします（「今、動かないのはどこ？」）。材料を 1 つ渡します。",
      "場の前に、合言葉付きのリンクで開きます。型紙を 1 度出しておきます。刷った紙の物差しが 10cm かを測ります。自分でも 1 つ作って、詰まる所を知っておきます（答えとしては見せません）。")),
)
BUTTONS = ("入口へ戻る",)  # 前は「おもちゃを選ぶ」と 2 つで、同じ所へ行く対だった（本人のサイト体験レビュー 11-07 の 3「同じ物が何回も出る」。/toys は入口へ送るので、/toys へ向く道は置かない）


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


# 採られた後に外した行と替えた行（どちらも 11-06 夜の決め直し）。記録の採られた文の節は書き換えず、節の末に外した事と替えた事を書いた。
# 外した行: 公開の場でも写真と動画を上げられる形にしたため。替えた行: 窓口の決定・推しの字（話した字は頁に出さない決定、J-034 に合わせた）。
# 記録から外した行を除き、替えた行を当てた字が、頁と一字も違わない事を見る
REMOVED = {"3 写真と動画": ("合言葉なしで開く公開の場では、写真と動画はのせられません。",)}
# 11-08: 2 の 1 行目と 3 の 2 行目を、上げた動画の声を字にしてから消す形（omochae.voice_text）に合わせた案に替えた（本人の確かめ待ち・research/36 の節の末に記録）
# 11-08（2 回目）: 2 の 1 行目と 5 の 4 行目を、押して話した間の声と作業の頁のカメラの区切りを承認の時に送る形（本人 415・「公開デモでも声も録る。」・web.clips）に
# 合わせた案に替え、3 の最後に作業の頁のカメラの 1 行を足した（本人の確かめ待ち・research/36 の節の末に記録）
# 11-08（3 回目）: 作業の頁を聞くための経路にした（本人 539）ので、2 の 3 行目の最後に 1 文を足し、2 の 7 行目・3 の最後の行・5 の 4 行目の 3 つ目の文を替えた
# （本人の答え 11-08「字の替え 11 か所も、カメラの区切りを外す事も、推しのとおり。」・research/36 の節の末に記録）
REPLACED = {"2 声と字のあつかい": {"聞くのは、ボタンを押した後だけです。「はじめる」を押すと、「つぎ」「もどる」などの操作の言葉を聞きます。質問は「こまった」の後の 1 つだけ受けます。工夫は、マイクを押してから話した事だけを受けます。「こまった」やマイクを押していない間は、まわりの話し声は残りません。押した後は、近くの人の声が字になる事があります。": "聞くのは、ボタンを押した後だけです。「はじめる」を押すと、「つぎ」「もどる」などの操作の言葉を聞きます。質問は「こまった」の後の 1 つだけ受けます。工夫は、マイクを押してから話した事だけを受けます。「こまった」やマイクを押していない間は、まわりの話し声は残りません。押した後は、近くの人の声が字になる事があります。作業の頁の「聞く」だけは、押した間の声を受けて、質問として答えます。", "質問の字は、案内をよくするために残します。質問に答える時に AI（Claude）に送るのは、質問の字だけです。": "手帖の「こまった」など、字の欄で聞いた質問の字は、案内をよくするために残します。答える時に AI（Claude）に送るのは、その字だけです。作業の頁の「聞く」で聞いた時は、聞いた字と手元の写真（3 枚まで）を AI（Claude）に送って答え、字も写真も残しません。", "残した工夫の字は、ほかの人も読めます。": "残した工夫の字は、このサイトを作っている人だけが読みます。ほかの人の頁には、AI（Claude）が短くまとめた字だけを出します。", "声は録音しません。このサイトは声を受け取りません。": "話す口では、「話す」を押して話した間の声を録り、のこすで承認した時に受け取ります。声は、この機械の中で字にしてから消します（字にできない時も、3 日で消します）。声は AI（Claude）には送りません。"}, "5 AI（Claude）の役目": {"「動画を見てもらう」を押した時は、動画から取り出した 3 枚の絵を AI（Claude）が見ます。声は渡しません。": "「動画を見てもらう」を押した時は、動画から取り出した 3 枚の絵を AI（Claude）が見ます。声は渡しません。作業の頁で「聞く」を押した時は、聞いた字と手元の写真（3 枚まで）を、その場で AI（Claude・Anthropic の API）に送って答えます。答えた後は、このサイトの側では消します。合言葉なしで開く公開の場では、聞けません。"}, "3 写真と動画": {"写真と動画は、いつ・どこでとったかなどの情報を消してから残します。動画の音は消します。": "写真と動画は、いつ・どこでとったかなどの情報を消してから残します。動画の声は、この機械の中で字にしてから消します。字にできない時も、3 日で消します。字は、このサイトを作っている人だけが読みます。子どもの声は入れないでください。"}}
# 採られた後に足した行（どちらも決め直し。1 行目は窓口の決定 11-06 夜・案 A、2 行目は本人の決定 11-06 夜）。公開の場では、上げた画面にだけ
# 「取り下げる」の釦を置き、押せる間（写真の鍵の期限と、次の記録で鍵が外れる事）を言う。節の末に足す
ADDED = {"3 写真と動画": ("作業の頁のカメラは、録りません。「聞く」を押した時だけ、手元の写真を 3 枚まで撮って AI（Claude）に送り、答えた後に消します。写真を撮るのは後ろのカメラの時だけで、HMD の頁では撮りません。",), "4 取り下げ（あとから消す）": ("公開の場では、上げた画面の「取り下げる」で消せます。", "押せるのは、上げてから2時間の間と、次の記録を残すまでです。")}
_r36 = (ROOT / "docs/process/research/36-road-and-audience.md").read_text(encoding="utf-8")
assert "3 の 5 行目「合言葉なしで開く公開の場では、写真と動画はのせられません。」は、11-06 夜の決め直しで外した" in _r36, "外した事の記録が無い"
assert "2 の 6 行目「残した工夫の字は、ほかの人も読めます。」は、11-06 夜の決め直しで「残した工夫の字は、このサイトを作っている人だけが読みます。ほかの人の頁には、AI（Claude）が短くまとめた字だけを出します。」に替えた" in _r36, "替えた事の記録が無い"
assert "4 の最後に「公開の場では、上げた画面の「取り下げる」で消せます。」を、11-06 夜の決め直しで足した" in _r36, "足した事の記録が無い（1 行目）"
assert "2 の 1 行目「声は録音しません。このサイトは声を受け取りません。」と、3 の 2 行目「" in _r36 and "11-08 に、上げた動画の声をこの機械の中で字にしてから消す形" in _r36, "11-08 に替えた事の記録が無い"
assert "11-08 の 2 回目に、押して話した間の声と作業の頁のカメラの区切りを、のこすで承認した時に送る形" in _r36, "11-08 の 2 回目に替えた事の記録が無い"
assert "11-08 の 3 回目に、作業の頁を聞くための経路にした" in _r36, "11-08 の 3 回目に替えた事の記録が無い"
assert "その次の行に「押せるのは、上げてから2時間の間と、次の記録を残すまでです。」を、本人の決定" in _r36, "足した事の記録が無い（2 行目）"
assert all(set(REMOVED[h]) <= set(lines) for h, lines in recorded() if h in REMOVED), "外した行が採られた文に無い（記録が変わった）"
assert all(set(REPLACED[h]) <= set(lines) for h, lines in recorded() if h in REPLACED), "替えた行が採られた文に無い（記録が変わった）"
kept = tuple((h, tuple(REPLACED.get(h, {}).get(x, x) for x in lines if x not in REMOVED.get(h, ())) + ADDED.get(h, ())) for h, lines in recorded())
assert kept == ADOPTED, "決定の記録の字と、この試験の字が違う。記録が直ったなら、頁と試験を記録から抜き直す"
heads = [h for h, _ in ADOPTED]
assert len(heads) == 6 and sum(len(lines) for _, lines in ADOPTED) == 34, "題と見出しと合わせて 41 行（採られた 39 行から 1 行を外し、行を替え、3 行を足した）"
expected = TITLE + "".join(heads) + "".join(h + "".join(lines) for h, lines in ADOPTED) + "".join(BUTTONS)

# 1. 2 つの皮で、採られた文のまま（2 も同じ所で見る）
for look in ("tenji", "zine"):
    page = otona.page(look)
    assert f"<title>{TITLE}" in page, look
    assert main_text(page) == expected, (look, "採られた文と字が違う、または外の字がある")
    assert page.count('<section class="sec" id=') == 6 and page.count('<a href="#') == 6, look
    assert 'href="/toys"' not in page and 'href="/"' in page, look

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
# 2 の 6 行目の裏付け: 話した字は、記録に結んでいても、ほかの人の頁（手帖の記録の札）に出さない（J-034）。AI がまとめた字の置き場はまだ無いので、何も出ない
from omochae import loop  # noqa: E402
from web import hanasu  # noqa: E402
_rid, _ = records.add({"source_id": "NDL-1187053-R0000005-L", "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
assert talk_log.add("NDL-1187053-R0000005-L", "keep", "話した工夫の見本", record_id=_rid)[1] == []
assert hanasu.kufu_block("NDL-1187053-R0000005-L", loop.record(_rid)) == "", "話した字は、ほかの人の頁に出さない"
assert "used_by(rid)" in inspect.getsource(records.withdraw), "型紙を直す理由に使った記録は、記録そのものは残る"
assert re.fullmatch(r"記録の番号 R-0003", wording.record_no("R-0003")), "番号は手帖の記録の頁に、この形で出る"
assert media_review.SHOWS == ("object", "people"), "物だけ / 人や声が入る、を人が確かめる"
assert talk_log.blocked("山田小学校の田中です") and talk_log.blocked("電話は 090-1234-5678 です"), "名乗りや連絡先の形の言葉は機械が落とす"
assert not talk_log.blocked("田中さんに教わった"), "全部を見分ける事はできない、と書く根拠。ここが変わったら文を確かめ直す"
assert ask.REFUSE and ask.MECHANISM_WORDS, "動く仕組みの答えは言わない"
assert media_review.uploaded_here and "取り下げる</button>" in inspect.getsource(techo_site) and "/media/withdraw" in inspect.getsource(play_server), \
    "公開の場では、上げた画面の「取り下げる」で消せる（押した時の動きは test_photo_owner_only の 7 が見る）"
assert "この 3 コマ" in inspect.getsource(observe) and "声は渡さない" in inspect.getsource(observe), "動画を見てもらう時は 3 枚の絵だけを渡す"
from omochae import voice_text  # noqa: E402
assert voice_text.LIMIT == 72 * 3600 and "voice/" not in inspect.getsource(techo_site.media_of), "動画の声は字にしてから消し、字にできない時も 3 日で消す。頁へ返す道は声を拾わない"
assert '"-an"' in inspect.getsource(techo_site.clean_video), "頁に出す動画からは音を落とす"
print("ok 大人の方への頁は採られた文のままで、2 つの皮と合言葉なしの場で開き、約束の裏付けがある")
