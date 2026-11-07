"""画面に出す言葉の表の通り道（#135）。作る側の字は表を通り、人が書いた文は通らない。本物の API は呼ばない。

なぜ印で見るか: 新しい字は本人の確認の後に入るので、字では見られない。替える関数を印を付ける物に置き換え、印の付き方で通り道だけを見る。
表の中身が変わっても、この試験は変えなくてよい。
"""
import importlib
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
# 本物の記録と版を置き場へ写す。作る側が残した控えの札まで開くため。本物の data/ には書かない
for part in ("records", "loop"):
    shutil.copytree(ROOT / "data" / part, os.path.join(DATA, part))

from web import plain_words, wording  # noqa: E402

keep_note = wording.record_note
# 入口の引用の札は読み込む時に字を作るので、ほかの頁を読み込む前に替える
wording.MAKER = "■"
wording.plain = lambda text: f"▲{text}"
wording.record_no = lambda rid: f"▼{rid}"
wording.record_note = lambda text: f"●{text}" if text else text
wording.sheet_set = lambda name: f"◆{name}"
wording.frame = lambda sid: f"◇{sid}"

from api import ask  # noqa: E402
from omochae import hypotheses, media_review, records  # noqa: E402
from web import techo_site  # noqa: E402
from web.play_server import esc, serve, sources  # noqa: E402

ask._key_present = lambda: False  # 手元に鍵があっても呼ばない

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


# 1 つのブラウザとして動く（記録を残した画面の鍵の cookie を持つ。説明と字を足す口は、その画面にだけ開く）
urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPCookieProcessor()))


def get(path):
    return urllib.request.urlopen(base + path).read().decode()


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    try:
        return urllib.request.urlopen(r).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


data = hypotheses.load(G)
h = hypotheses.sheet_of(G)  # 頁が出すのはたたき台の仮説の欄（御来迎の今の組 goraigo-v14 は H-C）
page = get(f"/toy/{G}")
# 玩具の頁: data/hypotheses の欄。原文の引用の「確かめた人」は、本人の言葉（11-08）「原文の引用確かめた人要らない」で玩具の頁から外した
# （図鑑とくずし字の頁の確かめた人の印は下で見る）
for want in (f"▲{esc(h['how_it_moves'])}", f"試して見る事: ▲{esc(h['to_measure'])}",
             f"〔{esc(h['evidence'][0]['certainty'])}〕▲{esc(h['evidence'][0]['what'])}（▲{esc(h['evidence'][0]['where'])}）",
             f"▲{esc(data['analogy']['written_by'])}"):
    assert want in page, want
assert "原文の引用。確かめた人" not in page, "玩具の頁に原文の引用の確かめた人が残った"
# 作る側が残した試行の控えと、記録の札の番号（字が同じ行が頁の頭の一覧にもあるので、札の形で見る）
# 札の版は記録を刷った組の番号（窓口の決定 11-07・#513 の (a)。R-0001 は 11-04 の前の組の紙なので、その組の番号）
r1 = next(r for r in records.all_records(G) if r["id"] == "R-0001")
assert f"・{hypotheses.label_of(r1.get('sheet_set') or hypotheses.current_set(hypotheses.load(G)), r1.get('sheet_version', 1))}・▼R-0001</p>" in page and "メモ: ●" in page, "記録の札"
# 入口の引用の札、一覧の場所、手帖の組の版と記録の番号
# 入口から章の部屋（歌と札）を外した（本人のサイト体験レビュー 11-07 の 4）。札は玩具の頁の頭（原画と歌）で見る
assert "確かめた人: ■" not in get("/"), "入口に章の札を出さない（札は玩具の頁。test_reader_words が見る）"
others = [s for s in sources() if hypotheses.stage(s) != "必須"]
# 前は図鑑の一覧の場所の字（◇）も見ていた。図鑑の頁は外した（本人の言葉 11-08「図鑑のページ要らない」）
# 手帖の作る頁には、組の版も記録の番号も出さない（作る側の印を学ぶ人に見せない。#87）。記録の番号は、手帖の記録の頁に出る
techo = get(f"/toy/{G}/techo")
assert "goraigo-v10" not in techo and "R-0001" not in techo, "手帖の作る頁"
assert "▼R-0001" in get(f"/toy/{G}/techo/kiroku"), "手帖の記録の頁"
# くずし字を読む頁（前は図鑑の頁も見ていた。図鑑の頁は外した・本人の言葉 11-08）
yomi = post(f"/zukan/{G}/yomi", {"mine": "ためしの読み"})
assert "確かめた人: ▲本人" in yomi, "くずし字の確かめた人"
# 読みが割れた事の文と見出しは、文ごと表を通る
for want in ("▲読みが割れた事", "▲手元の複写", "▲本人が 2026-11-03 に", "▲もう一方の読みは"):
    assert want in yomi, want
