"""デモ動画の台本の順（docs/demo/plan.md の 4）を 1 か所に置く。

なぜ別のファイルか: 書き出し（build）・仮の拍（beat）・曲の拍合わせ（song）の 3 つが同じ順を読む。
どれかが持つと、互いを読み合う形になり、順が食い違っても気づけない。

本人の決定（11-05）「哲学よりの動画にして」で、機能の説明の場面 4 を外し、言葉の札（demo.words）を足した。
本人の言葉（11-05）「今話してるこの部分が今回のハッカソンの核になる！！」で、3 段と輪（demo.core）を筋の真ん中に置いた。
本人の言葉（11-05 夕）で順番が決まった（手で作る楽しさに気づく事が最初で、AI が良くなるのは後）。言葉の札を word_touch と word_ai に絞り、
空いた尺は作る場面（scene3・core_make・core_keep）に回した。組み立ては、手で作る所を長く → 持ち寄り → みんなの工夫で AI が次をよくする。
"""
import importlib

# 言葉の札（word_*）とつなぎの字幕の札（bridge）と終わりの字幕の札（close）と問いの札（ask）は demo.words、核の一周の図と画面（core_*）は demo.core で描く。
# 終わりは、初めと同じ字幕（close）→ 問い（ask）の順（本人の決定 11-05）。
# つなぎ 2 の輪（core_loop）は持ち寄り（core_gallery）の次（本人の決定 11-05）。作った人の言葉で版が変わる場面（scene6）は、手で作る側なので持ち寄りの前に置く。
SCENES = ["flip", "scene2", "bridge", "word_touch", "core_map", "scene3", "core_make", "core_keep", "core_voice", "scene5", "scene6", "core_gallery",
          "core_loop", "word_ai", "scene7", "close", "ask"]


def load_scene(name):
    """場面の名前から、CUES・DURATION・main を持つ物を返す。"""
    if name.startswith("word_") or name in ("bridge", "close", "ask"):
        mod = importlib.import_module("demo.words")
        return mod.scene_module(name) if hasattr(mod, "scene_module") else mod
    if name.startswith("core_"):
        mod = importlib.import_module("demo.core")
        return mod.scene_module(name) if hasattr(mod, "scene_module") else mod
    return importlib.import_module(f"demo.{name}")
