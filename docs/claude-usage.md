# Claude の使い方の記録

作業しながら更新する。まだ実施していない事は実施したように書かない。

## 開発で使った物

| 面 | 用途 |
|---|---|
| Claude Code（Opus 5.5） | 調査、案の比較、設計、コード、試験、文書の作成 |
| Claude Code の Web 検索 | 先行例の確認（`docs/process/research/05-three-axes.md`） |

## 製品の中で Claude を呼ぶ所

裏の制作の仮説生成（`src/api/generate.py`）、言葉の仮説を寸法に写す口（`src/api/words.py`）、輪の後半（記録の解釈・次の手の提案）で Messages API の tool use を呼ぶ形を作った。道具は 8 回・やり直しは 2 回で止める（`src/api/config.py` の MAX_TOOL_CALLS・MAX_RETRIES）。このほか、作っている途中の手順の質問に答える口（`src/api/ask.py`、11-04）が Messages API を 1 回呼ぶ。仕組みとどの仮説かは答えず、よくある言葉は刷った説明から API なしで答え、それ以外は鍵がある時だけ Claude に組み方と凡例だけを渡す。入口のサイトの中の手帖の頁（`src/web/techo_site.py`）もこの口を使う。本物の API はまだ 1 回も呼んでいない。試験は記録した形の偽物。実行時のモデルは本人の決定で全部 Opus 5.5（`src/api/config.py`）。計画書どおりにした判断で、下の層と質を比べた結果ではない。上限は `src/api/budget.py` で守る（`docs/process/decisions/J017-runtime-model.md`）。

## 作り手の工房の Claude Code の機能

本人の決定（カード 20261102-211820-2 の案 2）で、作品の輪に合った機能を repo に足した。選び分けの理由と開発の運転の形は [docs/process/claude-story.md](process/claude-story.md)（本人が確認した）。

| 機能 | 置き場 | 中身 |
|---|---|---|
| Skill | `.claude/skills/backstage/SKILL.md` | 裏の制作の手順。API の鍵なしで仮説の案を作り、`hypotheses import-draft` で人が採る前の受付に入れる |
| MCP | `.mcp.json`・`src/api/mcp_server.py` | API の輪と同じ道具（寸法の検査、図の拡大、前例）と、案の全体の検査 `check_draft` |
| サブエージェント | `.claude/agents/second-eye.md` | 案の言葉と根拠を、作った者と別の目で読む。書き換えない |
| フック | `.claude/settings.json`・`.claude/hooks/ledger-check.sh` | 記録や台帳を直した直後に台帳の検査を回し、落ちた時と検査できない時は Claude に返す |

試験は `tests/test_claude_code.py`（MCP の応答、受付の床、フックの負の対照）。工房で実際に案を作った事はまだ無い。MCP は Claude Code が認識したが、使う前の承認はまだ。

## 決定的な検査との境目

型紙の座標と SVG・PDF は生成器が描き、寸法と印は検査が見る。基準は `tests/frozen/criteria.md`、入口は `./run.sh`。

## 批評

人のレビューは受けない。本人の決定で、批評は Claude のセッションだけで行う（`docs/process/decisions/J018-no-peer-review.md`）。批評の役も Claude なので、人の評価の代わりにはならない。

## 検証

- 実施済み: `./run.sh` の全場面と試験（数は `./run.sh` の最後の行）、まっさらな clone での実行、PNG の目視
- 実施済み: 実物での試作 1 回（11-04、成人 5 人。御来迎は動き、虎は途中。[試行の索引](process/trials/README.md)）
- 持ち寄りの機能だけ、生成と別のセッション（同じアカウントの Claude）に検品させ、指摘を直した
- 未実施: 11-04 の試行を受けて直した版（goraigo-v8 以降）の実物での試作、型紙の部分の別セッションでの検証、提出前の敵対的な試験

## 凍結の変更の記録

