#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据集名称迁移脚本
为现有无 name 字段的数据集生成默认名称

格式："{book_name}_P{min_page}-{max_page}_{timestamp}"
- 单页："{book_name}_P{page}_{timestamp}"
- 无页码："{book_name}_{timestamp}"
- 无书名：使用 "未知书本"

Requirements: 6.5
"""

import pymysql
import json
from datetime import datetime


# 数据库连接配置
MYSQL_CONFIG = {
    'host': '47.82.64.147',
    'port': 3306,
    'user': 'aiuser',
    'password': '123456',
    'database': 'aiuser',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(**MYSQL_CONFIG)


def check_name_column_exists(cursor):
    """
    检查 datasets 表是否存在 name 字段
    
    Returns:
        bool: True 如果存在，False 如果不存在
    """
    cursor.execute("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = %s 
          AND TABLE_NAME = 'datasets' 
          AND COLUMN_NAME = 'name'
    """, (MYSQL_CONFIG['database'],))
    result = cursor.fetchone()
    return result['cnt'] > 0


def add_name_column(cursor):
    """
    为 datasets 表添加 name 字段
    """
    print("      添加 name 字段到 datasets 表...")
    cursor.execute("""
        ALTER TABLE datasets 
        ADD COLUMN name VARCHAR(200) DEFAULT NULL COMMENT '数据集名称' 
        AFTER dataset_id
    """)
    print("      name 字段添加成功")
    
    # 添加索引
    print("      添加 name 字段索引...")
    try:
        cursor.execute("CREATE INDEX idx_datasets_name ON datasets(name)")
        print("      索引添加成功")
    except pymysql.Error as e:
        if e.args[0] == 1061:  # Duplicate key name
            print("      索引已存在，跳过")
        else:
            raise


def generate_default_name(book_name, pages, created_at):
    """
    生成默认数据集名称
    
    Args:
        book_name: 书本名称，可能为 None
        pages: 页码列表（JSON字符串或列表），可能为 None
        created_at: 创建时间，datetime 对象
    
    Returns:
        str: 生成的默认名称
    """
    # 处理书名
    name_part = book_name if book_name else "未知书本"
    
    # 处理页码
    page_part = ""
    if pages:
        # 解析 pages（可能是 JSON 字符串或已解析的列表）
        if isinstance(pages, str):
            try:
                pages_list = json.loads(pages)
            except (json.JSONDecodeError, TypeError):
                pages_list = []
        else:
            pages_list = pages
        
        if pages_list and isinstance(pages_list, list):
            # 过滤有效页码并排序
            valid_pages = sorted([p for p in pages_list if isinstance(p, int) and p > 0])
            if valid_pages:
                if len(valid_pages) == 1:
                    page_part = f"_P{valid_pages[0]}"
                else:
                    page_part = f"_P{min(valid_pages)}-{max(valid_pages)}"
    
    # 处理时间戳
    if created_at:
        if isinstance(created_at, datetime):
            timestamp = created_at.strftime('%m%d%H%M')
        else:
            # 尝试解析字符串
            try:
                dt = datetime.strptime(str(created_at), '%Y-%m-%d %H:%M:%S')
                timestamp = dt.strftime('%m%d%H%M')
            except (ValueError, TypeError):
                timestamp = datetime.now().strftime('%m%d%H%M')
    else:
        timestamp = datetime.now().strftime('%m%d%H%M')
    
    # 组合名称
    return f"{name_part}{page_part}_{timestamp}"


