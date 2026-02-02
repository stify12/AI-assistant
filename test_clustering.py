"""测试聚类服务"""
from services.clustering_service import ClusteringService
import json

# 测试聚类服务
result = ClusteringService.cluster_task_errors('fd34d559')
print('聚类结果:')
print(f'  success: {result.get("success")}')
print(f'  total_errors: {result.get("total_errors")}')
print(f'  clusters: {len(result.get("clusters", []))} 个')

if result.get('clusters'):
    print('\n前3个聚类:')
    for i, c in enumerate(result['clusters'][:3]):
        print(f'  [{i+1}] {c.get("label", "")}')
        print(f'      样本数: {c.get("sample_count")}')
        print(f'      描述: {c.get("description", "")[:50]}...')
        print(f'      根因: {c.get("root_cause", "")[:50]}...')
