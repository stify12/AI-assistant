#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复任务 2a54e4fd 的数据集匹配
"""
import json

# 读取任务文件
with open('batch_tasks/2a54e4fd.json', 'r', encoding='utf-8') as f:
    task = json.load(f)

# 读取数据集
with open('datasets/fa2e6320.json', 'r', encoding='utf-8') as f:
    dataset = json.load(f)

print(f"数据集 {dataset['dataset_id']}: Book {dataset['book_id']}, Pages {dataset['pages']}")
print()

updated = 0
for item in task['homework_items']:
    book_id = str(item['book_id'])
    page_num = item['page_num']
    old_match = item.get('matched_dataset')
    
    # 检查是否应该匹配到 fa2e6320
    if book_id == dataset['book_id'] and page_num in dataset['pages']:
        if old_match != dataset['dataset_id']:
            print(f"更新: 第{page_num}页 - {old_match} -> {dataset['dataset_id']}")
            item['matched_dataset'] = dataset['dataset_id']
            item['status'] = 'matched'
            updated += 1
        else:
            print(f"已匹配: 第{page_num}页 -> {dataset['dataset_id']}")
    else:
        print(f"不匹配: 第{page_num}页 (Book: {book_id}, 当前: {old_match})")

print(f"\n总共更新了 {updated} 个作业")

if updated > 0:
    # 保存任务文件
    with open('batch_tasks/2a54e4fd.json', 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    print("任务文件已更新")
