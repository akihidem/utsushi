"""凍結の床を試験で見る: 必須の 2 種（御来迎 goraigo-v10・張子の首振り虎 tora-v3）の紙が、控えた指紋と同じ（U-43、#115）。
虎は次の組（tora-v4）に上げたので、前の組 tora-v3 も今の組 tora-v4 も比べる。前の組の控えは、次の組を足した後も残す（本人の指示）。
御来迎は今の組 goraigo-v10 のまま（次の組は形を見直してから。雛形に FROZEN_SET が無いので今の組だけを組む）。

なぜ要るか: 型紙の洗練（U-43）は、必須 2 種の今の版を変えず、次の版として足す決まり。今までは取り込みのたびに
指紋を手で比べていて、比べる道具が repo に無かった（関門の帳面の記録）。手で比べる形は、比べ忘れた回に床が黙って崩れる。

何の指紋か: 必須 2 種のたたき台（記録の欄 "sheet"、どちらも H-A）の版 1 の、型紙・手順の紙（原図の有り無し）・試した後の紙と、
玩具ごとの先生の見る紙。刷る SVG の SHA-256。
前は 8 仮説の全部（31 枚）を見ていた。本人の決定（11-05、#332 の点 3、J-032）「型紙はおもちゃ一個につき一個」で、今の組を
H-A の 1 枚にそろえたので、H-A 以外の仮説の紙（御来迎 H-B〜H-E・虎 H-B〜H-C の 22 枚）は照合から外した。
外した紙の指紋は控えの "removed" に残し、比べない（何を外したかが後から読めるように）。H-A の紙と先生の紙の指紋は変えていない。
配置でなく SVG にしたのは、線の太さや折り線を刷るかのような、描く側（render.py）の変更も紙を変えるため。
PDF にしないのは、PDF が作った時刻と機械の字の埋め込みで揺れるため。

指紋は 2 通り控える。
- real: この機械の字（Noto Serif CJK JP）で測った配置。刷る紙そのもの。字の版が控えた時と違う機械では比べられない
- standin: 字の幅を決まった値に置き換えた配置。字の版に依らず、どの機械でも比べる
字の版が違う機械で real が合わない事を、床の崩れと読み違えないために分けた。どちらも通るコードは同じなので、
コードと data の変更は standin だけでも見つかる。

控えを書き換える口は作らない。`--add` は、控えに無い紙を足すだけ。次の版（goraigo-v11・tora-v4）を足す時は、
今の版を刷れる道を残したまま、新しい紙を `--add` で足す。今の版の指紋を変える時は tests/floor_pin.json を手で直し、
理由を commit に書く（tests/frozen と同じ扱い）。

使い方（PYTHONPATH=src で）: `python tests/test_floor_pin.py`（比べる。./run.sh も回す）/ `--add`（無い紙を足す）/
`--dump <置き場>`（比べる SVG を書き出す。指紋が変わった時に、直す前と後の commit で書き出して diff を取るため）。
"""
import hashlib
import json
import pathlib
import re
import sys
import tempfile

from PIL import Image

from omochae import marks, textfit
from omochae.compose import TEMPLATES, compose
from omochae.hypotheses import ROOT, letter
from omochae.instructions import compose_after, compose_sheet, compose_teacher
from omochae.render import to_svg

PIN = pathlib.Path(__file__).with_name("floor_pin.json")
# 必須の 2 種。玩具を増やす線は記録に stage "試作" を書くので、ここには足さない（床は必須 2 種の完成）。
REQUIRED = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")
# 字の版を見分ける文字。和文は全角で版に依らず、版で変わりうるのは欧文と数字と約物の幅。
PROBE = "".join(chr(c) for c in range(0x20, 0x7F)) + "あア一、。「」（）・ー〔〕"


class _Standin:
    """字の幅の代わり。cmap と hmtx の両方の役をする（欧文は半角、ほかは全角）。"""

    def get(self, cp):
        return cp

    def __getitem__(self, cp):
        return (500 if cp < 0x2000 else 1000, 0)


def font_mark():
    """この機械の字の印。控えた時と同じなら、real の指紋を比べられる。"""
    cmap, hmtx, upem = textfit._font()
    adv = [hmtx[cmap[ord(ch)]][0] if cmap.get(ord(ch)) else None for ch in PROBE]
    return hashlib.sha256(json.dumps([upem, adv]).encode()).hexdigest()[:16]


def _num(m):
    v = round(float(m.group()), 3)
    return repr(v + 0.0)  # -0.0 を 0.0 にそろえる


def normalize(svg):
    """機械で揺れる所だけを落とす: 小数の末尾の桁（三角関数と交点の計算）と、原図の写しの中身（JPEG の作り方）。"""
    svg = re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,(略)", svg)
    return re.sub(r"-?\d+\.\d+(?:e-?\d+)?", _num, svg)


