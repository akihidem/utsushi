"""作業しながら見る頁の試作（HMD を想定。本人の指示 11-06「実装やってみて。作業する場面で使えるといいよね」）。

半年後に向けた試作で、main には入れない（試作の枝 try/hmd。凍結の中なので、試しのリンクでだけ見せる）。
狙い: 両手を作る事に空けたまま、手順の字と組み立ての 3D を目の前に出し、声で送る。

判断の芯:
- 組み立ては kumitate の部品をそのまま使う。送るのも kumitate の釦を押す形にして、絵と動きの作りを 2 つにしない。
- 手順の字は目線の高さ（画面の上）に大きく出す。3D はその下で、画面の高さに合わせて大きくする。押す所は大きく、間を空ける。
- 声で送る言葉は、手帖の声の操作と同じ「つぎ・もどる・もう一回」。聞くのは「はじめる」を押した後だけ。
  字は残さず、送る言葉を探すだけ（頁から外へ何も送らない）。頁を隠したら聞くのを止める。
- 声を字にできないブラウザでは、ボタンとキーボード（→ ← スペース。足の踏み板や指輪の送りは PageDown・PageUp を送る）で送る。
- 開いたら手順 1 の字を出し、刷った紙のまま止める（最初の「つぎ」で 1 手目が動く）。できあがりの「つぎ」では戻さない（下の 1 手ずつの節）。
- 暗い地にする。透けて見える HMD の画面では、明るい地が目に強いため（試作の読みで、機械では確かめていない）。
- 文は全部、試作の文（本人の確認の前）。採られた字（つぎ・もどる・もう一回・はじめる）だけは手帖と同じ。
- 本人の感想（11-06）「折る操作などが早く再生されどうしたらいいかわからない」: 1 つの手順の動きを「手」に分け、「つぎ」1 回で
  1 手だけ動かして止まる。手は、切る・折る・通す・置く・開く の 1 つ。折りは折り目 1 本ずつ（多い時は数本ずつ、1 つの動きで 6 回まで）。
  見る向きが変わるだけの動きは前後の手に付ける（「つぎ」を言ったのに何も起きない、を作らない）。折りは 1 本 2.2 秒から、切るは 2.2 倍。
  手順が替わった時は、字を読む間を置いてから動かす。「もどる」は 1 手もどり、「もう一回」は今の手をもう一度動かす。
  手順の中の手の数と済んだ数は、字でなく点で示す（新しい字を足さない）。最後の「つぎ」では、はじめに戻さない
  （言い間違いで組み上がった形が消えないように。はじめに戻すのは「はじめから」）。
  この進め方は、同じ感想から別の窓が作った枝 proto/hmd-work-view の物を移した（統括の決め 11-06: 枝は try/hmd に 1 つにする）。
- 声の約束（本人の決定 11-06・手帖の作り直しの案 2 と同じ）: 認識の字の全部が操作の言葉と一致した時だけ動く。
  「次の手順ってどうやるの」のような話し声では動かない。認識が付ける空白と句読点は除いてから比べる。読みの候補は 3 つまで見る。
- 作っている間、画面が消えないように頼む（断られても動く）。
- 本人の追加（11-06）「普通にiPhoneのカメラのオーバーレイでもできるようにしたら」: /toy/<玩具>/kasane で、後ろのカメラの映像の上に
  手順の字と 3D を重ねる。
- **カメラの区切り**（本人 11-08 330・412「解析につかう」・415「カメラの映像は、押した時の短い区切りだけ。」・窓口の決め A2）: カメラを出している間、
  「ここで止まった」を押した後の 10 秒だけを録り（音なし・頁が持つ映像の流れを使う・web.clips.camClip）、この端末の中に置く。押す前は何も録らず、
  カメラを出しただけでは録らない。送るのは、のこすで承認した時だけ（web.nokosu）。前の「映像は機械の中だけで、送りも残しもしない」は、この決めで替わった。
  頁の台本は外へ何も送らない（送る口は のこすの頁の 1 か所）。のこす へ移る道を押すと、録った区切りを渡す印が付く（web.clips の handOver）。
- 重ねる（本人の言葉 11-08「A → B → C の順。」の A。設計 grove の state/kasane-a-design-20261108.md・統括の決め ①〜③）: カメラの映像の上に、
  今の手順の 3D を半透明（不透明 0.6・机の色は透明）で重ね、指で位置・大きさ・向きを実物に合わせる。1 本指で動かし、2 本指の間の長さの比で
  大きさ、2 本を結ぶ線の角の差で向き（画面の中で回す）、2 本の真ん中の動きで位置。Safari の gesturechange（visionOS・Mac の板）も同じ所へ渡す
  （2 本の指が別々に来ない機械の備え。Pointer Events で 2 本が来ている時は使わず、2 度効かせない）。鍵は + − で大きさ、[ ] で向き、0 で元に戻す。
  追いかけはしない（映像の中の紙を見つけて動かす事はしない）。合わせは舞台（.rt-stage）の transform だけで持ち、舞台の中（kumitate の
  .rt-scene の見る向き）とは別にして、互いに上書きしない。重ねている間は、1 本指は「動かす」だけにし、3D の見る向きを回す kumitate の
  1 本指の回しは止める（同じ指の動きに 2 つの意味を持たせない・見る向きは手順の向きのまま）。止め方は、頁の capture の段で指の知らせを
  受けて先へ渡さない形（kumitate の作りは替えない）。層の順は下から 映像 → 3D → 手順の字・頭の帯・押す所。
  重ねるのは、カメラに重ねる頁ではカメラが付いた時から止めた時まで、HMD の道では最初から（透ける画面の向こうに実物が見えるため。
  「iPhone でも HMD のブラウザでも同じ」）。重ね始めた時の位置と大きさ（舞台が頁にあった所）を既定にし、「元に戻す」と画面の向きや大きさが
  替わった時はそこへ戻す。合わせた位置は頁の中だけに持ち、残さない・送らない。前の 4 隅の印（4 つを紙の角へ動かして囲みに入れる形・
  11-07）は外した（4 つで 8 回触るより 1〜2 本の指で合い、向きも合わせられる。字の無い印が画面から 4 つ減る）。
  映像は video に出すだけで、canvas に写さない。録るのは「ここで止まった」を押した後の 10 秒だけで、送るのは のこすで承認した時（上のカメラの区切り・web.clips・web.nokosu）。
- 中を見る（本人の言葉 11-07「AI が 3D で表示して中身をそこで分解できる構造表示」）: 組み立ての節が分解した形（window.kumitateSplit の X。
  3D の担当が kumitate に足す口）を持つ時だけ釦を出す。開く時は今の手の終わりの形から分解した形へ動かし、とじる時は戻す。
  開いている間に手順を送ったら、先にとじた事にしてから送る（送りは手の終わりの形に置き直してから動くので、形は取り違えない）。
  口が無い時（分解した形の無い組）は釦を出さない。分解は形と中身を見せるだけで、動きの答えは出さない（J-013）。
"""
import json

