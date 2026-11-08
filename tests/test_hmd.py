"""作業しながら見る頁（web.hmd・/toy/<玩具>/kasane と /toy/<玩具>/kasane/hmd）の試験。聞くための経路（本人 11-08 539「3D 重ねずに、質問も
できるだけにしよう。…記録はここでは取らず、質問のための経路と割り切る。」）。本物の API・マイク・カメラは使わない。
受け口（POST /toy/<玩具>/kasane/ask）の側は tests/test_kasane_ask.py が見る。前の重ねる形（3D・指の合わせ・中を見る・声の操作・ここで止まった）
の試験は、この試験の 11-08 の main（ad6d67f9）の版にある（戻す時はそこから）。

見る事:
1. 頁の字と作り: 今の手順の字 1 行と ← →・大きな「聞く」・こたえ。3D と声の操作とカメラの区切りは無い。頁の台本は端末に何も置かない
   （localStorage・sessionStorage・IndexedDB・cookie を使わない。回の判定は web.clips の start_assets だけ）。網に送るのは聞く口の 1 か所だけ。
   写真は後ろのカメラと分かる時だけ撮り、HMD の道は撮らない。長押しで字の選びが出ない
2. 道: 2 つの道で開く。玩具を選ぶ頁は持たない。手帖の手順の画面の印「カメラで聞く」（本人の答え 11-08 の ②）からの 1 つだけ
3. Chrome で歩く: 手順の送り（釦と鍵）・押したまま離す形と 1 回押して始める形の両方で 1 回だけ送る・送る中身（今の手順の番号・声の型・
   写真の数が後ろのカメラ 3・前のカメラ 0・HMD 0）・待つ間の字（聞いています・考えています）・答えを出して読み上げる・頁を隠したら送らずに止める
4. 大きさと置き場: 字の一番長い手順と長い答えでも、押す所は頁を動かさずに全部見え、「聞く」は 96px 以上・ほかは 64px 以上・重ならない・
   横にはみ出さない（4 つの大きさ・縦の狭い画面は iframe）
5. 手帖の手順の画面の印（前からの測り）: 印と字「カメラで聞く」が読める大きさで切れず、帯の印と重ならない

./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/test_mic_seen.py と同じ）。入っている Chrome で頁を開いて歩く。
Chrome が無い機械と、Chrome が何も答えなかった時は、測れないと出して通す。落ちるのは、歩けて結果が違う時と、歩き始めたのに終わらなかった時。
映像の流れ（MediaStream）が付いたままだと、headless の Chrome の時間が進まず頁を書き出さないので、歩く台本は結果を書く前にカメラを止める。
"""
import html
import json
import os
import re
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from measure_tap import chrome  # noqa: E402
from omochae import hypotheses  # noqa: E402
from web import clips, hmd, naoru, play_server  # noqa: E402

# 原画の写し（out/sources・git の外）がある時は、手帖の上の帯に原画の小さな絵（#genga-thumb）が出る。写しの無い木では出ないので、
# 帯の印どうしの重なり（作業の頁への印と原画の小さな絵）を見ない試験になり、今の main で写しのある木でだけ落ちた所を拾えなかった（11-08）。
# 写しの有り無しの両方で測る: "pic" は写しが無い木でも同じ形の絵の包みを置く形（tests/test_landscape_fit.py と同じ）、"nopic" は絵を出さない形
from web import genga  # noqa: E402

_real_pic = genga._pic
PIC = {"m": "pic"}


def _pic(sid, src, alt, lazy=False, href=None, **kw):
    if PIC["m"] == "nopic":
        return "", False
    got = _real_pic(sid, src, alt, lazy=lazy, href=href, **kw)
    return got if got[0] else (f'<span class="genga-pic" style="--genga-r:0.7000"><img src="data:," width="700" height="1000" alt="{html.escape(alt)}"></span>', True)


genga._pic = _pic

G, T = hmd.TOYS
# ---- 1. 頁の字と作り
for sid in (G, T):
    assert hmd.available(sid), sid
    texts = hmd.steps(sid)
    assert len(texts) >= 3, sid
    for cam in (True, False):
        page = hmd.page(sid, cam=cam)
        words = json.loads(re.search(r'<script type="application/json" id="hmd-words">(.*?)</script>', page, flags=re.S).group(1))
        assert words["steps"] == texts and words["sid"] == sid and words["hmd"] is (not cam), "手順の字は組み方の節と同じ文"
        assert words["frames"] == (hmd.FRAMES if cam else 0), "写真はカメラの道だけ（HMD の道は撮らない）"
        assert f'<p id="hmd-text" aria-live="polite">{html.escape(texts[0])}</p>' in page and f"1 / {len(texts)}" in page, "開いた時は手順 1"
        assert f'<button type="button" id="hmd-ask" aria-pressed="false">{hmd.ASK}</button>' in page and f"<h2>{hmd.ANSWER}</h2>" in page
        assert (hmd.CAM_NOTE in page) is cam and (hmd.HMD_NOTE in page) is (not cam), "道ごとの断りの 1 行（送る物が違う）"
        assert ('<video id="hmd-cam"' in page) is cam and ('id="hmd-camera"' in page) is cam, "映像とカメラの釦はカメラの道だけ"
        for gone in ('id="rt-stage"', 'id="hmd-stuck"', 'id="hmd-split"', 'id="hmd-listen"', 'id="hmd-reset"', "ここで止まった", "中を見る", "元に戻す", "はじめる"):
            assert gone not in page, ("3D・重ねる・声の操作・カメラの区切りは外した", gone)
        # 回の判定（#655 の守り）: 作業の頁は録らないが、開いた時と戻る釦で読み直さずに戻った時の判定は置く（web.clips の start_assets）
        assert page.count(clips.start_assets(sid)) == 1 and clips.assets() not in page, "回の判定だけを置き、録る台本は置かない"
        assert f'<a href="/otona">{hmd.OTONA_LINK}</a>' in page and f'href="/toy/{sid}/techo/kiroku"' in page
