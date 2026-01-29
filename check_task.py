import json
import sys

task_file = sys.argv[1] if len(sys.argv) > 1 else "batch_tasks/3ad11e36.json"
d = json.load(open(task_file))

print(f"task_id: {d.get('task_id')}")
print(f"name: {d.get('name')}")
print(f"subject_name: {d.get('subject_name')}")
print(f"homework_items: {len(d.get('homework_items', []))}")
print(f"total_questions: {d.get('overall_report', {}).get('total_questions')}")
print(f"has_score: {d.get('has_score')}")

# 检查第一个作业的数据结构
item = d.get('homework_items', [])[0]
print(f"\nKeys in item: {list(item.keys())}")
print(f"Keys in evaluation: {list(item.get('evaluation', {}).keys())}")

# 检查 homework_result 中的分数
hr = json.loads(item.get('homework_result', '[]'))
print(f"\nhomework_result 题目数: {len(hr)}")
if hr:
    print(f"第一题: {hr[0]}")

# 检查 data_value 中的分数
dv = json.loads(item.get('data_value', '[]'))
print(f"\ndata_value 题目数: {len(dv)}")
if dv:
    print(f"第一题 score: {dv[0].get('score')}")
