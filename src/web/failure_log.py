"""作る側が読む失敗の記録。デモや本番で何かが落ちた時に、後から原因を引けるようにする（stderr に出す）。

学ぶ人の書いた文と合言葉を残さない事を先に守る。要求の記録を切ってあるのと同じ理由（play_server の log_message）。
- 道は ? より前だけ。合言葉は最初の 1 回 ?k= で来る
- 例外の文は既定で出さない。int(form["x"]) の ValueError のように、送られた値がそのまま入り得る。型で中身が分かる物だけを出す（safe_text）
- トレースバックは、ファイル・行・関数・コードの行だけ。値は入らない
"""
import json
import re
import sys
import time
import traceback

KEY_LIKE = re.compile(r"sk-[A-Za-z0-9_-]{8,}")
# 文に入るのが引数や属性の名前だけの例外。最初の本番で落ちそうな所（モデルの引数の間違いなど）なので、出さないと見分けられない
NAMES_ONLY = (TypeError, AttributeError, ImportError)
LONG_NAME = 200  # これより長いファイルの名前は出さない。送られた値が名前に入った時（File name too long）に、その値を残さないため


def safe_text(e, private=()):
    """例外の文のうち、記録に残してよい物。学ぶ人の書いた文が入らないと型で分かる物だけを返す。ほかは空。"""
    name = type(e).__name__
    if isinstance(e, json.JSONDecodeError):
        text = f"{e.msg}（{e.lineno} 行 {e.colno} 列）"  # e.doc は読もうとした文そのものなので使わない
    elif isinstance(e, OSError):
        where = e.filename if isinstance(e.filename, str) and len(e.filename) <= LONG_NAME else ""
        text = " ".join(x for x in (e.strerror, where) if x)
    elif name == "AgentStopped":
        text = str(e).split(":")[0]  # 前の方は決まった文。後ろには案の中身が入り得る
    elif isinstance(e, NAMES_ONLY) or name == "BudgetStop" or type(e).__module__.startswith("anthropic"):
        text = str(e)
    else:
        return ""
    for value in private:
        if value:
            text = text.replace(value, "[伏せた]")
    return KEY_LIKE.sub("[鍵]", text)


def _frames(e):
    """トレースバックの行だけ。原因の例外が連なっていれば、その分も。文は入れない。"""
    out, seen = [], set()
    while e is not None and id(e) not in seen:
        seen.add(id(e))
        out.append(f"{type(e).__name__}:\n" + "".join(traceback.format_tb(e.__traceback__)))
        e = e.__cause__ or (None if e.__suppress_context__ else e.__context__)
    return "".join(out)


def _write(method, path, what, e, private=()):
    text = safe_text(e, private)
    head = f"[{time.strftime('%Y-%m-%d %H:%M:%S %z')}] {method} {path.partition('?')[0]} {what}: {type(e).__name__}" + (f": {text}" if text else "")
    # 1 回の print にまとめる。サーバは要求ごとに別のスレッドで動くので、分けると別の要求の行と混ざる
    print(head + ("" if type(e).__name__ == "BudgetStop" else "\n" + _frames(e).rstrip()), file=sys.stderr)


def request_failed(method, path, e):
    """画面の全体の受け皿から呼ぶ。"""
    _write(method, path, "の失敗", e)


def claude_failed(role, method, path, e, private=()):
    """Claude を呼ぶ所から呼ぶ。role は ask・interpret・observe。private は、API の文に混じっても残さない値（質問の文など）。"""
    _write(method, path, f"Claude の呼び出しの失敗（役 {role}）", e, private)
