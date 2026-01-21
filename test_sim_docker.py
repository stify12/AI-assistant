#!/usr/bin/env python
"""测试相似度计算 - Docker 容器内"""
import sys
sys.path.insert(0, '/app')

# 直接测试 jieba + TF-IDF
t1 = "古桥没有很高价值且令人高兴它快要倒塌了"
t2 = "立交桥没有很高价值但令人高兴它快要倒塌了"

print("=== 直接测试 jieba + TF-IDF ===")
try:
    import jieba
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    
    words1 = ' '.join(jieba.cut(t1))
    words2 = ' '.join(jieba.cut(t2))
    print(f"分词1: {words1}")
    print(f"分词2: {words2}")
    
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([words1, words2])
    sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    print(f"TF-IDF 相似度: {sim:.2%}")
except Exception as e:
    print(f"错误: {e}")

print("\n=== 测试 text_utils 函数 ===")
from utils.text_utils import calculate_similarity, calculate_char_similarity

t1_raw = "古桥没有很高价值，且令人高兴，它快要倒塌了"
t2_raw = "立交桥没有很高价值，但令人高兴，它快要倒塌了"

print(f"字符相似度: {calculate_char_similarity(t1_raw, t2_raw):.2%}")
print(f"calculate_similarity: {calculate_similarity(t1_raw, t2_raw):.2%}")
