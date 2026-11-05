"""手順の紙。型紙と同じ検査（印字域・文字の重なり・印）を通す。

判断の芯: 答えを先に言わない。計算の開く角度の上限は刷らない（作る前の予想と、測った数を比べるのが目的なので）。
結果は雛形ごとの値で、同じ大きさの欄で、既定の選択を置かない。
"""
from .compose import GAP, LINE, TEMPLATES, TITLE_SIZE, _block, set_label
from .floors import check_layout
from .marks import mark_lines
from .model import Failure, TextBox
from .page import PAGES
from .textfit import text_width

# 型紙より字を大きく、欄を広くする。手で書き込む紙で、子どもも使うため。
BODY_SIZE, HEAD_SIZE = 3.6, 4.4
ANSWER_GAP, FIX_ROW = 9.0, 10.0
DIAGRAM_W, DIAGRAM_H = 42.0, 62.0
PICTURE_SIZE = 2.8
# 見て考える 4 問は、本人の 4 つの着目（research/20）に 1 つずつ当てる。①②楽しさ ③納得 ④哲学（作りながら思いつく）。
# 1 の「動いたか」は丸の欄で問う。角度や回数は今回の課題でない（本人、11-04）。
QUESTIONS = ("一番おもしろかったのはどの時ですか", "どうしたら、もっと楽しくなりますか",
             "なぜそう動くのか、自分の言葉か絵で（まだ分からない所も書く）", "作っている途中で思いついた事は何ですか")
RESULT_HEAD = "おもちゃとして動きましたか（1 つに丸）"
STUCK = "最初の一歩でつまずいた所"
PREDICT_H = 15.0
# 手順の紙の作る前の欄と、試した後の紙の見出し。本人が採った字で、一字も変えない（11-05、#302 の案 A）。
# 前の字は、先に書かないと始められないように読めた（予想の段は #242 で外した）。問いと枠は、端末の無い場でも考えを書けるように残す。
BEFORE_HEAD = "思った事（書かなくても作れます）"
NEXT_HEAD = "次はこれを変えて試す"
# 必須 2 種の今の組は指紋を変えないので、前の字のまま刷る（凍結の床）。次の組で上の字に直す。
# 組の名前で持つ: 組を上げると前の字は外れ、この表に残った行を tests/test_sheet_heads.py が名指しして落ちる（消し忘れないため）。
_OLD_HEADS = ("作る前に", "次はこれを変えて試す（予想を書いてから）")
FROZEN_HEADS = {"goraigo-v10": _OLD_HEADS, "tora-v3": _OLD_HEADS}


def _heads(sheet_set):
    """その組で刷る（作る前の欄の見出し, 試した後の紙の見出し）。"""
    return FROZEN_HEADS.get(sheet_set, (BEFORE_HEAD, NEXT_HEAD))


def steps(p, template="slider_fan"):
    return TEMPLATES[template].steps(p)


PICTURES_W = 75.0
# 吉澤・Randlett の記号の矢じり（research/22 の候補 1）。谷は中を塗る、山は白抜き。型紙の見える面には置かない（本人の決定 d と逆向きなので）。
VALLEY_HEAD, MOUNTAIN_HEAD = "black", "white"


