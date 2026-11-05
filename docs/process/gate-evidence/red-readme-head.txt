# 命令: .venv/bin/python tests/test_readme_head.py
# commit: 6f386d7（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 34, in <module>
    fold, start, end, close = at("<details>"), at("<!-- summary:start -->"), at("<!-- summary:end -->"), at("</details>")
                              ~~^^^^^^^^^^^^^
  File "tests/test_readme_head.py", line 27, in at
    assert lines.count(text) == 1, (text, lines.count(text))
           ^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('<details>', 0)
rc=1
