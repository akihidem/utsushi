"""デモ動画の台本の順（docs/demo/plan.md の 4）を 1 か所に置く。

なぜ別のファイルか: 書き出し（build）・仮の拍（beat）・曲の拍合わせ（song）の 3 つが同じ順を読む。
どれかが持つと、互いを読み合う形になり、順が食い違っても気づけない。

本人の決定（11-05）「哲学よりの動画にして」で、機能の説明の場面 4 を外し、言葉の札（demo.words）を足した。
"""
import importlib

# 言葉の札（word_*）と問いの札（ask）は 1 つのファイル（demo.words）で描く。絵の形が同じで、違うのは字だけなので。
SCENES = ["flip", "scene2", "word_make", "scene3", "scene5", "word_fix", "scene6", "word_ai", "scene7", "word_who", "ask"]


def load_scene(name):
    """場面の名前から、CUES・DURATION・main を持つ物を返す。"""
    if name.startswith("word_") or name == "ask":
        mod = importlib.import_module("demo.words")
        return mod.scene_module(name) if hasattr(mod, "scene_module") else mod
    return importlib.import_module(f"demo.{name}")
