"""手帖の記録の頁の記録の札の頭に、試した日と型紙の版を出す（統括の確かめ 11-08: #657 でつくるの頁から記録の札を外した後、写真も感想も無い記録
（御来迎の R-0001・R-0002 など）は、日付と版がサイトのどこにも出なくなった）。字は前のつくるの頁の記録の札と同じ（zukan.record_date・hypotheses.label_of）。

見る事:
1. 写真も感想も無い記録でも、手帖の記録の頁のその札の頭の 1 行に、試した日（「11 月 4 日」の形）と型紙の版（組の番号の呼び方）が出る
2. 合言葉なしの場（記録の番号を出さない場）でも、日付と版は出る（人の言葉でないので）
3. 字は前のつくるの頁の札と同じ部品で作る（一字でも違えば落ちる）
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, records  # noqa: E402
from web import techo_site, zukan  # noqa: E402

G = "NDL-1187053-R0000005-L"
GS = hypotheses.sheet_of(G)["id"]
rid, fails = records.add({"source_id": G, "hypothesis_id": GS, "sheet_version": 1, "result": records.results_for(G)[0], "tried_on": "2026-11-04"})
assert rid and not fails, fails
r = next(x for x in records.all_records(G) if x["id"] == rid)
date = zukan.record_date(r)
ban = hypotheses.label_of(r.get("sheet_set") or hypotheses.current_set(hypotheses.load(G)), r.get("sheet_version", 1))
assert date == "11 月 4 日" and ban, (date, ban)
for public in (False, True):
    page = techo_site.records_page(G, public=public)
    head = re.search(rf'<div class="item" id="{rid}">.*?<p class="meta">(.*?)</p>', page, re.S)
    assert head, (public, "札が無い")
    assert f"{date}・{ban}" in head.group(1), (public, head.group(1))
print("ok 手帖の記録の頁の札の頭に、試した日と型紙の版（写真も感想も無い記録でも・合言葉なしの場でも）")
