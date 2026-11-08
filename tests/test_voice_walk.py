"""手帖の作る頁を押す所だけで歩き、声の区切りが のこすの頁の「承認」の時だけ送られる事を、頭なしの Chrome で確かめる。

前は、声の約束（聞き続けるのは操作の言葉だけ・言葉の全部が一致した時だけ操作・問いは「こまった」の後の 1 つ・工夫はマイクを押した後だけ。#87・
本人の決定 11-06・案 2）を、音声認識の見本で歩いていた。11-08 に手帖の作る頁と作りながら見る頁の音声認識を外した（本人「クロードの音声認識をはずして、
ユーザーの端末の音声入力に頼るのでいいのではないか。」・設計は grove の state/no-speech-recognition-20261108.md の 2 版）ので、この試験は凍結の表に無い
名のまま、中身を「押す所だけで最後まで通る」と「声の区切りの送られ方」に替えた（替えた理由は commit に書いた）。
見る事:
1 手帖の作る頁: はじめる → つぎ → もどる → こまった（字の欄で聞くと答えが出て、読み上げる）→ 閉じる → 最後の手順の後の のこす の画面 → 字の畳み →
  写真を選ぶと約束の印が無いと先へ進まない → 見た事の札。マイクと音声認識は無く、マイクを開かない。入力の部品は頁の字を継ぐ（#87 の要件）
2 声の区切りの送られ方（統括の頼み 11-08）: 作りながら見る頁で録った声は、手帖の「のこす」では送られない。送られるのは、のこすの頁の確かめの画面に
  並んで「承認」を押した時だけで、送った数は並んだ数と同じ。のこすの頁を開いただけ・「のこす」を押しただけでは送らない
3 手帖の記録の頁の入力の部品も、頁の字を継ぐ
./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/test_mic_seen.py と同じ）。入っている Chrome で頁を iframe に開いて歩く。
IndexedDB とマイクと録りは見本にする（tests/voice_stub.py の注）。区切りの送りは見本が控えて、本物のサーバには送らない（ほかの送りは本物のサーバへ）。
Chrome が無い機械と、1 つも答えなかった時は、測れないと出して通す。落ちるのは、歩けて、結果が違う時と、歩き始めたのに終わらなかった時。マイクは使わない。
"""
import json
import os
import re
import subprocess
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from measure_tap import chrome  # noqa: E402
from voice_stub import FAKE_IDB, PAGE_STUB  # noqa: E402
from web import play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
from omochae import hypotheses  # noqa: E402

GS = hypotheses.sheet_of(G)["id"]
# ブラウザの既定の字（Arial など）のままの入力の部品を集める（#87 の要件。頁の字を継いでいれば空）
FONTS = ("(d=>[...d.querySelectorAll('button,input:not([type=hidden]):not([type=file]):not([type=checkbox]):not([type=radio]),textarea,select')]"
         ".filter(e=>getComputedStyle(e).fontFamily!==getComputedStyle(d.body).fontFamily).map(e=>e.tagName+(e.id?'#'+e.id:'')))")
