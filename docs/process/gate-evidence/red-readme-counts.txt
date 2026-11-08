# 命令: .venv/bin/python tests/test_readme_head.py
# commit: 42b269cf（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 127, in <module>
    assert "提出の日に数え直して書きます" not in text and "（11-08 16:40 に数えた）" in use and "統括と窓口を除く担当のセッションは" in use, "数の行"
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 数の行
rc=1
