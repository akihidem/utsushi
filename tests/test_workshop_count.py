"""ワークショップの回数の数え方（本人の言葉 11-07「ワークショップ 4 回は 11 月 4・5・6・7 日でよい。回数の数え方と改善の歴史の表はこの 4 回で
そろえてください」）。README と CLAUDE.md の、回数を出す所を見る。

見る事:
1. 30 秒の要約（README と CLAUDE.md の 2 か所。同じ字である事は omochae.ledger の L.summary が見る）が「ワークショップは 4 回（11 月 4・5・6・7 日）」で、
   前の「実物の試行は 1 回」の数え方が残っていない
2. 回は日付で呼び、「何回目」と言わない。前の記録は 11-06 を「2 回目」と呼ぶが、4 回を 11-04・05・06・07 と数えると 3 回目になり、
   数え方が食い違う（審査用の頁のワークショップの節と同じ決まり）
3. 11-04 の回の中身（卒業生 5 人・御来迎が動いた）と、前からの字「今の組の紙は実物で確かめていない」は消さずに残す
   （記録では、11-06 に刷ったのは前の組で、11-05・11-07 は動画の感想を受けた回。今の組を実物で試した記録は無い）
4. README の「できること」の見出しも 4 回の数え方
5. README の「データの扱い」: 人の記録は 4 回のワークショップをまとめた記録（本人の言葉 11-07）で、repo に在る物は写真と動画の置き場の日付と数のとおり。
   卒業生 5 人は 11-04 の参加者として書く
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
readme = (ROOT / "README.md").read_text(encoding="utf-8")
claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

for name, text in (("README.md", readme), ("CLAUDE.md", claude)):
    summary = next(l for l in text.splitlines() if l.startswith("- **今の状態**"))
    assert "ワークショップは 4 回（11 月 4・5・6・7 日）" in summary, (name, "4 回の数え方")
    assert "実物の試行は 1 回" not in text and "試行は 11-04 の 1 回" not in text, (name, "前の数え方が残る")
    assert "回目" not in summary, (name, "回は日付で呼ぶ")
    assert "11 月 4 日の回は本人の教え子の卒業生 5 人" in summary and "筒から扇を開いて動いた" in summary, (name, "11-04 の回の中身を残す")
    assert "今の組の紙は実物で確かめていない" in summary, (name, "前からの字を残す")

head = next(l for l in readme.splitlines() if l.startswith("## できること"))
assert "ワークショップは 11 月 4・5・6・7 日の 4 回" in head and "回目" not in head, head

# 5. データの扱い: 人の記録は 4 回のワークショップをまとめた記録（本人の言葉 11-07「11/4567のまとめた記録です」）。repo に在る物の書き方は、
# 写真と動画の置き場（docs/process/trials/photos/<日付>/）の日付と数のとおり（SECURITY.md の 11-04 と 11-06 の写真 43 枚と動画 1 本と同じ事実）。
# 卒業生 5 人は 11-04 の参加者なので、4 回の全部に広げて書かない
data = readme[readme.index("## データの扱い"):]
data = data[:data.index("\n## ")]
assert "11 月 4・5・6・7 日の 4 回のワークショップをまとめた記録" in data, data[:200]
dirs = sorted(p for p in (ROOT / "docs/process/trials/photos").iterdir() if p.is_dir())
assert dirs, "写真の置き場が無い"
photos = sum(1 for d in dirs for f in d.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png"))
videos = sum(1 for d in dirs for f in d.iterdir() if f.suffix.lower() in (".mp4", ".mov"))
dates = " と ".join(f"11-{d.name[6:]}" for d in dirs)
assert f"{dates} の試行の写真 {photos} 枚と動画 {videos} 本" in data, (dates, photos, videos, data[:300])
assert data.count("卒業生 5 人") == 1 and "11-04 の参加者は本人の教え子の卒業生 5 人" in data, "卒業生 5 人は 11-04 の参加者として書く"
assert "回目" not in data and "の分だけ" not in data and "11 月 4 日と 6 日のワークショップの分" not in data, data[:200]
print("ok ワークショップの回数の数え方（要約・できることの見出し・日付で呼ぶ・11-04 の回の中身・データの扱いは 4 回をまとめた記録で、在る物は置き場の日付と数のとおり）")
