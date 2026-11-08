# 命令: .venv/bin/python tests/test_name_heart.py
# commit: 095fb28b（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_name_heart.py", line 29, in <module>
    assert readme.count("\n## 名前に込めた思い\n") == 1 and readme.index("\n## 名前に込めた思い\n") < readme.index("\n## 試す\n"), "README の頭の後・試すの前"
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: README の頭の後・試すの前
rc=1
