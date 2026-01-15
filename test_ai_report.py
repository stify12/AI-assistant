"""测试 AI 报告生成的数据结构"""
import json
import os

# 查找 batch_tasks 目录下的任务文件
batch_tasks_dir = 'batch_tasks'
if os.path.exists(batch_tasks_dir):
    for filename in os.listdir(batch_tasks_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(batch_tasks_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            print(f"\n=== 任务: {task_data.get('name', filename)} ===")
            print(f"状态: {task_data.get('status')}")
            
            homework_items = task_data.get('homework_items', [])
            print(f"作业数: {len(homework_items)}")
            
            total_questions = 0
            total_correct = 0
            error_distribution = {}
            
            for hw in homework_items:
                if hw.get('status') == 'completed' and hw.get('evaluation'):
                    result = hw['evaluation']
                    print(f"\n  作业 {hw.get('homework_id')}:")
                    print(f"    evaluation keys: {list(result.keys())}")
                    
                    # 检查字段名
                    hw_total = result.get('total_questions', 0) or result.get('total', 0)
                    hw_correct = result.get('correct_count', 0) or result.get('correct', 0)
                    print(f"    total_questions: {result.get('total_questions')}, total: {result.get('total')}")
                    print(f"    correct_count: {result.get('correct_count')}, correct: {result.get('correct')}")
                    print(f"    使用值: total={hw_total}, correct={hw_correct}")
                    
                    total_questions += hw_total
                    total_correct += hw_correct
                    
                    for err_type, count in result.get('error_distribution', {}).items():
                        error_distribution[err_type] = error_distribution.get(err_type, 0) + count
            
            print(f"\n汇总: 总题数={total_questions}, 正确数={total_correct}")
            print(f"错误分布: {error_distribution}")
            
            # 只测试第一个任务
            break
else:
    print("batch_tasks 目录不存在")
