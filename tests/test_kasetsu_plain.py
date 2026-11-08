"""つくるの頁と刷る紙で、仮説を印なしの「仮説」と書く（本人の言葉 11-08「つくる、のところ仮説Cとか仮説Aとかはなしで仮説、と表記する」）。

見る事:
1. つくるの頁（玩具の頁・組み立て・作りながら見る・手帖・重ねる）の見える字（字の節と alt・aria-label など）に、仮説の印の形
   「仮説 A」「A の紙」が無い。玩具の頁の仮説の札に大きな印の字（div.letter）が無い。呼び名の「仮説」は出る
2. 英語で開いた同じ頁に「Idea A」の形が無い（訳の表の値も印を外した。表に無い字は tests/test_en_all が止める）
3. 刷る紙の題（hypotheses.print_sheet）と 3D の机の上の紙の題に印が無い。前の組の紙は前の題のまま（tests/test_floor_pin が控えで見る）
4. 印そのものは記録の番号として残る（hypotheses.letter・仮説の id は替えない。内部の印や記録の番号は替えない、統括の割り振り）
"""
import html
import os
import pathlib
import re
import sys
import tempfile
import threading
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import assembly, hypotheses  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web.play_server import serve  # noqa: E402

G, T, PLAIN = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R", "NDL-1187053-R0000020-R"  # 御来迎・虎・風車（見本の札があった試作の玩具）
MARK = re.compile(r"仮説 ?[A-ZＡ-Ｚ](?![A-Za-z0-9])|(?<![A-Za-z0-9])[A-Z] の紙")
EN_MARK = re.compile(r"\b(?:Idea|Guess|Hypothesis) [A-Z]\b|\b[Ss]heet [A-Z]\b")


def visible(page):
    """見える字（字の節と、読み上げ・代わりの字の属性）。台本と CSS の中は見ない。"""
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    out = [html.unescape(t) for t in re.findall(r">([^<]+)<", page)]
    out += [html.unescape(v) for v in re.findall(r'(?:alt|title|aria-label|placeholder)="([^"]*)"', page)]
    return [" ".join(t.split()) for t in out if t.strip()]


srv = serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"


def get(path, cookie="utsushi_lang=ja"):
    req = urllib.request.Request(base + path, headers={"Cookie": cookie})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read().decode("utf-8")


try:
    for sid in (G, T, PLAIN):
        body = urllib.parse.urlencode({"hypothesis": hypotheses.sheet_of(sid)["id"]}).encode()
        urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{sid}/print", data=body, headers={"Origin": base}), timeout=300).read()
    # 1・2. つくるの頁の見える字
    for sid in (G, T, PLAIN):
        # 重ねる頁（/kasane）は組み立ての 3D がある必須 2 種だけ（ほかの玩具は 404）
        for path in (f"/toy/{sid}", f"/toy/{sid}/kumitate", f"/toy/{sid}/tsukuru", f"/toy/{sid}/techo") + ((f"/toy/{sid}/kasane",) if sid != PLAIN else ()):
            page = get(path)
            left = [t for t in visible(page) if MARK.search(t)]
            assert not left, ("仮説の印が見える字に残る", path, left[:3])
            assert 'class="letter"' not in page, ("仮説の札の大きな印の字", path)
            en = get(path, "utsushi_lang=en")
            left = [t for t in visible(en) if EN_MARK.search(t)]
            assert not left, ("英語の頁に仮説の印が残る", path, left[:3])
        assert "仮説「" in get(f"/toy/{sid}") and "仮説の紙" in get(f"/toy/{sid}/tsukuru"), sid
    # 3. 刷った紙の題（今の組の型紙の SVG の頭の字）
    for sid in (G, T):
        data = hypotheses.load(sid)
        found = sorted(pathlib.Path(os.environ["OMOCHAE_DATA"]).rglob(f"{hypotheses.sheet_of(sid)['id']}_v1.svg"))
        found = [p for p in found if sid in str(p) and "/.tmp" not in str(p)]
        assert found, ("刷った紙が無い", sid)
        head = found[0].read_text(encoding="utf-8")
        assert f"{data['toy']} 型紙 仮説「{hypotheses.sheet_of(sid)['name']}」" in head and not MARK.search(head), (sid, MARK.findall(head)[:3])
    # 見本の札（デモ用の作り物）は外した（本人の言葉 11-08「見本の記録をワークショップのデータで作成して欲しい。」）。
    # 見本の札があった玩具の頁にも、仮説の印が見える字に残らない
    page = get(f"/toy/{PLAIN}")
    assert 'class="item is-sample"' not in page and not [t for t in visible(page) if MARK.search(t)]
finally:
    srv.shutdown()
# 4. 印は記録の番号として残る（呼び名の部品は 1 か所）
assert hypotheses.SHOWN == "仮説" and hypotheses.letter(hypotheses.sheet_of(G)) == hypotheses.sheet_of(G)["id"].split("-")[1]
assert hypotheses.shown_name(hypotheses.sheet_of(G)) == f"仮説「{hypotheses.sheet_of(G)['name']}」"

# 3. 3D の机の上の紙の題（今の組）
for sid in (G, T):
    data = hypotheses.load(sid)
    h = hypotheses.sheet_of(sid)
    tpl = TEMPLATES[data.get("template", "slider_fan")]
    title = assembly._sheet_title(data, tpl, h["params"] or {}, h)
    assert title == f"{data['toy']} 型紙 仮説 {hypotheses.paper_label(data, 1)}" and not MARK.search(title), title

print("ok つくるの頁と刷る紙は印なしの「仮説」: 玩具の頁・組み立て・作りながら見る・手帖・重ねる（日本語と英語）・紙の題・3D の紙の題・見本の札があった頁。印は記録の番号として残る")