# 公開の場（本人 11-08「4 つとも推しのとおり。」の ①・別の目の止め 11-08）: 開いた時から「この場では聞けません」。「聞く」・カメラの釦・映像を置かず、
# 送る物の断りも置かない（何も送らない）。手順の字と ← → は見られる。台本は「聞く」が無い時、マイクとカメラの所まで進まない
for sid in (G, T):
    for cam in (True, False):
        pub = hmd.page(sid, cam=cam, public=True)
        assert f'<p class="hmd-public" id="hmd-public">{hmd.ASK_PUBLIC}</p>' in pub, (sid, cam, "公開の場は開いた時から断りの字")
        for gone in ('id="hmd-ask"', 'id="hmd-camera"', "<video", hmd.CAM_NOTE, hmd.HMD_NOTE):
            assert gone not in pub, (sid, cam, "公開の場に聞く口とカメラを置かない", gone)
        assert f'<p id="hmd-text" aria-live="polite">{html.escape(hmd.steps(sid)[0])}</p>' in pub and 'id="hmd-next"' in pub, "手順は見られる"
script = hmd.SCRIPT
assert script.index("if(!askBtn)return;") < script.index("getUserMedia({audio:true") and script.index("if(!askBtn)return;") > script.index("const cam=$('hmd-cam')"), \
    "「聞く」が無い頁では、マイクの所まで台本が進まない（カメラの所は釦が無いので動かない）"
for word in ("XMLHttpRequest", "sendBeacon", "WebSocket", "<form", "localStorage", "sessionStorage", "indexedDB", "document.cookie", "camClip", "utsushiClips.", "SpeechRecognition"):
    assert word not in hmd.SCRIPT, ("この頁の台本は端末に置かず、声の操作をしない", word)
assert hmd.SCRIPT.count("fetch(") == 1 and "fetch(`/toy/${T.sid}/kasane/ask`" in hmd.SCRIPT, "網に送るのは聞く口の 1 か所だけ"
assert "(v.getSettings().facingMode||'')==='environment'" in hmd.SCRIPT and "if(T.hmd||!cam||!back()" in hmd.SCRIPT, "写真は後ろのカメラと分かる時だけ・HMD の道は撮らない"
assert "frames:T.hmd?[]:" in hmd.SCRIPT, "HMD の道は写真を送らない（二重の止め）"
assert "facingMode:{ideal:'environment'}" in hmd.SCRIPT and "audio:false" in hmd.SCRIPT and "{audio:true,video:false}" in hmd.SCRIPT, "映像に声を混ぜず、声は聞く間だけ"
assert "addEventListener('pagehide',away)" in hmd.SCRIPT and "if(drop){idle();return}" in hmd.SCRIPT, "頁を離れたら止めて、録りかけは送らない"
assert "user-select:none" in hmd.STYLE and "-webkit-touch-callout:none" in hmd.STYLE and "touch-action:none" in hmd.STYLE, "長押しで字の選びや呼び出しの窓が出ない"
assert hmd.ASK_SECONDS == 12 and hmd.FRAMES == 3 and hmd.FRAME_EDGE == 960
assert not hmd.available("NDL-1187053-R0000004-L"), "作業の頁を開く玩具は 2 つだけ"

# ---- 2. 道
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoFollow(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoFollow)


def get(path):
    try:
        r = opener.open(base + path, timeout=120)
        return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)


for sid in (G, T):
    assert get(f"/toy/{sid}/kasane/hmd")[0] == 200 and get(f"/toy/{sid}/kasane")[0] == 200
