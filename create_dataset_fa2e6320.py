#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建数据集 fa2e6320 for book_id 1998967464626053121 pages 2,3,4,5
"""
import pymysql
import json
from datetime import datetime

# 数据库配置
DB_CONFIG = {
    'host': '47.113.230.78',
    'port': 3306,
    'user': 'zpsmart',
    'password': 'rootyouerkj!',
    'database': 'zpsmart',
    'charset': 'utf8mb4'
}

def get_baseline_data():
    """从数据库中提取基准数据"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    base_effects = {}
    
    # 查询每个页面的一个样本作业
    for page_num in [2, 3, 4, 5]:
        sql = """
        SELECT homework_result, subject_id 
        FROM zp_homework 
        WHERE book_id = '1998967464626053121' 
        AND page_num = %s 
        AND homework_result IS NOT NULL 
        AND homework_result != ''
        LIMIT 1
        """
        cursor.execute(sql, (page_num,))
        result = cursor.fetchone()
        
        if result and result['homework_result']:
            try:
                homework_data = json.loads(result['homework_result'])
                subject_id = result['subject_id']
                
                # 转换为 base_effects 格式
                page_data = []
                for item in homework_data:
                    # 提取基准数据
                    base_item = {
                        'index': item.get('index', ''),
                        'answer': item.get('mainAnswer', item.get('answer', '')),
                        'userAnswer': item.get('userAnswer', ''),
                        'correct': item.get('correct', 'no'),
                        'tempIndex': item.get('tempIndex', 0),
                        'questionType': 'objective',  # 默认客观题
                        'bvalue': '4'  # 默认分值
                    }
                    
                    # 跳过空数据
                    if base_item['index'] or base_item['answer'] or base_item['userAnswer']:
                        page_data.append(base_item)
                
                if page_data:
                    base_effects[str(page_num)] = page_data
                    print(f"✓ 页面 {page_num}: 提取了 {len(page_data)} 道题")
                else:
                    print(f"✗ 页面 {page_num}: 没有有效数据")
            except json.JSONDecodeError as e:
                print(f"✗ 页面 {page_num}: JSON解析失败 - {e}")
        else:
            print(f"✗ 页面 {page_num}: 没有找到作业数据")
    
    cursor.close()
    conn.close()
    
    return base_effects, subject_id if 'subject_id' in locals() else 1

def create_dataset():
    """创建数据集文件"""
    print("开始创建数据集 fa2e6320...")
    
    base_effects, subject_id = get_baseline_data()
    
    if not base_effects:
        print("错误: 没有提取到任何基准数据")
        return False
    
    # 计算总题目数
    question_count = sum(len(questions) for questions in base_effects.values())
    
    dataset = {
        'dataset_id': 'fa2e6320',
        'book_id': '1998967464626053121',
        'subject_id': subject_id,
        'pages': [2, 3, 4, 5],
        'base_effects': base_effects,
        'created_at': datetime.now().isoformat(),
        'question_count': question_count
    }
    
    # 保存到本地
    output_file = 'datasets/fa2e6320.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 数据集创建成功!")
    print(f"  - 文件: {output_file}")
    print(f"  - Book ID: {dataset['book_id']}")
    print(f"  - Subject ID: {dataset['subject_id']}")
    print(f"  - 页面: {dataset['pages']}")
    print(f"  - 总题数: {question_count}")
    
    return True

if __name__ == '__main__':
    create_dataset()
