# 凍結した合格の基準（床の一覧）

一度 commit したら変えない。変える時は理由を commit と `docs/claude-usage.md` に残す。
exit code: 0 = 通る / 3 = 落ちる（検査の名前を出す）/ 4 = 検査できない。
入口は `run.sh`。結果は `out/RESULT.md`。

| ID | 見る事 | 負の対照（場面） | 期待 |
|---|---|---|---|
| F1.marks | 型紙の PDF から pdftotext で、所蔵（国立国会図書館デジタルコレクションと永続 ID）・改変・出典 ID・「仮説」が取り出せる | `neg_marks_all`・`neg_marks_source_id` | 3・F1.marks |
| F2.bom | 部品表の素材が空でない。置き換えには元の素材（推定）と理由がある | `neg_bom_material`・`neg_bom_original` | 3・F2.bom |
| F3.result | 結果は雛形の値（御来迎は 3 値、虎は揺れた／揺れないの 2 値）。「わからない」を「動いた」に数えない | `tests/test_records.py` の負の場面 | 3・F3.result |
| F4.evidence | 寸法の変更と次に試す物の提案には根拠の記録 ID が要る。仮説の順位は扱わない（順位が混ざった提案は落とす。J-025） | `tests/test_loop.py` の負の場面 | 3・F4.evidence |
| F5.range | 寸法が雛形の範囲の中で、知らない名前が無い | `neg_range` | 3・F5.range |
| F5.print_area | 全部品と全文字が印字域に収まる | `neg_print_area` | 3・F5.print_area |
| F5.overlap | 部品どうしが重ならない | `neg_overlap` | 3・F5.overlap |
| F5.text_overlap | 文字どうしが重ならず、文字が部品の枠をまたがない。幅はフォントから測る | `neg_text_overlap` | 3・F5.text_overlap |
| F5.fan_length | 折り数 × 折り幅 ＝ 扇の長さ | `neg_fan_length` | 3・F5.fan_length |
| F5.fan_height | 畳んだ扇の高さ（軸の形は中心の高さ＋扇の高さ）≦ 押し上げる量（静かな時の台から口まで）。口の台の形も軸の形と同じ見方 | `neg_fan_height`・`neg_fan_height_rim` | 3・F5.fan_height |
| F5.fan_thickness | 畳んだ扇の厚さ ≦ 内筒の一辺 − 2 | `neg_fan_thickness` | 3・F5.fan_thickness |
| F5.slide_clearance | 内筒の一辺 < 外筒の一辺 − 1（等号は落とす） | `neg_slide_clearance` | 3・F5.slide_clearance |
| F5.figure_height | 像の高さ ≦ 折りの高さ ＋ 6 | `neg_figure_height` | 3・F5.figure_height |
| F5.base_size | 扇の台 ≦ 内筒の一辺 | `neg_base_size` | 3・F5.base_size |
| F5.stroke | 下から押す形は 押す部品の長さ ≧ 筒の高さ。つまみの形は 内筒が筒に収まり、溝が筒の端から 5mm 以上離れる | `neg_stroke_tube`・`neg_stroke_tab` | 3・F5.stroke |
| F5.pivot | 虎の雛形の族の床。重心が軸より下、静かな時の傾きが 15° まで、穴の余白、揺れの余裕、重りと頭が底に当たらない | `neg_pivot_weight_above`・`neg_pivot_tilt`・`neg_pivot_ear`・`neg_pivot_floor` | 3・F5.pivot |
| F6.label | 図鑑の文は印を持ち、印の無い文は公開できない。印は原文の引用／仮説／観察の 3 分類。原文の引用は翻刻か人が確かめた文だけ。文言の検査はしない | `tests/test_labels.py` の負の場面 | 3・F6.label |
| F7.revision | 版 2 は根拠の記録 ID を持ち、版 1 と寸法が違い、式のある寸法は向きが式と合う。式の無い変更には印を付ける | `tests/test_loop.py` の負の場面 | 3・F7.revision |
| F8.references | 仮説や提案が引いた前例の ID は実在する | `tests/test_loop.py`・`tests/test_records.py` の負の場面 | 3・F8.references |
| F9.human | 記録の解釈・版の更新の人の確認が無いと次に進めない。仮説の採否と型紙の確定は、人が仮説を選んで刷る操作で代える（確定の記録は未実装） | `tests/test_loop.py` の負の場面 | 3・F9.human |

## F5.stroke の由来

`docs/process/research/03-mechanism-dimensions.md` の計算で見つかった行程の不足を、検査にした物。

## 正の場面

`pos_tab`・`pos_tube`・`pos_stick`・`pos_long_title`（長い見出しでも部品が下へ送られて通る）は exit 0。

## 追加した床（理由は docs/process/research/08 と decisions/J005）

既存の床は変えず、足しただけ。凍結の時には考えていなかった形の失敗が計算で見つかったため。

| ID | 見る事 | 負の対照 | 期待 |
|---|---|---|---|
| F5.fan_clearance | 帯の長さの開く上限が、筒の口の角に当たらない角度に収まる | `neg_fan_clearance` | 3・F5.fan_clearance |
| F5.image_box | 描き直しの絵が部品の中にあり、折り線と糊代をまたがない | `neg_image_box` | 3・F5.image_box |
| F5.image_count | PDF に貼られた画像が 0 枚（原図を貼らない。J-007） | `neg_image_count` | 3・F5.image_count |

