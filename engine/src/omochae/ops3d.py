"""3D で組む操作と、その操作から作る手順の文（御来迎 つまみの形）。

制作者の決定（2026-11-06「手順の文は 3D の操作から作る」）による。3D で組める部品（外筒・内筒・竹串）の手順だけを、型紙のデータ
（線を刷るか色の境で折るか・谷か山か・穴の数・部品の番号と名）から作る。omochae.fold3d が同じ部品のデータを 3D の中で折って組んで
確かめるので、手順の文と 3D の組み方が食い違わない（データを直すと、文も 3D も一緒に変わる）。
判断の芯:
- 台・扇・糸・像・物差し・切る手順は、まだ 3D で組んでいないので雛形の文のまま（3D で組むまで広げるかは制作者が決める）
- 手順の番号はずらさない。作った人の報告と直しの案が、手順の番号を鍵にしているため。組み立ての最後の動き（押し上げて蛇腹が開く）は、
  今の手順の後ろに足す（制作者の追加 2026-11-06）
- 2 つ目の筒の文の「は／も」は、1 つ目の筒と折り方（色の境か破線か・谷か山か）が違えば「は」、同じなら「も」。制作者の決定の手順 2
  「2 内筒は破線で谷折りし、糊代で貼って角筒にする」が、今のデータから一字も違わずにできる
- 雛形からも読むので、ここは雛形と組み立ての検査（compose・fold3d）を読み込まない（読み込みの輪を作らない）
"""


def fold_words(part):
    """部品の折り方の言葉: どこで折るか（色の境か破線か）と、谷か山か。"""
    where = "色の境" if part.hide_folds else "破線"
    if part.mountain and not part.valley:
        kind = "山折り"
    elif part.valley and not part.mountain:
        kind = "谷折り"
    else:
        kind = "谷折りと山折り"  # 角筒では出ない形。出れば、文に両方を言う（どちらかに言い切らない）
    return where, kind


def ops(parts, p):
    """つまみの形の、3D で組む操作の並び（組む順）。Returns [(種類, 手順の文)]。種類は fold3d が確かめる操作の名前。

    fold_outer・fold_inner は筒を折って閉じる（3D.close・3D.face）、thread は竹串を内筒の穴に通す、insert は内筒を外筒に入れる、
    push は押し上げる行程（3D.skewer が行程の全部で竹串が溝を通る事を見る）。
    """
    by = {q.key: q for q in parts}
    outer, inner = by["tube"], by["pusher"]
    # 扇は手順 13 の文に名を出すだけ。外筒と内筒だけを渡しても呼べるようにする（3D の確かめは扇の部品を要らない）
    fan = by["fan"].label if "fan" in by else "扇"
    w1, w2 = fold_words(outer), fold_words(inner)
    particle = "も" if w1 == w2 else "は"
    return [
        ("fold_outer", f"{outer.label}を{w1[0]}で{w1[1]}し、糊代で貼って角筒にする"),
        ("fold_inner", f"{inner.label}{particle}{w2[0]}で{w2[1]}し、糊代で貼って角筒にする"),
        ("thread", f"竹串を {inner.label}の {len(inner.holes)} つの穴に通す"),
        ("insert", f"{inner.name}を {outer.label}に入れ、竹串の端を溝から出す"),
        # 押し上げる量は文に入れない（制作者の答え 2026-11-06「上に押し上げる」だけでいい）。長さは 3D.skewer が竹串の行程として見る
        ("push", f"竹串の端を溝に沿って上に押し上げると、{fan}が {outer.label}の口から出て、蛇腹が開く"),
    ]
