"""型紙エンジンが出す作り方の 3D（JSON）を読む口（決定 2026-11-07。assembly_json の注）。

見る線:
1. 書いて読み戻す: サイトの前の組の組み立て（虎 tora-v4・御来迎 goraigo-v10）を同じ形の JSON に書き、読み戻すと、頁へ渡す形
   （手順ごとの形・面のつながり）が元と同じ。読む口が、頁の今の描き方（面の木と向き付きの角）を落とさない事を、エンジンの JSON の前に見る
2. 形の照らし: JSON の部品の外形・穴・折り線・面の広さがサイトの部品と違うと、違う所を言う
3. 段の数: JSON の段が手順の文と 1 対 1 でなければ F13.assembly で落とす
4. 向き付きの角が無い JSON（angles と谷山だけ）も、棒の種類と持ち主を JSON の頭に置いた JSON も、同じ形に読む
5. assemble の口: 今の組の JSON があればそれを読み、寸法か形が違えば組み立てを出さない（None）。無ければ前の組の書き方で組む
"""
import copy
import json
import os
import pathlib
import tempfile

os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp())

from omochae import assembly, assembly_json, hypotheses, instructions
from omochae.assembly_json import Shown
from omochae.compose import TEMPLATES
from omochae.templates import pivot_counterweight, slider_fan
from web import kumitate

T, G = "NDL-1187053-R0000014-R", "NDL-1187053-R0000005-L"


def close(a, b, path="", tol=2e-3):
    """頁へ渡す形どうしが、数の丸めの差の内で同じか。違う所の道を返す（同じなら None）。"""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return f"{path}: 鍵が違う {sorted(set(a) ^ set(b))}"
        for k in a:
            got = close(a[k], b[k], f"{path}.{k}", tol)
            if got:
                return got
        return None
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return f"{path}: 長さが違う {len(a)} と {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            got = close(x, y, f"{path}[{i}]", tol)
            if got:
                return got
        return None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return None if abs(a - b) <= tol else f"{path}: {a} と {b}"
    return None if a == b else f"{path}: {a!r} と {b!r}"


def ball_at(frames):
    """粘土の玉の行列を、置き場（平行移動）だけにする。玉は向きを持たないので、JSON は置き場だけを書く（前の組の作りは、頭を揺らす時に
    粘土の丸い面も回していた）。"""
    for f in frames:
        for q in f["q"]:
            for m in [q.get("s", {}).get("clay", {}).get("m"), q.get("p", {}).get("clay:0")]:
                if m:
                    m[:12] = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]
    return frames


class at_set:
    """雛形の組を置き換えて組む（控えの組を刷る道と同じ）。"""

    def __init__(self, tpl, name):
        self.tpl, self.name = tpl, name

    def __enter__(self):
        self.keep, self.tpl.SHEET_SET = self.tpl.SHEET_SET, self.name

    def __exit__(self, *_):
        self.tpl.SHEET_SET = self.keep


def round_trip(sid, template):
    bench = assembly.assemble(sid)
    assert bench is not None and not isinstance(bench, Shown)
    p = {**TEMPLATES[template].DEFAULTS, **(hypotheses.sheet_of(sid).get("params") or {})}
    words = instructions.steps(p, template)
    doc = json.loads(json.dumps(assembly_json.dump(bench, words, {"params": p}), ensure_ascii=False))
    parts = [s.part for k, s in bench.sheets.items() if k != "clay"]
    shown = assembly_json.bench_of(doc, parts, words, bench.paper)
    return bench, doc, parts, words, shown


# 1. 書いて読み戻す（虎 tora-v4）。前の組の頁と同じ形になる
with at_set(pivot_counterweight, "tora-v4"):
    bench, doc, parts, words, shown = round_trip(T, "pivot_counterweight")
