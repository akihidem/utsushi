"""デモ動画の台本の順（docs/demo/plan.md の 4）を 1 か所に置く。

なぜ別のファイルか: 書き出し（build）・仮の拍（beat）・曲の拍合わせ（song）の 3 つが同じ順を読む。
どれかが持つと、互いを読み合う形になり、順が食い違っても気づけない。

本人の決定（11-05）「哲学よりの動画にして」で、機能の説明の場面 4 を外し、言葉の札（demo.words）を足した。
本人の言葉（11-05）「今話してるこの部分が今回のハッカソンの核になる！！」で、3 段と輪（demo.core）を筋の真ん中に置いた。
本人の言葉（11-05 夕）で順番が決まった（手で作る楽しさに気づく事が最初で、AI が良くなるのは後）。組み立ては、手で作る所を長く → 持ち寄り → みんなの工夫で AI が次をよくする。
本人の指示（11-05 20:07）と語り（20:04）で、始まりを問いと職人のおもちゃ、その後に語りの形にした。
本人の方針（11-05 20:10）「たくさん見る審査員の認知負荷を減らす方針が1番最初。癒し系で。」が一番の決め方。足りない時は速めずに減らす。
本人の決定（11-06）「本人の言葉の札は戻す。同じ秒だけ他を削って入れて」で、word_touch を手で作る場面の直前（外す前と同じ所）へ戻した。
本人の決定（11-06、カード 125217）で、前半を表（サイトと作る体験）、後半を「では裏でどう動いているか」（型紙の生まれ方・工夫が次の版になる輪・作り方）にした。
本人の言葉（11-06）「最初にフロントを見せて、では裏でどうシステムがうごいているか見て行こう、という構成がわかりやすいかも」が元。
境目の札（border）の字は「ここからは、裏のしくみ。」、その 3 秒は始まり（opening）を 11.6 → 8.6 秒に縮めて作った（どちらも本人の決定）。
語りの後ろの 2 文（talk_physics・talk_claude）は、文の順を変えずに後半の頭へ移した。どの場面の字も変えていない。
"""
import importlib

# 語りの札（talk_*）・言葉の札（word_*）・つなぎの字幕の札（bridge）・終わりの字幕の札（close）・問いの札（ask）は demo.words、核の一周の図と画面（core_*）は demo.core で描く。
# 始まりは本人の指示（11-05 20:07）の問いと職人のおもちゃ（opening）。つなぎ 2 の輪（core_loop）は、前は持ち寄り（core_gallery）の次だった（本人の決定 11-05）。
# 表と裏に分けた（本人の決定 11-06）ので、今は持ち寄りの後に境目と語りの後ろの 2 文が入り、その次になる。
# 終わりは、初めと同じ字幕（close）→ 問い（ask）の順（本人の決定 11-05）。
# 前半・表: 始まり → 語り（玩具と失われた事・江都二色）→ 絵は止めて残した → 本人の言葉 → 開く・作る・残す・動いた・持ち寄る。
# 境目: border。後半・裏: 語りの後ろの 2 文 → 輪 → 本人の言葉 → 断りとクレジット。終わり: 初めと同じ字幕 → 問い。
# 「紙で作って、動いた。」（scene5）は作る頁（core_make）のすぐ後（窓口の決定 11-07。デモが教育の原形をどこで見せるかの確かめの推し 2）:
# 作る → 動いた → 残す → 持ちよる の順になり、画面が 40 秒続く塊が割れる。前は 残す（core_keep）の後だった
FRONT = ["opening", "talk_toys", "talk_lost", "scene2", "flip", "word_touch", "scene3", "core_make", "scene5", "core_keep", "core_gallery"]
BACK = ["talk_physics", "talk_claude", "core_loop", "word_ai", "scene7"]
SCENES = [*FRONT, "border", *BACK, "close", "ask"]
# 3 分に入らないので外した場面（本人が戻すかを決める。コードは残すので、SCENES へ戻せば動く）。docs/demo/plan.md の 4 に書いた。
LEFT_OUT = ("core_map", "core_voice", "scene6", "bridge")
# 外へ出す前に片づける物（印のほか）。demo.build が build.json の not_for_release に載せる。
BEFORE_RELEASE = ()  # 字幕とクレジットの隅の札の行は本人が決めた（11-06）

