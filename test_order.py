#!/usr/bin/env python
"""测试混合相似度算法"""
from utils.text_utils import calculate_similarity, calculate_char_similarity

print("=== 混合相似度测试 (60% TF-IDF + 40% 序列) ===\n")

test_cases = [
    # (文本1, 文本2, 说明)
    ("原句①介绍造型，③介绍结构，②介绍工艺", 
     "原句①介绍造型，②介绍结构，③介绍工艺", 
     "词序差异"),
    
    ("古桥没有很高价值，且令人高兴，它快要倒塌了", 
     "立交桥没有很高价值，但令人高兴，它快要倒塌了", 
     "语义差异(古桥vs立交桥)"),
    
    ("答案是A", "答案是a", "大小写差异"),
    ("答案是A", "答案是B", "完全不同答案"),
    
    ("这道题的答案是正确的", "这道题的答案是正确的", "完全相同"),
    
    ("①②③④⑤", "①③②④⑤", "序号顺序差异"),
    ("①②③④⑤", "⑤④③②①", "序号完全颠倒"),
]

for t1, t2, desc in test_cases:
    char_sim = calculate_char_similarity(t1, t2)
    mixed_sim = calculate_similarity(t1, t2)
    print(f"【{desc}】")
    print(f"  文本1: {t1}")
    print(f"  文本2: {t2}")
    print(f"  字符相似度: {char_sim:.2%}")
    print(f"  混合相似度: {mixed_sim:.2%}")
    print()
