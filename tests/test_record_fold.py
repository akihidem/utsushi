"""玩具の頁の記録の欄の畳み（#300「もっと書く（あれば）」）は、欄ごと外した（本人の答え 11-07 夕の Q3「試した記録を残すは寄せる — のこすへ」）。

前のこの試験は、記録の欄のうち最初に見える欄を 3 つにし、残りを畳む形（RECORD_MORE）を見ていた。欄が無くなったので、
同じ名の試験で、欄と畳みが戻っていない事だけを見る（関門の帳面の前の節がこの試験を指すので、名は残す）。
欄が無い事と のこす への道は tests/test_ux_fold_record.py、記録が残せる事は手帖の側（tests/test_techo_step.py）が見る。
畳みの開け閉めの印（skin.TAP_FLOOR の summary::before）は、ほかの畳みのために、ここで続けて見る。
"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import toy  # noqa: E402

assert not hasattr(toy, "record_form") and not hasattr(toy, "RECORD_MORE"), "記録の欄の作りが戻っている"
for sid in ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"):
    page = toy.toy_page(sid)
    assert 'id="record"' not in page and "もっと書く（あれば）" not in page, (sid, "記録の欄の畳みが玩具の頁に戻っている")
# 押す所の決まり（#137）で summary を inline-flex にする幅でも、畳み（組み方・これまでの記録ほか）の開け閉めの印が出る。
# 消えると、ただの字に見えて畳みに気づけない。前は記録の欄の畳みを見る所で一緒に見ていた（欄を外した後も、ほかの畳みのために残す。別の目の指摘 11-07）
from web import skin  # noqa: E402

assert "summary::before" in skin.TAP_FLOOR and "details[open]>summary::before" in skin.TAP_FLOOR
assert "▶" not in skin.TAP_FLOOR, "iPhone で絵文字になる事がある"
assert skin.TAP_FLOOR in toy.toy_page("NDL-1187053-R0000005-L")
print("ok 玩具の頁の記録の欄の畳みは、欄ごと外したまま（本人の答え Q3）。ほかの畳みの開け閉めの印は出る")
