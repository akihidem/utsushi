# J-030 届け先はいろんな国の人（外国の人に届く形の方針）

- **状態**: 本人の方針（2026-11-05、窓口を通して届いた）。段 1 は本人の指示「実装までやって」で作る。この文書は作る側が方針の形にした物で、紹介文の文面は本人の採否待ち
- **本人の言葉**: 「ぜっかく江戸時代のおもちゃを作れるようにするから、このおもちゃの存在を知って欲しい。いろんな国の人に知って欲しい。」
- **範囲の決まり**: 凍結の床（必須 2 種の今の版の紙）を壊さない範囲で

## 今の壁（11-05 の code を見て数えた）

| 壁 | 今の形 | 外国の人に起きる事 |
|---|---|---|
| サイトの字 | 全部日本語 | 何の頁か分からない。図だけは伝わる |
| 型紙と手順の紙の字 | 日本語で刷る。組み方の文も日本語 | 刷れても組めない。部品の番号と折り線の凡例の絵だけが頼り |
| 紙の大きさ | A4 と B4 だけ | 米国とカナダの Letter（216×279mm）は A4 より 18mm 低い。紙の余白は上下とも 1cm ほどなので、100% で刷ると端が切れる見込み（#109 の枝の型紙の検分の余白から出した見込みで、刷って確かめていない）。用紙に合わせて刷ると 94% ほどになり、物差しの 10cm が合わない |
| 材料の名前 | 竹串・たこ糸・粘土 | 別の物で足りるが、そう書いていない |
| 聞く口 | 手元の答えは日本語の語の表。鍵のある時だけ Claude で、返事の指示も日本語 | 英語で聞くと、鍵が無ければ答えられない。鍵があっても日本語で返す。「仕組みには答えない」の門の語も日本語だけなので、英語の問いは素通りする。だから段 1 の英語の頁には聞く口を置かない |
| 玩具の名前と歌 | 名前は多くが見立て。確かめた読みは必須の 2 種だけ | 英語の名前は無い。歌は言葉遊びで、訳すと別物になる |
| 動画の字幕 | 日本語を絵に焼き込む（src/demo の各場面） | 音声の説明も無いので、字が読めないと筋が分からない |
| README・提出の文 | 日本語。エンジンの README に英語が 1 文 | repo を開いても入口が無い |

## 方針

1. **絵を先に。** 字の読めない人にも図は手がかりになる見込みで、入口も紹介も絵を最初に出す。伝わるかは確かめていない（11-04 の試行では、日本語の話者も原図を見て詰まった）。
2. **字の少ない道を太くする。** 開いたらすぐ型紙を刷れる道（#242）と、手順の絵を使う。訳を増やすより先に、この道を使う。手順の絵だけで組めるかは見込みで、確かめていない。
3. **同じ線を、どの言葉でも守る。** 紙で動いても昔の作り方の証明にはならない。学習の効果を主張しない。どの案も答えと言わない。成績にしない。英語の文でも同じ。短くする時に、この断りを落とさない。
4. **訳は訳と分かるように。** 確かめた読み（原文）を正本に置き、英語は「訳（案）」の印を付ける。歌の訳は意味の手がかりで、原文の代わりにしない。Claude の訳は人が確かめるまで案。
5. **見慣れない物として飾らない。** 「不思議な東洋の玩具」のように売らない。作って確かめられる玩具として出す。御来迎のような信仰に関わる名は、短く意味を添える。
6. **凍結の床を守る。** 必須 2 種の今の版の紙は変えない。英語の紙は別の道で足し、日本語の紙の指紋（tests/test_floor_pin.py）が同じである事を見る。
7. **外国の人の記録は、同意の形を決めてから。** 子どもの情報の決まりは国で違う（research/31 の 4）。まず見る・刷る・作るまでを開き、上げる口は開かない。

## 段

| 段 | 中身 | 凍結との関係 | 重さの見積もり |
|---|---|---|---|
| 0（提出まで） | README の先頭に英語の紹介。提出の文に英語の概要。動画に英語の字幕の別ファイル（絵を作り直さない）。絵の出典を英語でも書く（NDL の記録に英語の帰属の文がある） | code に触らない | 半日。英語の字幕は撮影の後 |
| 1（本人の指示「実装までやって」） | サイトに英語の入口（/en）と玩具ごとの頁（/en/toy）。紹介・図・手順の文の英語・刷る口。紙は日本語のままと断る | 紙は変えない | 半日〜1 日 |
| 2（提出の後） | 英語の型紙と手順の紙（別の道。Letter も）。81 種の英語の名前（見立ての印つき）。聞く口を聞かれた言葉で返し、門の語も英語に広げる。歌の訳。エンジンの README の英語 | 床の試験で指紋を見ながら | 2〜3 日 |
| 3（同意の形の後） | 外国の人の記録と写真。博物館などへの紹介 | 同意の形と、紹介先への連絡は本人が決める | 未定 |

比べた代案:

| 代案 | 捨てた理由 |
|---|---|
| 全部の頁を 2 言語にする | 提出までに質が揃わない。訳の確かめが追いつかない。半端な訳は、線（断り）を落とす危険が大きい |
| 自動翻訳に任せる | 歌と断りの文が崩れる。「証明にはならない」が抜けても気づけない |
| 英語の皮を 3 つ目のサイトにする | 本人の決定（白と黒の 2 サイト）と別の軸で、組み合わせが増える。言葉はサイトの見た目と分ける |
| 型紙の今の版に英語を足す | 凍結の床に当たる |

## 英語の紹介文（案。本人の採否待ち）

