"""雛形の直しの記録（U-32）。記録と人の説明が先に無いと置けず、置いた物は台帳から引ける。"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import loop, records  # noqa: E402

G = "NDL-1187053-R0000005-L"
rid, f = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "わからない"})
assert rid and not f
args = dict(sheet_set="goraigo-v8", commit="9e590cd", changes=["溝を下から切り込む"], by="本人")
tid, f = loop.save_template_change([rid], **args)
assert tid is None and {x.floor for x in f} == {"F9.human"}, "人の説明の前は置けない"
assert not loop.save_explanation(rid, "本人", "穴を切るのが大変", "下から切る")
tid, f = loop.save_template_change(["R-9999"], **args)
assert tid is None and "F8.references" in {x.floor for x in f}
tid, f = loop.save_template_change([rid], **{**args, "by": " "})
assert tid is None and "F9.human" in {x.floor for x in f}
tid, f = loop.save_template_change([rid], **{**args, "changes": []})
assert tid is None and "F7.revision" in {x.floor for x in f}
tid, f = loop.save_template_change([rid], **args)
assert tid == "T-0001" and not f
t = loop.template_changes()[0]
assert t["kind"] == "template_change" and t["record_ids"] == [rid] and t["adopted_by"] == "本人"
print("ok")
