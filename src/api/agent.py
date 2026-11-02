"""上限つきの小さなエージェントの輪。

なぜ Tool Runner でなく自分で書くか: 道具 8 回・やり直し 2 回の上限で必ず止まり、そこまでの結果を人へ渡すため。
常駐しない。人の操作（記録の確定など）の後に 1 回だけ呼ばれる。
最終結果は submit_result の道具で受ける。Opus 5.5 は tool_choice の強制が使えないので、指示と自前の検証で守る。
"""
from dataclasses import dataclass, field

from . import config

BETAS = ["server-side-fallback-2026-07-01"]


class AgentStopped(Exception):
    """上限・拒否・長さの超過で結果なしに止まった。理由を人に見せる。"""


@dataclass
class Trace:
    tool_calls: list = field(default_factory=list)
    retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


def default_client():
    import anthropic

    return anthropic.Anthropic()


def run(role, system, user, tools, submit_schema, execute, validate=None, client=None):
    """Returns (result, trace)。execute(name, input) は道具の実行、validate(result) は失敗の文の一覧を返す。"""
    client = client or default_client()
    trace = Trace(model=config.MODELS[role])
    definitions = tools + [{"name": "submit_result", "description": "最終結果を提出する。作業の最後に必ず 1 回呼ぶ。", "input_schema": submit_schema}]
    messages = [{"role": "user", "content": user}]
    for _ in range(config.MAX_TOOL_CALLS + config.MAX_RETRIES + 3):
        response = client.beta.messages.create(
            model=trace.model, max_tokens=config.MAX_TOKENS, system=system, tools=definitions, messages=messages,
            output_config={"effort": config.EFFORT[role]}, thinking={"type": "adaptive"}, betas=BETAS, fallbacks="default",
        )
        usage = getattr(response, "usage", None)
        trace.input_tokens += getattr(usage, "input_tokens", 0) or 0
        trace.output_tokens += getattr(usage, "output_tokens", 0) or 0
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
        if submitted is not None:
            errors = validate(submitted.input) if validate else []
            if not errors:
                return submitted.input, trace
            trace.retries += 1
            if trace.retries > config.MAX_RETRIES:
                raise AgentStopped("検査に落ち続けた: " + " / ".join(errors))
            results.append({"type": "tool_result", "tool_use_id": submitted.id, "is_error": True, "content": "検査に落ちた。直して提出し直す: " + " / ".join(errors)})
        messages.append({"role": "user", "content": results})
    raise AgentStopped("輪の上限に達した")
