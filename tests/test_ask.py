"""作っている最中の手順の質問の口（本人の決定 11-04）。仕組みは答えず、語そのものを尋ねる短い問いは刷った説明から答え、AI には仮説を渡さない。"""
import os
import tempfile
from types import SimpleNamespace

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tempfile.mkdtemp(), "api-usage.jsonl")  # 本物の台帳に書かない（#151）

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

# 語そのものを尋ねる短い問いは、語の説明だけを返す（AI を呼ばない。呼べば object() は落ちる）
for q, word in (("谷折りって？", "谷折り"), ("蛇腹とは", "蛇腹"), ("蛇腹とは？", "蛇腹"), ("谷折りって何", "谷折り"), ("谷折りは何？", "谷折り"),
                ("谷折り って何", "谷折り"), ("糊代って何ですか", "糊代"), ("のりしろってなに？", "のりしろ"), ("ジャバラ", "ジャバラ"),
                ("物差しの意味は？", "物差し"), ("色の境ってどういう意味", "色の境"), ("蛇腹がわからない", "蛇腹"), ("山折りが分かりません", "山折り"),
                ("谷折りを教えてください", "谷折り")):
    assert ask.answer(G, "H-A", q, client=object()) == (ask.GLOSSARY[word], "glossary"), q
assert ask.answer(G, "H-A", "谷折りと山折りって何？", client=object()) == (f"{ask.GLOSSARY['谷折り']} {ask.GLOSSARY['山折り']}", "glossary")

# 語が入っていても、ほかの中身がある問いに語の説明で答えた事にしない。AI へ渡す（#287。蛇腹の固定は 11-04 の試行で一番手こずった所）
for q in ("蛇腹が固定できない。どうしたらいい？", "蛇腹がすぐ開いてしまう", "糊代がはがれる", "谷折りしたら破れた", "色の境で折れない", "物差しが 10cm にならない",
          "蛇腹って何回折るの？", "蛇腹ってなんで開くの？", "蛇腹って何？固定できないんだけど", "谷折りって何？ 電話は 090-1234-5678 です"):
    f = Fake("端を糊代で貼ります。")
    assert ask.answer(G, "H-A", q, client=f) == ("端を糊代で貼ります。", "ai"), q
    assert q in f.sent["messages"][0]["content"], q

# 鍵が無い時: 語が入っていれば語の説明を残し、AI に聞けない事も言う（どこから は no_key。語の表で答えた問いと数を分ける）
ask._key_present = lambda: False
text, how = ask.answer(G, "H-A", "蛇腹が固定できない。どうしたらいい？")
assert how == "no_key" and text.startswith(ask.GLOSSARY["蛇腹"]) and ask.NO_KEY in text, (text, how)
assert ask.answer(G, "H-A", "竹串はいつ通すの？") == (ask.NO_KEY, "no_key")
# 鍵が無くても、語そのものの問いと仕組みの問いの答えは変わらない
assert ask.answer(G, "H-A", "谷折りって？") == (ask.GLOSSARY["谷折り"], "glossary")
assert ask.answer(G, "H-A", "これはどう動くの？") == (ask.REFUSE, "refuse")
assert ask.answer(G, "H-A", "蛇腹はどう動くの？") == (ask.REFUSE, "refuse"), "語が入っていても、仕組みの問いは先に断る"
print("ok")
