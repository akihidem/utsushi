# 命令: .venv/bin/python tests/test_readme_head.py
# commit: 654256ed（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 49, in <module>
    order = [at(ONE_LINE), at(WORDS), *map(at, ADOPTED), *map(at, JUDGE), fold, start, end, close]
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "tests/test_readme_head.py", line 41, in at
    assert lines.count(text) == 1, (text, lines.count(text))
           ^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('- **何の作品か**: 図と歌だけが残る江戸の玩具を、紙の型紙で作って動かし、仕組みを確かめます。サイト（うつし）で玩具を選んで型紙を刷ります。型紙を作る仕組みは、エンジン（paper to toy）として別に開発し、engine/ にも入れました。', 0)
rc=1
