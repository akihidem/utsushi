"""話した考えから紙を作り直す（ループ1、Issue #335）。玩具の頁の「考えを話す」の節のすぐ後に置く小さな節と、その受け口。

本人の言葉（11-05 17:57）「インカメラか音声でAIが作った仮説を見ながら自分の考えを話す。このときこの仮説に反応して型紙が生成されるとなお良い」。
生まれる紙は「たたき台から変えた、その人の案」（#332）で、新しい仮説を並べる形にしない。
本人の決定（11-05 18:08）「仮説は書かず、話すことができる。そうすると型紙を再生成できる」: 入口は話した考え（talk_log の think）だけで、
書く欄（自分の仮説の form）は使わない。作り直す元はその玩具のたたき台の一番新しい版（api.words.base_of）。中身の道は api.words（request_think・fill_think・adopt_words）。

判断の芯:
- どの考えか: 画面のその場限りの印（who。skin.WHO_SCRIPT が POST のフォームに足す）で、その人が最後に残した考えを選ぶ（words.latest_think）。印が無い画面（JS なし）では作れない。
- 採った案の字は、玩具の頁の札に出さない（words.spoken_own_ids で外す）: 話した字は、記録に結ぶ前は学ぶ人の頁に出さない決まり（talk_log）。本人は印の URL で見る。
- 頼んだ後の様子は、本人だけが持つ印（token）の URL で見る（/toy/<玩具>?at=think-<印>#think）。W-番号は数えられるので、番号では開かない。
- 節は、たたき台の寸法が全部読める玩具の頁だけに出す（ready。今は必須 2 種）。雛形に呼び名の無い寸法が残っていても、それを変える案は作らない（api.words.check_names）。
- 話した字が読める物（頼んだ後の頁・OWN-n の紙・字が刷られた手順の紙）は、作った本人の画面からしか開かない。その場限りの印（who）を確かめて頼んだ人に、印（token）を cookie で渡す。
  who は sessionStorage にあって GET に載らず、絵と別タブの PDF では送れないため、cookie にした。URL に載せないので、URL を渡されても開かない。ブラウザを閉じれば消える（押し直すと、同じ who の人は受け取り直せる）。
- 1 台の機械を順に使う場のために、鍵には期限があり（api.words.key_live。2 時間）、記録を残すとその案は閉じる（api.words.key_open）。同じタブの who で押し直しても、閉じた案へは戻らない。
  試した後の紙だけは、話した字が刷られず、記録の後に本人が使う紙なので、記録を残した後も期限の中は開く。
- 合言葉なしの場では、節も受け口も閉じ、OWN-n の紙は開かない（J-028 の線。誰でも開ける場で、人の言葉を別の人に見せない）。
- 鍵がある所では、押した 1 回で Claude に寸法を写させる。鍵が無い所・合言葉なしで開いた場（J-028: 費用のかかる呼び出しをさせない）・呼べなかった時は、
  作る側の待ちに置く（作る側が端末で python -m api.words fill を打つ）。どちらも、刷る前に本人がこの節で、変えた所と決めた所を見て「この紙にする」を押す。
- 刷るのは今ある自分の仮説の道（hypotheses.save_own → print_own）。紙には「自分で立てた」の印（marks.OWN_HYPOTHESIS）が刷られ、
  雛形に乗らない考えは型紙なしの紙（print_free）になる。紙の置き場と開く道（/sheet/<玩具>/OWN-n_v1…）も今の物のまま。
- 紙を作った直後に、その紙の絵を節の中に出す。順位・点・推しは付けない（#145 の要件を話す道でも。理由の文は api.words.check_no_rank が入口で止める）。
- 利用者向けの文は少なく、小学生に分かる言葉にした。本人の決定（11-05 21:5x・全部このまま）で採られた文で、一字も変えない（tests/test_loop1_think.py の ADOPTED が見る）。
  順位や良し悪しの言葉は使わない（J-025）。
"""
import json
import urllib.parse

from api import words
from omochae import hypotheses, making_log

from .play_server import esc, out_dir