assert '<video id="hmd-cam"' in get(f"/toy/{G}/kasane")[1] and '<video id="hmd-cam"' not in get(f"/toy/{G}/kasane/hmd")[1], "映像はカメラの道だけ"
assert get("/toy/NDL-1187053-R0000004-L/kasane")[0] == 404 and get("/toy/NDL-1187053-R0000004-L/kasane/hmd")[0] == 404, "2 つのほかの玩具では開かない"
assert get("/hmd")[0] == 404 and get(f"/hmd/{G}")[0] == 404, "玩具を選ぶ頁と試作の枝の番地は持たない"
# 道は手帖の手順の画面の印から 1 つだけ（作る口は手帖 1 つの決まり。印の字は本人の答え 11-08 の ②「カメラで聞く」）
assert hmd.CAM_LINK == "カメラで聞く"
for sid in (G, T):  # 手帖は刷った紙がある時に手順の画面を出すので、先に刷る（刷るのはその玩具のたたき台 sheet_of）
    sheet = hypotheses.sheet_of(sid)["id"]
    urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{sid}/print", data=f"hypothesis={sheet}".encode(), headers={"Origin": base}), timeout=120).read()
for sid in (G, T):
    techo = get(f"/toy/{sid}/techo")[1]
    assert f'<p class="meta nokosu-route" data-on="start">{naoru.ROUTE_MAKING}</p>' in techo, sid
    assert techo.count('href="/toy/' + sid + '/kasane"') == 1 and f'<a class="kasane-go" id="kasane-go" href="/toy/{sid}/kasane" title="{hmd.CAM_LINK}" data-on="step">' in techo \
        and f'<span>{hmd.CAM_LINK}</span></a>' in techo, sid
assert "/kasane" not in get("/toy/NDL-1187053-R0000004-L/techo")[1], "2 つのほかの玩具の手帖には道を出さない"
for path in ("/", "/toys", f"/toy/{G}", f"/toy/{G}/kumitate", "/gallery"):
    assert "/kasane" not in get(path)[1], ("道は手帖の手順の画面からの 1 つだけ", path)

pub_server = play_server.serve(0, public_open=True)
threading.Thread(target=pub_server.serve_forever, daemon=True).start()
try:
    for path in (f"/toy/{G}/kasane", f"/toy/{G}/kasane/hmd"):
        got = urllib.request.urlopen(f"http://127.0.0.1:{pub_server.server_address[1]}{path}", timeout=120).read().decode()
        assert hmd.ASK_PUBLIC in got and 'id="hmd-ask"' not in got and "<video" not in got, ("公開の場の作業の頁は聞けない頁", path)
finally:
    pub_server.shutdown()
    pub_server.server_close()

exe = chrome()
if not exe:
    server.shutdown()
    print("ok 作業しながら見る頁の字と道。測れない: Chrome が無いので、聞く・大きさ・手帖の印は歩いていない")
    raise SystemExit(0)
send, getter = play_server.Handler._send, play_server.Handler.do_GET

# ---- 5. 手帖の最初の画面: のこすへの道の 1 行（前は重ねる頁への道）を置いても、大きいボタン「はじめる」が狭い画面の最初の画面に入る
# （別の目の確かめ 11-07: 道を上に置くと 320×568 で 22px 出た）。
# headless の Chrome は窓を 500px より狭くできないので、その大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ測り方）
FIT_SIZES, FIT_TOYS = ((320, 568), (375, 667)), (G, T, "NDL-1187053-R0000004-L")
FIT_WRAP = """<!doctype html><meta charset="utf-8"><body>__FRAMES__<pre id="measured"></pre><script>
addEventListener('load',()=>setTimeout(()=>{const out=[];for(const f of document.querySelectorAll('iframe')){const d=f.contentDocument,w=f.contentWindow;
const st=d.getElementById('start'),go=d.querySelector('.nokosu-route');const r=st.getBoundingClientRect(),g=go&&go.getBoundingClientRect();
out.push({sid:f.dataset.sid,w:w.innerWidth,h:w.innerHeight,start:Math.round(r.bottom),go:g?[Math.round(g.top),Math.round(g.bottom)]:null,sx:d.documentElement.scrollWidth});st.click();d.documentElement.style.overflowY='scroll'}
setTimeout(()=>{let i=0;for(const f of document.querySelectorAll('iframe')){const d=f.contentDocument,w=f.contentWindow,o=out[i++];
const seen=(e)=>e&&!e.hidden&&getComputedStyle(e).display!=='none'&&e.getBoundingClientRect().width>0,box=(e)=>{const b=e.getBoundingClientRect();return [Math.round(b.left),Math.round(b.top),Math.round(b.right),Math.round(b.bottom)]};
const kg=d.getElementById('kasane-go'),kl=kg&&kg.querySelector('span'),li=d.querySelector('#steps li.on'),keys=[...d.querySelectorAll('.keys a,.keys button')].filter(seen);
const others=['mic','close','genga-thumb'].map(id=>d.getElementById(id)).filter(seen);
o.step={kasane:seen(kg)?box(kg):null,label:kl&&seen(kl)?{box:box(kl),px:parseFloat(getComputedStyle(kl).fontSize),lines:Math.round(kl.getBoundingClientRect().height/parseFloat(getComputedStyle(kl).lineHeight)),cut:kl.scrollWidth>kl.clientWidth+1||kl.getBoundingClientRect().right>kg.getBoundingClientRect().right+1||kl.getBoundingClientRect().left<kg.getBoundingClientRect().left-1||kl.getBoundingClientRect().bottom>kg.getBoundingClientRect().bottom+1||kl.getBoundingClientRect().top<kg.getBoundingClientRect().top-1,iconOut:(()=>{const sv=kg.querySelector('svg');if(!sv)return true;const a=sv.getBoundingClientRect(),b=kg.getBoundingClientRect();return a.top<b.top-1||a.bottom>b.bottom+1})()}:null,bar:['mic','close','genga-thumb','kasane-go'].map(id=>d.getElementById(id)).filter(seen).map(e=>[Math.round(e.getBoundingClientRect().top),Math.round(e.getBoundingClientRect().bottom)]),text:li?box(li):null,others:others.map(box),keysBottom:Math.max(0,...keys.map(k=>Math.round(k.getBoundingClientRect().bottom)))}}
document.getElementById('measured').textContent=JSON.stringify(out)},700)},800))</script>"""


