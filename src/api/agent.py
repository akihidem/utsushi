"""上限つきの小さなエージェントの輪。

なぜ Tool Runner でなく自分で書くか: 道具 8 回・やり直し 2 回の上限で必ず止まり、そこまでの結果を人へ渡すため。
常駐しない。人の操作（記録の確定など）の後に 1 回だけ呼ばれる。
最終結果は submit_result の道具で受ける。Opus 5.5 は tool_choice の強制が使えないので、指示と自前の検証で守る。
"""
from dataclasses import dataclass, field

from . import budget, config

BETAS = ["server-side-fallback-2026-07-01"]


class AgentStopped(Exception):
    """上限・拒否・長さの超過で結果なしに止まった。理由を人に見せる。"""


class Preview(Exception):
    """下見の時、最初の呼び出しの直前で止めて、送るはずだった中身を運ぶ。"""

    def __init__(self, request):
        super().__init__("下見なので呼ばなかった")
        self.request = request


class PreviewClient:
    """下見の偽の client。鍵も通信も要らない。

    なぜ: 本物の試験の前に、本人が「何を送るか」を見て承認できるようにするため。
    本物と同じ run を通すので、下見と本番で送る中身がずれない。
    """

    def __init__(self):
        from types import SimpleNamespace

        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **request):
        raise Preview(request)


def elide_images(request):
    """下見の記録に画像の中身を残さない。大きく、人が読む物でないため。大きさだけ書く。"""
    import copy

    out = copy.deepcopy(request)
    for message in out.get("messages", []):
        for block in message["content"] if isinstance(message.get("content"), list) else []:
            if isinstance(block, dict) and block.get("type") == "image":
                block["source"]["data"] = f"<base64 {len(block['source']['data'])} 文字を省いた>"
    return out


@dataclass
class Trace:
    tool_calls: list = field(default_factory=list)
    retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


def default_client():
    """鍵は repo の .env から読む。起動の環境に鍵を置かない運用なので、ここでだけ読み、表示も記録もしない。"""
    import pathlib

    import anthropic

    env = pathlib.Path(__file__).resolve().parents[2] / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("ANTHROPIC_API_KEY=") and line.split("=", 1)[1].strip():
                return anthropic.Anthropic(api_key=line.split("=", 1)[1].strip())
    return anthropic.Anthropic()


def schema_errors(instance, schema):
    """提出された結果を、提出の道具に渡した JSON Schema で見る。失敗の文の一覧を返す。

    なぜ自前で見るか: 道具の input_schema は Claude への案内で、API は形を強制しない（strict を使っていない）。
    欠けた欄の案が受付を通らないよう、受ける側で決定的に落とす（外の検品の指摘、11-04）。
    """
    from jsonschema import Draft202012Validator

    return [f"{'/'.join(str(x) for x in e.absolute_path) or '(全体)'}: {e.message}" for e in Draft202012Validator(schema).iter_errors(instance)]


def run(role, system, user, tools, submit_schema, execute, validate=None, client=None):
    """Returns (result, trace)。execute(name, input) は道具の実行、validate(result) は失敗の文の一覧を返す。"""
    client = client or default_client()
    trace = Trace(model=config.MODELS[role])
    definitions = tools + [{"name": "submit_result", "description": "最終結果を提出する。作業の最後に必ず 1 回呼ぶ。", "input_schema": submit_schema}]
    messages = [{"role": "user", "content": user}]
    run_usd = 0.0
    for _ in range(config.MAX_TOOL_CALLS + config.MAX_RETRIES + 3):
        # 呼ぶ前に毎回見る。途中で上限に当たれば、そこで止めて人へ返す。
        # この 1 回の最悪の費用（送る中身の見積もり + 出力の上限）まで足して見る。今までの消費だけだと 1 回分はみ出す。
        budget.check(run_usd, budget.worst_case(trace.model, budget.estimate_tokens(system, definitions, messages), config.MAX_TOKENS))
        # 1 回の生成で道具の往復ごとに図と指示を送り直すので、キャッシュで入力の費用を下げる。
        # 指示と道具の定義は変わらないので、その終わりに目印を置く。伸びていく会話は自動の目印に任せる。
        response = client.beta.messages.create(
            model=trace.model, max_tokens=config.MAX_TOKENS, system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            tools=definitions, messages=messages, cache_control={"type": "ephemeral"},
            output_config={"effort": config.EFFORT[role]}, thinking={"type": "adaptive"}, betas=BETAS, fallbacks="default",
        )
        usage = getattr(response, "usage", None)
        counts = {k: getattr(usage, k, 0) or 0 for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}
        # 入力の数はキャッシュの外の残りだけなので、書いた分と読んだ分も足して数える。足さないと費用を少なく見積もる。
        trace.input_tokens += counts["input_tokens"] + counts["cache_creation_input_tokens"] + counts["cache_read_input_tokens"]
        trace.output_tokens += counts["output_tokens"]
        run_usd += budget.add(role, trace.model, counts["input_tokens"], counts["output_tokens"], counts["cache_creation_input_tokens"], counts["cache_read_input_tokens"])
        if response.stop_reason == "refusal":
            raise AgentStopped("Claude が応答を断った。入力を人が確かめる")
        if response.stop_reason == "max_tokens":
            raise AgentStopped("応答が長さの上限に達した")
        messages.append({"role": "assistant", "content": response.content})
        uses = [b for b in response.content if b.type == "tool_use"]
        if not uses:
            messages.append({"role": "user", "content": "submit_result を呼んで結果を提出してください。"})
            trace.retries += 1
            if trace.retries > config.MAX_RETRIES:
                raise AgentStopped("結果が提出されなかった")
            continue
        results = []
        submitted = None
        for block in uses:
            if block.name == "submit_result":
                submitted = block
                continue
            if len(trace.tool_calls) >= config.MAX_TOOL_CALLS:
                results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": "道具の上限に達した。今ある情報で submit_result を呼ぶ。"})
                continue
            trace.tool_calls.append(block.name)
            try:
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": execute(block.name, block.input)})
            except Exception as e:  # 道具の失敗は Claude に返して直させる。輪全体を落とさない
                results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": f"{type(e).__name__}: {e}"})
        if submitted is not None and len(uses) > 1:
            # 同じ応答で他の道具も呼んだ時の提出は、その道具の結果を読む前に書かれている。受けずに結果を返し、出し直させる。
            # tool_use には必ず tool_result を返す決まりなので、提出にも「受けなかった」を返す。
            # 検査の落ちではないのでやり直しの回数には数えない。止まるのは輪の上限（range）で保証する。
            results.append({"type": "tool_result", "tool_use_id": submitted.id, "is_error": True, "content": "同じ応答で他の道具も呼んだので、この提出は受けていない。道具の結果を読んでから、submit_result だけを呼び直す。"})
        elif submitted is not None:
            errors = validate(submitted.input) if validate else []
            if not errors:
                return submitted.input, trace
            trace.retries += 1
            if trace.retries > config.MAX_RETRIES:
                raise AgentStopped("検査に落ち続けた: " + " / ".join(errors))
            results.append({"type": "tool_result", "tool_use_id": submitted.id, "is_error": True, "content": "検査に落ちた。直して提出し直す: " + " / ".join(errors)})
        messages.append({"role": "user", "content": results})
    raise AgentStopped("輪の上限に達した")