from omochae import hypotheses

from . import clips, kumitate, skin
from .skin import esc

CAMERA, CAMERA_OFF = "カメラを出す", "カメラを止める"
# 作業の頁のカメラの断り（設計の 6 節の字・本人の確かめ待ち）。前は作りながら見る頁と同じ PRIVACY（「映像はこの端末の中だけで、送りも残しもしません。」）を
# 使っていたが、区切りを送る形になったので分けた（作りながら見る頁の鏡は録らないので、そちらの字は本当のまま）
CAM_NOTE = "カメラの映像は、押した後の 10 秒だけをこの端末に置き、のこすで承認した時に送ります。押していない間は録りません。"
STUCK = "ここで止まった"  # 作りながら見る頁と同じ字（採られた字）。押した後の 10 秒を録る
OTONA_LINK = "保護者の方へ、ファシリテーターの方へ"  # 前からある頁の名（くわしい説明の道）
KEEP_LINK = "のこす"  # 帯の駅の字。録った区切りを のこす の頁へ渡す道
# 分解の釦（本人の決定 11-07: 開く「中を見る」・戻す「とじる」。「もどる」は手順を戻す釦と同じ字なので使わない）
SPLIT_OPEN, SPLIT_CLOSE = "中を見る", "とじる"
NO_CAMERA = "この機械ではカメラを使えません。"
# 重ねる（A）の新しい字。本人の確かめ待ちの案（統括 11-08）。差し替えはこの 2 つだけ
RESET = "元に戻す"
FIT_HINT = "1 本指で動かし、2 本指で大きさと向きを合わせます。"
# 手帖の最初の画面から重ねる頁へ行く道の名（本人の決定 11-07「口の名「カメラに重ねる」」）
CAM_LINK = "カメラに重ねる"

TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")  # 組み立ての書き方がある玩具（御来迎・虎）
TITLE = "作業しながら見る（試作）"
LISTEN, STOP = "はじめる", "止める"
NEXT, PREV, AGAIN = "つぎ", "もどる", "もう一回"
MIC_OFF = "声で送る: 止まっています"
MIC_ON = "聞いています: 「つぎ」「もどる」「もう一回」"
NO_VOICE = "このブラウザでは声で送れません。ボタンか、キーボードの → ← で送れます。"
BLOCKED = "マイクの許しがありません。ボタンか、キーボードの → ← で送れます。"
HOW = ("「はじめる」を押すと、ブラウザ（ネットを見るアプリ）が声を字にします。そのとき、声がブラウザの会社に送られることがあります。"
       "この頁は、送る言葉を探すだけです。声も字も残しません。")
TRIAL = "試作です。HMD（頭に付ける画面）で、両手を空けたまま見る形を試しています。"
# 声の言葉（言った字 → 操作）。認識は漢字で返す事が多いので、同じ意味の書き方を並べる。全部が一致した時だけ操作にする。
# つぎ・もどる・もう一回 は手帖の作り直しで採られた言葉（web/voice_words の表と同じ字。まだ main に無い）。はじめから・止める はこの試作の足し
WORDS = {**dict.fromkeys(("つぎ", "次", "つぎへ", "次へ", "すすむ", "進む", "できた", "出来た"), "next"),
         **dict.fromkeys(("もどる", "戻る", "まえに", "前に"), "prev"),
         **dict.fromkeys(("もう一回", "もういっかい", "もう1回", "もう１回", "もう一度", "もういちど"), "again"),
         **dict.fromkeys(("はじめから", "初めから", "最初から"), "top"),
         **dict.fromkeys(("とめて", "止めて", "とめる", "止める", "おわり", "終わり"), "stop")}
CLEAN = r"[\s。、．，！？!?…・]"  # 認識が付ける空白と句読点を除いてから比べる

