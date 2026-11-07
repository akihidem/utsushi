"""組み方の節は文だけ（本人の答え 11-07 夕の Q2「組み方は 3D を基本として文字で見る。図は要らない」。夕方のサイトのレビューの 4・13）。

見る事:
1. 全部の玩具の組み方の節（玩具の頁の畳みと組み立ての頁の両方が使う kumitate.section）に、手順の間の平らな図（svg）が無い
2. 3D のある玩具（御来迎・虎）は、組み立ての頁で 3D が組み方の文より上。頭の遊び方の文と原図は残す（組み方の図でない）
3. 文だけを読む道（pictures=False）は、絵を組む道と同じ文を返す（手帖が使う絵の道は変えない）
4. 3D の下の断りは、頁から無くなる「組み方の絵」を指さない
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from web import kumitate  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"

# 1. 全部の玩具
sids = sorted(p.stem for p in (hypotheses.ROOT / "data/hypotheses").glob("*.json"))
with_steps = 0
for sid in sids:
    sec = kumitate.section(sid)
    if not sec:
        continue
    with_steps += 1
    steps_part = sec[sec.index('<ol class="kumi-steps">'):]
    assert "<svg" not in sec and "kumi-pic" not in sec, (sid, "組み方の節に図が残っている")
    assert re.findall(r"<li><p>(.*?)</p></li>", steps_part, re.S), (sid, "手順の文が無い")
assert len(sids) >= 83 and with_steps >= 80, (len(sids), with_steps)

# 2. 3D のある玩具の組み立ての頁
for sid in (G, T):
    page = kumitate.page(sid)
    assert kumitate.available(sid) and page.index('id="kumitate"') < page.index('id="kumikata"'), (sid, "3D が文より上")
    assert f"<b>{kumitate.PLAY_HEAD}</b>" in page, (sid, "遊び方の文は残す")

# 3. 文だけの道と、絵を組む道
texts, pictures, which = kumitate.steps(T)
only = kumitate.steps(T, pictures=False)
assert only[0] == texts and only[1] == [] and only[2] == [-1] * len(texts), "文だけの道は同じ文を返す"
assert pictures, "絵を組む道（手帖が使う）は今のまま"

# 4. 断りの指し先
assert "組み方" in kumitate.NOTE_SHAPE and "組み方の絵" not in kumitate.NOTE_SHAPE

print(f"ok 組み方の節は文だけ（{with_steps} 種で図なし・3D は文より上・遊び方の文は残す・断りは組み方を指す）")
