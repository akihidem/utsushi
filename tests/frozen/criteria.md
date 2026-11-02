# 凍結した合格の基準（床の一覧）

一度 commit したら変えない。変える時は理由を commit と `docs/claude-usage.md` に残す。
exit code: 0 = 通る / 3 = 落ちる（検査の名前を出す）/ 4 = 検査できない。
入口は `run.sh`。結果は `out/RESULT.md`。

| ID | 見る事 | 負の対照（場面） | 期待 |
|---|---|---|---|
| F1.marks | 型紙の PDF から pdftotext で、所蔵（国立国会図書館デジタルコレクションと永続 ID）・改変・出典 ID・「仮説」が取り出せる | `neg_marks_all`・`neg_marks_source_id` | 3・F1.marks |
| F2.bom | 部品表の素材が空でない。置き換えには元の素材（推定）と理由がある | `neg_bom_material`・`neg_bom_original`（未実装） | 3・F2.bom |
| F3.result | 結果は 3 値。「わからない」を「動いた」に数えない | `neg_result_unknown`（未実装） | 3・F3.result |
| F4.evidence | 寸法や仮説の順位の変更には根拠の記録 ID が要る | `neg_change_no_record`（未実装） | 3・F4.evidence |
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
| F5.pivot | 虎の雛形の族の床（未実装。名前だけ決める） | `neg_pivot_*`（未実装） | 3 |
| F6.label | 図鑑の文は印を持ち、印の無い文は公開できない。原文の引用は翻刻か人が確かめた文だけ。**分類の数と文言検査は本人の答え（判断待ち）の後に 1 回だけ追記する** | （未実装） | 3・F6.label |
| F7.revision | 版 2 は根拠の記録 ID を持ち、版 1 と寸法が違い、式のある寸法は向きが式と合う。式の無い変更には印を付ける | （未実装） | 3・F7.revision |
| F8.references | 仮説が引いた前例の ID は実在する | （未実装） | 3・F8.references |
| F9.human | 仮説の採否・型紙の確定・記録の解釈・版の更新の人の確認が無いと次に進めない | （未実装） | 3・F9.human |

## F5.stroke の由来

`docs/process/research/03-mechanism-dimensions.md` の計算で見つかった行程の不足を、検査にした物。

## 正の場面

`pos_tab`・`pos_tube`・`pos_stick`・`pos_long_title`（長い見出しでも部品が下へ送られて通る）は exit 0。
