#!/usr/bin/env python3
"""检查 fa2e6320 数据集"""
import json
from services.database_service import AppDatabaseService

dataset_id = 'fa2e6320'

# 查询数据集信息
sql = "SELECT * FROM zp_batch_datasets WHERE dataset_id = %s"
rows = AppDatabaseService.execute_query(sql, (dataset_id,))

if rows:
    ds = rows[0]
    pages = ds['pages']
    if isinstance(pages, str):
        pages = json.loads(pages)
    print(f"Dataset: {dataset_id}")
    print(f"  Book ID: {ds['book_id']}")
    print(f"  Pages (from dataset): {pages}")
    print(f"  Question count: {ds['question_count']}")
    print()

# 查询基准效果
sql = "SELECT page_num, COUNT(*) as count FROM zp_baseline_effects WHERE dataset_id = %s GROUP BY page_num ORDER BY page_num"
rows = AppDatabaseService.execute_query(sql, (dataset_id,))

print("Base effects by page:")
for row in rows:
    print(f"  Page {row['page_num']}: {row['count']} questions")
