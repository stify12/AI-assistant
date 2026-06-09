#!/usr/bin/env python3
"""检查批量评估任务中的主观题数据"""
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

print(f"任务名称: {data.get('name', 'N/A')}")
print(f"创建时间: {data.get('created_at', 'N/A')}")

# 检查第一个作业的评估数据
homework_items = data.get('homework_items', [])
if not homework_items:
    print("没有作业数据")
    exit(1)

first_hw = homework_items[0]
print(f"\n第一个作业:")
print(f"  学生: {first_hw.get('student_name', 'N/A')}")
print(f"  状态: {first_hw.get('status', 'N/A')}")

evaluation = first_hw.get('evaluation', {})
by_question_type = evaluation.get('by_question_type', {})

print(f"\n题型统计 (by_question_type):")
if not by_question_type:
    print("  ⚠️ by_question_type 字段不存在或为空")
else:
    for qtype, stats in by_question_type.items():
        print(f"  {qtype}: {json.dumps(stats, ensure_ascii=False)}")

# 检查overall_report
overall_report = data.get('overall_report', {})
overall_by_type = overall_report.get('by_question_type', {})
print(f"\n整体报告题型统计:")
if not overall_by_type:
    print("  ⚠️ overall_report.by_question_type 不存在或为空")
else:
    for qtype, stats in overall_by_type.items():
        print(f"  {qtype}: {json.dumps(stats, ensure_ascii=False)}")