# 活字の文と「字が違う所があります」の 2 文は、確かめた読みが活字と同じ字の時は出さない。御来迎は本人の決め（11-08「御来迎の歌の読みは「怠らじ」」）で
# 活字と同じ字になった（前は本人の表記「怠けらじ」で 1 字違い、この 2 文が出ていた）。字が違う時に今までどおり出る事は tests/test_kuzushi_notes.py が見る
assert "▲複写 B の頁" not in yomi and "▲上の「人が確かめた読み」" not in yomi, "活字と同じ字なら、違いの文は出さない"
# 紙を作って記録を残し、次の版まで進めた後の窓・改善の輪・ギャラリー
post(f"/toy/{G}/print", {"hypothesis": GS})
post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた", "impression": "すっと開いた", "note": "本人が折った"})
rid = records.all_records(G)[-1]["id"]
post(f"/record/{rid}/explain", {"text": "折りが固くて戻る", "next_idea": "厚さを変える", "by": "大人"})
post(f"/record/{rid}/next", {"interpretation": "折りが固い", "param": "fold_count", "to": "45", "why": "開きを見る", "by": "大人"})
assert not hypotheses.save_own(G, "糸で引く", "糸で引いて開く", "糸らしい線")[1]  # 前に書かれた仮説の形（頁の書く欄は外した。J-032 の点 2）。文は図鑑に出る
post(f"/toy/{G}/ask", {"hypothesis": GS, "question": "紙の端はどこまで切りますか"})
# 説明を待つ記録と、頭の帯に出る写真（人が確かめた物だけが出る）
post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた"})
waiting = records.all_records(G)[-1]["id"]
folder = techo_site.media_dir(rid)
folder.mkdir(parents=True, exist_ok=True)
(folder / "m1.jpg").write_bytes(b"\xff\xd8\xff")
assert media_review.record(rid, "m1.jpg", "object", "確認者") == []
# 次の版を待つ報告は、説明のある今のたたき台の記録。11-04 の R-0001・R-0002 は前の組の押し方の違う紙なので数えない（窓口の決定 案 A 11-06）
post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない"})
ready = records.all_records(G)[-1]["id"]
post(f"/record/{ready}/explain", {"text": "途中で止まった", "next_idea": "折りを減らす", "by": "大人"})
page = get(f"/toy/{G}?see={GS}&kind=sheet&v=2")
assert f'class="side"' in page and f"▼{rid}" in page.split('class="side"', 1)[1].split("</div></div>", 1)[0], "窓の版の添え書き"
assert f'aria-label="▼{rid}' in page, "頭の帯の写真"
# 輪の節は作る側の様子の頁（本人の答え 11-07 夕の Q5 で、玩具の頁の足の「型紙の改善の輪」は外し、作る側の様子の頁 /loop/<印> へ移した）。札への道は玩具の頁の札（/toy/<印>#R-…）を指す
kz = get(f"/loop/{G}").split('id="kaizen"', 1)[1]
assert f"<a href=/toy/{G}#{rid}>▼{rid}</a>" in kz, "改善の輪: 版のもとの記録"
assert re.search(rf'次の版を待つ報告 \d+ 件: [^（]*<a href="/toy/{G}#{ready}">▼{ready}</a>', kz), "改善の輪: 次の版を待つ報告"
assert f'href="/toy/{G}#R-0001">▼R-0001</a>' not in kz.split("次の版を待つ報告", 1)[1].split("</p>", 1)[0], "前の組の別の形の記録は数えない"
assert re.search(rf'説明を待つ報告 \d+ 件: [^（]*<a href="/toy/{G}#{waiting}">▼{waiting}</a>', kz), "改善の輪: 説明を待つ報告"
gallery = get("/gallery")
# 寄せられた声と職人の言葉の節は、序の頁（よむ）へ移した（本人のサイト体験レビュー 11-07 の言葉 6、直しの設計の D）
yomu = get("/about")
# 職人の言葉の節は もちよる（本人の言葉 11-08「職人の言葉、はもちよるに移動」）。寄せられた声は序の頁のまま
assert f"▼{rid}" in gallery and "▲持ち寄りの入口（フォーム）から" in yomu and "▲紙や玩具を作る人の言葉を" in gallery, "ギャラリーと序の頁"
assert "▲作った人の報告" in kz, "改善の輪の節の固定の文"
assert "▲鍵が置かれると" in post(f"/record/{rid}/ai-interpret", {}), "鍵が無い時の AI の口"
# 人が書いた文は表を通らない（記録の感想・説明・自分の仮説・歌の引用）
for text in ("すっと開いた", "折りが固くて戻る", "本人が折った"):
    assert text in page, text
    assert f"▲{text}" not in page, text
song = next(e["text"] for e in hypotheses.json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))["transcription"]["entries"] if e.get("checked_by") and not e.get("rejected_by"))
assert song in page and f"▲{song}" not in page, "歌の引用"
# 前は図鑑の頁の歌の引用と自分の仮説の字も見ていた（図鑑の頁は外した・本人の言葉 11-08）
# 2 つの表は 1 か所に読める（#135・#317）。数える命令は内輪の言葉の表も読み、同じ語を両方に書かず、読む人の字にむずかしい語を戻さない
keep_table = wording.TABLE
wording.TABLE = ((re.compile("棚卸し"), "作る側"),)
counted = importlib.reload(plain_words).census({"/見本": "<p>棚卸しの注を読みます。</p>"})["words"]
assert any(x["word"] == "棚卸し" for x in counted), counted
wording.TABLE = keep_table
importlib.reload(plain_words)
hard = [w for w in plain_words.TABLE if w["word"] in plain_words.OWN_WORDS and w["word"] not in plain_words.NOT_A_WORD_HIT]
for raw, reader in [(row.pattern, reader) for row, reader in wording.TABLE] + list(wording.RECORD_NOTES.items()):
    assert raw not in plain_words.OWN_WORDS, raw
    for w in hard:
        assert not w["pattern"].search(reader), (reader, w["word"])
# 人が書いたメモは、作る側の控えの文でなければそのまま返る
assert keep_note("本人が折った") == "本人が折った" and keep_note(None) is None
print("ok")
