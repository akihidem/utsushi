"""外の検品（2026-11-04、src/api の指摘）で見つかった穴を塞いだ事の試験。本物の API は呼ばない。

なぜ 1 本にまとめ、番号で区切るか: 指摘ごとに「直す前に落ちる（Red）→ 直した後に通る（Green）」を
別々に残すため。`python tests/test_api_review_fixes.py 3` で 3 番だけを回せる。引数が無ければ全部回す。
番号は検品の指摘の番号（1 予算の前払い / 2 提出と道具の同居 / 3 案の形 / 4 根拠の玩具と確定 /
5 新しい仮説の形 / 6 記録の玩具と仮説の雛形 / 8 最適化で assert が消える）。7 は指摘の誤りで直していない。
"""
import json
import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace as NS

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tempfile.mkdtemp(), "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import agent, ask, budget, config, generate as gen, loop_agents  # noqa: E402
from omochae import hypotheses, loop, records  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
gs = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
ts = json.loads((ROOT / "data/sources" / f"{T}.json").read_text(encoding="utf-8"))
A = {"push_part": "tab", "hub": "axle", "pusher_height": 15}
C = {"push_part": "stick", "hub": "axle", "pusher_height": 84}
# 日割りの上限は日付で変わる（表に無い日は既定の額）。試験を回す日で結果が変わらないよう、表にある日に固定する。
budget._today = lambda: "11-04"


def fresh():
    """番号ごとに置き場を分ける。前の番号の費用や記録が次の番号の結果を変えないため。"""
    os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
    os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tempfile.mkdtemp(), "api-usage.jsonl")


def floors(fs):
    return {f.floor for f in fs}


def tool(name, input, i="t"):
    return NS(type="tool_use", name=name, input=input, id=f"{i}-{name}")


class Fake:
    """台本どおりに返す偽の client。usage は 1 回ごとに変えられる（予算の試験のため）。"""

    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        content, stop, *usage = self.script.pop(0)
        u = usage[0] if usage else {"input_tokens": 10, "output_tokens": 5}
        return NS(content=content, stop_reason=stop, usage=NS(**u))


def spend(usd, day=None):
    with open(budget._path(), "a", encoding="utf-8") as f:
        f.write(json.dumps({"day": day or budget._today(), "role": "x", "model": "claude-opus-5-5", "input": 0, "output": 0, "usd": usd}) + "\n")


def hyp(name, params, template="slider_fan", evidence=None):
    return {"name": name, "how_it_moves": "動かす", "physics": "折り目の力", "evidence": evidence or [{"kind": "image", "where": "寝かせた筒", "what": "棒", "certainty": "観察"}],
            "against": ["未確認"], "to_measure": "角度", "template_id": template, "params": params, "vs_prediction": {"same": ["手で動かす"], "different": ["棒"]}}


SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}


def must_stop(fn):
    try:
        fn()
    except budget.BudgetStop:
        return
    raise AssertionError("予算で止まるはず")


