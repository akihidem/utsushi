"""Claude の道具と MCP の口の source_id の床（#174）: 形の合わない ID は、ファイルを読む前に道具の失敗として断る。

なぜ要るか: 道具の入力は Claude が書き、Claude には外の人が書いた持ち寄りの文も渡る。source_id をそのままパスにつなぐと、
data/sources の外の JSON を読み、out/zoom の外へ書く形が通る。画面の側は形を確かめてからパスにしているので、同じ式で揃える。
網には出ない。置き場の外の JSON は一時の場所に置いて、読まれない事を見る。
"""
import json
import pathlib
import re
import tempfile
import urllib.request

from api import loop_agents, mcp_server, tools
from api.tools import ToolInputError, check_source_id
from omochae.store import SID
from web import play_server

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"

# 式は画面・道具・MCP の口で同じ 1 つ。式を書いてあるのは src の中で 1 か所だけ
assert play_server.SID == SID
written = [p.relative_to(ROOT).as_posix() for p in (ROOT / "src").rglob("*.py")
           if re.search(r"NDL-\\d\+-R\\d\+", p.read_text(encoding="utf-8"))]
assert written == ["src/omochae/store.py"], written

# 今ある玩具の頁の ID は全部通る（枝番つきも）
ids = [p.stem for p in (ROOT / "data/sources").glob("NDL-*.json")]
assert len(ids) > 80
for sid in ids:
    check_source_id(sid)

with tempfile.TemporaryDirectory() as tmp:
    # data/sources の外の、読めてしまう形の記録。拡大の道具が読めば URL を作って取りに行く
    decoy = pathlib.Path(tmp) / "decoy"
    good = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
    decoy.with_suffix(".json").write_text(json.dumps(good), encoding="utf-8")
    bad_ids = [str(decoy), "../sources/" + G, f"{G}/../{G}", "../../../etc/passwd", G + "\n", " " + G, "own-scans", "", 123, ["x"], {"a": 1}]

    for sid in bad_ids:
        try:
            check_source_id(sid)
        except ToolInputError:
            continue
        raise AssertionError(f"通ってしまった: {sid!r}")

    fetched = []
    real = urllib.request.urlopen
    urllib.request.urlopen = lambda url, *a, **k: fetched.append(url) or (_ for _ in ()).throw(OSError("試験は網に出ない"))
    try:
        for sid in bad_ids:
            for name, args in (("zoom_picture", {"source_id": sid, "x": 1, "y": 1, "w": 1, "h": 1}),
                               ("check_params", {"source_id": sid, "template_id": "slider_fan", "params": {}}),
                               ("list_records", {"source_id": sid}),
                               ("get_known_examples", {"source_id": sid}),
                               ("list_contributions", {"source_id": sid})):
                # API の輪の入口: 例外で返す（agent.run が道具の失敗として Claude に返す）
                try:
                    loop_agents.execute(name, args)
                except ToolInputError as e:
                    assert "source_id" in str(e), str(e)
                else:
                    raise AssertionError(f"{name} が通した: {sid!r}")
                # MCP の口: 同じ断りを isError で返す。サーバは落ちない
                got = mcp_server.handle({"id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})["result"]
                assert got["isError"] is True and "ToolInputError" in got["content"][0]["text"], (name, sid, got)
            got = mcp_server.handle({"id": 1, "method": "tools/call",
                                     "params": {"name": "check_draft", "arguments": {"source_id": sid, "draft": {}}}})["result"]
            assert got["isError"] is True and "ToolInputError" in got["content"][0]["text"], (sid, got)
            try:
                tools.zoom_source(sid, 1, 1, 1, 1)
            except ToolInputError:
                pass
            else:
                raise AssertionError(f"zoom_source が通した: {sid!r}")
    finally:
        urllib.request.urlopen = real
    assert fetched == [], f"置き場の外の記録を読んで取りに行った: {fetched}"

# 持ち寄りの一覧は source_id を省ける（全部の玩具）。省いた時は断らない
assert isinstance(json.loads(loop_agents.execute("list_contributions", {})), list)
assert isinstance(json.loads(loop_agents.execute("list_contributions", {"source_id": None})), list)
# 形が合って実在する ID は、今までどおり動く
assert isinstance(json.loads(loop_agents.execute("get_known_examples", {"source_id": G})), list)
got = mcp_server.handle({"id": 1, "method": "tools/call", "params": {"name": "check_draft", "arguments": {"source_id": G, "draft": {}}}})["result"]
assert got["isError"] is False, got
print("ok source_id")
