## 公開のデモの応答に守りの頭を付ける（直しの担当、issue/sec-headers、11-07 夜）

- 目的: 公開のデモの応答が、トンネルの先で溜め置かれて別の人に返る事と、別のサイトの枠に入れて押させる形を防ぐ
- なぜか: 公開の前の点検（11-07 昼）の U18（Cache-Control が無い）と U20（守りの頭が無い）。本人の決め（11-07 21:2x）「(a) を出す」
- どうしたらいいか（比べた案と推し）:
  - 推し: play_server の全部の応答に、口が自分で決めた頭を上書きしない形で足す。頁と JSON は private, no-store、絵と紙は private。X-Frame-Options: DENY と CSP の frame-ancestors 'none'。Referrer-Policy は same-origin
  - 比べた案 1: 全部を no-store にする。絵と紙を同じ人の端末でも毎回読み直すので、遅い網で頁が重くなる。共有の溜め置きは private で止まるので採らない
  - 比べた案 2: Referrer-Policy を no-referrer にする（点検の時の対処案）。ブラウザは同じ頁からのフォームの POST に Origin: null を付けるので、書き込みの口の Origin の照らし（同じ頁から来た物だけを受ける）が全部断る形になる。採らない
  - 比べた案 3: CSP で script-src なども締める。頁の中の script と style の書き方を全部見直す事になり、今夜の締めでは確かめ切れないので、frame-ancestors だけにした
- ゴールの要件: 入口・玩具の頁・断りの頁の応答に private, no-store・X-Frame-Options: DENY・frame-ancestors 'none'・Referrer-Policy: same-origin・nosniff。絵と紙は private だけ、JSON は no-store
- 検証ゲート: **済み**。Red: 今の main（57cfadf4）にこの試験だけを置くと、入口の応答に Cache-Control が無くて rc 1（gate-evidence/red-guard-headers.txt）。Green: この枝で rc 0（green-guard-headers.txt）
- エビデンスゲート: 頭を見るほかの試験（test_error_pages・test_public_gate・test_public_open・test_lan_switch・test_write_limit と、頭を読む試験の全部）がこの木で rc 0
- 確かめていない事: 公開の場（トンネルの先）で、応答の cf-cache-status が溜め置かない形になるか（CHECK 5 で見る）。本物のブラウザでの、フォームの送りの通り（Referrer-Policy の same-origin で Origin が付く事は、決まりで読んだだけ）
- マージ後の書き戻し: Issue は立てていない
