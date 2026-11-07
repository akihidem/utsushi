"""作った人の報告（omochae.feedback）の形と、集めて直しの案を出す所を確かめる（Issue #21）。"""
import json
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import feedback as fb  # noqa: E402

OK = {"template": "spinner", "form": "pinwheel", "built": True, "moved": "partly", "finish": 3,
      "motion_notes": "息では回るが、風では止まる", "finish_notes": "羽の角がよれた",
      "problems": [{"kind": "fit", "step": 4, "note": "柄と羽の間が狭く、羽が柄に擦れた"}]}

# 1. 形の誤りを落とす。知らない雛形・その雛形に無い形・決まりの外の値・知らない困り事の種類
assert fb.check(OK) == [], [f.line() for f in fb.check(OK)]
for bad in ({**OK, "template": "no_such"}, {**OK, "form": "jaw"}, {**OK, "moved": "yes"}, {**OK, "finish": 6},
            {**OK, "built": "はい"}, {**OK, "problems": [{"kind": "smell", "step": 1, "note": ""}]}):
    assert any(f.floor == "F12.report" for f in fb.check(bad)), bad

# 2. 個人の情報（メールアドレス・電話番号・郵便番号・名前や連絡先の欄）を落とす。全角はそろえてから見る
for pii in ({**OK, "motion_notes": "a.b@example.com まで"}, {**OK, "finish_notes": "０９０－１２３４－５６７８"},
            {**OK, "problems": [{"kind": "other", "step": None, "note": "〒123-4567 に住む"}]}, {**OK, "name": "山田"}):
    assert any(f.floor == "F12.pii" for f in fb.check(pii)), pii

# 2b. 日本語に続く番号・区切りの違う番号・どの欄（params・source_id・reported_at・困り事の余分な欄）にあっても落とす
for pii in ({**OK, "motion_notes": "電話090-1234-5678"}, {**OK, "motion_notes": "住所123-4567"}, {**OK, "motion_notes": "09012345678"},
            {**OK, "motion_notes": "090 1234 5678"}, {**OK, "motion_notes": "090.1234.5678"}, {**OK, "motion_notes": "(090)1234-5678"},
            {**OK, "motion_notes": "+81-90-1234-5678"}, {**OK, "motion_notes": "〒1234567"}, {**OK, "motion_notes": "090\u20101234\u20105678"},
            {**OK, "motion_notes": "090\u20131234\u20135678"}, {**OK, "motion_notes": "a\u200b@example.invalid"},
            {**OK, "source_id": "山田太郎 090-1234-5678"}, {**OK, "params": {"name": "山田", "tel": "090-1234-5678"}},
            {**OK, "reported_at": "a@example.invalid"}, {**OK, "problems": [{"kind": "fit", "step": 1, "note": "", "tel": "090-1234-5678"}]}):
    assert any(f.floor in ("F12.pii", "F12.report") for f in fb.check(pii)), pii
# 2b2. 区切りの違う番号・漢数字・前に数が付く番号・空白の郵便番号・崩したメール・連絡先の印も、文の欄で F12.pii で落とす
for t in ("090/1234/5678", "090・1234・5678", "090_1234_5678", "090,1234,5678", "090～1234～5678", "090の1234の5678",
          "〇九〇-一二三四-五六七八", "2.5 090 1234 5678", "手順3 03 1234 5678", "〒123 4567", "〒 123 4567", "1234567",
          "郵便123-4567.", "a @ example.invalid", "a@example . invalid", "a(at)example.invalid", "山田@例え.日本", "LINE: yamada_taro", "@yamada_taro",
          "https://x.com/yamada"):
    assert any(f.floor == "F12.pii" for f in fb.check({**OK, "motion_notes": t})), t
