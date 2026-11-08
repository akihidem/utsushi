"""作っている最中の手順の質問に答える口（本人の決定、2026-11-04）。

本人の元の言葉: 試行で作っていた人たちが「谷折り、山折りがわからない」などの作る時の疑問を Claude に聞けるといいのでは。
範囲は手順の質問だけで、聞かれた時だけ答える。仮説への返事の順（紙 → 本人の記録と説明 → AI）は変えない。

判断の芯:
- 仕組み・動き方・どの仮説かの質問には答えない。紙で試す前に答えを渡さないため（J-013）
- よく出る言葉（谷折り・山折り・糊代・蛇腹・色の境など）そのものを尋ねる短い問いは、型紙に刷った説明だけからその場で答える。AI も鍵も要らない
- 語が入っていても作り方を聞く問いは、語の説明では答えにならないので、ほかの問いと同じに扱う（#287。試行で一番手こずった蛇腹の固定がこの形）
- それ以外は Claude に、その紙の組み方と凡例と用意する物だけを渡して答えさせる。仮説の名前と動き方は渡さない
- 答えに仮説の名前や動き方の文が混ざったら、出さずに断りの文に替える（渡していないが、念のため出口でも見る）
- 本物の API は、本人が repo の .env に鍵を置いた時だけ動く（J-023。鍵を置く事が本人の承認）。鍵が無ければ、その旨を返す
- 玩具ごとの中身（11-08）: 語の表（GLOSSARY）の字は御来迎の紙（扇の紙 slider_fan。筒と扇・組み方の絵の蛇腹と色の境）の字で、前は
  どの玩具にも返していた（公開デモの虎で「谷折り・山折り」と聞くと、御来迎の筒と扇の答えが返った）。字は本人の確かめの字なので一字も
  替えず、使う玩具を扇の紙に絞る。ほかの玩具の語の問いは、その紙の組み方と凡例を渡して Claude に聞く（鍵が無ければ断りだけ）。
  Claude に渡す凡例も、前は全部の玩具に御来迎の字（線の無い面（外筒と扇）は色の境で折る）と前の谷と山の言い方を渡していたので、
  その玩具の型紙が刷る字（compose の谷と山の言い方）から作り、色の境の 1 句は扇の紙にだけ添える（instructions が蛇腹と色の境の絵を刷るのも扇の紙だけ）
"""
import re

from omochae import compose, hypotheses
from omochae.compose import TEMPLATES

from . import budget, config

MECHANISM_WORDS = ("仕組み", "しくみ", "どう動", "どうやって動", "なぜ動", "どうして動", "動き方", "正解", "答え", "仮説", "本当は", "昔は", "どれが正しい", "どっちが正しい")
REFUSE = "それは、紙で試して確かめる所なので、ここでは答えません。試した後に、記録と説明を残してから考えてみてください。"
# 呼び名は「組み方の絵」（文章のプリント廃止で手順の紙は刷らなくなり、絵は組み立ての頁と作りながら見る頁で見る。本人の確認済み 11-06）
NO_KEY = "AI の答えは、この場では使えません。型紙の凡例と、組み方の絵を見てください。"
MAX_QUESTION = 300