def techo_fit(lang=""):
    # lang="en" は英語の頁（訳の表の字で印の字の塊の大きさが替わる。#628 の別の目: 前の訳は 4 行に折れて印から上下に出た）。
    # 言葉の切り替えは cookie なので、日本語の頁と同じ回に混ぜず、英語だけの回にする
    q = f"&amp;lang={lang}" if lang else ""

    def do_wrap(self):
        if self.path == "/__fit":
            frames = "".join(f'<iframe data-sid="{sid}" src="/toy/{sid}/techo?v=1&amp;n=1{q}" width="{w}" height="{h}" style="border:0;display:block"></iframe>'
                             for w, h in FIT_SIZES for sid in FIT_TOYS)
            return send(self, 200, FIT_WRAP.replace("__FRAMES__", frames))
        return getter(self)

    play_server.Handler.do_GET = do_wrap
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=1600,1200",
                                  "--virtual-time-budget=20000", "--dump-dom", f"{base}/__fit"], capture_output=True, text=True, timeout=170).stdout
    except subprocess.TimeoutExpired:
        return None
    finally:
        play_server.Handler.do_GET = getter
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    return json.loads(found.group(1).replace("&quot;", '"')) if found and found.group(1).strip() else None


for sid in FIT_TOYS:  # 手帖は刷った紙がある時だけ「はじめる」を出すので、測る玩具は全部刷る
    urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{sid}/print", data=f"hypothesis={hypotheses.sheet_of(sid)['id']}".encode(),
                                                  headers={"Origin": base}), timeout=120).read()
fits, fits_en = [], []
for mode in ("pic", "nopic"):
    PIC["m"] = mode
    got_ja = techo_fit() or techo_fit()
    got_en = techo_fit("en") or techo_fit("en")
    if got_ja is None or got_en is None:
        fits = fits_en = None
        break
    for f in got_ja + got_en:
        f["pic"] = mode
    fits += got_ja
    fits_en += got_en
PIC["m"] = "pic"
if fits is not None and fits_en is not None:
    # 英語の頁は印の字の塊（字が印の高さに収まり、写真機の形が印の外へ押し出されない・帯が 1 行）だけを同じ線で見る（統括の決め 11-08）。
    # 英語の最初の画面の「はじめる」の位置は、断りの字の長さで替わる別の事なので、ここでは数だけを出す（en_start）
    for f in fits_en:
        f["lang"] = "en"
    fits = fits + fits_en
elif fits is not None:
    fits = None  # 英語の回が答えなかった時は、測れないとして出す（日本語だけで通さない）
if fits is None:
    unmeasured_fit = "手帖の最初の画面の大きさ（Chrome が答えなかった）"
