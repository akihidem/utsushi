"""再現ギャラリー（J-022 の 3、一覧の U-21）。試した記録 1 件を 1 枚にして、記録の順に並べた静的な頁を書き出す。

判断の芯（J-022）:
- 並べるのは記録の順。順位や「よく動いた順」にしない（J-025）。動かなかった・わからない記録も同じ大きさで並べる
- 見出しは「試した記録」。「再現できた」とは書かない（昔の玩具が再現されたかは測り切れない、philosophy.md）
- 載せるのは記録・人の説明・雛形の直しの台帳と、試行ごとに本人が載せると決めた写真と動画だけ。仮説の動き方の文は載せない
  （ギャラリーを先に見た人に答えを渡さないため。仮説は字と版だけで指す）
- 公開のサーバは作らない。手元で書き出し、repo の docs/gallery に置く
"""
import argparse
import html
import pathlib
import sys

from . import loop, records
from .hypotheses import letter, load

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 試行ごとの写真と動画。本人の決定で repo に載せた物だけ（U-09）。どの仮説の物かは分からないので、試行の単位で添える。
TRIAL_MEDIA = {"2026-11-04": {"dir": "docs/process/trials/photos/20261104", "photos": ["p01.jpg", "p07.jpg", "p09.jpg"], "video": "goraigo-motion.mp4",
                              "note": "成人 5 人の実作の試行（記録の全体は docs/process/trials/README.md）。写真と動画がどの仮説の紙かは分からない"}}

STYLE = """body{margin:0;background:#f6f3ec;color:#2b2722;font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif}
main{max-width:1100px;margin:0 auto;padding:8vh 5vw}h1{font-weight:400;letter-spacing:.4em;font-size:34px;margin:0 0 6px}
.lead{color:#5d554a;font-size:14px;line-height:2;letter-spacing:.06em}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:28px;margin-top:40px}
.card{background:#fbf9f4;border:1px solid #d8cdb6;padding:22px 24px;box-shadow:0 18px 30px -24px rgba(70,55,35,.4)}
.card h2{font-weight:400;font-size:18px;letter-spacing:.2em;margin:0 0 12px}.meta{font-size:12px;color:#8b8172;letter-spacing:.08em;line-height:1.9}
.res{display:inline-block;border:1px solid #b9a982;padding:2px 12px;margin:6px 0 10px;letter-spacing:.2em}
.card p{font-size:14px;line-height:1.9}.media{margin-top:48px}.media .row{display:flex;gap:16px;flex-wrap:wrap}
.media img,.media video{height:220px;max-width:100%;border:1px solid #d8cdb6;background:#fff}
.chg{margin-top:48px}.chg li{font-size:14px;line-height:1.9}"""


def esc(s):
    return html.escape(str(s or ""), quote=True)


def card(rec, data):
    h = next((x for x in data["hypotheses"] if x["id"] == rec["hypothesis_id"]), None)
    who = f"仮説 {letter(h)}" if h else esc(rec["hypothesis_id"])
    told = loop.explanation(rec["id"])
    # 取り下げた説明は字が空になるので、空の欄を並べない。
    body = ((f'<p><b>説明</b>（{esc(told["by"])}）: {esc(told["text"])}</p>' if told.get("text") else "") + (f'<p><b>次の思いつき</b>: {esc(told["next_idea"])}</p>' if told.get("next_idea") else "") if told
            else '<p class="meta">人の説明はまだ無い</p>')
    sheet = esc(rec.get("sheet_set") or f'版 {rec.get("sheet_version", 1)}')
    when = esc(rec.get("tried_on") or rec.get("recorded_at", "")[:10])
    return (f'<article class="card" id="{esc(rec["id"])}"><h2>{esc(data["toy"])} {who}</h2>'
            f'<p class="meta">{esc(rec["id"])}・試した日 {when}・紙 {sheet}</p><span class="res">{esc(rec["result"])}</span>{body}</article>')


def build(base=""):
    """頁の HTML を返す。base は写真と動画への相対の道の頭（docs/gallery から見て ../../）。"""
    recs = records.all_records()
    cards = "".join(card(r, load(r["source_id"])) for r in recs) or '<p class="meta">試した記録はまだ無い</p>'
    media = ""
    for day in sorted({r.get("tried_on") for r in recs if r.get("tried_on") in TRIAL_MEDIA}):
        m = TRIAL_MEDIA[day]
        imgs = "".join(f'<img src="{base}{m["dir"]}/{p}" alt="試行の写真 {p}">' for p in m["photos"])
        vid = f'<video src="{base}{m["dir"]}/{m["video"]}" controls muted playsinline></video>' if m.get("video") else ""
        media += f'<section class="media"><h2 class="meta">{esc(day)} の試行の写真と動画</h2><p class="meta">{esc(m["note"])}</p><div class="row">{imgs}{vid}</div></section>'
    chg = "".join(f'<li>{esc(t["id"])}（{esc(t["sheet_set"])}、{esc(t["adopted_by"])}が採った。根拠 {esc("・".join(t["record_ids"]))}）: {esc("／".join(t["changes"]))}</li>'
                  for t in loop.template_changes())
    chg = f'<section class="chg"><h2 class="meta">記録から次の版へ（雛形の直し）</h2><ul>{chg}</ul></section>' if chg else ""
    return ('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>うつし · 試した記録</title><style>{STYLE}</style><main><h1>試した記録</h1>'
            '<p class="lead">紙の型紙で作って試した記録を、記録の順に並べます。並びに上下はありません。動かなかった記録も、わからなかった記録も同じ大きさです。'
            '紙で動いても、昔の作り方の証明にはなりません。</p>'
            f'<div class="cards">{cards}</div>{media}{chg}</main></html>\n')


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.gallery", description="記録から再現ギャラリー（試した記録）の静的な頁を書き出す")
    ap.add_argument("--out", default=str(ROOT / "docs/gallery/index.html"))
    args = ap.parse_args(argv)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    base = "../../" if out.resolve().parent == (ROOT / "docs/gallery").resolve() else ""
    out.write_text(build(base), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
