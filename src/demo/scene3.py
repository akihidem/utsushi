"""場面 3: 使い手の画面（play_server、J-024）を開いて、型紙は正解でなく AI の仮説である事の札へ寄る。

使い方: python -m demo.scene3 --out <repo の外の場所>/scene3.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 画面が撮れない・chrome か ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 本人の決定（11-05、#242）「予想の段を無くして、すぐ作る形にする」で、予想を打ち込む絵をやめた。
  前の版の筋（予想が先）を残すと、動画が今の道具と食い違うため。
- 型紙は正解でなく AI が考えた仮説である事（本人の言葉 11-05）を、画面の札に寄って見せる。
- 本人の決定（11-05 17:26）「型紙は説を羅列せず、おもちゃ一個につき一個にする。理由はその型紙が完璧ではないから。その型紙をたたき台に色々試行錯誤する」。
  頁の札はたたき台の 1 枚になった（J-032）。札を 5 枚並べる段と、その字幕は外した。
- 字幕「型紙は正解ではなく、Claude が考えた仮説」は 1 枚の形でも正しい（審査員が見る所は Claude とはっきり書く。本人の決定 11-06）。J-032 で紙に刷る仮説の印の文は今のままで、「たたき台」に替えないと本人が決めた。
- 本人の方針（11-05 20:10）「認知負荷を減らす」「癒し系」で、字は 1 度に 1 かたまり。隅の札は外し、画面を撮った事と出所はクレジットへ寄せた（demo.scene7）。
- 画面は描き直さず、本物の play_server を手元（127.0.0.1）で立てて headless の Chrome で撮る。
  描き直した画面では「この道具がそう動く」事の証拠にならない。撮るのは書き出しの度で、画面が直されれば動画も追いつく。
- 置き場は一時の場所（OMOCHAE_DATA）にする。repo の data/ の記録が画面に混ざらないように。
- 画面の札が 1 枚でなければ書き出さない（plates_ok。頁が思わぬ形に変わった事に気づくため）。
- 玩具の動き方は描かない。矢印・扇の絵・開く様子は足さない。画面に映るのは道具の字と
  江戸の図そのものだけで、足すのは寄りと字幕だけ。
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

from demo.flip import H, PAPER, SUMI, W, contact_sheet, ease, fade, render, text
from demo.words import draw_chunk

ROOT = pathlib.Path(__file__).resolve().parents[2]
SID = "NDL-1187053-R0000005-L"   # 御来迎の頁。場面 2 と同じ頁
DURATION = 11.0
DPR = 2                          # 撮る時の画素の倍率。寄った時に字がぼけないよう、2 倍で撮って縮める
SHOT_W = 1600                    # 撮る窓の幅（CSS の px）。ルックブックの頁が 1180px で真ん中に来る
SHOT_H = 3400                    # 撮る高さの下限。足りない時は測った枠から伸ばす（need_height）
# 使う枠の下に残す余白（CSS の px）。寄った絵は、枠の下に枠の高さの半分ほどを映すため。
SHOT_MARGIN = 400
# 寄った絵に入れる範囲（CSS の px）。上は前提の札の上の節の題まで、下は型紙の札の下の端まで。
ABOVE_PREMISE = 120
BELOW_PLATE = 4

# 合図の表。絵の動きも字幕もここだけを読む。曲を付ける時は拍に合わせてこの時刻を直す。
CUES = {
    "page_in": (0.0, 1.0),      # 開いた画面が現れる（頭は江戸の図と歌の見開き）
    "to_premise": (2.4, 3.8),   # 前提の札の所へ寄る
    "premise": (2.8, 3.4),      # 前提の字が現れる
    "screen_out": (7.4, 8.2),   # 画面が紙の地へ溶ける
    "closing": (8.2, 8.7),      # 締めの字幕。画面が消えてから現れる（字を重ねない）
}

# 字は 1 かたまりずつ。前の「仕組みは 1 つに決めず、仮説として並べる。」は本人の決定（17:26）と逆なので外した。
TITLE_PREMISE = "型紙は正解ではなく、Claude が考えた仮説です。"   # ですます調（11-07 昼の本人の直しの (1)・案）
CLOSING = ("開いたら、すぐ作れます。",)
CAPTIONS = (TITLE_PREMISE, *CLOSING)

BOX = (160, 196, 1760, 936)  # 画面を映す枠（場面 1 の紙の地を周りに残す）。上に 1 行の余白


def phase(t, cue):
    # flip.phase は flip.CUES を読むので、この場面の CUES で同じ事をする（flip.py は変えない）
    a, b = CUES[cue]
    return ease((t - a) / (b - a))


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


def plates_ok(on_page):
    """型紙は玩具に 1 枚（J-032）なので、頁の札はたたき台の 1 枚だけ。data には仮説が残るので、記録の数とは比べない。"""
    return on_page == 1


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
    if not plates_ok(len(rects["plate"])):
        # 札が 1 枚でない時は、動画の言う事と頁が食い違うので書き出さない。
        print(f'検査できない: 型紙の札が 1 枚でない（画面 {len(rects["plate"])}）', file=sys.stderr)
        return None
    (out / "rects.json").write_text(json.dumps({"dpr": DPR, **rects}, ensure_ascii=False, indent=1), encoding="utf-8")
    return Image.open(png).convert("RGB"), rects


# ---- 描く所（時刻だけで決まる） ----

def page_color(shot):
    """撮った画面の地の色。枠の外をこの色で埋め、継ぎ目を見せない。
    皮の色は main で変わる（生成りから白へ替わった時、書き込んだ色のまま枠の外に帯が出た）ので、撮った絵の隅から読む。"""
    return shot.getpixel((2, shot.height - 3))


def _cam(center, width):
    return (center[0], center[1], width)


def _lerp_cam(c0, c1, u):
    # 幅は対数で補う。直線で補うと、寄りの終わりが急に見える（場面 2 と同じ考え）。
    return (c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u, c0[2] * (c1[2] / c0[2]) ** u)


class Scene3:
    duration = DURATION

    def __init__(self, shot, rects, sid=SID, dpr=DPR):
        self.shot, self.dpr = shot, dpr
        bw, bh = BOX[2] - BOX[0], BOX[3] - BOX[1]
        self.aspect = bh / bw
        # 寄りの位置は測った枠から決める（画面が直されても追いつく）。
        pr, pl = rects["premise"][0], rects["plate"][0]
        self.cam_page = _cam((SHOT_W / 2, 500), SHOT_W * 1.12)            # 頁の頭の見開き全体
        # 前提の札と、その下の札 1 枚を切らずに映す。札は 1 枚なので、途中で切ると何の札か分からない。
        top, bottom = pr[1] - ABOVE_PREMISE, pl[1] + pl[3] + BELOW_PLATE
        width = max(pr[2] * 1.1, (bottom - top) / self.aspect)
        self.cam_premise = _cam((pr[0] + pr[2] / 2, top + width * self.aspect / 2), width)

    def view(self, shot, cam):
        """撮った画面の cam の所を、枠の大きさに写す。枠の外は画面の地の色で埋める。"""
        cx, cy, cw = cam
        bw, bh = BOX[2] - BOX[0], BOX[3] - BOX[1]
        k = bw / (cw * self.dpr)  # 撮った画素 → 動画の画素
        x0, y0 = (cx - cw / 2) * self.dpr, (cy - cw * self.aspect / 2) * self.dpr
        return shot.transform((bw, bh), Image.AFFINE, (1 / k, 0, x0, 0, 1 / k, y0), resample=Image.BICUBIC, fillcolor=page_color(shot))

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        out, c = phase(t, "screen_out"), phase(t, "closing")
        a_screen = phase(t, "page_in") * (1 - out)
        if a_screen > 0:
            shot = self.view(self.shot, _lerp_cam(self.cam_page, self.cam_premise, phase(t, "to_premise")))
            if a_screen < 1:
                shot = Image.blend(Image.new("RGB", shot.size, PAPER), shot, a_screen)
            img.paste(shot, BOX[:2])
            draw.rectangle((BOX[0] - 1, BOX[1] - 1, BOX[2], BOX[3]), outline=fade(SUMI, 0.3 * a_screen), width=2)
        # 字は 1 かたまりだけ。頁の頭は絵で分かるので字を置かない。
        a_line = phase(t, "premise") * (1 - out)
        # 字は下の真ん中の字幕の帯（ファイナリストから借りた点 1・2。前は枠の上の余白と、真ん中に大きく）
        from demo.words import band

        if a_line > 0:
            img = band(img, (TITLE_PREMISE,), a_line)
        if c > 0:
            img = band(img, CLOSING, c)
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
        contact_sheet(scene, a.sheet, times=(0.5, 1.5, 2.6, 3.2, 4.0, 6.0, 7.6, 8.6, 10.8))
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
