"""どの頁の台本も、ブラウザの音声認識（Web Speech API の SpeechRecognition・webkitSpeechRecognition）を使わない。

なぜ: 本人 11-08「サイトの中の「はなす」がうまく動かない。クロードの音声認識をはずして、ユーザーの端末の音声入力に頼るのでいいのではないか。」と
本人の答え (A)「声を録る釦を置いて残す。」で、話す口・手帖の作る頁・作りながら見る頁の台本から音声認識を外した
（設計は grove の state/no-speech-recognition-20261108.md の 2 版）。作業の頁（web.hmd・/toy/<玩具>/kasane と /kasane/hmd）の声の操作は、
この PR では替えない（統括の決め 11-08: 別の担当の「聞くだけ」の作り直しで外す）。その道だけを WORK として除く。作り直しが入ったら、除くのをやめる
（WORK を空にする。空にした時に落ちれば、まだ残っている）。前の試験は、台本の字の組み合わせを 1 つの頁ずつ見ていたので、
後から別の頁や部品が音声認識を足しても、どの試験も落ちなかった。全部の頁の道（web.i18n.routes。英語の訳し漏れの試験と同じ道）と、
前からの英語の頁・作業の頁・記録を残した画面の手帖の記録の頁（記録の札の足す口が開く）を回し、どの頁の字にも名が無い事を見る。
字は頁の中の台本と CSS と注の全部で見る（注に名が残っていても落とす: 頁を読む人が、使っているのかを見分けられないため）。
読み上げ（speechSynthesis）は音声認識とは別の物で、残す（答えと手順を声で聞く）。
"""
import json
import os
import pathlib
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, records  # noqa: E402
from web import i18n  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

BANNED = ("SpeechRecognition", "webkitSpeechRecognition", "processLocally", "SpeechGrammar", "OMOCHAE_VOICE")
# 作業の頁を聞くだけにする作り直し（先に main に入った）で、作業の頁の音声認識も外れたので、除く道も字も無い（上の注の「除くのをやめる」）
WORK = ()
WORK_SRC = ()
G = "NDL-1187053-R0000005-L"
KEY = "b" * 24  # この画面が記録を残した時の鍵（記録の札の足す口は、その画面にだけ開く・records.mine）

srv = serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"


def get(path, cookie=""):
    req = urllib.request.Request(base + path, headers={"Cookie": cookie} if cookie else {})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, r.read().decode("utf-8", "replace"), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), e.headers.get("Content-Type", "")


try:
    i18n.prime(base, sources())  # 作りながら見る頁と手帖は、刷った後でしか開かない
    # 記録の札の足す口（keep）は、記録を残した画面にだけ開く。1 つ記録を残し、その画面として読む
    body = urllib.parse.urlencode({"hypothesis": hypotheses.sheet_of(G)["id"], "result": "動いた"}).encode()
    urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/record", data=body, headers={"Origin": base}), timeout=120).read()
    rid = records.all_records(G)[-1]["id"]
    records.claim(rid, KEY)
    paths = [p for p in i18n.routes(sources()) + ["/en", f"/en/toy/{G}"] if not p.endswith(WORK)]
    assert len(paths) >= 7 * len(sources()), ("全部の玩具の頁を回す", len(paths))
    seen, bad = 0, []
    for path in paths:
        for cookie in ("", f"utsushi_rec={KEY}"):
            code, text, ctype = get(path, cookie)
            if not ctype.startswith("text/html"):
                continue
            seen += 1
            for word in BANNED:
                if word in text:
                    bad.append((path, word))
    kiroku = get(f"/toy/{G}/techo/kiroku", f"utsushi_rec={KEY}")[1]
    assert f'name="record" value="{rid}"' in kiroku, "記録の札の足す口を開いた画面でも回した"
    assert seen >= len(paths), (seen, len(paths))
    assert not bad, ("音声認識の名が頁にある", bad[:10])
    # 読み上げは残す（音声認識とは別の物）。作りながら見る頁と手帖の作る頁の答えの読み上げ
    for path in (f"/toy/{G}/tsukuru", f"/toy/{G}/techo"):
        assert "speechSynthesis" in get(path)[1], ("読み上げは残す", path)
finally:
    srv.shutdown()
    srv.server_close()
# 台本の元の字（頁に出ない作りの中）にも無い。頁を開かない部品が後から足しても、ここで落ちる
src = [p for p in sorted((ROOT / "src/web").glob("*.py")) if p.name not in WORK_SRC]
named = [p.name for p in src if any(w in p.read_text(encoding="utf-8") for w in ("webkitSpeechRecognition", "new SpeechRecognition", "window.SpeechRecognition"))]
assert not named, ("音声認識を使う台本の字が残っている", named)
print(json.dumps({"pages": seen, "banned": list(BANNED)}, ensure_ascii=False), "ok: どの頁の台本も音声認識を使わない（読み上げは残す）")