STYLE = """
body.hmd-page{background:#14161a;color:#f3efe6}
.hmd-page .nav,.hmd-page .foot{display:none}
.hmd-page main{max-width:none;padding:0 max(16px,2vw)}
.hmd{display:flex;flex-direction:column;gap:14px;min-height:100vh;padding:14px 0 18px}
.hmd-top{display:flex;flex-wrap:wrap;gap:8px 22px;align-items:baseline;font-size:clamp(18px,1.6vw,28px);letter-spacing:.06em;color:#c9c2b4}
.hmd-top b{color:#f3efe6;font-weight:600}
#hmd-count{font-variant-numeric:tabular-nums}
.hmd-mic{margin-left:auto;padding:4px 14px;border:2px solid #5d6470;border-radius:999px}
.hmd-mic[data-state=on]{border-color:#7fd1a8;color:#bff0d6}
.hmd-mic[data-state=none],.hmd-mic[data-state=blocked]{border-color:#c98a6a;color:#f0c7b0}
#hmd-heard{min-width:6em;color:#ffe08a}
.hmd-k{display:grid;grid-template-columns:minmax(0,1fr) minmax(220px,300px);grid-template-areas:"text acts" "stage acts" "note acts";grid-template-rows:auto auto 1fr;gap:14px 26px;align-items:start}
.hmd-k .lead,.hmd-k .rt-acts{display:none}
.hmd-k #rt-text{grid-area:text;margin:0;min-height:2.6em;font-size:clamp(30px,3.6vw,64px);line-height:1.45;letter-spacing:.04em;color:#fffaf0}
.hmd-k .rt-stage{grid-area:stage;justify-self:center;margin:0;zoom:var(--hmd-zoom,1);border-color:#3a3f48;cursor:grab}
.hmd-k .meta{grid-area:note;color:#9a9385;font-size:14px}
.hmd-acts{grid-area:acts;display:flex;flex-direction:column;gap:12px}
/* 押す所は全部、頁を動かさずに見える所に置く（カメラの釦が画面の外に出て、iPhone で探せなかった。11-06 の撮った画面で見た） */
.hmd-acts button{margin:0;text-align:center;min-height:clamp(64px,8vh,100px);padding:0 .6em;font-size:clamp(22px,2.2vw,36px);letter-spacing:.12em;border-radius:14px;border:2px solid #6b7280;background:#22262d;color:#f3efe6;cursor:pointer}
.hmd-acts button:focus-visible{outline:4px solid #ffe08a;outline-offset:3px}
.hmd-acts #hmd-next{background:#2e5b46;border-color:#7fd1a8}
.hmd-acts #hmd-listen{background:#3b3550;border-color:#a99be0}
.hmd-acts #hmd-listen[aria-pressed=true]{background:#5a2f2f;border-color:#e09b9b}
.hmd-note{font-size:14px;line-height:1.8;color:#9a9385;max-width:60em}
.hmd-note a{color:#c9c2b4}
/* ここで止まった は、カメラを出している間だけ出す。録っている 10 秒は枠の色で見せる */
body:not(.cam-on) #hmd-stuck{display:none}
/* 横で低い画面でカメラを出している間の押す所の並び（「ここで止まった」が 1 つ増えて 2 列だと 4 段になり、元に戻す が画面の外へ出た・
   test_hmd の 横・低い・重ねる）は、下の 横で高さの低い画面の 4 列 2 段の形にまとめた（3 列でも、虎の字の一番長い手順では 3 段目が外へ出た） */
#hmd-stuck[data-state=rec]{border-color:#ffe08a}
/* 縦に長い画面（iPhone を縦に持つ）: 手順の字・3D・押す所の順。字の欄は 3 行分の高さに決め、手順が替わっても 3D の大きさと置き場が
   動かないようにする。頭の帯は 1 行（聞き取った字の写しは、当たった釦が光るので縦では出さない）。押す所は「つぎ」を左の大きな 1 つ、
   ほかを右の 4 列 2 段にして、iPhone の見える高さ（390×664 ほど）でも 3D の下に全部入れる。前は 2 列 2 段で、カメラに重ねる頁の釦
   （もどる・もう一回・はじめる・カメラ・ここで止まった・中を見る・重ねている間の元に戻す の 7 つ）が 3 段目に溢れ、375×667 の字の長い
   手順で画面の下へ出た（別の目の測り 11-08）。4 列にすると 1 つの釦の幅が狭いので、長い字（カメラを止める）は釦の中で 2 行に折れる */
@media (max-aspect-ratio:1/1){.hmd{gap:8px;padding-top:8px}
.hmd-top{flex-wrap:nowrap;gap:10px;font-size:14px;letter-spacing:.02em}.hmd-top b,#hmd-count{white-space:nowrap}.hmd-mic{min-width:0;padding:2px 10px;border-width:1px;border-radius:12px;line-height:1.4}#hmd-heard{display:none}
.hmd-k{grid-template-columns:minmax(0,1fr);grid-template-areas:"text" "stage" "acts" "note";grid-template-rows:none;gap:8px}
.hmd-k #rt-text{font-size:clamp(19px,5.6vw,26px);min-height:4.35em}
.hmd-acts{display:grid;grid-template-columns:1.15fr repeat(4,1fr);grid-template-rows:64px 64px;gap:8px}
.hmd-acts #hmd-next{grid-row:1/3;min-height:96px}
.hmd-acts button{min-height:64px;padding:0 .3em;font-size:clamp(15px,4.2vw,22px);letter-spacing:0;line-height:1.2;white-space:normal;overflow-wrap:anywhere;justify-content:center;text-align:center}}
@media (prefers-reduced-motion:reduce){.hmd-acts button{transition:none}}
.hmd-list{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}
/* 手の印: 今の手順の中に手がいくつあり、いくつ済んだか（字にしない。1 手だけの手順では出さない） */
#hmd-dots{display:flex;gap:.55em;margin:0;min-height:.8em;font-size:clamp(16px,1.6vw,28px)}
#hmd-dots span{width:.8em;height:.8em;border-radius:50%;box-sizing:border-box;border:2px solid #6b7280}
#hmd-dots span.on{background:#ffe08a;border-color:#ffe08a}
/* 「つぎ」はいちばん押す所なので大きく。当たった言葉の札は少しの間光る */
.hmd-acts #hmd-next{min-height:96px}
.hmd-acts button[disabled]{opacity:.35;cursor:default}
.hmd-acts button.hit{background:#ffe08a;border-color:#ffe08a;color:#14161a}
body.hmd-cam{background:#000}
#hmd-cam{position:fixed;inset:0;width:100%;height:100%;object-fit:cover;z-index:-1;background:#000}
/* 重ねる（A）: 舞台は頁の置き場のまま、映像（z -1）の上・字と押す所（z 2）の下に置く。合わせは舞台の transform（置き場からのずれ・大きさ・向き）。
   半透明にして下の実物を透かす。指は舞台だけが受ける。頁の流れから外さないので、字が長い手順でも押す所の置き場は前と同じ（fit の縮尺も効く） */
body.fit-on .hmd-k .rt-stage{position:relative;z-index:1;transform-origin:50% 50%;opacity:.6;touch-action:none;cursor:move;--rt-table:transparent;background:transparent;border-color:rgba(255,255,255,.35)}
body.fit-on .hmd-top,body.fit-on #hmd-dots,body.fit-on .hmd-k #rt-text,body.fit-on .hmd-acts,body.fit-on .hmd-note{position:relative;z-index:2}
#hmd-reset,#hmd-fit-hint{display:none}body.fit-on #hmd-fit-hint{display:inline}body.fit-on #hmd-reset{display:flex}
/* 横で高さの低い画面（1024×600 など）は、押す所を「つぎ」の下に 4 列にする（「つぎ」は 4 列の幅）。重ねている間は「元に戻す」で 7 つになり、
   1 列では下の釦が画面の外へ出た（別の目の測り 11-08・統括の決め）。2 列・3 列でも、虎の字の一番長い手順では頭の帯が 2 行に折れ、
   「ここで止まった」が足された後は 3 段目が外へ出たので、4 列 2 段にした（字は釦の中で折れる）。縦の画面は別の形（下の max-aspect-ratio の所） */
@media (min-aspect-ratio:1/1) and (max-height:800px){.hmd-acts{display:grid;grid-template-columns:repeat(4,1fr);align-content:start;gap:8px}.hmd-acts #hmd-next{grid-column:1/-1}.hmd-acts button{min-height:64px;padding:0 .25em;font-size:clamp(15px,1.5vw,26px);letter-spacing:.02em;line-height:1.25;white-space:normal;overflow-wrap:anywhere;justify-content:center;text-align:center}}
body.hmd-cam .hmd{position:relative}
body.hmd-cam .hmd-k #rt-text{background:rgba(0,0,0,.55);padding:8px 14px;border-radius:10px;text-shadow:0 1px 3px #000}
body.hmd-cam .hmd-top{background:rgba(0,0,0,.45);padding:6px 12px;border-radius:10px}
body.hmd-cam .hmd-k .rt-stage{--rt-table:transparent;background:rgba(20,22,26,.35);border-color:rgba(255,255,255,.25)}
body.hmd-cam .hmd-acts button{background:rgba(34,38,45,.8)}
body.hmd-cam .hmd-note{background:rgba(0,0,0,.55);padding:6px 10px;border-radius:8px}
.hmd-list a{display:inline-flex;align-items:center;min-height:96px;padding:0 34px;font-size:clamp(26px,2.6vw,42px);border:2px solid #7fd1a8;border-radius:14px;color:#f3efe6;text-decoration:none}
"""

