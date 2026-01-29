import json
import sys

task_file = sys.argv[1] if len(sys.argv) > 1 else "batch_tasks/3ad11e36.json"
d = json.load(open(task_file, encoding='utf-8'))

item = d['homework_items'][0]
print("item keys:", list(item.keys()))
print()
print("有 homework_result:", 'homework_result' in item)
print("有 data_value:", 'data_value' in item)
print("有 evaluation:", 'evaluation' in item)

if 'evaluation' in item:
    eval_data = item['evaluation']
    print("evaluation keys:", list(eval_data.keys()))
    errors = eval_data.get('errors', [])
    print("errors 数量:", len(errors))
    if errors:
        print("第一个 error keys:", list(errors[0].keys()))
