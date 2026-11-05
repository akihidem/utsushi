"""型紙の窓の中で紙を見られ（札はたたき台の 1 枚だけ。J-032）、「刷る」は紙に印刷する所だけを指す（#127。要件 S-01・S-06）。

なぜ: 札の「刷る」は絵を作るだけで印刷せず、窓の説明と順が逆だった。ほかの仮説を見るには節を戻って札ごとに押す必要があり、
押せない点線の札の理由は title にしか無く、スマホでは読めなかった。
"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import hypotheses, loop  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    return urllib.request.urlopen(base + path).read().decode()


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    try:
        x = urllib.request.urlopen(r)
        return x.status, x.geturl(), x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, "", e.read().decode()


def visible(page):
    """画面に出る字だけ（style と script と属性を除く）。"""
    return re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script)\b.*?</\1>", " ", page, flags=re.S))


def win(page):
    return page.split('id="win"', 1)[1].split("</section>", 1)[0]


# 予想の段は #266 で外したので、予想を置かずに開いた頁で窓を見る
page = get(f"/toy/{G}")
ids = [h["id"] for h in hypotheses.load(G)["hypotheses"]]
first, other = hypotheses.sheet_of(G)["id"], ids[1]
making = lambda hid: f'<form method="post" action="/toy/{G}/print#win" class="inline"><input type="hidden" name="hypothesis" value="{hid}"><input type="hidden" name="at" value="win"><button data-busy>'
# 窓の札はたたき台の 1 枚だけ（本人の決定 11-05、J-032）。最初の 1 枚も窓の中で作れる。上の節の札は「型紙を見る」で、印刷とは言わない
assert "型紙を見る</button>" in page and making(first) in win(page) and making(other) not in win(page), win(page)[:600]
assert "仮説の札を押すと、紙を作ってここに出します" in visible(win(page))
# 窓の札から押して紙を作れない時は、理由も窓で読める。上の節の札から押した時は、上の節で読む（#121 の線）
real = hypotheses.print_sheet
hypotheses.print_sheet = lambda *a, **k: 1
code, _, failed = post(f"/toy/{G}/print", {"hypothesis": first, "at": "win"})
assert code == 422 and "型紙を作れませんでした" in win(failed), (code, win(failed)[:300])
code, _, failed = post(f"/toy/{G}/print", {"hypothesis": first})
assert code == 422 and "型紙を作れませんでした" not in win(failed) and "型紙を作れませんでした" in failed.split('id="kasetsu"', 1)[1], code
hypotheses.print_sheet = real
code, where, page = post(f"/toy/{G}/print", {"hypothesis": first})
assert code == 200 and f"see={first}" in where and where.endswith("#win"), (code, where)
w = win(page)
# 「刷る」「印刷」は、紙に印刷する所にだけ出る。PDF の釦の下の案内（#297）も印刷する所なので除く
rest = visible(re.sub(r'<details class="print-help">.*?</details>', "", w, flags=re.S))
for printing in ("印刷する時は PDF を 100% で", "印刷する前に案を検討する所", "PDF を開いて印刷する", "100% で刷り"):
    assert printing in rest, printing
    rest = rest.replace(printing, "")
assert "刷" not in rest and "印刷" not in rest, rest[:400]
assert not [b for b in re.findall(r"<button[^>]*>(.*?)</button>", page, re.S) if "刷" in b or "印刷" in b]
assert "紙を作りました" in page and "刷りました" not in page
# 紙ができた札は字のリンクになる。ほかの仮説の札は窓にも節にも出ない。順位や推しの字は足さない
assert making(first) not in w and f"see={first}&" in w and making(other) not in w, w[:600]
assert "仮説の点線の札は" not in w
# 仮説の札の下には紙ごとの字のリンクを並べない。種類と版は窓の札で選ぶ（#127 の補足）
plates = page.split('id="kasetsu"', 1)[1].split('id="win"', 1)[0]
assert "kind=tejun" not in plates and f'see={first}&kind=sheet&v=1#win" aria-label=' in plates, plates[-600:]
assert "おすすめ" not in w and "順位" not in w
assert post(f"/toy/{G}/print", {"hypothesis": other, "at": "win"})[0] == 422 and not list(out_dir(G).glob(f"{other}_v1*")), "断った紙を残さない"
# 型紙の確定の記録は、押した紙の分だけ残る（線は変えない）
assert {c["hypothesis_id"] for c in loop.sheet_confirmations(G)} == {first}
# 試した後の紙は、記録の前は渡さず、理由を字で出す
assert "試した後の紙は、記録を残すと開きます" in visible(win(page))
assert f"{first}_v1_after" not in win(page)
assert post(f"/toy/{G}/record", {"hypothesis": first, "result": "動いた"})[0] in (200, 303)
page = get(f"/toy/{G}?see={first}")
assert "試した後の紙は、記録を残すと開きます" not in visible(win(page)), "開いた後は言わない"

server.shutdown()
print("ok")
