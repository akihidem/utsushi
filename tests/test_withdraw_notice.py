"""取り下げの説明文（本人の決定、Issue #335）。本物の API は呼ばない。

本人が確かめた字を、一字も変えずに置く。一字でも変わったら落ちるように、ここに決定の文を書く（句点も足さない）。

見る線:
- 事実のとおりになる頁に出る: 話す口（玩具の頁・作りながら見る頁）、手帖の上げる節
- 手帖は、記録が増えても 1 回だけ（記録ごとの口は、同じ節の中に並ぶ）
- 持ち寄りの所（ギャラリーの説明と form）には出さない。持ち寄りは書き出す束に入らないので、文の後半が事実と合わない
- 端末の案内に出る: README の取り下げの節、--talk-only の説明、根拠に使われて止めた時の文、取り下げた後の文。番号の打ち間違いには出さない
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("OMOCHAE_VOICE", None)

from omochae import records  # noqa: E402
from web import contrib_server, hanasu  # noqa: E402
from web.play_server import serve  # noqa: E402

DECIDED = "取り下げると、このサイトの中からは消えます。前にエンジンへ渡した分は残ります"
PARA = f'<p class="meta">{DECIDED}</p>'
G = "NDL-1187053-R0000005-L"
ROOT = pathlib.Path(__file__).resolve().parents[1]
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()


def page(path):
    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}") as r:
        return r.read().decode()


def cli(*args):
    # 説明の文が折り返されないように、幅を広くして見る
    return subprocess.run([sys.executable, "-m", "omochae.records", *args], capture_output=True, text=True, stdin=subprocess.DEVNULL, env={**os.environ, "COLUMNS": "400"})


def trial():
    rid, failures = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "わからない"})
    assert not failures, failures
    return rid


rids = [trial(), trial()]

# 話す口: 声の断りのすぐ下に出る。玩具の頁と、作りながら見る頁
for name, path in (("玩具の頁", f"/toy/{G}"), ("作りながら見る頁", f"/toy/{G}/tsukuru?h=H-A&n=2")):
    body = page(path)
    assert body.count(DECIDED) == 1 and re.search(re.escape(hanasu.NOTICE) + r"[^\n]*?</p>" + re.escape(PARA), body), name

# 手帖: 上げる節の説明のすぐ下。記録ごとの口が並んでも 1 回だけ
techo = page(f"/toy/{G}/techo")
assert f'id="up-notice">{hanasu.UPLOAD_NOTICE}</p>{PARA}' in techo and techo.count(DECIDED) == 1
assert techo.count('name="scene" value="keep"') == 2, "記録ごとの口が並ぶ見本になっていない"

# 持ち寄りの所には出さない（「前にエンジンへ渡した分は残ります」が事実と合わない）。説明の文がある事も見て、見本の取り違えで通らないようにする
gallery = page("/gallery")
assert "送られた物は確かめてから載せます。" in gallery and DECIDED not in gallery
assert "取り下げを申し出られる事に同意します" in contrib_server.FORM and DECIDED not in contrib_server.FORM

# README: 取り下げの節に別の段落で置く（行末に句点が無い事まで見る）
readme = (ROOT / "README.md").read_text(encoding="utf-8")
part = readme[readme.index("手帖から上げた記録を消す時は"):readme.index("仮説を自分で立てたい時は")]
assert f"\n{DECIDED}\n" in part and readme.count(DECIDED) == 1

# 文を持つ所は 1 か所
assert records.WITHDRAW_NOTICE == DECIDED

# --talk-only の説明
line = next(x for x in cli("withdraw", "--help").stdout.splitlines() if x.strip().startswith("--talk-only"))
assert line.endswith(DECIDED), line

# 根拠に使われて止めた時の文は --talk-only を案内するので、同じ説明を添える
used_by = records.used_by
records.used_by = lambda rid: ["P-0001"]
gone, fs = records.withdraw(rids[0])
records.used_by = used_by
assert gone == [] and fs[0].floor == "F4.evidence" and "--talk-only" in fs[0].message and fs[0].message.endswith(DECIDED), fs

# 取り下げた後の文は、どの消し方でも最後の行に、そのまま出る
for rid, opts in ((rids[0], []), (rids[1], ["--media-only"]), (trial(), ["--talk-only"])):
    r = cli("withdraw", rid, *opts)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[-1] == DECIDED, r.stdout

# 打ち間違いの番号には、取り下げた時の説明を出さない
r = cli("withdraw", "R-9999")
assert r.returncode == 3 and DECIDED not in r.stdout + r.stderr, r.stdout + r.stderr
print("OK")
