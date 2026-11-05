"""核の一周: ①仮説を見ながら自分の考えを話す → ②作りながら工夫を話す → ③できた物を上げて工夫と考えを残す → ギャラリーと、良くなる輪。

使い方: python -m demo.core <場面の名前> --out <repo の外の場所>/core.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 画面が撮れない・chrome か ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 本人の言葉（11-05）「今話してるこの部分が今回のハッカソンの核になる！！」。動画の真ん中に置き、見ている人が 3 段と輪を覚えて帰る形にする。
- 今ある物だけを、動いている画面として映す。作りながら見る頁・声で聞く口・写真を上げる手帖・ギャラリー・版の輪は、
  本物の play_server を一時の置き場で立て、本物の口へ送ってから headless の Chrome で撮る（場面 3 と同じ作り）。
- まだ無い物（声の取り込み・エンジンごとの改善）は、動いているように見せない。core_map・core_voice・core_loop は図で描き、
  画面に「図」「これから」と書く。撮れるようになったら、demo.build の --clip でその場面だけを差し替える。
- 画面に映す例の記録は、字の頭に「（例）」を付け、隅の札に作り物と書く。人の報告に見せかけないため。写真は確かめ表で通った 11-04 の物だけ。
- 版の輪は本物の口（説明 → 次の版）を通して、一時の置き場に版 2 を作って撮る。描き直した絵では「動いている」事の証拠にならないため。
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
from demo.scene3 import SCREEN_BG, _chrome, _ensure_picture, _free_port
from demo.words import step_badge

SID = "NDL-1187053-R0000005-L"   # 御来迎の頁。場面 2・3 と同じ
HID = "H-A"
PHOTO = ROOT / "docs/process/trials/photos/20261104/p01.jpg"   # 確かめ表で通った写真（demo.scene5 の PHOTOS）
DPR = 2
BOX = (160, 196, 1760, 936)      # 画面を映す枠（場面 3 と同じ）
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
    "make": (f"/toy/{SID}/tsukuru?h={HID}&n=3&ev=stuck", 1280, {"stage": ".stage", "henji": "#henji"}),
    "keep": (f"/toy/{SID}/techo", 1000, {"up": '[aria-label="上げる"]'}),
    "gallery": ("/gallery", 1400, {"made": "#ageta"}),
    "toy": (f"/toy/{SID}", 1400, {"kaizen": "#kaizen", "minna": "#minna"}),
}

# 3 段の図の字。段の文は words.STEPS。「今ある」と「これから」を分けて書き、無い物を有るように見せない。
HAVE = ("今ある: 開いたらすぐ作る頁", "今ある: 作りながら見る頁・声で聞く口", "今ある: 写真を上げる手帖")
VOICE_LINE = "話した声とカメラの様子を取り込む所は、これから作ります"
LOOP_NODES = ("型紙（AI の仮説）", "作る（人の工夫）", "残す（写真と言葉）", "次の版（人が採る）")
LOOP_OUTER = "エンジンごと良くなる（これから作る）"
AI_NOTE = "AI が読む所は道を作った段で、本物の API ではまだ回していません"
VOICE_BOXES = ("話す・映す", "字と札にする", "工夫と考えの記録へ")

SECONDS = {"core_map": 8.0, "core_make": 11.0, "core_keep": 7.0, "core_voice": 5.0, "core_gallery": 9.0, "core_loop": 9.0}
CUES_ALL = {
    "core_map": {"title": (0.0, 0.6), "s1": (0.6, 1.2), "s2": (1.6, 2.2), "s3": (2.6, 3.2), "after": (3.8, 4.4), "loop": (4.8, 5.6)},
    "core_make": {"in": (0.0, 0.8), "move": (4.2, 5.6)},
    "core_keep": {"in": (0.0, 0.8), "move": (1.6, 3.0)},
    "core_voice": {"in": (0.0, 0.6), "b1": (0.6, 1.1), "b2": (1.3, 1.8), "b3": (2.0, 2.5)},
    "core_gallery": {"in": (0.0, 0.8), "second": (4.4, 5.2)},
    "core_loop": {"title": (0.0, 0.6), "ring": (0.6, 2.2), "outer": (3.0, 4.4)},
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
    return shot.transform((bw, bh), Image.AFFINE, (1 / k, 0, x0, 0, 1 / k, y0), resample=Image.BICUBIC, fillcolor=SCREEN_BG)


def _lerp(c0, c1, u):
    return (c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u, c0[2] * (c1[2] / c0[2]) ** u)


def _cam_on(rect, margin=1.08, top=True, aspect=(BOX[3] - BOX[1]) / (BOX[2] - BOX[0])):
    """測った所へ寄るカメラ。top は所の頭を枠の上に合わせる（長い節の頭から読ませるため）。"""
    x, y, w, h = rect
    cw = max(w * margin, 700)
    return (x + w / 2, (y - 20 + cw * aspect / 2) if top else y + h / 2, cw)


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
        blend = a_in
        if s["at"]:
            blend = self._p(t, s["at"])
        if blend < 1:
            view = Image.blend(Image.new("RGB", view.size, PAPER), view, blend)
        img.paste(view, BOX[:2])
        draw.rectangle((BOX[0] - 1, BOX[1] - 1, BOX[2], BOX[3]), outline=fade(SUMI, 0.35 * blend), width=2)
        text(draw, (80, 62), s["title"], 52, fade(SUMI, blend), True)
        text(draw, (80, 132), s["sub"], 34, fade(SUMI, blend))
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


class MapCard:
    """3 段と輪の図。動画の真ん中の地図。動いている画面ではないので「図」と書く。"""

    def __init__(self, cues):
        self.cues = cues
        self.duration = SECONDS["core_map"]

    def _p(self, t, cue):
        a, b = self.cues[cue]
        return ease((t - a) / (b - a))

    def frame(self, t):
        from demo.words import STEPS

        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        a = self._p(t, "title")
        text(d, (80, 62), "ここが真ん中: 3 段と輪", 56, fade(SUMI, a), True)
        text(d, (W - 80, 76), "図", 30, fade(SUMI, 0.7 * a), False, "ra")
        bw, gap, x0, y0, bh = 520, 60, 110, 190, 300
        for i, (mark, words) in enumerate(STEPS):
            v = self._p(t, f"s{i + 1}")
            if v <= 0:
                continue
            x = x0 + i * (bw + gap)
            _box(d, (x, y0, x + bw, y0 + bh), fade(SUMI, 0.7 * v))
            text(d, (x + 30, y0 + 22), mark, 64, fade(SHU, v), True)
            head, _, tail = words.partition("、")
            text(d, (x + 30, y0 + 112), head + "、", 42, fade(SUMI, v), True)
            text(d, (x + 30, y0 + 168), tail, 42, fade(SUMI, v), True)
            text(d, (x + 30, y0 + bh - 52), HAVE[i], 26, fade(SUMI, 0.8 * v))
            if i < 2:
                _arrow(d, (x + bw + 8, y0 + bh // 2), (x + bw + gap - 8, y0 + bh // 2), fade(SUMI, 0.7 * v))
        v = self._p(t, "after")
        if v > 0:
            text(d, (W // 2, y0 + bh + 18), VOICE_LINE, 30, fade(SHU, v), False, "ma")
            ya = y0 + bh + 90
            _arrow(d, (x0 + 2 * (bw + gap) + bw // 2, y0 + bh + 6), (x0 + 2 * (bw + gap) + bw // 2, ya), fade(SUMI, 0.7 * v))
            _box(d, (1100, ya, 1810, ya + 90), fade(SUMI, 0.7 * v))
            text(d, (1455, ya + 22), "ギャラリーで見られる（今ある）", 38, fade(SUMI, v), True, "ma")
        u = self._p(t, "loop")
        if u > 0:
            ya = y0 + bh + 90
            _box(d, (110, ya + 130, 860, ya + 220), fade(SUMI, 0.7 * u))
            text(d, (485, ya + 152), "型紙が次の版へ（今ある）", 38, fade(SUMI, u), True, "ma")
            _box(d, (1000, ya + 130, 1810, ya + 220), fade(SHU, u), dashed=True)
            text(d, (1405, ya + 152), LOOP_OUTER, 38, fade(SHU, u), True, "ma")
            _arrow(d, (1455, ya + 96), (1455, ya + 126), fade(SUMI, 0.7 * u))
            _arrow(d, (995, ya + 175), (866, ya + 175), fade(SUMI, 0.7 * u))
            _arrow(d, (150, ya + 126), (150, y0 + bh + 8), fade(SUMI, 0.7 * u))
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
    """良くなる輪の図。内の実線は今ある版の輪、外の点線はこれから作るエンジンごとの輪。撮れたら --clip core_loop=… で差し替える。"""

    def __init__(self, cues):
        self.cues = cues
        self.duration = SECONDS["core_loop"]

    def frame(self, t):
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        p = lambda c: ease((t - self.cues[c][0]) / (self.cues[c][1] - self.cues[c][0]))
        a = p("title")
        text(d, (80, 62), "こう回す", 56, fade(SUMI, a), True)
        text(d, (80, 136), f"実線は今ある輪。点線は{SOON}輪", 34, fade(SUMI, a))
        text(d, (W - 80, 76), "図", 30, fade(SUMI, 0.7 * a), False, "ra")
        cx, cy, rx, ry = W // 2, 590, 520, 230
        pos = [(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)]
        v = p("ring")
        if v > 0:
            for i, (x, y) in enumerate(pos):
                x2, y2 = pos[(i + 1) % 4]
                k = 0.26
                _arrow(d, (x + (x2 - x) * k, y + (y2 - y) * k), (x + (x2 - x) * (1 - k), y + (y2 - y) * (1 - k)), fade(SUMI, 0.75 * v))
            for (x, y), label in zip(pos, LOOP_NODES):
                text(d, (x, y - 26), label, 44, fade(SUMI, v), True, "ma")
        u = p("outer")
        if u > 0:
            _box(d, (cx - rx - 330, cy - ry - 80, cx + rx + 330, cy + ry + 90), fade(SHU, u), dashed=True)
            text(d, (cx, cy - 26), LOOP_OUTER, 40, fade(SHU, u), True, "ma")
            text(d, (cx, cy + ry + 112), AI_NOTE, 28, fade(SUMI, 0.85 * u), False, "ma")
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
        whole = (shots["make"][2] / 2, 560, shots["make"][2] * 1.04)
        return Screens(name, cues, shots, 2, "工夫を声で残す口はこれから。今あるのは手順を見る頁と、声で聞く口", [
            {"at": None, "shot": "make", "move": "move", "from": whole, "to": _cam_on(rects["henji"], 1.5),
             "title": "作りながら見る頁", "sub": "手順を見ながら作る。止まったら、そのまま声か字で聞ける"}])
    if name == "core_keep":
        rects = shots["keep"][1]
        return Screens(name, cues, shots, 3, "カメラと声で残す口はこれから。今あるのは写真と工夫の欄", [
            {"at": None, "shot": "keep", "move": "move", "from": (shots["keep"][2] / 2, 500, shots["keep"][2] * 1.3), "to": _cam_on(rects["up"], 1.5),
             "title": "写真を上げる手帖", "sub": "できた物の写真と、工夫した所を記録に添える"}])
    if name == "core_gallery":
        made, kai = shots["gallery"][1]["made"], shots["toy"][1]["kaizen"]
        return Screens(name, cues, shots, 0, EXAMPLE_NOTE, [
            {"at": None, "shot": "gallery", "from": _cam_on(made, 1.1), "to": _cam_on(made, 1.1), "title": "他の人が作った物", "sub": "作った物と工夫を、ギャラリーで見られる"},
            {"at": "second", "shot": "toy", "from": _cam_on(kai, 1.1), "to": _cam_on(kai, 1.1), "title": "型紙の改善の輪", "sub": "報告と人の説明から、次の版へ（人が採る）"}])
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