# 型紙に刷った説明（凡例・組み方・組み方の絵）と同じ中身だけで答える。新しい作り方を足さない。
GLOSSARY = {
    "谷折り": "谷折りは、折った所が手前にへこむ折り方です。型紙では破線で、線の無い面（筒と扇）は色の境で折ります。",
    "山折り": "山折りは、折った所が手前に出る折り方です。型紙では一点鎖線で、線の無い面（筒と扇）は色の境で折ります。",
    "糊代": "糊代は、斜線の所です。そこにのりを付けて、となりの部分の裏に貼ります。",
    "のりしろ": "糊代は、斜線の所です。そこにのりを付けて、となりの部分の裏に貼ります。",
    "蛇腹": "蛇腹は、山折りと谷折りを交互にして、端から順に畳む形です。組み方の絵の「蛇腹（横から）」で、上の角が山、下の角が谷です。",
    "ジャバラ": "蛇腹は、山折りと谷折りを交互にして、端から順に畳む形です。組み方の絵の「蛇腹（横から）」で、上の角が山、下の角が谷です。",
    "色の境": "線の無い面（外筒と扇）は、色が変わる所で折ります。扇は 2 色の板が交互で、その境が折り目です。",
    "物差し": "刷った物差しに定規を当てて 10cm か確かめます。違う時は、印刷の設定を「100%」（用紙に合わせない）にして刷り直します。",
}
# 語そのものを尋ねる形。問い全体がこの形の時だけ語の表で答える（#287）。語の後に別の中身があれば、語の説明は答えにならない。
# 迷う形は入れない: 外れても AI か「語の説明と、鍵が無い事」に落ちるだけだが、入れすぎると工夫を聞いた人に定義だけが返る。
# 手帖の頁の JS も同じ形を使う（web/techo.py の data）ので、JS でも読める書き方だけにする。
TERM_QUESTION = (
    rf"(?:(?:{'|'.join(map(re.escape, GLOSSARY))})[\s、,・とや]*)+"
    r"(?:って|とは|は|が|の|を)?\s*"
    r"(?:(?:何|なに|なん)(?:のこと)?(?:ですか|でしょうか)?|(?:どういう)?意味(?:は|ですか)?|(?:わから|分から)ない(?:です)?|(?:わかり|分かり)ません|教えて(?:ください)?)?"
    r"[\s。．.、,？?！!…]*"
)


def is_mechanism(question):
    return any(w in question for w in MECHANISM_WORDS)


def glossary(question):
    hits = [text for word, text in GLOSSARY.items() if word in question]
    return " ".join(dict.fromkeys(hits)) or None


def asks_term(question):
    return re.fullmatch(TERM_QUESTION, question) is not None


FAN = "slider_fan"  # 語の表と、凡例の色の境の 1 句が書かれた紙（御来迎）


def template_name(source_id, hypothesis_id=None):
    """その紙の雛形の名。hypothesis_id が無い時は、その玩具のたたき台の紙。"""
    data = hypotheses.load(source_id)
    if hypothesis_id:
        h = next((x for x in data["hypotheses"] + hypotheses.own_hypotheses(source_id) if x["id"] == hypothesis_id), {})
    else:
        h = hypotheses.sheet_of(source_id)
    return h.get("template") or data.get("template", FAN)


def legend(template):
    """その雛形の型紙が刷る凡例の字（谷と山の言い方は compose が刷る物と同じ）。色の境で折る 1 句は扇の紙だけ。"""
    valley, mountain = compose.FOLD_WORDS if compose.new_fold_words(TEMPLATES[template]) else compose._OLD_SHEET_FOLD_WORDS
    out = f"切る＝実線、{valley}＝破線、{mountain}＝一点鎖線、糊代＝斜線"
    return out + "。線の無い面（外筒と扇）は色の境で折る" if template == FAN else out


def sheet_context(source_id, hypothesis_id):
    """その紙の組み方・用意する物だけ。仮説の名前と動き方は入れない。"""
    data = hypotheses.load(source_id)
    # 話した考えから作った本人の案（OWN-n）も、その紙の寸法で答える（ループ1、#335）。名前と話した字は入れない。
    h = next(x for x in data["hypotheses"] + hypotheses.own_hypotheses(source_id) if x["id"] == hypothesis_id)
    name = h.get("template") or data.get("template", FAN)
    tpl = TEMPLATES[name]
    if hypothesis_id.startswith("OWN-") and not h.get("params"):  # 型紙なしの紙に、雛形の手順は無い。無い手順を答えさせない
        return "組み方: 型紙の無い紙です。手順は刷った紙にあります。", h
    p = {**tpl.DEFAULTS, **(h.get("params") or {})}
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(tpl.steps(p), 1))
    materials = "\n".join(f"・{m}" for m in tpl.materials(p))
    return f"組み方:\n{steps}\n\n用意する物:\n{materials}\n\n凡例: {legend(name)}", h


