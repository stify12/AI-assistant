#!/bin/bash
cd /www/wwwroot/ai-grading/Ai/datasets
for f in *.json; do
    echo "=== $f ==="
    python3 -c "import json; d=json.load(open('$f')); print('Book ID:', d['book_id']); print('Pages:', d['pages']); print('Question count:', d.get('question_count', 'N/A'))"
    echo ""
done
