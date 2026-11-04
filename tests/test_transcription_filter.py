"""Claude に渡す歌の読みに、本人が採らなかった語が残らない事（U-05 の手順書の下見で見つかった不具合、11-04）。"""
import json

from api.generate import transcription_for_claude

src = json.loads(open("data/sources/NDL-1187053-R0000005-L.json", encoding="utf-8").read())
out = json.dumps(transcription_for_claude(src), ensure_ascii=False)
assert "怠らし" not in out, "採らなかった読みの語が、採った読みの注の中から渡っている"
assert "怠けらじ" in out, "採った読みは渡す"
print("ok")
