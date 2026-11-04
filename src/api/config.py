"""実行時のモデルを 1 か所で決める。

全部 Opus 5.5 にするのは本人の決定（docs/process/decisions/J017-runtime-model.md）。質を比べて選んだのではなく、計画書どおりにした判断。
費用の歯止めはモデルでなく src/api/budget.py の上限で持つ。配分を変える時はここだけを直す。
"""
MODELS = {"generate": "claude-opus-5-5", "interpret": "claude-opus-5-5", "propose": "claude-opus-5-5", "words": "claude-opus-5-5", "ask": "claude-opus-5-5"}
# ask は作っている最中の手順の質問（src/api/ask.py）。短い答えなので effort は low、長さも小さく取る。
EFFORT = {"generate": "high", "interpret": "medium", "propose": "high", "words": "medium", "ask": "low"}
ASK_MAX_TOKENS = 2000
MAX_TOOL_CALLS = 8
MAX_RETRIES = 2
MAX_TOKENS = 16000
