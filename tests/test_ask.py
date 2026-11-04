"""作っている最中の手順の質問の口（本人の決定 11-04）。仕組みは答えず、よくある言葉は刷った説明から答え、AI には仮説を渡さない。"""
import os
import tempfile
from types import SimpleNamespace

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api import ask  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 仕組み・どの仮説かは答えない
for q in ("どういう仕組みで動くの？", "仮説 A と C どっちが正しい？", "正解を教えて"):
    assert ask.answer(G, "H-A", q, client=object()) == (ask.REFUSE, "refuse"), q
# よくある言葉は刷った説明から（AI を呼ばない。呼べば object() は落ちる）
text, how = ask.answer(G, "H-A", "谷折り、山折りがわからない", client=object())
assert how == "glossary" and "手前にへこむ" in text and "手前に出る" in text
assert ask.answer(G, "H-A", " ", client=object())[1] == "refuse"


class Fake:
    def __init__(self, reply):
        self.reply, self.sent = reply, None
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **req):
        self.sent = req
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reply)], usage=SimpleNamespace(input_tokens=10, output_tokens=5))


# AI に渡すのは組み方と凡例だけで、仮説の名前と動き方は入らない
from omochae import hypotheses  # noqa: E402

h = next(x for x in hypotheses.load(G)["hypotheses"] if x["id"] == "H-A")
f = Fake("内筒に竹串を通してから、外筒に入れます。")
text, how = ask.answer(G, "H-A", "竹串はいつ通すの？", client=f)
assert how == "ai" and text.startswith("内筒")
sent = f.sent["messages"][0]["content"]
assert "組み方" in sent and h["name"] not in sent and h["how_it_moves"] not in sent and "仮説" not in sent
assert f.sent["model"] == "claude-opus-5-5"
# 答えに仮説の言葉が混ざったら出さない
assert ask.answer(G, "H-A", "竹串はいつ通すの？", client=Fake(f"これは{h['name']}です"))[1] == "refuse"
print("ok")
