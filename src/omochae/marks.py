"""型紙に刷る印（所蔵・改変・出典 ID・仮説）と、刷った後の検査。

なぜ PDF から読み直すか: 「描く命令を出した」ではなく「刷られた紙に載っている」ことを保証するため。
字が画像化された・隠れた・別の字に落ちた場合も、ここで落ちる。
"""
import re
import subprocess

from .model import Failure, ToolMissing

HOLDER = "国立国会図書館デジタルコレクション"
HYPOTHESIS = "仮説（ためしの案）: AI が考えた、ためしに作るための案の 1 つです。正しい答えではありません。作って、動くか見て、直していきます。"
# 必須 2 種の今の組（凍結の床・tests/test_floor_pin.py）に刷る文。やさしい言葉の文（#318、本人の決定 11-05）へ替えた時、
# 本人に「必須 2 種の今の版の紙は変えず、次の版から」と確かめて採ったので、今の組だけ前の文（#258 の決定の文）のまま刷る。
# 次の組（goraigo-v11・tora-v4）を足す時は、その玩具を FROZEN_SETS から外す（雛形の SHEET_SET と食い違うと test_hypothesis_label が落ちる）。
HYPOTHESIS_FROZEN = "仮説: AI が考えた、試すための 1 つの翻案です。正解ではありません。作って、動きを確かめて、直していきます"
FROZEN_SETS = {"NDL-1187053-R0000005-L": "goraigo-v10", "NDL-1187053-R0000014-R": "tora-v3"}
# 使い手が自分で立てた仮説の紙の文。人の仮説を「AI が考えた」と刷らないため（print_own）。文の残りは上と揃える。
OWN_HYPOTHESIS = "仮説（ためしの案）: 自分で考えた、ためしに作るための案の 1 つです。正しい答えではありません。作って、動くか見て、直していきます。"
# 頁の「すぐ作る」の頭に出す文（本人の言葉 11-05「型紙が正解ではなくて、とりあえずAIが考えた仮説であるということを明示する」）。文の変更は本人の確認に回す。
PREMISE_PAGE = "この型紙は、正しい答えではありません。AI が「こうかな？」と考えた、ためしの案（仮説）です。うまく動かない所も出てきます。どう工夫したかを記録に書いてください。次の型紙をよくするヒントになります。"
# 輪を回す Claude に渡す前提（本人の言葉 11-05「システム側もそれを認識した上でループを回す」）。同じ文を全部の担当に渡す事を tests/test_loop_premise.py が見る。
LOOP_PREMISE = ("前提: 型紙は正解ではなく、とりあえず AI が考えた仮説です。不完全で、うまく動かない所が出ます。"
                "動かない事は作った人の出来ではなく、仮説への返事です。人が工夫で乗り切った所（記録の fixes・止まった所）を、次の版の一番の材料にします。")


def without_premise(text):
    """成績の語の床（成功・失敗・正解を頁に出さない）の前に、本人の言葉の打ち消しの形だけを除く。
    本人の言葉（11-05）は「型紙が正解ではなくて」で、人を採点する語でなく採点を打ち消す文なので、言葉のまま出す。
    「正解です」「不正解」のような形は除かないので、床は残る。"""
    return re.sub(r"(?<!不)正解では(?:なく|ありません)", "", text)


def hypothesis_line(source):
    """紙に刷る仮説の文。刷る所（mark_lines）と刷った後の検査（check_pdf）が別の文を見ると、正しい紙を断るので 1 か所にする。"""
    return source.get("hypothesis_mark", HYPOTHESIS_FROZEN if source.get("source_id") in FROZEN_SETS else HYPOTHESIS)


def mark_lines(source, omit=None):
    if omit == "all":
        return []
    lines = [f"所蔵: {source['holding']}", source["modification_note"], hypothesis_line(source)]
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
    # 短い語だけを探すと、本文が欠けても化けても別の所に同じ語が残れば通ってしまう。刷った文をそのまま探す。
    need = {
        "所蔵": HOLDER,
        "所蔵の文": source["holding"],
        "永続ID": source["persistent_id"],
        "改変": source["modification_note"],
        "出典ID": source["source_id"],
        "仮説": hypothesis_line(source),
    }
    return [Failure("F1.marks", name, f"PDF から「{text}」を取り出せない") for name, text in need.items() if "".join(text.split()) not in flat]