assert doc["format"] == assembly_json.FORMAT and len(doc["steps"]) == len(words) and doc["finale"]["poses"]
assert shown.failures == [], [f.line() for f in shown.failures]
assert assembly_json.same_parts(doc, parts) == [], assembly_json.same_parts(doc, parts)
miss = close(ball_at(kumitate.frames_of(shown)), ball_at(kumitate.frames_of(bench)), "frames")
assert miss is None, miss
miss = close(kumitate.trees_of(shown), kumitate.trees_of(bench), "trees")
assert miss is None, miss
for key, sheet in bench.sheets.items():  # 面の形も同じ（前の壁の四角い穴を含む）
    for i, s in enumerate(sheet.panels):
        assert s.symmetric_difference(shown.sheets[key].panels[i]).area < 1e-6, (key, i)
assert any(s.interiors for s in shown.sheets["body"].panels), "前の壁の四角い穴が面に無い"
tora_bench, tora_doc, tora_parts, tora_words = bench, doc, parts, words

# 1. 書いて読み戻す（御来迎 goraigo-v10）。最後のできあがり（扇が開く所）は頁の計算で動かすので、書き出さない段の前まで同じ
# 御来迎の今の組（goraigo-v14）は 3D で組まない（立体は 3D の枝が JSON で入れる）。3D の書き出しは控えの組 goraigo-v10 で前と同じに見る
slider_fan.SHEET_SET = slider_fan.FROZEN_SET
bench, doc, parts, words, shown = round_trip(G, "slider_fan")
assert shown.failures == [], [f.line() for f in shown.failures]
assert assembly_json.same_parts(doc, parts) == []
got, want = kumitate.frames_of(shown), kumitate.frames_of(bench)
for pose in [q for f in got + want for q in f["q"]]:
    # 御来迎の部品には中を切る所が無く、切れ端の印（plug）は頁で何もしない。前の組の作りは印を立てたままにしている
    pose.pop("plug")
miss = close(got[:len(words)], want[:len(words)], "frames")
assert miss is None, miss
assert "r" in got[8]["q"][-1] and {"row", "thread"} <= set(got[8]["q"][-1]["r"]), "糸が読めていない"
assert any(q.get("cut") for f in got for q in f["q"]) and any(q.get("ruler") for f in got for q in f["q"])

# 2. 形の照らし: 外形・穴・折り線・面の広さが違うと言う
doc, parts = tora_doc, tora_parts
bad = copy.deepcopy(doc)
body = next(jp for jp in bad["parts"] if jp["key"] == "body")
body["outline"] = [[x + 1, y] for x, y in body["outline"]]
assert any("外形が違う" in x for x in assembly_json.same_parts(bad, parts))
bad = copy.deepcopy(doc)
next(jp for jp in bad["parts"] if jp["key"] == "body")["holes"].pop()
assert any("holes が違う" in x for x in assembly_json.same_parts(bad, parts))
bad = copy.deepcopy(doc)
row = next(iter(next(jp for jp in bad["parts"] if jp["key"] == "strip")["tree"]["rows"].values()))
row["hinge"] = [[x + 3, y] for x, y in row["hinge"]]
assert any("刷る折り線" in x for x in assembly_json.same_parts(bad, parts))
bad = copy.deepcopy(doc)
next(jp for jp in bad["parts"] if jp["key"] == "drop")["panels"][0]["poly"][0][0] += 2
assert any("面を合わせた広さ" in x for x in assembly_json.same_parts(bad, parts))
bad = copy.deepcopy(doc)
bad["parts"] = [jp for jp in bad["parts"] if jp["key"] != "tail"]
assert any("tail: サイトの部品が JSON に無い" in x for x in assembly_json.same_parts(bad, parts))
# 面の中の穴を JSON が書いていなくても、サイトの部品の中を切る所を面から抜く（穴が塞がって見えない）
bad = copy.deepcopy(doc)
for jp in bad["parts"]:
    for pn in jp["panels"]:
        pn.pop("inner")
assert assembly_json.same_parts(bad, parts) == []
assert any(s.interiors for s in assembly_json.bench_of(bad, parts, tora_words).sheets["body"].panels)

# 3. 段の数が手順の文と合わなければ落とす（多くても少なくても）
for change in (lambda d: d["steps"].pop(), lambda d: d["steps"].append(copy.deepcopy(d["steps"][-1]))):
    bad = copy.deepcopy(doc)
    change(bad)
    fails = [f.line() for f in assembly_json.bench_of(bad, parts, tora_words).failures]
    assert len(fails) == 1 and "F13.assembly" in fails[0] and "1 対 1" in fails[0], fails