SCRIPT = r"""<script>(()=>{
const $=id=>document.getElementById(id),body=document.body;
const next=$('rt-next'),prev=$('rt-prev'),text=$('rt-text'),count=$('rt-count'),stage=$('rt-stage');
const mic=$('hmd-mic'),heard=$('hmd-heard'),listen=$('hmd-listen'),shown=$('hmd-count'),dots=$('hmd-dots');
const T=JSON.parse($('hmd-words').textContent),P=window.kumitateParts;
// 作業の頁を開いた時は、玩具の頁で作り始めた回を引き継ぐ（web.clips の openedAs の work）。回が無い時だけ、ここで作り始める
addEventListener('DOMContentLoaded',()=>{if(window.utsushiClips)setTimeout(()=>utsushiClips.openedAs(T.sid,'work').catch(()=>{}))});
// 戻る釦で頁が読み直されずに戻った時（bfcache・pageshow の persisted）は、前の頁がどこでも作り始めとする（別の目の残る穴・統括の決め）。
// 同じ人が のこす から戻る釦で戻った時も、前に渡した区切りは次に渡す時に新しい印になって並ばなくなるが、前の人の声を次の人に送らない方を採る
addEventListener('pageshow',(e)=>{if(e.persisted&&window.utsushiClips)utsushiClips.startMaking(T.sid,false).catch(()=>{})});
if(!next||!prev)return;
const at=()=>Number(stage.dataset.at||0),done0=()=>!count.textContent;
const still=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
const chip={next:$('hmd-next'),prev:$('hmd-prev'),again:$('hmd-again')};
const flash=op=>{const b=chip[op];if(!b)return;b.classList.add('hit');setTimeout(()=>b.classList.remove('hit'),500)};

// ---- 1 手ごとに止まる進め方（本人の感想 11-06「折る操作などが早く再生されどうしたらいいかわからない」）
// 1 つの手順の動きを「手」に分け、「つぎ」1 回で 1 手だけ動かして止まる。手は、切る・折る・通す・置く・開く の 1 つ。
// 折りは折り目 1 本ずつ止まる（多い時は数本ずつ、1 つの動きで 6 回まで）。見る向きが変わるだけの動きは、前後の手に付ける。
// 速さも遅くする（折りは 1 本 2.2 秒から。切る動きは 2.2 倍の長さ）。手順が替わった時は、字を読む間を置いてから動かす。
const moves=[];let done=0,token=0,onDone=null;
// 1 つの動きが終わった知らせ（kumitate が形を置き終えた後に出す）で、手の中の次の動きへつなぐ
document.addEventListener('kumitate-beat',e=>{const d=e.detail;if(d.beat===d.beats&&onDone){const f=onDone;onDone=null;f()}});
if(P){const F=P.F,TR=P.T;
const kind=(A,B)=>{const k={cut:!!B.cut,open:!!B.open,fold:[],scene:false,moved:false,dur:B.dur||0};
 for(const key in B.s){const a=A.s[key],b=B.s[key];if(!a){k.scene=true;continue}
  const rows=TR[key].rows;
  for(const i in rows)if(Math.abs((a.a[i]||0)-(b.a[i]||0))>.01)k.fold.push([key,i,B.o&&B.o[key]&&B.o[key][i]!==undefined?B.o[key][i]:-rows[i][5]]);
  if(a.m.join()!==b.m.join())k.moved=true}
 for(const key in A.s)if(!B.s[key])k.scene=true;
 if((A.paper||0)!==(B.paper||0))k.scene=true;
 k.rod=Object.keys(B.r).some(n=>!A.r[n]);
 k.tool=!!B.ruler&&String(A.ruler||'')!==String(B.ruler);
 k.act=k.cut||k.open||k.fold.length>0||k.rod||k.tool||(k.moved&&!k.scene&&k.dur>500);
 return k};
const slow=k=>k.cut?2.2:k.open?1.6:k.fold.length?Math.max(1.6,1800/(k.dur||1100)):k.rod?1.8:1.5;
// 途中の形: 折り目のうち、順の早い物（upto まで）だけを折った形。置き場と見る向きは、折り始めのまま
const mix=(A,B,upto,folds)=>{const Q={...A,s:{},o:B.o,dur:undefined,cut:undefined,open:undefined,cam:undefined};
 for(const key in A.s){const a=A.s[key];Q.s[key]={m:a.m,n:a.n,a:{...a.a}}}
 for(const f of folds)if(f[2]<=upto&&Q.s[f[0]])Q.s[f[0]].a[f[1]]=B.s[f[0]].a[f[1]];
 return Q};
let pose=F[0].q[0];
F.forEach((f,i)=>{const list=[];
 for(let j=i===0?1:0;j<f.q.length;j++){const A=pose,B=f.q[j];list.push({A,B,k:kind(A,B)});pose=B}
 if(!list.length)return;
 // 見る向きだけの動きなどは、前の手に付ける（短い動きと、後ろに手が無い時）か、次の手に付ける
 const groups=[];let pend=[];
 list.forEach((t,n)=>{if(t.k.act){groups.push({pre:pend,act:t,post:[]});pend=[]}
  else if(groups.length&&(t.k.dur<=500||!list.slice(n+1).some(x=>x.k.act)))groups[groups.length-1].post.push(t);
  else pend.push(t)});
 if(!groups.length)groups.push({pre:[],act:null,post:pend});else if(pend.length)groups[groups.length-1].post.push(...pend);
 for(const g of groups){const pre=g.pre.map(t=>[t.A,t.B,1.3]),post=g.post.map(t=>[t.A,t.B,1.3]);
  const ords=g.act?[...new Set(g.act.k.fold.map(x=>x[2]))].sort((x,y)=>x-y):[];
  const parts=[];
  if(ords.length>1){const size=Math.ceil(ords.length/6);let A=g.act.A,lo=-Infinity;
   for(let s=0;s<ords.length;s+=size){const lastOne=s+size>=ords.length,upto=ords[Math.min(s+size,ords.length)-1];
    const n=g.act.k.fold.filter(x=>x[2]>lo&&x[2]<=upto).length,B=lastOne?{...g.act.B}:mix(g.act.A,g.act.B,upto,g.act.k.fold);
    B.dur=Math.max(2200,1100*n);parts.push([A,B,1]);A=B;lo=upto}}
  else if(g.act)parts.push([g.act.A,g.act.B,slow(g.act.k)]);
  if(!parts.length){moves.push({i,chain:post,end:post[post.length-1][1]});continue}
  parts.forEach((part,x)=>{const chain=[...(x===0?pre:[]),part,...(x===parts.length-1?post:[])];moves.push({i,chain,end:chain[chain.length-1][1]})})}});
body.dataset.moves=moves.length}
const ok=P&&moves.length>0;
// 手の並び（どの手がどの手順か）を頁の印に出す。試験が、組の手順と手の数を決め打ちせずに期待を出すため（字ではない。組が替わっても同じに測る）
body.dataset.plan=moves.map(m=>m.i).join(',');
const halt=()=>{token++;onDone=null;P.stop()};
const endOf=k=>k<0?P.F[0].q[0]:moves[k].end;
// 中を見る: 分解した形（kumitateSplit.X）が在る時だけ釦を出す。開くと今の手の終わりの形から分解した形へ、とじると戻す
const split=$('hmd-split'),SP=window.kumitateSplit;let opened=false;
function shut(){if(!opened)return;opened=false;split.textContent=T.splitopen;split.setAttribute('aria-pressed','false');body.classList.remove('split-on')}
if(split){if(!SP||!SP.X)split.hidden=true;else split.addEventListener('click',()=>{halt();body.dataset.busy='';const now=endOf(done-1);
 if(opened){shut();P.play(SP.X,[now],0)}else{opened=true;split.textContent=T.splitclose;split.setAttribute('aria-pressed','true');body.classList.add('split-on');P.play(now,[SP.X],0)}})}
// 1 手を動かす。動きの途中で次の言葉が来たら、その手の終わりの形にしてから次へ進む
const run=(k,read)=>{shut();halt();const me=token,chain=moves[k].chain;P.rest(endOf(k-1));
 if(still){P.rest(moves[k].end);return}
 let n=0;const step=()=>{if(me!==token)return;if(n===chain.length){body.dataset.busy='';return}
  const c=chain[n++];window.kumitateSlow=c[2];onDone=step;P.play(c[0],[c[1]],0)};
 body.dataset.busy='1';setTimeout(step,read?900:250)};
// 今の手順の字と数と、手の印（点）を出す。手順は、最後に動かした手の手順（まだ動かしていない時は手順 1）
const paint=()=>{const i=moves[Math.max(done-1,0)].i;P.go(i);
 const n=moves.filter(m=>m.i===i).length,k=moves.slice(0,done).filter(m=>m.i===i).length;
 dots.textContent='';if(n>1)for(let x=0;x<n;x++){const d=document.createElement('span');if(x<k)d.className='on';dots.append(d)}
 chip.prev.disabled=done===0;chip.again.disabled=done===0;chip.next.disabled=done===moves.length;body.dataset.at=i;body.dataset.move=done;
 // 手順の字の行の数が替わると 3D の置き場が動くので、描いた後に大きさを測り直す
 requestAnimationFrame(()=>fit())};
const back=k=>{shut();halt();done=k;P.rest(endOf(done-1));body.dataset.busy='';paint()};
// 操作。kumitate の口が無い時（節の作りが変わった時）は、前の進め方（kumitate の釦を押す・手順ごと）で動く
const act={
 next:()=>{if(!ok){next.click();return}
  if(done>=moves.length)return false;const was=done?moves[done-1].i:-1;done++;paint();run(done-1,moves[done-1].i!==was)},
 prev:()=>{if(!ok){if(!prev.disabled)prev.click();return}if(done===0)return false;back(done-1)},
 again:()=>{if(!ok){if(done0())return;if(prev.disabled){next.click();prev.click()}else{prev.click();next.click()}return}
  if(done===0)return false;run(done-1)},
 top:()=>{if(!ok){if(done0()){next.click();return}let n=0;while(!prev.disabled&&n++<99)prev.click();return}
  if(done===0)return false;back(0)},
 stop:()=>{stopListen();return false}};
const go=op=>{if(act[op]()!==false)flash(op)};
// 釦と鍵（足の踏み板・指輪の送りは PageDown・PageUp を送る）
for(const op in chip)chip[op].addEventListener('click',()=>go(op));
document.addEventListener('keydown',e=>{const el=e.target.closest?e.target:document.body;if(el.closest('input,textarea'))return;
 if(el.closest('button')&&(e.key===' '||e.key==='Enter'))return;if(e.altKey||e.ctrlKey||e.metaKey)return;
 const k={ArrowRight:'next',PageDown:'next',' ':'next',ArrowLeft:'prev',PageUp:'prev',r:'again',R:'again',Home:'top'}[e.key];
 if(k){e.preventDefault();go(k)}});
// 作業は手順 1 から始める。開いた時は刷った紙のまま止め、手順 1 の字を出す（kumitate の頁は、開くとできあがりの形を見せる作り）
if(ok){done=0;P.rest(endOf(-1));paint()}else if(done0())next.click();
// 数を頭の帯へ写す（kumitate の数をそのまま使う）
const copy=()=>{shown.textContent=count.textContent||T.done};copy();
new MutationObserver(copy).observe(count,{childList:true,characterData:true,subtree:true});
// 3D を、頁を動かさずに見える所いっぱいに大きくする。縦の画面では、3D の下に押す所が来るので、その高さを引く
const acts=document.querySelector('.hmd-acts');
const fit=()=>{const r=stage.getBoundingClientRect(),z=parseFloat(getComputedStyle(stage).zoom)||1,wide=innerWidth>innerHeight;
 const w=r.width/z,h=r.height/z,top=r.top+scrollY,avail=innerHeight-top-(wide?16:acts.offsetHeight+24);
 const col=stage.parentElement.clientWidth-(wide?340:0);
 stage.style.setProperty('--hmd-zoom',Math.max(.3,Math.min(2.4,avail/h,col/w)).toFixed(2));if(P)P.view()};
// 縮める下限は 0.3（前は 0.35。390×664 の虎の字の一番長い手順で、押す所の下の段が 9px 外へ出た。11-08 の測り）
addEventListener('resize',fit);fit();
// 声。聞くのは「はじめる」の後だけ。認識の字の全部が操作の言葉と一致した時だけ動かし、ほかの字は捨てる（送らない・残さない）
const SR=window.SpeechRecognition||window.webkitSpeechRecognition,CLEAN=new RegExp(T.clean,'g');
let rec=null,on=false;
// 声の様子の字が替わると頭の帯の高さが変わるので、3D の大きさを測り直す
const say=(s,state)=>{mic.textContent=s;mic.dataset.state=state;fit()};
const hit=t=>T.words[t.replace(CLEAN,'')]||null;
function stopListen(){on=false;if(rec)try{rec.stop()}catch(_){}say(T.off,'off');listen.textContent=T.listen;listen.setAttribute('aria-pressed','false')}
function startListen(){
 if(!SR){say(T.none,'none');return}
 try{rec=new SR()}catch(_){say(T.none,'none');return}
 rec.lang='ja-JP';rec.continuous=false;rec.interimResults=false;rec.maxAlternatives=3;
 rec.onresult=e=>{if(!on)return;const r=e.results[e.results.length-1];
  for(let i=0;i<r.length;i++){const k=hit(r[i].transcript);if(k){heard.textContent='「'+r[i].transcript.trim().slice(-10)+'」';go(k);return}}};
 rec.onerror=e=>{if(['not-allowed','service-not-allowed','audio-capture'].includes(e.error)){on=false;say(T.blocked,'blocked');listen.textContent=T.listen;listen.setAttribute('aria-pressed','false')}};
 // 1 回の聞き取りが終わるたびに聞き直す（聞いている間と、頁が見えている間だけ）
 rec.onend=()=>{if(on&&!document.hidden){try{rec.start()}catch(_){}}};
 try{rec.start()}catch(_){return}
 on=true;say(T.on,'on');listen.textContent=T.stop;listen.setAttribute('aria-pressed','true')}
listen.addEventListener('click',()=>{on?stopListen():startListen();wake()});
if(!SR)say(T.none,'none');
// 作っている間、画面が消えないように頼む（断られても動く）
const wake=()=>{try{if(navigator.wakeLock&&!document.hidden)navigator.wakeLock.request('screen').catch(()=>{})}catch(_){}};
wake();
const cam=$('hmd-cam'),camBtn=$('hmd-camera'),camNote=$('hmd-cam-note');
if(cam&&camBtn){let tracks=null;
 const off=()=>{if(tracks)tracks.forEach(x=>x.stop());tracks=null;cam.srcObject=null;document.body.classList.remove('cam-on');camBtn.textContent=T.camera;fitOff()};
 // ここで止まった: 押した後の 10 秒だけを録る（web.clips.camClip）。カメラを出していない時は何もしない。録る数がいっぱいの時は 1 行で知らせる
 const stuck=$('hmd-stuck');
 if(stuck)stuck.addEventListener('click',async()=>{if(!tracks||!window.utsushiClips||stuck.dataset.state==='rec')return;
  const r=await utsushiClips.camClip(cam.srcObject,{sid:T.sid,step:Number(body.dataset.at||0)+1,button:'stuck'});
  if(r==='full'){camNote.textContent=T.full;return}
  if(r==='rec'){stuck.dataset.state='rec';setTimeout(()=>{stuck.dataset.state=''},T.cam*1000)}});
 if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){camBtn.hidden=true;camNote.textContent=T.nocamera}
 camBtn.addEventListener('click',async()=>{if(tracks){off();return}
  try{const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});tracks=s.getTracks();cam.srcObject=s;
   document.body.classList.add('cam-on');camBtn.textContent=T.cameraoff;fitOn()}catch(_){camNote.textContent=T.nocamera}});
 addEventListener('pagehide',off);document.addEventListener('visibilitychange',()=>{if(document.hidden)off()})}
// ---- 重ねる（A）。合わせは舞台の transform だけで持つ（頁の置き場からのずれ・大きさ・向き）。頁の中だけに持ち、残さない・送らない
const fitBtn=$('hmd-reset');let fitting=false;const F={x:0,y:0,s:1,r:0};
// 舞台には頁の幅に合わせる縮尺（zoom）が掛かっていて、zoom は translate の長さにも掛かるので、ずれは zoom で割って画面の px に合わせる
const fitPut=()=>{const z=parseFloat(getComputedStyle(stage).zoom)||1;
 stage.style.transform='translate('+(F.x/z).toFixed(2)+'px,'+(F.y/z).toFixed(2)+'px) rotate('+F.r.toFixed(2)+'deg) scale('+F.s.toFixed(4)+')';
 // 試験と見る人の道具が、合わせた値を字でなく読めるように（画面の px のずれ・大きさ・向き）
 stage.dataset.fit=[F.x.toFixed(1),F.y.toFixed(1),F.s.toFixed(4),F.r.toFixed(2)].join(',')};
// 既定は重ね始めた所（頁の置き場・見えていた大きさ・向き 0）。重ねても 3D が跳ばない
const fitHome=()=>{Object.assign(F,{x:0,y:0,s:1,r:0});fitPut()};
function fitOn(){if(fitting)return;fitting=true;body.classList.add('fit-on');fitHome()}
function fitOff(){if(!fitting)return;fitting=false;body.classList.remove('fit-on');stage.style.transform='';delete stage.dataset.fit}
// 大きさは 0.3〜4 倍。真ん中は画面の中に留める（舞台の置き場の真ん中から、画面の端までのずれ）
const clampS=v=>Math.max(.3,Math.min(4,v)),keepIn=()=>{const r=stage.getBoundingClientRect(),cx=r.left+r.width/2-F.x,cy=r.top+r.height/2-F.y;
 F.x=Math.max(-cx,Math.min(innerWidth-cx,F.x));F.y=Math.max(-cy,Math.min(innerHeight-cy,F.y))};
// 指: 1 本で動かす・2 本で大きさ（指の間の長さの比）と向き（2 本を結ぶ線の角の差）と位置（2 本の真ん中）。始めの形から測るので、
// 指を足したり離したりしたら、残った指で測り直す（跳ばない）。capture の段で受けて先へ渡さない（kumitate の 1 本指の回しを止める）
const pts=new Map();let g0=null;
const begin=()=>{g0={F:{...F},p:[...pts.values()].map(q=>q.slice())}};
const ang=(a,b)=>Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI,len=(a,b)=>Math.hypot(b[0]-a[0],b[1]-a[1])||1,mid=(a,b)=>[(a[0]+b[0])/2,(a[1]+b[1])/2];
const onStage=e=>fitting&&e.target&&e.target.closest&&e.target.closest('.rt-stage')===stage;
document.addEventListener('pointerdown',e=>{if(!onStage(e))return;e.stopPropagation();e.preventDefault();pts.set(e.pointerId,[e.clientX,e.clientY]);
 try{stage.setPointerCapture(e.pointerId)}catch(_){}begin()},true);
document.addEventListener('pointermove',e=>{if(!fitting||!pts.has(e.pointerId))return;e.stopPropagation();e.preventDefault();pts.set(e.pointerId,[e.clientX,e.clientY]);
 const p=[...pts.values()],q=g0.p;
 if(p.length>=2&&q.length>=2){const c0=mid(q[0],q[1]),c=mid(p[0],p[1]);F.s=clampS(g0.F.s*len(p[0],p[1])/len(q[0],q[1]));
  F.r=g0.F.r+ang(p[0],p[1])-ang(q[0],q[1]);F.x=g0.F.x+c[0]-c0[0];F.y=g0.F.y+c[1]-c0[1]}
 else if(p.length===1&&q.length===1){F.x=g0.F.x+p[0][0]-q[0][0];F.y=g0.F.y+p[0][1]-q[0][1]}
 keepIn();fitPut()},true);
const lift=e=>{if(!pts.has(e.pointerId))return;e.stopPropagation();pts.delete(e.pointerId);begin()};
document.addEventListener('pointerup',lift,true);document.addEventListener('pointercancel',lift,true);
// Safari の gesture の知らせ（visionOS・Mac の板）。Pointer Events で 2 本の指が来ている時は使わない（同じ動きを 2 度効かせない）
let gs=null;
document.addEventListener('gesturestart',e=>{if(!onStage(e))return;e.preventDefault();gs=pts.size>=2?null:{...F}},true);
document.addEventListener('gesturechange',e=>{if(!fitting||!gs||pts.size>=2)return;e.preventDefault();F.s=clampS(gs.s*(e.scale||1));F.r=gs.r+(e.rotation||0);fitPut()},true);
document.addEventListener('gestureend',()=>{gs=null},true);
// 鍵: + − で大きさ、[ ] で向き、0 で元に戻す（→ ← スペースは手順の送りのまま）
document.addEventListener('keydown',e=>{if(!fitting||e.altKey||e.ctrlKey||e.metaKey)return;const el=e.target;if(el&&el.closest&&el.closest('input,textarea'))return;
 const k={'+':[1.1,0],'=':[1.1,0],'-':[1/1.1,0],'[':[1,-5],']':[1,5]}[e.key];
 if(k){e.preventDefault();F.s=clampS(F.s*k[0]);F.r+=k[1];fitPut()}else if(e.key==='0'){e.preventDefault();fitHome()}});
if(fitBtn)fitBtn.addEventListener('click',fitHome);
// 画面の向きや大きさが替わったら、既定を測り直して戻す（ずれた合わせのまま 3D を置かない）
addEventListener('resize',()=>{if(fitting)fitHome()});
// HMD の道は最初から重ねる（透ける画面の向こうに実物が見えるため。統括の決め ①）
if(document.querySelector('.hmd[data-fit-always]'))fitOn();
// 隠れたら聞くのを止め、見えたら聞いていた時だけ戻す。頁を離れたら止める（手帖の作り直しと同じ）
document.addEventListener('visibilitychange',()=>{if(document.hidden){if(rec)try{rec.stop()}catch(_){}}else{if(on&&rec)try{rec.start()}catch(_){}wake()}});
addEventListener('pagehide',()=>{if(on)stopListen()});
})()</script>"""


