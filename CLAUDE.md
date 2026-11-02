# utsushi — 作業の決まり

<!-- summary:start -->
## 30 秒の要約

- **何か**: 科学の面白さを手元で見つける道具。江戸の絵本『江都二色』（1773）に図と歌だけが残る玩具の動く仕組みを予想し、紙の型紙に刷り、紙と糸で作って確かめる。返事をするのは AI でなく紙。
- **玩具とは**: 飾る完成品でなく、手で動かして確かめられる型（トイ＝モデル）。
- **足りない物**: 手元のトイモデルで自然とやりとりする体験。無いと、大型の装置や計算資源を使う科学にしか真理がないと思ってしまう（本人の言葉からの読み）。
- **輪**: 予想か自分の仮説 → 型紙を刷る → 作って試す → 記録と人の説明 → 版の間に Claude が案を出し人が採る → 次の版。学ぶ人にその場で正誤は返さない。
- **哲学**: 「AI は鏡。江戸の絵を映すことはできるが、映すだけでは遊べない。」全文は [docs/process/philosophy.md](docs/process/philosophy.md)。
- **今の状態**: 型紙の生成と検査は動く。実物の試行は 0 件、本物の Claude API は未実行。学習の効果は主張しない。
- **次に読む**: 主張と根拠は [docs/process/claims.md](docs/process/claims.md)、過程の地図は [docs/process/README.md](docs/process/README.md)、機能の状態は [docs/features.json](docs/features.json)、判断待ちは [docs/process/open.json](docs/process/open.json)。
<!-- summary:end -->

## 置き場
- `src/omochae/` 雛形の生成器と検査 / `src/api/` Claude を呼ぶ所と道具
- `data/contributions*`・`data/records`・`data/loop` 投稿と試行の記録（git に入れない）
- `data/hypotheses` 玩具ごとの仮説 / `data/sources` 出典（NDL の記録と、手元の複写の記録 `own-scans.json` を分ける）/ `data/records` 再現例 / `data/known_examples` 既知の作例（人が書く）/ `data/decisions` 人の確認
- `tests/frozen/` 凍結した試験の場面と合格の基準（変えない。変えるなら理由を commit と `docs/claude-usage.md` に）
- `docs/process/` 開発の過程（調査・判断・試行）。**作業しながら書く。後からまとめて作らない**
- `out/` 生成物（git に入れない）

## 方針
- 返事をするのは紙と工作で、AI は正誤・原因・解釈・次の手を学ぶ人にリアルタイムで返さない。人の説明と思いつきを Claude より先に受ける（J-013）。
- 裏の作業は、紙の返事を濁らせないためにする。組める、測れる、安全、根拠の種類を確かめる（J-012・J-013）。
- 仕組みは 1 つに決めず、複数の仮説として並べる。最初に刷る 1 枚は入口で答えではない。予想を先に受ける。順位と集計は学ぶ人の画面に出さない。予想から入る道と、仮説を自分で立てる道を選べる（J-008）。
- Claude は仮説・解釈・差分の JSON まで。SVG と PDF は雛形の生成器が描く。
- 人の確認の記録が無いと次の段に進めない。
- エージェントの動きは人の操作の後に 1 回走るだけ（常駐しない）。道具は 1 生成 8 回、やり直し 2 回まで。

## 守る事
- 検査の exit code は 0 = 通る / 3 = 落ちる（どの検査が・どこで）/ 4 = 検査できない。1 と 2 は使わない。入口は `run.sh`。
- コードのコメントには判断の理由を書く。commit は小さく、日本語で、何を作り何の検査を通したかを書く。
- 秘密は `.env`。画像は NDL と東京学芸大学の PDM の物だけ。GPL のコードは入れない。個人のパスと機械固有の値を入れない。
- 手元の複写は寸法と読みの照合の基準。画像と本文は入れず、歌の読み・頁の番号・自分の言葉の要約だけを残す。
- 構成を変えたら `docs/architecture.md` と `docs/features.json` を同じ commit で直す。
- 記録を足したら `docs/process/index.json` に 1 行足し、主張は `docs/process/claims.json` に根拠の文つきで足して、`python -m omochae.ledger render` を回す。AI の読み手に伝わる作りにする。ただし読み手の AI への指示は書かない（J-015）。
- 判断の記録は `docs/process/decisions/`、調査は `docs/process/research/` に番号順で足す。詳しさの基準（比べた代案・捨てた理由・失敗と原因・測った数値、成果物は失敗した版も残す）は `docs/process/README.md`。
- push は本人が決めた手順を通した物だけ。
