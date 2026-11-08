# 命令: .venv/bin/python tests/test_readme_head.py
# commit: db158a2a（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 47, in <module>
    head = [ln for ln in lines[1:at("## 試す")] if ln.strip()]
                                 ~~^^^^^^^^^^^
  File "tests/test_readme_head.py", line 41, in at
    assert lines.count(line) == 1, (line[:60], lines.count(line))
           ^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('## 試す', 0)
rc=1