def available(sid):
    return sid in TOYS and kumitate.available(sid)


def page(sid, look="tenji", cam=False):
    """1 つの玩具の、作業しながら見る頁。帯と足は出さない（見る所を手順と 3D だけにする）。
    cam=True はカメラに重ねる頁（後ろのカメラの映像の上に手順と 3D。/toy/<印>/kasane）。cam=False は HMD 向け（/toy/<印>/kasane/hmd）。
    道は玩具ごとに置く: 作る口は手帖 1 つの決まり（地図の 1）なので、玩具を選ぶ頁は持たず、選びなおす時は えらぶ（/toys）へ戻す。"""
    toy = hypotheses.load(sid)["toy"]
    words = {"words": WORDS, "on": MIC_ON, "off": MIC_OFF, "none": NO_VOICE, "blocked": BLOCKED, "listen": LISTEN, "stop": STOP, "done": kumitate.DONE,
             "clean": CLEAN, "camera": CAMERA, "cameraoff": CAMERA_OFF, "nocamera": NO_CAMERA, "splitopen": SPLIT_OPEN, "splitclose": SPLIT_CLOSE,
             "sid": sid, "full": clips.FULL, "cam": clips.CAM_SECONDS}
    camera = ('<video id="hmd-cam" playsinline muted autoplay></video>' if cam else "")
    camera_btn = (f'<button type="button" id="hmd-camera">{esc(CAMERA)}</button><button type="button" id="hmd-stuck">{esc(STUCK)}</button>' if cam else "")
    # 手順の画面には長い断り（初めて録る時の 1 行・端末の置き場の 1 行）を置かず、カメラの断りの 1 行と、くわしい説明の頁（保護者の方へ）への道だけ
    # （統括の決め・別の目の止め 2: 320×568 で手順の画面に縦の送りが出た）。端末の置き場の 1 行は、のこすの確かめの画面に出す
    camera_note = (f'<span id="hmd-cam-note">{esc(CAM_NOTE)}</span> <a href="/otona">{esc(OTONA_LINK)}</a> <a href="/toy/{esc(sid)}/techo/kiroku">{esc(KEEP_LINK)}</a> ' if cam else "")
    # 組み立ての節を覚える鍵は、組み立ての節と同じ物（紙の寸法と組の名。kumitate._key）。寸法だけだと、組が替わっても前の組の立体を覚えている
    params = kumitate._key(sid)
    body = (f'<div class="hmd"><div class="hmd-top"><b>{esc(toy)}</b><span id="hmd-count"></span><span id="hmd-heard" aria-live="polite"></span>'
            f'<span class="hmd-mic" id="hmd-mic" data-state="off" aria-live="polite">{esc(MIC_OFF)}</span></div>'
            f'<p id="hmd-dots" aria-hidden="true"></p>'
            f'<div class="hmd-k">{kumitate._block_html(sid, params)}'
            f'<div class="hmd-acts"><button type="button" id="hmd-next">{esc(NEXT)}</button><button type="button" id="hmd-prev">{esc(PREV)}</button>'
            f'<button type="button" id="hmd-again">{esc(AGAIN)}</button><button type="button" id="hmd-listen" aria-pressed="false">{esc(LISTEN)}</button>{camera_btn}'
            f'<button type="button" id="hmd-split" aria-pressed="false">{esc(SPLIT_OPEN)}</button>'
            # 元に戻す は重ねている間だけ出す（重ねていない時は押す所の数を前のまま 6 つにする）
            f'<button type="button" id="hmd-reset">{esc(RESET)}</button></div></div>'
            f'<p class="hmd-note"><span id="hmd-fit-hint">{esc(FIT_HINT)} </span>{camera_note}{esc(HOW)} {esc(TRIAL)} <a href="/">玩具を選びなおす</a></p></div>{camera}'
            f'<script type="application/json" id="hmd-words">{json.dumps(words, ensure_ascii=False)}</script>{SCRIPT}' + (clips.assets() if cam else ""))
    # HMD の道は最初から重ねる（統括の決め ①）。頁の印で script に知らせる（字ではない）
    body = body if cam else body.replace('<div class="hmd">', '<div class="hmd" data-fit-always="1">', 1)
    return skin.shell(f"{toy}: {TITLE}", body, look, path=f"/toy/{sid}/kasane" + ("" if cam else "/hmd"), extra_style=STYLE,
                      body_class="hmd-page hmd-cam" if cam else "hmd-page")

