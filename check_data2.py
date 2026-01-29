import json
import sys

task_file = sys.argv[1] if len(sys.argv) > 1 else "batch_tasks/3ad11e36.json"
d = json.load(open(task_file, encoding='utf-8'))

print(f"homework_items 数量: {len(d.get('homework_items', []))}")

# 统计所有作业的题目数
total_dv = 0
total_hr = 0
for i, item in enumerate(d.get('homework_items', [])):
    dv = json.loads(item.get('data_value', '[]'))
    hr = json.loads(item.get('homework_result', '[]'))
    total_dv += len(dv)
    total_hr += len(hr)
    if i == 0:
        print(f"\n第一份作业:")
        print(f"  data_value 题数: {len(dv)}")
        print(f"  homework_result 题数: {len(hr)}")
        # 检查是否有 children
        if dv and 'children' in dv[0]:
            print(f"  第一题有 children: {len(dv[0].get('children', []))}")
        if hr and 'children' in hr[0]:
            print(f"  homework_result 第一题有 children: {len(hr[0].get('children', []))}")

print(f"\n总计:")
print(f"  data_value 总题数: {total_dv}")
print(f"  homework_result 总题数: {total_hr}")

# 检查 overall_report
report = d.get('overall_report', {})
print(f"\noverall_report:")
print(f"  total_questions: {report.get('total_questions')}")
print(f"  has_score: {d.get('has_score')}")