def test_1():
    """呼ぶ前に、この 1 回の最悪の費用まで足して上限を見る。今までの消費だけを見ると、上限の直前から 1 回分はみ出す。"""
    fresh()
    cap = budget.DAILY_CAP[budget._today()]
    # 今日の残りが 1 回の出力の上限の費用（16000 × $20/M = $0.32）より少ない。呼べばはみ出し得る
    spend(cap - 0.05)
    blocked = Fake([])
    must_stop(lambda: agent.run("generate", "指示", "問い", [], SCHEMA, lambda n, i: "", client=blocked))
    assert blocked.calls == [], "はみ出し得る 1 回を呼ばない"
    # 累計の停止線も同じ（今日の分は 0 で、前の日までの累計が線の直前）
    fresh()
    spend(budget.STOP_TOTAL - 0.05, day="01-01")
    blocked = Fake([])
    must_stop(lambda: agent.run("generate", "指示", "問い", [], SCHEMA, lambda n, i: "", client=blocked))
    assert blocked.calls == []
    # 1 回の生成の上限: 1 往復目で $2.9 使ったら、2 往復目（最悪 $0.32 以上）は呼ばない
    fresh()
    big = {"input_tokens": 725_000, "output_tokens": 0}  # 725000 × $4/M = $2.90
    client = Fake([([tool("echo", {}, "a")], "tool_use", big), ([tool("submit_result", {"answer": "x"}, "b")], "tool_use")])
    must_stop(lambda: agent.run("generate", "指示", "問い", [{"name": "echo", "description": "", "input_schema": {"type": "object"}}], SCHEMA, lambda n, i: "", client=client))
    assert len(client.calls) == 1, "2 往復目は呼ばない"
    # 手順の質問の口も同じ見方をする
    fresh()
    spend(cap - 0.001)
    f = NS(sent=None)
    f.messages = NS(create=lambda **req: setattr(f, "sent", req))
    must_stop(lambda: ask.answer(G, "H-A", "竹串はいつ通すの？", client=f))
    assert f.sent is None, "手順の質問も、はみ出し得る 1 回を呼ばない"
    # 余裕があれば今までどおり呼ぶ。図の base64 の長さを文字数として数えて、大きな図 1 枚で止めない
    fresh()
    image = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "A" * 3_000_000}}, {"type": "text", "text": "問い"}]
    ok = Fake([([tool("submit_result", {"answer": "x"}, "c")], "tool_use")])
    assert agent.run("generate", "指示", image, [], SCHEMA, lambda n, i: "", client=ok)[0] == {"answer": "x"}
    # 前からの呼び方（引数なし・今の 1 回の費用だけ）はそのまま動く
    fresh()
    budget.check()
    budget.check(0.5)
    must_stop(lambda: budget.check(budget.PER_RUN_CAP))
    # 最悪の見積もりは、出力を上限まで使い、入力を全部キャッシュの書き込み（入力の単価の 1.25 倍）で数える
    assert abs(budget.worst_case("claude-opus-5-5", 1_000_000, 1_000_000) - (4 * 1.25 + 20)) < 1e-9
    must_stop(lambda: budget.check(budget.PER_RUN_CAP - 0.1, 0.2))


def test_2():
    """同じ応答に他の道具と submit_result が並んだら、道具の結果を返してから提出し直させる。結果を読まずに出した提出を受けない。"""
    fresh()
    ran = []

    def execute(name, inp):
        ran.append(name)
        return "echo の結果"

    tools = [{"name": "echo", "description": "", "input_schema": {"type": "object"}}]
    client = Fake([([tool("echo", {}, "a"), tool("submit_result", {"answer": "早すぎる"}, "a")], "tool_use"),
                   ([tool("submit_result", {"answer": "読んだ後"}, "b")], "tool_use")])
    result, trace = agent.run("interpret", "s", "u", tools, SCHEMA, execute, client=client)
    assert ran == ["echo"], "並んだ道具は実行する"
    assert len(client.calls) == 2 and result == {"answer": "読んだ後"}, "同居した提出は受けず、もう 1 度呼ぶ"
    # messages は同じリストを使い回すので、道具の結果を返した user の発言を探す。
    back = [m for m in client.calls[1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)][-1]["content"]
    ids = {b["tool_use_id"]: b for b in back}
    assert ids["a-echo"]["content"] == "echo の結果", "道具の結果を返す"
    assert ids["a-submit_result"].get("is_error") is True, "提出には受けなかった事を返す（tool_use には必ず tool_result を返す）"
    assert trace.retries == 0, "同居は検査の落ちではないので、やり直しの回数に数えない"


