"""核の一周: 本人の定義（11-05 17:57）の 4 つのループ。①仮説を見ながら考えを話す → ②作りながら工夫を話す → その上でエンジンごと直る → ③できた物を上げて残す。

使い方: python -m demo.core <場面の名前> --out <repo の外の場所>/core.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 画面が撮れない・chrome か ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 本人の言葉（11-05）「今話してるこの部分が今回のハッカソンの核になる！！」。動画の真ん中に置き、見ている人が 3 段と輪を覚えて帰る形にする。
- 今ある物だけを、動いている画面として映す。作りながら見る頁・声で聞く口・写真を上げる手帖・ギャラリーは、
  本物の play_server を一時の置き場で立て、本物の口へ送ってから headless の Chrome で撮る（場面 3 と同じ作り）。
- まだ無い物（声の取り込み・エンジンごとの改善）は、動いているように見せない。core_map・core_voice・core_loop は図で描き、
  画面に「図」「これから」「いま作っているところ」と書く。撮れるようになったら、demo.build の --clip でその場面だけを差し替える。
- 本人の言葉（11-05 夕）「AIが良くなるのは副次的なもので、みんなが手で実際に作ることその楽しさに気づくことが最初。」で順番が決まった。
  組み立ては、手で作る所を長く → 持ち寄り → みんなの工夫で AI が次をよくする。地図（core_map）の真ん中は手で作る所で、AI の字を置かない。輪（core_loop）は持ち寄りの次に短く置く。
- 図は本人のループの定義の形にする。今動いていない所（型紙が生まれる・エンジンごと直る・システムが直る）は点線にして「いま作っているところ」と書く。
- つなぎ 2 の文は本人が決めた字のまま出す（本人の決定 11-05）。本人の言葉の札にはしないので、その印を付けない。
  本物の Claude API はまだ 1 度も動いていない。輪は図のままで、そう書く。聞く口の答えも AI の物に見せない（今の答えは型紙の言葉から出す）。
- 作りながら見る頁は手順を順に映す（1 → 2 → 3 で止まって聞く）。1 枚の絵に長く留まるより、作り進める所が伝わるため。手帖は上げる欄から上げた記録まで動く。
- 画面に映す例の記録は、字の頭に「（例）」を付け、隅の札に作り物と書く。人の報告に見せかけないため。写真は確かめ表で通った 11-04 の物だけ。
- 例の記録は本物の口（説明 → 次の版）まで通し、一時の置き場に版 2 を作って撮る。作りながら見る頁に出る「版 2」が、本物の口で作った版であるため。
- 顔と声は入れない（J-022）。鏡（カメラ）は押さないと動かないので、撮る画面には映らない。
- frame(t) は時刻だけから 1 コマを描く純関数（場面 1 と同じ）。合図は CUES だけを読むので、曲の拍に寄せられる。
"""
import argparse
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import types
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw

from demo.flip import H, PAPER, ROOT, SHU, SUMI, W, contact_sheet, ease, fade, render, text
from demo.scene3 import _chrome, _ensure_picture, _free_port, page_color
from demo.words import step_badge

SID = "NDL-1187053-R0000005-L"   # 御来迎の頁。場面 2・3 と同じ
HID = "H-A"
PHOTO = ROOT / "docs/process/trials/photos/20261104/p01.jpg"   # 確かめ表で通った写真（demo.scene5 の PHOTOS）
DPR = 2
BOX = (160, 196, 1760, 936)      # 画面を映す枠（場面 3 と同じ）
ASPECT = (BOX[3] - BOX[1]) / (BOX[2] - BOX[0])
SHOT_NOTE = "画面: utsushi の使い手の画面（play_server）を手元で動かして撮った"
EXAMPLE_NOTE = "（例）の記録は動画のための作り物。見本の札も作り物。写真は 11-04 の試行（U-24 の確かめ済み）"
SOON = "これから作る"

# 本物の口へ送る例の記録。どれも「（例）」で始める。
EXAMPLE = {"hypothesis": HID, "result": "動いた", "note": "（例）動画のために入れた例の記録です", "impression": "（例）筒を押すと扇が開いた。切る所が難しかった",
           "fix_part": "（例）内筒", "fix_change": "（例）土台の紙を 2 枚重ねた", "fix_outcome": "（例）押しやすくなった"}