# ── 利用者向けの文。本人の決定（11-05 21:5x・全部このまま）で採られた文 ──
GO = "この考えから紙を作る"
LEAD = "残した考えに合わせて、もとの紙を変えます。"
NONE = "先に、考えを話すか書いて「残す」を押してください。"
WAITING = "作る人が、この考えから紙を作っています。あとで、もう一度この釦を押すと、続きが見られます。"
CHECK = "あなたの言葉から変えた所と、こちらで決めた所です。よければ「この紙にする」を押してください。"
FROM_WORDS = "あなたの言葉から"
FILLED = "こちらで決めた所"
NO_FIT = "今の型紙には合わないので、型紙なしの紙（身の回りの紙とひもで作る紙）になります。"
OK = "この紙にする"
DONE = "紙ができました。"
SEE = "紙を見る"
MAKE = "作りながら見る（机の端に置く・試作）"  # 玩具の頁の入口と同じ字（新しい文を足さない）
ASKED = "頼みました。"
FAILED = "紙を作れませんでした。もう一度押してください。"

SAME = "もとの紙のまま"
# 寸法の呼び名。今ある呼び名（toy._param_label）に無い物だけ、必須 2 種の分を足した（同じ決定）。ほかの玩具の呼び名は新しい文なので、足す時に本人の確認が要る。
NAMES = {"push_part": "押す所", "hub": "扇の中心", "pusher_height": "内筒の高さ（mm）", "mount": "頭の付け方"}
VALUES = {"tab": "つまみ", "tube": "内筒", "stick": "柄", "axle": "軸", "rim": "筒の口の台", "neck": "首を穴に入れる", "hang": "吊る"}

# 本人が画面で採った印（adopt_words の decided_by）。名前は受けない決まりなので、役の名前だけを残す。
BY_PAGE = "画面で本人"


def labels(h):
    """自分の仮説として残す時の名前と根拠（紙に刷られる）。本人の決定（11-05 21:5x）で採られた文。"""
    letter = hypotheses.letter(h)
    return f"仮説 {letter} から変えた案", f"仮説 {letter} の紙を見て話した考え"


COOKIE = "utsushi_own_"


def _tokens(handler):
    """その画面が持つ印。"""
    out = set()
    for part in handler.headers.get("Cookie", "").split(";"):
        name, _, value = part.strip().partition("=")
        if name.startswith(COOKIE) and value:
            out.add(value)
    return out


def _key_header(handler, w):
    """本人の画面へ印を渡す。ブラウザを閉じれば消えるように Max-Age を付けない。外から開く場（合言葉付き）は https なので Secure を付ける。"""
    secure = "; Secure" if getattr(handler.server, "public_key", None) else ""
    return ("Set-Cookie", f"{COOKIE}{w['id']}={w['token']}; Path=/; HttpOnly; SameSite=Lax{secure}")


def _holds(handler, sid, token):
    """その印の案を、この画面が今開いてよいか（鍵を持ち、期限の中で、まだ記録で区切っていない）。"""
    w = words.by_token(sid, token) if token in _tokens(handler) else None
    return bool(w and words.key_open(w))


def mine(handler, sid):
    """この画面が今開いてよい案の OWN-n。記録の form・手帖の札・作りながら見る頁に、本人の案だけを出すために引く（ほかの人の案は並べない）。"""
    if getattr(handler.server, "public_open", False):
        return set()
    found = (words.by_token(sid, t) for t in _tokens(handler))
    return {w["own_id"] for w in found if w and w.get("own_id") and words.key_open(w)}


def latest_mine(handler, sid):
    """この画面の一番新しい案（作りながら見る頁が、紙の印の無い時に開く紙）。無ければ None。"""
    return max(mine(handler, sid), key=lambda oid: int(oid.rsplit("-", 1)[1]), default=None)


def usable(handler, sid, hid):
    """その紙への札・工夫・問い・記録を、この画面から受けてよいか。話した考えから作った案は、作った本人の画面からだけ（期限の内・記録の前）。ほかの紙は今までどおり。"""
    return not str(hid).startswith("OWN-") or hid not in words.spoken_own_ids(sid) or hid in mine(handler, sid)


def opens(handler, sid, oid, after=False):
    """OWN-n の紙を、この画面に開いてよいか。書いて立てた仮説の紙は今までどおり（合言葉なしの場を除く）。after は試した後の紙（記録で閉じない）。"""
    if getattr(handler.server, "public_open", False):
        return False
    if oid not in words.spoken_own_ids(sid):
        return True
    usable = words.key_live if after else words.key_open
    return any((w := words.by_token(sid, t)) and w.get("own_id") == oid and usable(w) for t in _tokens(handler))