def _arc_arrow(shapes, x1, y, x2, rise, head):
    """折る向きの弧の矢印。弧は 2 次のベジェ曲線を線分で近似し、終わりに矢じりの三角を置く。"""
    cx, cy = (x1 + x2) / 2, y - rise * 2
    pts = [((1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t * t * x2, (1 - t) ** 2 * y + 2 * (1 - t) * t * cy + t * t * y)
           for t in (i / 10 for i in range(11))]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        shapes.append({"kind": "line", "x1": ax, "y1": ay, "x2": bx, "y2": by})
    (ax, ay), (bx, by) = pts[-3], pts[-1]
    dx, dy = bx - ax, by - ay
    n = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / n, dy / n
    length, half = 1.8, 0.9
    base = (bx - ux * length, by - uy * length)
    tri = [(bx, by), (base[0] - uy * half, base[1] + ux * half), (base[0] + uy * half, base[1] - ux * half)]
    shapes.append({"kind": "poly", "pts": tri, "fill": head, "sw": 0.25, "tag": "arrowhead"})


def _first_steps(x, y, shapes, texts):
    """最初の一歩と蛇腹の畳み方の小さな絵（v8、U-25 で色と矢印を足した）。幅 50mm に収め、絵の下の y を返す。

    試行で手が止まったのは平面から立体への最初の一歩で（本人の補足所見）、「ジャバラに折る発想が出てこない」
    「谷折り、山折りがわからない」の声があった。絵は形の作り方だけで、扇がどう開くか（仕組み）は描かない（紙で確かめる前に答えを見せない。J-013）。
    平らな筒は v9 の外筒と同じく 1 面おきに地の色を変え、境に線を引かない。型紙と絵が食い違うと、どこで折るかで迷うため。
    """
    from .templates.slider_fan import PAPER, PAPER_ALT

    # 1) 平らな外筒 → 角筒。4 面の帯と糊代、谷折りの矢印、組んだ角筒の斜めの姿
    y = _block(texts, ["まず筒を 1 つ作る（色の境で谷折り）"], x, y, PICTURE_SIZE, 50)
    fw, fh, sy = 6.0, 11.0, y + 4.5
    for i in range(4):
        shapes.append({"kind": "poly", "pts": [(x + fw * i, sy), (x + fw * (i + 1), sy), (x + fw * (i + 1), sy + fh), (x + fw * i, sy + fh)],
                       "fill": PAPER if i % 2 == 0 else PAPER_ALT, "tag": "tube_face"})
    shapes.append({"kind": "rect", "x": x, "y": sy, "w": fw * 4, "h": fh})
    shapes.append({"kind": "rect", "x": x + fw * 4, "y": sy + 1, "w": 3, "h": fh - 2})
    # 右の面を手前へ起こす谷折り。境の上をまたぐ弧にする（記号の決まり: 矢印は動く側から行き先へ）。
    _arc_arrow(shapes, x + fw * 3.5, sy - 0.5, x + fw * 2.5, 1.8, VALLEY_HEAD)
    ax, my = x + fw * 4 + 5, sy + fh / 2
    shapes += [{"kind": "line", "x1": ax, "y1": my, "x2": ax + 6, "y2": my},
               {"kind": "line", "x1": ax + 4, "y1": my - 2, "x2": ax + 6, "y2": my},
               {"kind": "line", "x1": ax + 4, "y1": my + 2, "x2": ax + 6, "y2": my}]
    bx, by = ax + 9, sy + 3
    shapes += [{"kind": "rect", "x": bx, "y": by, "w": 6, "h": fh - 3},
               {"kind": "line", "x1": bx, "y1": by, "x2": bx + 3, "y2": by - 3},
               {"kind": "line", "x1": bx + 6, "y1": by, "x2": bx + 9, "y2": by - 3},
               {"kind": "line", "x1": bx + 3, "y1": by - 3, "x2": bx + 9, "y2": by - 3},
               {"kind": "line", "x1": bx + 9, "y1": by - 3, "x2": bx + 9, "y2": by + fh - 6},
               {"kind": "line", "x1": bx + 6, "y1": by + fh - 3, "x2": bx + 9, "y2": by + fh - 6}]
    texts.append(TextBox(x, sy - 4.5, 50, fh + 4.5, None))
    # 2) 蛇腹: 横から見た山と谷
    zy = sy + fh + 3
    # 線の無い面（v9 の筒と扇）は色の境で折る事も、ここで言う。
    zz = _block(texts, ["蛇腹（横から）: 上が山、下が谷", "線の無い面は色の境で折る"], x, zy, PICTURE_SIZE, 50)
    pts = [(x + 4 * i, zz + (1 if i % 2 else 6)) for i in range(9)]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        shapes.append({"kind": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2})
    texts.append(TextBox(x, zz, 33, 7, None))
    # 3) 矢じりの見本。塗った矢じり＝谷（手前へ）、白い矢じり＝山（向こうへ）。
    # 見本は縦に 2 段。横に並べると、右の原図の写しの説明と重なる（検査 F5.text_overlap で分かった）。
    end = zz + 8
    for name, head in (("谷折り（手前へ）", VALLEY_HEAD), ("山折り（向こうへ）", MOUNTAIN_HEAD)):
        _arc_arrow(shapes, x, end + 3, x + 6, 1.2, head)
        texts.append(TextBox(x, end, 7, 4.5, None))  # 矢じりの先は弧の終わりより下へ約 0.9mm 出るので、その分まで取る
        end = max(end + 4.5, _block(texts, [name], x + 7.5, end, PICTURE_SIZE, text_width(name, PICTURE_SIZE) + 0.5))
    return end


# 折る順のコマ（research/22 の候補 4）。押し方と中心の置き方で変わる所だけを分け、組み方の文と同じ部品番号を使う。
def _order_panels(p):
    second = {"tab": "2 内筒を角筒にし、竹串を通す", "stick": "2 土台を角筒にし、割り箸を差す", "tube": "2 内筒を角筒にする"}[p["push_part"]]
    # 他のコマと同じく部品番号から書き出す（レビューの指摘: 4 コマ目だけ番号が無く、読み方がそろわなかった）。
    # 1 行に収める。糸を先に通す順は組み方の文にある。
    last = "3 台に 4 扇と 5 像を貼る" if p["hub"] == "axle" else "3 台に 4 扇の端と 5 像を貼る"
    return [("tube", "1 外筒を切って角筒に"), (p["push_part"], second), ("fan", "4 扇を色の境で蛇腹に"), ("join", last)]


PANEL_GAP, PANEL_H = 4.0, 14.0


def _panel_size(width, n):
    return (width - PANEL_GAP * (n - 1)) / n, PANEL_H


def _panel_picture(kind, x, y, w, h, shapes):
    """コマの絵。形の作り方だけで、扇が開く様子（仕組み）は描かない（紙で確かめる前に答えを見せない。J-013）。"""
    cx = x + w / 2

    def prism(px, py, pw, ph):
        shapes.extend([{"kind": "rect", "x": px, "y": py, "w": pw, "h": ph},
                       {"kind": "line", "x1": px, "y1": py, "x2": px + 2, "y2": py - 2},
                       {"kind": "line", "x1": px + pw, "y1": py, "x2": px + pw + 2, "y2": py - 2},
                       {"kind": "line", "x1": px + 2, "y1": py - 2, "x2": px + pw + 2, "y2": py - 2},
                       {"kind": "line", "x1": px + pw + 2, "y1": py - 2, "x2": px + pw + 2, "y2": py + ph - 2},
                       {"kind": "line", "x1": px + pw, "y1": py + ph, "x2": px + pw + 2, "y2": py + ph - 2}])

    if kind == "tube":
        prism(cx - 4, y + 3, 7, h - 5)
    elif kind in ("tab", "tube_in"):
        prism(cx - 3, y + 5, 5, h - 8)
    elif kind == "stick":
        prism(cx - 3, y + 4, 5, 5)
        shapes.append({"kind": "rect", "x": cx - 1, "y": y + 9, "w": 1.5, "h": h - 10})
    elif kind == "fan":
        pts = [(cx - 8 + 2 * i, y + h / 2 + (-2 if i % 2 else 2)) for i in range(9)]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            shapes.append({"kind": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2})
    else:  # join: 台の上に像と畳んだ扇を載せる。開く様子は描かない。
        shapes.append({"kind": "rect", "x": cx - 8, "y": y + h - 4, "w": 16, "h": 2})
        shapes.append({"kind": "rect", "x": cx - 6, "y": y + h - 9, "w": 4, "h": 5})
        shapes.append({"kind": "rect", "x": cx + 1, "y": y + h - 12, "w": 3, "h": 8})
    if kind == "tab":
        shapes.append({"kind": "line", "x1": cx - 7, "y1": y + h / 2, "x2": cx + 7, "y2": y + h / 2})


def _panel_kind(kind, i):
    """2 コマ目が筒の時は、1 コマ目の外筒より細い内筒を描く。紙と画面（step_pictures）で同じ絵にするため 1 か所に置く。"""
    return "tube_in" if kind == "tube" and i == 1 else kind


def _fold_order(x, y, width, p, shapes, texts):
    """折る順の図を 4 コマで刷り、下の y を返す。手順を細かく決めすぎず、順を変える余白を文で渡す（本人の「工夫の余白」）。"""
    head = "折る順（目安）"
    _block(texts, [head], x, y, HEAD_SIZE, width)
    # 余白の文は見出しと同じ行に置く（A4 に収めるため）。順を決めつけないことは、見出しのすぐ横で言う。
    hw = text_width(head, HEAD_SIZE) + 3
    _block(texts, [ORDER_NOTE], x + hw, y + (HEAD_SIZE - PICTURE_SIZE) * LINE, PICTURE_SIZE, width - hw)
    y += HEAD_SIZE * LINE
    panels = _order_panels(p)
    pw, ph = _panel_size(width, len(panels))
    gap = PANEL_GAP
    bottom = y
    for i, (kind, caption) in enumerate(panels):
        px = x + i * (pw + gap)
        shapes.append({"kind": "rect", "x": px, "y": y, "w": pw, "h": ph, "tag": "order_panel"})
        texts.append(TextBox(px, y, pw, ph, None))
        _panel_picture(_panel_kind(kind, i), px, y, pw, ph, shapes)
        bottom = max(bottom, _block(texts, [caption], px, y + ph + 0.5, PICTURE_SIZE, pw))
    return bottom


ORDER_NOTE = "順番は目安です。やりやすい順に変えてよい。自分の順を見つけたら、直した点に書く"


def _steps_to_panels(texts):
    """手順の文が触る部品から、折る順のコマを選ぶ。コマは手順の番号を持たないので、部品の名前で結ぶ。
    順は戻さない（最後の「内筒を外筒に入れ」は組み上げなので、1 コマ目へ戻さず 4 コマ目のまま）。"""
    at, out = 0, []
    for t in texts:
        if "3 台" in t and "貼る" in t:
            hit = 3
        elif "扇" in t:
            hit = 2
        elif any(w in t for w in ("内筒", "土台", "竹串", "割り箸")):
            hit = 1
        else:
            hit = 0
        at = max(at, hit)
        out.append(at)
    return out


def step_pictures(template_id, p, texts):
    """手帖の 1 手 1 画面に出す絵（段 1。本人の決定 11-05、#87）。Returns (絵の並び, 手順ごとの絵の番号)。絵は形の並びで、render.shapes_svg が描く。

    手順ごとの絵はまだ無いので、手順の紙に刷ってある絵をそのまま使う。紙と画面で絵が食い違わず、刷っていない画面でも形から描ける。
    折る順の 4 コマがあるのは slider_fan（御来迎）だけ（compose_sheet の fan の時だけ刷る）。ほかの雛形は手順の紙の図 1 枚を、全部の手順で出す（段 2 で手順ごとの絵を描くまで）。
    どちらも紙に刷ってある物なので、見せてよい範囲は紙と変わらない（J-013。扇が開く様子は、紙と同じくコマに描いていない）。
    """
    if template_id != "slider_fan":
        return [TEMPLATES[template_id].diagram(0, 0, DIAGRAM_W, DIAGRAM_H, p)], [0] * len(texts)
    page = PAGES["A4"]
    panels = _order_panels(p)
    pw, ph = _panel_size(page.x1 - page.x0, len(panels))
    pictures = []
    for i, (kind, _) in enumerate(panels):
        shapes = []
        _panel_picture(_panel_kind(kind, i), 0, 0, pw, ph, shapes)
        pictures.append(shapes)
    return pictures, _steps_to_panels(texts)


def compose_sheet(template_id, params, source, title, how_it_moves, page_name="A4", version=1, picture=None):
    """Returns (layout, failures)。picture は完成のイメージとして載せる原図の写しの道（v8、slider_fan だけ）。

    U-25（本人が案 1〜4 を採った、11-04）: 角度と回数と物差しを外し、問いを本人の 4 つの着目に合わせた。
    測る紙から、作りながら考える紙へ。答えを先に言わない事は変えない（J-013）。
    """
    tpl = TEMPLATES[template_id]
    p = {**tpl.DEFAULTS, **params}
    page = PAGES[page_name]
    texts, shapes = [], []
    width = page.x1 - page.x0
    y = _block(texts, [f"手順の紙 {title}"], page.x0, page.y0, TITLE_SIZE, width)
    y = set_label(texts, f"刷った組 {tpl.SHEET_SET}", page, y)  # U-31
    y = _block(texts, mark_lines(source), page.x0, y + 1, BODY_SIZE, width)
    top = y + GAP
    left_w = width - DIAGRAM_W - GAP
    diagram_x = page.x1 - DIAGRAM_W
    shapes += tpl.diagram(diagram_x, top, DIAGRAM_W, DIAGRAM_H, p)
    texts.append(TextBox(diagram_x, top, DIAGRAM_W, DIAGRAM_H, None))
    # 図の説明は雛形が持てる（全部の玩具の線の報告）。御来迎の筒の言葉を、車や凧の図に刷らないため。無ければ今までの文。
    _block(texts, [getattr(tpl, "DIAGRAM_CAPTION", "閉じた時の中の様子（破線は筒の中）")], diagram_x, top + DIAGRAM_H + 1, 2.8, DIAGRAM_W)
    y = _block(texts, ["組み方"], page.x0, top, HEAD_SIZE, left_w)
    y = _block(texts, [f"{i}. {s}" for i, s in enumerate(tpl.steps(p), 1)], page.x0, y, BODY_SIZE, left_w)
    y = _block(texts, ["遊び方", how_it_moves, "力を入れすぎず、手でゆっくり動かす"], page.x0, y + 1, BODY_SIZE, left_w)
    y = max(y, top + DIAGRAM_H + 8) + 2
    images = []
    fan = template_id == "slider_fan"
    # 絵は作る前の欄の右の空きに置く（v8）。頁を伸ばさずに済む。
    pics_y = y
    ask_w = width - PICTURES_W - GAP if fan else width

    def field(label, x, y0, w=30.0):
        lw = text_width(label, BODY_SIZE)
        texts.append(TextBox(x, y0, lw, BODY_SIZE * LINE, label, BODY_SIZE))
        shapes.append({"kind": "rect", "x": x + lw + 1.5, "y": y0, "w": w, "h": BODY_SIZE * LINE})
        texts.append(TextBox(x + lw + 1.5, y0, w, BODY_SIZE * LINE, None))
        return x + lw + w + 5

    m = tpl.measures(p)
    y = _block(texts, [_heads(tpl.SHEET_SET)[0]], page.x0, y, HEAD_SIZE, ask_w)
    y = _block(texts, [m["predict"]], page.x0, y, BODY_SIZE, ask_w)
    # 動き方を言葉か絵で書くので、1 行の枠でなく描ける広さの枠にする。
    shapes.append({"kind": "rect", "x": page.x0, "y": y + 0.5, "w": ask_w, "h": PREDICT_H, "tag": "predict_box"})
    texts.append(TextBox(page.x0, y + 0.5, ask_w, PREDICT_H, None))
    y += PREDICT_H + 3
    # 作り始めて動かすまでの分は外した（角度と同じく測る欄）。詰まった所を言葉で残し、次の版に返す（試行で手が止まったのは最初の一歩）。
    # 最初の一歩の絵の横に置く。絵を見て、どこで詰まったかを書けるように。
    y = _block(texts, [STUCK], page.x0, y, HEAD_SIZE, ask_w) + ANSWER_GAP - 2
    shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x0 + ask_w, "y2": y - 1.5})
    y += 2
    if m["rows"]:
        y = _block(texts, ["試した事"], page.x0, y, HEAD_SIZE, ask_w)
        for row in m["rows"]:
            x = page.x0
            for label, w in row:
                x = field(label, x, y, w)
            y += BODY_SIZE * LINE + 2
    if fan:
        px = page.x1 - PICTURES_W
        pics_end = _first_steps(px, pics_y, shapes, texts)
        if picture:
            # 完成のイメージとして原図を試しに載せる（本人の決定、11-04）。縮めた写しを埋め込み、PDF を重くしない。
            import io
            from PIL import Image
            im = Image.open(picture).convert("RGB")
            im.thumbnail((360, 600))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=80)
            h = 28.0
            w = h * im.width / im.height
            ix = page.x1 - w
            images.append({"x": ix, "y": pics_y, "w": w, "h": h, "data": buf.getvalue()})
            texts.append(TextBox(ix, pics_y, w, h, None))
            pics_end = max(pics_end, _block(texts, ["完成の", "イメージ", "（原図）"], ix, pics_y + h + 0.5, 2.8, w))
        y = max(y, pics_end) + 2
        y = _fold_order(page.x0, y, width, p, shapes, texts) + 2
    y = _block(texts, ["見て考える"], page.x0, y, HEAD_SIZE, width)
    for q in QUESTIONS:
        y = _block(texts, [q], page.x0, y, BODY_SIZE, width) + ANSWER_GAP
        shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x1, "y2": y - 1.5})
    y += 1
    # 丸の欄は問いと同じ行に並べる（A4 に収めるため）。入らない幅なら次の行へ送る。
    # 結果の欄の見出しも雛形が持てる。動かない玩具に「動きましたか」と問わないため。
    head = getattr(tpl, "RESULT_HEAD", RESULT_HEAD)
    _block(texts, [head], page.x0, y, HEAD_SIZE, width)
    x = page.x0 + text_width(head, HEAD_SIZE) + 3
    if x + 34 * len(tpl.RESULTS) > page.x1:
        x, y = page.x0, y + HEAD_SIZE * LINE
    # 欄を同じ大きさにする。「わからない」を小さくすると、選ぶのをためらわせるため。
    for r in tpl.RESULTS:
        shapes.append({"kind": "rect", "x": x, "y": y, "w": 30, "h": BODY_SIZE * LINE + 1})
        texts.append(TextBox(x + 2, y + 0.5, text_width(r, BODY_SIZE), BODY_SIZE * LINE, r, BODY_SIZE))
        x += 34
    y += BODY_SIZE * LINE + 4
    y = _block(texts, ["直した点（部品・変えた事・結果）"], page.x0, y, HEAD_SIZE, width)
    # 行は 2 つ。版 2 の紙のように遊び方の文が長くなって頁に入らない時は 1 行にする（表そのものは必ず残す）。
    # 1 行でも入らない時は、行の枠が印字域の外に出て check_layout が F5.print_area で落とす。
    rows = max(1, min(2, int((page.y1 - y) // FIX_ROW)))
    for _ in range(rows):
        for col, cw in enumerate((40.0, 80.0, 70.0)):
            shapes.append({"kind": "rect", "x": page.x0 + sum((40.0, 80.0, 70.0)[:col]), "y": y, "w": cw, "h": FIX_ROW})
        texts.append(TextBox(page.x0, y, width, FIX_ROW, None))
        y += FIX_ROW
    # 物差しは型紙にある（刷りの倍率は型紙で確かめる）。この紙では測らないので刷らない（U-25）。
    failures = check_layout(page, [], texts)
    return {"page": page, "parts": [], "texts": texts, "samples": [], "ruler": None, "shapes": shapes, "images": images}, failures


# どちらが良いかを決める問いは置かない（J-025、順位を付けない）。3 問目は次の試しを自分で決める余白（本人の「工夫の余白」）。
COMPARE_QUESTIONS = ("それぞれ、どこがおもしろく動きましたか", "2 つで、動き方のどこが違いましたか", "もう 1 つ見比べるなら、何を変えますか")
COMPARE_LIMIT = "どちらかがよく動いても、昔の作り方の証明にはなりません。紙で言えるのは、この紙がどう動くかまでです。"


def compose_compare(source, toy, ha, hb, labels, page_name="A4"):
    """2 つの仮説を見比べる紙（J-019）。計算の上限も、どちらが正しいかの欄も置かない。

    判断の芯: 問うのは「どこが違ったか」で、勝ち負けを決めない（記録は観察で成績にしない。philosophy.md）。
    """
    page = PAGES[page_name]
    width = page.x1 - page.x0
    texts, shapes = [], []
    y = _block(texts, [f"見比べる紙 {toy} 仮説 {labels[0]} と 仮説 {labels[1]}"], page.x0, page.y0, TITLE_SIZE, width)
    y = _block(texts, mark_lines(source), page.x0, y + 1, BODY_SIZE, width)
    # 型紙が同じ仮説の組（御来迎の C と D）は動かし方だけが違う。2 個作らせると、作りの差が動かし方の差に混ざる。
    same = (ha.get("template"), ha.get("params")) == (hb.get("template"), hb.get("params"))
    head = "型紙は 1 つ。1 個を作り、同じ物を 2 通りの動かし方で試す" if same else "2 つの型紙を同じ紙で刷って作り、同じ手で試す"
    y = _block(texts, [head], page.x0, y + GAP, HEAD_SIZE, width)
    for label, h in zip(labels, (ha, hb)):
        y = _block(texts, [f"{label}: {h['name']}", h["how_it_moves"], f"見る物: {h['to_measure']}"], page.x0, y + 1, BODY_SIZE, width)
    y = _block(texts, ["作る前に: どちらがどう違うと思いますか"], page.x0, y + GAP, HEAD_SIZE, width)
    y += ANSWER_GAP
    shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x1, "y2": y - 1.5})
    # 各 3 回の角度の表は外した（角度は今回の課題でない、U-25 の案 3）。見るのは動き方のおもしろさと違い。
    # 書く欄を広く取る。表が無くなった分、言葉か絵で書けるようにする。
    y = _block(texts, ["見て考える"], page.x0, y + GAP, HEAD_SIZE, width)
    for q in COMPARE_QUESTIONS:
        y = _block(texts, [q], page.x0, y, BODY_SIZE, width) + ANSWER_GAP * 2
        shapes.append({"kind": "line", "x1": page.x0, "y1": y - ANSWER_GAP - 1.5, "x2": page.x1, "y2": y - ANSWER_GAP - 1.5})
        shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x1, "y2": y - 1.5})
    y = _block(texts, [COMPARE_LIMIT], page.x0, y + 1, BODY_SIZE, width)
    failures = check_layout(page, [], texts)
    return {"page": page, "parts": [], "texts": texts, "samples": [], "ruler": None, "shapes": shapes}, failures


