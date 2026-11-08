# 命令: sh -c '.venv/bin/python tests/test_about_engine.py; a=$?; .venv/bin/python tests/test_readme_head.py; b=$?; echo "about=$a head=$b"; [ $a -eq 0 ] && [ $b -eq 0 ]'
# commit: 82dac852（回した時の HEAD）
Traceback (most recent call last):
  File "tests/test_about_engine.py", line 40, in <module>
    assert f"<h2>{about.ENGINE_HEAD}</h2>" in shown and about.EXAMPLE_MAIN in shown and about.POSITION_FIRST in shown, "具体例の本文と位置づけの 1 文目"
                                                        ^^^^^^^^^^^^^^^^^^
AttributeError: module 'web.about' has no attribute 'EXAMPLE_MAIN'
Traceback (most recent call last):
  File "tests/test_readme_head.py", line 72, in <module>
    order = [at(ONE_LINE), at(SUMMARY_HEAD), *map(at, ROWS), *map(at, PREMISE), at(WORDS), *map(at, ADOPTED), fold, start, end, close]
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "tests/test_readme_head.py", line 62, in at
    assert lines.count(text) == 1, (text, lines.count(text))
           ^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('| 確かめた事 | 4 日間のワークショップ（11 月 4・5・6・7 日）を開きました。デモで体験してもらう 2 案は、それぞれ型紙の版 14・版 7 まで、ワークショップのフィードバックで直りました。 | `data/history/kaizen-history.json`・下の数の欄 |', 0)
about=1 head=1
rc=1
