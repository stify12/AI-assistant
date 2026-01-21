#!/usr/bin/env python
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

t1 = '原句①介绍造型，③介绍结构，②介绍工艺'
t2 = '原句①介绍造型，②介绍结构，③介绍工艺'

words1 = ' '.join(jieba.cut(t1))
words2 = ' '.join(jieba.cut(t2))
print('分词1:', words1)
print('分词2:', words2)

vectorizer = TfidfVectorizer()
tfidf = vectorizer.fit_transform([words1, words2])
sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
print(f'TF-IDF相似度: {sim:.2%}')
