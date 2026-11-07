"""型紙とエンジンの改善の歴史の表を読む口（本人の言葉 11-07「どう改善が進むかは山場なのでデモにも載せたいところ。サイトにも記載したい」）。

表は型紙エンジン（paper-to-toy）の記録から作った物で、grove の state/history の kaizen-history.json を data/history/kaizen-history.json に写して持つ。
頁と README は版ごとの字を自分で書かず、この表の字を出す（設計 0.7 節「字の元は表だけ」）。表が出し直されたら copy で写し直す。

判断の芯:
- 並べる版は、表の最新ではなく、サイトが今刷っている組（雛形の SHEET_SET）まで。頁が刷る紙と、頁が「今の版」と言う紙を同じにするため
  （表にはサイトにまだ来ていない版も載る。11-07 の朝は御来迎 v11〜v14 がそうだった）。
- エンジンの今の版も、表の最新ではなく、サイトが今刷る組が結ぶエンジンの版の大きい方（設計の担当と合わせた 11-07）。
  サイトの紙が結ばないエンジンの版を「今」と言わないため。エンジンの版を刻んでいない型紙の版（御来迎 v13）は数に入れない。
- 写す時に外す欄は 3 つ。機械のパスの入る欄（strip。版の並びの絵の置き場）は、repo に個人のパスを入れない決まりのため。
  ワークショップの欄（workshops・workshops_source）は、11-06 の感想の中身のまとめに読める字があり、参加者の感想の要点は
  GitHub に入れない決まりに当たりうるので外す（窓口の決め 11-07 案 A）。版の行の sheet_pdf も外す（ROW_DROP）。ほかの欄は表のまま写す。
  出す形（indent 1・ensure_ascii なし・末尾に改行）は審査用の頁の写し（#518）とそろえ、どちらが先に入っても同じ字にする。
- 版ごとの紙の絵（刷った紙の 1 枚目を縮めた物）は生成物なので repo に入れない（画像は NDL と東京学芸大学の PDM の物だけの決まり）。
  out/history/ の下に置き、表の行の sheet_image（sheets/<組の名>.png）で引く。版の並びの絵（strip）は切らない（統括の決め 11-07。
  並びの配置が替わっても崩れないよう、エンジンが組ごとに 1 枚ずつ出した物を使う）。
- 置き場に絵が無い版は、repo の中から作る（本人の見直し 11-07 22:16「過去の版が表示されていない。」。repo の clone だけで動く公開の場は
  out/ が空なので、全部の額が空だった）。作れるのは 2 つ: 改善の輪より前の版は、刷って渡した紙の PDF（docs/process/trials/sheets/<組>/ の
  仮説 A の型紙。v1〜v4 は仮説 A に当たる tab の紙。エンジンが出した絵と同じ紙なのを 11-07 に絵の差で確かめた）の 1 枚目。今の組は、
  今の雛形でたたき台を刷った 1 枚目（サイトが今刷る紙と同じ）。間の版（御来迎 v11〜v13・虎 v4〜v6）はエンジンの repo の記録にしか無く、
  repo の中からは作れないので、頁は「この版の絵は残っていない」と出す（作り直した絵を、その版の紙として見せない）。
  作った絵は小さい写し（幅 298）にして out/history/sheets に置く（生成物なので repo に入れない決まりはそのまま）。作るのは絵が求められた時で、
  頁を返す時は作れるかだけを見る（頁を遅くしない）
"""
import contextlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading

from .compose import TEMPLATES
from .hypotheses import ROOT

PATH = ROOT / "data/history/kaizen-history.json"
PICTURES = ROOT / "out/history"
DROP = ("strip", "workshops", "workshops_source")
# 版の行ごとに外す欄。sheet_pdf は刷った PDF の Drive の置き場で、フォルダの名の日時の番号が push の門の痕跡の見張りに当たる（設計の担当と合わせた 11-07）
ROW_DROP = ("sheet_pdf",)
SET_NO = re.compile(r"-v(\d+)$")
# 表の行の絵の名は sheets/ の下の 1 枚だけを受ける。表の字から out/ の外のファイルを開かないため
IMAGE = re.compile(r"sheets/[a-z0-9-]+\.png")


def load(path=None):
    return json.loads(pathlib.Path(path or PATH).read_text(encoding="utf-8"))


def set_no(name):
    m = SET_NO.search(name or "")
    return int(m.group(1)) if m else None


def versions(template, data=None):
    """雛形の型紙の版の行を古い順に。サイトが今刷る組までで、今の組の行の now を真にする。表に雛形が無い時は空。"""
    data = data or load()
    toy = next((t for t in data["toys"] if t["template"] == template), None)
    if toy is None:
        return []
    now = TEMPLATES[template].SHEET_SET
    upto = set_no(now)
    rows = [v for v in toy["versions"] if set_no(v["set"]) is not None and set_no(v["set"]) <= upto]
    return [{**v, "now": v["set"] == now} for v in sorted(rows, key=lambda v: set_no(v["set"]))]


def toys(data=None):
    """表にある雛形ごとに (玩具の名, 雛形の名, 今の組の行)。今の組が表に無い雛形は行を None にする。"""
    data = data or load()
    out = []
    for t in data["toys"]:
        if t["template"] not in TEMPLATES:
            continue
        rows = versions(t["template"], data)
        out.append((t["toy"], t["template"], next((v for v in rows if v["now"]), None)))
    return out


