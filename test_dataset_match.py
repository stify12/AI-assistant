#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据集匹配功能
"""
import json
import os

def test_dataset_match():
    """测试数据集匹配"""
    # 读取数据集
    dataset_file = 'datasets/fa2e6320.json'
    with open(dataset_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    print("数据集信息:")
    print(f"  Dataset ID: {dataset['dataset_id']}")
    print(f"  Book ID: {dataset['book_id']}")
    print(f"  Pages: {dataset['pages']}")
    print(f"  Subject ID: {dataset['subject_id']}")
    print(f"  Question Count: {dataset['question_count']}")
    print()
    
    # 测试匹配逻辑
    test_cases = [
        {'book_id': '1998967464626053121', 'page_num': 2, 'expected': True},
        {'book_id': '1998967464626053121', 'page_num': 3, 'expected': True},
        {'book_id': '1998967464626053121', 'page_num': 4, 'expected': True},
        {'book_id': '1998967464626053121', 'page_num': 5, 'expected': True},
        {'book_id': '1998967464626053121', 'page_num': 6, 'expected': False},
        {'book_id': '1997848714229166082', 'page_num': 2, 'expected': False},
    ]
    
    print("匹配测试:")
    for test in test_cases:
        book_id = test['book_id']
        page_num = test['page_num']
        expected = test['expected']
        
        # 匹配逻辑（同时检查整数和字符串形式）
        matched = (
            dataset['book_id'] == book_id and 
            (page_num in dataset['pages'] or str(page_num) in [str(p) for p in dataset['pages']])
        )
        
        status = "✓" if matched == expected else "✗"
        print(f"  {status} Book: {book_id[-6:]}, Page: {page_num} -> {matched} (expected: {expected})")
    
    print()
    print("基准数据详情:")
    for page, questions in dataset['base_effects'].items():
        print(f"  第 {page} 页: {len(questions)} 道题")
        for i, q in enumerate(questions[:2], 1):  # 只显示前2题
            print(f"    {i}. 题号: {q['index']}, 答案: {q['answer'][:30]}...")

if __name__ == '__main__':
    test_dataset_match()