def allowed_at(handler, sid, at):
    """頼んだ後の頁を開く at。本人の印でなければ、節を開かない（URL だけでは話した字を見せない）。"""
    if at.startswith("think-") and (getattr(handler.server, "public_open", False) or not _holds(handler, sid, at[len("think-"):])):
        return ""
    return at


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
        return (w, None) if words.key_open(w) else (None, NONE)  # 閉じた案の鍵は渡し直さない（同じタブの次の人）
    if not words.think_fresh(talk):
        return None, NONE
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
    # 紙に刷った組を、刷る時に残す（たたき台を刷る時と同じ型紙の確定）。束が、この紙の記録を同じ組の札や工夫と同じ群に入れるため。記録の時の組では、版が上がった後に違う組になる。
    from omochae import loop
    from omochae.compose import TEMPLATES

    loop.confirm_sheet(sid, oid, 1, BY_PAGE, TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].SHEET_SET)
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


def readable(template, k, v):
    """学ぶ人が読める形で出せるか。呼び名の無い寸法と、呼び名の無い字の値は、内部の名前になる。"""
    return _name(template, k) != k and (not isinstance(v, str) or v in VALUES)


def ready(sid):
    """節を出す玩具か。たたき台の寸法が全部読める玩具だけ（今は必須 2 種）。内部の名前（board_w など）を学ぶ人に見せないため。
    ほかの玩具の呼び名は新しい文で、足す時に本人の確認が要る。足せば、ここが自然に真になる。"""
    template, params = hypotheses.load(sid).get("template", "slider_fan"), words.base_of(sid)[1]
    return bool(params) and all(readable(template, k, v) for k, v in params.items())


def changeable(sid):
    """その玩具で変えられる寸法（呼び名のある物）。Claude と作る側へ先に見せる。"""
    from omochae.compose import TEMPLATES

    template = hypotheses.load(sid).get("template", "slider_fan")
    t = TEMPLATES[template]
    return sorted(k for k in {*getattr(t, "DEFAULTS", {}), *getattr(t, "RANGES", {})} if _name(template, k) != k)


def _changes(sid, w, r):
    """変えた所は「もと → 今」で、文を見た人が決めた所は理由つきで、もとのままの所は畳んで見せる。内部の名前を学ぶ人に見せない（今ある呼び名を使う）。"""
    template = hypotheses.load(sid).get("template", "slider_fan")
    p, base = r.get("params", {}), words.current_values(sid, w.get("base_params"))
    said = "".join(f"<li>{esc(_name(template, k))}: {esc(_value(base[k])) + ' → ' if k in base else ''}{esc(_value(p.get(k)))}</li>" for k in r.get("from_words", []))
    filled = [f for f in r.get("filled_in", []) if f["why"] != words.KEPT_AS_IS]
    # もとのままの所は、読める物だけを出す（変わらないので、確かめに要らない。雛形の既定の寸法を、内部の名前で出さない）。
    kept = [f["param"] for f in r.get("filled_in", []) if f["why"] == words.KEPT_AS_IS and readable(template, f["param"], p.get(f["param"]))]
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
        # 次の段（作る）への道。その紙の手順の頁を開き、工夫がこの紙に付く（本人の描く一周の順）。
        make = f'<p><a class="btn quiet" href="/toy/{esc(sid)}/tsukuru?h={esc(w.get("own_id", ""))}">{esc(MAKE)}</a></p>'
        return f'{said}<p>{esc(DONE)} <a href="/sheet/{esc(sid)}/{esc(name)}">{esc(SEE)}</a></p>{fig}{make}'
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
        w = None
        # 印を知っているだけでは採れない。本人の画面（cookie）からだけ。
        _, why = confirm(sid, token) if _holds(handler, sid, token) else (None, FAILED)
        msg = why or ""  # できた時の文は節の中に出る（2 回並べない）
    if not token or (act == "think-ok" and why):
        return handler._send(422, handler._toy(sid, errors=[msg], at="think"))
    headers = [("Location", f"/toy/{sid}?msg={urllib.parse.quote(msg)}&at=think-{urllib.parse.quote(token)}#think")]
    return handler._send(303, "", headers=headers + ([_key_header(handler, w)] if w else []))
