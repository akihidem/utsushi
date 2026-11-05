"""デモ動画の台本の順（docs/demo/plan.md の 4）を 1 か所に置く。

なぜ別のファイルか: 書き出し（build）・仮の拍（beat）・曲の拍合わせ（song）の 3 つが同じ順を読む。
どれかが持つと、互いを読み合う形になり、順が食い違っても気づけない。

本人の決定（11-05）「哲学よりの動画にして」で、機能の説明の場面 4 を外し、言葉の札（demo.words）を足した。
本人の言葉（11-05）「今話してるこの部分が今回のハッカソンの核になる！！」で、3 段と輪（demo.core）を筋の真ん中に置いた。
本人の言葉（11-05 夕）で順番が決まった（手で作る楽しさに気づく事が最初で、AI が良くなるのは後）。組み立ては、手で作る所を長く → 持ち寄り → みんなの工夫で AI が次をよくする。
本人の指示（11-05 20:07）と語り（20:04）で、始まりを問いと職人のおもちゃ、その後に語りの形にした。
本人の方針（11-05 20:10）「たくさん見る審査員の認知負荷を減らす方針が1番最初。癒し系で。」が一番の決め方。足りない時は速めずに減らす。
本人の決定（11-06）「本人の言葉の札は戻す。同じ秒だけ他を削って入れて」で、word_touch を手で作る場面の直前（外す前と同じ所）へ戻した。
"""
import importlib

# 語りの札（talk_*）・言葉の札（word_*）・つなぎの字幕の札（bridge）・終わりの字幕の札（close）・問いの札（ask）は demo.words、核の一周の図と画面（core_*）は demo.core で描く。
# 始まりは本人の指示（11-05 20:07）の問いと職人のおもちゃ（opening）。つなぎ 2 の輪（core_loop）は持ち寄り（core_gallery）の次（本人の決定 11-05）。
# 終わりは、初めと同じ字幕（close）→ 問い（ask）の順（本人の決定 11-05）。
SCENES = ["opening", "talk_toys", "talk_lost", "scene2", "flip", "talk_physics", "talk_claude", "word_touch", "scene3", "core_make", "core_keep", "scene5", "core_gallery",
          "core_loop", "word_ai", "scene7", "close", "ask"]
# 3 分に入らないので外した場面（本人が戻すかを決める。コードは残すので、SCENES へ戻せば動く）。docs/demo/plan.md の 4 に書いた。
LEFT_OUT = ("core_map", "core_voice", "scene6", "bridge")
# 外へ出す前に片づける物（印のほか）。demo.build が build.json の not_for_release に載せる。
BEFORE_RELEASE = ("クレジットの隅の札の行が本人の確認待ち（docs/demo/plan.md の 4）",)


def load_scene(name):
    """場面の名前から、CUES・DURATION・main を持つ物を返す。"""
    if name.startswith(("word_", "talk_")) or name in ("bridge", "close", "ask"):
        mod = importlib.import_module("demo.words")
        return mod.scene_module(name) if hasattr(mod, "scene_module") else mod
    if name.startswith("core_"):
        mod = importlib.import_module("demo.core")
        return mod.scene_module(name) if hasattr(mod, "scene_module") else mod
    return importlib.import_module(f"demo.{name}")