EXPLAIN = {"text": "（例）扇の折りが多くて固く、開きにくいと読んだ", "next_idea": "（例）折りの数を減らす", "by": "（例）作った人"}
# 次の版で変える寸法。床（扇が筒に隠れる・開ける）を通る値を実際に送って選んだ。ここが通らない時は止める（通った振りをしない）。
NEXT = {"interpretation": "（例）折りが多くて固い", "param": "fold_count", "to": 24, "why": "（例）折りの数を減らして試す", "by": "（例）作った人"}

# 撮る頁: (道, 窓の幅, 測る所)
PAGES = {
    "make1": (f"/toy/{SID}/tsukuru?h={HID}&n=1", 1280, {"stage": ".stage"}),
    "make2": (f"/toy/{SID}/tsukuru?h={HID}&n=2", 1280, {"stage": ".stage"}),
    "make": (f"/toy/{SID}/tsukuru?h={HID}&n=3&ev=stuck", 1280, {"stage": ".stage", "henji": "#henji"}),
    "keep": (f"/toy/{SID}/techo", 1000, {"up": '[aria-label="上げる"]'}),
    "gallery": ("/gallery", 1400, {"made": "#ageta"}),
}

# 本人のループの定義（11-05 17:57）。(札, 上の箱の行, 下の箱の並び)。下の箱は (行, いま作っているところか)。無い物を有るように見せない。
LOOPS = (
    ("ループ 1", ("① 仮説を見ながら", "考えを話す"), ((("反応して", "型紙が生まれる"), True),)),
    ("ループ 2", ("② 作りながら", "工夫を話す"), ((("型紙が直る",), False),)),
    ("ループ 3", ("その上で",), ((("エンジンごと直る",), True),)),
    ("ループ 4", ("③ できた物を", "上げて残す"), ((("ギャラリーで見られる",), False), (("型紙も直る",), False), (("システムも直る",), True))),
)
NOW_MAKING = "いま作っているところ"
COL_W, COL_GAP, COL_X0 = 412, 36, 82   # ループの列の幅・間・左端
TOP_H, ARROW_H, ONE_H, STACK_H, STACK_GAP = 170, 70, 170, 100, 12   # 上の箱・矢印の所・下の箱 1 つの時・積む時・積む間の高さ
MAP_Y, LOOP_Y = 228, 248               # 地図と輪の図の札の高さ。輪の図は上につなぎの字がある
MAP_TITLE = "ここが真ん中: 手で作る"
MAP_SUB = "4 つのループの図です。実線は今ある所。点線はいま作っているところ"
# つなぎ 2（本人の決定 11-05）。字は変えない。行の切れ目だけで分ける。
BRIDGE2 = ("作ったものを持ちよると、AI もそれを見て、", "次の型紙を少しずつよくしていきます。")
NOW_LINE = "いま作っているところです"
VOICE_LINE = "話した声とカメラの様子を取り込む所は、これから作ります"
AI_NOTE = "本物の Claude API は、まだ 1 度も動かしていません"
GALLERY_PAN = 850                # ギャラリーの列を下へ動く量（CSS の px）。節の高さを越えない所で止める
MAKE_NOTE = "工夫を声で残す口は、これから作ります。今の聞く口は、型紙の言葉から答えます。AI の答えは、まだ動かしていません"
VOICE_BOXES = ("話す・映す", "字と札にする", "工夫と考えの記録へ")

