"""作業の頁の「聞く」に答える口（本人 11-08 539「3D 重ねずに、質問もできるだけにしよう。質問した時のその瞬間の写真を何枚か撮って、
音声を文字にして認識して、クロードが考えて答えを音声で出すようにする。iPhone のカメラと HMD で使えるようにする。記録はここでは取らず、
質問のための経路と割り切る。」）。設計は grove の state/kasane-ask-20261108.md（2 版・3 版）。

判断の芯:
- 答える範囲は手帖の「こまった」の口（api.ask）と同じ。仕組み・動き方・どの仮説かには答えず、語そのものの問いは語の表で答える（J-013・#287）。
  渡すのはその紙の組み方・用意する物・凡例（ask.sheet_context）と今の手順の字だけで、仮説の名前と動き方は渡さない。出口でも ask.leaks で見る
- 違うのは 2 つ。手元の写真（3 枚まで）を一緒に渡す事と、何も残さない事（539「記録はここでは取らず」）。この関数は何も書かない。
  呼ぶ側（play_server）も making_log・talk_log・records を呼ばない。費用の台帳（budget.add）には、日・役・型・数・額だけが入る（字は入らない）
- 写真に人の顔や体が写っていたら、写真に触れずに断るよう答えの決まりに書く。これは送った後の手当てで、送る前の止めは頁の側
  （後ろのカメラと分かる時だけ撮る・HMD の道は撮らない）
- 答えは声で読み上げるので、話し言葉で短く、記号や箇条書きを使わない形に決める
- 型は今の決まり（config.MODELS の 1 か所・J017）のまま。速さのために替えるかは本人の決め（設計の 2 版の 6）
"""
import base64

from omochae import hypotheses

from . import ask, budget, config

ROLE = "kasane"
MAX_FRAMES = 3
SYSTEM = (ask.SYSTEM + "写真が付いている時は、作っている人の手元の写真です。手順を助けるために見ます。"
          "写真に人の顔や体が写っていたら、写真のことには触れず、「手元だけを写してください」とだけ言います。"
          "答えは声で読み上げるので、話し言葉で 2 文か 3 文にし、記号や箇条書きを使いません。うまい・へた、できた・できていないは言いません。")


def answer(source_id, question, frames=(), step_line="", client=None):
    """Returns (答えの文, どこから: "glossary"|"ai"|"refuse"|"no_key")。question は字にした問い、frames は JPEG の中身の並び（3 枚まで）。
    step_line は今の手順の字（呼ぶ側が頁と同じ組み方の文から作る）。この関数は何も残さない。"""
    question = (question or "").strip()[:ask.MAX_QUESTION]
    if not question:
        return "", "refuse"
    if ask.is_mechanism(question):
        return ask.REFUSE, "refuse"
    if ask.asks_term(question):
        return ask.glossary(question), "glossary"
    if client is None:
        from .agent import default_client

        if not ask._key_present():
            return ask.NO_KEY, "no_key"
        client = default_client(ROLE)
    context, h = ask.sheet_context(source_id, hypotheses.sheet_of(source_id)["id"])
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(b).decode()}}
               for b in list(frames)[:MAX_FRAMES]]
    content.append({"type": "text", "text": f"{context}\n\n{step_line}\n\n質問: {question}".replace("\n\n\n\n", "\n\n")})
    messages = [{"role": "user", "content": content}]
    # 呼ぶ前に、この 1 回の最悪の費用まで足して上限を見る（api.ask と同じ見方）。写真は 1 枚を決まった数で数える（budget.estimate_tokens）
    budget.check(0.0, budget.worst_case(config.MODELS[ROLE], budget.estimate_tokens(SYSTEM, messages), config.ASK_MAX_TOKENS))
    response = client.messages.create(
        model=config.MODELS[ROLE], max_tokens=config.ASK_MAX_TOKENS, system=SYSTEM, messages=messages,
        thinking={"type": "adaptive"}, output_config={"effort": config.EFFORT[ROLE]},
    )
    usage = getattr(response, "usage", None)
    budget.add(ROLE, config.MODELS[ROLE], getattr(usage, "input_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0)
    text = "".join(getattr(b, "text", "") for b in response.content if getattr(b, "type", "") == "text").strip()
    if not text or ask.leaks(text, h):
        return ask.REFUSE, "refuse"
    return text, "ai"