# 2b4. 3 回目のレビューのすり抜け。文の欄の数字の多い所・連絡先の語・@ は、書き方に関わらず落とす
for t in ("090 の 1234 の 5678 山田太郎", "090(携帯)1234-5678", "090、、、1234、、、5678", "090.1234-5678", "090-1234.5678",
          "090 12 34 56 78", "0 9 0 1 2 3 4 5 6 7 8", "123 - 4567", "123_4567", "123/4567", "〒 123 - 4567", "123.4567",
          "123-4567本町", "123-4567 本郷3丁目", "a at b dot jp", "a(at)b(dot)jp", "a@gmail", "メアドは yamada アット gmail",
          "LINE yamada", "Twitter: yamada", "インスタ yamada_taro", "x.com/yamada"):
    assert any(f.floor == "F12.pii" for f in fb.check({**OK, "motion_notes": t})), t
# 2b5. 欄をまたいで分けた番号・間を空けた番号・大字・長音を含む連絡先の語。工作の語「ライン」は落とさない
for bad in ({**OK, "motion_notes": "090-123", "finish_notes": "4-5678"},
            {**OK, "motion_notes": "〒123", "problems": [{"kind": "other", "step": None, "note": "4567"}]},
            {**OK, "motion_notes": "090-12" + "あ" * 20 + "34-56" + "い" * 20 + "78"},
            {**OK, "motion_notes": "零九零壱弐参四五六七八"}, {**OK, "motion_notes": "メールは yamada"},
            {**OK, "motion_notes": "ツイッターは yamada_taro"}):
    assert any(f.floor == "F12.pii" for f in fb.check(bad)), bad
for fine in ("折りラインがずれた", "カットラインが細い", "fold line が見えない"):
    assert not [f for f in fb.check({**OK, "motion_notes": fine}) if f.floor == "F12.pii"], fine
# 2b6. 数の欄で番号を運ばせない。手順の番号は 40 まで、寸法は雛形の範囲の中。見えない文字を挟んだ連絡先の語も落とす
for bad in ({**OK, "stuck_step": 9012345678}, {**OK, "problems": [{"kind": "fit", "step": 9012345678, "note": ""}]},
            {**OK, "stuck_step": 90}, {**OK, "params": {"vane_radius": 9012345678}}):
    assert any(f.floor == "F12.report" for f in fb.check(bad)), bad
assert any(f.floor == "F12.pii" for f in fb.check({**OK, "motion_notes": "メ\u200bール yamada_taro"}))
assert any(f.floor == "F12.report" for f in fb.check({**OK, "params": {"axle_d": 3.09012345678}}))  # 小数の後ろで番号を運ばせない
assert fb.check({**OK, "params": {"axle_d": 3.5}}) == []
for t in ("メ\ufe0fール yamada", "メ\u0301ール yamada", "メ ール yamada", "ラ イ ン yamada_taro"):
    assert any(f.floor == "F12.pii" for f in fb.check({**OK, "motion_notes": t})), t
assert not [f for f in fb.check({**OK, "motion_notes": "fold line 3mm が見えない"}) if f.floor == "F12.pii"]
# 2b3. 決まった形の欄も、値を絞る（自由な文を入れさせない）。深い入れ子は落ちずに F12.report
for bad in ({**OK, "params": {"kind": "山田太郎 横浜市"}}, {**OK, "source_id": "NDL-1-R1-L-yamada_taro"},
            {**OK, "reported_at": "9999-99-99"}):
    assert any(f.floor == "F12.report" for f in fb.check(bad)), bad
deep = []
for _ in range(3000):
    deep = [deep]
assert any(f.floor == "F12.report" for f in fb.check({**OK, "params": {"radius": deep}}))
# 2c. 普通の寸法・日付・記号・小数の並び・範囲は落とさない
# 数字の多い所（近くに 7 桁以上）は、寸法でも落とす（番号との見分けは式ではつかないので、安全の側に倒す。知らせで「番号は書かない」と言う）。
# 次は数字が少なく、落とさない
for fine in ("12-34mm", "羽 8 枚・半径 46mm", "0.5mm の紙で 3 回折った", "手順 4 で止まった", "2 回目で回った", "息で 10 秒回った"):
    assert not [f for f in fb.check({**OK, "motion_notes": fine}) if f.floor == "F12.pii"], fine
