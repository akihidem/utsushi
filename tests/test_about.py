"""序の頁の試験。本人の言葉と書誌の値が出て、仮説の名前と成績の言葉が出ない事、2 つの皮で変数が違う事を見る。"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae.marks import without_premise  # noqa: E402
from web import about  # noqa: E402

pages = {k: about.page(k) for k in ("tenji", "zine")}
for k, h in pages.items():
    for w in ("『江都二色』", "1773", "北尾重政", "紙で実験して確かめる道具", "AI は鏡", "info:ndljp/pid/1187053", "TIMSS 2023", "採否待ち", 'href="/toys"'):
        assert w in h, (k, w)
    # 仕組みの答えと仮説の名前を書かない。成績の言葉を使わない
    for w in ("成功", "失敗", "正解", "仮説 A", "H-A", "つまみ", "内筒"):
        assert w not in without_premise(h), (k, w)
    assert "IntersectionObserver" not in h and "<blockquote>" in h, k
# 末尾の 2 つは同じ釦の形にする。字のリンクを並べると、並びの高さに伸びて縦長の押す所になり、下線が字から離れる（#141）
for k, h in pages.items():
    assert '<a class="btn" href="/toys">おもちゃを選ぶ</a><a class="btn quiet" href="/">入口へ戻る</a>' in h, k
roots = [re.search(r":root\{([^}]*)\}", h).group(1) for h in pages.values()]
assert roots[0] != roots[1] and "--bg:#fcfcfa" in roots[0] and "--bg:#0b0a09" in roots[1]
print("ok")
