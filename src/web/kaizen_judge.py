"""審査用の頁「改善の一周」（/kaizen。本人の言葉 11-07「提出のデモサイトでは、完成を提出すると改善されて型紙が新しくなるところが見れるページを審査用として入れよう」）。

記録済みの 1 周を、段ごとの札で上から順に見せる（設計 grove の state/judge-page-20261107.md の案 A。その場で回す口は窓口の決めの後）。
判断の芯:
- 字の元は repo の中の記録だけ: サイトの輪は data/records・data/loop、エンジンの輪は改善の歴史の表（data/history/kaizen-history.json。エンジンが出した表の写し）。
  頁で版ごとの字を書き足さない。表が出し直されたら写し直す。
- 誰がしたかを記録のとおりに分ける: 人（作る・説明・決める）・エンジン（記録を束ねた下書きと検査。機械は決めない）・Claude（直しを実装した。commit に共作の印）。
  Claude が記録を読んで案を出す段は、作ってあるが、この 3 つの 1 周では使っていない（本物の API は未実行）。作り話にしないので、その段の札は出さない。
- 本人の名は、字の表の作り手の言い方（wording.MAKER）で言う（表の字の「制作者」も替える。窓口の決め 11-07）。作った人の名前は出さない。
- 合体待ちの版は出さない（窓口の決め 11-07: 入ってから出す）。表の流れの文（story）も、まだ入っていない PR が出てくる間は出さない。
- 誰がしたかが記録に無い段（表の「見直しの指摘」）には、誰の印を付けない（その段は出さない）。
- 新しい字（題・段の名・誰の印・断り）は定数にまとめた。字は本人の確かめ（窓口）。
"""
import json
import pathlib

from . import skin
from .skin import esc
from .wording import MAKER  # 作り手の言い方は字の表の 1 か所（#135）

ROOT = pathlib.Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data/history/kaizen-history.json"
SITE_REC, SITE_EXPL, SITE_CHANGE = ROOT / "data/records/R-0001.json", ROOT / "data/loop/explanation-R-0001.json", ROOT / "data/loop/template-change-0001.json"
# Claude が記録 R-0001 を読んだ案（11-07 02:18 の本物の呼び出し・人の確認待ち）の写し。元は手元の置き場（data/loop・git の外）。
# 写す時に呼び出しの記録（型の名と字の数）を外した。人が確かめると元の置き場が confirmed になり、写しを取り直す
PENDING = ROOT / "data/kaizen-judge/interpretation-R-0001.json"
REPO = "https://github.com/akihidem"

# 新しい字（本人の確かめ・窓口へ）
TITLE = "改善の一周"
LEAD = "作った人の記録から、型紙が直って次の版になるまでを、本当にあった 3 つの一周で見せます。"
WHO = {"human": "人", "engine": "エンジン", "claude": "Claude"}
WHO_NOTE = {"human": "作る・説明する・決める", "engine": "記録を束ねた下書きと検査。決めない", "claude": "直しを実装した"}
NOT_YET = "Claude が記録を読んで直しの案を出す段は、済んだ 3 つの一周では使っていません。最後の 1 件は、Claude が記録を読んだ案で、人の確かめを待っています。"
DONE = "済んだ一周（人が確かめ、採り、版が上がった）"
PENDING_STATE = "Claude の案・人の確認待ち（まだ型紙は変わっていない）"
PENDING_LOOP = "いま回っている一周: Claude が記録を読んだ"
CONF = "確からしさ"
WAIT = "まだ。人が読んで、確かめるか直すかを決める"
NOT_CHANGED = "まだ型紙は変わっていない"
LOOPS = ("1 周目: サイトの輪", "2 周目: エンジンの輪", "山場: 3D で見つかった当たり")

STYLE = """
.kz-loop{margin:40px 0}.kz-loop h2{margin:0 0 6px}
.kz-steps{list-style:none;margin:16px 0 0;padding:0;border-left:2px solid var(--rule)}
.kz-steps li{margin:0 0 18px;padding:0 0 0 18px;position:relative}
.kz-steps li::before{content:"";position:absolute;left:-7px;top:6px;width:12px;height:12px;border-radius:50%;background:var(--paper,#fff);border:2px solid var(--ink)}
.kz-who{display:inline-block;font-size:12px;letter-spacing:.08em;padding:1px 8px;border:1px solid var(--rule);border-radius:10px;margin-right:8px}
.kz-who.human{border-color:var(--ink)}.kz-who.claude{border-color:#b04030;color:#b04030}
.kz-steps h3{display:inline;font-size:16px;margin:0}
.kz-steps p,.kz-steps ul{margin:6px 0 0}.kz-steps ul{padding-left:1.2em}
.kz-ver{font-size:18px;letter-spacing:.06em}
.kz-state{display:inline-block;margin:4px 0 0;padding:2px 10px;border:1px solid var(--ink);border-radius:12px;font-size:13px}
.kz-loop.pending{border:2px dashed #b04030;padding:8px 16px 4px;border-radius:8px}.kz-loop.pending .kz-state{border-color:#b04030;color:#b04030}
.kz-steps li.wait{color:var(--mute)}
"""


