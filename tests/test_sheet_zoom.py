"""型紙の拡大は SVG を主に、大きさを 3 段で変えられ、Esc と絵の外で閉じる（#128。要件 S-01・S-02）。

なぜ: 拡大は PNG を CSS で引き伸ばすだけで、物差しの目盛りと字がにじんでいた。閉じる道も右上の小さな字 1 つだった。
"""
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    try:
        x = urllib.request.urlopen(base + path)
        return x.status, x.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    return urllib.request.urlopen(r).status


def zoom_of(page):
    return page.split('id="zoom"', 1)[1].split("</div></div>", 1)[0]


assert post(f"/toy/{G}/predict", {"text": "筒を押すと扇が開く"}) in (200, 303)
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"}) in (200, 303)
page = get(f"/toy/{G}?see=H-A")[1]
z = zoom_of(page)
# 窓の小さな絵は PNG のまま。拡大だけ SVG にする（窓は軽く、拡大はにじまない）
assert f'<img src="/sheet/{G}/H-A_v1.png"' in page.split('id="zoom"', 1)[0]
assert f'<img src="/sheet/{G}/H-A_v1.svg"' in z, z[:300]
# 大きさは 3 段。JS なしで切り替わる
for n in (100, 180, 300):
    assert f'id="zs{n}"' in z and f'<label for="zs{n}">{n}%</label>' in z, n
assert z.count("checked") == 1 and 'id="zs180" checked' in z
# Esc と絵の外で閉じる。JS が無くても閉じる字のリンクは効く
assert 'class="close" href="#win"' in z and "'Escape'" in page and "history.back()" in page
# SVG が無い紙は PNG に戻る
svg = out_dir(G) / "H-A_v1.svg"
kept = svg.read_bytes()
svg.unlink()
assert f'<img src="/sheet/{G}/H-A_v1.png"' in zoom_of(get(f"/toy/{G}?see=H-A")[1])
svg.write_bytes(kept)
# 試した後の紙の門は SVG でも同じ
assert get(f"/sheet/{G}/H-A_v1_after.svg")[0] == 403
assert "H-A_v1_after.svg" not in get(f"/toy/{G}?see=H-A&kind=after")[1]
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた"}) in (200, 303)
assert get(f"/sheet/{G}/H-A_v1_after.svg")[0] == 200
assert f"/sheet/{G}/H-A_v1_after.svg" in zoom_of(get(f"/toy/{G}?see=H-A&kind=after")[1])

server.shutdown()
print("ok")
