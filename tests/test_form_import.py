"""外の入口（Google フォーム）の CSV の取り込み（f17、J-021）。題が違えば止まり、検査に落ちた行は入れず、取り込んだ後に CSV を消せる。"""
import csv
import os
import pathlib
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import contrib, form_import  # noqa: E402

d = pathlib.Path(tempfile.mkdtemp())
head = ["タイムスタンプ"] + list(form_import.Q.values())
good = {"投稿の種類": "作り方の知見", "あなたの立場": "職人", "本文": "蛇腹は端から交互に折ると揃う。", "確かさの種類": "作っている",
        "出所（情報の時）": "", "いつ頃・どこで（思い出の時）": "", "玩具の名": "御来迎", "載せる時の名前（任意）": "紙の人",
        "連絡先（任意・公開しません）": "", "書いた物の権利": "自分で書いた", "公開の条件": "CC BY 4.0 で公開してよい",
        "確かめ": "規約に同意します, 18 歳以上です（または保護者の同意があります）, 人が特定できる名前や顔は書いていません"}
bad = dict(good, **{"確かめ": "規約に同意します"})  # 同意が足りない
f = d / "answers.csv"
with open(f, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=head)
    w.writeheader()
    w.writerow({"タイムスタンプ": "x", **good})
    w.writerow({"タイムスタンプ": "y", **bad})
got, fails = form_import.run(f)
assert len(got) == 1 and len(fails) == 1 and fails[0][0] == 3 and "同意" in fails[0][1], (got, fails)
assert (contrib.dirs()["inbox"] / f"{got[0]}.json").exists(), "受付に入った"
assert "蛇腹は" not in fails[0][1], "落ちた行の本文は出さない"
# 題が表と違えば 1 行も入れない
g = d / "wrong.csv"
g.write_text("投稿の種類,本文\n情報,x\n", encoding="utf-8")
assert form_import.run(g)[0] == [] and "題が表と違う" in form_import.run(g)[1][0][1]
# 取り込んだ後に CSV を消す
form_import.run(f, delete_csv=True)
assert not f.exists()
print("ok")
