"""型紙に刷る印（所蔵・改変・出典 ID・仮説）と、刷った後の検査。

なぜ PDF から読み直すか: 「描く命令を出した」ではなく「刷られた紙に載っている」ことを保証するため。
字が画像化された・隠れた・別の字に落ちた場合も、ここで落ちる。
"""

from .model import Failure
from .tools import run_tool

HOLDER = "国立国会図書館デジタルコレクション"
# 制作者の言葉（2026-11-05）「型紙が正解ではなくて、とりあえずAIが考えた仮説であるということを明示する」による。
# 文言は制作者に出して決める（#57）。刷った後の検査（F1.marks）は、この文がそのまま PDF から読める事を見る。
HYPOTHESIS = "仮説: AI が考えた、試すための 1 つの翻案です。正解ではありません。作って、動きを確かめて、直していきます"


def mark_lines(source, omit=None):
    """型紙に刷る印の行。古い刷り物から起こした型紙は所蔵（holding）を、科学の模型（江戸の玩具でない試作）は、所蔵の代わりに
    形の比の出所の文献（reference）を刷る。科学の模型に所蔵の文を刷ると、持っていない所蔵を言う事になるため。"""
    if omit == "all":
        return []
    head = f"出典: {source['reference']}" if source.get("reference") else f"所蔵: {source['holding']}"
    lines = [head, source["modification_note"], HYPOTHESIS]
    if omit != "source_id":
        lines.insert(2, f"出典ID: {source['source_id']}")
    return lines


def check_image_count(pdf_path, expected=0):
    """PDF に貼られた画像の数を見る。原図を貼らず描き直す決まりを、できた紙で確かめる。"""
    out = run_tool(["pdfimages", "-list", str(pdf_path)], "pdfimages で読めない", text=True).stdout
    # 透明度の smask は別の行に出るので、image の行だけを数える。
    found = sum(1 for line in out.splitlines()[2:] if line.split()[2] == "image")
    return [] if found == expected else [Failure("F5.image_count", "PDF", f"貼られた画像の数 {found} が見込み {expected} と違う")]


def check_pdf(pdf_path, source):
    out = run_tool(["pdftotext", str(pdf_path), "-"], "pdftotext で読めない", text=True).stdout
    # 印が折り返されても読めるよう、空白と改行を全部取ってから探す。
    flat = "".join(out.split())
    # 短い語だけを探すと、本文が欠けても化けても別の所に同じ語が残れば通ってしまう。刷った文をそのまま探す。
    if source.get("reference"):
        # 科学の模型: 所蔵の代わりに、「出典:」に続く文献の文がそのまま読める事を見る（所蔵の名と永続 ID は持たない）。
        # 頭の「出典:」ごと探す（文献の文だけだと、頭の語が欠けても、文が別の所に残れば通った。見直しの指摘）
        need = {"出典の文献": f"出典: {source['reference']}", "改変": source["modification_note"], "出典ID": source["source_id"], "仮説": HYPOTHESIS}
    else:
        need = {
            "所蔵": HOLDER,
            "所蔵の文": source["holding"],
            "永続ID": source["persistent_id"],
            "改変": source["modification_note"],
            "出典ID": source["source_id"],
            "仮説": HYPOTHESIS,
        }
    return [Failure("F1.marks", name, f"PDF から「{text}」を取り出せない") for name, text in need.items() if "".join(text.split()) not in flat]