- #146 で、F3.result の文を「どの雛形も 動きの言葉・その打ち消し・わからない の 3 値」に変え、虎でも「わからない」を選べるようにした。説明の欄は「わからない、でもよい」と書くのに、虎では選べなかったため。虎の 2 値は前の本人の判断（`docs/process/research/15-philosophy-review.md`）で、この変更は本人の確認待ち。頭が揺れるかどうかで足りるという物差しは変えていない。前の札で残った記録の値も受ける形を文に足した。必須 2 種の今の組の紙は変えない（虎の手順の紙は 2 つの欄のまま。雛形の `PAPER_RESULTS`。指紋は `tests/test_floor_pin.py` で同じ）。狙いの検査の名前と負の場面は変えていない（札に無い言葉は断る）。
- 本人の決定（11-05、#332 の点 2、`docs/process/decisions/J032-one-sheet-per-toy.md`）「見比べる紙は外す」で、凍結の基準から F11.compare を外した。この床が守る紙（J-019）を刷る道が無くなり、型紙が玩具ごとに 1 枚のたたき台になって、競合する仮説を並べて見分ける芯も外れたため。基準の文と照合の表を直し、試験 `test_discriminate` を外し、外れた事を見る `tests/test_no_compare_sheet.py` を足した。場面は変えていない。必須 2 種の紙の指紋も変わらない。前に渡した compare-v1・compare-v2 の PDF は履歴として残す。
- 本人の決定（11-05、#332、`docs/process/decisions/J032-one-sheet-per-toy.md`）「型紙は説を羅列せず、おもちゃ一個につき一個にする」と点 3「必須 2 種は、今の組から 1 枚にする」で、凍結の 2 つを変えた。(1) `tests/frozen/criteria.md` の F9.human の文を、人が仮説を選んで刷る形から、玩具ごとに 1 枚のたたき台（記録の欄 `sheet`）を刷る形にした。必須 2 種の今の組はたたき台でない仮説を F9.human で断る（`tests/test_one_sheet.py`）。照合の表も同じ commit で直した。(2) `tests/floor_pin.json` の照合を 31 枚から 9 枚（御来迎 H-A の 4 枚・虎 H-A の 3 枚・先生の見る紙 2 枚）にし、H-A 以外の 22 枚（御来迎 H-B〜H-E の 16 枚・虎 H-B〜H-C の 6 枚）は消さずに `removed` へ移して理由の印を付けた。比べる紙の指紋は 1 つも変えていない（real・standin とも元の値のまま）。下限 `>= 31` は `>= 9` にした。負の対照 3 つは同じ向きで拾う（寸法 1・組の版 5・組み方の文 1）。F11.compare（見比べる紙）は外すと決まったが、この変更では触っていない。
- 本人の決定（11-05、#242）「予想の段を無くして、すぐ作る形にする」で、床 F9.prediction を外した。予想か自分の仮説が無いと仮説と型紙を出さない床で、共有のデモでは人ごとに分かれず（#208）、作り始めるまでの段にもなっていた。基準の文を直し、照合の表を作り直した。かざして選ぶ頁の試験は頁ごと外した。場面の中身は変えていない。必須 2 種の紙の指紋は同じ。
- 本人の決定（11-05、#258）で、紙に刷る仮説の文を「仮説: AI が考えた、試すための 1 つの翻案です。正解ではありません。作って、動きを確かめて、直していきます」に替えた（エンジンと同じ文）。必須 2 種の 31 枚の字が変わるので、`tests/floor_pin.json` の指紋を取り直した。直す前と後の SVG を比べ、どの紙もこの 1 行の外は同じで、寸法と形は変わっていない。場面と基準の文は変えていない。
- 本人の決定（11-05、#163）で、床 F5.fan_height の口の台の形の見方を paper-to-toy と同じにした（押し上げる量と比べる）。元の見方は台の下の空きと比べていたので、静かな時に扇の上 12mm が口から出る H-E と `pos_rim` が通っていた。H-E を 14 折り・高さ 36mm に直した。必須の今の版（goraigo-v10）の**例外**で、次の版にしていない。控えの指紋 `tests/floor_pin.json` は H-E の型紙・手順の紙・手順の紙（原図つき）の 3 枚だけを手で直した。ほかの 28 枚は同じ。`pos_rim`・`neg_fan_clearance` を替え、元の寸法を `neg_fan_height_rim` にした。理由は `tests/frozen/criteria.md` の「F5.fan_height を直した」。J-019 と J-020 の「172°」は当時の記録なので書き換えていない（今の H-E の計算の上限は 178°）。
- 凍結した場面と基準を機械で守るため、照合の表 `tests/frozen/manifest.json` を足した（#165）。場面と基準の文は変えていない。場面を消す・変える・足す、基準の文を変える、在るはずの試験を消すと、`./run.sh` が rc 4 でそのファイルを名指しする。これからは、凍結を変える commit に表の変更も入れる（`python tests/run_floors.py --write-manifest`）。試験は数でなく名前で持つ（並んで動く線が試験を足すたびに、同じ 1 行でぶつからないため）。
- 8cf3ee9 までの見直しで見つかった所を直すため、床 F5.holes を足し、F5.stroke（内筒を下から押す形の押し上げる量）・F5.pivot（首の帯が穴を通る見方を正した。吊る形の軸の高さと重りの位置）・F8.references（根拠の記録の出典）に見る事を足した。負の対照の場面と既存の期待は変えていない。理由と中身は `tests/frozen/criteria.md` の「見直しで足した所」。
- 11-04 の試行を受けた本人の決定（goraigo-v8）で、F5.stroke のつまみの形の溝の端の見方（口の側だけ）と、柄の形の土台の高さの見方を変え、F5.image_count を手順の紙では載せた原図の数と照らす形にした。理由と中身は `tests/frozen/criteria.md` の「goraigo-v8 で変えた所」と `docs/process/trials/README.md`。