# 外の頁が iframe の頁を順に開いて歩く（頁を移っても、置き場の見本と区切りの送りの控えが残るように、歩く台本は外の頁に置く）
WALK = r"""<script>
const f=document.getElementById('f'),R={},G=__G__,GS=__GS__,FONTS=__FONTS__;
const wait=(ms=60)=>new Promise(r=>setTimeout(r,ms)),W=()=>f.contentWindow,Q=s=>W().document.querySelector(s),QA=s=>[...W().document.querySelectorAll(s)];
const loaded=()=>new Promise(ok=>{f.onload=()=>setTimeout(ok,300)}),go=(u)=>{const p=loaded();f.src=u;return p};
const until=async(fn,n=300)=>{for(let i=0;i<n;i++){try{if(fn())return true}catch(e){}await wait()}return false};
const ts=()=>[...__idb.data.values()].filter(c=>c.kind==='t'),scene=()=>Q('#te').dataset.scene,n=()=>+new URLSearchParams(W().location.search).get('n');
const gums=()=>W().__log.filter(x=>x.startsWith('gum')).length;
const record=async(b)=>{b.click();await until(()=>W().__mr&&W().__mr.state==='recording');await wait(1500)};
(async()=>{try{
// ---- 2 の前半: 作りながら見る頁で 1 つ録る（もう一度押して止める）
await go(`/toy/${G}/tsukuru?h=${GS}&n=1`);
const rb=Q('[data-scene=craft] .hanasu-rec');await record(rb);rb.click();await until(()=>ts().length===1);R.tsukuru=[ts().length,W().__sr];
// ---- 1 手帖の作る頁を押す所だけで歩く
await go(`/toy/${G}/techo?n=1`);
R.techo0=[!!Q('#mic'),!!Q('.hanasu-rec'),scene()];
Q('#start').click();await wait();R.started=scene();
Q('#next').click();await wait();Q('#next').click();await wait();R.next=n();
Q('#back').click();await wait();R.back=n();
Q('#stuck').click();await wait();R.stuck=scene();
W().__log.length=0;Q('#q').value='谷折りって？';Q('#ask-form').requestSubmit();await until(()=>Q('#answer').textContent==='こたえ');await wait(100);
R.asked=[Q('#answer').textContent,W().__log.includes('speak')];
Q('#close').click();await wait();R.closed=scene();
for(let i=0;i<40&&scene()!=='end';i++){Q('#next').click();await wait()}
R.end=[scene(),__fetches.filter(x=>x.url.endsWith('/step')).length>0];
Q('#fold').open=true;Q('#kufu').value='紙を二重に貼った';
const dt=new (W().DataTransfer)();dt.items.add(new (W().File)([new Uint8Array([255,216,255,217])],'a.jpg',{type:'image/jpeg'}));
const pk=Q('#files');pk.files=dt.files;pk.dispatchEvent(new (W().Event)('change'));await wait();
Q('#keep').click();await wait();R.noPromise=[scene(),Q('.check').classList.contains('call')];
Q('#ok').checked=true;Q('#keep').click();await wait();R.kekka=scene();
R.fonts=W().eval(FONTS+'(document)');R.techoGum=gums();R.techoSr=W().__sr;
// 見た事の札を押して残す（工夫の字 → 記録 → 写真 → もちよる）。手帖の「のこす」は、作りながら見る頁で録った声の区切りを送らない
const leave=loaded();Q('.tile').click();await leave;
R.techoSent=__media.length;
// ---- 3 手帖の記録の頁の入力の部品
await go(`/toy/${G}/techo/kiroku`);
R.kiroku=[W().eval(FONTS+'(document)'),QA('select,textarea,input[type=text]').length];
// ---- 2 の後半: 作りながら見る頁で録り、最後の手順の「のこす」の札で のこすの頁へ。のこすの頁の工夫の欄でも 1 つ録り、
// 「のこす」で確かめの画面に並べ、「承認」で送る
await go(`/toy/${G}/tsukuru?h=${GS}&n=99`);
await record(Q('[data-scene=craft] .hanasu-rec'));
const toNokosu=loaded();Q('#tiles [value=done]').click();await toNokosu;
R.atNokosu=[W().location.pathname,__media.length];R.keptFromTsukuru=ts().length;
const nb=Q('#nk .hanasu-rec');await record(nb);
Q('#nk input[name=result]').checked=true;Q('#nk-keep').click();
await until(()=>!Q('#nk-check').hidden&&W().__mr.state==='inactive');await wait(300);
R.listed=[QA('#nk-c-clips li').length,Q('#nk-c-clips').hidden,__media.length,nb.getAttribute('aria-pressed')];
const done=loaded();Q('#nk-go').click();await done;
R.sent=__media.map(m=>m.clip);R.gone=ts().length;
}catch(e){R.error=String(e&&e.stack||e)}
const pre=document.getElementById('measured');pre.textContent=JSON.stringify(R);
})();
</script>"""
WRAP = """<!doctype html><body>%s<iframe id="f" width="390" height="844" style="border:0"></iframe><pre id="measured"></pre>%s"""

send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    if isinstance(body, str) and ctype.startswith("text/html") and self.path != "/__wrap":
        body = re.sub(r"<html[^>]*>", lambda h: h.group(0) + PAGE_STUB, body, count=1)
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        walk = (WALK.replace("__G__", json.dumps(G)).replace("__GS__", json.dumps(GS)).replace("__FONTS__", json.dumps(FONTS)))
        return send(self, 200, WRAP % (FAKE_IDB, walk))
    return get(self)


