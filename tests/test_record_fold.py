"""玩具の頁の記録の欄の畳み（#300「もっと書く（あれば）」）は、欄ごと外した（本人の答え 11-07 夕の Q3「試した記録を残すは寄せる — のこすへ」）。

前のこの試験は、記録の欄のうち最初に見える欄を 3 つにし、残りを畳む形（RECORD_MORE）を見ていた。欄が無くなったので、
同じ名の試験で、欄と畳みが戻っていない事だけを見る（関門の帳面の前の節がこの試験を指すので、名は残す）。
欄が無い事と のこす への道は tests/test_ux_fold_record.py、記録が残せる事は手帖の側（tests/test_techo_step.py）が見る。
"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import toy  # noqa: E402

assert not hasattr(toy, "record_form") and not hasattr(toy, "RECORD_MORE"), "記録の欄の作りが戻っている"
for sid in ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"):
    page = toy.toy_page(sid)
    assert 'id="record"' not in page and "もっと書く（あれば）" not in page, (sid, "記録の欄の畳みが玩具の頁に戻っている")
print("ok 玩具の頁の記録の欄の畳みは、欄ごと外したまま（本人の答え Q3）")
