"""查询服务器数据集"""
from services.database_service import AppDatabaseService
import json

rows = AppDatabaseService.get_datasets()
for r in rows:
    pages = r['pages']
    if isinstance(pages, str):
        pages = json.loads(pages)
    print(f"{r['dataset_id']}: {r['book_name']} - pages={pages}, count={r['question_count']}")