else:
    unmeasured_fit = ""
    en_start = []
    for f in fits:
        en = f.get("lang") == "en"
        if en:
            en_start.append(f"{f['sid'][-6:]} {f['w']}×{f['h']} はじめるの下の端 {f['start']}")
        else:
            assert f["start"] <= f["h"] and f["sx"] <= f["w"], ("「はじめる」が最初の画面に入り、横にはみ出さない", f)
            # のこすへの道の 1 行は、全部の玩具の最初の画面に「はじめる」の下で出て、重ならず、最初の画面から押し出さない
            assert f["go"] and f["go"][0] >= f["start"], ("のこすへの 1 行は「はじめる」の下に置き、重ならない", f)
        # 手順の画面の作業の頁への印（本人の答え 11-08「どこかに道を戻す。」・字は本人の答え 11-08 の ②「カメラで聞く」）: 組み立ての書き方がある玩具だけに出て、画面の中にあり、
        # 手順の字と上の帯の印（マイク・閉じる印・原画の小さな絵）と重ならず、押す所（もどる・つぎ・こまった）を最初の画面から押し出さない
        # 手順の画面は送りの棒を必ず出した形で測る（html の overflow-y:scroll）。頁が縦に送れる長さの時（原画の写しがある木・英語の頁）は、
        # 右寄せの印が送りの棒の幅（15px）だけ左へ寄り、幅 320 で作業の頁への印と原画の小さな絵が重なった（今の main で落ちた・#635 の left:96px）。
        # 送りの棒の有り無しで替わる所を、写しの有り無しに左右されずに見るため
        st = f["step"]
        over = lambda a, b: not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])  # noqa: E731
        if f["sid"] == "NDL-1187053-R0000004-L":
            assert st["kasane"] is None, ("組み立ての書き方が無い玩具には印が無い", f)
        else:
            k = st["kasane"]
            assert k and k[0] >= 0 and k[2] <= f["w"] and k[3] <= f["h"], ("印が画面の中", f)
            assert not (st["text"] and over(k, st["text"])) and not any(over(k, o) for o in st["others"]), ("印が字や上の帯の印と重ならない", f)
            # 印に添えた字（本人の答え 11-08「印に「カメラに重ねる」の字を足す。」・今の字は「カメラで聞く」）は 12px 以上で、切れずに印の中に収まる（統括の決め 11-08）
            assert st["label"] and not st["label"]["cut"] and not st["label"]["iconOut"] and st["label"]["px"] >= 12, ("印の字が読める大きさで切れず、印の高さに収まる", f)
            # 帯は 1 行のまま: 上の帯の印（マイク・閉じる・原画の小さな絵・この印）の上の端がそろい、この印は帯の一番高い印（マイク 72px）より下へ出ない
            assert len({t for t, _ in st["bar"]}) == 1 and k[3] <= max(b for _, b in st["bar"]), ("帯が 2 行にならない", f)
            # マイクとの間は 8px 以上（統括の気づき 11-08: 4px は指で押し違えやすい）。マイクは帯の左の端の印
            assert k[0] - st["others"][0][2] >= 8, ("マイクと印の間が 8px 以上", f)
        if not en:
            assert st["keysBottom"] <= f["h"], ("手順の画面の押す所が最初の画面に入る", f)
    print("英語の頁の最初の画面（数だけ）:", "・".join(en_start))


