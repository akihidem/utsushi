# 命令: .venv/bin/python tests/test_readme_head.py
# commit: 93368ce（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 45, in <module>
    assert not ("<!--" in ln or "-->" in ln) or HIDDEN.fullmatch(ln), ln
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: <!-- デモ動画のリンクの置き場。上げた後に足す。
rc=1
