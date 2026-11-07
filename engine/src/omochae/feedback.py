"""作った人の報告（組み上がりの感想と、動いた様子）を確かめ、雛形・形ごとに集めて、直しの案の行き先を出す（Issue #21）。

制作者の方針（2026-11-05）: 型紙は、組み上がった物の完成度と、動きの完成度を高めるように洗練させる。その材料は、作った人の報告。
エンジンの受け持ちは、報告の形・その検査・集計と、手元の入口と人の確認（omochae.intake。制作者の決定で入口もエンジンの側・#22）。
公開はサイト（提出物の側）が受け持つ。
判断の芯:
- 今の検査は式と配置だけを見て、実物で確かめた値が 1 つも無い。報告は、その見込みを確かめる唯一の材料になる。
- 直しは人が採る。この道具は型紙も寸法も書き換えず、困り事が「どの寸法・床・組み方の文」に当たるかの行き先だけを出す。
  案に新しい寸法の値を持たせないのは、少ない報告から値を決め打つと、仮説の違いと作り方の違いが混ざるため。
- 報告に名前や連絡先を入れない。提出物の持ち寄りの検査（F10.pii）と同じ見方で、全角や見えない文字をそろえてから落とす。
  落とした報告の中身は、集計にも知らせにも出し直さない。
- 名前や住所は式では見分けられない。だから、まとめ（summarize の入口）は人が受け入れた報告（reviewed_at がある）だけを数える。
- メモは信用しない文として扱う。まとめには 1 行にして出し、Markdown では記号を無効にする（見出しや HTML のタグを差し込めた）。
終了: 0 = 通る / 3 = 落ちる / 4 = 確かめられない（置き場が無い等）。
"""
import datetime
import html
import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter

from .__main__ import Parser
from .compose import TEMPLATES

ROOT = pathlib.Path(__file__).resolve().parents[2]
from .model import Failure

MOVED = ("moved", "partly", "not")  # 動いた・少し動いた・動かない
FINISH = range(1, 6)  # 仕上がりの点（1 悪い〜5 良い）。作った人の見た目の感じで、数えて比べるためだけの物
# 困り事の種類と、その直しの行き先。床の名は族ごと（下の FLOORS）に差し込む。
KINDS = {
    "cut": "切る線・組み方の文（切る順・大人がする所）",
    "fold": "折り線・凡例（谷と山の向き）",
    "glue": "糊代の大きさと位置",
    "fit": "寸法の隙間と、それを見る床（{floor}）",
    "motion": "動きの式と床（{floor}）・既定の寸法",
    "mark": "位置の印（貼る所・差す深さ）",
    "material": "部品表・用意する物",
    "finish": "描き直しの絵・部品の形（仕上がり・見た目）",
    "other": "人が読んで決める",
    # 型紙の外の行き先（#23 制作者の決定「子どもの工作の様子を蓄積して、サービス全体の改善をする」）
    "guide": "案内（組み方の説明・組み立ての頁・画面の文）",  # 手順の紙は廃止（制作者の決まり 2026-11-06「文章のプリントは廃止。組み立て用のページだけでいい。」）
    "answer": "聞く口の答え（質問への返事）",
    "site": "サイトの流れ（選ぶ・刷る・送るまでの道筋）",
}
SERVICE_KINDS = ("guide", "answer", "site")
MAX_STEP = 40  # 手順の番号の上限。どの雛形の組み方も 40 手順より短い。上限が無いと、数の欄で電話番号を運べた
MAX_MINUTES = 600  # かかった時間の上限（分）。一続きの工作で考えにくい長さは書き間違いと見る
# 文の長さの上限（字）。画面の欄の maxlength と同じ（感想 MAX_TEXT・困り事 MAX_NOTE）。上限が無いと、連絡先の式が長い文で
# 2 乗の時間をかけ（1 万字で約 2 秒）、大きな報告 1 つで summarize が止まった。長い文は式を当てる前に落とす
MAX_TEXT = 600
MAX_NOTE = 300
# 報告 1 つの葉（文・数・真偽）の数と、文の合計の長さの上限。1 つずつ短くても、幅の広い list に大量に並べると同じく止まった。
# 画面から来る報告は、感想 2 つ（600 字）・困り事 3 つ（300 字）と短い名だけなので、この中に十分収まる
MAX_STRINGS = 100
MAX_TOTAL = 4000
# 雛形ごとの動きの床。雛形を足したら、ここにも足す（test_feedback の 5 で漏れを見る）。
FLOORS = {
    "slider_fan": "F5.fan_clearance・F5.slide_clearance ほか", "pivot_counterweight": "F5.pivot",
    "spinner": "F5.spin", "whistle": "F5.sound", "popup_jar": "F5.popup・F5.jar_seat", "slide_box": "F5.slide",
    "wheel_cart": "F5.wheel", "balance": "F5.balance", "twist_drum": "F5.drum", "float": "F5.float",
    "pull_nod": "F5.pull_nod", "lever_link": "F5.link", "launcher": "F5.launch", "stand_figure": "F5.stand",
    # 江戸の玩具でない模型の試作（振り子の波・DNA の二重らせん）。寸法の決まりと組み合わせは範囲の床で落とすので、直しの行き先も範囲の床
    "pendulum_wave": "F5.range（振り子の波の寸法の決まり）",
    "helix": "F5.range",
}
ALLOWED = {"template", "form", "params", "source_id", "built", "moved", "finish", "motion_notes", "finish_notes",
           "problems", "reported_at", "reviewed_at",
           "stuck_step", "gave_up", "minutes"}  # 作る様子（#23）: 止まった手順・やめたか・かかった時間（分）  # reviewed_at は入口（omochae.intake）で人が受け入れた時刻
