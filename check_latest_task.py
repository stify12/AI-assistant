#!/usr/bin/env python3
"""检查服务器上最新批量评估任务的数据结构"""
import json
import os
from pathlib import Path

batch_dir = Path("batch_tasks")
if not batch_dir.exists():
    print("batch_tasks目录不存在")
    exit(1)

# 获取最新的任务文件
files = sorted(batch_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
if not files:
    print("没有找到任务文件")
    exit(1)

latest_file = files[0]
print(f"最新任务文件: {latest_file.name}")

with open(latest_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\n任务名称: {data.get('name', 'N/A')}")
print(f"创建时间: {data.get('created_at', 'N/A')}")

# 检查第一个作业的评估数据
homework_items = data.get('homework_items', [])
if not homework_items:
    print("没有作业数据")
    exit(1)

first_hw = homework_items[0]
print(f"\n第一个作业:")
print(f"  学生: {first_hw.get('student_name', 'N/A')}")

evaluation = first_hw.get('evaluation', {})
by_question_type = evaluation.get('by_question_type', {})

print(f"\n题型统计字段:")
if not by_question_type:
    print("  ⚠️ by_question_type 字段不存在或为空")
else:
    for qtype in by_question_type.keys():
        stats = by_question_type[qtype]
        print(f"  {qtype}: total={stats.get('total', 0)}, correct={stats.get('correct', 0)}")

# 检查overall_report
overall_report = data.get('overall_report', {})
overall_by_type = overall_report.get('by_question_type', {})
print(f"\n整体报告题型统计:")
if not overall_by_type:
    print("  ⚠️ overall_report.by_question_type 不存在或为空")
else:
    for qtype in overall_by_type.keys():
        stats = overall_by_type[qtype]
        print(f"  {qtype}: total={stats.get('total', 0)}, correct={stats.get('correct', 0)}, accuracy={stats.get('accuracy', 0):.2%}")
