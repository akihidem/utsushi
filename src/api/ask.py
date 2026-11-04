"""作っている最中の手順の質問に答える口（本人の決定、2026-11-04）。

本人の元の言葉: 試行で作っていた人たちが「谷折り、山折りがわからない」などの作る時の疑問を Claude に聞けるといいのでは。
範囲は手順の質問だけで、聞かれた時だけ答える。仮説への返事の順（紙 → 本人の記録と説明 → AI）は変えない。

判断の芯:
- 仕組み・動き方・どの仮説かの質問には答えない。予想を書いて紙で試す前に答えを渡さないため（F9.prediction、J-013）
- よく出る言葉（谷折り・山折り・糊代・蛇腹・色の境など）は、型紙に刷った説明だけからその場で答える。AI も鍵も要らない
- それ以外は Claude に、その紙の組み方と凡例と用意する物だけを渡して答えさせる。仮説の名前と動き方は渡さない
- 答えに仮説の名前や動き方の文が混ざったら、出さずに断りの文に替える（渡していないが、念のため出口でも見る）
- 本物の API は、本人が repo の .env に鍵を置いた時だけ動く（J-023。鍵を置く事が本人の承認）。鍵が無ければ、その旨を返す
"""
from omochae import hypotheses
from omochae.compose import TEMPLATES

from . import budget, config

MECHANISM_WORDS = ("仕組み", "しくみ", "どう動", "どうやって動", "なぜ動", "どうして動", "動き方", "正解", "答え", "仮説", "本当は", "昔は", "どれが正しい", "どっちが正しい")
REFUSE = "それは、予想を書いて紙で試して確かめる所なので、ここでは答えません。試した後に、記録と説明を残してから考えてみてください。"
NO_KEY = "AI の答えは、まだ使えません（鍵が置かれていない）。型紙の凡例と手順の紙の絵を見てください。"
MAX_QUESTION = 300

# 型紙に刷った説明（凡例・組み方・手順の紙の絵）と同じ中身だけで答える。新しい作り方を足さない。
GLOSSARY = {
    "谷折り": "谷折りは、折った所が手前にへこむ折り方です。型紙では破線で、線の無い面（筒と扇）は色の境で折ります。",
    "山折り": "山折りは、折った所が手前に出る折り方です。型紙では一点鎖線で、線の無い面（筒と扇）は色の境で折ります。",
    "糊代": "糊代は、斜線の所です。そこにのりを付けて、となりの部分の裏に貼ります。",
    "のりしろ": "糊代は、斜線の所です。そこにのりを付けて、となりの部分の裏に貼ります。",
    "蛇腹": "蛇腹は、山折りと谷折りを交互にして、端から順に畳む形です。手順の紙の「蛇腹（横から）」の絵で、上の角が山、下の角が谷です。",
    "ジャバラ": "蛇腹は、山折りと谷折りを交互にして、端から順に畳む形です。手順の紙の「蛇腹（横から）」の絵で、上の角が山、下の角が谷です。",
    "色の境": "線の無い面（外筒と扇）は、色が変わる所で折ります。扇は 2 色の板が交互で、その境が折り目です。",
    "物差し": "刷った物差しに定規を当てて 10cm か確かめます。違う時は、印刷の設定を「100%」（用紙に合わせない）にして刷り直します。",
}


def is_mechanism(question):
    return any(w in question for w in MECHANISM_WORDS)


def glossary(question):
    hits = [text for word, text in GLOSSARY.items() if word in question]
    return " ".join(dict.fromkeys(hits)) or None


def sheet_context(source_id, hypothesis_id):
    """その紙の組み方・用意する物だけ。仮説の名前と動き方は入れない。"""
    data = hypotheses.load(source_id)
    h = next(x for x in data["hypotheses"] if x["id"] == hypothesis_id)
    tpl = TEMPLATES[h.get("template") or data.get("template", "slider_fan")]
    p = {**tpl.DEFAULTS, **h.get("params", {})}
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(tpl.steps(p), 1))
    materials = "\n".join(f"・{m}" for m in tpl.materials(p))
    legend = "切る＝実線、谷折り＝破線（手前にへこむ）、山折り＝一点鎖線（手前に出る）、糊代＝斜線。線の無い面（外筒と扇）は色の境で折る"
    return f"組み方:\n{steps}\n\n用意する物:\n{materials}\n\n凡例: {legend}", h


SYSTEM = ("あなたは紙工作の手順の質問だけに答える係です。渡された組み方・用意する物・凡例の範囲で、切る・折る・貼る・組む順の疑問に、"
          "やさしい日本語で 3 文以内で答えます。仕組み・動き方・なぜ動くか・どれが正しいかは答えず、「試して確かめる所です」とだけ言います。"
          "渡された文に無い作り方を足しません。分からない時は「手順の紙の絵を見てください」と言います。")


def leaks(answer, h):
    """答えに仮説の名前や動き方の文が混ざっていないか。"""
    return any(x and x in answer for x in (h.get("name"), h.get("how_it_moves"), "仮説"))


def answer(source_id, hypothesis_id, question, client=None):
    """Returns (答えの文, どこから: "glossary"|"ai"|"refuse"|"no_key")。聞かれた時だけ呼ぶ。記録には残さない。"""
    question = (question or "").strip()[:MAX_QUESTION]
    if not question:
        return "聞きたい事を書いてください。", "refuse"
    if is_mechanism(question):
        return REFUSE, "refuse"
    known = glossary(question)
    if known:
        return known, "glossary"
    context, h = sheet_context(source_id, hypothesis_id)
    if client is None:
        from .agent import default_client

        if not _key_present():
            return NO_KEY, "no_key"
        client = default_client()
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