PROBLEM_KEYS = {"kind", "step", "note"}
# 出典の ID と時刻は決まった形だけを通す。自由な文を入れられる欄を、感想の 2 つと困り事の note に絞るため。
# 個人の情報の形の見方。式だけで全部の書き方は止められないので、これは補助で、受け入れの前に人が全文を読む（omochae.intake）。
# 見方は has_pii の docstring（数字の多い所と、連絡先の語と印）。omochae.engine_loop も同じ has_pii を使う（見方を 1 つに保つ）。
REPORTED_AT = re.compile(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:\d{2}|Z)?)?")
REPORTED_AT_MAX_DEPTH = 8  # 報告の入れ子の深さの上限。深い入れ子で再帰が止まらないように
KANJI_DIGITS = str.maketrans("〇一二三四五六七八九零壱弐参", "01234567890123")  # 大字（零壱弐参）も
# 式は、同じ所を読み直さない形にする（#31）。\s* を続けたり（\s*(…)?\s*）、語の並びを点より先に読んだり（[a-z0-9-]+\.）すると、
# 上限の中の文でも 2 乗や 3 乗の時間をかけた（「LINE + 空白 596 字」で 1 欄 1 秒を越えた）。下の形は、前の形と同じ文に当たる
CONTACT = re.compile(r"(?i)@|アット|メアド|メール|電話|携帯|https?://|www\.|(?<=[a-z0-9-])\.(com|net|org|jp|io|me|co|app|dev)\b"
                     # at と dot は、dot の後にドメインの終わりが続く時だけ（「look at the red dot」の様な普通の文で落とした）
                     r"|\bat\b(?:(?!\bat\b).)*?\bdot\b\s*(com|net|org|jp|io|me|co|app|dev)\b|(?<![a-z])(tel|e-?mail|mail)(?![a-z])"
                     # ID は「部品IDが」「出典IDを」の工作の語と重なるので、は・:・=・is か空白の後に英数字が続く時だけ連絡先と見る
                     # （空白を消した文では「ID は taro」が「IDはtaro」になり、空白を残した文（_norm）では「ID taro」で当たる。
                     #  区切り無しの「ideas」を当てないため、区切りは必ず要る）
                     r"|(?<![a-z])id(?:\s*(?:は|is|[:：=])\s*|\s+)[a-z0-9_.]{3,}|twitter|ツイッター|インスタ|instagram|tiktok|youtube"
                     r"|facebook|フェイスブック|discord|ディスコード|スレッズ|gmail|yahoo"
                     # LINE は工作の語（折りライン・fold line）と重なるので、ID が続く時だけ連絡先と見る
                     # （「折りライン2.5mm」「fold line bent」で落としていたので、ライン は英字で始まる名が続く時、英語の line は ID か : が続く時だけ）
                     r"|(?<![a-z])line\s*(?:id\s*)?[:：]|(?<![a-z])line\s*id\s*[a-z0-9_.]{3,}|ライン\s*(?:(?:の\s*)?id\s*)?(?:(?:は|[:：=])\s*)?[a-z_][a-z0-9_.]{3,}")
