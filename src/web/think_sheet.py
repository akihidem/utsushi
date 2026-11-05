"""話した考えから紙を作り直す（ループ1、Issue #335）。玩具の頁の「考えを話す」の節のすぐ後に置く小さな節と、その受け口。

本人の言葉（11-05 17:57）「インカメラか音声でAIが作った仮説を見ながら自分の考えを話す。このときこの仮説に反応して型紙が生成されるとなお良い」。
生まれる紙は「たたき台から変えた、その人の案」（#332）で、新しい仮説を並べる形にしない。
本人の決定（11-05 18:08）「仮説は書かず、話すことができる。そうすると型紙を再生成できる」: 入口は話した考え（talk_log の think）だけで、
書く欄（自分の仮説の form）は使わない。作り直す元はその玩具のたたき台（api.words.tatakidai。今は H-A）。中身の道は api.words（request_think・fill_think・adopt_words）。

判断の芯:
- どの考えか: 画面のその場限りの印（who。skin.WHO_SCRIPT が POST のフォームに足す）で、その人が最後に残した考えを選ぶ（words.latest_think）。印が無い画面（JS なし）では作れない。
- 採った案の字は、玩具の頁の札に出さない（words.spoken_own_ids で外す）: 話した字は、記録に結ぶ前は学ぶ人の頁に出さない決まり（talk_log）。本人は印の URL で見る。
- 頼んだ後の様子は、本人だけが持つ印（token）の URL で見る（/toy/<玩具>?at=think-<印>#think）。W-番号は数えられるので、番号では開かない。
- 鍵がある所では、押した 1 回で Claude に寸法を写させる。鍵が無い所・合言葉なしで開いた場（J-028: 費用のかかる呼び出しをさせない）・呼べなかった時は、
  作る側の待ちに置く（作る側が端末で python -m api.words fill を打つ）。どちらも、刷る前に本人がこの節で、変えた所と決めた所を見て「この紙にする」を押す。
- 刷るのは今ある自分の仮説の道（hypotheses.save_own → print_own）。紙には「自分で立てた」の印（marks.OWN_HYPOTHESIS）が刷られ、
  雛形に乗らない考えは型紙なしの紙（print_free）になる。紙の置き場と開く道（/sheet/<玩具>/OWN-n_v1…）も今の物のまま。
- 紙を作った直後に、その紙の絵を節の中に出す。順位・点・推しは付けない（#145 の要件を話す道でも。理由の文は api.words.check_no_rank が入口で止める）。
- 利用者向けの文は少なく、小学生に分かる言葉にした。どれも「文面は本人の確認待ち」（Issue #318 の決まり: 採られた文ではない）。
  順位や良し悪しの言葉は使わない（J-025）。
"""
import json
import urllib.parse

from api import words
from omochae import hypotheses, making_log

from .play_server import esc, out_dir

# ── 利用者向けの文。文面は本人の確認待ち（どれも新しい文。採られたら、このまま固定する） ──
GO = "この考えから紙を作る"  # 文面は本人の確認待ち
LEAD = "残した考えに合わせて、もとの紙を変えます。"  # 文面は本人の確認待ち
NONE = "先に、考えを話すか書いて「残す」を押してください。"  # 文面は本人の確認待ち
WAITING = "作る人が、この考えから紙を作っています。あとで、もう一度この釦を押すと、続きが見られます。"  # 文面は本人の確認待ち
CHECK = "あなたの言葉から変えた所と、こちらで決めた所です。よければ「この紙にする」を押してください。"  # 文面は本人の確認待ち
FROM_WORDS = "あなたの言葉から"  # 文面は本人の確認待ち
FILLED = "こちらで決めた所"  # 文面は本人の確認待ち
NO_FIT = "今の型紙には合わないので、型紙なしの紙（身の回りの紙とひもで作る紙）になります。"  # 文面は本人の確認待ち
OK = "この紙にする"  # 文面は本人の確認待ち
DONE = "紙ができました。"  # 文面は本人の確認待ち
SEE = "紙を見る"  # 文面は本人の確認待ち
ASKED = "頼みました。"  # 文面は本人の確認待ち
FAILED = "紙を作れませんでした。もう一度押してください。"  # 文面は本人の確認待ち

