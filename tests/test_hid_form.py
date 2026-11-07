"""仮説の印の形でない値では、刷った紙を探さない（セキュリティの点検 U16）。

なぜ: printed_versions の hid は、フォーム（talk・record-json・ask）から検査なしで来る。glob の形にそのまま入れると、
「..」や「**」で置き場の外まで広く探させられ、合言葉なしで開いた場でもサーバを詰まらせられた。
印の形（H-… と OWN-数。紙を返す口 /sheet/... と同じ形）の時だけ探し、ほかは探さずに空を返す。
"""
import os
import pathlib
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
d = pathlib.Path(tempfile.mkdtemp())
for name in ("H-A_v1.pdf", "H-A_v3.pdf", "H-N1_v2.pdf", "OWN-2_v1_free.pdf", "OWN-2_v2.pdf", "H-A_v1_tejun.pdf", "memo.txt"):
    (d / name).write_bytes(b"%PDF")


class Dir:
    """置き場の代わり。探した形を数える（探さない事を確かめるため）。"""

    def __init__(self, path):
        self.path, self.asked = path, []

    def exists(self):
        return True

    def glob(self, pattern):
        self.asked.append(pattern)
        return self.path.glob(pattern)


box = Dir(d)
play_server.out_dir = lambda sid: box

# 印の形の物は、今までどおり刷った版の番号を返す
assert play_server.printed_versions(G, "H-A") == [1, 3], play_server.printed_versions(G, "H-A")
assert play_server.printed_versions(G, "H-N1") == [2]
assert play_server.printed_versions(G, "OWN-2") == [1, 2], "自分の仮説は型紙なしの紙（_free）も数える"
assert play_server.printed_versions(G, "H-B") == []
seen = len(box.asked)

# 印の形でない値は、探さずに空を返す
for bad in ("", "../H-A", "H-A/../H-A", "*", "**", "**/H-A", "H-A*", "H-?", "[H]-A", "h-a", "H-", "OWN-", "OWN-x", "OWN-1/..", "H-A\n", "H-A ", None, 3, ["H-A"]):
    assert play_server.printed_versions(G, bad) == [], bad
assert len(box.asked) == seen, f"印の形でない値で探した: {box.asked[seen:]}"
print("ok: 印の形でない値では、刷った紙を探さない")
