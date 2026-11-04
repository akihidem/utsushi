"""外の入口（Google フォーム）の回答の CSV を、手元の受付へ取り込む（f17、J-021）。

本人の決定（2026-11-04）: 外の入口を今日開ける。形は J-021 で決まっている: 既製のフォームで受け、本人が CSV で書き出し、
手元で今の受付と同じ検査（F10）にかけて取り込み、取り込んだ後にフォームの回答と CSV を消す。メールアドレスは集めない。
写真と動画の添付は、本人の決定（11-04、「ファイル添付はしてもよい」）で受ける。Google フォームの添付は回答者が Google に
入る必要があり、ファイルは本人の Google ドライブに入る。CSV にはファイルではなくドライブのリンクが入るので、リンクを非公開の欄に
預け、写真の決まり（権利の持ち主・人が特定できる物が無い確かめ）を当てる。ファイルは本人が確かめて手元へ移し、確かめた後に消す。
判断の芯:
- フォームの質問の題と選び肢は docs/process/contributions-form.md の表と一字一句同じにする。題で列を引くので、違えば取り込まずに止まる
- 1 行ずつ contrib.submit に渡す。検査に落ちた行は受付に入れず、行番号と理由だけを出す（本文は出さない）
- 取り込んだ後の CSV は --delete-csv で消す（J-021 の「取り込み後に消す」）。フォームの側の回答は本人が消す
"""
import argparse
import csv
import pathlib
import sys

from . import contrib

# フォームの質問の題 → 受付の欄。題は docs/process/contributions-form.md と同じ。
Q = {
    "kind": "投稿の種類",
    "role": "あなたの立場",
    "body": "本文",
    "certainty": "確かさの種類",
    "origin": "出所（情報の時）",
    "where_when": "いつ頃・どこで（思い出の時）",
    "toy_name": "玩具の名",
    "display_name": "載せる時の名前（任意）",
    "contact": "連絡先（任意・公開しません）",
    "basis": "書いた物の権利",
    "license": "公開の条件",
    "attest": "確かめ",
    "files": "ファイル添付（任意）",  # 本人のアカウントで作ったフォームの 13 番目の題（11-04、窓口が作成）
}
# 添付の欄は任意なので、古い表で作ったフォーム（この欄が無い CSV）も取り込めるようにする。
OPTIONAL = {"files"}
KIND = {"写真": "photo", "情報": "info", "思い出": "memory", "作り方の知見": "knowhow"}
ROLE = {"職人": "craftsperson", "店": "shop", "研究者": "scholar", "思い出のある人": "memory", "その他": "other"}
BASIS = {"自分で書いた": "own_work", "持ち主の許しがある": "permission", "パブリック・ドメイン": "public_domain", "分からない": "unknown"}
LICENSE = {"CC BY 4.0 で公開してよい": "CC-BY-4.0", "表示だけ（再利用は不可）": "display_only"}
ATTEST = {"規約に同意します": "agrees_terms", "18 歳以上です（または保護者の同意があります）": "adult_or_guardian",
          "人が特定できる名前や顔は書いていません": "no_identifiable_people"}


def to_contribution(row):
    """1 行をフォームの答えから受付の形にする。選び肢が表に無い時は、そのまま渡して検査に落とさせる。"""
    g = lambda k: (row.get(Q[k]) or "").strip()
    checked = {s.strip() for s in g("attest").split(",") if s.strip()} if g("attest") else set()
    links = [u.strip() for u in (row.get(Q["files"]) or "").split(",") if u.strip()]
    return {"kind": KIND.get(g("kind"), g("kind")), "role": ROLE.get(g("role"), g("role")), "body": g("body"),
            "certainty": g("certainty"), "origin": g("origin"), "where_when": g("where_when"), "toy_name": g("toy_name"),
            "display_name": g("display_name"), "contact": g("contact"),
            "rights": {"basis": BASIS.get(g("basis"), g("basis")), "license": LICENSE.get(g("license"), g("license")), "holder": g("display_name")},
            "attest": {v: (k in checked) for k, v in ATTEST.items()}, "via": "form",
            # 添付があれば写真として扱い、写真の決まりを当てる（check_rights の has_photo）。リンクは公開の記録に入れない欄に預ける。
            "_has_image": bool(links), "form_files": links}


def run(csv_path, delete_csv=False):
    """Returns (受け付けた ID の一覧, 落ちた行 [(行番号, 理由)])。題が足りない CSV は 1 行も取り込まない。"""
    p = pathlib.Path(csv_path)
    with open(p, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        header = set(rows[0].keys()) if rows else set()
    missing = [t for k, t in Q.items() if k not in OPTIONAL and t not in header] if rows else []
    if missing:
        return [], [(0, "フォームの題が表と違う: " + "、".join(missing))]
    got, bad = [], []
    for i, row in enumerate(rows, 2):  # 1 行目は題
        cid, failures = contrib.submit(to_contribution(row))
        if cid:
            got.append(cid)
        else:
            bad.append((i, "；".join(f"{x.where}: {x.message}" for x in failures)))
    if delete_csv:
        p.unlink()
    return got, bad


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.form_import", description="Google フォームの回答の CSV を手元の受付へ取り込む（J-021）")
    ap.add_argument("csv")
    ap.add_argument("--delete-csv", action="store_true", help="取り込んだ後に CSV を消す（J-021 の決まり）")
    args = ap.parse_args(argv)
    try:
        got, bad = run(args.csv, args.delete_csv)
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        print(f"検査できない: CSV を読めない（{type(e).__name__}）", file=sys.stderr)
        return 4
    for cid in got:
        print(f"受け付けた {cid}（確かめてから approve で公開）")
    for line, why in bad:
        print(f"FAIL 行 {line}: {why}", file=sys.stderr)
    print("フォームの側の回答を消してください（J-021）")
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
