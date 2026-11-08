## 公開のデモで、型紙を印刷する の作り直す口だけを Claude につなぐ（Issue 対応の担当、issue/public-think、11-08）

- 目的: 合言葉なしの公開のデモでも、「Claude に話して型紙を作り直す」口が本当に動く形にする。ほかの AI の口は閉じたまま
- なぜか: 本人の決め（11-08・統括を通して）「公開のデモにも、本当に動く形で出してください。鍵と予算の止め（1日30回・0）つきです。安全の事項5（公開ではAIを呼ばない）とは、この口だけは本人の決めで開けます。他の口は閉じたままにしてください。」。設計は grove の state/public-think-20261108.md（統括の確かめ済み）
- どうしたらいいか:
  - serve に public_think（既定は偽）と、命令の印 --public-think。合言葉なしの場（--public）と一緒の時だけ使える。この印の時だけ、鍵のある所でも公開の場を立てる（印が無ければ前のとおり立たない）
  - think_sheet._closed: 公開の場で印がある時は、作り直す口（受け口 think-talk・think-sheet・think-ok・頼んだ後の様子・自分の案の紙）を開く。話した字・様子・自分の案の紙は、前のとおり頼んだ画面の鍵（cookie）を持つ画面だけ
  - ほかの AI の口（/ask・/ask-json・ai-interpret・ai-observe・kasane/ask）は、呼ぶたびに public_open を見て閉じたまま（安全の事項 5・#728）
  - 止め（1 日 30 回・予算の止め・書き込みの数の止め）は公開の場でも同じに効く（どれも場を見ない作り）
  - 頁の作り直す口は、合言葉の場と同じ見た目（toy_page の think・play_server._toy が渡す）
  - run-demo.sh --open に --public-think を渡せる形（--open だけなら前のまま）
  - あわせて main の落ち test_print_busy: think-talk も紙を作る送り（押した時に待つ印）なので、試験の紙を作る送りの並びに足した
- 見た事: 偽の Claude（試験）は beta の口が無く、道具を使う口（api.agent.run）が呼べずに待ちへ落ちていた。偽の Claude に beta の口を足して、作り直す口が Claude まで届く事を見た
- ゴールの要件: `tests/test_public_ai_closed.py` の 3（印の時だけ鍵のある所で立つ・印は公開の場とだけ・ほかの 5 つの口は Claude を呼ばない・頁に口が出る・作り直す口だけが呼ぶ）と `tests/test_print_busy.py`
- 検証ゲート: **済み**。Red は `docs/process/gate-evidence/red-public-think.txt`（今の main で serve に印が無く rc 1・test_print_busy が think-talk の待つ印で rc 1）
- エビデンスゲート: **済み**。Green は `docs/process/gate-evidence/green-public-think.txt`（19 本・rc 0）
