# 命令: sh -c '.venv/bin/python tests/test_about_engine.py; a=$?; .venv/bin/python tests/test_readme_head.py; b=$?; echo "about=$a head=$b"; [ $a -eq 0 ] && [ $b -eq 0 ]'
# commit: a2e9cbb3（回した時の HEAD）
ok うつしと paper to toy（序の頁の置き場・位置づけ・具体例・仕組みの 5 文・段の図・README のエンジンの短い節と大前提が序の頁と同じ字）
ok README の頭は本人が採った字で、要約 10 項目は畳んである
about=0 head=0
rc=0