def engine_now(data=None):
    """エンジンの今の版の行。サイトが今刷る組が結ぶエンジンの版の大きい方。どの組も結ばない時は None。"""
    data = data or load()
    nos = [row["engine_version"] for _, _, row in toys(data) if row and row.get("engine_version")]
    if not nos:
        return None
    return next((e for e in data["engine_versions"] if e["engine_version"] == max(nos)), None)


TRIAL_SHEETS = ROOT / "docs/process/trials/sheets"
THUMB_W = 298  # 額の小さい写しの幅（額は幅 596 の半分の大きさで並ぶ。2 倍の画面でもぼけすぎない所）
_build_lock = threading.Lock()


def _name(row):
    name = row.get("sheet_image") or ""
    return name if IMAGE.fullmatch(name) else None


def trial_pdf(set_name):
    """改善の輪より前の版の、刷って渡した型紙の PDF（仮説 A。v1〜v4 は仮説 A に当たる tab）。無い時は None。"""
    folder = TRIAL_SHEETS / set_name
    if not re.fullmatch(r"[a-z]+-v\d{1,3}", set_name or "") or not folder.is_dir():
        return None
    toy = set_name.split("-v")[0]
    for stem in (f"{toy}_H-A_v{set_no(set_name)}", f"{toy}_tab_v{set_no(set_name)}"):
        if (folder / f"{stem}.pdf").is_file():
            return folder / f"{stem}.pdf"
    return None


def _current_source(set_name):
    """今の組なら、その雛形で刷る玩具の出典の ID。今の組でない・玩具が見つからない時は None。"""
    for name, template, _row in toys():
        if TEMPLATES[template].SHEET_SET != set_name:
            continue
        for f in sorted((ROOT / "data/hypotheses").glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("toy") == name and d.get("template", "slider_fan") == template:
                return d["source_id"]
    return None


def can_picture(row):
    """額に絵を出せるか（置き場に在る・repo の中から作れる）。頁を返す時に見る（ここでは作らない）。"""
    name = _name(row)
    if name is None:
        return False
    set_name = name[len("sheets/"):-len(".png")]
    return (PICTURES / name).is_file() or trial_pdf(set_name) is not None or _current_source(set_name) is not None


def _thumb(pdf, dest):
    """PDF の 1 枚目を幅 THUMB_W の PNG にして dest に置く（一時のファイルから置き換える）。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d) / "p"
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-singlefile", "-png", "-scale-to-x", str(THUMB_W), "-scale-to-y", "-1",
                        str(pdf), str(base)], check=True, capture_output=True, timeout=60)
        tmp = dest.with_name(f".{dest.name}.tmp")
        shutil.copyfile(base.with_suffix(".png"), tmp)
        tmp.replace(dest)


def build_picture(set_name):
    """repo の中から版の絵を作って置き場に置く。作れた時はパス、作れない時は None。"""
    dest = PICTURES / "sheets" / f"{set_name}.png"
    pdf = trial_pdf(set_name)
    sid = None if pdf else _current_source(set_name)
    if pdf is None and sid is None:
        return None
    with _build_lock:  # 同じ絵を同時に 2 度作らない（額が並ぶ頁は絵を一度に求める）
        if dest.is_file():
            return dest
        try:
            if pdf is not None:
                _thumb(pdf, dest)
            else:
                from . import hypotheses
                data = hypotheses.load(sid)
                with tempfile.TemporaryDirectory() as d:
                    out = pathlib.Path(d) / "sheet.pdf"
                    with contextlib.redirect_stdout(io.StringIO()):  # 刷った一時の置き場のパスを、サーバの出力に出さない
                        rc = hypotheses.print_sheet(sid, hypotheses.sheet_id(data), str(out))
                    if rc != 0 or not out.is_file():
                        return None
                    _thumb(out, dest)
        except (OSError, subprocess.SubprocessError):
            return None
    return dest


def picture(row):
    """版の行の紙の絵のパス。置き場に無ければ repo の中から作る。作れない・名が決まりの外の時は None。"""
    name = _name(row)
    if name is None:
        return None
    path = PICTURES / name
    if path.is_file():
        return path
    return build_picture(name[len("sheets/"):-len(".png")])


def copy(src):
    """表を data/history に写し、表と同じ所の sheets/ の絵を out/history/sheets に置く。返すのは (写した表, 置いた絵の数)。"""
    src = pathlib.Path(src)
    data = load(src)
    kept = {k: v for k, v in data.items() if k not in DROP}
    for t in kept.get("toys", []):
        t["versions"] = [{k: v for k, v in row.items() if k not in ROW_DROP} for row in t["versions"]]
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(kept, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    placed = 0
    for t in kept["toys"]:
        for v in t["versions"]:
            name = v.get("sheet_image") or ""
            if IMAGE.fullmatch(name) and (src.parent / name).is_file():
                (PICTURES / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src.parent / name, PICTURES / name)
                placed += 1
    return kept, placed


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] != "copy":
        print("使い方: python -m omochae.kaizen_history copy <表の json>（終了: 0 写した / 4 写せない）", file=sys.stderr)
        return 4
    try:
        kept, placed = copy(argv[1])
    except (OSError, ValueError, KeyError) as e:
        print(f"写せない: {e}", file=sys.stderr)
        return 4
    rows = sum(len(t["versions"]) for t in kept["toys"])
    print(f"写した: 表（{kept.get('made_at', '')}・型紙の版 {rows} 行・エンジンの版 {len(kept['engine_versions'])} 行）・紙の絵 {placed} 枚")
    return 0


if __name__ == "__main__":
    sys.exit(main())