SAME = "もとの紙のまま"  # 文面は本人の確認待ち
# 寸法の呼び名。今ある呼び名（toy._param_label）に無い物だけ、必須 2 種の分を足す。文面は本人の確認待ち。ほかの玩具の呼び名は確認の後に足す。
NAMES = {"push_part": "押す所", "hub": "扇の中心", "pusher_height": "内筒の高さ（mm）", "mount": "頭の付け方"}  # 文面は本人の確認待ち
VALUES = {"tab": "つまみ", "tube": "内筒", "stick": "柄", "axle": "軸", "rim": "筒の口の台", "neck": "首を穴に入れる", "hang": "吊る"}  # 文面は本人の確認待ち

# 本人が画面で採った印（adopt_words の decided_by）。名前は受けない決まりなので、役の名前だけを残す。
BY_PAGE = "画面で本人"


def labels(h):
    """自分の仮説として残す時の名前と根拠（紙に刷られる）。文面は本人の確認待ち。"""
    letter = hypotheses.letter(h)
    return f"仮説 {letter} から変えた案", f"仮説 {letter} の紙を見て話した考え"


def use_claude(handler):
    """鍵があり、合言葉なしで開いた場でない時だけ Claude を呼ぶ（J-028）。"""
    from api import ask

    return not getattr(handler.server, "public_open", False) and ask._key_present()


