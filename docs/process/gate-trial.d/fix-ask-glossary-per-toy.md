## 手帖の「こまった」の語の表を御来迎の紙の時だけ使い、凡例をその玩具の型紙が刷る字から作る（修正の担当、fix/ask-glossary-per-toy、11-08 夕）

- 目的: 公開デモ（ad6d67f9）の虎の作る頁で「谷折り・山折り」と聞くと、答えが御来迎の「筒と扇」の事を言った（11-08 に動画の作業の時に見つかった）。違う玩具の中身が渡らないようにする
- 出所: `src/api/ask.py` の語の表 GLOSSARY（谷折り・山折り・色の境・蛇腹の字が御来迎の紙の字）をどの玩具にも返していた。「谷折り・山折り」は語そのものを尋ねる形に当たるので、Claude を呼ばずにこの字が返った。Claude に渡す `sheet_context` の凡例の字も、全部の玩具に「線の無い面（外筒と扇）は色の境で折る」と前の谷と山の言い方を渡していた
- どうしたか: 語の表の字は本人の確かめの字なので一字も替えず、使う玩具を扇の紙（slider_fan・御来迎）に絞った。ほかの玩具の語の問いは、その紙の組み方と凡例を渡して Claude に聞く（鍵が無ければ断りだけ）。凡例は compose の谷と山の言い方（その紙が刷る字）から作り、色の境の 1 句は扇の紙だけに添える（instructions が蛇腹と色の境の絵を刷るのも扇の紙だけ）
- ゴールの要件: tests/test_ask.py の虎の節（虎の語の問い 4 つに語の表を返さない・Claude に渡す紙の字に 筒と扇・外筒・扇・蛇腹（横から）・色の境 が無い・凡例はその紙が刷る谷と山の言い方・御来迎は前のとおり語の表で答える）
- 検証ゲート: **済み**。Red: 今の main（d71e15c7）の木に新しい試験だけを置いて rc 1（虎の「谷折り・山折り」に御来迎の筒と扇の字が返った。`docs/process/gate-evidence/red-ask-glossary-per-toy.txt`）。Green: rc 0（`green-ask-glossary-per-toy.txt`）
- エビデンスゲート: 関わる試験 22 本（test_api_review_fixes・test_ai_feedback・test_call_timeouts・test_ask_floor・test_ask・test_budget_after_period・test_failure_log・test_demo_walk・test_demo_walk_all・test_kumikata_words・test_making_log・test_loop1_round・test_own_form_gone・test_public_open・test_reply_visible・test_tsukuru・test_voice_walk・test_words_card_1106・test_write_limit・test_techo・test_wording・test_reader_words）が rc 0
- 確かめていない事: 本物の Claude が虎の凡例で語の問いに答えた字（試験は偽の答え手）。書き出しの静かな手帖（web.techo の out/techo/index.html。play_server からは出していない）の頁の台本は、今も語の表を玩具を問わずに使う（この PR の外）
- マージ後の書き戻し: Issue は立てていない
