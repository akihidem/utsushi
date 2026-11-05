"""仮説の札の足と頁の足を、別の名前で持つ事を見る（#124）。

なぜ: 札の足が頁の足と同じ .foot だと、頁の足の余白・中央寄せ・上の罫が札に掛かり、釦が 2 行に折れた。
測った大きさはブラウザが要るので、ここでは名前の分かれ方だけを見る（測った値は gate-evidence/green-plate-acts.txt）。
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import skin, toy  # noqa: E402

SID = "NDL-1187053-R0000005-L"
for look in skin.SKINS:
    html = toy.toy_page(SID, look)
    plates = html[html.index('<div class="plates">'):html.index('id="win"')]
    n = plates.count('class="plate"')
    assert n >= 2, look
    assert plates.count('<div class="acts">') == n, (look, n)
    assert 'class="foot"' not in plates, look
    assert len(re.findall(r'<p class="foot">', html)) == 1, look  # 頁の足は 1 つのまま
assert ".plate .acts{" in skin.BASE and ".plate .foot" not in skin.BASE
# 頁の足の決まりは変えていない（札の直しで頁の足の見た目を変えない）。字の 12px は字の大きさの床（#137）
assert ".foot{padding:48px 5vw 40px;font-size:12px;color:var(--mute);letter-spacing:.1em;text-align:center;border-top:1px solid var(--rule)}" in skin.BASE
print("ok")
