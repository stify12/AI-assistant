#!/usr/bin/env python3
"""测试批量评估学科筛选功能"""

import requests
import json
from datetime import datetime

BASE_URL = "http://47.82.64.147:5000"

def test_create_task_with_subject():
    """测试创建带学科的任务"""
    
    # 1. 获取作业列表
    print("1. 获取作业列表...")
    response = requests.get(f"{BASE_URL}/api/batch/homework", params={
        'subject_id': 2,  # 数学
        'hours': 168
    })
    data = response.json()
    
    if not data['success'] or not data['data']:
        print("❌ 没有找到作业")
        return
    
    homework_ids = [hw['id'] for hw in data['data'][:5]]  # 取前5个
    print(f"✓ 找到 {len(homework_ids)} 个作业")
    
    # 2. 创建任务（不提供名称，测试自动生成）
    print("\n2. 创建任务（测试自动命名）...")
    response = requests.post(f"{BASE_URL}/api/batch/tasks", json={
        'subject_id': 2,  # 数学
        'homework_ids': homework_ids
    })
    data = response.json()
    
    if not data['success']:
        print(f"❌ 创建失败: {data.get('error')}")
        return
    
    task_id = data['task_id']
    print(f"✓ 任务创建成功: {task_id}")
    
    # 3. 获取任务详情，检查学科信息
    print("\n3. 检查任务详情...")
    response = requests.get(f"{BASE_URL}/api/batch/tasks/{task_id}")
    data = response.json()
    
    if data['success']:
        task = data['data']
        print(f"✓ 任务名称: {task['name']}")
        print(f"✓ 学科ID: {task.get('subject_id')}")
        print(f"✓ 学科名称: {task.get('subject_name')}")
        
        # 验证自动命名格式
        now = datetime.now()
        expected_name = f"数学-{now.month}/{now.day}"
        if task['name'] == expected_name:
            print(f"✓ 自动命名正确: {expected_name}")
        else:
            print(f"⚠ 任务名称不符合预期: 期望 {expected_name}, 实际 {task['name']}")
    
    # 4. 测试学科筛选
    print("\n4. 测试学科筛选...")
    response = requests.get(f"{BASE_URL}/api/batch/tasks", params={
        'subject_id': 2
    })
    data = response.json()
    
    if data['success']:
        tasks = data['data']
        print(f"✓ 找到 {len(tasks)} 个数学任务")
        for task in tasks[:3]:
            print(f"  - {task['name']} (学科: {task.get('subject_name', '未知')})")
    
    print("\n✅ 测试完成!")

if __name__ == '__main__':
    test_create_task_with_subject()
