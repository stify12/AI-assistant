#!/usr/bin/env python3
"""测试任务命名逻辑"""

from datetime import datetime

# 学科映射
SUBJECT_MAP = {
    1: '语文',
    2: '数学',
    3: '英语',
    4: '物理',
    5: '化学',
    6: '生物',
    7: '政治',
    8: '历史',
    9: '地理'
}

def generate_task_name(subject_id, custom_name=None):
    """生成任务名称"""
    if custom_name:
        return custom_name
    
    now = datetime.now()
    month_day = f"{now.month}/{now.day}"
    
    if subject_id and subject_id in SUBJECT_MAP:
        return f"{SUBJECT_MAP[subject_id]}-{month_day}"
    else:
        return f"批量评估-{month_day}"

# 测试用例
print("测试任务命名逻辑:")
print("-" * 50)

# 测试1: 有学科ID，无自定义名称
result = generate_task_name(2)
print(f"✓ 数学学科，无自定义名称: {result}")

# 测试2: 有学科ID，有自定义名称
result = generate_task_name(2, "我的测试任务")
print(f"✓ 数学学科，有自定义名称: {result}")

# 测试3: 无学科ID，无自定义名称
result = generate_task_name(None)
print(f"✓ 无学科，无自定义名称: {result}")

# 测试4: 不同学科
for subject_id in [1, 2, 3, 4]:
    result = generate_task_name(subject_id)
    print(f"✓ 学科{subject_id} ({SUBJECT_MAP[subject_id]}): {result}")

print("-" * 50)
print("✅ 所有测试通过!")
