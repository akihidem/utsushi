"""押して止まる所（使い勝手の点検で見つけた 3 件）。新しい字は足さない。

1. 手帖の約束の印は、写真か動画を選んだ時だけ要る。写真なしの「のこす」は印が無くても押せる。合言葉なしの場も写真の口があるので、同じ印を出す（本人の決定 11-06 で口を開けた。前は口が閉じていて、印を出さなかった）
2. 写真を選ばずに残した時の返事を「上げました」にしない（上げていないので）。字は頁の記録の返事に今ある字
3. 「この考えから紙を作る」の戻り先は #think。断りの文はそこにあり、頁の頭に戻ると見えなかった（幅 390 で 2978px 下）。
   11-08 に玩具の頁から #think の口ごと外した（本人の言葉「つくるの「考えを話す」は無くす。」・字の欄の無い釦は行き止まりになった）ので、
   頁に釦が無い事と、部品（think_sheet.section・_status）の戻り先が #think のままである事と、受け口の断りの文が落ちない事を見る
4. 「残す」の前に釦を押しても、話した字を消さない。字はタブの中にだけ持ち、サーバへ送らない（送るのは「残す」の時だけ、hanasu の決まり）。
   玩具の頁の字の欄（考えを話す の口）は 11-08 に外した（本人の言葉 11-08「つくるの「考えを話す」は無くす。」）ので、頁に欄が無い事と、
   釦が字を送らない事と、話す口の台本の持ち方を見る
5. 約束の印なしに写真を送らない。前の手帖の頁では、写真を選んで別の頁へ行って戻ると、ブラウザが写真を戻すのに change を出さず、押した時に写真が上がった
   （この PR の最初の形で別の目のレビューが見つけた）。作り直した手帖（1 手 1 画面、#87）は、選んだ写真を頁の中に持って選ぶ欄を空に戻すので、
   ブラウザが戻す写真は無い。印は「のこす」を押した時に見て、記録の口へ何かを送る前に止める（歩いて確かめるのは tests/test_voice_walk.py）

押した時の動きはブラウザが要るので、ここでは頁と script の形を見る（./run.sh はブラウザなしで動く決まり）。実物で押した結果は帳面の節に書く。
1・2・5 は、前の手帖の頁（techo_site の SCRIPT）で見ていた物を、作り直した頁（techo_step）の形で見る形に書き直した。
"""
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import hanasu, techo_step, think_sheet  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
from omochae import hypotheses  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
ROOT = pathlib.Path(__file__).resolve().parents[1]
shut = []


def start(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    shut.append(server)
    return f"http://127.0.0.1:{server.server_address[1]}"


def get(base, path):
    return urllib.request.urlopen(base + path, timeout=60).read().decode()


def post(base, path, data):
    q = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    try:
        r = urllib.request.urlopen(q, timeout=60)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


base, public = start(), start(public_open=True)
# 作り直した手帖は、たたき台の紙が刷ってある時だけ作る画面を出す（刷っていない時は紙を作る道だけ）
assert post(base, f"/toy/{G}/print", {"hypothesis": GS})[0] == 200

# 1. 約束の印
page = get(base, f"/toy/{G}/techo")
mark = re.search(r'<input type="checkbox" id="ok"[^>]*>', page)
assert mark, "写真の口が開いている場には印を出す"
assert "required" not in mark.group(0), ("写真を選ばない時は要らない", mark.group(0))
keep = techo_step.SCRIPT[techo_step.SCRIPT.index("const keepPress"):techo_step.SCRIPT.index("form.onsubmit")]
guard = "if (chosen.length && !ok.checked) { ok.closest('label').classList.add('call'); return; }"
assert guard in keep, "選んだ写真か動画がある時だけ要る（印の無い場は、写真を選べないので ok を見ない）"
shown = get(public, f"/toy/{G}/techo")
public_mark = re.search(r'<input type="checkbox" id="ok"[^>]*>', shown)
assert public_mark and "required" not in public_mark.group(0) and "大人の手元だけ" in shown, "合言葉なしの場でも写真の口があるので、同じ印を出す"
assert '<input type="file" id="files" disabled hidden>' not in shown and '<input type="file" id="files"' in shown, "対照: 合言葉なしの場の頁で、口が開いている"

# 5. 選んだ写真は頁の中に持ち、選ぶ欄は空に戻す（ブラウザが戻す写真を作らない）。印なしには、記録の口へ何も送らない
assert "picker.onchange = () => { chosen = chosen.concat([...picker.files]); picker.value = ''; showPicked(); };" in techo_step.SCRIPT, "選ぶ欄を空に戻す"
assert keep.index(guard) < keep.index("record-json"), "足せるかを聞く前に止める"
save = techo_step.SCRIPT[techo_step.SCRIPT.index("const save = async"):]
assert "files = chosen.slice(0, max)" in save and "if (go.disabled) return;" in save, "送るのは頁の中に持った写真だけ。押し直しでは送らない"
assert techo_step.SCRIPT.index(guard) < techo_step.SCRIPT.index("const save = async"), "見た事の札（記録を作る所）へ進む前に止める"

# 2. 返事
assert "done = files.length ? await sendFiles(j.id, files) : '記録を残しました';" in save, "写真を選ばずに残したら「上げました」と言わない"
assert "記録を残しました" in (ROOT / "src/web/play_server.py").read_text(encoding="utf-8"), "新しい字でなく、頁の記録の返事に今ある字"

# 3. 戻り先
page = get(base, f"/toy/{G}")
assert "think-sheet" not in page and 'id="think"' not in page and think_sheet.GO not in page, "玩具の頁に作り直す口（行き止まり）が残った"
assert f'action="/toy/{G}/think-sheet#think"' in think_sheet.section(G), "部品の釦は断りの文のある節へ戻す"
pending = think_sheet._status(G, {"status": "pending_human", "how_it_moves": "x", "token": "t", "result": {}})
assert f'action="/toy/{G}/think-ok#think"' in pending, "こちらの釦も同じ節へ戻す"
code, body = post(base, f"/toy/{G}/think-sheet", {"who": ""})
assert code == 422 and think_sheet.NONE in body, "受け口の断りの文は頁に残る（節が無くても落とさない）"

# 4. 話した字
# 字の欄（考えを話す の口）は、前は釦の節のすぐ前にあった。本人の言葉 11-08「つくるの「考えを話す」は無くす。」で口ごと外したので、頁に無い
assert 'id="hanasu"' not in page and 'name="scene" value="think"' not in page, "字の欄は外した"
go = re.search(r'<form[^>]*think-sheet[^>]*>(.*?)</form>', think_sheet.section(G), re.S).group(1)  # 部品の釦（頁からは外した・上の 3）
assert "<textarea" not in go and "<input" not in go, "釦は字を送らない"
script = hanasu.SCRIPT
keep = script[script.index("// 「残す」の前に"):script.index("addEventListener('pagehide',stop)")]
assert "e.target.closest('#think')" in keep, "#think の釦を押す時に持つ"
assert "sessionStorage.setItem" in keep and "sessionStorage.removeItem" in keep, "タブの中に持ち、読み直したら消す"
assert "fetch" not in keep, "サーバへ送らない"
assert "via:box.dataset.via" in keep and "box.dataset.via=d.via" in keep, "話した字か書いた字かも一緒に持って戻す"
assert "if(d&&!said.value){said.value=d.text" in keep, "読み直した後の空の欄にだけ戻す（書きかけの字を上書きしない）"

for server in shut:
    server.shutdown()
print("ok 写真を選ばずに残せて、釦は断りの文のある節へ戻り、話した字は消えない")
