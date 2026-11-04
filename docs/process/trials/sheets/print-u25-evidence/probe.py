"""凍結の条件を、変更の前後どちらのコードでも動く形（文字と配置だけ）で 1 つずつ判定する。Red/Green の証拠を取るため。"""
import json, pathlib, sys
ROOT = pathlib.Path(sys.argv[1])
from omochae import instructions as I
from omochae.templates import slider_fan, pivot_counterweight
src = lambda s: json.loads((ROOT / "data/sources" / f"{s}.json").read_text(encoding="utf-8"))
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
hyp = json.loads((ROOT / "data/hypotheses" / f"{G}.json").read_text(encoding="utf-8"))
fan = {**slider_fan.DEFAULTS, "push_part": "stick", "hub": "axle", "pusher_height": 84}
sheet, sf = I.compose_sheet("slider_fan", fan, src(G), "御来迎 版 1", "押す")
tora, tf = I.compose_sheet("pivot_counterweight", pivot_counterweight.DEFAULTS, src(T), "虎 版 1", "触れる")
flat = lambda L: "".join(t.text for t in L["texts"] if t.text)
try:
    after, af = I.compose_after(src(G), "x", hyp["after_try"], sheet_set="goraigo-v9")
except TypeError:
    after, af = I.compose_after(src(G), "x", hyp["after_try"])
comp, cf = I.compose_compare(src(G), "御来迎", hyp["hypotheses"][0], hyp["hypotheses"][1], ("A", "B"))
shapes = sheet["shapes"]
rows = [
 ("S 手順の紙が検査を通る", sf == [] and tf == []),
 ("A1 予想は動き方を言葉か絵で", "押すと、どこがどう動くと思いますか（言葉か絵で）" in flat(sheet) and "頭はどう動くと思いますか（言葉か絵で）" in flat(tora)),
 ("A2 角度・回数・分・物差しを刷らない", not any(w in flat(sheet) for w in ("（度）", "角度", "回数", "作り始めて", "10cm の物差し")) and sheet.get("ruler") is None),
 ("A3 丸の見出しが「おもちゃとして動きましたか」", "おもちゃとして動きましたか（1 つに丸）" in flat(sheet)),
 ("A4 4 つの着目の 4 問", all(q in flat(sheet) for q in ("一番おもしろかったのはどの時ですか", "どうしたら、もっと楽しくなりますか", "作っている途中で思いついた事は何ですか"))),
 ("A5 最初の一歩でつまずいた所", "最初の一歩でつまずいた所" in flat(sheet)),
 ("B 試した後の紙に納得の問い・物差し無し", "札を読んで、納得できましたか。どこが自分の考えと違いましたか" in flat(after) and after.get("ruler") is None),
 ("C 見比べる紙に角度の表が無い", "回目" not in flat(comp) and "それぞれ、どこがおもしろく動きましたか" in flat(comp)),
 ("D 先生の見る紙がある", hasattr(I, "compose_teacher")),
 ("F1 谷は塗り・山は白抜きの矢じり", {"black", "white"} <= {s.get("fill") for s in shapes if s.get("tag") == "arrowhead"}),
 ("F4 折る順（目安）3〜5 コマ", 3 <= sum(1 for s in shapes if s.get("tag") == "order_panel") <= 5 and "やりやすい順に変えてよい" in flat(sheet)),
 ("色 平らな筒を v9 の 2 色で交互に塗る", [s["fill"] for s in shapes if s.get("tag") == "tube_face"] == [slider_fan.PAPER, slider_fan.PAPER_ALT] * 2),
]
for name, ok in rows:
    print(("PASS" if ok else "FAIL"), name)
print(f"{sum(ok for _, ok in rows)}/{len(rows)} PASS")
