# 凍結した合格の基準（床の一覧）

一度 commit したら変えない。変える時は理由を commit と `docs/claude-usage.md` に残す。
exit code: 0 = 通る / 3 = 落ちる（検査の名前を出す）/ 4 = 検査できない。
入口は `run.sh`。結果は `out/RESULT.md`。

| ID | 見る事 | 負の対照（場面） | 期待 |
|---|---|---|---|
| F1.marks | 型紙の PDF から pdftotext で、所蔵（国立国会図書館デジタルコレクションと永続 ID）・改変・出典 ID・「仮説」が取り出せる | `neg_marks_all`・`neg_marks_source_id` | 3・F1.marks |
| F2.bom | 部品表の素材が空でない。置き換えには元の素材（推定）と理由がある | `neg_bom_material`・`neg_bom_original` | 3・F2.bom |
| F3.result | 結果は 3 値。「わからない」を「動いた」に数えない | `tests/test_records.py` の負の場面 | 3・F3.result |
| F4.evidence | 寸法や仮説の順位の変更には根拠の記録 ID が要る | `tests/test_loop.py` の負の場面 | 3・F4.evidence |
| F5.range | 寸法が雛形の範囲の中で、知らない名前が無い | `neg_range` | 3・F5.range |
| F5.print_area | 全部品と全文字が印字域に収まる | `neg_print_area` | 3・F5.print_area |
| F5.overlap | 部品どうしが重ならない | `neg_overlap` | 3・F5.overlap |
| F5.text_overlap | 文字どうしが重ならず、文字が部品の枠をまたがない。幅はフォントから測る | `neg_text_overlap` | 3・F5.text_overlap |
| F5.fan_length | 折り数 × 折り幅 ＝ 扇の長さ | `neg_fan_length` | 3・F5.fan_length |
| F5.fan_height | 畳んだ扇の高さ ≦ 静止時の筒の空き（高さ − 押し上げる量） | `neg_fan_height` | 3・F5.fan_height |
| F5.fan_thickness | 畳んだ扇の厚さ ≦ 内筒の一辺 − 2 | `neg_fan_thickness` | 3・F5.fan_thickness |
| F5.slide_clearance | 内筒の一辺 < 外筒の一辺 − 1（等号は落とす） | `neg_slide_clearance` | 3・F5.slide_clearance |
| F5.figure_height | 像の高さ ≦ 折りの高さ ＋ 6 | `neg_figure_height` | 3・F5.figure_height |
| F5.base_size | 扇の台 ≦ 内筒の一辺 | `neg_base_size` | 3・F5.base_size |
| F5.stroke | 下から押す形は 押す部品の長さ ≧ 筒の高さ。つまみの形は 内筒が筒に収まり、溝が筒の端から 5mm 以上離れる | `neg_stroke_tube`・`neg_stroke_tab` | 3・F5.stroke |
| F5.pivot | 虎の雛形の族の床。重心が軸より下、静かな時の傾きが 15° まで、穴の余白、揺れの余裕、重りと頭が底に当たらない | `neg_pivot_weight_above`・`neg_pivot_tilt`・`neg_pivot_ear`・`neg_pivot_floor` | 3・F5.pivot |
| F6.label | 図鑑の文は印を持ち、印の無い文は公開できない。原文の引用は翻刻か人が確かめた文だけ。**分類の数と文言検査は本人の答え（判断待ち）の後に 1 回だけ追記する** | （未実装） | 3・F6.label |
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

F9.prediction は、予想か自分の仮説が無いと仮説の一覧も型紙も出さない床で、F9 の一部として足した。F9.own は自分の仮説に動かし方と根拠を求め、雛形に乗らない仮説を型紙にしない床。試験は `tests/test_hypotheses.py`。

F5.fan_height は、軸の形では「中心の高さ＋折りの高さ ≦ 押し上げる量」で見る。`pos_rim` は台に載せる形の正の場面。

## 持ち寄りの床（本人の決定で範囲に入った。設計は docs/process/research/09）

試験は `tests/test_contrib.py`。exit code は 0／3／4。

| ID | 見る事 | 負の対照（試験の中の場面） |
|---|---|---|
| F10.intake | 種類・本文・確かさ・同意の 3 点が揃う。画像は JPEG か PNG で 5MB まで | 同意なし・空の本文・偽の画像・大きすぎる画像 |
| F10.rights | 写真は権利の持ち主が要る。根拠が不明の物は公開できない | 持ち主なし・根拠不明の公開 |
| F10.review | 公開には確認した人の記録が要る。状態が受付でなければ公開できない | 名前なし・却下の後の公開 |
| F10.pii | 公開する文にメール・電話・郵便番号の形があれば公開できない | 本文のメール・電話・郵便番号 |
| F10.public | 公開の頁と道具は確認済みだけを返す。連絡先を出さない。取り下げで消える。道具は CC BY だけを返す | 受付中の投稿・受付中の写真の URL・取り下げの後・公開の記録が戻された後・表示だけの投稿 |