SECONDS = {"core_map": 9.0, "core_make": 14.0, "core_keep": 9.0, "core_voice": 4.0, "core_gallery": 9.0, "core_loop": 9.0}
CUES_ALL = {
    "core_map": {"title": (0.0, 0.6), "l1": (0.6, 1.2), "l2": (1.6, 2.2), "l3": (2.6, 3.2), "l4": (3.6, 4.2), "voice": (4.8, 5.4)},
    "core_make": {"in": (0.0, 0.8), "step2": (3.6, 4.0), "step3": (7.2, 7.6), "move": (10.0, 11.2)},
    "core_keep": {"in": (0.0, 0.8), "move": (1.4, 2.6), "record": (5.0, 5.2), "move2": (5.2, 6.4)},
    "core_voice": {"in": (0.0, 0.4), "b1": (0.4, 0.8), "b2": (0.9, 1.3), "b3": (1.4, 1.8)},
    "core_gallery": {"in": (0.0, 0.8), "pan": (2.0, 6.0)},
    "core_loop": {"title": (0.0, 0.6), "now": (0.6, 1.2), "loops": (1.2, 2.2)},
}
_SHOTS = {}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _post(base, path, data, ctype="application/x-www-form-urlencoded"):
    """本物の口へ送る。(番号, 中身) を返す。別のサイトからの送信を断る門を通すため Origin を付ける。"""
    body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
    req = urllib.request.Request(base + path, data=body, headers={"Origin": base, "Content-Type": ctype})
    try:
        r = urllib.request.build_opener(NoRedirect).open(req, timeout=120)
        return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")


def seed(base):
    """一時の置き場に、例の記録・写真・説明・次の版を本物の口で入れる。通らない時は言って止める（通った振りをしない）。"""
    if _post(base, f"/toy/{SID}/print", {"hypothesis": HID})[0] != 303:
        raise OSError("型紙が刷れない")
    code, out = _post(base, f"/toy/{SID}/record-json", EXAMPLE)
    if code != 201:
        raise OSError(f"例の記録が入らない（{code}）")
    rid = json.loads(out)["id"]
    if _post(base, f"/record/{rid}/media", PHOTO.read_bytes(), "image/jpeg")[0] != 201:
        raise OSError("写真が入らない")
    if _post(base, f"/record/{rid}/explain", EXPLAIN)[0] != 303:
        raise OSError("説明が入らない")
    code, out = _post(base, f"/record/{rid}/next", NEXT)
    if code != 303:
        raise OSError(f"次の版が刷れない（{code}）")
    return rid


def _measure(chrome, tmp, base, path, selectors, width):
    """同じ HTML を Chrome に読ませ、測る所と頁の高さを返す（CSS の px）。本物の頁には手を入れず、写しに測る script を足す。"""
    html = urllib.request.urlopen(base + path, timeout=30).read().decode("utf-8")
    pick = json.dumps(selectors, ensure_ascii=False)
    js = (f'<script>addEventListener("load",()=>{{const o={{h:document.documentElement.scrollHeight}},s={pick};for(const k in s){{const e=document.querySelector(s[k]);'
          'if(e){const b=e.getBoundingClientRect();o[k]=[b.x,b.y+scrollY,b.width,b.height]}}'
          'const p=document.createElement("pre");p.id="rects";p.textContent=JSON.stringify(o);document.body.appendChild(p)})</script>')
    copy = pathlib.Path(tmp) / "copy.html"
    copy.write_text(html.replace('<meta charset="utf-8">', f'<meta charset="utf-8"><base href="{base}/">', 1).replace("</body>", js + "</body>") if "</body>" in html
                    else html.replace('<meta charset="utf-8">', f'<meta charset="utf-8"><base href="{base}/">', 1) + js, encoding="utf-8")
    r = _chrome(chrome, tmp, [f"--window-size={width},1200", "--dump-dom", copy.as_uri()])
    start = r.stdout.find('<pre id="rects">')
    if start < 0:
        return None
    return json.loads(r.stdout[start + 16:r.stdout.index("</pre>", start)])


