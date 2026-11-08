"""上げた動画を Claude が見る観察の補助（J-022、本人の「最初の構想を全て実装し終えたい」、11-04）。

J-022 の線: 動画を Claude が見るのは観察の補助と型紙の判定だけで、成績にしない。順位を付けない。
判断の芯:
- 動画から 3 コマを取り出して見せる（ffmpeg）。声は渡さない（上げる時の決まりも「声なし」）
- 返すのは「見えた事」と「見えなかった事」だけ。仕組みの答え・成否・上手下手は言わせず、出口でも言葉を見る
- 人の説明が先（J-013）。記録に人の説明が無ければ呼ばない
- 本物の API は本人が鍵を置いた時だけ（J-023）。費用は今までの見張り（budget）で、呼ぶ前に最悪の費用を足して見る
"""
from omochae.marks import LOOP_PREMISE, without_premise
import base64
import json
import pathlib
import subprocess
import tempfile

from omochae import loop, store

from . import budget, config

# 本人の言葉（11-05）「カメラで見るのはそういうとこだよ」: 見るのは、不完全な型紙（AI の仮説）を人が工夫で乗り切る過程で、人の出来を測るためではない。
SYSTEM = (LOOP_PREMISE + "\n紙で作った玩具を手で動かした短い動画のコマを見て、見えた事だけを書く係です。"
          "どの部品がどう動いたか、どこで止まったか、紙がたわんだか、人がどう工夫して乗り切ったか、を見えたとおりに短く書きます。人の出来は書きません。"
          "仕組みの答え、昔の作り方、うまい・へた、成功・失敗、点数は書きません。見えない事は「見えなかった事」に書きます。")
SCHEMA = {"type": "object", "properties": {"observed": {"type": "array", "items": {"type": "string"}},
                                           "unclear": {"type": "array", "items": {"type": "string"}}},
          "required": ["observed", "unclear"]}
BANNED = ("成功", "失敗", "正解", "上手", "下手", "点数", "順位")


def frames(video_path, n=3):
    """動画から等間隔に n コマを JPEG で取り出す。ffmpeg が無い・読めない・時間切れの時は空。"""
    out = []
    with tempfile.TemporaryDirectory() as d:
        try:
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video_path)],
                                       capture_output=True, text=True, check=True, timeout=config.VIDEO_TIMEOUT).stdout.strip() or 0)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
            return []
        for i in range(n):
            t = dur * (i + 0.5) / n
            f = pathlib.Path(d) / f"f{i}.jpg"
            try:
                r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video_path), "-frames:v", "1", "-vf", "scale=640:-1", str(f)],
                                   capture_output=True, timeout=config.VIDEO_TIMEOUT)
            except (OSError, subprocess.TimeoutExpired):
                return []
            if r.returncode == 0 and f.exists():
                out.append(f.read_bytes())
    return out


def path(rid):
    return loop.folder() / f"observation-{rid}.json"


def observation(rid):
    return store.read_json_or_skip(path(rid))


def observe(rid, video_path, client):
    """Returns (結果 or None, 断った理由)。結果は記録の横に置き、人が読む（観察の補助で、採点に使わない）。"""
    if not loop.explained(rid):  # 取り下げで字が空になった説明も、説明が無いと読む（J-013）
        return None, "人の説明が先"
    imgs = frames(video_path)
    if not imgs:
        return None, "動画のコマを取り出せない"
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(b).decode()}} for b in imgs]
    content.append({"type": "text", "text": "この 3 コマで見えた事を、決まった形の JSON だけで返してください: {\"observed\": [...], \"unclear\": [...]}"})
    budget.check(0.0, budget.worst_case(config.MODELS["observe"], 3 * 1600 + 400, config.ASK_MAX_TOKENS))
    try:
        r = client.messages.create(model=config.MODELS["observe"], max_tokens=config.ASK_MAX_TOKENS, system=SYSTEM,
                                   messages=[{"role": "user", "content": content}], thinking={"type": "adaptive"}, output_config={"effort": config.EFFORT["observe"]})
    except BaseException:  # 呼べなかった時は予約を返す（安全の事項 3 への対応・budget の頭の注）
        budget.release()
        raise
    usage = getattr(r, "usage", None)
    budget.add("observe", config.MODELS["observe"], getattr(usage, "input_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0)
    text = "".join(getattr(b, "text", "") for b in r.content if getattr(b, "type", "") == "text").strip()
    try:
        result = json.loads(text[text.index("{"): text.rindex("}") + 1])
    except ValueError:
        return None, "答えの形が読めない"
    if not isinstance(result.get("observed"), list) or not isinstance(result.get("unclear"), list):
        return None, "答えの形が違う"
    flat = " ".join(map(str, result["observed"] + result["unclear"]))
    # 前提の文の否定の形（正解ではなく）を返事が引いても、成績の語とは数えない（marks.without_premise）。
    if any(w in without_premise(flat) for w in BANNED):
        return None, "成否や点の言葉が入っていたので出さない"
    loop._write(path(rid), {"record_id": rid, "observed": result["observed"], "unclear": result["unclear"], "video": pathlib.Path(video_path).name, "by": "claude", "label": "観察（Claude の補助）", "at": loop._now()})
    return result, ""