F11.compare は案 B で足した床。見分ける物差しの無い雛形と、同じ仮説どうしは見比べる紙にしない。負の対照は `tests/test_discriminate.py`。

F9.prediction は、予想か自分の仮説が無いと仮説の一覧も型紙も出さない床で、F9 の一部として足した。F9.own は自分の仮説に動かし方と根拠を求め、雛形に乗らない仮説を型紙にしない床。試験は `tests/test_hypotheses.py`。

F5.fan_height は、軸の形では「中心の高さ＋折りの高さ ≦ 押し上げる量」で見る。`pos_rim` は台に載せる形の正の場面。

### F5.fan_height を直した（2026-11-05・本人の決定。#163）

元の文は「畳んだ扇の高さ ≦ 静止時の筒の空き（高さ − 押し上げる量）」で、口の台の形はこの通りに見ていた。ところが静かな時の台から口までは押し上げる量で、高さ − 押し上げる量は台の下の空き（内筒が入る所）だった。そのため、扇が口から出る寸法が通っていた（元の H-E と `pos_rim` は扇の高さ 48・押し上げる量 36 で、静かな時に扇の上 12mm が口から出る）。paper-to-toy では 2026-11-04 の本人の決定で直してあり、同じ名前の床が 2 つの repo で別の意味になっていた。

- 床を paper-to-toy と同じにし、口の台の形も押し上げる量と比べる
- 御来迎の H-E を 14 折り・高さ 36mm に直した。今の版（goraigo-v10）の例外で、次の版にしない（本人の決定）。控えの指紋で変えたのは H-E の型紙・手順の紙・手順の紙（原図つき）の 3 枚。H-E の紙は試行で使っていない
- `pos_rim` は扇が隠れる寸法（扇の高さ 36・折り数 14）に替えた。元の寸法は負の場面 `neg_fan_height_rim` にした
- `neg_fan_clearance` は口の台の形で、元の寸法（扇の高さ 48）だと F5.fan_height でも落ち、狙いの F5.fan_clearance だけで落ちる場面でなくなるので、扇の高さを 36 にした（F5.fan_clearance だけで落ちる事は変わらない）

## goraigo-v8 で変えた所（2026-11-04、11-04 の試行を受けた本人の決定）

- **F5.stroke（つまみの形）**: 溝を筒の下の端まで開いた切り込みにした（くり抜かない）ので、溝の端の 5mm は口の側だけを見る。下の端は開いているので見ない。柄の形（H-C・H-D）には土台（短い内筒）を足し、土台の高さが静止時の筒の空きに収まる事を見る。負の対照 `neg_stroke_tab` の場面と期待は変えていない（内筒が筒に収まらない形で落ちる）
- **F5.image_count**: 型紙は今も 0 枚。手順の紙だけ、完成のイメージとして載せた原図の数と照らす（原図の写しが手元に無い所では載せず 0 枚）。J-007 の例外として本人が決めた

## 見直しで足した所（2026-11-04、8cf3ee9 までの見直しで見つかった所）

既存の床の名前と負の対照の場面は変えず、見る事を足しただけ。どれも許した寸法で作れない型紙が通っていた。証拠は `docs/process/gate-evidence/fix-tpl-*-red.txt`（直す前に落ちる）と `-green.txt`（直した後に通る）。

| ID | 足した事 | 試験 |
|---|---|---|
| F5.holes（新しい床） | 穴が部品の紙の中にある（御来迎）。開く糸の穴は要から 35mm に固定なので、低い扇では紙の外に出る。像の穴が像より高い時も落とす | `tests/test_slider_holes.py` |
| F5.stroke | 内筒を下から押す形は、押し上げる量 ≦ 筒の高さ（静止時に内筒の上の端が筒の中にある） | `tests/test_slider_tube_stroke.py` |
| F5.pivot | 首の形: 帯の幅は穴の中で縦に並ぶとして、10° 傾いても帯が穴の縁に当たらない（軸は壁の 6mm 後ろ）。前は帯の幅の 2 割しか引かず、穴より広い帯も通していたので、見方を正した。吊る形: axle_height が刷る耳の穴の高さ（胴の高さ − 4）と同じで、重りの位置が頭の中にある | `tests/test_pivot_neck_opening.py`・`tests/test_pivot_hang_model.py` |
| F8.references | 提案の根拠の記録は、提案と同じ出典（玩具）の物 | `tests/test_loop_record_source.py` |

## 持ち寄りの床（本人の決定で範囲に入った。設計は docs/process/research/09）

試験は `tests/test_contrib.py`。exit code は 0／3／4。

| ID | 見る事 | 負の対照（試験の中の場面） |
|---|---|---|
| F10.intake | 種類・本文・確かさ・同意の 3 点が揃う。画像は JPEG か PNG で 5MB まで | 同意なし・空の本文・偽の画像・大きすぎる画像 |
| F10.rights | 写真は権利の持ち主が要る。根拠が不明の物は公開できない | 持ち主なし・根拠不明の公開 |
| F10.review | 公開には確認した人の記録が要る。状態が受付でなければ公開できない | 名前なし・却下の後の公開 |
| F10.pii | 公開する文にメール・電話・郵便番号の形があれば公開できない | 本文のメール・電話・郵便番号 |
| F10.public | 公開の頁と道具は確認済みだけを返す。連絡先を出さない。取り下げで消える。道具は CC BY だけを返す | 受付中の投稿・受付中の写真の URL・取り下げの後・公開の記録が戻された後・表示だけの投稿 |
