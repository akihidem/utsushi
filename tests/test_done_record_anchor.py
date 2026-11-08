"""送った後の戻り先（play_server.Handler._done）。統括の割り振り 11-08（つくるの続き・別の目の確かめの気づき）。

見る事:
1. 記録の札（錨が記録の番号 R- と 4 桁以上）へ戻す時は、手帖の記録の頁のその札（#R-…）に着く。前は記録の並びの頭（#mine）に着き、どの札か探す事になった。
   番号が 5 桁でも同じ道（R-\\d{4,}）。形の違う錨は札の道にしない
2. 記録を残した時（fresh）は、札へ戻す時も手帖へ戻す時（back=techo・JS の無い画面の のこす）も、fresh の合図と写真の鍵を閉じる行（_up_close）を付ける。
   付けないと、同じ機械の次の人が前の人の写真の口を持ったままになる（test_photo_owner_only・test_who_fresh と同じ線）
3. fresh でない時は、写真の鍵を閉じない
"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import play_server  # noqa: E402

CLOSE = ("Set-Cookie", "utsushi_up=; Max-Age=0")


class Stub:
    """_done が使う所だけを持つ受け手（送った物を控える）。"""

    def __init__(self):
        self.sent = None

    def _send(self, code, body, headers=()):
        self.sent = (code, dict(headers).get("Location", ""), list(headers))

    def _up_close(self):
        return [CLOSE]


def done(**kw):
    s = Stub()
    play_server.Handler._done(s, "NDL-1187053-R0000005-L", "残しました", **kw)
    return s.sent


# 1
for rid in ("R-0001", "R-12345"):
    code, loc, _ = done(anchor=rid)
    # at= にも番号を渡し、返事の文をその札の頭に出す（techo_site.records_page）
    assert code == 303 and loc.startswith("/toy/NDL-1187053-R0000005-L/techo/kiroku?") and f"&at={rid}" in loc and loc.endswith(f"#{rid}"), (rid, loc)
code, loc, _ = done(anchor="R-12")
assert "/techo/kiroku" not in loc, ("形の違う錨を札の道にした", loc)  # 形の違う錨は前からの玩具の頁の道（at と錨）へ
# 2
for kw in ({"anchor": "R-0001"}, {"back": "techo"}, {"back": "techo", "anchor": "kinyu"}):
    code, loc, headers = done(fresh=True, **kw)
    assert "fresh=1" in loc and CLOSE in headers, (kw, loc, headers)
code, loc, _ = done(back="techo", fresh=True)
assert loc.startswith("/toy/NDL-1187053-R0000005-L/techo/kiroku?") and loc.endswith("#mine"), loc
code, loc, _ = done(back="techo", anchor="kinyu", fresh=True)
assert "&at=kinyu" in loc and loc.endswith("#kinyu"), loc
# 3
for kw in ({"anchor": "R-0001"}, {"back": "techo"}):
    code, loc, headers = done(**kw)
    assert "fresh=1" not in loc and CLOSE not in headers, (kw, loc)
print("ok 送った後の戻り先: 記録の札は手帖の記録の頁のその札（#R-…・4 桁以上）・残した時は札へも手帖へも fresh と写真の鍵を閉じる行・残さない時は閉じない")
