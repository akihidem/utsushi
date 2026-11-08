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
    # 仮説の札は仮説の段にある。札の並びから、仮説の段の終わり（次の段 たとえ の頭）まで。前は考えを話す節の頭までだったが、
    # 考えを話す は外した（本人の言葉 11-08「つくるの「考えを話す」は無くす。」）
    plates = html[html.index('<div class="plates">'):html.index('id="tatoe"')]
    n = plates.count('class="plate"')
    assert n == 1, look  # 札はたたき台の 1 枚だけ（J-032）
    # 札の足（acts）にあった「型紙を見る」は外した（刷る口は頭の「つくる」1 つ。本人のサイト体験レビュー 11-07 の 3）。札は仮説の字だけで、足を持たない
    assert plates.count('<div class="acts">') == 0 and "型紙を見る" not in plates, (look, n)
    assert 'class="foot"' not in plates, look
    assert len(re.findall(r'<p class="foot">', html)) == 1, look  # 頁の足は 1 つのまま
assert ".plate .acts{" in skin.BASE and ".plate .foot" not in skin.BASE
# 札が 1 枚だけの頁は、狭い 1 列に残さない（題が折れ、右が空く。撮った画面で見つけた）。一覧で札が並ぶ頁には効かない形にする
assert ".plates>.plate:only-child{grid-column:1/-1;" in skin.BASE
# 頁の足の決まりは変えていない（札の直しで頁の足の見た目を変えない）。字の 12px は字の大きさの床（#137）
assert ".foot{padding:48px 5vw 40px;font-size:12px;color:var(--mute);letter-spacing:.1em;text-align:center;border-top:1px solid var(--rule)}" in skin.BASE
print("ok")
