"""御来迎の次の組 goraigo-v14（examples/goraigo_v14.json）。制作者の言葉（2026-11-06）「御来迎、4扇は今の倍の長さにして欲しい。」と
「内筒が外筒よりもふた回りくらい小さいのでスカスカ。抵抗があった方がいい。」による。

v13 の見本から変えたのは 6 つの寸法だけ（扇はまるごと倍・押し上げる量・外筒の高さ・内筒と台）。次を見る:
1. v14 は v13 から 6 つの寸法だけが違い、検査（床）を全部通る。必須の紙（omochae.sheets の REQUIRED）は v14 で刷る。
2. 扇: 開く角の見込みは v13 と同じ 176°（帯も高さも倍）。帯だけを倍にした寸法は口の角に当たり（F5.fan_clearance）、高さだけを倍に
   した寸法は v13 の押し上げる量では静かな時に口から出る（F5.fan_height）。後者は v14 の押し上げる量なら通るが、88° しか開かない。
3. 内筒: 隙間は片側 0.75mm（v13 は 2mm）。床の境（外筒 − 1）の 25 は落ち、24.9 は通る。台は内筒の口に差し込める大きさ。
4. 3D（python -m omochae.fold3d）: 外筒と内筒が閉じ、内筒が外筒に入り（隙間 0.75mm）、静かな時に扇と像が口の下に隠れる。
5. 置き方: 扇の右の列が左の列より下まで来るので、文字は左の列の内筒の下から、右の段（台・像・受け）の左までの幅で刷る。
   右の段が左の列より上で終わる v13 は、前と同じ所から刷る（v13 の紙が 1 バイトも変わらない事は、刷り比べで別に見た）。
紙の厚み・たわみ・摩擦は入れていない。内筒の「抵抗」の強さは、刷った紙で確かめる。
"""
import json
import os
import pathlib
import subprocess
import sys

from omochae import sheets
from omochae.__main__ import load_source
from omochae.compose import GAP, compose
from omochae.templates import slider_fan as sf

ROOT = pathlib.Path(__file__).resolve().parents[1]
ex = {n: json.loads((ROOT / f"examples/{n}.json").read_text(encoding="utf-8")) for n in ("goraigo_v13", "goraigo_v14")}
v13, v14 = (dict(sf.DEFAULTS, **ex[n]["params"]) for n in ("goraigo_v13", "goraigo_v14"))
src = load_source(ex["goraigo_v14"]["source_id"])


def floors(base, **kw):
    return [f.floor for f in compose("slider_fan", {**base, **kw}, src)[2]]


# 1. v13 から 6 つの寸法だけ。検査を全部通り、必須の紙は v14
assert {k for k in v14 if v14[k] != v13[k]} == {"tube_height", "push_amount", "fold_count", "fold_height", "pusher_side", "base_side"}
assert ex["goraigo_v14"]["source_id"] == ex["goraigo_v13"]["source_id"] and v14["push_part"] == sf.RISE
assert sf.check_range(v14) == [] and floors(v14) == [], floors(v14)
assert sheets.REQUIRED["slider_fan"] == "examples/goraigo_v14.json"

# 2. 扇はまるごと倍（板の幅は同じ）で、開く角は v13 と同じ
n13, n14 = (int(q["fold_count"]) for q in (v13, v14))
assert n14 == 2 * n13 and v14["fold_height"] == 2 * v13["fold_height"] and v14["fold_width"] == v13["fold_width"]
deg = lambda q: sf.opening_bound_deg(int(q["fold_count"]), q["fold_width"], q["fold_height"])
assert abs(deg(v14) - deg(v13)) < 1e-9 and 175 < deg(v14) < 178, deg(v14)
assert "F5.fan_clearance" in floors(v13, fold_count=n14)            # 帯だけを倍: 353° 開こうとして口の角に当たる
assert "F5.fan_height" in floors(v13, fold_height=v14["fold_height"])  # 高さだけを倍: v13 の押し上げる量では静かな時に口から出る
assert floors(v14, fold_count=n13) == [] and 87 < deg(dict(v14, fold_count=n13)) < 89  # v14 の行程なら通るが 88° しか開かない

# 3. 内筒の隙間（片側）は 2mm → 0.75mm。床の境は外筒 − 1
A, a, b, t = v14["tube_side"], v14["pusher_side"], v14["base_side"], v14["paper_thickness"]
assert (A - a) / 2 == 0.75 and (v13["tube_side"] - v13["pusher_side"]) / 2 == 2
assert floors(v14, pusher_side=25, base_side=24.5) == ["F5.slide_clearance"]
assert floors(v14, pusher_side=24.9, base_side=24.4) == []
assert a - 1 <= b <= a - 2 * t

# 4. 3D: 筒が閉じ、内筒が外筒に入り、静かな時に扇と像が口の下に隠れる
env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
r = subprocess.run([sys.executable, "-m", "omochae.fold3d", "--scenario", str(ROOT / "examples/goraigo_v14.json")], cwd=ROOT, env=env,
                   capture_output=True, text=True)
assert r.returncode == 0, r.stdout + r.stderr
assert "断面のすき間 0.75mm" in r.stdout and "扇と像は口の 2.6mm 下に隠れ" in r.stdout and "内筒は外筒に 57.5mm 入る" in r.stdout, r.stdout


# 5. 置き方
def layout(q):
    _, page, fails = compose("slider_fan", q, src)
    assert not fails, [f.line() for f in fails]
    by = {x.key: x for x in page["parts"]}
    body = [tb for tb in page["texts"] if tb.owner is None and tb.y > by["tube"].y]  # 部品の札と見出しの外の文字（用意する物と凡例）
    return by, body


by, body = layout(v14)
fan, pusher, base = by["fan"], by["pusher"], by["base"]
row = max(by[k].y + by[k].height for k in ("base", "figure", "cradle"))
assert base.y >= fan.y + fan.height and row > pusher.y + pusher.height  # 右の列（扇と、その下の段）が、左の列（外筒と内筒）より下まで来る
assert body and min(tb.y for tb in body) >= pusher.y + pusher.height  # 文字は内筒の下から
assert max(tb.x + tb.w for tb in body) <= base.x - GAP + 1e-6  # 右の段（台・像・受け）の左まで
by13, body13 = layout(v13)
row13 = max(by13[k].y + by13[k].height for k in ("base", "figure", "cradle"))
assert row13 <= by13["pusher"].y + by13["pusher"].height  # v13 は右の段が左の列より上で終わる（前の置き方のまま）
assert min(tb.y for tb in body13) >= by13["pusher"].y + by13["pusher"].height
print("ok 御来迎 v14（扇はまるごと倍・内筒の隙間 0.75mm・置き方）")
