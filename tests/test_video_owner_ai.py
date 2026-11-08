"""確認の前の動画を Claude に渡す口は、上げた本人の鍵を持つ画面だけ。読んだ文も、その画面にだけ出す（tests/test_photo_owner_only.py の続き）。

見る事:
1. 動画を見てもらう釦は、上げた本人の画面にだけ出る。別の人が送っても 403 で、Claude を呼ばず、文も残らない
2. 上げた本人は呼べる。読んだ文はその画面にだけ出て、どの動画を読んだかを控える
3. 鍵の期限を過ぎたら閉じる。説明の前も、別の人には 403 が先
4. 物だけと確かめた後は誰でも呼べて、文も誰にでも出る。人や声が入ると確かめた動画は誰も呼べず、前に読んだ文も出さない
5. どの動画を読んだかの控えが無い前の文は、その記録の動画を見られる画面にだけ出す
"""
import http.client
import json
import re
import os
import pathlib
import tempfile
import threading
import urllib.parse
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from api import agent, ask, observe  # noqa: E402
from omochae import loop, media_review, records  # noqa: E402
from web.play_server import serve  # noqa: E402
from web.techo_site import media_dir  # noqa: E402
from web import wording  # noqa: E402

ask._key_present = lambda: True
observe.frames = lambda path: [b"koma"]
G = "NDL-1187053-R0000005-L"
OWN_KEY, OTHER_KEY = "agetahitonokagi", "betsunohitonokagi"
READ = "扇が筒の口から上へ出た"


class Fake:
    def __init__(self):
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **req):
        self.calls += 1
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps({"observed": [READ], "unclear": []}, ensure_ascii=False))], usage=SimpleNamespace(input_tokens=1, output_tokens=1))


fake = Fake()
agent.default_client = lambda role=None: fake
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
port = server.server_address[1]


def call(path, key=None, form=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=120)
    h = {"Host": f"127.0.0.1:{port}"}
    if key:
        h["Cookie"] = f"utsushi_up={key}"
    body = None
    if form is not None:
        body = urllib.parse.urlencode(form)
        h.update({"Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/x-www-form-urlencoded"})
    c.request("POST" if form is not None else "GET", path, body, h)
    r = c.getresponse()
    data = r.read().decode(errors="replace")
    c.close()
    return r.status, data


