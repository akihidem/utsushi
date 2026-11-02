"""型紙に刷る印（所蔵・改変・出典 ID・仮説）と、刷った後の検査。

なぜ PDF から読み直すか: 「描く命令を出した」ではなく「刷られた紙に載っている」ことを保証するため。
字が画像化された・隠れた・別の字に落ちた場合も、ここで落ちる。
"""
import subprocess

from .model import Failure, ToolMissing

HOLDER = "国立国会図書館デジタルコレクション"
HYPOTHESIS = "仮説: 復元ではなく、仮説に基づく翻案です"


def mark_lines(source, omit=None):
    if omit == "all":
        return []
    lines = [f"所蔵: {source['holding']}", source["modification_note"], HYPOTHESIS]
    if omit != "source_id":
        lines.insert(2, f"出典ID: {source['source_id']}")
    return lines


def check_image_count(pdf_path, expected=0):
    """PDF に貼られた画像の数を見る。原図を貼らず描き直す決まり（J-007）を、できた紙で確かめる。"""
    try:
        out = subprocess.run(["pdfimages", "-list", str(pdf_path)], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise ToolMissing(f"pdfimages で読めない: {e}")
    # 透明度の smask は別の行に出るので、image の行だけを数える。
    found = sum(1 for line in out.splitlines()[2:] if line.split()[2] == "image")
    return [] if found == expected else [Failure("F5.image_count", "PDF", f"貼られた画像の数 {found} が見込み {expected} と違う")]


def check_pdf(pdf_path, source):
    try:
        out = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise ToolMissing(f"pdftotext で読めない: {e}")
    # 印が折り返されても読めるよう、空白と改行を全部取ってから探す。
    flat = "".join(out.split())
    need = {
        "所蔵": HOLDER,
        "永続ID": source["persistent_id"],
        "改変": "改変",
        "出典ID": source["source_id"],
        "仮説": "仮説",
    }
    return [Failure("F1.marks", name, f"PDF から「{text}」を取り出せない") for name, text in need.items() if text not in flat]