# ---- 3. Chrome で歩く: 聞く
# 見本は頁の script より先に置く。録る口（MediaRecorder）・カメラとマイク（getUserMedia）・網（fetch）・読み上げ（speechSynthesis）を差し替える。
# カメラは canvas の流れ（絵がある）に、向き（facingMode）の見本を付ける。本物のマイクとカメラは使わない
ANSWER = "破線の所を、手前にへこむように折ってください。"
STUB = r"""<script>(()=>{window.__net=[];window.__said=[];const FACING=__FACING__;
class MR{constructor(s,o){this.stream=s;this.mimeType=(o&&o.mimeType)||'';this.state='inactive'}
 start(){this.state='recording'}
 stop(){if(this.state==='inactive')return;this.state='inactive';const t=this;setTimeout(()=>{t.ondataavailable&&t.ondataavailable({data:new Blob(['v'.repeat(3000)],{type:'audio/webm'})});t.onstop&&t.onstop()},0)}}
MR.isTypeSupported=t=>t.startsWith('audio/webm');window.MediaRecorder=MR;
const md={getUserMedia:async c=>{if(c&&c.video){const cv=document.createElement('canvas');cv.width=640;cv.height=480;const g=cv.getContext('2d');
  const paint=()=>{g.fillStyle='#'+((Math.random()*0xffffff)|0).toString(16).padStart(6,'0');g.fillRect(0,0,640,480)};paint();const iv=setInterval(paint,100);
  const s=cv.captureStream(10),tr=s.getVideoTracks()[0];tr.getSettings=()=>({facingMode:FACING});const st=tr.stop.bind(tr);tr.stop=()=>{clearInterval(iv);st()};return s}
 return new MediaStream()}};
Object.defineProperty(navigator,'mediaDevices',{get:()=>md,configurable:true});
window.fetch=async(u,o)=>{__net.push([String(u),o&&o.body?JSON.parse(o.body):null]);await new Promise(r=>setTimeout(r,50));
 return new Response(JSON.stringify({text:__ANSWER__,from:'ai'}),{headers:{'Content-Type':'application/json'}})};
Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>__said.push(u.text),cancel:()=>{}},configurable:true});
})()</script>"""
ASKWALK = r"""<script>(async()=>{
const wait=(ms=60)=>new Promise(r=>setTimeout(r,ms)),R={},$=s=>document.querySelector(s),b=document.body,ask=$('#hmd-ask'),cam=$('#hmd-camera'),v=$('#hmd-cam');
const pd=t=>ask.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:1,button:0,isPrimary:true,pointerType:'touch'}));
const until=async(f,n=200)=>{for(let i=0;i<n&&!f();i++)await wait(50)};
const net=()=>__net.map(x=>[x[0],x[1]&&x[1].step,x[1]&&x[1].type,x[1]&&(x[1].frames||[]).length,!!(x[1]&&x[1].voice)]);
// HMD の道（映像が無い）では、時間を進める形の headless の Chrome が待ちの間を先へ飛ばし、声を読む所（FileReader）が終わる前に測った。
// カメラの道と同じに、映像の流れが付いている間は時間がふつうに進むので、見えない video に見本の流れを付けておき、結果を書く前に止める
let pace=null;if(!cam){const cv=document.createElement('canvas'),g=cv.getContext('2d'),iv=setInterval(()=>{g.fillRect(0,0,8,8)},100);pace=document.createElement('video');
 pace.muted=true;pace.style.display='none';pace.srcObject=cv.captureStream(10);document.body.appendChild(pace);pace.play().catch(()=>{});pace.stop=()=>{clearInterval(iv);pace.srcObject.getTracks().forEach(t=>t.stop());pace.srcObject=null}}
const keys=()=>[...Object.keys(localStorage).map(k=>'l:'+k),...Object.keys(sessionStorage).map(k=>'s:'+k)].sort().join(',');
try{
 R.store0=keys();
 R.init=[$('#hmd-count').textContent,$('#hmd-prev').disabled,$('#hmd-text').textContent,$('#hmd-answer').hidden,ask.textContent];
 $('#hmd-next').click();await wait();R.next=[$('#hmd-count').textContent,$('#hmd-text').textContent,$('#hmd-prev').disabled];
 b.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));await wait();R.key=$('#hmd-count').textContent;
 b.dispatchEvent(new KeyboardEvent('keydown',{key:'PageUp',bubbles:true,cancelable:true}));await wait();R.key2=$('#hmd-count').textContent;
 if(cam){cam.click();await until(()=>v.videoWidth>0);R.cam=[v.videoWidth>0,b.dataset.back,cam.textContent]}
 // 押したまま話して離す形
 pd('pointerdown');await until(()=>ask.getAttribute('aria-pressed')==='true');
 R.listening=[ask.textContent,ask.getAttribute('aria-pressed'),$('#hmd-state').textContent];
 await wait(2400);pd('pointerup');await until(()=>ask.dataset.state==='wait'||__net.length>0,100);
 R.thinking=[ask.textContent,$('#hmd-state').textContent];
 await until(()=>!$('#hmd-answer').hidden);
 R.hold={net:net(),reply:$('#hmd-reply').textContent,said:__said.slice(),btn:[ask.textContent,ask.getAttribute('aria-pressed'),$('#hmd-state').textContent]};
 // 1 回押して始める形: 短く押して離しても録り続け、もう一度押すと止まって送る
 pd('pointerdown');await until(()=>ask.getAttribute('aria-pressed')==='true');await wait(100);pd('pointerup');await wait(400);
 R.tapStill=[ask.getAttribute('aria-pressed'),__net.length];
 pd('pointerdown');await until(()=>__net.length>=2);pd('pointerup');await until(()=>ask.textContent===__ASK__);
 R.tap=__net.length;
 // 頁を隠したら止めて、録りかけは送らない（カメラも止まる）
 pd('pointerdown');await until(()=>ask.getAttribute('aria-pressed')==='true');
 let hidden=false;Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
 hidden=true;document.dispatchEvent(new Event('visibilitychange'));await wait(500);
 R.hid=[__net.length,ask.getAttribute('aria-pressed'),ask.textContent,v?!!v.srcObject:null];hidden=false;
 R.store=keys();
}catch(e){R.error=String(e&&e.stack||e)}
try{if(v&&v.srcObject&&cam)cam.click();if(pace)pace.stop()}catch(_){}
const pre=document.createElement('pre');pre.id='measured';pre.textContent=JSON.stringify(R);document.body.appendChild(pre);
})();</script>"""
# ---- 4. 大きさと置き場: 字の一番長い手順まで送り、長い答えを出した形で測る（カメラは付けない）
LONG_ANSWER = "破線の所を、手前にへこむように折ります。折る前に定規を当てて、線の上を爪でなぞっておくと、まっすぐに折れます。" * 2
LAYOUT = r"""<script>(async()=>{
const wait=(ms=60)=>new Promise(r=>setTimeout(r,ms)),R={},$=s=>document.querySelector(s);
try{const W=JSON.parse($('#hmd-words').textContent).steps;let LG=0;W.forEach((t,i)=>{if(t.length>W[LG].length)LG=i});
for(let i=0;i<LG;i++){$('#hmd-next').click();await wait(20)}
$('#hmd-reply').textContent=__LONG__;$('#hmd-answer').hidden=false;$('#hmd-state').textContent=__THINKING__;await wait(200);
const box=e=>{const r=e.getBoundingClientRect();return[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]};
R.btn=[...document.querySelectorAll('.hmd button')].filter(e=>!e.hidden&&getComputedStyle(e).display!=='none').map(e=>[e.id,...box(e),e.scrollWidth>e.clientWidth+1]);
R.parts=['.hmd-top','.hmd-step','#hmd-answer','#hmd-state','.hmd-acts'].map(s=>[s,...box($(s))]);
R.len=$('#hmd-text').textContent.length;R.at=LG;R.px=parseFloat(getComputedStyle($('#hmd-text')).fontSize);
R.vw=innerWidth;R.vh=innerHeight;R.sx=document.documentElement.scrollWidth}catch(e){R.error=String(e&&e.stack||e)}
const pre=document.createElement('pre');pre.id='measured';pre.textContent=JSON.stringify(R);document.body.appendChild(pre);
})();</script>"""


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=(env|user|layout)", self.path)
    if m and isinstance(body, str) and "/kasane" in self.path:
        kind = m.group(1)
        if kind == "layout":
            walk_js = LAYOUT.replace("__LONG__", json.dumps(LONG_ANSWER, ensure_ascii=False)).replace("__THINKING__", json.dumps(hmd.THINKING, ensure_ascii=False))
            stub = ""
        else:
            walk_js = ASKWALK.replace("__ASK__", json.dumps(hmd.ASK, ensure_ascii=False))
            stub = STUB.replace("__FACING__", json.dumps("environment" if kind == "env" else "user")).replace("__ANSWER__", json.dumps(ANSWER, ensure_ascii=False))
        body = body.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + stub, 1).replace("</body>", walk_js + "</body>", 1)
    return send(self, code, body, ctype, headers)


