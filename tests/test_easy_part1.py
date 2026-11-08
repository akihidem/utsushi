"""やさしい日本語の表の分け 1（data/i18n/yasashii.d/1.json）の書き方の決めを見る（11-07 夜・本人の言葉「このモードはルビつけて
やさしい日本語に全体の文が変換されるモード」）。

なぜ要るか: 土台の test_easy_all は、頁が開く事とルビの印の形を見るが、漢字にルビが付いているか（漢字は全部ルビ）・読みの字・
玩具の名を替えていないかは見ない。3 つの窓が同じ決めで書くので、分け 1 の決めを機械で残す（後で直す人が崩さないため）。

見る事:
1. 分け 1 の表が在り、形は {"note", "strings"}・鍵は字の順
2. 値の漢字は全部ルビの中（｜漢字《よみ》）。ルビの元は漢字だけ、読みはひらがなだけ
3. 値の数の印（{0}{1}…）は鍵と同じ
4. 値が "=" の物は、英語の表でも "=" の物（人の記録・感想は替えない）
5. 玩具の名（仮説の記録の toy）がそのまま鍵の物は、ルビを外すと一字も同じ（玩具の名は替えない・ルビだけ）
6. 入口の題字と副題の 3 行は、字を足さず言い換えず、ルビだけ（サイトの担当の頼み: 入口の題字と副題は日本語の頁と同じ字にルビだけ）
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PART = ROOT / "data/i18n/yasashii.d/1.json"
KANJI = re.compile(r"[㐀-䶿一-鿿豈-﫿々〆ヶ]")
RUBY = re.compile(r"｜([^｜《》]+)《([^｜《》]+)》")
PH = re.compile(r"\{\d+\}")

# 1. 形
assert PART.exists(), "分け 1 の表が無い"
table = json.loads(PART.read_text(encoding="utf-8"))
assert set(table) == {"note", "strings"} and table["strings"], list(table)
strings = table["strings"]
assert list(strings) == sorted(strings), "鍵は字の順に並べる（3 つの窓のファイルと英語の表と同じ）"
en = json.loads((ROOT / "data/i18n/en.json").read_text(encoding="utf-8"))["strings"]

bad = []
for k, v in strings.items():
    if v == "=":
        # 4. 替えない字は、英語でも替えない物だけ
        if en.get(k) != "=":
            bad.append(("= は英語でも = の物だけ", k))
        continue
    # 2. ルビ
    for m in RUBY.finditer(v):
        if not re.fullmatch(r"[㐀-䶿一-鿿豈-﫿々〆ヶ]+", m.group(1)):
            bad.append(("ルビの元が漢字だけでない", k))
        if not re.fullmatch(r"[ぁ-ゖー]+", m.group(2)):
            bad.append(("読みがひらがなだけでない", k))
    if KANJI.search(RUBY.sub("", v)):
        bad.append(("ルビの無い漢字", k))
    # 3. 数の印
    if sorted(PH.findall(k)) != sorted(PH.findall(v)):
        bad.append(("数の印が鍵と違う", k))
assert not bad, bad[:10]

# 5. 玩具の名
names = set()
for f in (ROOT / "data/hypotheses").glob("*.json"):
    toy = json.loads(f.read_text(encoding="utf-8")).get("toy")
    if isinstance(toy, str) and toy:
        names.add(toy)
renamed = [k for k in strings if k in names and strings[k] != "=" and RUBY.sub(lambda m: m.group(1), strings[k]) != k]
assert names and not renamed, renamed
# 6. 入口の題字と副題の 3 行は、ルビを外すと鍵と一字も同じ
TITLE = ("江都二色より", "うしなわれた玩具の動きを", "紙でよみがえらせる")  # 3 行目は本人の答え 11-08
changed = [k for k in TITLE if k not in strings or RUBY.sub(lambda m: m.group(1), strings[k]) != k]
assert not changed, ("入口の題字と副題は、ルビだけを振る（字を足さない・言い換えない）", changed)
print(f"ok やさしい日本語の表の分け 1（{len(strings)} 鍵・漢字は全部ルビ・読みはひらがな・数の印・= の扱い・玩具の名と入口の題字は替えない）")
