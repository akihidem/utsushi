# 命令: .venv/bin/python tests/test_readme_head.py
# commit: ace2a5f0（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 66, in <module>
    order = [at(ONE_LINE), at(SUMMARY_HEAD), *map(at, ROWS), *map(at, PREMISE), at(WORDS), *map(at, ADOPTED), fold, start, end, close]
                           ~~^^^^^^^^^^^^^^
  File "tests/test_readme_head.py", line 56, in at
    assert lines.count(text) == 1, (text, lines.count(text))
           ^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('## 要約', 0)
rc=1