# 届いたら差し込む物の置き場（本人の決定 11-06: 手だけの映像を語りの場面の後ろに敷く・語りは本人が自分の声で読む）。
# まだ届いていない間は、今の映す物のまま書き出し、build.json の slots に「待ち」と残す（置き場の印）。外へ出す事は止めない:
# 手と声は動画を良くする物で、無くても台本は組める（撮る物の一覧のとおり）。職人のおもちゃの動画（opening）だけが外へ出す前に要る。
# 名前は撮る物の一覧と語りを読む 1 枚の名前のまま（手 A〜E、声 A1〜A6）。置き場は git の外（画像・動画・声は repo に入れない）。
# hands: (撮る物の名前, 使う秒) の並び。場面の頭から順に敷き、使い切った後は今の地（紙の地・図）に戻る。
# voice: 1 文ずつのファイル。場面の頭から順に流す。場面の秒に入らない時は名指しして止める（速めない）。
SLOT_DIR = "out/demo/slots"
SLOTS = {
    "talk_toys": {"hands": (("A", 6.0), ("B", 5.8)), "voice": ("A1", "A2")},
    "talk_lost": {"hands": (("C", 12.2),), "voice": ("A3",)},
    "scene2": {"voice": ("A4",)},
    # 13 の手は 8 → 10.4 秒にし、後ろの画面を 原画 → 型紙 の 2 枚にした（窓口の決定 11-07。確かめの推し 1。字と 16 秒は変えない）:
    # D 切る・折る・組む → E 手で動かす → F 作った物を手のひらに（「自分の手のひらで考える」の下）→ H 原画 → I 型紙（原画を写した型紙＝まねぶ）
    "talk_physics": {"hands": (("D", 5.0), ("E", 3.8), ("F", 1.6), ("H", 2.8), ("I", 2.8)), "voice": ("A5",)},
    "talk_claude": {"voice": ("A6",)},
}
HANDS_EXT, VOICE_EXT = ".mp4", ".m4a"
# 効果音（統括の頼み 11-07: 音楽の担当が公有の音から作った 切る・折る（の代わり）・塗る（の代わり）を、手の映像の音ハメに）。
# (場面, 場面の頭からの秒, 音の名, 大きさ dB) の並び。置き場は SFX_DIR/<名>.wav（git の外。grove の state/demo-sfx から写す）。
# 映像の中身に合う所だけに置く: 10 の写真の 1 枚目（切る）と 2 枚目（組む）、13 の手の D（虎の胴を組む）と E（筒から扇が開く）。
# 塗る所は今の映像に無いので、塗るの代わりの音は置かない。語りと重なる 13 は 5 dB 下げる（音楽の担当の目安 4〜6 dB）。
# どの候補を使うかは人が耳で選ぶ（切る cut-1・cut-2・cut-snip、折るの代わり fold-1・fold-2・fold-3）。名前を替えれば差し替わる
SFX_DIR = "out/demo/slots/sfx"
SFX = (
    ("scene5", 0.5, "cut-1", 0.0),
    ("scene5", 2.2, "fold-1", 0.0),
    ("talk_physics", 1.0, "fold-2", -5.0),
    ("talk_physics", 6.2, "fold-3", -5.0),
)


def load_scene(name):
    """場面の名前から、CUES・DURATION・main を持つ物を返す。"""
    if name.startswith(("word_", "talk_")) or name in ("bridge", "close", "ask", "border"):
        mod = importlib.import_module("demo.words")
        return mod.scene_module(name) if hasattr(mod, "scene_module") else mod
    if name.startswith("core_"):
        mod = importlib.import_module("demo.core")
        return mod.scene_module(name) if hasattr(mod, "scene_module") else mod
    return importlib.import_module(f"demo.{name}")
