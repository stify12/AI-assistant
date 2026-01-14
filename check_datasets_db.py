#!/usr/bin/env python3
"""检查数据库中的数据集"""
import json
from services.database_service import DatabaseService

# 查询所有数据集
sql = """
    SELECT dataset_id, book_id, pages, question_count, created_at
    FROM zp_batch_datasets
    ORDER BY created_at DESC
"""

rows = DatabaseService.execute_query(sql)

print(f"找到 {len(rows)} 个数据集:\n")

for row in rows:
    dataset_id = row['dataset_id']
    book_id = row['book_id']
    pages = row['pages']
    if isinstance(pages, str):
        pages = json.loads(pages)
    question_count = row['question_count']
    created_at = row['created_at']
    
    print(f"Dataset ID: {dataset_id}")
    print(f"  Book ID: {book_id}")
    print(f"  Pages: {pages}")
    print(f"  Questions: {question_count}")
    print(f"  Created: {created_at}")
    print()
