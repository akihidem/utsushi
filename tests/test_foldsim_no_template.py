"""型紙にできない仮説（template_id が null）は、折りの書き出しも断る（レビュー指摘、print_sheet と同じ意味にそろえる）。

なぜ: 既定の雛形へ黙って落とすと、仮説と無関係な寸法の SVG が「その仮説の折り」として残る。
"""
import tempfile

from omochae import foldsim, hypotheses

real = hypotheses.load


def fake(source_id):
    data = real(source_id)
    data["hypotheses"] = data["hypotheses"] + [{"id": "H-Z", "name": "雛形に無い機構", "how_it_moves": "x", "template_id": None}]
    return data


hypotheses.load = fake
out = tempfile.mkdtemp()
try:
    written = foldsim.export("NDL-1187053-R0000005-L", "H-Z", out)
except ValueError as e:
    assert "型紙にできない" in str(e), e
else:
    raise AssertionError(f"型紙にできない仮説で書き出した: {written}")
import pathlib

assert not list(pathlib.Path(out).iterdir()), "何も書かない"
assert foldsim.main(["H-Z", "--out", out]) == 3, "命令は 3（落ちる）で返す"
print("ok")
