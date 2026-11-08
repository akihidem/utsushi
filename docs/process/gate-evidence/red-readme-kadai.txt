# 命令: .venv/bin/python tests/test_readme_head.py
# commit: 63502330（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 82, in <module>
    assert text.count(KADAI) == 1 and kadai_sec.rstrip().endswith(KADAI), "課題の節の末尾に本人の字"
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 課題の節の末尾に本人の字
rc=1