def run_chrome(url, size, budget=60000):
    with tempfile.TemporaryDirectory() as profile:
        return subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", f"--window-size={size}",
                               f"--virtual-time-budget={budget}", "--dump-dom", url], capture_output=True, text=True, timeout=170).stdout


def walk(path, kind):
    """Chrome で 1 回歩く。返すのは、頁が書いた結果（歩き終われば dict、何も答えなければ None、頁は出たが書かなければ "started"）。"""
    hold = {}

    def tagged(self, code, body, ctype="text/html; charset=utf-8", headers=()):
        self.path = hold.get("path", self.path)
        return wrapped(self, code, body, ctype, headers)

    def tagging_get(self):
        hold["path"], self.path = self.path, re.sub(r"[?&]walk=\w+", "", self.path)
        return getter(self)

    play_server.Handler._send, play_server.Handler.do_GET = tagged, tagging_get
    try:
        out = run_chrome(f"{base}{path}?walk={kind}", "1280,800")
    except subprocess.TimeoutExpired:
        return None
    finally:
        play_server.Handler._send, play_server.Handler.do_GET = send, getter
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    if not found:
        return "started" if 'class="hmd"' in out else None
    return json.loads(html.unescape(found.group(1)))


LAYOUT_SIZES = ((1280, 720), (1024, 600), (390, 664), (375, 667), (320, 568))
LAYOUT_WRAP = """<!doctype html><meta charset="utf-8"><body style="margin:0">__FRAMES__<pre id="measured"></pre><script>
addEventListener('load',()=>setTimeout(()=>{const out=[];for(const f of document.querySelectorAll('iframe')){const m=f.contentDocument.getElementById('measured');
out.push({sid:f.dataset.sid,path:f.dataset.path,w:Number(f.width),h:Number(f.height),got:m?JSON.parse(m.textContent):null})}
document.getElementById('measured').textContent=JSON.stringify(out)},6000))</script>"""


def layout():
    """5 つの大きさ × 2 つの玩具 × 2 つの道を iframe で開き、字の一番長い手順と長い答えの形で測る（headless の Chrome は窓を 500px より狭くできない）。"""
    hold = {}

    def tagged(self, code, body, ctype="text/html; charset=utf-8", headers=()):
        self.path = hold.get(self.path, self.path)
        return wrapped(self, code, body, ctype, headers)

    def tagging_get(self):
        if self.path == "/__layout":
            frames = "".join(f'<iframe data-sid="{sid}" data-path="{p}" src="/toy/{sid}/{p}?walk=layout" width="{w}" height="{h}" style="border:0;display:inline-block;vertical-align:top"></iframe>'
                             for w, h in LAYOUT_SIZES for sid in (G, T) for p in ("kasane", "kasane/hmd"))
            return send(self, 200, LAYOUT_WRAP.replace("__FRAMES__", frames))
        bare = re.sub(r"[?&]walk=\w+", "", self.path)
        hold[bare] = self.path
        self.path = bare
        return getter(self)

    play_server.Handler._send, play_server.Handler.do_GET = tagged, tagging_get
    try:
        out = run_chrome(f"{base}/__layout", "2700,4200")
    except subprocess.TimeoutExpired:
        return None
    finally:
        play_server.Handler._send, play_server.Handler.do_GET = send, getter
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    return json.loads(html.unescape(found.group(1))) if found and found.group(1).strip() else None


