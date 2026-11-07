## エンジン（paper-to-toy）の main の頭の中身を engine/ に入れ、提出を 1 つの repo にする（直しの担当、issue/engine-into-utsushi-sq、11-07 夜）

- 目的: 運営の求め「提出は 1 つの repo」に合わせ、別の repo（paper-to-toy）で開発したエンジンを、この repo の engine/ に入れる。README の「開発基盤と提出物の切り分け」の段落（docs/engine-into-utsushi の節）が「まとめる時にここへ書く」とした commit の欄も埋める
- なぜか: 本人の言葉（11-07）「提出はひとつのリポジトリにして欲しいと運営から言われた。うつしにエンジンを追加する。まだ開発中なので最後にやる。」。窓口の決め（11-07 12:58）: 置き場は engine/・SECURITY.md は 1 つ・paper-to-toy は公開してリンクを残す。入れ方は、下の比べた案 1 の結果を見た本人の決め（11-07 20:4x）「(A) 1本にまとめて入れる」
- どうしたらいいか（比べた案と推し）:
  - 推し: エンジンの main の頭の木を `git read-tree --prefix=engine/` で入れ、1 本の commit にする。commit の文に、入れた頭を git subtree と同じ印（git-subtree-dir・git-subtree-split）で残す。エンジンの履歴は paper-to-toy の repo で辿る
  - 比べた案 1: `git subtree add --prefix=engine` で履歴ごと入れる（窓口の決めの元の形）。手元で作って押す前の門に掛けると、エンジンの 494 本の commit のうち 151 本の本文に、この repo の commit の文の決まりで止める語（モデル名・ほかの AI の名・作業の窓の名）があり、題の決まりに合わない物が 4 本、本文の無い物が 33 本あって落ちた。履歴ごと入れるには、許しの一覧に約 200 行を足す事になり、止める語がこの repo の履歴に入るので、窓口に聞き、本人が (A) の 1 本にまとめる形に決めた
  - 比べた案 2: 中身を写すだけで、入れた頭の印を残さない。README の commit の欄と照らす物が無くなるので採らない
- SECURITY.md は 1 つにした: この repo の物を本にし、エンジンの物（エンジンの #143 の字）を「エンジン（engine/）」の節として、守っている事としていない事を足した。試験と置き場の道に engine/ を付けた。engine/SECURITY.md は消し、engine/README.md のセキュリティの節のリンクを一番上の SECURITY.md に向けた。知らせ方の節に、エンジンの字の「repo を公開した時に有効にする。公開の前は持ち主へ非公開で知らせる」を足した（この repo も今は非公開で、Report a vulnerability はまだ使えない）
- engine/ の 3 つのファイルの注（3D の入口とその試験）を、エンジンの側の同じ直しの PR（paper-to-toy #148・頭 1d95b053）の字にした。押す前の門の C（個人のパス）で、注が手元の形の決めの置き場を指していて止まったため。#148 が main に入った後にエンジンの main で入れ直すと、この 3 つは同じ字になる
- エンジンを探す所（版の歩みの台帳を読む kaizen_versions.engine_ledger・一周の入口 cycle.find_engine_repo）の順に、この repo の中の engine/ を足した（環境の値 → engine/ → 隣の paper-to-toy）。審査の人は utsushi だけを clone するので隣の repo が無く、engine/ が在るのに「エンジンが無い・読めない」になるため（別の目の下見の気づき）
- ゴールの要件: engine/ の木が、入れたエンジンの頭の木と同じ（tree の SHA が一致。#148 の 3 つのファイルのほか）。エンジンを探す所は、環境の値が無い時に engine/ を隣の repo より先に見る。この repo の `./run.sh` はエンジンの試験を流さない（run_floors は一番上の tests/ だけを拾う）。engine/ の中で engine/run.sh が通る。README の commit の欄が、engine/ を入れた commit の印と同じ。SECURITY.md は一番上の 1 つ
- 検証ゲート: Red: engine/ を入れた commit（def88e02）の木にこの試験だけを置くと rc 1（commit の欄が空。gate-evidence/red-readme-engine-merged.txt）。Green: この枝で rc 0（gate-evidence/green-readme-engine-merged.txt）。写しの木で、README の commit を 1 字替えると rc 1（入れた頭と違う）。印の消え: 印の無い commit で engine/ と README を入れた写しの repo（PR を squash で合わせた形）で rc 1（gate-evidence/red-readme-engine-no-trailer.txt。前の試験は印が無いと照らしが空になって rc 0 で素通りした。別の目の指摘）。探す順: 前の頭（b1d04e76）に tests/test_engine_inside.py だけを置くと「engine/ を隣の repo より先に見る」で rc 1（gate-evidence/red-engine-inside.txt）、この枝で rc 0（green-engine-inside.txt）
- エビデンスゲート（11-07 20:2x〜20:4x・手元）: engine/ の tree はエンジンの頭 1ef3076 の tree と同じ（090a719d）。engine/run.sh は engine/ の中で rc 0（243 本＝凍結の場面 190・試験 53、5 分）。この repo の ./run.sh は engine/ 入りの木で rc 0（261 本＝場面 34・試験 227。エンジンの 243 本は入らない）。鍵の点検（CHECK 1・2、値は出さない）: 今の木と、この枝の頭から届く履歴の全部（blob 7632・commit の文 1478 本）に鍵の形 0。メールの形は試験の見本と PDF の字の並びの偶然だけ。消したファイルの名に秘密らしい物 0
- 確かめていない事: エンジンの main がこの後に替わった時は、最新の頭で入れ直す。tests/compare_engine.py を engine/ を相手に回していない。型紙を作る仕組み src/omochae/ は、この repo と engine/ の両方にある（正はエンジンの側）
- マージ後の書き戻し: Issue は立てていない