def papers(picture, strict):
    """必須 2 種の紙を {名前: 比べる SVG} で返す。strict の時は、検査に落ちる紙があれば止める（床は刷れる事を含む）。"""
    out = {}

    def put(name, layout, failures):
        assert layout is not None, (name, [f.line() for f in failures])
        assert not (strict and failures), (name, [f.line() for f in failures])
        out[name] = normalize(to_svg(layout))

    for sid in REQUIRED:
        # 記録を直接読む。hypotheses.load は人が採った新しい仮説を data/loop から重ねるので、機械ごとに紙の数が変わる。
        data = json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8"))
        source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
        tpl = TEMPLATES[data.get("template", "slider_fan")]
        now = tpl.SHEET_SET
        # 前の組がある雛形（FROZEN_SET を持つ。今は虎）は、雛形の組を前の名前に置いて組む（前の版を刷れる道）。印の文も前の文のまま
        # （#318 で本人が「今の版の紙は変えず、次の版から」と確かめた）。前の組の無い雛形（御来迎）は今の組だけ
        sets = ([(tpl.FROZEN_SET, {**source, "hypothesis_mark": marks.HYPOTHESIS_FROZEN})] if hasattr(tpl, "FROZEN_SET") else []) + [(now, source)]
        for sheet_set, src in sets:
            tpl.SHEET_SET = sheet_set
            try:
                # たたき台の 1 枚だけ（J-032）。ほかの仮説の紙は今の組で刷らないので、床でもない。
                for h in [h for h in data["hypotheses"] if h["id"] == data["sheet"]]:
                    tid = h.get("template") or data.get("template", "slider_fan")
                    base = f"{sheet_set}/{h['id']}"
                    name = f"仮説 {letter(h)}「{h['name']}」"
                    # 題と呼び方は hypotheses.print_sheet と同じ（版 1）。
                    _, layout, failures = compose(tid, h["params"], src, "A4", 1, f"{data['toy']} 型紙 {name}版 1")
                    put(f"{base}/型紙", layout, failures)
                    put(f"{base}/手順の紙", *compose_sheet(tid, h["params"], src, f"{name} 版 1", h["how_it_moves"]))
                    if tid == "slider_fan":  # 原図の写しを載せる道（goraigo-v8 から）。刷った組はこちら
                        put(f"{base}/手順の紙（原図つき）", *compose_sheet(tid, h["params"], src, f"{name} 版 1", h["how_it_moves"], picture=picture))
                    put(f"{base}/試した後の紙", *compose_after(src, name, data["after_try"], sheet_set=sheet_set))
                put(f"{sheet_set}/先生の見る紙", *compose_teacher(src, data["toy"], sheet_set=sheet_set))
            finally:
                tpl.SHEET_SET = now
    return out


def both(with_real=True):
    """(real の紙, standin の紙)。原図の写しは git の外なので、決まった大きさの代わりの絵で配置だけを見る。"""
    with tempfile.TemporaryDirectory() as tmp:
        picture = pathlib.Path(tmp) / "standin.jpg"
        Image.new("RGB", (300, 460), "#cccccc").save(picture)
        real = papers(picture, strict=True) if with_real else None
        keep = textfit._font
        textfit._font = lambda: (_Standin(), _Standin(), 1000)
        try:
            standin = papers(picture, strict=False)  # 代わりの字幅では、はみ出しの検査は当てにならない
        finally:
            textfit._font = keep
    return real, standin


def digest(svg):
    return hashlib.sha256(svg.encode("utf-8")).hexdigest()


