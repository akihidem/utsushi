"""実行時のモデルを 1 か所で決める。

既定は Opus 5.5（公式の既定）。解釈と差分案を安いモデルに分けるかは本人の判断待ちで、答えが出たらここだけを直す。
"""
MODELS = {"generate": "claude-opus-5-5", "interpret": "claude-opus-5-5", "propose": "claude-opus-5-5"}
EFFORT = {"generate": "high", "interpret": "medium", "propose": "high"}
MAX_TOOL_CALLS = 8
MAX_RETRIES = 2
MAX_TOKENS = 16000
