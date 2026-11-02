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


def _get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


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
    for sid, t in TARGETS.items():
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
            "modification_note": "改変: 図をもとに寸法と形を起こした翻案で、原図そのものではありません",
            # 翻刻は人が写す欄。読みが割れる事があるので複数を持てる形にする。
            "transcription": {"status": "pending", "entries": []},
            "reading_hypothesis": {"status": "pending", "entries": []},
        }
        path = ROOT / "data/sources" / f"{sid}.json"
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            old_time = old.pop("fetched_at", now)
            # 人が入れた翻刻と読みは取り込みで消さない。
            rec["transcription"] = old.get("transcription", rec["transcription"])
            rec["reading_hypothesis"] = old.get("reading_hypothesis", rec["reading_hypothesis"])
            old["original_publication"] = rec["original_publication"]  # 文を直しても、それだけで取得日時を動かさない
            rec["fetched_at"] = old_time if old == rec else now
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
