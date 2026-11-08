# 命令: .venv/bin/python tests/test_workshop_count.py
# commit: f032cc8a（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_workshop_count.py", line 30, in <module>
    assert "のべ 30 人参加し、全員が実物の型紙を試した" in summary and "そのうち 11 月 4 日の回は" in summary, (name, "5 人はのべ 30 人に入る")
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('README.md', '5 人はのべ 30 人に入る')
rc=1