# 大文字の LINE の後に名が続く形（LINE yamada）。大文字と小文字を分けて見るのは、工作の英語（line them up）と分けるため。
# 空白を残した文だけで見る。空白を消した文で見ると、後ろの語までつながって名に見え、「LINE is bent」「LINE A1 is a part mark」で落とした。
# そのため、語の中に空白や見えない文字を挟む「L I N E yamada」は式では止めない（受け入れの前に人が全文を読む。README の限り）
LINE_CAPS = re.compile(r"(?<![A-Za-z])LINE\s*(?:(?:の\s*)?ID\s*)?(?:(?:は|[:：=])\s*)?[A-Za-z_][A-Za-z0-9_.]{3,}")
# 大文字小文字に関わらず、数字か _ を含む 4 字以上の名が続く形（Line taro_123・LiNe taro_123・Line _taro）。
# 数字や _ の入った名は工作の英語に出ない。4 字より短い物（Line A1 の様な部品の印）は当てない。
# これは空白を残した文だけで見る。空白を消すと、前の語とつながって見逃し（use Line _taro）、離れた _ と語がつながって当たった（line _ red mark）
LINE_NAMED = re.compile(r"(?i:(?<![a-z])line\s*(?:(?:の\s*)?id\s*)?(?:(?:は|[:：=])\s*)?(?=[a-z_][a-z0-9_.]{3,})(?=[a-z0-9.]*[0-9_])[a-z0-9_.]+)")