# 2d. 型の崩れた入力でも落ちずに F12.report を返す。落とした報告の値は知らせに出さない
for broken in ({**OK, "template": ["spinner"]}, {**OK, "problems": [{"kind": ["fit"]}]}, {**OK, "template": "a@example.invalid"},
               {**OK, "params": "x"}, {**OK, "motion_notes": 3}):
    fl = fb.check(broken)
    assert fl and "a@example.invalid" not in " ".join(f.line() for f in fl), broken

# 3. 集めると、雛形・形ごとに動いた割合・仕上がりの点・多い困り事（手順つき）・直しの行き先が出る
reports = [OK, {**OK, "moved": "moved", "finish": 5, "problems": []},
           {**OK, "moved": "not", "finish": 2, "problems": [{"kind": "fit", "step": 4, "note": "擦れて回らない"},
                                                            {"kind": "glue", "step": 2, "note": "糊代が小さい"}]},
           {"template": "balance", "form": "okiagari", "built": True, "moved": "moved", "finish": 4}]
s = fb.summarize(reports)
pw = s[("spinner", "pinwheel")]
assert pw["n"] == 3 and pw["moved"] == {"moved": 1, "partly": 1, "not": 1}, pw
scores = [3, 5, 2]  # 3 つの報告の仕上がりの点
assert abs(pw["finish_mean"] - sum(scores) / len(scores)) < 1e-9
assert pw["problems"][0]["kind"] == "fit" and pw["problems"][0]["count"] == 2 and pw["problems"][0]["steps"] == {4: 2}
assert "F5.spin" in pw["problems"][0]["target"], pw["problems"][0]["target"]
assert s[("balance", "okiagari")]["n"] == 1
# 直しは人が採る。案は型紙や寸法を書き換えない（案の中に寸法の新しい値を持たない）
assert all("new_value" not in p for p in pw["problems"])