def _load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _maker(text):
    return str(text).replace("制作者", MAKER).replace("本人", MAKER)


def _step(who, head, body):
    return (f'<li><span class="kz-who {esc(who)}" title="{esc(WHO_NOTE[who])}">{esc(WHO[who])}</span><h3>{esc(head)}</h3>{body}</li>')


def _p(text):
    return f"<p>{esc(_maker(text))}</p>"


def _ul(items):
    return "<ul>" + "".join(f"<li>{esc(_maker(x))}</li>" for x in items) + "</ul>"


def _pr_links(prs, repo="paper-to-toy"):
    return "・".join(f'<a href="{REPO}/{repo}/pull/{int(n)}">#{int(n)}</a>' for n in prs)


def site_loop():
    """1 周目（サイトの輪・11-04）。記録 R-0001 → 人の説明 → 直し T-0001（雛形の組 goraigo-v8）。"""
    rec, ex, ch = _load(SITE_REC), _load(SITE_EXPL), _load(SITE_CHANGE)
    if not (rec and ex and ch):
        return ""
    v_from, v_to = rec.get("sheet_set", ""), ch.get("sheet_set", "")
    steps = (_step("human", "作った記録", _p(f'{rec.get("tried_on", "")}・見た事「{rec.get("result", "")}」・刷った組 {v_from}'))
             + _step("human", "人の説明", _p(ex.get("text", "")) + (_p("次の思いつき: " + ex["next_idea"]) if ex.get("next_idea") else ""))
             + _step("human", "直しの案", _ul(ch.get("changes", [])))
             + _step("human", "人が決める", _p(f'{MAKER}が採った（{str(ch.get("at", ""))[:10]}）'))
             + _step("claude", "直しを作る", f'<p><a href="{REPO}/utsushi/commit/{esc(ch.get("commit", ""))}">{esc(ch.get("commit", ""))}</a></p>')
             + _step("human", "次の版", f'<p class="kz-ver">{esc(v_from)} → {esc(v_to)}</p>'))
    return f'<section class="sec kz-loop" id="site"><h2>{esc(LOOPS[0])}</h2><p class="kz-state">{esc(DONE)}</p><ol class="kz-steps">{steps}</ol></section>'


def _version(hist, toy_word, set_name):
    toy = next((t for t in hist.get("toys", []) if toy_word in t.get("toy", "")), None)
    return next((v for v in (toy or {}).get("versions", []) if v.get("set") == set_name), None) if toy else None


def _merged(v):
    return v is not None and "合体待ち" not in json.dumps(v, ensure_ascii=False)


def engine_loop(hist):
    """2 周目（エンジンの輪・11-06）。作る様子の札と作る前のレビュー → エンジンが束ねた案 → 人が採る → エンジンの版 2 → 虎 v4。"""
    v = _version(hist, "虎", "tora-v4")
    ev = next((e for e in hist.get("engine_versions", []) if e.get("engine_version") == v.get("engine_version")), None) if v else None
    if not (_merged(v) and ev):
        return ""
    whys = v.get("why", [])
    steps = (_step("human", "作った記録", "".join(_p(w["text"]) for w in whys if "動画" in w.get("kind", "")))
             + _step("human", "人の説明", "".join(_p(w["text"]) for w in whys if "レビュー" in w.get("kind", "")))
             + _step("engine", "直しの案", _p("・".join(ev.get("proposals", []))))
             + _step("human", "人が決める", _p(ev.get("line", "")))
             + _step("claude", "直しを作る", f"<p>{_pr_links(v.get('prs', []))}</p>" + _ul(v.get("changed", [])))
             + _step("human", "次の版", f'<p class="kz-ver">型紙の版 v{int(v["sheet_version"]) - 1} → v{int(v["sheet_version"])}・エンジンの版 {int(v["engine_version"])}</p>'))
    return f'<section class="sec kz-loop" id="engine"><h2>{esc(LOOPS[1])}</h2><p class="kz-state">{esc(DONE)}</p>{_p(v.get("line", ""))}<ol class="kz-steps">{steps}</ol></section>'