def video_record(key=OWN_KEY, explained=True):
    rid, failures = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
    assert not failures, failures
    if explained:
        assert not loop.save_explanation(rid, "作った人", "開いた", "速く押す")
    d = media_dir(rid)
    d.mkdir(parents=True, exist_ok=True)
    (d / "m1.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    media_review.claim(rid, "m1.mp4", key)
    return rid


def reviewed(rid, shows):
    """人の確認の結果を置く。動画の中身は作り物なので、確認の命令（音を落とす）を通さず、結果の形だけを置く。"""
    (media_dir(rid) / "review.json").write_text(json.dumps({"m1.mp4": {"shows": shows}}), encoding="utf-8")
    __import__('omochae.media_review', fromlist=['bind_legacy']).bind_legacy()  # 名だけの確認は通さない（安全の事項 2 の続き）ので、試験の置き場の確認も今の中身に結び直す


# 本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などはすべてもちよるに統合する。」で、つくるの頁から記録の札を外した。
# 記録の札の操作（動画を見てもらう）と読んだ文は手帖の記録の頁にあるので、そこで見る。つくるの頁には、どの画面にも札が出ない事を、呼ぶたびに見る
def pages(key=None):
    toy = call(f"/toy/{G}", key)[1]
    assert "/ai-observe" not in toy and READ not in toy, "つくるの頁に記録の札が残った"
    return call(f"/toy/{G}/techo/kiroku", key)[1]


def card(page, rid):
    """手帖の記録の頁の、その記録の札（「記録の番号 R-…」から次の記録の番号まで。札の中にも item の箱があるので、箱でなく番号で区切る）。"""
    return re.split(r"記録の番号 R-\d{4}", page.split(wording.record_no(rid), 1)[1], maxsplit=1)[0]


def kiroku(key=None):
    return pages(key)


rid = video_record()
form = f"/record/{rid}/ai-observe"
# 1. 釦は上げた本人の画面にだけ。別の人が送っても 403 で、呼ばず、残らない
assert form in pages(OWN_KEY), "上げた本人には釦が出る"
for key in (None, OTHER_KEY):
    assert form not in pages(key), "別の人には釦を出さない"
    assert call(form, key, {})[0] == 403, "受け口でも断る"
assert fake.calls == 0 and observe.observation(rid) is None, "別の人の頼みで Claude を呼ばない"

# 2. 上げた本人は呼べる。読んだ文はその画面にだけ
assert call(form, OWN_KEY, {})[0] == 303
assert fake.calls == 1 and observe.observation(rid)["video"] == "m1.mp4", "どの動画を読んだかを控える"
assert READ in pages(OWN_KEY), "上げた本人には読んだ文が出る"
assert READ not in pages() and READ not in pages(OTHER_KEY), "確認の前の動画を読んだ文を、別の人に出さない"

# 3. 期限を過ぎたら閉じる。説明の前も、別の人には 403 が先
owners = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "records" / "media" / rid / "owners.json"
kept = owners.read_text(encoding="utf-8")
old = (datetime.now(timezone(timedelta(hours=9))) - timedelta(hours=media_review.OWNER_HOURS, minutes=1)).isoformat(timespec="seconds")
owners.write_text(json.dumps({k: {**v, "at": old} for k, v in json.loads(kept).items()}), encoding="utf-8")
assert call(form, OWN_KEY, {})[0] == 403 and form not in pages(OWN_KEY) and READ not in pages(OWN_KEY), "期限の後は上げた本人の画面も閉じる"
owners.write_text(kept, encoding="utf-8")
early = video_record(explained=False)
assert call(f"/record/{early}/ai-observe", None, {})[0] == 403, "別の人には説明の有無を言わない"
assert call(f"/record/{early}/ai-observe", OWN_KEY, {})[0] == 422, "上げた本人には今までどおり説明が先"

# 4. 確認の後は確認のとおり
reviewed(rid, "object")
assert form in pages(OTHER_KEY) and READ in card(kiroku(OTHER_KEY), rid), "物だけと確かめた後は誰にでも"
calls = fake.calls
assert call(form, OTHER_KEY, {})[0] == 303 and fake.calls == calls + 1, "物だけと確かめた後は誰でも呼べる"
hidden = video_record()
assert call(f"/record/{hidden}/ai-observe", OWN_KEY, {})[0] == 303
assert READ in card(kiroku(OWN_KEY), hidden)
reviewed(hidden, "people")
calls = fake.calls
assert call(f"/record/{hidden}/ai-observe", OWN_KEY, {})[0] == 303 and fake.calls == calls, "人や声が入る動画は誰も渡せない（前からの断りの文）"
for key in (OWN_KEY, None):
    assert READ not in card(kiroku(key), hidden), "人や声が入る動画を読んだ前の文も出さない"

# 5. どの動画を読んだかの控えが無い前の文は、その記録の動画を見られる画面にだけ
older = video_record()
loop._write(observe.path(older), {"record_id": older, "observed": ["前の文の目印"], "unclear": [], "by": "claude", "label": "観察（Claude の補助）"})
assert "前の文の目印" in card(kiroku(OWN_KEY), older) and "前の文の目印" not in card(kiroku(OTHER_KEY), older)
assert "前の文の目印" in call(f"/toy/{G}/techo/kiroku", OWN_KEY)[1] and "前の文の目印" not in call(f"/toy/{G}/techo/kiroku")[1]

print("ok: 確認の前の動画を Claude に渡す口と読んだ文は、上げた本人の画面だけ")
