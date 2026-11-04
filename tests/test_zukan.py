"""図鑑の頁の試験（J-016、f15）。印の無い文を出さない・予想が先・採らなかった読みを出さない・引用は確かめた読みだけ、を見る。

本物の記録や予想を汚さないよう、OMOCHAE_DATA を空の一時の置き場にしてから読み込む。
"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, labels, records  # noqa: E402
from web import zukan  # noqa: E402
from web.play_server import serve, source, sources  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
base = f"http://127.0.0.1:{server.server_address[1]}"
threading.Thread(target=server.serve_forever, daemon=True).start()


def get(path):
    try:
        r = urllib.request.urlopen(base + path)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def sentences(body):
    """画面に出た文（li と歌）を取り出す。文の数え方を画面の組みに合わせ、印の有無を外から確かめるため。"""
    return re.findall(r"<li>(.*?)</li>", body)


def hypothesis_words(sid):
    data = hypotheses.load(sid)
    return [w for h in data["hypotheses"] for w in (h["name"], h["how_it_moves"])]


# 予想の前: 頁は開き、仮説の名前と動かし方は出ない。仮説の代わりに予想へのリンクだけ
code, idx = get("/zukan")
assert code == 200 and "図鑑" in idx
for sid in sources():
    assert f'href="/zukan/{sid}"' in idx and f'href="/toy/{sid}"' in idx and f'href="/toy/{sid}/techo"' in idx
    code, body = get(f"/zukan/{sid}")
    assert code == 200, sid
    assert "予想を書くと仮説が見られる" in body and f'href="/toy/{sid}"' in body
    for w in hypothesis_words(sid):
        assert w not in body and w not in idx, w
assert 'href="/gallery"' in idx
assert get("/zukan/NDL-0-R0000001-L")[0] == 404

# 採らなかった読み「怠らし」はどこにも出ない。引用は人が確かめた読みだけ
for sid in sources():
    src = source(sid)
    body = get(f"/zukan/{sid}")[1]
    for e in src["transcription"]["entries"]:
        if e.get("checked_by") and not e.get("rejected_by"):
            assert e["text"] in body, e["text"]
        else:
            assert e["text"] not in body, e["text"]
assert "怠らし" not in idx and "怠らし" not in get(f"/zukan/{G}")[1]
# 確かめていない読み・採らなかった読みは引用の候補から外れる（頁ごと落とさないため、ここで絞る）
fake = {"transcription": {"entries": [{"text": "確かめた", "checked_by": "人", "read_by": "Claude"}, {"text": "未確認", "read_by": "Claude"},
                                      {"text": "採らない", "checked_by": "人", "rejected_by": "人"}]}}
assert [q["text"] for q in zukan.quote_lines(fake)] == ["確かめた"]
assert all(q["label"] == labels.QUOTE for q in zukan.quote_lines(fake))

# 記録と予想の後: 観察の文が増え、仮説の名前が出る
rid, fail = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "わからない", "tried_on": "2026-11-04"})
assert not fail
hypotheses.save_prediction(G, "つまみを上げると開く")
body = get(f"/zukan/{G}")[1]
assert f"{rid} 仮説 A の紙: わからない（試した日 2026-11-04）" in body
assert "予想を書くと仮説が見られる" not in body
for w in hypothesis_words(G):
    assert w in body, w
# 予想は玩具ごと。もう 1 つの玩具の仮説はまだ隠れたまま
other = next(s for s in sources() if s != G)
assert all(w not in get(f"/zukan/{other}")[1] for w in hypothesis_words(other))

# 出た文はどれも 3 分類の印を持ち、組み立てた文の一覧は F6.label を通る
for sid in sources():
    body = get(f"/zukan/{sid}")[1]
    li = sentences(body)
    assert li or sid != G, sid  # もう 1 つの玩具は記録も予想も無く、文は歌だけ
    for s in li:
        assert re.match(rf'<span class="lb">({"|".join(labels.LABELS)})</span>', s), s
    # 歌の直後には引用の印がある
    assert body.count('<p class="song">') == len(re.findall(rf'class="song">[^<]*</p><p class="meta"><span class="lb">{labels.QUOTE}</span>', body))
    z = zukan.lines_for(sid)
    assert not labels.check(z["quotes"] + z["observations"] + z["hypotheses"]), sid

# 印の無い文が混ざれば描かない（公開の前の床）。画面は 500 で、文は出ない
for bad in ([{"text": "印の無い文"}], [{"text": "飾り", "label": "演出"}], [{"text": "裏付けの無い引用", "label": labels.QUOTE}]):
    try:
        zukan.guard(bad)
        raise AssertionError(bad)
    except zukan.Unlabeled:
        pass
orig = zukan.observation_lines
zukan.observation_lines = lambda sid, data: [{"text": "印の無い文"}]
try:
    code, body = get(f"/zukan/{G}")
    assert code == 500 and "印の無い文" not in body
    assert get("/zukan")[0] == 500
finally:
    zukan.observation_lines = orig
assert get(f"/zukan/{G}")[0] == 200

# 順位を付けない（J-025）
for word in ("順位", "1 位", "成功", "失敗", "再現できた"):
    assert word not in get("/zukan")[1], word
server.shutdown()
print("ok")