def add():
    real, standin = both()
    pin = json.loads(PIN.read_text(encoding="utf-8")) if PIN.exists() else {"font": font_mark(), "papers": {}}
    if pin["font"] != font_mark():
        print("足せない: 字の版が控えた時と違う（real の指紋が混ざる）", file=sys.stderr)
        return 1
    new = [n for n in real if n not in pin["papers"]]
    for n in new:
        pin["papers"][n] = {"real": digest(real[n]), "standin": digest(standin[n])}
        print("足した", n)
    PIN.write_text(json.dumps(pin, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ok 足した紙 {len(new)} 枚、控え {len(pin['papers'])} 枚")
    return 0


def dump(folder):
    real, standin = both()
    for kind, got in (("real", real), ("standin", standin)):
        for n, svg in got.items():
            path = pathlib.Path(folder) / kind / (n.replace("/", "__") + ".svg")
            path.parent.mkdir(parents=True, exist_ok=True)
            # 1 行の SVG は diff が読めないので、要素ごとに行を分ける。
            path.write_text(svg.replace("><", ">\n<"), encoding="utf-8")
    print(f"ok {folder} に {2 * len(real)} 枚")
    return 0


def compare(pin, kind, got):
    """控えと比べて (刷れなくなった紙, 控えに無い紙, 変わった紙) を返す。"""
    gone = sorted(set(pin["papers"]) - set(got))
    extra = sorted(set(got) - set(pin["papers"]))
    diff = sorted(n for n, p in pin["papers"].items() if n in got and digest(got[n]) != p[kind])
    return gone, extra, diff


def check():
    pin = json.loads(PIN.read_text(encoding="utf-8"))
    real, standin = both()
    # たたき台 2 枚 × 3 枚 ＋ 御来迎の原図つき 1 枚 ＋ 先生の紙 2 枚。前の下限 31 は 8 仮説の時の数（J-032 で 9 に直した）
    # 虎の次の組の 4 枚を足して 13。前の下限は 9（J-032、1 組の時）・31（8 仮説の時）
    assert len(pin["papers"]) >= 13, ("控えが減った", len(pin["papers"]))
    assert len(pin["removed"]["papers"]) == 22 and not set(pin["removed"]["papers"]) & set(pin["papers"]), "外した紙は印つきで残し、比べる紙と混ぜない"
    assert "本人の決定" in pin["removed"]["why"], "外した理由の印を残す"
    gone, extra, diff = compare(pin, "standin", standin)
    assert not gone, ("控えた紙が刷れなくなった（凍結の床）。今の版を刷れる道を残し、直しは次の版として足す", gone)
    assert not extra, ("控えに無い紙がある。足すなら --add", extra)
    assert not diff, ("必須 2 種の今の版の紙が変わった（凍結の床）。直しは次の版として足す。差は --dump で見る", diff)
    same_font = pin["font"] == font_mark()
    if same_font:
        diff = compare(pin, "real", real)[2]
        assert not diff, ("必須 2 種の今の版の紙が変わった（凍結の床、この機械の字での配置）。差は --dump で見る", diff)

    # 負の対照: 指紋が紙の変化を拾う事を、3 つの向きで確かめる（拾わない指紋は、同じと言っても意味が無い）。
    def broken(patch, undo):
        patch()
        try:
            return compare(pin, "standin", both(with_real=False)[1])
        finally:
            undo()

    fan, tiger = TEMPLATES["slider_fan"], TEMPLATES["pivot_counterweight"]
    now = fan.SHEET_SET
    goraigo = sorted(n for n in pin["papers"] if n.startswith(f"{now}/"))
    # 1. 寸法: 御来迎の扇の折り幅の既定を変える。既定に頼る仮説の型紙が変わり、虎は変わらない
    old = fan.DEFAULTS["fold_width"]
    gone, extra, diff1 = broken(lambda: fan.DEFAULTS.update(fold_width=old - 1), lambda: fan.DEFAULTS.update(fold_width=old))
    assert not gone and not extra and any(n.endswith("/型紙") for n in diff1) and set(diff1) <= set(goraigo), ("寸法", gone, extra, diff1)
    # 2. 組の版の名前だけを上げる（今の版を直接直す形。U-43 で採らなかった代案）。御来迎の今の版が 1 枚も刷れなくなる
    gone2, extra, diff = broken(lambda: setattr(fan, "SHEET_SET", "goraigo-v11"), lambda: setattr(fan, "SHEET_SET", now))
    assert gone2 == goraigo and len(extra) == len(goraigo) and not diff, ("組の版", gone2, extra, diff)
    # 3. 組み方の文: 虎の手順を 1 つ足す。虎の手順の紙だけが変わり、型紙は変わらない
    steps = tiger.steps
    gone, extra, diff3 = broken(lambda: setattr(tiger, "steps", lambda p: steps(p) + ["足した手順"]), lambda: setattr(tiger, "steps", steps))
    # 前の組（tora-v3）の手順も同じ steps から作るので、虎の両方の組の手順の紙が変わる
    assert not gone and not extra and diff3 == sorted(n for n in pin["papers"] if n.startswith("tora-") and n.endswith("/手順の紙")), ("組み方の文", gone, extra, diff3)
    # 4. 虎の前の組の見分けを外す（次の組の直しが前の組の紙に漏れる形）。前の組の紙が変わり、次の組の紙は変わらない
    was = tiger.frozen
    gone, extra, diff4 = broken(lambda: setattr(tiger, "frozen", lambda: False), lambda: setattr(tiger, "frozen", was))
    assert not gone and not extra and f"{tiger.FROZEN_SET}/H-A/型紙" in diff4 and not any(n.startswith(f"{tiger.SHEET_SET}/") for n in diff4), ("前の組の見分け", gone, extra, diff4)
    note = "" if same_font else "。字の版が控えた時と違うので、この機械の字での配置（real）は比べていない"
    print(f"ok 紙 {len(standin)} 枚の指紋が控えと同じ。負の対照で拾った紙: 寸法 {len(diff1)}・組の版 {len(gone2)}・組み方の文 {len(diff3)}・前の組の見分け {len(diff4)}{note}")
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["--add"]:
        sys.exit(add())
    if sys.argv[1:2] == ["--dump"] and len(sys.argv) == 3:
        sys.exit(dump(sys.argv[2]))
    sys.exit(check())
