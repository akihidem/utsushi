"""再取り込みで人が書いた欄を消さない（レビュー指摘）。通信はしない（偽の manifest を渡す）。

なぜ: crop_status や original_publication.checked_by は人が確かめた記録。取り込みで unverified／None に戻ると、確かめた履歴が消える。
ただし確かめた対象（切り出しの箱・奥付の読み）が変わった時は、古い確認を新しい値に付け替えない。
"""
import json
import pathlib
import tempfile

from omochae import ingest

manifest = {
    "metadata": [{"label": k, "value": v} for k, v in {
        "Persistent ID": "info:ndljp/pid/1187053", "DOI": "10.11501/1187053", "Title": "江都二色", "Creator": "c", "Publisher": "米山堂",
        "Publication Date (W3CDTF fortmat)": "1931", "Access Restrictions": "PDM"}.items()],
    "license": "L", "attribution": "A",
    "sequences": [{"canvases": [{"images": [{"resource": {"service": {"@id": f"https://x/{i}"}}}]} for i in range(1, 40)]}],
}
ingest._get = lambda url: json.dumps(manifest).encode() if url == ingest.MANIFEST else b"jpg"


def run(root):
    ingest.ROOT = root
    assert ingest.main() == 0


root = pathlib.Path(tempfile.mkdtemp())
run(root)
sid, other = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
path = root / "data/sources" / f"{sid}.json"
rec = json.loads(path.read_text(encoding="utf-8"))
before = rec["fetched_at"]
rec["crop_status"] = "checked"
rec["original_publication"]["checked_by"] = "本人"
rec["transcription"] = {"status": "done", "entries": [{"text": "う"}]}
path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
# 箱を人が確かめた後で、コードの側の箱が変わった場合（もう片方の出典で見る）
o = root / "data/sources" / f"{other}.json"
orec = json.loads(o.read_text(encoding="utf-8"))
orec.update(crop_status="checked", crop_region="pct:40,0,60,100")
orec["original_publication"].update(checked_by="本人", value="別の読み")
o.write_text(json.dumps(orec, ensure_ascii=False), encoding="utf-8")

run(root)
after = json.loads(path.read_text(encoding="utf-8"))
assert after["crop_status"] == "checked", after["crop_status"]
assert after["original_publication"]["checked_by"] == "本人", after["original_publication"]
assert after["transcription"]["entries"] == [{"text": "う"}]
assert after["fetched_at"] == before, "人の欄を残しただけで取得日時を動かさない"
oafter = json.loads(o.read_text(encoding="utf-8"))
assert oafter["crop_status"] == "unverified", "箱が変われば確認はやり直し"
assert oafter["original_publication"]["checked_by"] is None, "読みが変われば確認はやり直し"
assert set(ingest.HUMAN_FIELDS) >= {"transcription", "reading_hypothesis", "crop_status", "original_publication.checked_by"}
print("ok")
