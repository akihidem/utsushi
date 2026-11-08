"""しおりを型紙の PDF に一緒に刷る道（本人 11-08「しおりは型紙の PDF に一緒に刷る。」・設計 grove の state/shiori-in-sheet-20261108.md の 2.1 版）。

なぜ: しおりは手帖の鍵。型紙の PDF はサーバに 1 つの玩具・1 つの版ごとに 1 つだけ置いて誰にも同じ物を渡すので、1 人ごとの印は置いた PDF に
入れられない。押した時にその場で組んで返し、どこにも置かない形と、記録への結び方（押した人＝次に記録を残す人と決め打ちしない）を固める。
見る事:
1 合言葉付きの場の型紙の窓の PDF の釦は POST のフォーム（別のタブ）。返すのは型紙＋しおりの 1 頁（表だけ）・inline・no-store。最初の頁は置いた型紙と同じ中身。
  置いた PDF は替わらず、out の中にファイルが増えない。押すたびに台帳のしおりが 1 つ増える。GET では増えない
2 待ち: who と回の印が届いた時だけ待ちの cookie を渡す（台本の無い画面は待ちを作らない）。のこすの確かめの画面に 1 行が出るのは待ちがある時だけ
3 結ぶ: 「外す」を押さずに承認した記録（shiori=1）を、cookie・who・回・3 時間が合う時だけ結ぶ。違う who・外した・3 時間を過ぎた時は結ばない。
  結んでも結ばなくても待ちの cookie は消える
4 合言葉なしの場は受け口でも断り、台帳を作らない。決まった番地が無い場は型紙だけを返す
終了: 0 = 通る / 1 = 落ちる（assert）
"""
import hashlib
import http.cookiejar
import io
import json
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")
os.environ["OMOCHAE_SHIORI_BASE"] = "https://utsushi.konoba.workers.dev"

from pypdf import PdfReader  # noqa: E402

from omochae import hypotheses, shiori  # noqa: E402
from web import play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
H = hypotheses.sheet_of(G)["id"]
form = lambda d: urllib.parse.urlencode(d).encode()


class Stay(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def site(**kw):
    s = play_server.serve(0, **kw)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


def session(base):
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), Stay)

    def call(path, body=None):
        r = urllib.request.Request(base + path, data=body, headers={"Origin": base, "Content-Type": "application/x-www-form-urlencoded"} if body is not None else {})
        try:
            with op.open(r, timeout=120) as x:
                return x.status, x.read(), dict(x.headers), x.headers.get_all("Set-Cookie") or []
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers), e.headers.get_all("Set-Cookie") or []
    return call, jar


def ledger():
    return sorted(p.name for p in shiori.folder().glob("*.json"))


def entries():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(shiori.folder().glob("*.json"))]


# ---- 1 刷る
server, base = site()
call, jar = session(base)
assert call(f"/toy/{G}/print", form({"hypothesis": H}))[0] in (200, 303)
stem = f"{H}_v1"
sheet = play_server.out_dir(G) / f"{stem}.pdf"
assert sheet.exists(), sheet
before_sha = hashlib.sha256(sheet.read_bytes()).hexdigest()
toy = call(f"/toy/{G}")[1].decode()
assert f'<form method="post" action="/toy/{G}/sheet-shiori" target="_blank" class="shiori-print" data-sid="{G}">' in toy, "合言葉付きの場の PDF の釦は POST のフォーム（別のタブ）"
assert "PDF を開いて印刷する</button>" in toy and f'href="/sheet/{G}/{stem}.pdf"' not in toy.split('class="shiori-print"')[1].split("</form>")[0]
files_before = sorted(p.name for p in play_server.out_dir(G).rglob("*"))
WHO, RUN = "abcdefghij", "run0123456789"
code, pdf, head, cookies = call(f"/toy/{G}/sheet-shiori", form({"name": stem, "who": WHO, "run": RUN}))
assert code == 200 and head.get("Content-Type") == "application/pdf", (code, head)
assert head.get("Content-Disposition", "").startswith("inline;") and head.get("Cache-Control") == "no-store", head
assert any(c.startswith("utsushi_sp=") and "HttpOnly" in c and "Max-Age" not in c for c in cookies), cookies
got, src = PdfReader(io.BytesIO(pdf)), PdfReader(str(sheet))
assert len(got.pages) == len(src.pages) + 1, (len(got.pages), len(src.pages))
assert got.pages[0].get_contents().get_data() == src.pages[0].get_contents().get_data(), "最初の頁は置いた型紙と同じ中身"
assert hashlib.sha256(sheet.read_bytes()).hexdigest() == before_sha and sorted(p.name for p in play_server.out_dir(G).rglob("*")) == files_before, "置いた PDF は替わらず、何も書き出さない"
assert len(ledger()) == 1 and entries()[0]["pending"] and set(entries()[0]["pending"]) == {"nonce", "who", "run", "at"}
assert WHO not in json.dumps(entries()) and RUN not in json.dumps(entries()), "待ちは who と回の印そのものを持たない"
# 2 度押す → 台帳は 2 つ（押すたびに新しい印）。GET では増えない
assert call(f"/toy/{G}/sheet-shiori", form({"name": stem, "who": WHO, "run": RUN}))[0] == 200 and len(ledger()) == 2
assert call(f"/toy/{G}/sheet-shiori")[0] in (404, 405) and len(ledger()) == 2, "GET では作らない"
# 形の違う名・たたき台でない紙は断る
assert call(f"/toy/{G}/sheet-shiori", form({"name": "OWN-1_v1", "who": WHO, "run": RUN}))[0] == 404 and len(ledger()) == 2

