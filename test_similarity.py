#!/usr/bin/env python
"""测试相似度计算"""
from utils.text_utils import calculate_similarity, calculate_char_similarity

t1 = "古桥没有很高价值，且令人高兴，它快要倒塌了"
t2 = "立交桥没有很高价值，但令人高兴，它快要倒塌了"

print(f"字符相似度: {calculate_char_similarity(t1, t2):.2%}")
print(f"TF-IDF相似度: {calculate_similarity(t1, t2):.2%}")
