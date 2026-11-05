"""「次の版を作る」が途中で通らない時、置き場に何も増やさない（#158）。

なぜ試験にするか: 1 回の操作が 解釈の確定 → 提案 → 採用 → 刷る → 型紙の確定 を順に書くので、途中で落ちると前の分だけが残る。
解釈が確定で残ると根拠に使えてしまい、版の記録だけが残ると同じ値で送り直せず、版 2 の紙を刷る道も無かった。
"""
import json
import os
import pathlib
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, loop  # noqa: E402
from omochae.model import ToolMissing  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
DATA = pathlib.Path(os.environ["OMOCHAE_DATA"])
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST",
                               headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    try:
        x = urllib.request.urlopen(r)
        return x.status, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def tree():
    """置き場の全部のファイルと中身。ロックのファイルは読みの印なので数えない。"""
    return {str(p.relative_to(DATA)): p.read_bytes() for p in DATA.rglob("*") if p.is_file() and p.name != ".lock"}


def assert_nothing_added(before, why):
    after = tree()
    added = sorted(set(after) - set(before))
    changed = sorted(k for k in before if k in after and before[k] != after[k])
    assert not added and not changed, f"{why}: 増えた {added} 変わった {changed}"


# 版 1 を刷り、記録と説明まで進める。
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] in (200, 303)
assert post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "わからない"})[0] == 201
rid = next((DATA / "records").glob("R-*.json")).stem
assert post(f"/record/{rid}/explain", {"by": "本人", "text": "筒が支えになった", "next_idea": "折りを増やす"})[0] in (200, 303)
form = {"interpretation": "折りが多く、筒の口に当たって開き切らない", "param": "fold_count", "why": "口に当たらないように", "by": "本人"}
before = tree()

# 通らない値: どの段で落ちても、ファイルが 1 つも増えず、解釈も確定で残らない。
for bad, says in (({"to": "29"}, "筒の口の角に当たって"), ({"to": "abc"}, "新しい値は数で書く"), ({"to": "26", "why": " "}, "変える理由が無い"),
                  ({"to": "26", "param": "no_such"}, "変えてよい寸法の外"), ({"to": "26", "by": " "}, "確定した人の名前が無い"),
                  ({"to": "26", "interpretation": " "}, "解釈の案が無く")):
    code, page = post(f"/record/{rid}/next", form | bad)
    assert code == 422 and says in page, (bad, code, page[-400:])
    assert_nothing_added(before, f"通らない値 {bad}")
assert not loop.confirmed(rid), "通らなかった操作で解釈を確定にしない"

# 刷るのに失敗する: 検査に落ちても、道具が無くても、版の記録も半端な紙も残らない。
real_print = hypotheses.print_sheet


def print_fails(sid, hid, out, version=1, **kw):
    pathlib.Path(f"{out}.pdf").write_bytes(b"half")  # 半端な紙を書いてから落ちる
    return 3


def tool_gone(sid, hid, out, version=1, **kw):
    pathlib.Path(f"{out}.pdf").write_bytes(b"half")
    raise ToolMissing("pdftoppm が無い")


hypotheses.print_sheet = print_fails
code, page = post(f"/record/{rid}/next", form | {"to": "26"})
assert code == 422 and "版 2 の紙を作れませんでした" in page, (code, page[-400:])
assert_nothing_added(before, "刷るのが検査に落ちた")
hypotheses.print_sheet = tool_gone
code, _ = post(f"/record/{rid}/next", form | {"to": "26"})
assert code >= 400, code
assert_nothing_added(before, "刷る道具が無い")
hypotheses.print_sheet = real_print
assert loop.latest_version(G, "H-A") == 1
assert not list(out_dir(G).glob(".tmp-*")), "一時の場所を残さない"

# 通る値: 落ちた後に同じ値で送り直せて、全部が 1 組で揃う。
code, page = post(f"/record/{rid}/next", form | {"to": "26"})
assert code in (200, 303), page[-400:]
assert loop.confirmed(rid) and loop.latest_version(G, "H-A") == 2
for suffix in ("", "_tejun", "_after"):
    assert (out_dir(G) / f"H-A_v2{suffix}.pdf").read_bytes()[:4] == b"%PDF", f"版 2 の紙 {suffix}"
assert not list(out_dir(G).glob(".tmp-*")), "一時の場所を残さない"
v = json.loads((DATA / "loop" / f"version-{G}-H-A-2.json").read_text(encoding="utf-8"))
assert v["params"]["fold_count"] == 26 and v["changes"][0]["from"] != 26 and v["record_ids"] == [rid]
proposal = json.loads((DATA / "loop" / f"{v['proposal'].replace('P-', 'proposal-')}.json").read_text(encoding="utf-8"))
assert proposal["status"] == "decided" and proposal["accepted"] == {"version": 2}
assert any(c["version"] == 2 for c in loop.sheet_confirmations(G)), "型紙の確定も同じ操作で残る"
# 一時の場所で刷っても、紙には記録と同じ版と根拠が載る。
text = subprocess.run(["pdftotext", str(out_dir(G) / "H-A_v2.pdf"), "-"], capture_output=True, text=True, check=True).stdout
assert "版 2" in text and rid in text, text[:300]

# 紙の無い版: 作り直す口が画面に出て、押すと紙ができる。
page_before = urllib.request.urlopen(f"{base}/toy/{G}").read().decode()
assert "作り直す" not in page_before, "紙がある間は出さない"
gone = sorted(p.name for p in out_dir(G).glob("H-A_v2*"))
for name in gone:
    (out_dir(G) / name).unlink()
page_now = urllib.request.urlopen(f"{base}/toy/{G}").read().decode()
assert "版 2 の紙を作り直す" in page_now, "紙の無い版を画面で知らせる"
code, _ = post(f"/toy/{G}/reprint", {"hypothesis": "H-A", "version": "3"})
assert code == 422, "採っていない版は刷らない"
for bad in ({"hypothesis": "H-ZZ", "version": "2"}, {"hypothesis": "H-A", "version": "x"}, {"hypothesis": "H-A", "version": "0"},
            {"hypothesis": "H-A", "version": "1"}, {"hypothesis": "../../x", "version": "2"}):
    assert post(f"/toy/{G}/reprint", bad)[0] == 422, bad
count = len([c for c in loop.sheet_confirmations(G) if c["version"] == 2][0]["confirmations"])
code, _ = post(f"/toy/{G}/reprint", {"hypothesis": "H-A", "version": "2"})
assert code in (200, 303)
assert sorted(p.name for p in out_dir(G).glob("H-A_v2*")) == gone, "同じ組の紙ができる"
assert (out_dir(G) / "H-A_v2.pdf").read_bytes()[:4] == b"%PDF"
assert len([c for c in loop.sheet_confirmations(G) if c["version"] == 2][0]["confirmations"]) == count + 1
assert "作り直す" not in urllib.request.urlopen(f"{base}/toy/{G}").read().decode()
assert not list(out_dir(G).glob(".tmp-*")), "一時の場所を残さない"
server.shutdown()
print("ok")
