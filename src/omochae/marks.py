"""型紙に刷る印（所蔵・改変・出典 ID・仮説）と、刷った後の検査。

なぜ PDF から読み直すか: 「描く命令を出した」ではなく「刷られた紙に載っている」ことを保証するため。
字が画像化された・隠れた・別の字に落ちた場合も、ここで落ちる。
"""
import re
import subprocess

from .model import Failure, ToolMissing

HOLDER = "国立国会図書館デジタルコレクション"
# 必須 2 種の今の版（版 1）の紙に刷る文。凍結の床の指紋に入るので変えない（tests/test_floor_pin.py）。使い手が自分で立てた仮説の紙もこの文。
HYPOTHESIS = "仮説: 復元ではなく、試すための 1 つの翻案です。答えではありません"
# 本人の言葉（11-05）「型紙が正解ではなくて、とりあえずAIが考えた仮説であるということを明示する。システム側もそれを認識した上でループを回す」。
# AI の案から刷る紙の文。必須 2 種は次の版から、試作の玩具は今から（hypotheses.hypothesis_mark）。
AI_HYPOTHESIS = "仮説: この型紙は正解ではなく、とりあえず AI が考えた仮説です。復元でもありません"
# 頁に出す文。文の変更は本人の確認に回す。
PREMISE_PAGE = "この型紙は正解ではありません。とりあえず AI が考えた仮説です。うまく動かない所が出ます。工夫して乗り切った所を記録に残すと、次の版を直す材料になります。"
PREMISE_SHORT = "型紙は正解ではなく、AI が考えた仮説です。復元でもありません。"
# 輪を回す Claude に渡す前提。同じ文を全部の担当に渡す事を tests/test_loop_premise.py が見る。
LOOP_PREMISE = ("前提: 型紙は正解ではなく、とりあえず AI が考えた仮説です。不完全で、うまく動かない所が出ます。"
                "動かない事は作った人の出来ではなく、仮説への返事です。人が工夫で乗り切った所（記録の fixes・止まった所）を、次の版の一番の材料にします。")


def without_premise(text):
    """成績の語の床（成功・失敗・正解を頁に出さない）の前に、本人の言葉の否定の形だけを除く。
    本人の言葉（11-05）は「型紙が正解ではなくて」で、人を採点する語でなく採点を打ち消す文なので、言葉のまま出す。
    「正解です」「不正解」のような形は除かないので、床は残る。"""
    return re.sub(r"(?<!不)正解では(?:なく|ありません)", "", text)


def mark_lines(source, omit=None):
    if omit == "all":
        return []
    lines = [f"所蔵: {source['holding']}", source["modification_note"], source.get("hypothesis_mark", HYPOTHESIS)]
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