def compose_after(source, title, after, page_name="A4", sheet_set=None):
    """試した後の紙。対比を先に見せ、説明は折って閉じた札にする（J-013）。

    判断の芯: 説明を渡さず、次に変える条件を先に渡す。ただし誤った結論のまま終わらないよう、説明は手元に置いて自分で開ける。
    札は谷折りで白い帯の上に重ねて隠す。端末でなく紙で閉じるので、子どもに AI も鍵も要らない。
    """
    page = PAGES[page_name]
    width = page.x1 - page.x0
    texts, shapes = [], []
    y = _block(texts, [f"試した後の紙 {title}"], page.x0, page.y0, TITLE_SIZE, width)
    if sheet_set:
        y = set_label(texts, f"刷った組 {sheet_set}", page, y)  # U-31
    y = _block(texts, mark_lines(source), page.x0, y + 1, BODY_SIZE, width)
    y = _block(texts, ["渡す人へ: 下の札を点線で谷折りし、端をテープで止めてから、試した後に渡す"], page.x0, y + 1, BODY_SIZE, width)
    y = _block(texts, [_heads(sheet_set)[1]], page.x0, y + GAP, HEAD_SIZE, width)
    for c in after["contrasts"]:
        y = _block(texts, [c["change"], f"見る物: {c['watch']}"], page.x0, y + 1, BODY_SIZE, width)
        y += ANSWER_GAP
        shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x1, "y2": y - 1.5})
    # 物差しは外した（次の条件も角度でなく動き方を見る、U-25 の案 2）。
    # 札の中に納得の問いを 1 つ置く（着目 3）。札を開いた後にだけ読める所に置かないと、説明より先に問いが目に入る。
    card = ["札: 自分で開いた時だけ読む", *after["card"], AFTER_QUESTION]
    trial = []
    height = _block(trial, card, page.x0, 0, BODY_SIZE, width) + ANSWER_GAP
    fold = page.y1 - height - 1
    failures = []
    # 札を折り上げた先に文字があると隠れ方が崩れるので、重なる帯を空けられない時は刷らない。
    if fold - height - 1 < y:
        failures.append(Failure("F5.fold", title, "札を折って隠す帯が取れない"))
    shapes.append({"kind": "line", "x1": page.x0, "y1": fold, "x2": page.x1, "y2": fold, "dash": "1.5,1.5"})
    answer = _block(texts, card, page.x0, fold + 1, BODY_SIZE, width) + ANSWER_GAP
    shapes.append({"kind": "line", "x1": page.x0, "y1": answer - 1.5, "x2": page.x1, "y2": answer - 1.5})
    failures += check_layout(page, [], texts)
    return {"page": page, "parts": [], "texts": texts, "samples": [], "ruler": None, "shapes": shapes}, failures