def _norm(text):
    """全角を半角に、漢数字を数字に、どのダッシュと波も - にそろえ、見えない文字を消す。メールの崩し（空白・(at)）もそろえる。"""
    t = unicodedata.normalize("NFKC", str(text)).translate(KANJI_DIGITS)
    t = "".join("-" if unicodedata.category(ch) == "Pd" or ch in "ー−~〜" else ch for ch in t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")
    t = re.sub(r"(?:(?<!\s)\s+)?[(\[]\s*at\s*[)\]]\s*", "@", t, flags=re.I)
    t = re.sub(r"(?:(?<!\s)\s+)?@\s*", "@", t)
    # 点が 2 つ以上続く数の並び（090.1234.5678）は小数でなく区切り。小数と取り違えて番号を見逃した
    t = re.sub(r"(?<!\d)\d+(?:\.\d+){2,}", lambda m: m.group().replace(".", "-"), t)
    return re.sub(r"(?<=\w)\s*\.\s*(?=[^\W\d_])", ".", t)


def has_pii(text):
    """個人の情報の形があるか。3 回のレビューで、番号の書き方を式で追うと、区切り・空き・桁の分け方ですり抜け続けた。
    そこで書き方を追わず、次の 2 つで見る（安全の側に倒す。寸法の多い文も落ちるので、知らせで「番号は書かない」と言う）:
    - 数字の多い所: 近く（24 文字の中）に数字が 7 つ以上ある。電話（10 桁〜）も郵便番号（7 桁）も、ここに当たる。
    - 連絡先の語と印: @・アット・メール・電話・LINE・SNS の名・URL・ドメインの形。
    名前は式では見分けられないので、受け入れの前に人が全文を読む（omochae.intake の review）。"""
    # 連絡先の語は、長音の ー を - に直す前に見る（直した後では「メール」「ツイッター」が当たらなかった）
    # 見えない文字・結合文字・異体字セレクター・空白を消してから語を探す（語の中に挟むと、すり抜けた）
    raw = "".join(ch for ch in unicodedata.normalize("NFKC", str(text))
                  if unicodedata.category(ch) not in ("Cf", "Mn", "Me") and not ch.isspace())
    if CONTACT.search(raw):
        return True
    t = _norm(text)
    idx = [i for i, ch in enumerate(t) if ch.isdigit()]
    if any(idx[i + 6] - idx[i] < 24 for i in range(len(idx) - 6)):
        return True
    return CONTACT.search(t) is not None or LINE_CAPS.search(t) is not None or LINE_NAMED.search(t) is not None


def _strings(v, depth=0):
    """入れ子の中の文字列を全部出す（欄の名も）。文字列でない葉（数・真偽・null）は None を出す。
    None も出すのは、呼ぶ側が葉の数を数えて上限で止められるように（[0, 0, …] の様な幅の広い数の list で、
    文字列だけ数えると上限に掛からず、要素の数だけ知らせを作った）。深すぎる入れ子は ValueError（再帰が止まらないように）。"""
    if depth > REPORTED_AT_MAX_DEPTH:
        raise ValueError("入れ子が深すぎる")
    if isinstance(v, str):
        yield v
    elif not isinstance(v, (dict, list, tuple)):
        yield None
    elif isinstance(v, dict):
        for k, x in v.items():
            yield str(k)
            yield from _strings(x, depth + 1)
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from _strings(x, depth + 1)


def _iso_ok(at):
    """形だけでなく、日付として在るか（9999-99-99 を通さない）。"""
    try:
        datetime.datetime.fromisoformat(at)
        return True
    except ValueError:
        return False


def check(r):
    """報告 1 つを確かめる。Returns Failure の list（空なら通る）。
    知らせの文には、報告の値を入れない（落とした報告の中身を出し直さないため。欄の名も、決まりの外の物は出さない）。"""
    out = []
    if not isinstance(r, dict):
        return [Failure("F12.report", "報告", "JSON の物（辞書）でない")]
    # 個人の情報は、欄に関わらず全部の文字列で見る。決まった欄の中だけ見ると、params や source_id に書けばすり抜けた
    try:
        # source_id と時刻は、下で決まった形（在る出典・在る日付）だけを通すので、文の見方から外す。
        # 外さないと、出典の ID の 7 桁（1187053）を郵便番号と取り違えた
        # 一番上の欄も先に数える。数える前に一番上を写すと、欄の多い報告を写し終えるまで断れなかった
        if len(r) > MAX_STRINGS:
            return [Failure("F12.report", "報告", f"欄が多すぎる（{MAX_STRINGS} まで）")]
        # 全部を集めてから上限を見ると、大きな報告を全部たどり全部持ってからでないと断れなかった。1 つずつ数え、越えた所で止める
        texts, leaves, total = [], 0, 0
        for t in _strings({k: v for k, v in r.items() if k not in ("source_id", "reported_at", "reviewed_at")}):
            leaves += 1
            total += len(t) if t is not None else 0
            if leaves > MAX_STRINGS or total > MAX_TOTAL or (t is not None and len(t) > MAX_TEXT):
                return [Failure("F12.report", "報告",
                                f"文が長すぎるか多すぎる（1 つ {MAX_TEXT} 字・{MAX_STRINGS} 個・合わせて {MAX_TOTAL} 字まで）")]
            if t is not None:
                texts.append(t)
    except ValueError:
        return [Failure("F12.report", "報告", "入れ子が深すぎる")]
    # 数字は、文の欄を全部合わせても数える。欄をまたいで番号を分けたり、間を空けたりすると、1 つの文の幅では通った
    # problems の形は下で見る。ここで list でない物を回すと、数（"problems": 1）で例外になり、rc 3 で落とせなかった
    plist = r.get("problems") if isinstance(r.get("problems"), list) else []
    free = [r.get("motion_notes", ""), r.get("finish_notes", "")] + \
        [pr.get("note", "") for pr in plist if isinstance(pr, dict)]
    total_digits = sum(ch.isdigit() for x in free if isinstance(x, str) for ch in _norm(x))
    if any(has_pii(t) for t in texts) or total_digits >= 7:
        out.append(Failure("F12.pii", "報告", "数字の多い所か、連絡先の語（@・メール・電話・LINE・URL など）がある。番号や連絡先は書かない（寸法の数字も、近くに 7 つ以上あると落ちる）"))
    if set(r) - ALLOWED:
        out.append(Failure("F12.pii", "欄", f"決まりの外の欄が {len(set(r) - ALLOWED)} つある（名前や連絡先は書かない）"))
    t = r.get("template")
    tpl = TEMPLATES.get(t) if isinstance(t, str) else None
    if tpl is None:
        out.append(Failure("F12.report", "template", f"知らない雛形（{'・'.join(sorted(TEMPLATES))} のどれか）"))
    else:
        f = r.get("form")
        if not isinstance(f, str) or f not in tpl.FORMS:
            out.append(Failure("F12.report", "form", f"{tpl.ID} の形は {'・'.join(map(str, tpl.FORMS))}"))
        params = r.get("params", {})
        # 寸法は数だけ。文字の値は、雛形が文字を既定に持つ寸法（形の名など）の、英小文字の短い名だけ
        def ok_param(k, v):
            if k not in tpl.DEFAULTS or isinstance(v, bool):
                return False
            if isinstance(v, (int, float)):
                # 寸法は雛形の範囲（F5.range と同じ）の中だけ。範囲の外の大きな数で番号を運べた
                lo_hi = getattr(tpl, "RANGES", {}).get(k)
                # 小数は 2 桁まで（寸法は 0.01mm より細かく測れない）。桁を許すと、範囲の中の小数の後ろで番号を運べた
                return lo_hi is not None and lo_hi[0] <= v <= lo_hi[1] and round(v, 2) == v
            return isinstance(v, str) and isinstance(tpl.DEFAULTS[k], str) and re.fullmatch(r"[a-z_]{1,20}", v) is not None
        if not isinstance(params, dict) or not all(ok_param(k, v) for k, v in params.items()):
            out.append(Failure("F12.report", "params", f"{tpl.ID} の寸法の名と、数か形の値だけ"))
    sid = r.get("source_id")
    # 出典の ID は、data/sources に在る記録だけ。形だけで見ると、末尾に好きな文字を足せた
    if sid is not None and not (isinstance(sid, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", sid)
                                and (ROOT / "data/sources" / f"{sid}.json").exists()):
        out.append(Failure("F12.report", "source_id", "data/sources に無い出典の ID"))
    for key in ("reported_at", "reviewed_at"):
        at = r.get(key)
        if at is not None and not (isinstance(at, str) and REPORTED_AT.fullmatch(at) and _iso_ok(at)):
            out.append(Failure("F12.report", key, "日付か ISO 8601 の時刻でない"))
    if not isinstance(r.get("built"), bool):
        out.append(Failure("F12.report", "built", "組み上がったかを true か false で書く"))
    m = r.get("moved")
    if not isinstance(m, str) or m not in MOVED:
        out.append(Failure("F12.report", "moved", f"動いたかは {'・'.join(MOVED)} のどれか"))
    fin = r.get("finish")
    if not (isinstance(fin, int) and not isinstance(fin, bool) and fin in FINISH):
        out.append(Failure("F12.report", "finish", "仕上がりの点は 1〜5 の整数"))
    st = r.get("stuck_step")
    if st is not None and not (isinstance(st, int) and not isinstance(st, bool) and 1 <= st <= MAX_STEP):
        out.append(Failure("F12.report", "stuck_step", f"止まった手順の番号は 1〜{MAX_STEP} の整数か null"))
    if "gave_up" in r and not isinstance(r["gave_up"], bool):
        out.append(Failure("F12.report", "gave_up", "やめたかを true か false で書く"))
    mi = r.get("minutes")
    if mi is not None and not (isinstance(mi, int) and not isinstance(mi, bool) and 1 <= mi <= MAX_MINUTES):
        out.append(Failure("F12.report", "minutes", f"かかった時間は 1〜{MAX_MINUTES} 分の整数か null"))
    for key in ("motion_notes", "finish_notes"):
        if key in r and not isinstance(r[key], str):
            out.append(Failure("F12.report", key, "文で書く"))
    probs = r.get("problems", [])
    if not isinstance(probs, list):
        out.append(Failure("F12.report", "problems", "困り事は list"))
        probs = []
    for i, pr in enumerate(probs):
        if not isinstance(pr, dict) or not isinstance(pr.get("kind"), str) or pr["kind"] not in KINDS:
            out.append(Failure("F12.report", f"problems[{i}]", f"困り事の種類は {'・'.join(KINDS)} のどれか"))
            continue
        if set(pr) - PROBLEM_KEYS:
            out.append(Failure("F12.pii", f"problems[{i}]", "困り事に決まりの外の欄がある（kind・step・note だけ）"))
        if pr.get("step") is not None and not (isinstance(pr["step"], int) and not isinstance(pr["step"], bool) and 1 <= pr["step"] <= MAX_STEP):
            out.append(Failure("F12.report", f"problems[{i}].step", f"手順の番号は 1〜{MAX_STEP} の整数か null"))
        if "note" in pr and not isinstance(pr["note"], str):
            out.append(Failure("F12.report", f"problems[{i}].note", "文で書く"))
        elif len(pr.get("note", "")) > MAX_NOTE:
            out.append(Failure("F12.report", f"problems[{i}].note", f"困り事の文は {MAX_NOTE} 字まで"))
    return out


def _one_line(text):
    """メモを 1 行にする。改行（U+2028 などの字の区切りも）は空白に、制御の文字と見えない文字は消す。"""
    return "".join(ch for ch in " ".join(str(text).split()) if unicodedata.category(ch)[0] != "C")


def _md_text(text):
    """Markdown の中で字のまま読める形にする。行の頭の記号（# や -）は 1 行にした後は行の頭に来ないので、文の中で働く物だけ無効にする。"""
    return html.escape(re.sub(r"([\\`*_\[\]|~!])", r"\\\1", text), quote=False)


def summarize(reports):
    """通った報告を雛形・形ごとに集める。Returns {(template, form): 集計}。困り事は多い順で、行き先の文を付ける。"""
    out = {}
    for r in reports:
        if not isinstance(r, dict) or check(r):
            continue  # 通らない報告は数えない（CLI は先に check で除くが、道具として直に呼ばれても落ちないように）
        key = (r["template"], r["form"])
        g = out.setdefault(key, {"n": 0, "built": 0, "moved": Counter(), "finish": [], "kinds": {}})
        g["n"] += 1
        g["built"] += r["built"]
        g["moved"][r["moved"]] += 1
        g["finish"].append(r["finish"])
        for pr in r.get("problems") or []:
            if pr["kind"] in SERVICE_KINDS:
                continue  # サービスの困り事は service_summary で見る（型紙の直しの行き先と分ける）
            k = g["kinds"].setdefault(pr["kind"], {"count": 0, "steps": Counter(), "notes": []})
            k["count"] += 1
            if pr.get("step") is not None:
                k["steps"][pr["step"]] += 1
            if pr.get("note"):
                k["notes"].append(_one_line(pr["note"]))
    for (tid, _), g in out.items():
        g["moved"] = {m: g["moved"][m] for m in MOVED}
        g["finish_mean"] = sum(g["finish"]) / len(g["finish"])
        del g["finish"]
        floor = FLOORS.get(tid, "族の床")
        g["problems"] = [{"kind": kind, "count": v["count"], "steps": dict(v["steps"].most_common()),
                          "target": KINDS[kind].format(floor=floor), "notes": v["notes"][:5]}
                         for kind, v in sorted(g.pop("kinds").items(), key=lambda kv: -kv[1]["count"])]
    return out


def service_summary(reports):
    """サービス全体の集計（#23）。作る様子（止まった手順・やめた・かかった時間）と、案内・聞く口・サイトの流れの困り事。
    雛形をまたいで見るのは、止まる所や分かりにくい案内は、どの型紙でも同じ所に出る事があるため。"""
    good = [r for r in reports if isinstance(r, dict) and not check(r)]
    stuck = Counter((r["template"], r["form"], r["stuck_step"]) for r in good if r.get("stuck_step") is not None)
    mins = sorted(r["minutes"] for r in good if r.get("minutes") is not None)
    med = None
    if mins:
        h = len(mins) // 2
        med = mins[h] if len(mins) % 2 else (mins[h - 1] + mins[h]) / 2
    kinds = {}
    for r in good:
        for pr in r.get("problems") or []:
            if pr["kind"] in SERVICE_KINDS:
                k = kinds.setdefault(pr["kind"], {"count": 0, "steps": Counter(), "notes": []})
                k["count"] += 1
                if pr.get("step") is not None:
                    k["steps"][pr["step"]] += 1
                if pr.get("note"):
                    k["notes"].append(_one_line(pr["note"]))
    return {"n": len(good), "gave_up": sum(1 for r in good if r.get("gave_up")), "stuck": dict(stuck.most_common()),
            "minutes": {"n": len(mins), "median": med, "min": mins[0] if mins else None, "max": mins[-1] if mins else None},
            "problems": [{"kind": kind, "count": v["count"], "steps": dict(v["steps"].most_common()), "target": KINDS[kind],
                          "notes": v["notes"][:5]} for kind, v in sorted(kinds.items(), key=lambda kv: -kv[1]["count"])]}


def _service_markdown(sv):
    m = sv["minutes"]
    lines = ["# サービス全体（作る様子と、案内・聞く口・サイトの流れ）", "",
             f"- 報告 {sv['n']} 件、やめた {sv['gave_up']} 件",
             f"- かかった時間（書いた {m['n']} 件）: 中央 {m['median']} 分・最短 {m['min']}・最長 {m['max']}" if m["n"] else "- かかった時間: 書いた報告なし"]
    for (tid, form, step), c in list(sv["stuck"].items())[:10]:
        lines.append(f"- 止まった所: {tid} / {form} の手順 {step} × {c}")
    for p in sv["problems"]:
        steps = "・".join(f"手順 {k}×{v}" for k, v in p["steps"].items()) or "手順の番号なし"
        lines.append(f"- {p['kind']} {p['count']} 件（{steps}）→ 行き先: {p['target']}")
        lines += [f"  - 「{_md_text(n)}」" for n in p["notes"]]
    return "\n".join(lines + [""])


def _markdown(s):
    lines = ["# 作った人の報告の集計（直しの案の行き先。直しは人が採る）", ""]
    for (tid, form), g in sorted(s.items()):
        m = g["moved"]
        lines += [f"## {tid} / {form}（報告 {g['n']} 件・組み上がり {g['built']}）",
                  f"- 動いた {m['moved']}・少し {m['partly']}・動かない {m['not']}、仕上がりの点の平均 {g['finish_mean']:.1f}"]
        for p in g["problems"]:
            steps = "・".join(f"手順 {k}×{v}" for k, v in p["steps"].items()) or "手順の番号なし"
            lines.append(f"- {p['kind']} {p['count']} 件（{steps}）→ 行き先: {p['target']}")
            lines += [f"  - 「{_md_text(n)}」" for n in p["notes"]]
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    ap = Parser(prog="omochae.feedback", description="作った人の報告を確かめ（check）、雛形・形ごとに集める（summarize）。"
                                                     "終了: 0 通る / 3 落ちる / 4 確かめられない")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="報告の JSON を 1 つ確かめる").add_argument("file")
    sm = sub.add_parser("summarize", help="置き場の *.json の報告を集め、Markdown で出す（落ちた報告と人が受け入れていない報告は数えず、名前だけ知らせる）")
    sm.add_argument("dir")
    sm.add_argument("--json", action="store_true", help="Markdown でなく JSON で出す")
    args = ap.parse_args(argv)

    def load(path):
        try:
            return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError, RecursionError) as e:
            return e

    if args.cmd == "check":
        r = load(args.file)
        if isinstance(r, Exception):
            print(f"確かめられない: {r}", file=sys.stderr)
            return 4
        fails = check(r)
        for f in fails:
            print(f.line(), file=sys.stderr)
        return 3 if fails else 0
    d = pathlib.Path(args.dir)
    if not d.is_dir():
        print(f"確かめられない: 置き場が無い {d}", file=sys.stderr)
        return 4
    good = []
    for p in sorted(d.glob("*.json")):
        r = load(p)
        fails = [Failure("F12.report", "JSON", "読めない")] if isinstance(r, Exception) else check(r)
        if fails:
            # 落ちた報告は、ファイルの名と床の名だけを知らせる（個人の情報の形を含む中身を出し直さない）
            print(f"数えない: {p.name}（{'・'.join(sorted({f.floor for f in fails}))}）", file=sys.stderr)
        elif not r.get("reviewed_at"):
            # 式は名前や住所を見分けられないので、人が全文を読んでいない報告の文はまとめに出さない
            print(f"数えない: {p.name}（人が受け入れていない。intake の review accept を通す）", file=sys.stderr)
        else:
            good.append(r)
    s = summarize(good)
    sv = service_summary(good)
    if args.json:
        sv_json = {**sv, "stuck": [{"template": t, "form": f, "step": st, "count": c} for (t, f, st), c in sv["stuck"].items()]}
        print(json.dumps({"templates": [{"template": t, "form": f, **g} for (t, f), g in sorted(s.items())], "service": sv_json},
                         ensure_ascii=False, indent=1))
    else:
        print(_markdown(s))
        print(_service_markdown(sv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
