"""場面 3: 使い手の画面（play_server、J-024）を開くと、仮説 A〜E の札と型紙を刷る口がすぐ並ぶ所を見せる。

使い方: python -m demo.scene3 --out <repo の外の場所>/scene3.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 画面が撮れない・chrome か ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 本人の決定（11-05、#242）「予想の段を無くして、すぐ作る形にする」で、予想を打ち込む絵をやめた。
  前の版の筋（予想が先）を残すと、動画が今の道具と食い違うため。
- 型紙は正解でなく AI が考えた仮説である事（本人の言葉 11-05）を、画面の札に寄って見せる。
- 画面は描き直さず、本物の play_server を手元（127.0.0.1）で立てて headless の Chrome で撮る。
  描き直した画面では「この道具がそう動く」事の証拠にならない。撮るのは書き出しの度で、画面が直されれば動画も追いつく。
- 置き場は一時の場所（OMOCHAE_DATA）にする。repo の data/ の記録が画面に混ざらないように。
- 仮説の数の札は data/hypotheses の記録から数える（書き込まない）。画面の札の数と記録が食い違えば
  書き出さない。並びは記号の順で、5 枚を同じ倍率で同時に出す（順に 1 枚ずつ出すと順位に見える、J-025）。
- 玩具の動き方は描かない。矢印・扇の絵・開く様子は足さない。画面に映るのは道具の字と
  江戸の図そのものだけで、足すのは寄り・重ね・字幕だけ。
"""
import argparse
import json
import math
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from PIL import Image, ImageDraw

from demo.flip import FPS, H, PAPER, SHU, SUMI, W, contact_sheet, ease, fade, render, text
from demo.words import step_badge

ROOT = pathlib.Path(__file__).resolve().parents[2]
SID = "NDL-1187053-R0000005-L"   # 御来迎の頁。場面 2 と同じ頁
DURATION = 13.0
DPR = 2                          # 撮る時の画素の倍率。寄った時に字がぼけないよう、2 倍で撮って縮める
SHOT_W = 1600                    # 撮る窓の幅（CSS の px）。ルックブックの頁が 1180px で真ん中に来る
SHOT_H = 3400                    # 撮る高さの下限。足りない時は測った枠から伸ばす（need_height）
# 使う枠の下に残す余白（CSS の px）。寄った絵は、枠の下に枠の高さの半分ほどを映すため。
SHOT_MARGIN = 400
SCREEN_BG = (239, 232, 216)      # 画面の地の色（#efe8d8）。撮った枠の外をこの色で埋め、継ぎ目を見せない

# 合図の表。絵の動きも字幕もここだけを読む。曲を付ける時は拍に合わせてこの時刻を直す。
CUES = {
    "page_in": (0.0, 1.2),      # 開いた画面が現れる（頭は江戸の図と歌の見開き）
    "to_premise": (1.8, 3.0),   # 前提の札の所へ寄る
    "to_list": (5.6, 6.6),      # 仮説の札の所へ下がる
    "plates_in": (7.2, 8.0),    # 画面の 5 枚を切り出し、同じ大きさで 1 列に並べる（同時に出す）
    "closing": (10.2, 11.2),    # 締めの字幕。13 秒まで止めて読ませる
}

# 頭の 2 行。時刻の区切りは CUES から作り、別に時刻を持たない（合図の表を 1 つにするため）。
TITLE_TOY = "玩具の頁（utsushi の画面）"
SUB_OPEN = "開いたら、すぐ作れる"
TITLE_PREMISE = "型紙は正解ではなく、AI が考えた仮説"
SUB_PREMISE = "うまく動かない所が出る。人の工夫が、次の版の材料になる"
TITLE_LIST = "作りたい案を選んで、刷る"
SUB_READY = "作って、確かめる"
LABEL = "仮説 {n}（{toy}）"
SUB_LIST = "並びは記号の順。順位ではない"
CLOSING = ("開いたら、すぐ作る。", "仕組みは 1 つに決めず、仮説として並べる。")
SHOT_NOTE = "画面: utsushi の使い手の画面（play_server）を手元で動かして撮った"
MOD_NOTE = "改変: 画面に寄った。仮説の {n} 枚は切り出して 1 列に並べた"
CAPTIONS = (TITLE_TOY, SUB_OPEN, TITLE_PREMISE, SUB_PREMISE, TITLE_LIST, SUB_READY, LABEL, SUB_LIST, *CLOSING, SHOT_NOTE, MOD_NOTE)

BOX = (160, 196, 1760, 936)  # 画面を映す枠（場面 1 の紙の地を周りに残す）。上に 2 行、下に札の余白