# 4. 入口: check は 0 / 3、summarize は形の誤りや個人の情報のある報告を数えずに知らせる
with tempfile.TemporaryDirectory() as d:
    good, bad = pathlib.Path(d, "r1.json"), pathlib.Path(d, "r2.json")
    good.write_text(json.dumps({**OK, "reviewed_at": "2026-11-05T10:00:00+09:00"}, ensure_ascii=False), encoding="utf-8")
    bad.write_text(json.dumps({**OK, "motion_notes": "x@example.invalid"}, ensure_ascii=False), encoding="utf-8")
    run = lambda *a: subprocess.run([sys.executable, "-m", "omochae.feedback", *a], cwd=ROOT, capture_output=True, text=True,
                                    env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
    assert run("check", str(good)).returncode == 0
    r = run("check", str(bad))
    assert r.returncode == 3 and "F12.pii" in r.stderr, r.stderr
    r = run("summarize", d)
    assert r.returncode == 0 and "spinner" in r.stdout and "r2.json" in r.stderr, (r.stdout, r.stderr)
    assert "x@example.invalid" not in r.stdout + r.stderr  # 落とした報告の中身を出し直さない
    leak = pathlib.Path(d, "r3.json")
    leak.write_text(json.dumps({**OK, "template": "z@example.invalid"}), encoding="utf-8")
    r = run("check", str(leak))
    assert r.returncode == 3 and "z@example.invalid" not in r.stderr, r.stderr  # check も値を出し直さない
    pathlib.Path(d, "r4.json").write_text(json.dumps({**OK, "template": ["x"]}), encoding="utf-8")
    r = run("summarize", d)
    assert r.returncode == 0 and "spinner" in r.stdout, r.stderr  # 型の崩れた 1 つで集計が止まらない

# 5. 雛形を足したら、直しの行き先の床（FLOORS）にも足す。漏れると、その雛形の案が「族の床」としか言えない
from omochae.compose import TEMPLATES
# 雛形に無い行も残さない（main に無い雛形の行があっても気づけなかった）
assert set(TEMPLATES) == set(fb.FLOORS), sorted(set(TEMPLATES) ^ set(fb.FLOORS))
# 例の報告（examples/reports/spinner_pinwheel.json）は通る
assert fb.check(json.loads((ROOT / "examples/reports/spinner_pinwheel.json").read_text(encoding="utf-8"))) == []

# 6. 作る様子の欄（#23）: どの手順で止まったか・やめたか・かかった時間。型紙の外の行き先（案内・聞く口・サイトの流れ）
MK = {**OK, "stuck_step": 4, "gave_up": False, "minutes": 35,
      "problems": [{"kind": "guide", "step": 4, "note": "折る向きの説明が分からなかった"},
                   {"kind": "answer", "step": None, "note": "聞く口の答えが長かった"}]}
assert fb.check(MK) == [], [f.line() for f in fb.check(MK)]
for bad in ({**MK, "stuck_step": 0}, {**MK, "gave_up": "no"}, {**MK, "minutes": 0}, {**MK, "minutes": 9999}):
    assert any(f.floor == "F12.report" for f in fb.check(bad)), bad
sv = fb.service_summary([MK, {**MK, "stuck_step": 4, "gave_up": True, "minutes": 60},
                         {**OK, "template": "balance", "form": "okiagari", "problems": [{"kind": "site", "step": None, "note": "送る所が分かりにくい"}]}])
assert sv["n"] == 3 and sv["gave_up"] == 1 and sv["stuck"][("spinner", "pinwheel", 4)] == 2, sv
assert [k["kind"] for k in sv["problems"]] == ["guide", "answer", "site"] or {k["kind"] for k in sv["problems"]} == {"guide", "answer", "site"}
assert sv["minutes"]["median"] == 47.5, sv["minutes"]
# サービスの困り事は、雛形の集計に混ぜない（型紙の直しの行き先と分ける）
assert all(p["kind"] not in fb.SERVICE_KINDS for p in fb.summarize([MK])[("spinner", "pinwheel")]["problems"])

# 7. 工作の語（折りライン・部品ID・fold line・red dot）は連絡先と見ない。ID・LINE・メールは、ID らしい形が続く時だけ当てる
for fine in ("折りライン2.5mmずれた", "部品のIDが分からない", "出典IDを確かめた", "fold line bent", "line them up", "good ideas", "Line A1", "line a_", "line _ red mark", "LINE is bent", "LINE A1 is a part mark",
             "look at the red dot", "カットラインが細い"):
    assert not fb.has_pii(fine), fine
for text in ("email me", "LINE ID: taro_123", "ライン:taro123", "ラインID taro123", "id:taro99", "taro at gmail dot com",
             "LINE ID は taro_123", "LINEのIDはtaro_123", "ID は taro_123", "ラインのIDはtaro_123",
             "name at " + "x" * 50 + " dot com", "Line taro_123", "LiNe taro_123", "Line _taro",
             "use Line _taro", "LINE yamada"):
    assert fb.has_pii(text), text
# 長すぎる文・多すぎる葉は、連絡先の式を当てる前に落とす（長い文で式が 2 乗の時間をかけ、幅の広い list で止められた）。
# 時間の秒数は機械に依るので見ない。式（has_pii）が 1 度も呼ばれない事で、先に断った事を見る
real = fb.has_pii
def _no_call(_t):
    raise AssertionError("上限を越えた報告に連絡先の式を当てた")
fb.has_pii = _no_call
try:
    for big in ({**OK, "motion_notes": "a" * 19000}, {**OK, "problems": [{"kind": "fit", "note": "a"}] * 100000},
                {**OK, "problems": [0] * 100000}, {**OK, "finish_notes": "あ" * 600, "motion_notes": "あ" * 600,
                                                    "problems": [{"kind": "fit", "note": "あ" * 300}] * 10},
                {**OK, **{f"k{i}": 0 for i in range(100000)}}):
        assert [f.floor for f in fb.check(big)] == ["F12.report"], [f.line() for f in fb.check(big)][:3]
finally:
    fb.has_pii = real
# 困り事が list でなくても例外にせず落とす
assert any(f.floor == "F12.report" and "problems" in f.line() for f in fb.check({**OK, "problems": 1}))
assert any("problems[0].note" in f.line() for f in fb.check({**OK, "problems": [{"kind": "fit", "note": "あ" * 301}]}))
assert fb.check({**OK, "problems": [{"kind": "fit", "note": "あ" * 300}]}) == []

# 8. メモは信用しない文。改行と記号は、まとめに 1 行の字として出す（見出しの行や HTML のタグを差し込めた）
NASTY = "擦れた\n\n# 見出し\r\n<script>alert(1)</script>\u2028## 次\x1b[31m **太** [字](x) `c` | _y_ & \\"
for bad_note in ({"kind": "fit", "step": 4, "note": NASTY}, {"kind": "guide", "step": 4, "note": NASTY}):
    r8 = {**OK, "problems": [bad_note]}
    assert fb.check(r8) == [], [f.line() for f in fb.check(r8)]
    md = fb._markdown(fb.summarize([r8])) + "\n" + fb._service_markdown(fb.service_summary([r8]))
    plain = {**r8, "problems": [{**bad_note, "note": "擦れた"}]}
    md_plain = fb._markdown(fb.summarize([plain])) + "\n" + fb._service_markdown(fb.service_summary([plain]))
    assert md.count("\n") == md_plain.count("\n"), md  # 行が増えない
    assert not any(c in md for c in ("\r", "\x1b", "\u2028")), repr(md)  # 見えない文字も残さない
    line = next(ln for ln in md.splitlines() if "擦れた" in ln)
    assert line.startswith("  - 「") and line.endswith("」"), line
    # 字は残して読めるようにし、記号は無効にする
    assert "<script>" not in md and "&lt;script&gt;" in line and "見出し" in line, line
    for raw, safe in (("**", r"\*\*"), ("[字]", r"\[字\]"), ("`c`", r"\`c\`"), ("|", r"\|"), ("_y_", r"\_y\_"), ("&", "&amp;")):
        assert safe in line, (raw, line)
    # JSON の形でも、メモは 1 行にする（記号の無効化は Markdown の出す時だけ。JSON は JSON の決まりで守られる）
    notes = [n for g in fb.summarize([r8]).values() for pr in g["problems"] for n in pr["notes"]] \
        + [n for pr in fb.service_summary([r8])["problems"] for n in pr["notes"]]
    assert notes and all(not any(c in n for c in "\n\r\x1b\u2028") for n in notes) and all("<script>" in n for n in notes), notes

# 9. まとめは、人が受け入れた報告（reviewed_at がある）だけを数える。受付箱を直に指しても、読まれていない文を出さない
with tempfile.TemporaryDirectory() as d:
    pathlib.Path(d, "unread.json").write_text(json.dumps({**OK, "problems": [{"kind": "fit", "step": 4, "note": "山田といいます"}]}, ensure_ascii=False), encoding="utf-8")
    pathlib.Path(d, "read.json").write_text(json.dumps({**OK, "reviewed_at": "2026-11-05T10:00:00+09:00"}, ensure_ascii=False), encoding="utf-8")
    r = run("summarize", d)
    assert r.returncode == 0 and "unread.json" in r.stderr and "山田" not in r.stdout + r.stderr, (r.stdout, r.stderr)
    assert "報告 1 件" in r.stdout and "read.json" not in r.stderr.replace("unread.json", ""), (r.stdout, r.stderr)
    # 決まりの外の値の印は、印にならない
    pathlib.Path(d, "forged.json").write_text(json.dumps({**OK, "reviewed_at": "はい"}, ensure_ascii=False), encoding="utf-8")
    r = run("summarize", d)
    assert "forged.json" in r.stderr and "報告 1 件" in r.stdout, (r.stdout, r.stderr)
# 例の報告は、README のとおりにまとめられる
r = run("summarize", "examples/reports")
assert r.returncode == 0 and "報告 1 件" in r.stdout and r.stderr == "", (r.stdout, r.stderr)

# 10. 本物の報告の置き場は git の外。この repo で追跡する examples/reports に本物を置かない
from omochae import intake
assert intake.BASE.relative_to(ROOT).parts[0] == "local"
assert "local/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

# 11. 命令の間違った呼び方は rc 4（2 は使わない）
for wrong in ((), ("nope",), ("check",), ("summarize",), ("check", "a", "b"), ("summarize", "a", "--nope")):
    r = run(*wrong)
    assert r.returncode == 4, (wrong, r.returncode, r.stderr)

# 上限の中の文でも、連絡先の式が止まらない（#31）。上限で断るだけでは、「LINE + 空白」の様な文で式が 3 乗の時間をかけ、1 欄 1 秒を越えた。
# 秒数は機械に依るので、数回の中で一番速い時間を見て、混んだ機械の揺れで落ちないようにする
def _fastest(f, *a):
    best = None
    for _ in range(5):
        t0 = time.perf_counter()
        f(*a)
        best = min(best, time.perf_counter() - t0) if best is not None else time.perf_counter() - t0
    return best
_n = fb.MAX_TEXT
SLOW_SHAPES = ["LINE" + " " * (_n - 4), "line" + " " * (_n - 4), "ライン" + " " * (_n - 3), "LINE" + "\u3000" * (_n - 4),
               "line id" + " " * (_n - 7), "LINE の" + " " * (_n - 6), "a" * _n, "a-" * (_n // 2), "at " * (_n // 3),
               " " * (_n - 1) + "。", "(" + " " * (_n - 1), "1" * _n, "あ" * _n]
for text in SLOW_SHAPES:
    assert _fastest(fb.has_pii, text) < 0.1, text[:8]
    # 上限を越えて直に呼ばれても（束の入口の外の使い方）、2 乗や 3 乗に戻っていない事を、長い文で見る
    assert _fastest(fb.has_pii, (text * 34)[:20000]) < 1, text[:8]
for text in SLOW_SHAPES:
    wide = {**OK, "motion_notes": text, "finish_notes": text, "problems": [{"kind": "fit", "note": text[:fb.MAX_NOTE]}] * 3}
    assert _fastest(fb.check, wide) < 0.1, text[:8]
# 式の形を直しても、見方は変えない。空白の入れ方と語の組み合わせの全部で、当たる物は当たり、工作の語は当たらない
for sp in ("", " ", "   ", "\u3000"):
    for text in (f"LINE{sp}の{sp}ID{sp}は{sp}taro", f"LINE{sp}ID{sp}={sp}taro", f"LINE{sp}:{sp}taro", f"Line{sp}の{sp}id{sp}:{sp}taro_1",
                 f"ライン{sp}の{sp}id{sp}は{sp}taro", f"ライン{sp}id{sp}={sp}taro", f"line{sp}id{sp}:", f"line{sp}:", f"line{sp}id{sp}taro"):
        assert fb.has_pii(text), text
for text in ("taro.com", "my-toy.jp", "at the corner dot com", "at x dot jp", "a@b", "taro (at) example", "090.1234.5678"):
    assert fb.has_pii(text), text
# 続けて書いた印も、前の印が読んだ空白に関わらず全部そろえる
assert fb._norm("A1[ at ]  (at) b") == "A1@@b" and fb._norm("a @  @ b") == "a@@b" and fb._norm("1.2.3 4.5.6") == "1-2-3 4-5-6"
for text in ("折りライン2.5mm", "fold line bent", "LINE is", "line them up", "look at the red dot", "dot com at", ".com", "1.5 と 2.5"):
    assert not fb.has_pii(text), text

print("ok")