# 4. 向き付きの角（turns）が無く、谷山のとおりの角（angles。逆に折る所は負）だけの JSON も同じ形に読む
plain = copy.deepcopy(doc)
plates = assembly_json.bench_of(doc, parts, tora_words).sheets
for st in plain["steps"] + [plain["finale"]]:
    for got in st["poses"]:
        for key, mine in got["parts"].items():
            if "turns" not in mine:
                continue
            plate = plates[key]
            angles = {}
            for i, d in mine.pop("turns").items():
                k = plate.tree[int(i)][1]
                angles[i] = abs(d) if plate.turn(int(i), {k: abs(d)}) == d else -abs(d)
            mine["angles"] = angles
miss = close(kumitate.frames_of(assembly_json.bench_of(plain, parts, tora_words)), kumitate.frames_of(assembly_json.bench_of(doc, parts, tora_words)))
assert miss is None, miss

# 4. 棒の種類と持ち主を JSON の頭の rods に置いても、同じに読む（型紙エンジンの JSON の書き方）
top = copy.deepcopy(doc)
for st in top["steps"] + [top["finale"]]:
    for got in st["poses"]:
        for name, rod in got["rods"].items():
            top["rods"][name] = {"kind": rod.pop("kind"), "owner": rod.pop("owner")}
assert all(set(r) == {"from", "to"} for st in top["steps"] for got in st["poses"] for r in got["rods"].values()) and top["rods"]
miss = close(kumitate.frames_of(assembly_json.bench_of(top, parts, tora_words)), kumitate.frames_of(assembly_json.bench_of(doc, parts, tora_words)))
assert miss is None, miss

# 5. assemble の口: 置き場の今の組の JSON を読む。寸法か形が違えば出さない。無ければ前の組の書き方で組む
keep = assembly_json.DIR
try:
    assembly_json.DIR = pathlib.Path(tempfile.mkdtemp())
    with at_set(pivot_counterweight, "tora-v4"):
        assert not isinstance(assembly.assemble(T), Shown)  # JSON が無い
        assembly_json.path_of("tora-v4").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        got = assembly.assemble(T)
        assert isinstance(got, Shown) and got.failures == [], got
        assert close(ball_at(kumitate.frames_of(got)), ball_at(kumitate.frames_of(tora_bench))) is None
        # 頁の組み立ての節も、JSON から読んだ組み立てで組める
        html = kumitate._block_html.__wrapped__(T, "{}")
        assert html.count('class="rt-p"') == 2 * sum(len(s.panels) for s in got.sheets.values()) and 'id="rt-knife"' in html
        bad = copy.deepcopy(doc)
        bad["params"]["body_length"] += 1
        assembly_json.path_of("tora-v4").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        assert assembly.assemble(T) is None  # 別の寸法の紙の JSON
        bad = copy.deepcopy(doc)
        next(jp for jp in bad["parts"] if jp["key"] == "body")["holes"].pop()
        assembly_json.path_of("tora-v4").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        assert assembly.assemble(T) is None  # 刷る紙と形が違う JSON
        assembly_json.path_of("tora-v4").write_text(json.dumps({**doc, "format": "x/0"}, ensure_ascii=False), encoding="utf-8")
        try:
            assembly.assemble(T)
            raise AssertionError("形の名の違う JSON を読んだ")
        except ValueError as e:
            assert "omochae-assembly-3d/1" in str(e)
    # 御来迎の今の組には JSON が無いので、前の組の書き方で組む（置き場が空の間、頁は変わらない）
    assert not isinstance(assembly.assemble(G), Shown) and assembly.assemble(G) is not None
finally:
    assembly_json.DIR = keep
assert not assembly_json.path_of(slider_fan.SHEET_SET).exists()
print("ok 作り方の 3D の JSON を読む口。書いて読み戻すと同じ・形の照らし・段の数・角の向き・assemble の口")