SYSTEM = ("あなたは紙工作の手順の質問だけに答える係です。渡された組み方・用意する物・凡例の範囲で、切る・折る・貼る・組む順の疑問に、"
          "やさしい日本語で 3 文以内で答えます。仕組み・動き方・なぜ動くか・どれが正しいかは答えず、「試して確かめる所です」とだけ言います。"
          "渡された文に無い作り方を足しません。分からない時は「組み方の絵を見てください」と言います。")


def leaks(answer, h):
    """答えに仮説の名前や動き方の文が混ざっていないか。"""
    return any(x and x in answer for x in (h.get("name"), h.get("how_it_moves"), "仮説"))


def answer(source_id, hypothesis_id, question, client=None, allow_ai=True):
    """Returns (答えの文, どこから: "glossary"|"ai"|"refuse"|"no_key")。聞かれた時だけ呼ぶ。この関数は何も残さない。
    allow_ai=False は、鍵の有り無しに関わらず Claude を呼ばない（合言葉なしの公開の場・安全の事項 5 への対応）。返す字と形は鍵が無い時と同じ。
    質問の文を残すのは呼び手（play_server が omochae.making_log に、連絡先の形を落として残す。本人の決定 11-05、J-027）。"""
    question = (question or "").strip()[:MAX_QUESTION]
    if not question:
        return "聞きたい事を書いてください。", "refuse"
    if is_mechanism(question):
        return REFUSE, "refuse"
    fan = template_name(source_id, hypothesis_id) == FAN  # 語の表は扇の紙の字（上の芯の玩具ごとの中身）
    if asks_term(question) and fan:
        return glossary(question), "glossary"
    context, h = sheet_context(source_id, hypothesis_id)
    if not allow_ai:
        # 公開の場では、立てた後に鍵が置かれても呼ばない（立てる時の鍵の確かめだけに頼らない）。字は鍵が無い時と同じにして、頁の見た目と挙動を替えない
        known = glossary(question) if fan else None
        return f"{known} {NO_KEY}" if known else NO_KEY, "no_key"
    if client is None:
        from .agent import default_client

        if not _key_present():
            # 語が入っていれば語の説明は残す。ただ問いの答えにはならないので、語の表で答えた問いとは分けて no_key と返す。
            known = glossary(question) if fan else None
            return f"{known} {NO_KEY}" if known else NO_KEY, "no_key"
        client = default_client("ask")
    messages = [{"role": "user", "content": f"{context}\n\n質問: {question}"}]
    # 呼ぶ前に、この 1 回の最悪の費用まで足して上限を見る（輪の agent.run と同じ見方。外の検品の指摘、11-04）。
    budget.check(0.0, budget.worst_case(config.MODELS["ask"], budget.estimate_tokens(SYSTEM, messages), config.ASK_MAX_TOKENS))
    response = client.messages.create(
        model=config.MODELS["ask"], max_tokens=config.ASK_MAX_TOKENS, system=SYSTEM,
        messages=messages,
        thinking={"type": "adaptive"}, output_config={"effort": config.EFFORT["ask"]},
    )
    usage = getattr(response, "usage", None)
    budget.add("ask", config.MODELS["ask"], getattr(usage, "input_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0)
    text = "".join(getattr(b, "text", "") for b in response.content if getattr(b, "type", "") == "text").strip()
    if not text or leaks(text, h):
        return REFUSE, "refuse"
    return text, "ai"


def _key_present():
    import pathlib

    env = pathlib.Path(__file__).resolve().parents[2] / ".env"
    return env.exists() and any(line.startswith("ANTHROPIC_API_KEY=") and line.split("=", 1)[1].strip()
                                for line in env.read_text(encoding="utf-8").splitlines())