def test_3():
    """案の形を SCHEMA で見る。要る欄が欠けた案を、API の道でも Claude Code の道でも受けない。"""
    fresh()
    assert hypotheses.save_prediction(G, "筒を押すと上が開く")[1] == []
    thin = {k: v for k, v in hyp("欄が欠けた", A).items() if k not in ("physics", "against", "to_measure", "vs_prediction")}
    draft = {"hypotheses": [thin, hyp("b", C)], "references": []}
    assert gen.check_result(draft, gs), "欠けた欄を落とす"
    gid, fs = gen.import_draft(gs, draft, "セッション")
    assert gid is None and fs, "Claude Code の道でも受けない"
    assert gen.check_result({"hypotheses": [hyp("a", A), {**hyp("b", C), "evidence": "絵"}], "references": []}, gs), "型の違いを落とす"
    assert gen.check_result({"hypotheses": [hyp("a", A), hyp("b", C)]}, gs), "references も要る"
    # API の道: 欠けた案は直させ、直った案を受ける
    good = {"hypotheses": [hyp("a", A), hyp("b", C), {**hyp("雛形に無い読み", None, None), "params": None}], "references": []}
    client = Fake([([tool("submit_result", draft, "a")], "tool_use"), ([tool("submit_result", good, "b")], "tool_use")])
    gid, fs = gen.generate(gs, client, image="QQ==")
    assert not fs and gid and len(client.calls) == 2, "欠けた案は 1 度落として直させる"
    assert gen.check_result(good, gs) == [], "雛形に無い読み（params が null）は今までどおり通る"


def test_4():
    """根拠の記録・前例は、同じ玩具の物で、記録は人が解釈を確定した物だけ。別の玩具の記録や未確定の記録を根拠にしない。"""
    fresh()
    other, fs = records.add({"source_id": T, "hypothesis_id": "H-A", "sheet_version": 1, "result": "揺れた", "fixes": [], "note": "x"})
    assert not fs and loop.confirm_interpretation(other, "確認者", {"human_text": "揺れた"}) == []
    pending, fs = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動かない", "fixes": [], "note": "y"})
    assert not fs
    mine, fs = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動かない", "fixes": [], "note": "z"})
    assert not fs and loop.confirm_interpretation(mine, "確認者", {"human_text": "固い"}) == []

    def with_ref(rid, refs=()):
        ev = [{"kind": "record", "where": rid, "what": "試した", "certainty": "記録"}]
        return {"hypotheses": [hyp("a", A, evidence=ev), hyp("b", C)], "references": list(refs)}

    assert floors(gen.check_result(with_ref(other), gs)) == {"F8.references"}, "別の玩具の記録を根拠にしない"
    assert floors(gen.check_result({**with_ref(mine), "references": [other]}, gs)) == {"F8.references"}, "別の玩具の記録を前例にしない"
    assert floors(gen.check_result(with_ref(pending), gs)) == {"F9.human"}, "確定していない記録を根拠にしない"
    assert floors(gen.check_result({**with_ref(mine), "references": [pending]}, gs)) == {"F9.human"}
    assert gen.check_result(with_ref(mine, [mine]), gs) == [], "同じ玩具の確定した記録は根拠にできる"
    ev = [{"kind": "known_example", "where": mine, "what": "x", "certainty": "記録"}]
    assert floors(gen.check_result({"hypotheses": [hyp("a", A, evidence=ev), hyp("b", C)], "references": []}, gs)) == {"F8.references"}, "種類と ID が合わない根拠を通さない"


def _confirmed_record(source, hid, **kw):
    rid, fs = records.add({"source_id": source, "hypothesis_id": hid, "sheet_version": 1, "fixes": [], "note": "x", **kw})
    assert not fs, fs
    assert loop.save_explanation(rid, "確認者", "わからない", "もう一度") == []
    assert loop.confirm_interpretation(rid, "確認者", {"human_text": "x"}) == []
    return rid


NEXT = {"why": "比べる", "what_to_measure": "角度"}


def test_5():
    """新しい仮説の案は、一覧の仮説と同じ欄（名前・動き方・根拠・反証・測る事）を持つ。空の {} を案として残さない。"""
    fresh()
    rid = _confirmed_record(G, "H-A", result="動かない")
    newh = {"name": "糸で先に開く", "how_it_moves": "糸を引く", "evidence": [], "against": ["未確認"], "to_measure": "角度", "params": C}
    client = Fake([([tool("submit_result", {"new_hypothesis": {}, "next_to_try": NEXT, "references": [rid]}, "a")], "tool_use"),
                   ([tool("submit_result", {"new_hypothesis": {"name": "名だけ"}, "next_to_try": NEXT, "references": [rid]}, "b")], "tool_use"),
                   ([tool("submit_result", {"new_hypothesis": newh, "next_to_try": NEXT, "references": [rid]}, "c")], "tool_use")])
    pid, fs = loop_agents.draft_proposal(rid, gs, client)
    assert not fs and len(client.calls) == 3, "空の仮説・欄の欠けた仮説は直させる"
    saved = loop._read(loop.folder() / f"proposal-{pid[2:]}.json")
    assert saved["new_hypothesis"]["name"] == "糸で先に開く"
    req = loop_agents.PROPOSE_SCHEMA["properties"]["new_hypothesis"]["required"]
    assert {"name", "how_it_moves", "evidence", "against", "to_measure"} <= set(req)
    blank = {**newh, "how_it_moves": " "}
    assert loop_agents.check_new_hypothesis(blank), "空白だけの欄も落とす"
    assert loop_agents.check_new_hypothesis(newh) == []