AFTER_QUESTION = "札を読んで、納得できましたか。どこが自分の考えと違いましたか"


FREE_MATERIALS = ("包んでいた紙、広告の紙、紙袋など、手元の紙", "リボン、糸、輪ゴムなど、手元の紐", "のり、テープ、はさみ", "あれば割り箸か竹串")
FREE_THINK = ("どこが動くと思いますか", "動かす力はどこから来ますか（押す・引く・紙の戻る力・重さ）", "紙をどう切って、どう折りますか")


def compose_free(source, title, how_it_moves, evidence, results, page_name="A4"):
    """型紙なしの紙（本人の決定、哲学のレビューの第 1 点 (b)）。用意した型紙に乗らない仮説に返す。

    判断の芯: 雛形に無い機構を作れるふりをして寸法を出さない（F9.own）。代わりに、身の回りの紙と紐で
    自分で形を考えて作るための問いと欄を渡す。本人の言葉の「包んでいた紙、リボンに結ばれた紐」に一番近い紙。
    答えも寸法も刷らない。見た事の欄と問いは型紙の手順の紙と同じにして、記録を同じ形で残せるようにする。
    """
    page = PAGES[page_name]
    width = page.x1 - page.x0
    texts, shapes = [], []
    y = _block(texts, [f"型紙なしの紙 {title}"], page.x0, page.y0, TITLE_SIZE, width)
    y = _block(texts, mark_lines(source), page.x0, y + 1, BODY_SIZE, width)
    y = _block(texts, ["この仮説は、用意した型紙に乗りません。身の回りの紙と紐で、形を自分で考えて作ります"], page.x0, y + 1, BODY_SIZE, width)
    y = _block(texts, ["あなたの仮説", how_it_moves, f"図のどこを見たか: {evidence}"], page.x0, y + GAP, BODY_SIZE, width)
    y = _block(texts, ["用意する物", *[f"・{m}" for m in FREE_MATERIALS]], page.x0, y + 1, BODY_SIZE, width)
    y = _block(texts, ["作る前に考える"], page.x0, y + GAP, HEAD_SIZE, width)
    for q in FREE_THINK:
        texts.append(TextBox(page.x0, y, text_width(q, BODY_SIZE), BODY_SIZE * LINE, q, BODY_SIZE))
        y += BODY_SIZE * LINE + ANSWER_GAP
        shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x1, "y2": y - 1.5})
    # 描く欄。形を言葉にしにくい時に、図で考えられるように。
    texts.append(TextBox(page.x0, y + 1, text_width("ここに形を描く", BODY_SIZE), BODY_SIZE * LINE, "ここに形を描く", BODY_SIZE))
    box_y = y + 1 + BODY_SIZE * LINE
    shapes.append({"kind": "rect", "x": page.x0, "y": box_y, "w": width, "h": 45})
    texts.append(TextBox(page.x0, box_y, width, 45, None))
    y = box_y + 45 + GAP
    y = _block(texts, ["見て考える"], page.x0, y, HEAD_SIZE, width)
    for q in QUESTIONS:
        # 3 問目は長いので、紙の幅で折り返す。
        y = _block(texts, [q], page.x0, y, BODY_SIZE, width) + ANSWER_GAP
        shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x1, "y2": y - 1.5})
    y = _block(texts, [RESULT_HEAD], page.x0, y + 1, HEAD_SIZE, width)
    x = page.x0
    for r in results:
        shapes.append({"kind": "rect", "x": x, "y": y, "w": 30, "h": BODY_SIZE * LINE + 1})
        texts.append(TextBox(x + 2, y + 0.5, text_width(r, BODY_SIZE), BODY_SIZE * LINE, r, BODY_SIZE))
        x += 34
    y += BODY_SIZE * LINE + 4
    ruler_y = y
    texts.append(TextBox(page.x0, ruler_y, 100, 3, None))
    _block(texts, ["10cm の物差し。100% で刷る（用紙に合わせない）"], page.x0, ruler_y + 4, BODY_SIZE, width)
    failures = check_layout(page, [], texts)
    return {"page": page, "parts": [], "texts": texts, "samples": [], "ruler": (page.x0, ruler_y), "shapes": shapes}, failures