書名の読みは国立国会図書館の書誌の「エド ニシキ」に合わせた。数は記録の 83 種と本人の 88 種のどちらでも正しい「more than 80」にした。

予想の段を無くす本人の決定（#242）に合わせて書き直した。別の目で読んだ指摘も入れた（虎を組み上げた記録は無い。複写の別の書物が御来迎の仕組みに触れるので「書かれていない」とは言わない。狂歌の記録は無いので comic と書かない。"answers" は解答に読めるので responds にした）。

**一文**

> The toys in a 1773 Japanese picture book come with drawings and short poems, but the book does not explain how they worked. Print a paper model, build it, and test an idea. A model that moves does not prove how the original was made.

**短い紹介（README の先頭・提出の概要）**

> *Edo nishiki* (1773) is a Japanese picture book of toys. It has pictures and short poems, but it does not explain how the toys worked. utsushi turns those pictures into printable paper models, based on untested ideas about how they moved. Print one, build it, try it, and write down what you saw. The paper responds first, and after you have explained what you saw, AI can respond too. A paper model that moves does not prove how the original was made.

**少し長い紹介（サイトの英語の頁）**

> In 1773, the artist Kitao Shigemasa published a book of toys in Edo, today's Tokyo. The book, *Edo nishiki*, shows more than 80 toys with short poems, but it does not explain how they worked.
>
> utsushi lets you test ideas with your hands. Pick a toy and print a paper template right away. Each idea has its own template, and none of them is the answer. Cut, fold, glue, and try it. If it does not move, that is a result too: write down what happened, change one thing, and print the next version. You can also see what other people have made.
>
> Two toys have full templates, in Japanese only: the Goraigo (roughly, "welcoming descent"), a tube with a fan, and a tiger based on old papier-mâché toys. An earlier Goraigo moved in one trial with adults. No one has finished the tiger. The others are untested drafts, and their names are our guesses.
>
> A paper model that moves does not prove how the original was made. These are versions for experimenting, not reconstructions.
>
> Pictures: 1931 facsimile of the 1773 book, National Diet Library, Japan (public domain). The drawings on the templates are redrawn.

**そのまま出せない言葉の候補（どれも本人の確認が要る）**

| 原文 | 英語の案 | 確認が要る理由 |
|---|---|---|
| AI は鏡。江戸の絵を映すことはできるが、映すだけでは遊べない。 | AI is a mirror. It can reflect a picture from Edo, but you can't play with a reflection. | 本人の言葉の訳 |
| 自分で作れて、壊せて、直せる、というのが面白いと思う。 | You can make it yourself, break it, and fix it. That is the fun of it. | 本人の言葉の訳。11-05 の決まりで、サイトや概要で使う文面の採否は本人 |
| 自分で作ったから直せる。身の回りにあるもので作るから壊しても直せる。壊せるなら丁寧に扱える | You made it, so you can fix it. It's made from things around you, so if it breaks you can fix it. If you're free to break it, you can treat it with care. | 本人の言葉の訳。同じ決まり |
| 誰のために今作ってるか？という質問に対しては、手を動かす楽しさを忘れた人のために作っている。 | For people who have forgotten the joy of working with their hands. | 本人の言葉の訳。同じ決まり。デモ動画の終わりの質問の材料にもなるので、字幕の訳と合わせる |
| utsushi | 写し・映し（a copy, a reflection） | 語の意味は書けるが、この名を選んだ理由は本人から聞いていない（J-014）ので、理由としては書かない |

## 使う時の呼び名（案）

| 日本語 | 英語の案 | 根拠 |
|---|---|---|
| 江都二色 | *Edo nishiki* (1773) | NDL の書誌の読み。British Museum の目録にも同じ読みの項がある（概要だけ見た） |
| 北尾重政 | Kitao Shigemasa | 複製の奥付と NDL の書誌 |
| 御来迎 | the Goraigo（信仰に関わる名なので、意味を短く添える） | 確かめた読みは「御来迎」まで。英語の添え書きは案 |
| 張子の首振り虎 | a tiger based on old papier-mâché toys（hariko no kubifuri tora） | 英語は説明の訳で、定まった名ではない。動き方の語（nodding）は頁の頭では使わない。"paper tiger" は慣用句なので避ける |
| 型紙・手順の紙 | paper template・instruction sheet | 案。pattern は裁縫に読める（書き手の推測） |

## 本人に決めてもらう点

1. 英語の紹介文の採否と直し。英語を母語とする人に読んでもらうか。
2. 動画の英語: 字幕の別ファイルでよいか、英語の字幕を焼き込んだ版も作るか。推し: 別ファイル（作り直しの危険が無い。撮影の日程に当たらない）。

## 確かめていない事

- 外国の人に見てもらった確認。英語の文を英語の母語の人が読んだ確認。
- Letter で刷って切れるか（A4 の紙で出した見込みだけ）。
- 提出の要項が英語を求めているか（要項と照らす一覧は U-20 の残り）。
- 図と手順の絵が、字の読めない人に実際に伝わるか。
- 本物の Claude API はまだ 0 回なので、英語の文の "AI can respond" は作りの説明で、動かして確かめた事ではない。
- "more than 80" は棚卸しの見立てを含む（人の確認は無い）。

## 出典

- 国立国会図書館サーチの書誌（読み「エド ニシキ」）: https://ndlsearch.ndl.go.jp/en/books/R100000002-I000000739175
- British Museum の項（ukiyo-e.org の写し。概要だけ見た）: https://ja.ukiyo-e.org/image/bm/AN00296732_001_l