def migrate_dataset_names():
    """
    迁移数据集名称
    为所有 name 为 NULL 的数据集生成默认名称
    """
    conn = None
    cursor = None
    
    try:
        print("=" * 60)
        print("数据集名称迁移脚本")
        print("=" * 60)
        print()
        
        # 连接数据库
        print(f"[1/5] 连接数据库: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}")
        conn = get_connection()
        cursor = conn.cursor()
        print("      数据库连接成功")
        print()
        
        # 检查并添加 name 字段
        print("[2/5] 检查 name 字段...")
        if not check_name_column_exists(cursor):
            print("      name 字段不存在，正在添加...")
            add_name_column(cursor)
            conn.commit()
        else:
            print("      name 字段已存在")
        print()
        
        # 查询所有 name 为 NULL 的数据集
        print("[3/5] 查询需要迁移的数据集...")
        sql_query = """
            SELECT dataset_id, book_name, pages, created_at 
            FROM datasets 
            WHERE name IS NULL OR name = ''
        """
        cursor.execute(sql_query)
        datasets = cursor.fetchall()
        
        total_count = len(datasets)
        print(f"      找到 {total_count} 个需要迁移的数据集")
        print()
        
        if total_count == 0:
            print("[4/5] 无需迁移，所有数据集已有名称")
            print()
            print("[5/5] 迁移完成")
            print()
            print("=" * 60)
            print("迁移摘要")
            print("=" * 60)
            print(f"  总数据集数: 0")
            print(f"  成功迁移数: 0")
            print(f"  失败数: 0")
            return
        
        # 执行迁移
        print("[4/5] 开始迁移...")
        success_count = 0
        fail_count = 0
        
        for i, dataset in enumerate(datasets, 1):
            dataset_id = dataset['dataset_id']
            book_name = dataset['book_name']
            pages = dataset['pages']
            created_at = dataset['created_at']
            
            try:
                # 生成默认名称
                default_name = generate_default_name(book_name, pages, created_at)
                
                # 更新数据库
                sql_update = "UPDATE datasets SET name = %s WHERE dataset_id = %s"
                cursor.execute(sql_update, (default_name, dataset_id))
                
                success_count += 1
                print(f"      [{i}/{total_count}] {dataset_id}: {default_name}")
                
            except Exception as e:
                fail_count += 1
                print(f"      [{i}/{total_count}] {dataset_id}: 失败 - {str(e)}")
        
        # 提交事务
        conn.commit()
        print()
        print("[5/5] 迁移完成，事务已提交")
        print()
        
        # 打印摘要
        print("=" * 60)
        print("迁移摘要")
        print("=" * 60)
        print(f"  总数据集数: {total_count}")
        print(f"  成功迁移数: {success_count}")
        print(f"  失败数: {fail_count}")
        
        if fail_count > 0:
            print()
            print("  注意: 部分数据集迁移失败，请检查错误信息")
        
    except pymysql.Error as e:
        print(f"数据库错误: {e}")
        if conn:
            conn.rollback()
            print("事务已回滚")
        raise
        
    except Exception as e:
        print(f"迁移失败: {e}")
        if conn:
            conn.rollback()
            print("事务已回滚")
        raise
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print()
            print("数据库连接已关闭")


def preview_migration():
    """
    预览迁移结果（不实际执行更新）
    """
    conn = None
    cursor = None
    
    try:
        print("=" * 60)
        print("数据集名称迁移预览（不执行实际更新）")
        print("=" * 60)
        print()
        
        # 连接数据库
        print(f"连接数据库: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}")
        conn = get_connection()
        cursor = conn.cursor()
        print("数据库连接成功")
        print()
        
        # 检查 name 字段是否存在
        print("检查 name 字段...")
        name_exists = check_name_column_exists(cursor)
        if not name_exists:
            print("  name 字段不存在，执行迁移时将自动添加")
            print()
            # 查询所有数据集（因为 name 字段不存在，所有都需要迁移）
            sql_query = """
                SELECT dataset_id, book_name, pages, created_at 
                FROM datasets
            """
        else:
            print("  name 字段已存在")
            print()
            # 查询所有 name 为 NULL 的数据集
            sql_query = """
                SELECT dataset_id, book_name, pages, created_at 
                FROM datasets 
                WHERE name IS NULL OR name = ''
            """
        
        cursor.execute(sql_query)
        datasets = cursor.fetchall()
        
        total_count = len(datasets)
        print(f"找到 {total_count} 个需要迁移的数据集:")
        print()
        
        if total_count == 0:
            print("无需迁移，所有数据集已有名称")
            return
        
        print("-" * 80)
        print(f"{'dataset_id':<15} {'book_name':<25} {'生成的名称':<40}")
        print("-" * 80)
        
        for dataset in datasets:
            dataset_id = dataset['dataset_id']
            book_name = dataset['book_name'] or "未知书本"
            pages = dataset['pages']
            created_at = dataset['created_at']
            
            default_name = generate_default_name(book_name, pages, created_at)
            
            # 截断显示
            book_display = book_name[:22] + "..." if len(book_name) > 25 else book_name
            name_display = default_name[:37] + "..." if len(default_name) > 40 else default_name
            
            print(f"{dataset_id:<15} {book_display:<25} {name_display:<40}")
        
        print("-" * 80)
        print()
        print(f"共 {total_count} 个数据集将被更新")
        print()
        print("如需执行迁移，请运行: python migrate_dataset_names.py --execute")
        
    except Exception as e:
        print(f"预览失败: {e}")
        raise
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        # 执行实际迁移
        migrate_dataset_names()
    elif len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("数据集名称迁移脚本")
        print()
        print("用法:")
        print("  python migrate_dataset_names.py           # 预览迁移（不执行）")
        print("  python migrate_dataset_names.py --execute # 执行迁移")
        print("  python migrate_dataset_names.py --help    # 显示帮助")
    else:
        # 默认预览模式
        preview_migration()