def hypothesis_data(sid=SID):
    """仮説の記録をそのまま読む。数と記号はここからだけ取る（動画に数を書き込まない）。"""
    return json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8"))


def hypothesis_count(sid=SID):
    return len(hypothesis_data(sid)["hypotheses"])


def label(sid=SID):
    d = hypothesis_data(sid)
    return LABEL.format(n=len(d["hypotheses"]), toy=d["toy"])


def credit():
    """江戸の図の札は場面 2 の出所の記録を読む（頁の頭に同じ図が映るため。文を二重に持たない）。"""
    rec = json.loads(pathlib.Path(__file__).with_name("scene2_sources.json").read_text(encoding="utf-8"))
    return rec["credit"]


def phase(t, cue):
    # flip.phase は flip.CUES を読むので、この場面の CUES で同じ事をする（flip.py は変えない）
    a, b = CUES[cue]
    return ease((t - a) / (b - a))


def window(t, a, b, edge=0.4):
    """a〜b の間だけ見える字の濃さ。端の edge 秒で出入りする。"""
    return ease((t - a) / edge) * (1 - ease((t - (b - edge)) / edge))


# ---- 撮る所（網と Chrome を使う。床では通らない） ----

def _free_port():
    # 決め打ちの番号は、手元で本物の画面を開いている時にぶつかる。空いている番号を OS に選ばせる。
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _ensure_picture(sid):
    """頁の頭の江戸の図は out/sources にある時だけ画面に出る。無ければ ingest と同じ URL から取る（out/ は git の外）。"""
    pic = ROOT / "out/sources" / f"{sid}.jpg"
    if pic.exists():
        return
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    try:
        data = urllib.request.urlopen(src["image_url"], timeout=60).read()
    except OSError as e:
        # 図が無くても画面は撮れる（リンクだけになる）。止めずに知らせる。
        print(f"注意: 図が取れず、頁の頭は図のリンクだけで撮る（{e}）", file=sys.stderr)
        return
    pic.parent.mkdir(parents=True, exist_ok=True)
    pic.write_bytes(data)


def _chrome(chrome, tmp, args):
    return subprocess.run([chrome, "--headless=new", "--hide-scrollbars", "--disable-gpu", "--no-first-run",
                           f"--user-data-dir={tmp}/chrome", *args], capture_output=True, text=True, timeout=90)


def _rects(chrome, tmp, base, html, height):
    """同じ HTML を Chrome に読ませ、前提の札・仮説の札の位置を測る（CSS の px）。

    本物の頁には手を入れず、写しの末尾に測る script を足す。base を本物の口に向けるので、
    図も字の組みも本物と同じ所に来る。
    """
    js = ('<script>addEventListener("load",()=>{const o={};for(const[k,s]of[["premise","#premise"],["plate",".plate"]])'
          'o[k]=[...document.querySelectorAll(s)].map(e=>{const b=e.getBoundingClientRect();return[b.x,b.y+scrollY,b.width,b.height]});'
          'const p=document.createElement("pre");p.id="rects";p.textContent=JSON.stringify(o);document.body.appendChild(p)})</script>')
    copy = pathlib.Path(tmp) / "copy.html"
    copy.write_text(html.replace('<meta charset="utf-8">', f'<meta charset="utf-8"><base href="{base}/">', 1)
                    .replace("</body>", js + "</body>"), encoding="utf-8")
    r = _chrome(chrome, tmp, [f"--window-size={SHOT_W},{height}", "--dump-dom", copy.as_uri()])
    start = r.stdout.find('<pre id="rects">')
    if start < 0:
        return None
    return json.loads(r.stdout[start + 16:r.stdout.index("</pre>", start)])


def _used(rects):
    """動画で使う枠: 前提の札・仮説の札。頁の下の方の別の欄は映さない。"""
    return rects["premise"][:1] + rects["plate"]


def need_height(rects, minimum):
    """撮る窓の高さ（CSS の px）。使う枠の下端に寄りの余白を足す。決めた下限より低くはしない。

    11-05 に頁を作り直して長くなり、決め打ちの高さでは札 D・E の下が欠けた（切り出しの外が黒くなる）。
    頁が直されても追いつくよう、高さは測った枠から決める。
    """
    bottom = max((r[1] + r[3] for r in _used(rects)), default=0)
    return max(minimum, math.ceil(bottom + SHOT_MARGIN))


def shot_fits(rects, height):
    """使う枠が、撮った高さの中に余白ごと収まるか。収まらなければ書き出さない（欠けた札を動画に出さない）。"""
    return need_height(rects, 0) <= height