def peak_loop(hist):
    """山場（11-07）。サイトの作り方の 3D の試験で虎 v6 の当たり → 見直し → 人が決める → 型紙の版 v7（エンジンの版 7）。"""
    v = _version(hist, "虎", "tora-v7")
    if not _merged(v):
        return ""
    whys = v.get("why", [])
    find = [w for w in whys if "試験" in w.get("kind", "")]
    decide = [w for w in whys if "決定" in w.get("kind", "")]
    steps = (_step("engine", "作った記録", "".join(_p(w["text"]) for w in find))
             + _step("human", "人が決める", "".join(_p(w["text"]) for w in decide))
             + _step("claude", "直しを作る", f"<p>{_pr_links(v.get('prs', []))}</p>" + _ul(v.get("changed", [])))
             + _step("human", "次の版", f'<p class="kz-ver">型紙の版 v{int(v["sheet_version"]) - 1} → v{int(v["sheet_version"])}・エンジンの版 {int(v["engine_version"])}</p>'))
    # 流れの文に、まだ入っていない PR（表の「合体待ち」）が出てくる間は、文を出さない（入っていない事を済んだ事として言わないため）
    waiting = {c.get("pr") for c in hist.get("engine_changes", []) if "合体待ち" in str(c.get("status", ""))}
    text = hist.get("story", "")
    story = _p(text) if text and not any(f"#{n}" in text for n in waiting) else ""
    return f'<section class="sec kz-loop" id="peak"><h2>{esc(LOOPS[2])}</h2><p class="kz-state">{esc(DONE)}</p>{story}<ol class="kz-steps">{steps}</ol></section>'


def pending_loop():
    """いま回っている一周: Claude が記録 R-0001 を読んだ案（人の確認待ち）。済んだ一周と、札の色と字で分ける。
    記録と人の説明は記録の字のまま。Claude の読みは原因の読み（確からしさつき）と分からない事。人が確かめる段と次の版は「まだ」と出す。
    分からない事のうち、作る側の決定の番号が入った物は出さない（学ぶ人の頁と同じく内輪の番号を出さない）。"""
    pend, rec, ex = _load(PENDING), _load(SITE_REC), _load(SITE_EXPL)
    if not (pend and rec and ex) or pend.get("status") != "pending_human" or pend.get("drafted_by") != "claude":
        return ""
    import re
    from .wording import record_no
    causes = "<ul>" + "".join(f'<li>{esc(_maker(c.get("text", "")))}（{esc(CONF)}: {esc(c.get("confidence", ""))}）</li>' for c in pend["content"].get("causes", [])) + "</ul>"
    unknown = [u for u in pend["content"].get("unknown", []) if not re.search(r"(?<![A-Za-z0-9])[JUTWH]-\d+", u)]
    steps = (_step("human", "作った記録", _p(f'{record_no(pend["record_id"])}・{rec.get("tried_on", "")}・見た事「{rec.get("result", "")}」・刷った組 {rec.get("sheet_set", "")}'))
             + _step("human", "人の説明", _p(ex.get("text", "")) + (_p("次の思いつき: " + ex["next_idea"]) if ex.get("next_idea") else ""))
             + _step("claude", "Claude の読み", causes + ("<p>分からない事:</p>" + _ul(unknown) if unknown else ""))
             + _step("human", "人が確かめる", _p(WAIT)).replace("<li>", '<li class="wait">', 1)
             + _step("human", "次の版", _p(NOT_CHANGED)).replace("<li>", '<li class="wait">', 1))
    return (f'<section class="sec kz-loop pending" id="pending"><h2>{esc(PENDING_LOOP)}</h2><p class="kz-state">{esc(PENDING_STATE)}</p>'
            f'<ol class="kz-steps">{steps}</ol></section>')


def page(look=skin.DEFAULT, path="/kaizen"):
    hist = _load(HISTORY) or {}
    body = (f'<section class="sec"><h1>{esc(TITLE)}</h1><p class="lead">{esc(LEAD)}</p><p class="meta">{esc(NOT_YET)}</p></section>'
            + site_loop() + engine_loop(hist) + peak_loop(hist) + pending_loop())
    return skin.shell(TITLE, body, look, "", path, STYLE)
