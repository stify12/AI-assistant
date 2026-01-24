5#!/usr/bin/env python
"""
数据库迁移脚本
执行 add_error_analysis_tables.sql 中的建表语句
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, '/app')

import pymysql

def run_migration():
    """执行数据库迁移"""
    # 连接数据库
    conn = pymysql.connect(
        host=os.environ.get('MYSQL_HOST', 'mysql'),
        user=os.environ.get('MYSQL_USER', 'root'),
        password=os.environ.get('MYSQL_PASSWORD', 'root'),
        database=os.environ.get('MYSQL_DATABASE', 'ai_grading'),
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    
    # 读取SQL文件
    sql_file = os.path.join(os.path.dirname(__file__), 'add_error_analysis_tables.sql')
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 分割SQL语句
    statements = []
    current = []
    for line in sql_content.split('\n'):
        line = line.strip()
        if line.startswith('--') or not line:
            continue
        current.append(line)
        if line.endswith(';'):
            statements.append(' '.join(current))
            current = []
    
    # 执行每条语句
    success = 0
    skipped = 0
    for stmt in statements:
        if not stmt.strip():
            continue
        try:
            cursor.execute(stmt)
            print(f'[OK] {stmt[:60]}...')
            success += 1
        except pymysql.err.OperationalError as e:
            if 'already exists' in str(e):
                print(f'[SKIP] Table already exists')
                skipped += 1
            else:
                print(f'[ERROR] {e}')
        except Exception as e:
            print(f'[ERROR] {e}')
    
    conn.commit()
    conn.close()
    
    print(f'\nMigration completed: {success} executed, {skipped} skipped')

if __name__ == '__main__':
    run_migration()
