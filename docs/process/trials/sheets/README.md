# 型紙の版を捨てずに置く

本人に渡した型紙の PDF を全部ここに置く。良かった版だけにすると、何を直したかが追えなくなるため。**どれも実物で試した結果はまだ無い**（試行は 0 件）。本人の評価があるのは v5 の仮説 A だけ。

| 版 | 作った commit | 前の版から変えた事と理由 | 分かった問題、捨てた理由 | 記録 |
|---|---|---|---|---|
| goraigo-v1 | a76c29f | 最初の版。押し方 3 通り | 初期値に根拠が足りない | [research/03](../../research/03-mechanism-dimensions.md) |
| goraigo-v2 | 1ca4173 | 初期値を絵の測定と紙面の制約から出し直した | 手元の複写と照合していない | [research/06](../../research/06-rederive-defaults.md) |
| goraigo-v3 | 2837621 | 手元の複写を基準に寸法を直した | 台の形では扇が 180° までしか開けない | [research/07](../../research/07-own-scans.md)・[research/08](../../research/08-fan-axle.md) |
| goraigo-v4 | 30f5f50 | 扇を中心の軸で開く形にし、筒の面と像に原図を貼った | 拡大した図の粗さと裏写り。PDF が 1.8MB | [J-005](../../decisions/J005-axle-default.md)・[J-007](../../decisions/J007-redraw-not-paste.md) |
| goraigo-v5 | 3ecdb4e・d136f9b | 図を貼らず描き直した（約 0.1MB）。1 つの既定をやめ仮説ごとに刷った | 本人の評価「よくなった」（仮説 A）。動作は未確認 | [J-007](../../decisions/J007-redraw-not-paste.md)・[J-002](../../decisions/J002-mechanism-hypotheses.md) |
| goraigo-v6 | 2b09912 | 仮説ごとの手順の紙を足した | 実物は未確認 | [J-009](../../decisions/J009-sheet-and-records.md) |
| tora-v1 | 5a71051 | 虎の最初の版。仮説 3 つ | 胴の上面の縞が「1 胴」の文字に少し重なる（未修正）。実物は未確認 | [research/12](../../research/12-tiger.md) |

「変えた事」と「問題」は上の記録と commit から書いた。v1 と v2 の問題は次の版を作った理由から読んだ物で、実物の失敗ではない。
