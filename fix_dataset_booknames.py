"""
一次性脚本：补全数据集中缺失的 book_name 和 subject_id
同时更新名称中包含"未知书本"的数据集
"""
import os
import sys

# 设置环境变量
os.environ['USE_DB_STORAGE'] = 'true'

from services.database_service import DatabaseService, AppDatabaseService

def fix_booknames():
    """补全数据集中缺失的 book_name 和 subject_id"""
    
    # 1. 获取所有数据集
    datasets = AppDatabaseService.execute_query(
        "SELECT dataset_id, book_id, book_name, subject_id, name FROM datasets"
    )
    
    print(f"共 {len(datasets)} 个数据集")
    
    # 2. 找出需要修复的数据集（book_name 为空或 subject_id 为 NULL）
    missing = [d for d in datasets if not d.get('book_name') or d.get('subject_id') is None]
    print(f"需要修复: {len(missing)} 个")
    
    if not missing:
        print("所有数据集都有完整信息，无需修复")
        return
    
    # 3. 批量查询书本信息
    book_ids = list(set(d['book_id'] for d in missing if d.get('book_id')))
    print(f"需要查询 {len(book_ids)} 个书本")
    
    if not book_ids:
        print("没有有效的 book_id")
        return
    
    placeholders = ','.join(['%s'] * len(book_ids))
    sql = f"SELECT id, book_name, subject_id FROM zp_make_book WHERE id IN ({placeholders})"
    books = DatabaseService.execute_query(sql, tuple(book_ids))
    
    book_map = {b['id']: b for b in books}
    print(f"查询到 {len(books)} 个书本信息")
    
    # 4. 更新数据集
    updated = 0
    for d in missing:
        book_id = d.get('book_id')
        if not book_id:
            continue
        
        book_info = book_map.get(book_id)
        if book_info:
            book_name = book_info.get('book_name') or f"书本 {book_id[-6:]}"
            subject_id = book_info.get('subject_id')
            if subject_id is None:
                subject_id = 0
        else:
            book_name = f"书本 {book_id[-6:]}"
            subject_id = 0
        
        # 检查是否需要更新名称（替换"未知书本"）
        current_name = d.get('name') or ''
        new_name = current_name
        if '未知书本' in current_name:
            new_name = current_name.replace('未知书本', book_name)
        
        # 更新数据库
        AppDatabaseService.execute_update(
            "UPDATE datasets SET book_name = %s, subject_id = %s, name = %s WHERE dataset_id = %s",
            (book_name, subject_id, new_name, d['dataset_id'])
        )
        updated += 1
        print(f"  更新 {d['dataset_id']}: book_name={book_name}, subject_id={subject_id}, name={new_name}")
    
    print(f"\n完成！更新了 {updated} 个数据集")

if __name__ == '__main__':
    fix_booknames()
