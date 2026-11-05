"""デモ動画の台本の順（docs/demo/plan.md の 4）を 1 か所に置く。

なぜ別のファイルか: 書き出し（build）・仮の拍（beat）・曲の拍合わせ（song）の 3 つが同じ順を読む。
どれかが持つと、互いを読み合う形になり、順が食い違っても気づけない。

本人の決定（11-05）「哲学よりの動画にして」で、機能の説明の場面 4 を外し、言葉の札（demo.words）を足した。
本人の言葉（11-05）「今話してるこの部分が今回のハッカソンの核になる！！」で、3 段と輪（demo.core）を筋の真ん中に置いた。
本人の言葉（11-05 夕）で芯を「自分の手で触れる物を作る楽しさ」に置き直し、言葉の札を word_touch と word_ai に絞った。
札を減らした分は、作った物が持ち寄られる場面（core_gallery）と、AI が動きを強める輪（core_loop）の尺に回した。
"""
import importlib

# 言葉の札（word_*）と問いの札（ask）は demo.words、核の一周の図と画面（core_*）は demo.core で描く。
SCENES = ["flip", "scene2", "word_touch", "core_map", "scene3", "core_make", "core_keep", "core_voice", "scene5", "core_gallery", "scene6",
          "word_ai", "core_loop", "scene7", "ask"]


def load_scene(name):
    """場面の名前から、CUES・DURATION・main を持つ物を返す。"""
    if name.startswith("word_") or name == "ask":
        mod = importlib.import_module("demo.words")
        return mod.scene_module(name) if hasattr(mod, "scene_module") else mod
    if name.startswith("core_"):
        mod = importlib.import_module("demo.core")
        return mod.scene_module(name) if hasattr(mod, "scene_module") else mod
    return importlib.import_module(f"demo.{name}")
