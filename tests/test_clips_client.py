"""声とカメラの区切りの、端末の側（web.clips・hmd・hanasu・nokosu）。本人 11-08 330・412・415・「公開デモでも声も録る。」、窓口の決め A2・
承認の時にまとめて・それぞれ 5 つまで。設計は grove の state/voice-camera-send-20261108.md の 3 版と、作る時の統括の直し。

なぜ: 前は、声は録らず、作業の頁のカメラの映像は端末の中だけで送らなかった。本人の決めで、押した時の短い区切りを送って解析に使う形になった。
録るのは押した時だけ・承認まで送らない・端末に長く残さない・前の人の区切りを次の人に渡さない、を台本の形で固める（ブラウザなしで回す決まり）。
見る事:
1 置き場の台本: 外へ送る口が無い。開いた時に、別の画面の物と 3 時間を過ぎた物を消す。pagehide で消さない。
  渡す印は印の無い区切りにだけ付く。のこすの頁では、今の印と違う物を消す。数は 5 つまで。録る長さは 10 秒
2 作業の頁: 「ここで止まった」はカメラの頁だけ・カメラを出している間だけ。録るのは押した所だけで、カメラを出しただけでは録らない
3 話す口: 録るのは「話す」で聞き始めた後の 1 か所だけ
4 のこすの頁: 確かめの画面に区切りの並びと「外す」。承認の時、記録の後・写真の前に区切りを送る（見出し X-Utsushi-Clip。カメラは X-Utsushi-Step と
  X-Utsushi-Button も）。送れなかった時は、サーバの字を出さず決めた 1 行。承認の終わりに置き場と渡す印を消す
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from web import clips, hanasu, hmd, nokosu, techo_site  # noqa: E402

S = clips.SCRIPT
A = clips.assets()


def body(src, head, end):
    """台本の中の 1 つの関数の字（head から、次の end の前まで）。"""
    i = src.index(head)
    return src[i:src.index(end, i + len(head))]


# ---- 1 置き場の台本
for word in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "RTCPeerConnection", "document.cookie", "localStorage"):
    assert word not in S, ("置き場は外へ送らない", word)
assert (clips.CLIP_HOURS, clips.CLIP_MAX, clips.CAM_SECONDS) == (3, 5, 10)
assert "const HOURS=3,MAX=5,CAM=10*1000," in A and "__" not in A, "数は 1 か所の値から"
purge = body(S, "const purge=async()=>{", "\nconst ")
assert "c.who!==w" in purge and "now-c.at>AGE" in purge and "AGE=HOURS*3600000" in S, "別の画面の物と 3 時間を過ぎた物を消す"
assert "addEventListener('DOMContentLoaded',purgeOnce)" in S and "const purgeOnce=()=>purged||(purged=purge().catch(()=>{}))" in S, "どの頁を開いた時も消す（印は頁の終わりの台本が作るので、読み終えた後）"
assert "pagehide" not in S.replace("pagehide では消さない", ""), "pagehide では消さない（同じタブで のこす へ移る時にも起きるため）"
hand = body(S, "const handOver=async(sid)=>{", "\n")
marker = body(S, "const mark=async(sid,p)=>{", "\nconst ")
assert "await mark(sid,p)" in hand and "c.sid===sid&&c.who===w&&!c.pass" in marker and "c.pass=p.id" in marker, "渡す印は、その玩具の、印の無い区切りにだけ付ける"
# 印は玩具ごと・3 時間の内の今の印を使い直す（戻って録り足した後に渡しても、前に渡した区切りが消えない）・作り始めの後は新しい印
assert "const PK=(sid)=>'utsushi-pass:'+sid" in S and "sessionStorage.getItem(NK(sid))?null:passNow(sid)" in hand and "p=p||passMake(sid)" in hand
# 回の印（統括の決め 11-08）: 作り始めは玩具の頁を開いた時（のこす から戻った時は除く）。新しい回は印の無い区切りを消し、次は新しい渡す印。
# 作業の頁と手帖の「はじめる」は同じ玩具の回が 3 時間の内なら引き継ぐ。区切りに回の印を付け、渡す印は今の回の物にだけ付ける
new_run = body(S, "const runNew=async(sid)=>{", "\n// ")
assert "sessionStorage.setItem(RK(sid),JSON.stringify(r));sessionStorage.setItem(NK(sid),'1')" in new_run and "c.sid===sid&&!c.pass)await remove(c.id)" in new_run
assert "const startMaking=async(sid,fromNokosu)=>{if(fromNokosu&&runNow(sid))return;await runNew(sid)}" in S
assert "const goOn=async(sid)=>{if(!runNow(sid))await runNew(sid)}" in S
assert "run:r?r.id:null" in S and "c.run===r.id" in marker, "区切りに回の印・渡す印は今の回の物だけ"
opened = body(S, "const openedAs=async(sid,kind)=>{", "\naddEventListener")
assert "await purgeOnce();" in opened and "return startMaking(sid,back)" in opened and "goOn(sid)" in opened, "玩具の頁は作り始め・作業の頁は続き（消しの後で）"
assert "'/toy/'+sid+'/techo/kiroku'" in opened, "前の頁が その玩具の のこす なら引き継ぐ"
# 前の頁がこのサイトの頁でない所（URL を直に打った・外）から開いた作業の頁と手帖は、続きでなく作り始め（統括の決め 11-08）
assert "const fromOutside=()=>{try{return !document.referrer||new URL(document.referrer).origin!==location.origin}catch(e){return true}}" in S
assert "if(kind==='work')return back||(fromOutside()?startMaking(sid,false):goOn(sid))" in opened, "作業の頁は外から直に開くと作り始め"
# 承認の終わりは、その玩具の区切りと印だけ（ほかの玩具の区切りを消さない）
clr = body(S, "const clear=async(sid)=>{", "\n")
assert "if(c.sid===sid)await remove(c.id)" in clr and "s.clear()" not in S, clr
handed = body(S, "const handed=async(sid)=>{", "\nconst ")
assert "if(p&&(c.who===w||(k&&k.sid===sid&&c.who===k.who))&&c.pass===p.id)out.push(c);else await remove(c.id)" in handed, "のこすの頁では、今の印と違う物（印の無い物も）を消す"
assert "Date.now()-p.at<AGE" in S, "渡す印も 3 時間まで"
assert "await waiting(c.sid,c.kind)>=MAX" in S and "await waiting(meta.sid,'k')>=MAX)return 'full'" in S, "その玩具の、まだ渡していない区切りは 5 つまで"
cam = body(S, "const camClip=async(stream,meta)=>{", "\n// ")
assert "new MediaRecorder(stream,{videoBitsPerSecond:1000000})" in cam and "setTimeout(()=>{if(r.state!=='inactive')r.stop()},CAM)" in cam, "押した後の 10 秒"
assert "getUserMedia" not in cam, "カメラの区切りは頁が持つ映像の流れを使い、新しく開かない（音も開かない）"
voice = body(S, "const voiceStart=async(meta)=>{", "const voiceStop")
assert S.count("getUserMedia(") == 1 and "getUserMedia({audio:true})" in voice, "声のマイクは voiceStart の中の 1 か所だけ"
assert S.count("new MediaRecorder(") == 2, "録るのは声とカメラの 2 か所だけ"
assert "r.start()" in voice and "r.start()" in cam

# ---- 2 作業の頁
page_cam, page_hmd = hmd.page("NDL-1187053-R0000005-L", cam=True), hmd.page("NDL-1187053-R0000005-L")
assert f'<button type="button" id="hmd-stuck">{hmd.STUCK}</button>' in page_cam and 'id="hmd-stuck"' not in page_hmd
assert "body:not(.cam-on) #hmd-stuck{display:none}" in hmd.STYLE, "カメラを出している間だけ見える"
assert hmd.SCRIPT.count("camClip(") == 1 and "MediaRecorder" not in hmd.SCRIPT
handler = body(hmd.SCRIPT, "if(stuck)stuck.addEventListener('click',async()=>{", "}});")
assert handler.index("if(!tracks||!window.utsushiClips") < handler.index("utsushiClips.camClip(cam.srcObject,{sid:T.sid,step:Number(body.dataset.at||0)+1,button:'stuck'})")
assert "r==='full'){camNote.textContent=T.full" in handler
assert page_cam.count(A) == 1 and A not in page_hmd and clips.FULL in page_cam

# ---- 3 話す口
listen = body(hanasu.SCRIPT, "const listen=(root,onDevice)=>{", "document.addEventListener('click'")
assert listen.index("try{r.start()}") < listen.index("clip(root)") and hanasu.SCRIPT.count("clip(root)") == 1
assert hanasu.SCRIPT.count("utsushiClips.voiceStart(") == 1 and "MediaRecorder" not in hanasu.SCRIPT and "getUserMedia" not in hanasu.SCRIPT

# ---- 4 のこすの頁
G = "NDL-1187053-R0000005-L"
page = techo_site.records_page(G, paper=(hypotheses.sheet_of(G)["id"], 9))
assert 'id="nk-c-clips" hidden' in page and clips.HEAD in page and clips.STORE in page
assert nokosu.SCRIPT.replace("__REMOVE__", clips.REMOVE).count(f"b.textContent = '{clips.REMOVE}'") == 1 and "await utsushiClips.remove(c.id); clipsNow = clipsNow.filter((x) => x.id !== c.id); drawClips();" in nokosu.SCRIPT, "1 つずつ外す"
# 頁を開いた時: 渡すかどうかは openedAs の 'nokosu' に任せる（作る頁から来た時だけ渡す・直に開いたら作り始め・別の目の #659 の止め 2）
assert "utsushiClips.openedAs(sid, 'nokosu').then((list) => {" in nokosu.SCRIPT and "utsushiClips.adopt(sid).then(" not in nokosu.SCRIPT, "頁を開いた時に、渡す印の違う物を消す"
go_all = body(nokosu.SCRIPT, "go.onclick = async () => {", "\n};")
go = go_all[go_all.index("const said = "):]  # ふつうの承認（区切りだけの確かめの分かれの後）
order = [go.index(x) for x in ("/record-json`", "utsushiNewWho", "sendClips(j.id)", "sendFiles(j.id, list)", "utsushiClips.clear(sid)", "/gallery?msg=")]
assert order == sorted(order), ("承認の順: 記録 → 印の作り直し → 区切り → 写真 → 置き場を消す → もちよる", order)
send = body(nokosu.SCRIPT, "const sendClips = async (id) => {", "\n};")
assert "'X-Utsushi-Clip': c.kind" in send and "fetch(`/record/${id}/media`, { method: 'POST', headers: h, body: c.blob })" in send
assert "if (c.kind === 'k') { if (/^[0-9]+$/.test(String(c.step))) h['X-Utsushi-Step'] = String(c.step); if (c.button) h['X-Utsushi-Button'] = c.button; }" in send, \
    "カメラの区切りだけ、手順（数だけ）と釦を添える。声は区切りの種類だけ"
assert "if (m.ok) await utsushiClips.remove(c.id).catch(() => {}); else bad = true;" in send and "text()" not in send, "送れた物から消す。サーバの断りの字は読まない"
assert "if (clipBad) done = '__CLIP_FAIL__';" in go and clips.CLIP_FAIL in page, "送れなかった時は決めた 1 行"
assert go.index("sendClips(j.id)") < go.index("sendFiles(j.id, list)"), "区切りを送れなくても写真は送り続ける"
assert 'data-hanasu data-sid="' + G + '" data-scene="craft"' in page and 'class="hanasu-mic"' in page, "工夫の欄の話す口（押して話した間の声を録る）"
assert page.count(A) == 1, "置き場の台本は頁に 1 回（話す口の台本と一緒に置く）"
# 手帖の「のこす」の後の区切りだけの確かめ（#to=<記録の番号>・統括の決め 11-08 (a)）: 記録は作らず、区切りを手帖の記録へ送り、消して もちよるへ
assert "location.hash.match(/^#to=(R-[0-9]{4,})&msg=(.*)$/)" in nokosu.SCRIPT, "印の形は R- と数字だけ（ほかは ふつうの のこすの頁）"
to_go = go_all[:go_all.index("const said = ")]
assert "if (toRec) {" in to_go and "sendClips(toRec)" in to_go and "record-json" not in to_go and "/talk" not in to_go, "区切りだけの承認は記録を作らない"
assert to_go.index("sendClips(toRec)") < to_go.index("utsushiClips.clear(sid)") < to_go.index("location.assign(toGallery(bad ? '__CLIP_FAIL__' : toMsg))")
only = body(nokosu.SCRIPT, "const onlyClips = () => {", "\n")
assert "$('nk-c-rec').hidden = true" in only and "$('nk-fix').hidden = true" in only and 'id="nk-c-rec"' in page, "記録の行と「直す」を隠す"
opened_nk = body(nokosu.SCRIPT, "addEventListener('DOMContentLoaded', () => {\n  const newWho", "\n});")
assert opened_nk.index("clipsNow = list; utsushiClips.keepWho(sid, toRec); newWho();") < opened_nk.index("onlyClips()"), "並びを手元に持った直後に、前の印を控えてから、その場限りの印を作り直す（手帖が作り直さずに渡したため）"
assert "if (!clipsNow.length) { utsushiClips.dropKeep(); location.replace(toGallery(toMsg)); return; }" in opened_nk and "newWho(); utsushiClips.dropKeep(); location.replace(toGallery('__CLIP_FAIL__'))" in opened_nk, "並びが空なら もちよるへ・置き場が開かなければ決めた 1 行"
# どの出口でも、もちよるへ移る前に その場限りの印を作り直す（同じタブの次の人が前の人の印のまま作らない・別の目の設計の確かめ 1）
assert opened_nk.count("location.replace(") == 3 and "if (toRec) { newWho(); location.replace(toGallery(toMsg)); }" in opened_nk, "出口は 3 つ（台本が無い・並びが空・開かない）"
assert opened_nk.index("newWho();\n    if (!clipsNow.length) { utsushiClips.dropKeep(); location.replace(") > 0, "並びが空の出口も、作り直しの後"
assert to_go.index("utsushiClips.clear(sid)") < to_go.index("utsushiClips.dropKeep()") < to_go.index("location.assign("), "承認の出口で控えを消す（印は並べた時に作り直し済み）"
assert "addEventListener('pageshow', (e) => { if (e.persisted) location.reload(); });" in nokosu.SCRIPT, "戻る釦で読み直さずに戻った時は読み直す（同じ区切りや記録を送り直さない）"
# 読み直しても並ぶ控え: 同じ確かめの画面でだけ、控えた who の区切りを消さずに並べる
kp_fn = body(S, "const kept=()=>{", "\nconst keepWho")
assert "location.pathname==='/toy/'+k.sid+'/techo/kiroku'&&location.hash.startsWith('#to='+k.rec+'&')" in kp_fn and "Date.now()-k.at>=AGE" in kp_fn
assert "if(k&&k.sid===sid&&k.rec===rec)return" in body(S, "const keepWho=(sid,rec)=>{", "\n"), "読み直した時は控えを上書きしない（上書きすると作り直した印になる）"
assert "(c.who!==w&&!(k&&c.sid===k.sid&&c.who===k.who))" in purge and "k=kept()" in purge, "開いた時の消しは、控えた who の物だけを残す（同じ確かめの画面の時だけ）"
# 外へ X-Utsushi-Clip で送るのは のこすの頁の台本だけ（手帖・置き場の台本・作業の頁・作りながら見る頁・話す口には無い・別の目の気づき）
import pathlib  # noqa: E402

src = pathlib.Path(clips.__file__).parent
assert sorted(p.name for p in src.glob("*.py") if "'X-Utsushi-Clip'" in p.read_text(encoding="utf-8")) == ["nokosu.py"], "区切りを送る口は1つ"
draw = body(nokosu.SCRIPT, "const drawClips = () => {", "\n};")
assert "utsushiClips.list(" not in draw and "utsushiClips.adopt(" not in draw, "区切りだけの確かめは手元の並びから描く（作り直した印で並べ直すと消えるため）"
assert "try { const m = await fetch(`/record/${id}/media`" in send and "} catch (e) { bad = true; }" in send, "区切りごとに受け、落ちたら送れなかった事に"
print("ok: 声とカメラの区切りは押した時だけ録り、端末の中に置き、のこすの承認で送る（区切りの種類と手がかりの見出しつき）")

# 作り始めの呼び所: 手帖の「はじめる」と作業の頁を開いた時（作業の頁は、のこす の頁から戻った時を作り始めとしない）
from web import techo_step  # noqa: E402

assert "window.utsushiClipsStart(sid)" in techo_step.SCRIPT[techo_step.SCRIPT.index("$('start').onclick"):][:600], "手帖の「はじめる」で回を引き継ぐ"
st = clips.start_assets()
assert "if(r&&!out&&Date.now()-r.at<3*3600000)return" in st and "out=!document.referrer||new URL(document.referrer).origin!==location.origin" in st, "回の印が 3 時間の内でも、外から直に開いた手帖は引き継がない"
assert "cur.value.sid===sid&&!cur.value.pass)cur.delete()" in st and "'utsushi-pass-new:'+sid" in st, "回が無い時だけ、印の無い区切りを消し、次は新しい印"
assert not re.search(r"getUserMedia|MediaRecorder|fetch|XMLHttpRequest|sendBeacon|WebSocket|EventSource|RTCPeerConnection|document\.cookie", st), "録る code も外へ送る口も持たない"
# 手帖からは区切りを送らない（#659 の取り消し・統括の決め 11-08 (a)）。手帖は IndexedDB を開かずに印だけを見て、のこすの頁の確かめへ移る
assert "utsushiClipsSend" not in techo_step.SCRIPT and "X-Utsushi-Clip" not in techo_step.SCRIPT and "indexedDB" not in techo_step.SCRIPT
made = body(st, "window.utsushiClipsMade=(sid)=>{", "};\n")
assert "sessionStorage.getItem('utsushi-clips-made:'+sid)===r.id" in made and "Date.now()-r.at<3*3600000" in made and "indexedDB" not in made, "今の回に置いた印だけを見る"
assert "if(r)try{sessionStorage.setItem(MK(c.sid),r.id)}catch(e){}return true" in S and "[PK,NK,RK,MK].forEach(k=>sessionStorage.removeItem(k(sid)))" in clr, "置いた時に印を書き、承認の終わりに消す"
sv = techo_step.SCRIPT[techo_step.SCRIPT.index("const save = async (result)"):]
assert sv.index("toClips = clipsMade()") < sv.index("if (!toClips && window.utsushiNewWho) window.utsushiNewWho();"), "渡す時は手帖で印を作り直さない（のこすの頁が並べた後に作り直す）"
kp = techo_step.SCRIPT[techo_step.SCRIPT.index("const keepPress = async () =>"):techo_step.SCRIPT.index("const save = async (result)")]
assert "if (clipsMade()) { location.assign(toNokosu(target, done)); return; }" in kp, "前の記録に足す時も、区切りがあれば のこすの頁の確かめへ"
# 開いた時の作り始めの判定: 手帖の頁と作りながら見る頁（直に開いた時は作り始め・統括の決め 11-08）
G4 = "NDL-1187053-R0000005-L"
on_open = (f'<script>(()=>{{const s="{G4}";window.utsushiClipsStart&&utsushiClipsStart(s);'
           "addEventListener('pageshow',(e)=>{if(e.persisted&&window.utsushiClipsFresh)utsushiClipsFresh(s)})})()</script>")
assert clips.start_assets(G4).endswith(on_open) and on_open in techo_step.page(G4, [hypotheses.sheet_of(G4)["id"]], "tenji"), "開いた時と、戻る釦で読み直さずに戻った時"
start_fn = body(st, "window.utsushiClipsStart=(sid)=>{", "};\n")
assert "if(r&&!out&&Date.now()-r.at<3*3600000)return;fresh(sid)" in start_fn, "録らない頁の判定は作業の頁の「続き」と同じ（同じ出所の 3 時間の内は引き継ぐ・外か空は作り始め）"
assert "window.utsushiClipsFresh=fresh" in st and "cur.value.sid===sid&&!cur.value.pass)cur.delete()" in body(st, "const fresh=(sid)=>{", "};\n// 開いた時")
import inspect  # noqa: E402

from web import tsukuru  # noqa: E402

# 作りながら見る頁は刷った紙が無いと組めないので、組む所の字で見る（頁ごとの歩きは test_tsukuru）
assert "{SCRIPT}{clips.start_assets(sid)}</body></html>" in inspect.getsource(tsukuru.page) and "clips.assets()" not in inspect.getsource(tsukuru), "作りながら見る頁にも、開いた時の判定（録る code は足さない）"
# のこすの頁を開いた時の分かれ（openedAs の 'nokosu'）
nk_open = opened[opened.index("if(kind==='nokosu')"):opened.index("\n if(kind==='work')")]
assert "if(fromOutside()){await runNew(sid);try{sessionStorage.removeItem(PK(sid))}catch(e){}}" in nk_open, "直に開いたら作り始めで、渡す印も外す（前の人の物は並ばずに消える）"
assert "else if(fromMaking(sid))await handOver(sid);return handed(sid)" in nk_open, "作る頁から来た時だけ渡す・ほかは並べるだけ"
assert "u.origin===location.origin&&(u.pathname===t||u.pathname.startsWith(t+'/'))&&u.pathname!==t+'/techo/kiroku'" in S, "作る頁は、同じ出所の、その玩具の頁とその下の頁（のこすの頁そのものは除く）"
# 待つのは置き場が開くまでだけ（別の目の #659 の気づき）
op = body(S, "const open=()=>new Promise((ok,ng)=>{", "\nconst run=")
assert "setTimeout(()=>{late=true;dead=true;ng(new Error('wait'))},WAIT)" in op and "if(dead)return ng(new Error('wait'))" in op and "clearTimeout(t)" in op and "if(late)q.result.close()" in op and clips.OPEN_WAIT == 6 and "WAIT=6*1000" in A
assert "setTimeout" not in body(nokosu.SCRIPT, "const sendClips = async (id) => {", "\n};"), "送りには切りを掛けない"
# 作業の頁は、録る形なら openedAs の work、録らない形なら start_assets（中身は同じ決まり。作業の頁を録らない形へ替える PR がどちらで来ても通る。
# 作業の頁の側でどちらを使うかは test_hmd が見る）
hmd_page = hmd.page("NDL-1187053-R0000005-L", cam=True)
work_rec = "utsushiClips.openedAs(T.sid,'work')" in hmd.SCRIPT and "utsushiClips.startMaking(T.sid,back)" not in hmd.SCRIPT
work_plain = "utsushiClipsStart(s)" in hmd_page and "utsushiClips.openedAs(" not in hmd.SCRIPT
assert work_rec or work_plain, "作業の頁は続き（玩具の頁の回を引き継ぐ）"
assert 'utsushiClips.openedAs("NDL-1187053-R0000005-L","toy")' in hanasu.think_section("NDL-1187053-R0000005-L", {}), "玩具の頁は作り始め"
assert ("addEventListener('pageshow',(e)=>{if(e.persisted&&window.utsushiClips)utsushiClips.startMaking(T.sid,false)" in hmd.SCRIPT if work_rec
        else "if(e.persisted&&window.utsushiClipsFresh)utsushiClipsFresh(s)" in hmd_page), "戻る釦で読み直さずに戻った時も作り始め"
assert clips.STORE.endswith("このサイトをほかの画面で開くと、前に録った声と映像は消えます。"), "ほかの画面（2 つ目のタブ）で消える事を置き場の断りが言う（本人の答えの字 11-08）"
print("ok: 作り始めの消し・印は玩具ごとに使い直す・承認の後の消しはその玩具だけ")
