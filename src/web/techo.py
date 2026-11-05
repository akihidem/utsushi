"""「工作の手帖」アーティファクト（iPhone で手順を聞き、できた物を上げる口）の頁を書き出す。

本人の決定（2026-11-04、U-35「推しどおり 6 点で作る」）。設計は docs/process/research/23-phone-artifact.md。
判断の芯:
- 中身（組み方・用意する物・凡例・よくある言葉の説明）は repo のコードから書き出す。型紙と手帖が食い違わないため
- 仮説の名前と動き方は頁に入れない。紙は「仮説 A の紙」と字と組の版だけで指す（作りながら見る頁なので短くする）
- 手順の質問は src/api/ask.py と同じ線: 仕組みの質問は答えない、よくある言葉は刷った説明から、ほかは見ている人の Claude に組み方と凡例だけを渡す
- 上げた写真は上げた人と本人だけが見る。持ち寄りの場へは本人が選び、持ち寄りの床を通してから移す（J-021・F10）
- 頁は claude.ai のアーティファクトとして非公開で置く。人への共有は本人がする（外に出る操作）
出す先: out/techo/index.html（git の外。頁の中身は毎回ここから作り直す）。
"""
import base64
import io
import json
import pathlib
import sys

from omochae import hypotheses
from omochae.compose import TEMPLATES

from api import ask

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCES = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")
# 試行で配った紙（御来迎は A・C・D、虎は全部）。手帖は刷った紙について聞く所なので、紙のある仮説だけを並べる。
SHEETS = {"NDL-1187053-R0000005-L": ("H-A", "H-C", "H-D"), "NDL-1187053-R0000014-R": None}


def _thumb(sid):
    """原図の小さな写し（PDM。所蔵の印を添える）。無ければ空にして、頁は字だけで動く。"""
    p = ROOT / "out/sources" / f"{sid}.jpg"
    if not p.exists():
        return ""
    from PIL import Image

    im = Image.open(p).convert("RGB")
    im.thumbnail((360, 600))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=72)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def data():
    toys = []
    for sid in SOURCES:
        d = hypotheses.load(sid)
        src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
        tpl = TEMPLATES[d.get("template", "slider_fan")]
        keep = SHEETS.get(sid) or tuple(h["id"] for h in d["hypotheses"])
        sheets = []
        for h in d["hypotheses"]:
            if h["id"] not in keep:
                continue
            p = {**tpl.DEFAULTS, **h.get("params", {})}
            sheets.append({"id": h["id"], "label": f"仮説 {hypotheses.letter(h)} の紙", "steps": tpl.steps(p), "materials": tpl.materials(p)})
        toys.append({"sid": sid, "toy": d["toy"], "set": tpl.SHEET_SET, "results": list(tpl.RESULTS), "holding": src.get("holding", ""),
                     "thumb": _thumb(sid), "sheets": sheets})
    return {"toys": toys, "glossary": ask.GLOSSARY, "mechanism": list(ask.MECHANISM_WORDS), "refuse": ask.REFUSE, "system": ask.SYSTEM}


def main(argv=None):
    out = ROOT / "out/techo/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    tpl = (ROOT / "src/web/techo_page.html").read_text(encoding="utf-8")
    out.write_text(tpl.replace("/*TECHO_DATA*/null", json.dumps(data(), ensure_ascii=False)), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
