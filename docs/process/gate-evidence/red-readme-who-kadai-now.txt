# 命令: .venv/bin/python tests/test_readme_head.py
# commit: b0ac3899（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 94, in <module>
    assert lines.count(WHO) == 1 and lines.count(KADAI2) == 1, "課題の節の頭の 2 行は本人の字"
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 課題の節の頭の 2 行は本人の字
rc=1
