#!/usr/bin/env python3
"""检查服务器上的任务数据"""
import json
import sys

task_file = sys.argv[1] if len(sys.argv) > 1 else "batch_tasks/4bb0a303.json"

with open(task_file, 'r', encoding='utf-8') as f:
    d = json.load(f)

print("=== 任务基本信息 ===")
print(f"task_id: {d.get('task_id')}")
print(f"name: {d.get('name')}")
print(f"subject_id: {d.get('subject_id')} (type: {type(d.get('subject_id')).__name__})")
print(f"subject_name: {d.get('subject_name')}")
print(f"fuzzy_threshold: {d.get('fuzzy_threshold')}")
print(f"status: {d.get('status')}")

# 检查作业的book_name
for item in d.get('homework_items', [])[:1]:
    print(f"\n=== 作业信息 ===")
    print(f"book_name: {item.get('book_name')}")
    print(f"homework_name: {item.get('homework_name')}")

# 找有错误的作业
for item in d.get('homework_items', []):
    eval_data = item.get('evaluation', {})
    errors = eval_data.get('errors', [])
    if errors:
        print(f"\n=== 作业: {item.get('homework_name')} page:{item.get('page_num')} ===")
        print(f"错误数: {len(errors)}")
        for e in errors[:5]:
            print(f"\n  题号: {e.get('index')}")
            print(f"  错误类型: {e.get('error_type')}")
            # 检查两种数据格式
            base_user = e.get('base_user') or e.get('base_effect', {}).get('userAnswer', '')
            hw_user = e.get('hw_user') or e.get('ai_result', {}).get('userAnswer', '')
            print(f"  基准答案: {str(base_user)[:100]}")
            print(f"  AI答案: {str(hw_user)[:100]}")
            print(f"  similarity: {e.get('similarity')}")
            print(f"  keys: {list(e.keys())}")
        break
