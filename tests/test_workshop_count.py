"""ワークショップの回数の数え方（本人の言葉 11-07「ワークショップ 4 回は 11 月 4・5・6・7 日でよい。回数の数え方と改善の歴史の表はこの 4 回で
そろえてください」）。README と CLAUDE.md の、回数を出す所を見る。

見る事:
1. 30 秒の要約（README と CLAUDE.md の 2 か所。同じ字である事は omochae.ledger の L.summary が見る）が「ワークショップは 4 回（11 月 4・5・6・7 日）」で、
   前の「実物の試行は 1 回」の数え方が残っていない
2. 回は日付で呼び、「何回目」と言わない。前の記録は 11-06 を「2 回目」と呼ぶが、4 回を 11-04・05・06・07 と数えると 3 回目になり、
   数え方が食い違う（審査用の頁のワークショップの節と同じ決まり）
3. 11-04 の回の中身（卒業生 5 人・御来迎が動いた）は消さずに残す。今の組（版 14・版 7）もワークショップで実物を試した（本人の答え 11-08。前の「今の組の紙は実物で確かめていない」は外した）。5 人はのべ 30 人に入り、30 人は全員が実物を試した（本人の答え 11-08）
4. README の「確かめた事」の頭の行も 4 回の数え方（前は「できること」の見出し）
5. README の「データの扱い」: 人の記録は 4 回のワークショップをまとめた記録（本人の言葉 11-07）で、repo に在る物は写真と動画の置き場の日付と数のとおり。
   卒業生 5 人は 11-04 の参加者として書く。言った人の呼び方は、外に出す字では「制作者」にそろえた（README の組み直し 11-08・統括の照らし）
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
    assert "11 月 4 日の回は制作者の教え子の卒業生 5 人" in summary and "筒から扇を開いて動いた" in summary, (name, "11-04 の回の中身を残す")
    # 今の組（御来迎 版 14・虎 版 7）もワークショップで実物を試した（本人の答え 11-08「御来迎 版 14・虎 版 7、どちらもワークショップで実物を試した。
    # 「まだ実物で確かめていない」は外す。」）。前の字「今の組の紙は実物で確かめていない」は外した
    assert "今の組の紙（御来迎 版 14・虎 版 7）も、ワークショップで実物を試した" in summary and "実物で確かめていない" not in text, (name, "今の組も実物を試した")
    # 5 人はのべ 30 人に入り、30 人は全員が実物を試した（本人の答え 11-08「実物の試行 5 人はのべ 30 人に入る。30 人は全員、実物の試行をした。」）。
    # 5 人と 30 人を別の事のように並べない: 30 人の文に「全員が実物の型紙を試した」が付き、5 人は「そのうち」の回として書く
    assert "のべ 30 人参加し、全員が実物の型紙を試した" in summary and "そのうち 11 月 4 日の回は" in summary, (name, "5 人はのべ 30 人に入る")
    assert "卒業生がのべ 30 人参加した。" not in text, (name, "30 人だけの前の文が残っている")

# 4. README の組み直し（11-08）で「できること」の節は「確かめた事と、まだの事」になった。確かめた事の頭の行で 4 回の数え方を見る
done = readme[readme.index("### 確かめた事\n"):readme.index("### まだの事\n")]
first = next(l for l in done.splitlines() if l.startswith("- "))
assert first.startswith("- ワークショップは 4 回（11 月 4・5・6・7 日）") and "回目" not in done, first

# 5. データの扱い: 人の記録は 4 回のワークショップをまとめた記録（本人の言葉 11-07「11/4567のまとめた記録です」）。repo に在る物の書き方は、
# 写真と動画の置き場（docs/process/trials/photos/<日付>/）の日付と数のとおり（SECURITY.md の 11-04 と 11-06 の写真 43 枚と動画 1 本と同じ事実）。
# 卒業生 5 人は 11-04 の参加者なので、4 回の全部に広げて書かない
data = readme[readme.index("### データの扱い"):]
data = data[:min(i for i in (data.find("\n## "), data.find("\n### "), len(data)) if i >= 0)]
assert "11 月 4・5・6・7 日の 4 回のワークショップをまとめた記録" in data, data[:200]
dirs = sorted(p for p in (ROOT / "docs/process/trials/photos").iterdir() if p.is_dir())
assert dirs, "写真の置き場が無い"
photos = sum(1 for d in dirs for f in d.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png"))
videos = sum(1 for d in dirs for f in d.iterdir() if f.suffix.lower() in (".mp4", ".mov"))
dates = " と ".join(f"11-{d.name[6:]}" for d in dirs)
assert f"{dates} の試行の写真 {photos} 枚と動画 {videos} 本" in data, (dates, photos, videos, data[:300])
assert data.count("卒業生 5 人") == 1 and "11-04 の参加者は制作者の教え子の卒業生 5 人" in data, "卒業生 5 人は 11-04 の参加者として書く"
assert "下ののべ 30 人に入る" in data and "のべ 30 人参加し、全員が実物の型紙を試した" in data, "データの扱いでも 5 人は 30 人に入る"
# README の確かめた事の頭の行も、5 人を 30 人に含めて書く
assert "全員が実物の型紙を試しました（11 月 4 日の 5 人を含む。" in first, first
assert "回目" not in data and "の分だけ" not in data and "11 月 4 日と 6 日のワークショップの分" not in data, data[:200]
print("ok ワークショップの回数の数え方（要約・確かめた事の頭の行・日付で呼ぶ・11-04 の回の中身・データの扱いは 4 回をまとめた記録で、在る物は置き場の日付と数のとおり）")