- 本人の決定で仮説の順位をやめたので、F4.evidence の文から「仮説の順位の変更」を外し、「次に試す物の提案」と「順位は扱わない」を書いた。狙いの検査の名前は変えていない。理由は `docs/process/decisions/J025-no-ranking.md`。
- 本人の決定で案 B を採ったので、床 F11.compare を足した。既存の床は変えていない。理由は `docs/process/decisions/J019-experiment-sheet.md`。
- F6.label に本人の決定の内容を追記し、凍結を閉じた（3 分類、文言の検査なし）。凍結の時から「答えの後に 1 回だけ追記する」と書いてあった分で、これ以上は足さない。負の対照の欄を `tests/test_labels.py` にした。理由は `docs/process/decisions/J016-zukan-labels.md`。
- F3.result の文を、結果は雛形の値に変えた。虎は本人の判断で揺れた／揺れないの 2 値にしたため（`docs/process/research/15-philosophy-review.md`）。御来迎の 3 値は変えていない。
- 基準の文は変更なし。基準に名前を決めてあった負の対照 `neg_bom_material`・`neg_bom_original` の場面を、部品表の検査を作る時に足した。
- 既定の寸法を手元の複写の基準に変えたので、場面 `pos_tube`・`pos_stick` の押す部品の長さを 84 に、`neg_figure_height` の像の高さを 55 に直した。検査の基準の文は変えていない。狙いの検査も同じ。理由は `docs/process/research/07-own-scans.md`。
- 床 F5.fan_clearance・F5.image_box・F5.image_count を足した。既定を軸の形に変えたので、F5.fan_height の軸の形の式を基準に書き足した。理由は `docs/process/research/08-fan-axle.md`。
- 本人の決定で持ち寄りの場が範囲に入ったので、床 F10 を基準に足した。
- 本人の方針で図を貼らず描き直す事にしたので、F5.image_box・F5.image_count の基準の文と、場面 `neg_image_box`・`neg_image_count` の入力を直した。理由は `docs/process/decisions/J007-redraw-not-paste.md`。
- F10.public の見る事を足した（道具は CC BY だけ、戻された公開の記録も出さない）。F10.pii は受付の時にも見る。理由は `docs/process/decisions/J006-contributions-minimum.md`。
- 本人の指摘で仕組みを複数の仮説として並べる形に組み直したので、床 F9.prediction を足した。理由は `docs/process/decisions/J002-mechanism-hypotheses.md`。
- 本人の設計入力で自分の仮説から入る道を足したので、F9.prediction の文を直し、F9.own を足した。理由は `docs/process/decisions/J008-own-hypothesis-path.md`。
- 虎の雛形を作る時に、名前だけ決めてあった F5.pivot の中身と負の対照の名前を基準に書いた。
- 輪の後半を作る時に、F2・F3・F4・F7・F8・F9 の負の対照の欄を実際の試験の場所に直した。F9.human の文に、仮説の採否と型紙の確定の記録が未実装である事を書き足した。
