"""核の一周: 本人の定義（11-05 17:57）の 4 つのループ。①仮説を見ながら考えを話す → ②作りながら工夫を話す → その上でエンジンごと直る → ③できた物を上げて残す。

使い方: python -m demo.core <場面の名前> --out <repo の外の場所>/core.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 画面が撮れない・chrome か ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 本人の方針（11-05 20:10）「たくさん見る審査員の認知負荷を減らす方針が1番最初。癒し系で。」。画面の字は 1 度に 1 かたまりだけで、上に 1 行。
  題・副題・段の印・隅の札は外した。撮った画面である事と作り物の断りはクレジットへ寄せた（demo.scene7）。替わり目はゆっくり溶かす。
- 今ある物だけを、動いている画面として映す。作りながら見る頁・声で聞く口・写真を上げる手帖・ギャラリーは、
  本物の play_server を一時の置き場で立て、本物の口へ送ってから headless の Chrome で撮る（場面 3 と同じ作り）。
- まだ無い物（声の取り込み・エンジンごとの改善）は、動いているように見せない。core_map・core_voice・core_loop は図で描き、
  点線と「いま作っているところです」で分かるようにする。撮れるようになったら、demo.build の --clip でその場面だけを差し替える。
- 本人の言葉（11-05 夕）「AIが良くなるのは副次的なもので、みんなが手で実際に作ることその楽しさに気づくことが最初。」で順番が決まった。
  組み立ては、手で作る所を長く → 持ち寄り → みんなの工夫で AI が次をよくする。地図（core_map）の真ん中は手で作る所で、AI の字を置かない。輪（core_loop）は持ち寄りの次に置く。
- 図は本人のループの定義の形にする。今動いていない所（型紙が生まれる・エンジンごと直る・システムが直る）は点線にする。
- つなぎ 2 の文は本人が決めた字のまま出す（本人の決定 11-05）。本人の言葉の札にはしないので、その印を付けない。
- 作りながら見る頁は手順を順に映す（1 → 2 → 3 で止まって聞く）。1 枚の絵に長く留まるより、作り進める所が伝わるため。手帖は上げる欄から上げた記録まで動く。
- 画面に映す例の記録は、字の頭に「（例）」を付ける。人の報告に見せかけないため。写真は確かめ表で通った 11-04 の物だけ。
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
from demo.words import chunk_alpha, chunks_of, cues_of, draw_chunk, seconds_of

SID = "NDL-1187053-R0000005-L"   # 御来迎の頁。場面 2・3 と同じ
HID = "H-A"
PHOTO = ROOT / "docs/process/trials/photos/20261104/p01.jpg"   # 確かめ表で通った写真（demo.scene5 の PHOTOS）
DPR = 2
BOX = (160, 196, 1760, 936)      # 画面を映す枠（場面 3 と同じ）
ASPECT = (BOX[3] - BOX[1]) / (BOX[2] - BOX[0])
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

# 本人のループの定義（11-05 17:57）を輪の形にした。(上の字, 輪の中の字, 輪の形)。形は done = 実線 / now = 点線 / half = 半分が点線。
# 今動いていない所（型紙が生まれる・エンジンごと直る・システムが直る）を点線にする。無い物を有るように見せない。
LOOPS = (
    ("① 考えを話す", ("型紙が", "生まれる"), "now"),
    ("② 作りながら話す", ("型紙が", "直る"), "done"),
    ("その上で", ("エンジンごと", "直る"), "now"),
    ("③ 上げて残す", ("ギャラリーへ", "型紙も", "システムも直る"), "half"),
)
RING_R, RING_XS = 150, (300, 740, 1180, 1620)  # 輪の半径と、輪の真ん中の横の位置
MAP_Y, LOOP_Y = 500, 640                       # 地図と輪の図の、輪の真ん中の高さ
# 字幕の案（本人の確認待ち。docs/demo/plan.md の 4）。短く、1 かたまりで。
MAP_TITLE = "真ん中は、手で作る所。"
MAP_SUB = "点線は、これから作る所。"
GALLERY_LINE = "作った物を、持ちよる。"
GALLERY_PAN = 620                # ギャラリーの列を下へ動く量（CSS の px）。節の高さを越えない所で止める。速く見えない量にした
VOICE_BOXES = ("話す・映す", "字と札にする", "工夫と考えの記録へ")

SECONDS = {"core_map": 9.0, "core_make": 12.0, "core_keep": 7.0, "core_voice": 4.0, "core_gallery": 5.0, "core_loop": seconds_of("core_loop")}
CUES_ALL = {
    "core_map": {"title": (0.0, 0.8), "l1": (0.8, 1.6), "l2": (1.8, 2.6), "l3": (2.8, 3.6), "l4": (3.8, 4.6), "sub": (5.2, 6.0)},
    "core_make": {"in": (0.0, 0.8), "step2": (3.0, 3.8), "step3": (6.0, 6.8), "move": (7.0, 8.2), "ask": (8.2, 8.7)},
    "core_keep": {"in": (0.0, 0.8), "move": (0.8, 2.0), "record": (3.2, 3.4), "move2": (3.4, 4.6)},
    "core_voice": {"in": (0.0, 0.4), "b1": (0.4, 0.8), "b2": (0.9, 1.3), "b3": (1.4, 1.8)},
    "core_gallery": {"in": (0.0, 0.8), "pan": (1.0, 4.2)},
    "core_loop": dict(sorted({**cues_of("core_loop"), "rings": (0.4, 2.4)}.items(), key=lambda kv: kv[1])),
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


# 写真の確認の記録を残す（media_review）。人の確認の場の代わりではなく、作り物の記録を一時の置き場で撮るためだけの物。
REVIEW_CODE = ("import sys; from omochae import media_review as m; "
               "f = m.record(sys.argv[1], sys.argv[2], 'object', '確認者'); print(f, file=sys.stderr) if f else None; sys.exit(3 if f else 0)")


def seed(base, env):
    """一時の置き場に、例の記録・写真・説明・次の版を本物の口で入れる。通らない時は言って止める（通った振りをしない）。
    写真は確認の記録が無いとギャラリーに出ない（#314）。env は画面の口と同じ置き場を指すので、repo の data/ には書かない。"""
    if _post(base, f"/toy/{SID}/print", {"hypothesis": HID})[0] != 303:
        raise OSError("型紙が刷れない")
    code, out = _post(base, f"/toy/{SID}/record-json", EXAMPLE)
    if code != 201:
        raise OSError(f"例の記録が入らない（{code}）")
    rid = json.loads(out)["id"]
    code, name = _post(base, f"/record/{rid}/media", PHOTO.read_bytes(), "image/jpeg")
    if code != 201:
        raise OSError("写真が入らない")
    r = subprocess.run([sys.executable, "-c", REVIEW_CODE, rid, name.strip()], cwd=ROOT, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise OSError(f"写真の確認の記録が残らない（{r.stderr.strip()[:200]}）")
    if f"/record/{rid}/media/{name.strip()}" not in urllib.request.urlopen(base + "/gallery", timeout=30).read().decode("utf-8"):
        raise OSError("ギャラリーに写真が出ない")
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
                seed(base, env)
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
    """本物の画面を映す場面。segs: 段ごとの {at: 始まりの合図, shot: 絵の名前, move: 動く合図, from/to: カメラ, line: 上の 1 行}。"""

    def __init__(self, name, cues, shots, segs):
        self.cues, self.segs = cues, segs
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
        draw.rectangle((BOX[0] - 1, BOX[1] - 1, BOX[2], BOX[3]), outline=fade(SUMI, 0.3 * (1.0 if prev else blend)), width=2)
        # 上の 1 行。同じ字が続く段では替えない。字が替わる時は、前が消えてから次が現れる。
        at = self.cues[s["at"]][0] if s["at"] else 0.0
        v = ease((t - at) / 0.5) if not (prev and prev["line"] == s["line"]) else 1.0
        nxt = self.segs[seg + 1] if seg + 1 < len(self.segs) else None
        if nxt and nxt["line"] != s["line"]:
            v *= 1 - ease((t - (self.cues[nxt["at"]][0] - 0.5)) / 0.5)
        if s["line"] and v > 0:
            text(draw, (W // 2, 78), s["line"], 52, fade(SUMI, v), False, "ma")
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
        text(d, (cx, top + i * gap), line, size, color, False, "ma")


def _ring(d, cx, cy, r, spans, width=4):
    """輪を 1 本描く。spans は (始めの度, 終わりの度, 色, 点線か) の並びで、時計回り。最後の端に矢じりを付ける。"""
    box = (cx - r, cy - r, cx + r, cy + r)
    for a0, a1, color, dashed in spans:
        if dashed:
            a = a0
            while a < a1:
                d.arc(box, a, min(a + 9, a1), fill=color, width=width)
                a += 18
        else:
            d.arc(box, a0, a1, fill=color, width=width)
    end = math.radians(spans[-1][1])
    px, py = cx + r * math.cos(end), cy + r * math.sin(end)
    tx, ty = -math.sin(end), math.cos(end)   # 時計回りの向き
    nx, ny = -ty, tx
    d.polygon([(px + tx * 14, py + ty * 14), (px - tx * 8 + nx * 11, py - ty * 8 + ny * 11), (px - tx * 8 - nx * 11, py - ty * 8 - ny * 11)],
              fill=spans[-1][2])


def _rings(d, cy, alphas, strong=None, dash=1.0):
    """4 つの輪を横に並べて描く。alphas は輪ごとの濃さ。strong は太くする輪（手で作る所）。dash は点線の濃さ。"""
    for i, (label, inside, kind) in enumerate(LOOPS):
        a = alphas[i]
        if a <= 0:
            continue
        x = RING_XS[i]
        done, now = fade(SUMI, 0.65 * a), fade(SHU, dash * a)
        spans = {"done": ((-70, 250, done, False),), "now": ((-70, 250, now, True),), "half": ((-70, 90, done, False), (90, 250, now, True))}[kind]
        _ring(d, x, cy, RING_R, spans, 8 if i == strong else 4)
        text(d, (x, cy - RING_R - 66), label, 34, fade(SUMI, a), False, "ma")
        _lines_mid(d, x, cy, inside, 32, fade(SUMI, a), 46)
        if i:
            _arrow(d, (x - 440 + RING_R + 14, cy), (x - RING_R - 14, cy), fade(SUMI, 0.45 * a))


class MapCard:
    """4 つのループの図（本人の定義 11-05 17:57）。動画の真ん中の地図。動いている画面ではない。
    真ん中は手で作る所で（②の輪を太くする）、AI の字は置かない（本人の言葉 11-05 夕: AI が良くなるのは副次的）。"""

    def __init__(self, cues):
        self.cues = cues
        self.duration = SECONDS["core_map"]

    def _p(self, t, cue):
        a, b = self.cues[cue]
        return ease((t - a) / (b - a))

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        text(d, (W // 2, 96), MAP_TITLE, 60, fade(SUMI, self._p(t, "title")), False, "ma")
        _rings(d, MAP_Y, [self._p(t, f"l{i + 1}") for i in range(len(LOOPS))], strong=1, dash=0.7)
        v = self._p(t, "sub")
        if v > 0:
            text(d, (W // 2, 860), MAP_SUB, 40, fade(SUMI, v), False, "ma")
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
    """つなぎ 2 と 4 つのループの図。字は 1 かたまりずつ。AI はまだ動いていないので「いま作っているところです」を一緒に出す（本人の決定 11-05）。
    その字が出る間は点線の輪を濃くして、どこの話かを絵で分かるようにする。撮れたら --clip core_loop=… で差し替える。"""

    def __init__(self, cues):
        self.cues = cues
        self.duration = SECONDS["core_loop"]
        self.chunks = chunks_of("core_loop")

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        n = len(self.chunks)
        for i, lines in enumerate(self.chunks):
            v = chunk_alpha(self.cues, n, i, t)
            if v > 0:
                draw_chunk(d, lines, W // 2, 200, 56, v)
        a, b = self.cues["rings"]
        v = ease((t - a) / (b - a))
        if v > 0:
            near = ease((t - self.cues[f"c{n - 1}"][0]) / 0.5)
            _rings(d, LOOP_Y, [v] * len(LOOPS), dash=0.5 + 0.5 * near)
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
        head, stuck = _cam_page(shots["make"][2]), _cam_on(rects["henji"], 1.5)
        line = "手順を見ながら作る。"
        return Screens(name, cues, shots, [
            {"at": None, "shot": "make1", "from": head, "to": head, "line": line},
            {"at": "step2", "shot": "make2", "from": head, "to": head, "line": line},
            {"at": "step3", "shot": "make", "move": "move", "from": head, "to": stuck, "line": line},
            {"at": "ask", "shot": "make", "from": stuck, "to": stuck, "line": "止まったら、そのまま声か字で聞ける"}])
    if name == "core_keep":
        rects = shots["keep"][1]
        up = _cam_on(rects["up"], 1.95)  # 「工夫した所」の欄まで映す。字幕がそこを言っているので
        record = (up[0], max(up[1], rects["up"][1] + rects["up"][3] - up[2] * ASPECT / 2 + 10), up[2])  # 節の下の端、上げた記録の所
        return Screens(name, cues, shots, [
            {"at": None, "shot": "keep", "move": "move", "from": _cam_page(shots["keep"][2], 1.3), "to": up, "line": "できた物の写真と、"},
            {"at": "record", "shot": "keep", "move": "move2", "from": up, "to": record, "line": "工夫した所を記録に添える"}])
    if name == "core_gallery":
        made = shots["gallery"][1]["made"]
        top = _cam_on([made[0], made[1] + 10, made[2], made[3]], 1.1)  # 節の上の見出しの下線を枠に入れない
        # 持ち寄られた物の列を下へ動く。1 つの記録だけに見せず、何人もの物が集まる場だと分かるように。
        lower = (top[0], top[1] + min(GALLERY_PAN, max(0, made[3] - top[2] * ASPECT)), top[2])
        return Screens(name, cues, shots, [{"at": None, "shot": "gallery", "move": "pan", "from": top, "to": lower, "line": GALLERY_LINE}])
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
