"""手帖の作る頁（1 手 1 画面、#87）が、写真を「この画面が残した記録」に足す所を、入っている Chrome で歩いて確かめる（1 回の作りが 2 つの記録に割れる所の直し）。

字を見る試験では、押す順と送る順が分からない。本物の頁で、玩具の頁の記録の欄で残す → 手帖を開いて「のこす」の画面へ → 写真を選ぶ → 「のこす」を押す、を歩き、
残った記録と写真をサーバの側で数える。受け口の決まり（鍵・番号を受けない・期限・別の紙と版）は tests/test_photo_attach.py が見る。

歩く道:
N 約束の印（大人の手元だけ・顔なし・声なし）を入れずに押す: 何も送らない（足せるかも聞かない）。印の所を目立たせる
A 写真だけを選んで押す: 見た事の札を出さず、さっきの記録に足す（記録は増えない）。紙はいつも送る（この頁の紙は開いた時に決まっている）
B 写真のある記録には、もう足さない: 今までどおり見た事の札を出す。押す所は戻る
C 続けて 2 度押す: 同じ写真を 2 度送らない
E 工夫の字がある時は、足せるかを聞かない: 札を出し、選ぶと新しい記録になる（話した字は話す口の記録に残る）
前の頁（紙を選ぶ札のある頁）にあった「同じ見た事を選び直す」「別の紙を選び直す」の道は、この頁では見た事を足せるかの後に選び、紙を選ばないので無い。

./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/test_mic_seen.py と同じ）。入っている Chrome で頁を iframe に開いて歩く。
Chrome が無い機械と、Chrome が何も答えなかった時は、測れないと出して通す。落ちるのは、歩けて結果が違う時と、歩き始めたのに終わらなかった時。
main の #443 の歩く試験（前の手帖の頁を歩いた）を、作り直した頁の作りに合わせて書き直した。
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
os.environ.pop("OMOCHAE_VOICE", None)
os.environ.pop("ANTHROPIC_API_KEY", None)

from measure_tap import chrome  # noqa: E402
from omochae import records  # noqa: E402
from web import play_server, techo_site  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 親の頁。手帖と同じ origin に置き、iframe の中の頁を本物の操作と同じ順で動かす。写真は canvas で作った本物の JPEG（受け口は中身を読める物だけを受ける）。
WALK = r"""<!doctype html><body><iframe id="f" width="820" height="900" style="border:0"></iframe><pre id="measured">started</pre><script>(async()=>{
const R={},G=%s,f=document.getElementById('f');
const wait=(ms)=>new Promise(r=>setTimeout(r,ms));
const record=(result)=>fetch('/toy/'+G+'/record',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({hypothesis:'H-A',result}),redirect:'manual'});
// 頁が記録の口へ送った数を数える（約束の印が無い時に、足せるかも聞かない事を見るため）。足せるかを聞いた時の紙も控える
const open=()=>new Promise(r=>{f.onload=()=>{const w=f.contentWindow,real=w.fetch;w.__sent=0;w.__asked=null;w.fetch=(u,o)=>{if(String(u).includes('record-json')){w.__sent++;const q=new URLSearchParams(o&&o.body?o.body.toString():'');if(q.get('attach')==='1')w.__asked=q.get('hypothesis')}return real.call(w,u,o)};
 // 最後の手順の後から開き、「はじめる」で「のこす」の画面へ行く
 w.document.getElementById('start').click();r()};f.src='/toy/'+G+'/techo?n=99&t='+Math.random()});
const doc=()=>f.contentDocument,te=()=>doc().getElementById('te'),keep=()=>doc().getElementById('keep');
const jpeg=()=>new Promise(r=>{const c=document.createElement('canvas');c.width=c.height=8;c.getContext('2d').fillRect(0,0,8,8);c.toBlob(r,'image/jpeg')});
const pick=async()=>{const w=f.contentWindow,dt=new w.DataTransfer();dt.items.add(new w.File([await jpeg()],'a.jpg',{type:'image/jpeg'}));
 const p=doc().getElementById('files');p.files=dt.files;p.dispatchEvent(new w.Event('change'))};
// 押して、記録の頁へ移るか、見た事の札が出るまで待つ。移った時は頁に出す字（msg）を返す
const settle=async()=>{for(let i=0;i<300;i++){await wait(50);let w;try{w=f.contentWindow;if(w.location.pathname.endsWith('/techo/kiroku')&&doc().readyState==='complete')return new URL(w.location.href).searchParams.get('msg');
 if(te()&&te().dataset.scene==='kekka'&&!keep().disabled)return 'kekka'}catch(e){}}return 'timeout'};
const who=()=>sessionStorage.getItem('utsushi-who');
try{
 await record('動いた');await open();R.scene=te().dataset.scene;await pick();
 // N 約束の印なし
 const ok=doc().getElementById('ok');ok.checked=false;keep().click();await wait(400);R.n=[te().dataset.scene,f.contentWindow.__sent,keep().disabled,ok.closest('label').classList.contains('call')];
 // A 写真だけ
 R.who_a=[who()];doc().getElementById('ok').checked=true;keep().click();R.a_asked=f.contentWindow.__asked;R.a=await settle();R.who_a.push(who());
 // B 写真のある記録には足さない
 await open();await pick();doc().getElementById('ok').checked=true;keep().click();R.b_asked=f.contentWindow.__asked;R.b=await settle();R.b_sent=f.contentWindow.__sent;R.b_ready=!keep().disabled;
 // C 続けて 2 度押す
 await record('動かない');await open();await pick();doc().getElementById('ok').checked=true;keep().click();keep().click();R.c_sent=f.contentWindow.__sent;R.c=await settle();
 // E 工夫の字がある時は聞かない。札を選ぶと新しい記録
 await record('動いた');await open();await pick();doc().getElementById('ok').checked=true;doc().getElementById('kufu').value='二度目の作りは糊を少なく';
 R.who_e=[who()];keep().click();R.e_kekka=await settle();R.e_sent=f.contentWindow.__sent;
 doc().querySelector('.tile[value="動いた"]').click();R.e=await settle();R.who_e.push(who());
}catch(e){R.error=String(e&&e.stack||e)}
document.getElementById('measured').textContent=JSON.stringify(R);
})();</script>"""

send, get = play_server.Handler._send, play_server.Handler.do_GET


def do_get(self):
    if self.path == "/__walk":
        return send(self, 200, WALK % json.dumps(G))
    return get(self)


exe = chrome()
if not exe:
    print("測れない: Chrome が無い（受け口の決まりは tests/test_photo_attach.py が見る）")
    raise SystemExit(0)
play_server.Handler.do_GET = do_get
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/print", data=urllib.parse.urlencode({"hypothesis": "H-A"}).encode(), headers={"Origin": base}), timeout=120)


def walk():
    """Chrome で 1 回歩く。返すのは、頁が書いた結果（歩き終われば dict、始めただけなら "started"、何も答えなければ None）。"""
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=1000,1000",
                                  "--virtual-time-budget=90000", "--dump-dom", f"{base}/__walk"], capture_output=True, text=True, timeout=170).stdout
    except subprocess.TimeoutExpired:
        return None
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    if not found:
        return None
    text = found.group(1).replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return json.loads(text) if text.startswith("{") else text


got = walk()
if not isinstance(got, dict) and not records.all_records(G):
    got = walk()  # 混んだ機械では答えない事があるので、何も残っていなければ 1 度だけ回し直す
server.shutdown()
if got is None:
    print("測れない: Chrome が答えなかった（混んだ機械では起きる。受け口の決まりは tests/test_photo_attach.py が見る）")
    raise SystemExit(0)
assert isinstance(got, dict), ("歩き始めたのに終わらなかった", got, [(r["id"], r["result"]) for r in records.all_records(G)])
assert "error" not in got, got
rows = [(r["result"], r.get("via"), r.get("note") or "", len(techo_site.media_of(r["id"]))) for r in sorted(records.all_records(G), key=lambda r: r["id"])]
assert got["scene"] == "end", ("最後の手順の後から開くと「のこす」の画面", got)
# N 約束の印なしでは、足せるかも聞かず、何も送らない。押す所も止めず、印の所を目立たせる
assert got["n"] == ["end", 0, False, True], got
# A 写真だけで押すと、見た事の札を出さず、玩具の頁で残した記録に足す。紙は、この頁が作っている紙（たたき台）として送る
assert got["a"] == "上げました" and got["a_asked"] == "H-A", got
assert rows[0] == ("動いた", None, "", 1), rows
# 足した時は、その場限りの印を作り直さない（記録は増えていない。作り直すと、次の作りの話が 2 つの印に割れる）
assert got["who_a"][0] and got["who_a"][0] == got["who_a"][1], got
# B 写真のある記録にはもう足さず、今までどおり見た事の札を出す。聞いたのは 1 回だけで、押す所は戻る
assert got["b"] == "kekka" and got["b_asked"] == "H-A" and got["b_sent"] == 1 and got["b_ready"], got
# C 続けて 2 度押しても、写真は 1 つ。2 度目の押しは聞く所まで行かない
assert got["c"] == "上げました" and got["c_sent"] == 1 and rows[1] == ("動かない", None, "", 1), (got, rows)
# E 工夫の字がある時は聞かずに札を出し、選ぶと新しい記録にする。玩具の頁で残した記録は、写真なしのまま
assert got["e_kekka"] == "kekka" and got["e_sent"] == 0, ("工夫の字がある時は、足せるかを聞かない", got)
assert got["e"] == "上げました" and rows[2:4] == [("動いた", None, "", 0), ("動いた", "techo", "", 1)], (got, rows)
assert got["who_e"][0] and got["who_e"][0] != got["who_e"][1], ("新しい記録が残った時は、今までどおり印を作り直す", got)
assert len(rows) == 4, rows
print("ok 手帖の作る頁: 写真だけで「のこす」を押すと記録が 1 つのまま。写真のある記録・工夫の字がある時は今までどおり札を出す。2 度押しても写真は 1 つ")
