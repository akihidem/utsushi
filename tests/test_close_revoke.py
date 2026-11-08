"""「この画面をとじる」で、所有者の印をサーバの側でも失効させる（本人の指示 11-08 の安全の事項 6）と、所有者の cookie の Secure（事項 7）。

本人の条件: サイトの機能は維持した状態で、見た目、挙動は変えずに、セキュリティの事項にだけ対応する。
見る事:
1. 記録の鍵（records.claim）と写真の鍵（media_review.claim）を持つ画面が POST /close を押すと、同じ鍵の古い印（写した cookie）が拒まれる
   （records.mine と写真の見分けが通さない）。前は cookie を消すだけで、写した鍵が期限まで生きた
2. ほかの画面の鍵は失効しない（とじた画面の鍵だけ）。鍵の無い画面の /close も同じ返事（303）で、何も失効しない
3. 所有者の cookie は、合言葉なしの公開の場でも Secure（前は合言葉付きの場だけ）。手元の場は今までどおり Secure を付けない
4. とじた後の返事の形（行き先・cookie を消す行）は前と同じ
"""
import os
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import media_review, records  # noqa: E402
from web.play_server import serve  # noqa: E402


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


opener = urllib.request.build_opener(NoRedirect)


def close(base, cookie=""):
    headers = {"Origin": base, "Content-Type": "application/x-www-form-urlencoded"}
    if cookie:
        headers["Cookie"] = cookie
    try:
        r = opener.open(urllib.request.Request(base + "/close", data=b"", headers=headers), timeout=60)
        return r.status, r.headers.get("Location", ""), r.headers.get_all("Set-Cookie") or []
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", ""), e.headers.get_all("Set-Cookie") or []


for opened in (False, True):
    srv = serve(0, public_open=opened)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    rid, other, rec, up, rec2, up2 = f"R-{1001 + opened * 10:04d}", f"R-{1002 + opened * 10:04d}", f"rec-{opened}-aaaaaaaa", f"up-{opened}-bbbbbbbb", f"rec-{opened}-cccc", f"up-{opened}-dddd"
    for r in (rid, other):  # 写真の控えは記録ごとの置き場の箱に書く（上げた時はその箱が先にできている）
        (records.folder() / "media" / r).mkdir(parents=True, exist_ok=True)
    records.claim(rid, rec)
    records.claim(other, rec2)
    media_review.claim(rid, "p1.jpg", up)
    media_review.claim(other, "p2.jpg", up2)
    assert records.mine(rid, rec) and media_review.uploaded_here(rid, ["p1.jpg"], up), "試験の鍵が控えられていない"
    # 4. 鍵の無い画面の /close: 同じ返事・何も失効しない
    plain = close(base)
    assert plain[0] == 303 and "/gallery" in plain[1], plain
    assert records.mine(rid, rec) and media_review.uploaded_here(rid, ["p1.jpg"], up), "鍵の無い /close で失効した"
    # 1. 鍵のある画面の /close の後は、写した古い印が拒まれる
    code, where, cookies = close(base, f"utsushi_rec={rec}; utsushi_up={up}")
    assert code == 303 and where == plain[1], ("とじた後の返事の形が替わった", code, where, plain[1])
    assert not records.mine(rid, rec), ("とじた後も、写した記録の鍵が通る", opened)
    assert not media_review.uploaded_here(rid, ["p1.jpg"], up), ("とじた後も、写した写真の鍵が通る", opened)
    # 2. ほかの画面の鍵は生きたまま
    assert records.mine(other, rec2) and media_review.uploaded_here(other, ["p2.jpg"], up2), ("ほかの画面の鍵まで失効した", opened)
    # 3. cookie の Secure: 公開の場は付く・手元は付かない。消す行の形（Max-Age=0）は前のまま
    own = [c for c in cookies if c.startswith(("utsushi_rec=", "utsushi_up="))]
    assert len(own) == 2 and all("Max-Age=0" in c and "HttpOnly" in c for c in own), own
    assert all(("Secure" in c) == opened for c in own), ("所有者の cookie の Secure", opened, own)
    srv.shutdown()
    srv.server_close()
print("ok この画面をとじる: 記録と写真の古い印をサーバの側で失効させ、ほかの画面の鍵は残す。所有者の cookie は公開の場でも Secure・手元は今のまま")