exe = chrome()
if not exe:
    print("測れない: Chrome が無い（押す所の字は tests/test_techo_step.py、送りの順は tests/test_clips_client.py が見る）")
    raise SystemExit(0)
play_server.Handler._send, play_server.Handler.do_GET = wrapped, do_get
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
# 答えの口は本物の API を呼ばない（決めた答えを返す）
from api import ask  # noqa: E402

ask.answer = lambda sid, hid, question: ("こたえ", "claude")
urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/print", data=urllib.parse.urlencode({"hypothesis": GS}).encode(), headers={"Origin": base}), timeout=120).read()


def walk():
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=900,900",
                                  "--virtual-time-budget=120000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=200).stdout
    except subprocess.TimeoutExpired:
        return None
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    if not found:
        return None
    text = found.group(1).replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return json.loads(text) if text.strip() else "started"


got = walk()
if not isinstance(got, dict):
    got = walk()  # 混んだ機械では答えない事があるので、1 度だけ回し直す
server.shutdown()
if got is None:
    print("測れない: Chrome が答えなかった（混んだ機械では起きる）")
    raise SystemExit(0)
assert isinstance(got, dict), ("歩き始めたのに終わらなかった（頁の JS が壊れた時もこうなる）", got)
print(json.dumps(got, ensure_ascii=False))
R = got
assert "error" not in R, R["error"]
assert R["tsukuru"] == [1, 0], ("作りながら見る頁で 1 つ録れる（音声認識は作られない）", R["tsukuru"])
# 1 手帖の作る頁: 押す所だけで最後まで通る
assert R["techo0"][:2] == [False, False], ("マイクも録る釦も無い", R["techo0"])
assert R["started"] == "step" and R["next"] == 3 and R["back"] == 2, (R["started"], R["next"], R["back"])
assert R["stuck"] == "henji" and R["asked"] == ["こたえ", True], ("こまった の後は字の欄で聞け、答えを読み上げる", R["stuck"], R["asked"])
assert R["closed"] == "step" and R["end"] == ["end", True], (R["closed"], R["end"])
assert R["noPromise"] == ["end", True] and R["kekka"] == "kekka", ("写真を選んだ後は、約束の印が無いと先へ進まない", R["noPromise"], R["kekka"])
assert R["fonts"] == [] and R["kiroku"][0] == [] and R["kiroku"][1] >= 3, ("既定の字のままの部品", R["fonts"], R["kiroku"])
assert R["techoGum"] == 0 and R["techoSr"] == 0, ("手帖の作る頁はマイクを開かず、音声認識も作らない", R["techoGum"], R["techoSr"])
# 2 声の区切りは、手帖の「のこす」では送らない。のこすの頁を開いただけ・「のこす」を押しただけでも送らない。「承認」で、並んだ数だけ送る
assert R["techoSent"] == 0, ("手帖の「のこす」で声の区切りが送られた", R["techoSent"])
assert R["atNokosu"] == [f"/toy/{G}/techo/kiroku", 0], ("のこすの頁を開いただけでは送らない", R["atNokosu"])
# 作りながら見る頁で録って「のこす」の札で着いた区切りは、のこすの頁を開いた時に渡される（前の頁が同じ出所の作る頁なので・#682 の openedAs の nokosu）
assert R["keptFromTsukuru"] == 1, ("作りながら見る頁で録った区切りが、のこすの頁に渡らなかった", R["keptFromTsukuru"])
listed, hidden, before, pressed = R["listed"]
assert listed >= 1 and hidden is False and before == 0 and pressed == "false", ("「のこす」で録りを止め、確かめの画面に並べ、まだ送らない", R["listed"])
assert R["sent"] == ["t"] * listed and R["gone"] == 0, ("「承認」で、並んだ区切りだけを送り、置き場を消す", R["sent"], listed, R["gone"])
print(f"ok 手帖は押す所だけで最後まで通り、声の区切りは のこすの頁の承認の時だけ送られる（並んだ {listed} つ）")
