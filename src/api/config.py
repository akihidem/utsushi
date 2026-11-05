"""実行時のモデルを 1 か所で決める。

全部 Opus 5.5 にするのは本人の決定（docs/process/decisions/J017-runtime-model.md）。質を比べて選んだのではなく、計画書どおりにした判断。
費用の歯止めはモデルでなく src/api/budget.py の上限で持つ。配分を変える時はここだけを直す。
"""
MODELS = {"generate": "claude-opus-5-5", "interpret": "claude-opus-5-5", "propose": "claude-opus-5-5", "words": "claude-opus-5-5", "ask": "claude-opus-5-5", "observe": "claude-opus-5-5"}
# ask は作っている最中の手順の質問（src/api/ask.py）。短い答えなので effort は low、長さも小さく取る。
EFFORT = {"generate": "high", "interpret": "medium", "propose": "high", "words": "medium", "ask": "low", "observe": "low"}
ASK_MAX_TOKENS = 2000
MAX_TOOL_CALLS = 8
MAX_RETRIES = 2
MAX_TOKENS = 16000
# 画面の要求の中で呼ぶ役の時間切れ（秒）とやり直しの回数。SDK の既定（10 分・2 回）だと、応答が返らない時に頁が長く固まる。
# 値は見込み（本物の API をまだ呼んでいないので、応答の時間は測っていない）。ask と observe は短い答えで、interpret は考える分だけ長く取る。
# 命令から呼ぶ役（generate・propose・words）は人が待てるので、SDK の既定のまま。
SCREEN_TIMEOUT = {"ask": 45, "observe": 60, "interpret": 90}
SCREEN_RETRIES = 1
# 画面の役の輪（道具の往復）全部の時間の上限（秒）。1 回ごとの時間切れだけだと、往復の数だけ長くなる。
RUN_TIME_LIMIT = {"interpret": 180}
# ffprobe と ffmpeg の 1 本の時間切れ（秒）。上げられた動画は中身を確かめていないので、壊れた動画で止まり得る。
VIDEO_TIMEOUT = 15
