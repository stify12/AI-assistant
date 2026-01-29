import json
import sys

task_file = sys.argv[1] if len(sys.argv) > 1 else "batch_tasks/3ad11e36.json"
d = json.load(open(task_file, encoding='utf-8'))

item = d['homework_items'][0]
dv = json.loads(item.get('data_value', '[]'))
hr = json.loads(item.get('homework_result', '[]'))

print('data_value 题目数:', len(dv))
if dv:
    print('data_value 第一题 keys:', list(dv[0].keys()))
    print('data_value 第一题 score:', dv[0].get('score'))
    print('data_value 第一题 sorce:', dv[0].get('sorce'))
    print('data_value 第一题 maxScore:', dv[0].get('maxScore'))

print()
print('homework_result 题目数:', len(hr))
if hr:
    print('homework_result 第一题 keys:', list(hr[0].keys()))
    print('homework_result 第一题 score:', hr[0].get('score'))
