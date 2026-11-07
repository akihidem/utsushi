# 命令: .venv/bin/python tests/test_readme_engine.py
# commit: 5e3a61c（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_readme_engine.py", line 53, in <module>
    assert heads or not full, "engine/ を入れた commit の印（git-subtree-dir: engine・git-subtree-split）が履歴に無い"
           ^^^^^^^^^^^^^^^^^
AssertionError: engine/ を入れた commit の印（git-subtree-dir: engine・git-subtree-split）が履歴に無い
rc=1
