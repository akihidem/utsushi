"""玩具ごとの記録（予想・自分の仮説・型紙の確定）が、ID の前方一致でほかの玩具に混ざらない（#147）。

なぜ: 1 コマに複数の玩具が入り、ID の末尾に枝番（…-L-3）が付いた。記録をファイル名の前方一致で数えていたので、
枝番つきの玩具に書いた予想が、枝番なしの玩具（御来迎は …-L）の予想として数えられ、予想の門（F9.prediction）が開いた。
デモで試作の玩具を先に触ると、御来迎の「予想が先」が飛ぶ。自分の仮説の番号（OWN-n）も 2 つの玩具で取り合った。
"""
import contextlib
import io
import os
import pathlib
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, loop  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
ids = sorted(p.stem for p in (ROOT / "data/hypotheses").glob("NDL-*.json"))
# 枝番つきの玩具と、名前の前方一致で当たってしまう枝番なしの ID の組。
pairs = [(sid, sid.rsplit("-", 1)[0]) for sid in ids if re.search(r"-[LR]-\d+$", sid)]
assert len(pairs) >= 39, len(pairs)
bases = sorted({b for _, b in pairs})
assert "NDL-1187053-R0000005-L" in bases, "必須の御来迎が当たる組に入っている"


def seen(sid):
    """その玩具の側に見える物: (予想の門が開いているか, 予想の数, 自分の仮説の番号, 型紙の確定の数)。"""
    return (not hypotheses.need_prediction(sid), len(hypotheses.predictions(sid)),
            [h["id"] for h in hypotheses.own_hypotheses(sid)], len(loop.sheet_confirmations(sid)))


for b in bases:
    assert seen(b) == (False, 0, [], 0), b
# 枝番つきの玩具にだけ書く。
for sid, _ in pairs:
    path, failures = hypotheses.save_prediction(sid, "首が揺れると思う")
    assert path and not failures, sid
    rec, failures = hypotheses.save_own(sid, "糸で引く", "糸を引くと首が下がる", "首の後ろの線")
    assert rec["id"] == "OWN-1" and not failures, sid
    assert not loop.confirm_sheet(sid, "H-A", 1, "試験", "試験の組"), sid
for sid, b in pairs:
    assert seen(sid) == (True, 1, ["OWN-1"], 1), (sid, seen(sid))
    assert seen(b) == (False, 0, [], 0), (b, "枝番つきの玩具の記録が、枝番なしの側に出た", sid, seen(b))
# 枝番なしの玩具に書くと、自分の側だけが開き、番号は 1 から始まる。枝番つきの側は変わらない。
for b in bases:
    path, failures = hypotheses.save_prediction(b, "扇が開くと思う")
    assert path and not failures, b
    rec, failures = hypotheses.save_own(b, "下から押す", "内筒を押すと扇が出る", "筒の下の線")
    assert rec["id"] == "OWN-1" and not failures, (b, rec["id"], "番号をほかの玩具と取り合わない")
    assert not loop.confirm_sheet(b, "H-A", 1, "試験", "試験の組"), b
    assert seen(b) == (True, 1, ["OWN-1"], 1), (b, seen(b))
for sid, _ in pairs:
    assert seen(sid) == (True, 1, ["OWN-1"], 1), (sid, seen(sid))

# 読めない記録は数えない（門は開かない）。どのファイルかを stderr に出す（#153 の読む側と同じ向き）。
lone = "NDL-0000000-R0000001-L"  # 記録が 1 つも無い ID（どの玩具でもない）
assert seen(lone) == (False, 0, [], 0), lone
broken = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "decisions" / f"prediction-{lone}-書きかけ.json"
broken.write_text('{"source_id": "' + lone + '", "text": "途中', encoding="utf-8")
err = io.StringIO()
with contextlib.redirect_stderr(err):
    assert seen(lone) == (False, 0, [], 0), "読めない予想で門を開けない"
assert broken.name in err.getvalue(), err.getvalue()
print(f"ok 枝番つき {len(pairs)} 件、枝番なし {len(bases)} 件")