# 4 つの着目は本人の言葉のまま（research/20）。見出しを言い換えると、先生と作る側で見る物がずれる。
TEACHER_FOCUS = (
    ("おもちゃとして動いたか", "どこが動き、どこが動かなかったか。動かして人に見せに来たか"),
    ("どうしたらもっと楽しいか", "楽しそうだった時、手が止まった時。子どもが足した工夫"),
    ("仕組みは納得できるか", "自分の言葉で言った仕組み。まだ分からないと言った所"),
    ("哲学に沿った効果があったか", "作りながら思いついた事。手元の紙で確かめる様子（例: 筒ができた時に取り組み方が変わった）"),
)
TEACHER_NOTE = "授業の中で見た事を、4 つの着目ごとに書く紙です。点は付けない。子どもの名前は書かず、場面と様子を書く"


def compose_teacher(source, toy, page_name="A4", sheet_set=None):
    """先生の見る紙（U-25 の案 4、本人が採った）。4 つ目の着目は書かせるより見る方が確かな物があるので、先生が書く。

    判断の芯: 採点の欄を置かない（記録は観察で成績にしない、philosophy.md）。子どもの名前の欄を置かない
    （記録を人に結び付けず、場面に結び付ける。実の情報を repo とレビューに持ち出さないため）。
    """
    page = PAGES[page_name]
    width = page.x1 - page.x0
    texts, shapes = [], []
    y = _block(texts, [f"先生の見る紙 {toy}"], page.x0, page.y0, TITLE_SIZE, width)
    if sheet_set:
        y = set_label(texts, f"刷った組 {sheet_set}", page, y)  # U-31
    y = _block(texts, mark_lines(source), page.x0, y + 1, BODY_SIZE, width)
    y = _block(texts, [TEACHER_NOTE], page.x0, y + 1, BODY_SIZE, width)
    y += 2

    def field(label, x, y0, w):
        lw = text_width(label, BODY_SIZE)
        texts.append(TextBox(x, y0, lw, BODY_SIZE * LINE, label, BODY_SIZE))
        shapes.append({"kind": "rect", "x": x + lw + 1.5, "y": y0, "w": w, "h": BODY_SIZE * LINE})
        texts.append(TextBox(x + lw + 1.5, y0, w, BODY_SIZE * LINE, None))
        return x + lw + w + 5

    x = field("日付", page.x0, y, 30)
    x = field("場面", x, y, 60)
    field("人数", x, y, 15)
    y += BODY_SIZE * LINE + GAP

    def lines(y0, n):
        for _ in range(n):
            y0 += ANSWER_GAP
            shapes.append({"kind": "line", "x1": page.x0, "y1": y0 - 1.5, "x2": page.x1, "y2": y0 - 1.5})
        return y0

    for i, (focus, hint) in enumerate(TEACHER_FOCUS, 1):
        y = _block(texts, [f"{i}. {focus}"], page.x0, y, HEAD_SIZE, width)
        y = _block(texts, [hint], page.x0, y, PICTURE_SIZE, width)
        y = lines(y, 3) + 1
    y = _block(texts, ["聞こえたつぶやき（言葉のまま）"], page.x0, y, HEAD_SIZE, width)
    y = lines(y, 3) + 1
    y = _block(texts, ["次の版に返したい事"], page.x0, y, HEAD_SIZE, width)
    lines(y, 2)
    failures = check_layout(page, [], texts)
    return {"page": page, "parts": [], "texts": texts, "samples": [], "ruler": None, "shapes": shapes}, failures