def capture(cache, sid=SID):
    """play_server を一時の置き場で立て、開いた頁を撮る。撮れない時は None。"""
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        print("検査できない: chrome が無い", file=sys.stderr)
        return None
    _ensure_picture(sid)
    out = pathlib.Path(cache) / "scene3"
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="scene3-") as tmp:
        port = _free_port()
        base = f"http://127.0.0.1:{port}"
        url = f"{base}/toy/{sid}"
        # 一時の置き場に向けるので、repo の data/ の記録が画面に出ない。
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "OMOCHAE_DATA": f"{tmp}/data"}
        proc = subprocess.Popen([sys.executable, "-m", "web.play_server", str(port)], cwd=ROOT, env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            html = None
            for _ in range(50):
                try:
                    html = urllib.request.urlopen(url, timeout=5).read().decode("utf-8")
                    break
                except OSError:
                    time.sleep(0.2)
            if html is None:
                print("検査できない: 画面の口が開かない", file=sys.stderr)
                return None
            png = out / "page.png"
            # 先に決めた高さで測り、枠が収まらなければ伸ばして測り直す。高さで組みが変わる頁もあるので、
            # 撮るのは必ず測った時と同じ高さ。
            height = SHOT_H
            rects = None
            for _ in range(3):
                rects = _rects(chrome, tmp, base, html, height)
                if not rects or not rects["premise"] or shot_fits(rects, height):
                    break
                height = need_height(rects, height)
            png.unlink(missing_ok=True)
            _chrome(chrome, tmp, [f"--force-device-scale-factor={DPR}", f"--window-size={SHOT_W},{height}", f"--screenshot={png}", url])
            if not png.exists() or not rects or not rects["premise"]:
                print("検査できない: 画面が撮れない", file=sys.stderr)
                return None
            if not shot_fits(rects, height):
                print(f"検査できない: 使う枠が撮った画面に収まらない（高さ {height}）", file=sys.stderr)
                return None
        finally:
            proc.terminate()
            proc.wait(timeout=10)
    n = hypothesis_count(sid)
    if len(rects["plate"]) != n:
        # 記録と画面の数が違うと、動画の言う事と食い違うので書き出さない。
        print(f'検査できない: 仮説の札の数が記録と合わない（画面 {len(rects["plate"])}・記録 {n}）', file=sys.stderr)
        return None
    (out / "rects.json").write_text(json.dumps({"dpr": DPR, **rects}, ensure_ascii=False, indent=1), encoding="utf-8")
    return Image.open(png).convert("RGB"), rects


# ---- 描く所（時刻だけで決まる） ----

def _cam(center, width):
    return (center[0], center[1], width)


def _lerp_cam(c0, c1, u):
    # 幅は対数で補う。直線で補うと、寄りの終わりが急に見える（場面 2 と同じ考え）。
    return (c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u, c0[2] * (c1[2] / c0[2]) ** u)


class Scene3:
    duration = DURATION

    def __init__(self, shot, rects, sid=SID, dpr=DPR):
        self.shot, self.dpr = shot, dpr
        self.label = label(sid)
        self.mod_note = MOD_NOTE.format(n=hypothesis_count(sid))  # 枚数も記録から（書き込まない）
        self.credit = credit()
        bw, bh = BOX[2] - BOX[0], BOX[3] - BOX[1]
        self.aspect = bh / bw
        # 寄りの位置は測った枠から決める（画面が直されても追いつく）。
        pr = rects["premise"][0]
        self.cam_page = _cam((SHOT_W / 2, 500), SHOT_W * 1.12)            # 頁の頭の見開き全体
        self.cam_premise = _cam((pr[0] + pr[2] / 2, pr[1] + pr[3] / 2 + 60), pr[2] * 1.1)  # 前提の札
        plates = rects["plate"]
        x0 = min(p[0] for p in plates)
        x1 = max(p[0] + p[2] for p in plates)
        y0 = min(p[1] for p in plates)
        self.cam_list = _cam(((x0 + x1) / 2, y0 + (x1 - x0) * 1.08 * self.aspect / 2 - 60), (x1 - x0) * 1.08)
        # 仮説の札: 画面から切り出し、どれも同じ倍率で 1 列に。記号の順は画面の並び（元の記録の順）のまま。
        gap = 24
        s = min((BOX[3] - BOX[1]) / max(p[3] for p in plates), (W - 160 - gap * (len(plates) - 1)) / sum(p[2] for p in plates))
        self.plates = []
        x = (W - (sum(p[2] for p in plates) * s + gap * (len(plates) - 1))) / 2
        for p in plates:
            crop = shot.crop(tuple(round(v * dpr) for v in (p[0], p[1], p[0] + p[2], p[1] + p[3])))
            self.plates.append((round(x), BOX[1], crop.resize((round(p[2] * s), round(p[3] * s)), Image.LANCZOS)))
            x += p[2] * s + gap

    def view(self, shot, cam):
        """撮った画面の cam の所を、枠の大きさに写す。枠の外は画面の地の色で埋める。"""
        cx, cy, cw = cam
        bw, bh = BOX[2] - BOX[0], BOX[3] - BOX[1]
        k = bw / (cw * self.dpr)  # 撮った画素 → 動画の画素
        x0, y0 = (cx - cw / 2) * self.dpr, (cy - cw * self.aspect / 2) * self.dpr
        return shot.transform((bw, bh), Image.AFFINE, (1 / k, 0, x0, 0, 1 / k, y0), resample=Image.BICUBIC, fillcolor=SCREEN_BG)

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        a_in = phase(t, "page_in")
        a_plates = phase(t, "plates_in")
        a_screen = a_in * (1 - a_plates)
        if a_screen > 0:
            u = phase(t, "to_list")
            cam = _lerp_cam(_lerp_cam(self.cam_page, self.cam_premise, phase(t, "to_premise")), self.cam_list, u)
            shot = self.view(self.shot, cam)
            if a_screen < 1:
                shot = Image.blend(Image.new("RGB", shot.size, PAPER), shot, a_screen)
            img.paste(shot, BOX[:2])
            draw.rectangle((BOX[0] - 1, BOX[1] - 1, BOX[2], BOX[3]), outline=fade(SUMI, 0.35 * a_screen), width=2)
        # 仮説の札: 5 枚を同時に、同じ倍率で。1 枚ずつ出さない（出す順が順位に見えるため、J-025）。
        if a_plates > 0:
            for x, y, p in self.plates:
                if a_plates < 1:
                    p = Image.blend(Image.new("RGB", p.size, PAPER), p, a_plates)
                img.paste(p, (x, y))
                draw.rectangle((x - 1, y - 1, x + p.width, y + p.height), outline=fade(SUMI, 0.3 * a_plates), width=1)
        # 頭の 2 行: 段ごとに替える。区切りは CUES から。
        rows = (
            (0.0, CUES["to_premise"][0], TITLE_TOY, SUB_OPEN, SUMI),
            (CUES["to_premise"][0], CUES["to_list"][0], TITLE_PREMISE, SUB_PREMISE, SHU),
            (CUES["to_list"][0], CUES["plates_in"][0], TITLE_LIST, SUB_READY, SUMI),
            (CUES["plates_in"][0], CUES["closing"][0] + 0.4, self.label, SUB_LIST, SHU),
        )
        for a, b, title, sub, color in rows:
            al = window(t, a, b) * (a_in if a == 0.0 else 1)
            if al > 0:
                text(draw, (80, 62), title, 52, fade(color, al), True)
                text(draw, (80, 132), sub, 34, fade(SUMI, al))
        c = phase(t, "closing")
        if c > 0:
            veil = Image.new("RGBA", (W, H), PAPER + (round(235 * c),))
            img.paste(veil, (0, 0), veil)
            draw = ImageDraw.Draw(img)
            text(draw, (W // 2, 440), CLOSING[0], 58, fade(SUMI, c), True, "ma")
            text(draw, (W // 2, 530), CLOSING[1], 58, fade(SUMI, c), True, "ma")
        # 核の一周の 1 段目（demo.core）。声で話す口はまだ無いので、画面に出るのは仮説を見る所まで。
        if c < 1:
            step_badge(draw, 1, a_in * (1 - c))
        # 隅の札: 画面を撮った事、江戸の図の出所、手を入れた事。場面 1・2 と同じ大きさ。
        # 1 行では画面の幅を越えるので 3 行に分ける。
        for i, s in enumerate((SHOT_NOTE, self.credit, self.mod_note)):
            text(draw, (80, H - 112 + 30 * i), s, 22, fade(SUMI, 0.7))
        return img


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    a = ap.parse_args(argv)
    if not shutil.which("ffmpeg"):
        print("検査できない: ffmpeg が無い", file=sys.stderr)
        return 4
    shots = capture(a.cache)
    if shots is None:
        return 4
    scene = Scene3(*shots)
    if a.sheet:
        contact_sheet(scene, a.sheet, times=(0.8, 2.5, 4.0, 6.0, 7.0, 8.5, 10.0, 11.0, 12.8))
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
