"""試作の層（web.tameshi。入口と玩具の頁ひとつの別案、11-07）の試験。
なぜ: 本線を触らない層である事（道は OMOCHAE_TAMESHI=1 の時だけ開く）、頁の文が本人の言葉と今の頁の字だけである事、
押した時だけ動く事（見えた時に起こす仕掛けが無い）を、手で見なくても崩れないように固定する。"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("OMOCHAE_TAMESHI", None)

from web import play_server, tameshi  # noqa: E402

G, T, PLAIN = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R", "NDL-1187053-R0000009-L-2"

# 1. 本人の言葉は言い換えていない（grove の standing-decisions の本人の言葉の文そのもの。ここに元の文を書いて、字が 1 つでも変われば落とす）
SOURCE = (
    "「サイトの根幹は、ユーザーによりその場で自己改善する進化するウェブページ、型紙生成システム。これを最初に伝える必要がある。」",
    "「ユーザーには、絵が立体のおもちゃとなって自分の手のひらで遊べるようになることを体験してもらいたい。」",
    "「教育の原形、まねぶ、自らあそぶ、トライアンドエラー、つくってこわす、おそわる、教師は人間いがいに自分も含めた自然、周囲」",
    "「ワークショップ2回や型紙の試作を繰り返し、型紙のが改善されたことは面白いと思う。バージョンをサイトで明示したい。デモ動画でもこのことをはなして、型紙はもちろんエンジンも改善する仕組みになっていることを言いたいし示したい」",
    "「原画→型紙→3D という順番で、3D で見れる作成手順が空間に表示されるのを見ながら作っていく。」",
)
for key, w in tameshi.WORDS.items():
    assert any(w in s for s in SOURCE), (key, "本人の言葉の文の中に、そのままある事")
    assert w.endswith("。") or key == "genkei", (key, "文の単位で抜く")
assert "これを最初に伝える必要がある" not in "".join(tameshi.WORDS.values()), "作る側への指示の文は出さない"

# 2. 道は層のスイッチの時だけ開く
srv = play_server.serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"


def code(path):
    try:
        with urllib.request.urlopen(base + path, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


for p in ("/tameshi", f"/tameshi/toy/{G}", f"/tameshi/up/{G}", "/tameshi/guide.png"):
    assert code(p)[0] == 404, (p, "スイッチが無い時は閉じている")
os.environ["OMOCHAE_TAMESHI"] = "1"
try:
    st, top = code("/tameshi")
    assert st == 200
    # 根幹の 1 文が最初の画面に、絵は全部の玩具、押す所は button（押した時だけ開く）
    hall = top.split('class="ts-hall"', 1)[1].split("</section>", 1)[0]
    assert tameshi.WORDS["konkan"] in hall and tameshi.WHO in hall and f'href="#narabi">{tameshi.GO}<' in hall
    assert top.count('<button type="button" data-sid="') == len(play_server.sources())
    assert "IntersectionObserver" not in top and "whileInView" not in top
    for sid in (G, T, PLAIN):
        st, up = code(f"/tameshi/up/{sid}")
        assert st == 200 and 'class="ts-rise"' in up and f'href="/tameshi/toy/{sid}">{tameshi.MAKE}<' in up, sid
        st, page = code(f"/tameshi/toy/{sid}")
        assert st == 200, sid
        at = [page.index(f'<p class="no">{s}</p>') for s in tameshi.STEPS]
        assert at == sorted(at), (sid, "原画 → 型紙 → 3D の順")
        assert f'href="/toy/{sid}/kasane">{tameshi.KASANE}<' in page and "型紙の版 " in page
    # 道の外は閉じる
    for p in ("/tameshi/toy/NDL-0000000-R0000000-L", "/tameshi/ban/../x.png", "/tameshi/nope"):
        assert code(p)[0] == 404, p
finally:
    os.environ.pop("OMOCHAE_TAMESHI", None)
# 3. 本線の頁は変わらない（入口と玩具の頁に試作の字が出ない）
st, main_top = code("/")
assert st == 200 and "ts-hall" not in main_top and tameshi.WORDS["konkan"] not in main_top
srv.shutdown()
print("ok 試作の層はスイッチの時だけ開き、字は本人の言葉と今の頁の字だけ")
