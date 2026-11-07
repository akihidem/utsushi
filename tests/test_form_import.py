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
# 添付（本人の決定 11-04「ファイル添付はしてもよい」）: リンクは公開の記録に入らない預かりの所に置き、写真の決まりを当てる
import json  # noqa: E402

photo = dict(good, **{"投稿の種類": "写真", "ファイル添付（任意）": "https://drive.google.com/open?id=abc"})
nohold = dict(photo, **{"載せる時の名前（任意）": ""})  # 写真なのに権利の持ち主が無い
f2 = d / "photo.csv"
with open(f2, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=head + ["ファイル添付（任意）"])
    w.writeheader()
    w.writerow({"タイムスタンプ": "z", **photo})
    w.writerow({"タイムスタンプ": "w", **nohold})
got2, fails2 = form_import.run(f2)
assert len(got2) == 1 and fails2[0][0] == 3 and "持ち主" in fails2[0][1], (got2, fails2)
rec = json.loads((contrib.dirs()["inbox"] / f"{got2[0]}.json").read_text(encoding="utf-8"))
assert "drive.google" not in json.dumps(rec), "リンクは公開の記録に入れない"
assert "drive.google" in (contrib.dirs()["inbox"] / f"{got2[0]}.private").read_text(encoding="utf-8")
assert "drive.google" not in json.dumps(contrib.public_record({**rec, "status": "published"}))
# 題が表と違えば 1 行も入れない
g = d / "wrong.csv"
g.write_text("投稿の種類,本文\n情報,x\n", encoding="utf-8")
assert form_import.run(g)[0] == [] and "題が表と違う" in form_import.run(g)[1][0][1]
# 取り込んだ後に CSV を消す
form_import.run(f, delete_csv=True)
assert not f.exists()
# サイトの頁から作ったフォームへつなぐ（本人の指示 11-04）
from omochae.form_import import FORM_URL  # noqa: E402
from web.contrib_server import public_page  # noqa: E402
from web.techo_site import gallery_page, voices_sections  # noqa: E402

# 持ち寄りの入口（フォーム）は職人の言葉の節の中にあり、節ごと もちよるの頁へ移した（本人の言葉 11-08「職人の言葉、はもちよるに移動」。前は序の頁の足）
assert FORM_URL.startswith("https://docs.google.com/forms/") and FORM_URL in gallery_page([]) and FORM_URL in public_page()
assert FORM_URL not in voices_sections(), "序の頁に持ち寄りの入口が残る"
print("ok")
