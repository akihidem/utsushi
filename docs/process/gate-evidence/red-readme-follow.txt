# 命令: .venv/bin/python tests/test_readme_head.py
# commit: 611d1591（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 68, in <module>
    order = [at(ONE_LINE), at(SUMMARY_HEAD), *map(at, ROWS), *map(at, PREMISE), at(WORDS), *map(at, ADOPTED), fold, start, end, close]
             ~~^^^^^^^^^^
  File "tests/test_readme_head.py", line 58, in at
    assert lines.count(text) == 1, (text, lines.count(text))
           ^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('> うしなわれた玩具の動きを、紙でよみがえらせる', 0)
rc=1