# ---- 2 台本の無い画面（who と回が無い）は待ちを作らない・しおりは刷る
nojs, _ = session(base)
code, pdf2, head2, cookies2 = nojs(f"/toy/{G}/sheet-shiori", form({"name": stem}))
assert code == 200 and len(PdfReader(io.BytesIO(pdf2)).pages) == len(src.pages) + 1 and not any(c.startswith("utsushi_sp=") for c in cookies2)
assert len(ledger()) == 3 and sum(1 for e in entries() if e["pending"] is None) == 1
assert 'id="nk-c-shiori"' not in nojs(f"/toy/{G}/techo/kiroku")[1].decode(), "待ちの無い画面には 1 行を置かない"
assert 'id="nk-c-shiori" hidden' in call(f"/toy/{G}/techo/kiroku")[1].decode(), "待ちのある画面には 1 行を置く（台本が今の回と照らしてから見せる）"
# 出すかは頁を読んだ時に決めず、確かめの画面を出す時と承認の時に見直す（頁を開いた後の判定で、直に開いた時は作り始めになって回が替わる。
# 頁を読んだ時に決めると、見えたまま結ばれなかった・別の目の #702 の確かめ）
from web import nokosu  # noqa: E402

NS = nokosu.SCRIPT
assert "const shioriOn = () => {" in NS and "sw.hidden = !shioriOn;" not in NS, "1 行を出すかを頁を読んだ時に決めている"
show = NS[NS.index("f.onsubmit"):NS.index("$('nk-fix').onclick")]
assert "chk.hidden = false; shioriShow();" in show, "確かめの画面を出す時に見直す"
assert "...(shioriOn() ? { shiori: '1', run: runOf() } : {})" in NS, "承認の時にも見直してから結ぶ印を送る"


# ---- 3 結ぶ
def record(c, **extra):
    code, body, _, ck = c(f"/toy/{G}/record-json", form({"hypothesis": H, "result": "動いた", "impression": "扇が開いた", "who": WHO, **extra}))
    assert code == 201, (code, body)
    return json.loads(body)["id"], ck


def bound(rid):
    return [e for e in entries() if rid in e["records"]]


rid, ck = record(call, shiori="1", run=RUN)
assert len(bound(rid)) == 1 and any(c.startswith("utsushi_sp=;") or "utsushi_sp=; " in c or ("utsushi_sp=" in c and "Max-Age=0" in c) for c in ck), ("一番新しいしおりに結び、待ちの cookie を消す", ck)
assert not shiori.pending_fresh(None)
# 外した（shiori の印なし）→ 結ばない
call(f"/toy/{G}/sheet-shiori", form({"name": stem, "who": WHO, "run": RUN}))
rid2, _ = record(call, run=RUN)
assert bound(rid2) == [], "外したら結ばない"
# 違う who（次の人）→ 結ばない
call(f"/toy/{G}/sheet-shiori", form({"name": stem, "who": WHO, "run": RUN}))
code, body, _, _ = call(f"/toy/{G}/record-json", form({"hypothesis": H, "result": "動いた", "impression": "次の人", "who": "zzzzzzzzzz", "shiori": "1", "run": RUN}))
assert code == 201 and bound(json.loads(body)["id"]) == [], "前の人が刷った しおりに、次の人の記録を結ばない"
# 違う回（作り始めた後）→ 結ばない
call(f"/toy/{G}/sheet-shiori", form({"name": stem, "who": WHO, "run": RUN}))
rid4, _ = record(call, shiori="1", run="runOTHER0000")
assert bound(rid4) == [], "作り始めて回が替わったら結ばない"
# 3 時間を過ぎた待ち → 結ばない（台帳の道で直に）
tok = shiori.make(pending={"nonce": "n" * 24, "who": WHO, "run": RUN}, now=1000.0)
assert shiori.bind_pending("n" * 24, WHO, RUN, "R-9999", now=1000.0 + shiori.PENDING + 1) is False
assert shiori.bind_pending("n" * 24, WHO, RUN, "R-9999", now=1000.0 + 1) is False, "1 度使った待ち（切れて消した物）は、もう結ばない"
server.shutdown()

# ---- 4 合言葉なしの場・番地の無い場
n0 = len(ledger())
pub, pbase = site(public_open=True)
pcall, _ = session(pbase)
assert pcall(f"/toy/{G}/print", form({"hypothesis": H}))[0] in (200, 303)
ptoy = pcall(f"/toy/{G}")[1].decode()
assert "shiori-print" not in ptoy.replace("form.shiori-print", "") and f'href="/sheet/{G}/{stem}.pdf"' in ptoy, "公開の場は今のまま GET のリンク"
assert pcall(f"/toy/{G}/sheet-shiori", form({"name": stem, "who": WHO, "run": RUN}))[0] == 403 and len(ledger()) == n0, "受け口でも断り、台帳を作らない"
pub.shutdown()
os.environ.pop("OMOCHAE_SHIORI_BASE")
nb, nbase = site()
ncall, _ = session(nbase)
code, pdf3, head3, ck3 = ncall(f"/toy/{G}/sheet-shiori", form({"name": stem, "who": WHO, "run": RUN}))
assert code == 200 and len(PdfReader(io.BytesIO(pdf3)).pages) == len(src.pages) and len(ledger()) == n0 and not ck3, "番地が無い場は型紙だけ"
assert f'href="/sheet/{G}/{stem}.pdf"' in ncall(f"/toy/{G}")[1].decode() and 'class="shiori-print"' not in ncall(f"/toy/{G}")[1].decode()
nb.shutdown()
print("ok: しおりは押した時に作って型紙の後ろに足して返し、置かない・結ぶのは確かめの画面で外さず承認した時に who と回が合う時だけ・公開の場と番地の無い場は型紙だけ")