def capture(cache):
    """本物の画面を撮って {名前: (絵, 測った所)} を返す。同じ書き出しの中では 1 回だけ撮る（どの場面も同じ頁を映すので）。撮れない時は None。"""
    if _SHOTS:
        return _SHOTS
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        print("検査できない: chrome が無い", file=sys.stderr)
        return None
    _ensure_picture(SID)
    out = pathlib.Path(cache) / "core"
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="core-") as tmp:
        port = _free_port()
        base = f"http://127.0.0.1:{port}"
        # 一時の置き場に向けるので、repo の data/ に例の記録が残らない。
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "OMOCHAE_DATA": f"{tmp}/data"}
        proc = subprocess.Popen([sys.executable, "-m", "web.play_server", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(base + "/", timeout=5)
                    break
                except OSError:
                    time.sleep(0.2)
            else:
                print("検査できない: 画面の口が開かない", file=sys.stderr)
                return None
            try:
                seed(base)
            except OSError as e:
                print(f"検査できない: {e}", file=sys.stderr)
                return None
            shots = {}
            for name, (path, width, selectors) in PAGES.items():
                rects = _measure(chrome, tmp, base, path, selectors, width)
                if not rects or any(k not in rects for k in selectors):
                    print(f"検査できない: 頁の所が測れない（{name}）", file=sys.stderr)
                    return None
                png = out / f"{name}.png"
                png.unlink(missing_ok=True)
                _chrome(chrome, tmp, [f"--force-device-scale-factor={DPR}", f"--window-size={width},{math.ceil(rects['h'])}", f"--screenshot={png}", base + path])
                if not png.exists():
                    print(f"検査できない: 画面が撮れない（{name}）", file=sys.stderr)
                    return None
                shots[name] = (Image.open(png).convert("RGB"), rects, width)
        finally:
            proc.terminate()
            proc.wait(timeout=10)
    _SHOTS.update(shots)
    return _SHOTS


def _view(shot, cam, box=BOX, dpr=DPR):
    """撮った画面の cam (中心 x, 中心 y, 幅) の所を、枠の大きさに写す。枠の外は画面の地の色で埋める。"""
    cx, cy, cw = cam
    bw, bh = box[2] - box[0], box[3] - box[1]
    k = bw / (cw * dpr)
    x0, y0 = (cx - cw / 2) * dpr, (cy - cw * (bh / bw) / 2) * dpr
    return shot.transform((bw, bh), Image.AFFINE, (1 / k, 0, x0, 0, 1 / k, y0), resample=Image.BICUBIC, fillcolor=page_color(shot))


def _lerp(c0, c1, u):
    return (c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u, c0[2] * (c1[2] / c0[2]) ** u)


def _cam_on(rect, margin=1.08, top=True, aspect=ASPECT):
    """測った所へ寄るカメラ。top は所の頭を枠の上に合わせる（長い節の頭から読ませるため）。"""
    x, y, w, h = rect
    cw = max(w * margin, 700)
    return (x + w / 2, (y - 20 + cw * aspect / 2) if top else y + h / 2, cw)


def _cam_page(page_w, margin=1.04, aspect=ASPECT):
    """頁の頭から全体の幅を映すカメラ。題から読ませる（途中から映すと、何の頁か分からない）。"""
    cw = page_w * margin
    return (page_w / 2, cw * aspect / 2, cw)


class Screens:
    """本物の画面を映す場面。segs: 段ごとの (始まりの合図, 絵の名前, カメラの始まり, カメラの終わり, 題, 副題)。"""

    def __init__(self, name, cues, shots, step, note, segs):
        self.cues, self.step, self.note, self.segs = cues, step, note, segs
        self.shots = shots
        self.duration = SECONDS[name]

    def _p(self, t, cue):
        a, b = self.cues[cue]
        return ease((t - a) / (b - a))

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        a_in = self._p(t, "in")
        seg = 0
        for i, s in enumerate(self.segs):
            if s["at"] is None or t >= self.cues[s["at"]][0]:
                seg = i
        s = self.segs[seg]
        u = self._p(t, s["move"]) if s.get("move") else 0.0
        view = _view(self.shots[s["shot"]][0], _lerp(s["from"], s["to"], u))
        prev = self.segs[seg - 1] if seg else None
        blend = self._p(t, s["at"]) if s["at"] else a_in
        if blend < 1:
            # 段の替わり目は前の画面から重ねて替える。紙の地を挟むと、手順が進むたびに点滅して見えるため。
            base = _view(self.shots[prev["shot"]][0], prev["to"]) if prev else Image.new("RGB", view.size, PAPER)
            view = Image.blend(base, view, blend)
        img.paste(view, BOX[:2])
        draw.rectangle((BOX[0] - 1, BOX[1] - 1, BOX[2], BOX[3]), outline=fade(SUMI, 0.35 * (1.0 if prev else blend)), width=2)
        # 同じ字幕が続く段では字を替えない
        same = prev and (prev["title"], prev["sub"]) == (s["title"], s["sub"])
        words_in = a_in if same else blend
        text(draw, (80, 62), s["title"], 52, fade(SUMI, words_in), True)
        text(draw, (80, 132), s["sub"], 34, fade(SUMI, words_in))
        if self.step:
            step_badge(draw, self.step, a_in)
        for i, line in enumerate((SHOT_NOTE, s.get("note", self.note))):
            text(draw, (80, H - 82 + 30 * i), line, 22, fade(SUMI, 0.7))
        return img


def _arrow(draw, a, b, color, width=4, dashed=False):
    (x0, y0), (x1, y1) = a, b
    n = math.hypot(x1 - x0, y1 - y0)
    if n == 0:
        return
    ux, uy = (x1 - x0) / n, (y1 - y0) / n
    if dashed:
        d = 0.0
        while d < n - 22:
            e = min(d + 16, n - 18)
            draw.line((x0 + ux * d, y0 + uy * d, x0 + ux * e, y0 + uy * e), fill=color, width=width)
            d += 30
    else:
        draw.line((x0, y0, x1 - ux * 16, y1 - uy * 16), fill=color, width=width)
    draw.polygon([(x1, y1), (x1 - ux * 22 - uy * 11, y1 - uy * 22 + ux * 11), (x1 - ux * 22 + uy * 11, y1 - uy * 22 - ux * 11)], fill=color)


def _box(draw, xyxy, color, width=3, dashed=False):
    x0, y0, x1, y1 = xyxy
    if not dashed:
        draw.rounded_rectangle(xyxy, 14, outline=color, width=width)
        return
    for x in range(int(x0), int(x1), 28):
        draw.line((x, y0, min(x + 14, x1), y0), fill=color, width=width)
        draw.line((x, y1, min(x + 14, x1), y1), fill=color, width=width)
    for y in range(int(y0), int(y1), 28):
        draw.line((x0, y, x0, min(y + 14, y1)), fill=color, width=width)
        draw.line((x1, y, x1, min(y + 14, y1)), fill=color, width=width)


def _lines_mid(d, cx, cy, lines, size, color, gap):
    """行を縦の真ん中 cy にそろえて描く。"""
    top = cy - (len(lines) * gap) / 2
    for i, line in enumerate(lines):
        text(d, (cx, top + i * gap), line, size, color, True, "ma")


def _loop(d, i, y, a, strong=False, dash=1.0):
    """ループを 1 本描く。上の箱（人がする事）と下の箱（返ってくる事）を、行きと帰りの矢印でつなぐ。
    今動いていない所は点線にして「いま作っているところ」と書く。y は札の高さ、a は濃さ。strong は手で作る所の朱の太い枠。"""
    name, top, results = LOOPS[i]
    x = COL_X0 + i * (COL_W + COL_GAP)
    cx = x + COL_W // 2
    text(d, (x, y), name, 30, fade(SUMI, 0.8 * a), True)
    y0 = y + 46
    if strong:
        _box(d, (x, y0, x + COL_W, y0 + TOP_H), fade(SHU, a), 7)
    else:
        _box(d, (x, y0, x + COL_W, y0 + TOP_H), fade(SUMI, 0.7 * a))
    _lines_mid(d, cx, y0 + TOP_H // 2 - 6, top, 38, fade(SUMI, a), 56)
    y1 = y0 + TOP_H + ARROW_H
    now = results[0][1]
    color = fade(SHU, dash * a) if now else fade(SUMI, 0.7 * a)
    _arrow(d, (x + COL_W * 0.66, y0 + TOP_H + 6), (x + COL_W * 0.66, y1 - 6), color, dashed=now)
    _arrow(d, (x + COL_W * 0.34, y1 - 6), (x + COL_W * 0.34, y0 + TOP_H + 6), color, dashed=now)
    h = ONE_H if len(results) == 1 else STACK_H
    for lines, now in results:
        if now:
            _box(d, (x, y1, x + COL_W, y1 + h), fade(SHU, dash * a), dashed=True)
            _lines_mid(d, cx, y1 + h // 2 - 22, lines, 36, fade(SUMI, a), 46)
            text(d, (cx, y1 + h - 38), NOW_MAKING, 24, fade(SHU, a), True, "ma")
        else:
            _box(d, (x, y1, x + COL_W, y1 + h), fade(SUMI, 0.7 * a))
            _lines_mid(d, cx, y1 + h // 2 - 6, lines, 36, fade(SUMI, a), 46)
        y1 += h + STACK_GAP
    if i:
        _arrow(d, (x - COL_GAP + 4, y0 + TOP_H // 2), (x - 4, y0 + TOP_H // 2), fade(SUMI, 0.7 * a))


class MapCard:
    """4 つのループの図（本人の定義 11-05 17:57）。動画の真ん中の地図。動いている画面ではないので「図」と書く。
    真ん中は手で作る所で（②を朱の枠にする）、AI の字は置かない（本人の言葉 11-05 夕: AI が良くなるのは副次的）。"""

    def __init__(self, cues):
        self.cues = cues
        self.duration = SECONDS["core_map"]

    def _p(self, t, cue):
        a, b = self.cues[cue]
        return ease((t - a) / (b - a))

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        a = self._p(t, "title")
        text(d, (80, 62), MAP_TITLE, 56, fade(SUMI, a), True)
        text(d, (80, 136), MAP_SUB, 34, fade(SUMI, a))
        text(d, (W - 80, 76), "図", 30, fade(SUMI, 0.7 * a), False, "ra")
        for i in range(len(LOOPS)):
            v = self._p(t, f"l{i + 1}")
            if v > 0:
                _loop(d, i, MAP_Y, v, strong=i == 1, dash=0.7)
        v = self._p(t, "voice")
        if v > 0:
            text(d, (W // 2, 880), VOICE_LINE, 30, fade(SHU, v), False, "ma")
        return img


class VoiceCard:
    """声とカメラで残す所の図。まだ無いので、動いているように見せない。撮れたら --clip core_voice=… で差し替える。"""

    def __init__(self, cues):
        self.cues = cues
        self.duration = SECONDS["core_voice"]

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        p = lambda c: ease((t - self.cues[c][0]) / (self.cues[c][1] - self.cues[c][0]))
        a = p("in")
        text(d, (80, 62), "カメラか音声で、工夫と考えを残す", 52, fade(SUMI, a), True)
        text(d, (80, 132), f"{SOON}所の図です。動いている画面ではありません", 34, fade(SHU, a), True)
        step_badge(d, 3, a)
        bw, gap, x0, y0, bh = 480, 80, 110, 400, 200
        for i, label in enumerate(VOICE_BOXES):
            v = p(f"b{i + 1}")
            if v <= 0:
                continue
            x = x0 + i * (bw + gap)
            _box(d, (x, y0, x + bw, y0 + bh), fade(SHU, v), dashed=True)
            text(d, (x + bw // 2, y0 + 72), label, 44, fade(SUMI, v), True, "ma")
            if i < 2:
                _arrow(d, (x + bw + 8, y0 + bh // 2), (x + bw + gap - 8, y0 + bh // 2), fade(SHU, v), dashed=True)
        text(d, (W // 2, 680), "カメラで見るのは、不完全な型紙を人が工夫で乗り切る過程。人の出来は測らない", 36, fade(SUMI, p("b3")), False, "ma")
        return img


class LoopCard:
    """つなぎ 2 と 4 つのループの図。AI はまだ動いていないので「いま作っているところです」を一緒に出す（本人の決定 11-05）。
    地図と同じ形にして、最初に見た図の点線の所へ話が戻ったと分かるようにする。撮れたら --clip core_loop=… で差し替える。"""

    def __init__(self, cues):
        self.cues = cues
        self.duration = SECONDS["core_loop"]

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        p = lambda c: ease((t - self.cues[c][0]) / (self.cues[c][1] - self.cues[c][0]))
        a = p("title")
        for i, line in enumerate(BRIDGE2):
            text(d, (80, 52 + i * 62), line, 48, fade(SUMI, a), True)
        text(d, (80, 180), NOW_LINE, 36, fade(SHU, p("now")), True)
        text(d, (W - 80, 76), "図", 30, fade(SUMI, 0.7 * a), False, "ra")
        v = p("loops")
        if v > 0:
            for i in range(len(LOOPS)):
                _loop(d, i, LOOP_Y, v)
            text(d, (W // 2, 910), AI_NOTE, 28, fade(SUMI, 0.85 * v), False, "ma")
        return img


def build_scene(name, cues, cache=None, shots=None):
    """場面の絵の作りを返す。shots は試験で偽の画面を渡す口。"""
    if name == "core_map":
        return MapCard(cues)
    if name == "core_voice":
        return VoiceCard(cues)
    if name == "core_loop":
        return LoopCard(cues)
    shots = shots or capture(cache)
    if not shots:
        return None
    if name == "core_make":
        rects = shots["make"][1]
        head = _cam_page(shots["make"][2])
        words = {"title": "作りながら見る頁", "sub": "手順を見ながら作る。止まったら、そのまま声か字で聞ける"}
        return Screens(name, cues, shots, 2, MAKE_NOTE, [
            {"at": None, "shot": "make1", "from": head, "to": head, **words},
            {"at": "step2", "shot": "make2", "from": head, "to": head, **words},
            {"at": "step3", "shot": "make", "move": "move", "from": head, "to": _cam_on(rects["henji"], 1.5), **words}])
    if name == "core_keep":
        rects = shots["keep"][1]
        up = _cam_on(rects["up"], 1.95)  # 「工夫した所」の欄まで映す。字幕がそこを言っているので
        record = (up[0], max(up[1], rects["up"][1] + rects["up"][3] - up[2] * ASPECT / 2 + 10), up[2])  # 節の下の端、上げた記録の所
        words = {"title": "写真を上げる手帖", "sub": "できた物の写真と、工夫した所を記録に添える"}
        return Screens(name, cues, shots, 3, "カメラと声で残す口はこれから。今あるのは写真と工夫の欄", [
            {"at": None, "shot": "keep", "move": "move", "from": _cam_page(shots["keep"][2], 1.3), "to": up, **words},
            {"at": "record", "shot": "keep", "move": "move2", "from": up, "to": record, "note": EXAMPLE_NOTE, **words}])
    if name == "core_gallery":
        made = shots["gallery"][1]["made"]
        top = _cam_on([made[0], made[1] + 10, made[2], made[3]], 1.1)  # 節の上の見出しの下線を枠に入れない
        # 持ち寄られた物の列を下へ動く。1 つの記録だけに見せず、何人もの物が集まる場だと分かるように。
        lower = (top[0], top[1] + min(GALLERY_PAN, max(0, made[3] - top[2] * ASPECT)), top[2])
        return Screens(name, cues, shots, 0, EXAMPLE_NOTE, [
            {"at": None, "shot": "gallery", "move": "pan", "from": top, "to": lower, "title": "他の人が作った物", "sub": "作った物が持ち寄られ、ギャラリーで見られる"}])
    raise KeyError(name)


def _render(name, cues, argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    a = ap.parse_args(argv)
    try:
        scene = build_scene(name, cues, a.cache)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"検査できない: 画面が撮れない（{e}）", file=sys.stderr)
        return 4
    if scene is None:
        return 4
    if a.sheet:
        d = scene.duration
        contact_sheet(scene, a.sheet, tuple(round(d * k, 2) for k in (0.05, 0.15, 0.3, 0.42, 0.55, 0.65, 0.75, 0.88, 0.99)))
    return render(scene, pathlib.Path(a.out))


_MODULES = {}


def scene_module(name):
    """他の場面と同じ形の入口を返す。CUES は同じ物を返す（曲の拍合わせが中の時刻を動かすため）。"""
    if name not in _MODULES:
        cues = dict(CUES_ALL[name])
        _MODULES[name] = types.SimpleNamespace(CUES=cues, DURATION=SECONDS[name], main=lambda argv=None: _render(name, cues, argv))
    return _MODULES[name]


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in SECONDS:
        print(f"検査できない: 場面の名前は {'・'.join(SECONDS)}", file=sys.stderr)
        sys.exit(4)
    sys.exit(scene_module(sys.argv[1]).main(sys.argv[2:]))
