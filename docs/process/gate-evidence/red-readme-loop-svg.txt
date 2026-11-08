# 命令: .venv/bin/python tests/test_readme_head.py
# commit: fe38ca6c（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 76, in <module>
    assert IMG and how.count("![") == 1 and "```mermaid" not in text, "図は SVG の絵 1 つ（mermaid の塊を残さない）"
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 図は SVG の絵 1 つ（mermaid の塊を残さない）
rc=1
