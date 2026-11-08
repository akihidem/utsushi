## 作業の頁を「聞く」だけの経路に作り替える（修正の担当、issue/kasane-ask、11-08 夕）

- 目的: 本人の言葉（11-08）「3D 重ねずに、質問もできるだけにしよう。質問した時のその瞬間の写真を何枚か撮って、音声を文字にして認識して、クロードが考えて答えを音声で出すようにする。iPhone のカメラと HMD で使えるようにする。記録はここでは取らず、質問のための経路と割り切る。」。本人の答え（11-08）「4 つとも推しのとおり。」（合言葉のある場だけ・印の字「カメラで聞く」・新しい字 5 つ・3D は出さない）と「字の替え 11 か所も、カメラの区切りを外す事も、推しのとおり。」
- どうしたか: 頁（src/web/hmd.py）は今の手順の字 1 行と ← →・大きな「聞く」・こたえだけにした。押した間だけ声を録り（12 秒まで）、写真は後ろのカメラと分かる時だけ 3 枚まで撮る（HMD の道は撮らない）。送るのは止めた時の 1 回（POST /toy/<玩具>/kasane/ask）。声はこのサーバの中で常駐の作り手（asr_worker --serve・src/omochae/asr_serve.py）が字にし、字と写真を Claude（src/api/kasane.py）に渡して、答えの字を返す。頁は答えを出して端末の読み上げで読む。making_log・talk_log・records を呼ばず、声も字もファイルにしない。公開の場は「この場では聞けません」。3D・重ねる・中を見る・声の操作・ここで止まった（カメラの区切り）は外した
- 作りながら替えた所: 聞く口の玩具ごとの中身（語の表は御来迎の紙の時だけ・凡例はその玩具の型紙が刷る字）。公開デモの虎で「谷折り・山折り」に御来迎の答えが返った件から（前の口は別の PR で直す）。英語の印の字は幅 320 に収まる「Ask by camera」に（「Ask with the camera」は 3 行に折れて切れた・green-kasane-ask-page に残した）
- ゴールの要件: tests/test_kasane_ask.py（作り手の字・伏せ・時間切れ・掃除／受け口の断りと上限と回数／記録を取らない／渡す物／玩具ごとの中身）・tests/test_hmd.py（頁の字と作り・道・Chrome で聞く 3 つの道・5 つの大きさ × 2 つの玩具 × 2 つの道の置き場・手帖の印の測り）
- 検証ゲート: **済み**。Red: 今の main（095fb28b）の木に新しい試験だけを置いて、どちらも rc 1（聞く口と頁の形が無い。`docs/process/gate-evidence/red-kasane-ask.txt`・`red-kasane-ask-page.txt`）。Green: rc 0（`green-kasane-ask.txt`・`green-kasane-ask-page-2.txt`。`green-kasane-ask-page.txt` は英語の印の字が切れた時の rc 1 の控え）
- エビデンスゲート: 関わる試験（test_otona・test_clips_client・test_kumitate_hint・test_kumitate_tour・test_call_timeouts・test_techo_step・test_en_all・test_easy_all・test_easy_part1・test_easy_ruby・test_public_open・test_write_limit・test_failure_log・test_budget_after_period）が rc 0。./run.sh の全部は PR の本文に書く
- 測り: この機械（16 core・負荷 30 ほど）で、4 秒の機械の読み上げの問いを字にするのに large-v3-turbo で 13 秒・small で 2 秒（声が機械の読み上げなので、字の正しさは測れていない）
- 確かめていない事: 実機の iPhone の Safari（録りと読み上げが続けて動くか・audio/mp4）・Vision Pro の Safari・負荷の無い機械の待ち時間・本物の Claude の答えの字と待ち時間（試験は偽の答え手）・人の目
- マージ後の書き戻し: Issue は立てていない
