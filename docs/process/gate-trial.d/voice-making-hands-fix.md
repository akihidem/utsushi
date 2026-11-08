## 「つくっている様子」の手元の写真の線をそろえる（声の担当、voice/making-hands-fix、11-08 午後）

- 目的: #666 の確かめの止め（別の目）と統括の決め（11-08）。#666 で残した 20 枚のうち、20261104/p03（灰の上着の胴と黒い髪）・20261106/p02（黒い上着の胴と膝）は体が大きく写る。20261104/p05（袖と左下の膝）は、外した 20261104/p02 と同じ形。逆に外した 20261106/p24 は、ほぼ手元（靴の先と袖だけ）
- どうしたか: data/workshop_photo_kinds.json で、20261104/p03・20261106/p02・20261104/p05 を body（why つき）に、20261106/p24 を making に戻した。つくっている様子 は 18 枚、body は 11 枚。tests/test_mochiyoru_workshop.py に、人が決めた body の 11 枚と表が合う事の見張りを足した（決めを変えずに戻さない・外さない）
- 検証ゲート: **済み**。Red: 今の main（9cd182a3）の木で rc 1（4 枚が合わない。`docs/process/gate-evidence/red-making-hands-fix.txt`）。Green: rc 0（`green-making-hands-fix.txt`）
- エビデンスゲート: 関わる試験 5 本（test_workshop_gallery・test_workshop_photos・test_mochiyoru_toy_place・test_ledger・test_gate_evidence）が rc 0
- マージ後の書き戻し: Issue は立てていない