def test_6():
    """渡された玩具と記録の玩具が違えば Claude を呼ばない。案の雛形は、玩具の既定でなく、その記録の仮説の雛形を使う。"""
    fresh()
    tr = _confirmed_record(T, "H-A", result="揺れた")
    never = Fake([])
    pid, fs = loop_agents.draft_proposal(tr, gs, never)
    assert pid is None and floors(fs) == {"F8.references"} and never.calls == [], "別の玩具の記録で案を作らない"
    # 鶴の頁に、雛形の違う（振り子の）新しい仮説を人が採った後
    extras = [{"id": "H-N1", "name": "振り子で揺れる", "how_it_moves": "重りで揺れる", "status": "untested", "template": "pivot_counterweight", "params": {"mount": "neck"},
               "evidence": [], "against": [], "to_measure": "周期"}]
    loop._write(loop.folder() / f"extra-hypotheses-{G}.json", extras)
    rid = _confirmed_record(G, "H-N1", result="動かない")
    client = Fake([([tool("submit_result", {"next_to_try": NEXT, "references": [rid]}, "a")], "tool_use")])
    pid, fs = loop_agents.draft_proposal(rid, gs, client)
    assert not fs, fs
    sent = json.loads(client.calls[0]["messages"][0]["content"].split("<data>\n", 1)[1].rsplit("\n</data>", 1)[0])
    assert sent["template_id"] == "pivot_counterweight", "仮説の雛形を渡す"
    assert sent["allowed_params"] == sorted(loop.ALLOWED["pivot_counterweight"])


def test_8():
    """PYTHONOPTIMIZE が環境に残っていても、床の入口は assert を消さずに試験を回す。消えると落ちる試験が通って見える。"""
    sys.path.insert(0, str(ROOT / "tests"))
    import run_floors

    root = pathlib.Path(tempfile.mkdtemp())
    (root / "tests/frozen/scenarios").mkdir(parents=True)
    (root / "tests/test_masked.py").write_text("assert False, '消えてはいけない assert'\n", encoding="utf-8")
    run_floors.write_manifest(root)  # 床の入口は凍結の表と照らしてから回す（#165）。この小さな tree にも表を置く
    keep, old_root = os.environ.get("PYTHONOPTIMIZE"), run_floors.ROOT
    os.environ["PYTHONOPTIMIZE"] = "1"
    run_floors.ROOT = root
    try:
        rc = run_floors.main()
    finally:
        run_floors.ROOT = old_root
        if keep is None:
            os.environ.pop("PYTHONOPTIMIZE", None)
        else:
            os.environ["PYTHONOPTIMIZE"] = keep
    assert rc == 3, f"落ちる assert が通って見えた（rc={rc}）"
    assert "| test_masked |" in (root / "out/RESULT.md").read_text(encoding="utf-8") and "NG" in (root / "out/RESULT.md").read_text(encoding="utf-8")


ALL = {"1": test_1, "2": test_2, "3": test_3, "4": test_4, "5": test_5, "6": test_6, "8": test_8}

if __name__ == "__main__":
    # この試験自体も素の assert に頼るので、-O で回されたら黙って通らずに止める。
    if not __debug__:
        sys.exit("assert が消える設定（-O / PYTHONOPTIMIZE）では回さない")
    for key in sys.argv[1:] or ALL:
        ALL[key]()
        print(f"ok {key}")
    print("ok")