fits_unmeasured = unmeasured_fit
runs = {}
for name, (path, kind) in {"カメラの道・後ろのカメラ": (f"/toy/{G}/kasane", "env"), "カメラの道・前のカメラ": (f"/toy/{T}/kasane", "user"),
                           "HMD の道": (f"/toy/{G}/kasane/hmd", "env")}.items():
    got = walk(path, kind)
    runs[name] = got if isinstance(got, dict) else walk(path, kind)  # 混んだ機械では答えない事があるので、1 度だけ回し直す
sizes = layout() or layout()

server.shutdown()
unmeasured = []
if all(v is None for v in runs.values()) and sizes is None:
    unmeasured.append("聞くと大きさ（Chrome が答えなかった。混んだ機械では起きる）")
for name, got in runs.items():
    if got is None:
        unmeasured.append(f"{name}（Chrome が答えなかった）")
        continue
    assert isinstance(got, dict), ("歩き始めたのに終わらなかった", name, got)
    assert "error" not in got, (name, got)
    sid = T if "前のカメラ" in name else G
    texts = hmd.steps(sid)
    n = len(texts)
    cam = "HMD" not in name
    assert got["init"] == [f"1 / {n}", True, texts[0], True, hmd.ASK], (name, "開いた時は手順 1・こたえは隠れている", got)
    assert got["next"] == [f"2 / {n}", texts[1], False] and got["key"] == f"3 / {n}" and got["key2"] == f"2 / {n}", (name, "← → と鍵で手順を選ぶ", got)
    if cam:
        assert got["cam"] == [True, "1" if "後ろ" in name else "0", hmd.CAMERA_OFF], (name, "映像が付き、向きを読む", got)
    assert got["listening"] == [hmd.LISTENING, "true", hmd.LISTENING], (name, "押している間は「聞いています」", got)
    assert got["thinking"] == [hmd.THINKING, hmd.THINKING], (name, "離すと「考えています」", got)
    frames = 3 if "後ろ" in name else 0
    assert got["hold"]["net"] == [[f"/toy/{sid}/kasane/ask", 2, "audio/webm", frames, True]], \
        (name, "離した時に 1 回だけ送る・今の手順の番号・声の型・写真は後ろのカメラの時だけ 3 枚（前のカメラと HMD は 0）", got)
    # 読み上げの見本には、押した時の空の読み上げ（iPhone の Safari の音の許しのため）も入るので、字のある物だけを見る
    assert got["hold"]["reply"] == ANSWER and [x for x in got["hold"]["said"] if x] == [ANSWER] and got["hold"]["btn"] == [hmd.ASK, "false", ""], (name, "答えを出して読み上げ、元に戻る", got)
    assert got["tapStill"] == ["true", 1] and got["tap"] == 2, (name, "短く押して離しても録り続け、もう一度押すと止まって送る", got)
    assert got["hid"][:3] == [2, "false", hmd.ASK] and got["hid"][3] in (False, None), (name, "頁を隠したら止め、録りかけは送らない・カメラも止まる", got)
    # 頁のほかの台本（回の判定・言葉の切り替えなど）が開いた時に置く物は数えず、聞く間に増えた物だけを見る
    assert got["store"] == got["store0"], (name, "聞いても端末に何も置かない", got)
if sizes is None:
    unmeasured.append("大きさと置き場（Chrome が答えなかった）")
else:
    over = lambda a, b: not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])  # noqa: E731
    for f in sizes:
        name = f"{f['w']}×{f['h']}・{'御来迎' if f['sid'] == G else '虎'}・{f['path']}"
        got = f["got"]
        assert isinstance(got, dict) and "error" not in got, ("歩き始めたのに終わらなかった", name, f)
        texts = hmd.steps(f["sid"])
        assert got["at"] == max(range(len(texts)), key=lambda i: (len(texts[i]), -i)) and got["len"] >= 30, (name, "字の一番長い手順で測る", got)
        assert got["sx"] <= got["vw"], (name, "横にはみ出さない", got)
        assert got["px"] >= 17, (name, "手順の字は 17px 以上", got)
        for bid, left, top, right, bottom, cut in got["btn"]:
            assert top >= 0 and bottom <= got["vh"] and left >= 0 and right <= got["vw"], (name, "押す所が頁を動かさずに全部見える", bid, got)
            assert bottom - top >= (96 if bid == "hmd-ask" else 64) and not cut, (name, "「聞く」は 96px 以上・ほかは 64px 以上・字が釦からはみ出さない", bid, got)
        parts = got["parts"]
        for i, a in enumerate(parts):
            for b in parts[i + 1:]:
                assert not over(a[1:], b[1:]), (name, "手順の字・こたえ・待つ字・押す所が重ならない", a, b)
if fits_unmeasured:
    unmeasured.append(fits_unmeasured)
note = f"。測れない: {'・'.join(unmeasured)}" if unmeasured else ""
print(f"ok 作業しながら見る頁: 手順の字と「聞く」とこたえ。押した間だけ録り、離した時に 1 回だけ送り、写真は後ろのカメラの時だけ。端末に置かない{note}")