def request(sid, who, claude=False, client=None):
    """押した 1 回の中身（試験からも呼ぶ）。Returns (記録, 本人へ返す文か None)。
    一番新しい考えから既に頼んであれば、その案へ戻す: 2 度押しで案を並べず、後で戻って来た人が（本人の印の URL を持っていなくても）様子を見られるように。"""
    talk, name = words.latest_think(sid, who)
    if talk is None:
        return None, NONE
    w = words.asked_for(name)
    if w is not None:
        return w, None
    source = json.loads((hypotheses.ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    title, evidence = labels(words.base_of(sid)[0])
    w, failures = words.request_think(source, talk, name, title, evidence, client=client, use_claude=claude)
    if failures:
        from .hanasu import reason  # 床に当たった時の文は、話す口の採られた文をそのまま使う

        return None, reason(failures)
    return w, None


def confirm(sid, token):
    """本人が「この紙にする」を押した時。採って、自分の仮説として刷る。Returns (刷った紙の名前か None, 文か None)。
    採った後に刷れなかった時は、もう一度押せば刷り直す（採るのは 1 回だけ。押した人の案を失わない）。"""
    w = words.by_token(sid, token)
    if w is None:
        return None, FAILED
    if w.get("status") == "pending_human":
        rec, failures = words.adopt_words(w["id"], BY_PAGE)
        if failures:
            return None, FAILED
        oid = rec["id"]
    elif w.get("status") == "decided" and not sheet_of(sid, w.get("own_id", "")):
        oid = w.get("own_id", "")
    else:
        return None, FAILED
    out_dir(sid).mkdir(parents=True, exist_ok=True)
    if hypotheses.print_own(sid, oid, str(out_dir(sid) / f"{oid}_v1")) != 0:
        return None, FAILED
    return sheet_of(sid, oid), None


def sheet_of(sid, oid):
    """刷った紙の名前（型紙か、型紙なしの紙）。まだ無ければ None。"""
    for name in (f"{oid}_v1.pdf", f"{oid}_v1_free.pdf"):
        if (out_dir(sid) / name).exists():
            return name
    return None


def _name(template, k):
    from .toy import _param_label

    return NAMES.get(k) or _param_label(template, k)


def _value(v):
    return VALUES.get(v, v) if isinstance(v, str) else v


def _changes(sid, w, r):
    """変えた所は「もと → 今」で、文を見た人が決めた所は理由つきで、もとのままの所は畳んで見せる。内部の名前を学ぶ人に見せない（今ある呼び名を使う）。"""
    template = hypotheses.load(sid).get("template", "slider_fan")
    p, base = r.get("params", {}), w.get("base_params") or {}
    said = "".join(f"<li>{esc(_name(template, k))}: {esc(_value(base[k])) + ' → ' if k in base else ''}{esc(_value(p.get(k)))}</li>" for k in r.get("from_words", []))
    filled = [f for f in r.get("filled_in", []) if f["why"] != words.KEPT_AS_IS]
    kept = [f["param"] for f in r.get("filled_in", []) if f["why"] == words.KEPT_AS_IS]
    out = f'<p>{esc(CHECK)}</p><p class="meta">{esc(FROM_WORDS)}</p><ul>{said}</ul>'
    if filled:
        items = "".join(f"<li>{esc(_name(template, f['param']))}: {esc(_value(p.get(f['param'])))}（{esc(f['why'])}）</li>" for f in filled)
        out += f'<p class="meta">{esc(FILLED)}</p><ul>{items}</ul>'
    if kept:
        items = "".join(f"<li>{esc(_name(template, k))}: {esc(_value(p.get(k)))}</li>" for k in kept)
        out += f"<details><summary>{esc(SAME)}</summary><ul>{items}</ul></details>"
    return out


def _status(sid, w):
    if w["status"] == "waiting_maker":
        return f"<p>{esc(WAITING)}</p>"
    said = f'<blockquote>{esc(w["how_it_moves"])}</blockquote>'
    ok = (f'<form method="post" action="/toy/{esc(sid)}/think-ok"><input type="hidden" name="t" value="{esc(w["token"])}">'
          f"<button>{esc(OK)}</button></form>")
    if w["status"] == "decided":
        name = sheet_of(sid, w.get("own_id", ""))
        if not name:  # 採った後に刷れなかった時。押せば刷り直す（confirm）
            return f"{said}<p>{esc(FAILED)}</p>{ok}"
        # 紙を作った直後に、その紙の絵を画面に出す（#145 の要件を話す道でも）。絵は刷る時に PDF と一緒にできる。押すと PDF を開く。
        pic = name[:-len(".pdf")] + ".png"
        fig = f'<figure class="own-sheet" style="margin:12px 0"><a href="/sheet/{esc(sid)}/{esc(name)}"><img src="/sheet/{esc(sid)}/{esc(pic)}" alt="{esc(w["name"])}" style="display:block;width:100%;border:1px solid var(--frame)"></a></figure>' if (out_dir(sid) / pic).exists() else ""
        return f'{said}<p>{esc(DONE)} <a href="/sheet/{esc(sid)}/{esc(name)}">{esc(SEE)}</a></p>{fig}'
    r = w.get("result") or {}
    if r.get("fits"):
        body = _changes(sid, w, r)
    else:
        items = "".join(f"<li>{esc(x)}</li>" for x in r.get("not_fit", []))
        body = f"<p>{esc(NO_FIT)}</p><ul>{items}</ul>"
    return f"{said}{body}{ok}"


def section(sid, at="", note=""):
    """玩具の頁の小さな節。at が think-<印> の時（頼んだ後に戻った時）だけ、その様子と note（返事の文）を出す。"""
    w = words.by_token(sid, at[len("think-"):]) if at.startswith("think-") else None
    status = _status(sid, w) if w else ""
    # 確かめている間は頼む釦を出さない（押しても同じ案へ戻るだけで、押す釦が 2 つ並ぶと迷う）。
    go = "" if w and w["status"] == "pending_human" else f'<form method="post" action="/toy/{esc(sid)}/think-sheet"><button class="quiet">{esc(GO)}</button></form>'
    return f'<section class="sec" id="think">{note if at.startswith("think") else ""}<p class="lead">{esc(LEAD)}</p>{status}{go}</section>'


def post(handler, sid, act, form):
    """受け口（/toy/<玩具>/think-sheet と /think-ok）。戻り先は玩具の頁のこの節（送られた値を戻り先にしない）。"""
    if act == "think-sheet":
        w, why = request(sid, form.get("who", ""), claude=use_claude(handler))
        token, msg = (w["token"], ASKED) if w else ("", why)
    else:
        token = form.get("t", "")
        _, why = confirm(sid, token)
        msg = why or ""  # できた時の文は節の中に出る（2 回並べない）
    if not token or (act == "think-ok" and why):
        return handler._send(422, handler._toy(sid, errors=[msg], at="think"))
    return handler._send(303, "", headers=[("Location", f"/toy/{sid}?msg={urllib.parse.quote(msg)}&at=think-{urllib.parse.quote(token)}#think")])
