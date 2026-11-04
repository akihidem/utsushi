"""NDL の IIIF manifest から出典の記録と元の図を作る。

なぜ manifest を毎回読むか: 権利と書誌を手で写すと、写し間違いが型紙の印に刷られる。一次資料の値をそのまま運ぶ。
なぜ取得日時を内容が変わった時だけ更新するか: 何度走らせても git の差分が出ないようにするため。
"""
import json
import pathlib
import sys
import urllib.request

MANIFEST = "https://dl.ndl.go.jp/api/iiif/1187053/manifest.json"
ROOT = pathlib.Path(__file__).resolve().parents[2]
# 左右の切り分けは頁の境目で分ける。画像を見て境目が中央付近だと確かめた（docs/process/research/01）。
# 画素の箱として正確かは原画を型紙に入れる時に人が確かめるので、それまで unverified と記録する。
TARGETS = {
    "NDL-1187053-R0000005-L": {"toy": "御来迎", "canvas": 5, "side": "L", "region": "pct:0,0,50,100"},
    "NDL-1187053-R0000014-R": {"toy": "張子の首振り虎", "canvas": 14, "side": "R", "region": "pct:50,0,50,100"},
}


# 人が書く・確かめる欄。再取り込みで消さない（レビュー指摘: 前は翻刻と読みだけで、crop_status と奥付の確認者が戻っていた）。
# 「.」は入れ子の欄。欄を足す時はここに足し、tests/test_ingest_keep.py で確かめる。
HUMAN_FIELDS = ("transcription", "reading_hypothesis", "crop_status", "original_publication.checked_by")
# 確認の欄は、確かめた対象が同じ時だけ残す。切り出しの箱や奥付の読みがコードの側で変わったら、古い確認を新しい値に付け替えない。
CHECKED_AGAINST = {"crop_status": "crop_region", "original_publication.checked_by": "original_publication.value"}


def _dig(rec, dotted):
    *head, last = dotted.split(".")
    for k in head:
        rec = rec.get(k) if isinstance(rec, dict) else None
    return rec, last


def keep_human_fields(old, rec):
    """旧い記録の人の欄を新しい記録へ移す。rec を書き換える。"""
    for name in HUMAN_FIELDS:
        src, key = _dig(old, name)
        dst, _ = _dig(rec, name)
        if not isinstance(src, dict) or key not in src or not isinstance(dst, dict):
            continue
        target = CHECKED_AGAINST.get(name)
        if target:
            (a, ka), (b, kb) = _dig(old, target), _dig(rec, target)
            if not (isinstance(a, dict) and isinstance(b, dict) and a.get(ka) == b.get(kb)):
                continue
        dst[key] = src[key]


def _get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def inventory_targets():
    """全部の玩具を作る線（本人の指示、11-04）の分。棚卸し（data/inventory/edo-nishiki.json）のうち、仮説の記録を置いた玩具だけを取り込む。
    線が共有の TARGETS を書き足してぶつからないため、置いた仮説の記録の有無で決める。名前は棚卸しの見立てのまま（確かめ待ち）。"""
    inv = ROOT / "data/inventory/edo-nishiki.json"
    if not inv.exists():
        return {}
    out = {}
    for t in json.loads(inv.read_text(encoding="utf-8"))["toys"]:
        if t["id"] in TARGETS or not (ROOT / "data/hypotheses" / f"{t['id']}.json").exists():
            continue
        out[t["id"]] = {"toy": t["name_guess"], "canvas": t["frame"], "side": t["side"], "region": t["region"]}
    return out


def main():
    try:
        manifest = json.loads(_get(MANIFEST))
    except Exception as e:  # 通信の失敗は検査の失敗ではないので 4
        print(f"ingest: manifest を取れない: {e}", file=sys.stderr)
        return 4
    meta = {m["label"]: m["value"] for m in manifest["metadata"]}
    canvases = manifest["sequences"][0]["canvases"]
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
    (ROOT / "data/sources").mkdir(parents=True, exist_ok=True)
    (ROOT / "out/sources").mkdir(parents=True, exist_ok=True)
    for sid, t in {**TARGETS, **inventory_targets()}.items():
        c = canvases[t["canvas"] - 1]
        service = c["images"][0]["resource"]["service"]["@id"]
        image_url = f"{service}/{t['region']}/1600,/0/default.jpg"
        rec = {
            "source_id": sid,
            "toy": t["toy"],
            "persistent_id": meta["Persistent ID"],
            "doi": meta["DOI"],
            "title": meta["Title"],
            "creator_as_cataloged": meta["Creator"],
            "publisher": meta["Publisher"],
            "publication": meta["Publication Date (W3CDTF fortmat)"],
            "canvas": t["canvas"],
            "side": t["side"],
            "crop_region": t["region"],
            "crop_status": "unverified",
            "image_url": image_url,
            "holding": f"国立国会図書館デジタルコレクション {meta['Persistent ID']}（{meta['Publisher']}・{meta['Publication Date (W3CDTF fortmat)']} 年の複製）",
            "rights": meta["Access Restrictions"],
            "license_url": manifest["license"],
            "attribution": manifest["attribution"],
            # 奥付はコマ 31 の複製の版面にある。manifest には無いので、読んだ箇所を記録する（research/07）。
            "original_publication": {"value": "安永二歳癸巳正月（1773）", "basis": "NDL コマ 31 の左頁の奥付", "read_by": "Claude Code のセッション", "checked_by": None},
            "modification_note": "改変: 図を参照して寸法と形を起こし、色と線を描き直した翻案で、原図そのものではありません",
            # 翻刻は人が写す欄。読みが割れる事があるので複数を持てる形にする。
            "transcription": {"status": "pending", "entries": []},
            "reading_hypothesis": {"status": "pending", "entries": []},
        }
        path = ROOT / "data/sources" / f"{sid}.json"
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            old_time = old.pop("fetched_at", now)
            keep_human_fields(old, rec)
            # 奥付の文はコードの側で直す物で、取得した値ではない。文を直しても、それだけで取得日時を動かさない。
            # 前は比べる前に旧い記録の奥付を新しい物で上書きしていたので、人の確認の消失も差分として見えなかった（レビュー指摘）。
            strip = lambda r: {k: v for k, v in r.items() if k != "original_publication"}
            rec["fetched_at"] = old_time if strip(old) == strip(rec) else now
        else:
            rec["fetched_at"] = now
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        img = ROOT / "out/sources" / f"{sid}.jpg"
        if not img.exists():
            try:
                img.write_bytes(_get(image_url))
            except Exception as e:
                print(f"ingest: 画像を取れない {sid}: {e}", file=sys.stderr)
                return 4
        print(f"ingest: {sid} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
