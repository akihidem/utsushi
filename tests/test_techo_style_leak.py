"""手帖のゴシックと角丸を、手帖の外へ漏らさない（#126）。

なぜ試験にするか: 手帖の STYLE は「机に置いて離れて読むため」の物なのに、頭の帯にも、読む頁の /gallery にも掛かっていた。
./run.sh はブラウザなしで動くので、ここでは頁に載る CSS を見る（書体と角の実際の値はブラウザで測って帳面に書いた）。
"""
import os
import re
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import skin  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    return urllib.request.urlopen(base + path).read().decode()


# 頭の帯と足は骨の物なので、頁の本文の書体を受け継がない
assert re.search(r"\.nav[^{}]*\{[^}]*font-family:\"Noto Serif CJK JP\"", skin.NAV_STYLE), "頭の帯は骨の書体を自分で持つ"
assert re.search(r"\.foot[^{}]*\{[^}]*font-family:\"Noto Serif CJK JP\"", skin.NAV_STYLE), "足も骨の書体を自分で持つ"

# /gallery は読む頁なので、手帖の皮を掛けない
gallery = get("/gallery")
style = gallery[gallery.index("<style>"):gallery.index("</style>")]
assert not re.search(r'<body class="[^"]*\btecho\b', gallery), "手帖の印を付けない"
assert "Noto Sans JP" not in style and ".techo" not in style, "手帖の STYLE を載せない"
own = style[style.index(".gallery"):]
radius = re.findall(r"border-radius:([^;}]+)", own)
assert all(v.strip() == "0" for v in radius), radius
assert '<div class="gallery">' in gallery and 'class="panel" id="ageta"' in gallery

# 手帖の本文のゴシックは本人の指定（11-04）なので残す
techo = get(f"/toy/{G}/techo/kiroku")  # 頭の帯を持つのは手帖の記録の頁（作る頁は帯なしの 1 手 1 画面、#87）
# 手帖の書体は他の頁と同じ明朝（本人のサイトの見直し 11-07 22:16「のこす、手帖、のフォントが違う。」）。皮が漏れない事は前のまま見る
assert re.search(r'<body class="[^"]*\btecho\b', techo) and 'body.techo{font-family:"Noto Serif CJK JP"' in techo and "Noto Sans JP" not in techo
server.shutdown()
print("ok")
