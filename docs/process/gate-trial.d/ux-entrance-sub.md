## 入口の題の間の副題 3 行目を「紙でよみがえらせる」に（UX の担当、ux/entrance-sub、11-08）

- 目的: 本人の言葉 11-08「最初のページ、江都二色より／うしなわれた玩具の動きを／紙で実験して確かめる。紙で実験して確かめる、が長い。」と、3 行目の答え「紙でよみがえらせる。」
- どうしたか: web/looks.py の SUB（副題の 3 行の 1 か所・白と暗い版の入口が同じ字を出す）。訳の表に "brought back to life in paper"（英語の用語の担当の確かめ: 3 行で 1 つの句・in paper は紙の模型として・受け身は誰が元どおりにするかを言い切らない）、やさしい日本語の表に「｜紙《かみ》でよみがえらせる」（字の順の所）。試験 test_hall_tate と test_easy_part1 の字を替えた
- 検証ゲート: **済み**。Red: main の頭 ace2a5f0 に新しい試験 tests/test_hall_tate.py だけを置くと rc 1（gate-evidence/red-entrance-sub.txt）。Green: gate-evidence/green-entrance-sub.txt
