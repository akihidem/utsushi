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
assert "addEventListener('DOMContentLoaded',()=>{purge()" in S, "どの頁を開いた時も消す（印は頁の終わりの台本が作るので、読み終えた後）"
assert "pagehide" not in S.replace("pagehide では消さない", ""), "pagehide では消さない（同じタブで のこす へ移る時にも起きるため）"
hand = body(S, "const handOver=async(sid)=>{", "\n")
marker = body(S, "const mark=async(sid,p)=>{", "\nconst ")
assert "await mark(sid,p)" in hand and "c.sid===sid&&c.who===w&&!c.pass" in marker and "c.pass=p.id" in marker, "渡す印は、その玩具の、印の無い区切りにだけ付ける"
# 印は玩具ごと・3 時間の内の今の印を使い直す（戻って録り足した後に渡しても、前に渡した区切りが消えない）・作り始めの後は新しい印
assert "const PK=(sid)=>'utsushi-pass:'+sid" in S and "sessionStorage.getItem(NK(sid))?null:passNow(sid)" in hand and "p=p||passMake(sid)" in hand
# 作り始め（統括の決め・止め 3）: その玩具の印の無い区切りを消し、次は新しい印。のこす の頁から戻った時は消さない
start = body(S, "const startMaking=async(sid,fromNokosu)=>{", "\n// ")
assert "if(fromNokosu)return" in start and "c.sid===sid&&!c.pass)await remove(c.id)" in start and "sessionStorage.setItem(NK(sid),'1')" in start
# 承認の終わりは、その玩具の区切りと印だけ（ほかの玩具の区切りを消さない）
clr = body(S, "const clear=async(sid)=>{", "\n")
assert "if(c.sid===sid)await remove(c.id)" in clr and "s.clear()" not in S, clr
handed = body(S, "const handed=async(sid)=>{", "\nconst ")
assert "if(p&&c.who===w&&c.pass===p.id)out.push(c);else await remove(c.id)" in handed, "のこすの頁では、今の印と違う物（印の無い物も）を消す"
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
assert nokosu.SCRIPT.replace("__REMOVE__", clips.REMOVE).count(f"b.textContent = '{clips.REMOVE}'") == 1 and "await utsushiClips.remove(c.id); showClips();" in nokosu.SCRIPT, "1 つずつ外す"
assert "addEventListener('DOMContentLoaded', () => { if (window.utsushiClips) utsushiClips.list(sid)" in nokosu.SCRIPT, "頁を開いた時に、渡す印の違う物を消す"
go = body(nokosu.SCRIPT, "go.onclick = async () => {", "\n};")
order = [go.index(x) for x in ("/record-json`", "utsushiNewWho", "sendClips(j.id)", "sendFiles(j.id, list)", "utsushiClips.clear(sid)", "/gallery?msg=")]
assert order == sorted(order), ("承認の順: 記録 → 印の作り直し → 区切り → 写真 → 置き場を消す → もちよる", order)
send = body(nokosu.SCRIPT, "const sendClips = async (id) => {", "\n};")
assert "'X-Utsushi-Clip': c.kind" in send and "fetch(`/record/${id}/media`, { method: 'POST', headers: h, body: c.blob })" in send
assert "if (c.kind === 'k') { if (/^[0-9]+$/.test(String(c.step))) h['X-Utsushi-Step'] = String(c.step); if (c.button) h['X-Utsushi-Button'] = c.button; }" in send, \
    "カメラの区切りだけ、手順（数だけ）と釦を添える。声は区切りの種類だけ"
assert "if (m.ok) await utsushiClips.remove(c.id); else bad = true;" in send and "text()" not in send, "送れた物から消す。サーバの断りの字は読まない"
assert "if (clipBad) done = '__CLIP_FAIL__';" in go and clips.CLIP_FAIL in page, "送れなかった時は決めた 1 行"
assert go.index("sendClips(j.id)") < go.index("sendFiles(j.id, list)"), "区切りを送れなくても写真は送り続ける"
assert 'data-hanasu data-sid="' + G + '" data-scene="craft"' in page and 'class="hanasu-mic"' in page, "工夫の欄の話す口（押して話した間の声を録る）"
assert page.count(A) == 1, "置き場の台本は頁に 1 回（話す口の台本と一緒に置く）"
print("ok: 声とカメラの区切りは押した時だけ録り、端末の中に置き、のこすの承認で送る（区切りの種類と手がかりの見出しつき）")

# 作り始めの呼び所: 手帖の「はじめる」と作業の頁を開いた時（作業の頁は、のこす の頁から戻った時を作り始めとしない）
from web import techo_step  # noqa: E402

assert "window.utsushiClipsStart(sid)" in techo_step.SCRIPT[techo_step.SCRIPT.index("$('start').onclick"):][:600], "手帖の「はじめる」で作り始め"
st = clips.START_SCRIPT
assert "cur.value.sid===sid&&!cur.value.pass)cur.delete()" in st and "'utsushi-pass-new:'+sid" in st, "印の無い区切りを消し、次は新しい印"
assert not re.search(r"getUserMedia|MediaRecorder|fetch|XMLHttpRequest|sendBeacon|WebSocket|EventSource|RTCPeerConnection|document\.cookie", st), "録る code も外へ送る口も持たない"
assert "utsushiClips.startMaking(T.sid,back)" in hmd.SCRIPT and "'/toy/'+T.sid+'/techo/kiroku'" in hmd.SCRIPT, "作業の頁を開いた時（のこすから戻った時は除く）"
assert "addEventListener('pageshow',(e)=>{if(e.persisted&&window.utsushiClips)utsushiClips.startMaking(T.sid,false)" in hmd.SCRIPT, "戻る釦で読み直さずに戻った時も作り始め"
assert clips.STORE.endswith("別のタブでこのサイトを開くと、前のタブの区切りも消えます。"), "2 つ目のタブで消える事を置き場の断りが言う"
print("ok: 作り始めの消し・印は玩具ごとに使い直す・承認の後の消しはその玩具だけ")
