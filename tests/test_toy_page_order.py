"""玩具の頁（つくる）の節の並び（本人の言葉 11-08「つくるのページ、これまでの復元、仮説、組み立てを立体で見る、たとえと関連する事柄、型紙の順で。
考えを話す、作ってる途中で困ったら、は同じ窓で。」）。

見る線:
1. 頭（原画と題と つくる）の後の節は、これまでの復元 → 仮説 → 組み立てを立体で見る → たとえと、関連する事柄 → 型紙の窓 の順（版の歩みは型紙の窓のすぐ後のまま）
2. 仮説の札は型紙の窓の中から出て、仮説の節（見出し「仮説」）にある。断り（型紙は AI が考えた仮説）と輪の図も一緒に移り、断り → 輪の図 → 札 の順（型紙の窓には紙が残る）
3. 「考えを話す」と「作っている途中で困ったら」は同じ節（#hanasu）の中。#tsukuru の錨（作りながら見る頁の「← 玩具」の行き先）は同じ節の中に残る
4. 型紙の窓の後は、考えを話す（と困ったら）→ 組み方 → できたら、のこそう。のこそう の後ろに これまでの復元 は無い（上へ移した）
5. 刷る前も刷った後も同じ並び（刷った後は聞く口が同じ節に出る）
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses  # noqa: E402
from web.play_server import print_latest  # noqa: E402
from web.toy import MINNA_HEAD, toy_page  # noqa: E402

TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")


def sections(page):
    """頭の後の節（section）を、id と中身で並びの順に。"""
    body = page[page.index("</section>", page.index('<section class="hero">')):]
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'<section [^>]*id="([^"]+)"', body)]
    return [(name, body[a:(starts[i + 1][0] if i + 1 < len(starts) else len(body))]) for i, (a, name) in enumerate(starts)]


for printed in (False, True):
    for sid in TOYS:
        if printed:
            assert print_latest(sid, hypotheses.sheet_of(sid)["id"]) is not None, (sid, "紙を作れない")
        page = toy_page(sid)
        secs = sections(page)
        names = [n for n, _ in secs]
        body = dict(secs)
        # 1. 並び
        plate_sec = next(n for n, s in secs if 'class="plates"' in s)
        want = ["minna", plate_sec, "kasetsu", "tatoe", "win"]
        assert all(n in names for n in want), (sid, printed, names)
        assert [names.index(n) for n in want] == sorted(names.index(n) for n in want), (sid, printed, "並びが 復元 → 仮説 → 立体 → たとえ → 型紙 でない", names)
        assert names.index("minna") == 0, (sid, printed, "頭のすぐ後が これまでの復元 でない", names)
        assert f"<h2>{MINNA_HEAD}</h2>" in body["minna"] and "組み立てを立体で見る" in body["kasetsu"] and "たとえと、関連する事柄" in body["tatoe"]
        if "ban-ayumi" in names:
            assert names.index("ban-ayumi") == names.index("win") + 1, (sid, printed, "版の歩みが型紙の窓のすぐ後でない")
        # 2. 仮説の札は仮説の節
        assert plate_sec != "win" and 'class="plates"' not in body["win"], (sid, printed, "仮説の札が型紙の窓に残った")
        # 断り（型紙は AI が考えた仮説）と輪の図は札と一緒に仮説の節へ（断りは札より前・本人の言葉 11-05）。型紙の窓には紙が残る
        ps = body[plate_sec]
        assert ps.index('id="premise"') < ps.index('id="wa"') < ps.index('class="plates"'), (sid, printed, "仮説の節が 断り → 輪の図 → 札 でない")
        # 仮説の節の見出しは「仮説」（本人の答え 11-08「3 つともよい。」で置く。字は前からある字）
        assert ps.index("<h2>仮説</h2>") < ps.index('id="premise"'), (sid, printed, "仮説の節の見出しが無い")
        assert "<h2>型紙の窓</h2>" in body["win"] and 'id="premise"' not in body["win"], (sid, printed)
        # 3. 考えを話す と 困ったら は同じ節
        assert "<h2>考えを話す</h2>" in body["hanasu"] and 'id="tsukuru"' in body["hanasu"], (sid, printed)
        assert "tsukuru" not in names, (sid, printed, "困ったらの節が別の節のまま")
        if printed:
            assert 'id="ask"' in body["hanasu"] and "作っている途中で困ったら" in body["hanasu"], (sid, "聞く口が考えを話すと同じ節に無い")
            assert body["hanasu"].index("<h2>考えを話す</h2>") < body["hanasu"].index("作っている途中で困ったら"), sid
        else:
            assert 'id="ask"' not in page, (sid, "刷る前に聞く口が出た")
        # 4. 型紙の窓の後
        after = names[names.index("win"):]
        assert after.index("hanasu") < after.index("kumikata") < after.index("kiroku"), (sid, printed, after)
        assert "minna" not in after, (sid, printed, "これまでの復元 が下に残った")
print("ok 玩具の頁の節の並び: これまでの復元 → 仮説 → 組み立てを立体で見る → たとえと関連する事柄 → 型紙。考えを話す と 困ったら は同じ節")
