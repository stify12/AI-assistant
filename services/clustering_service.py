"""
错误聚类服务模块 (US-27)

使用AI对相似错误进行自动聚类分析。
"""
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from .database_service import AppDatabaseService
from .llm_service import LLMService


class ClusteringService:
    """错误聚类服务类"""
    
    @staticmethod
    def cluster_errors(
        error_type: str = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        对错误样本进行聚类 (US-27.1)
        
        使用 DeepSeek 分析错误样本的相似性，自动生成聚类标签。
        
        Args:
            error_type: 限定错误类型
            limit: 最大样本数
            
        Returns:
            dict: {clusters: list, total_samples: int}
        """
        # 获取待聚类的样本
        where_clause = "cluster_id IS NULL"
        params = []
        
        if error_type:
            where_clause += " AND error_type = %s"
            params.append(error_type)
        
        sql = f"""
            SELECT sample_id, error_type, base_answer, base_user, hw_user,
                   book_name, question_index
            FROM error_samples 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
        """
        params.append(limit)
        
        rows = AppDatabaseService.execute_query(sql, tuple(params))
        
        if not rows:
            return {'clusters': [], 'total_samples': 0}
        
        # 准备样本数据
        samples = []
        for row in rows:
            samples.append({
                'sample_id': row['sample_id'],
                'error_type': row['error_type'],
                'base_answer': row.get('base_answer', ''),
                'base_user': row.get('base_user', ''),
                'hw_user': row.get('hw_user', ''),
                'book_name': row.get('book_name', ''),
                'question_index': row.get('question_index', '')
            })
        
        # 调用AI进行聚类
        prompt = ClusteringService._generate_cluster_prompt(samples)
        
        try:
            response = LLMService.call_deepseek(prompt, model='deepseek-v3.2')
            cluster_result = ClusteringService._parse_cluster_response(response)
        except Exception as e:
            print(f'[Clustering] AI聚类失败: {e}')
            # 降级：按错误类型简单分组
            cluster_result = ClusteringService._fallback_clustering(samples)
        
        # 保存聚类结果
        clusters = []
        for cluster_data in cluster_result.get('clusters', []):
            cluster_id = str(uuid.uuid4())[:8]
            label = cluster_data.get('label', '未分类')
            description = cluster_data.get('description', '')
            sample_indices = cluster_data.get('sample_indices', [])
            
            # 获取聚类中的样本
            cluster_samples = [samples[i] for i in sample_indices if i < len(samples)]
            sample_count = len(cluster_samples)
            
            if sample_count == 0:
                continue

            # 保存聚类到数据库
            try:
                insert_sql = """
                    INSERT INTO error_clusters 
                    (cluster_id, label, description, error_type, sample_count, 
                     representative_sample_id, ai_generated)
                    VALUES (%s, %s, %s, %s, %s, %s, 1)
                """
                AppDatabaseService.execute_insert(insert_sql, (
                    cluster_id, label, description,
                    cluster_samples[0]['error_type'] if cluster_samples else None,
                    sample_count,
                    cluster_samples[0]['sample_id'] if cluster_samples else None
                ))
                
                # 更新样本的聚类ID
                sample_ids = [s['sample_id'] for s in cluster_samples]
                if sample_ids:
                    placeholders = ','.join(['%s'] * len(sample_ids))
                    update_sql = f"""
                        UPDATE error_samples 
                        SET cluster_id = %s, cluster_label = %s
                        WHERE sample_id IN ({placeholders})
                    """
                    AppDatabaseService.execute_update(
                        update_sql, 
                        tuple([cluster_id, label] + sample_ids)
                    )
                
                clusters.append({
                    'cluster_id': cluster_id,
                    'label': label,
                    'description': description,
                    'sample_count': sample_count,
                    'samples': cluster_samples[:5]  # 只返回前5个样本
                })
            except Exception as e:
                print(f'[Clustering] 保存聚类失败: {e}')
        
        return {
            'clusters': clusters,
            'total_samples': len(samples)
        }
    
    @staticmethod
    def get_clusters(error_type: str = None) -> List[Dict[str, Any]]:
        """
        获取聚类列表 (US-27.2)
        
        Returns:
            list: 聚类列表
        """
        where_clause = "1=1"
        params = []
        
        if error_type:
            where_clause += " AND error_type = %s"
            params.append(error_type)
        
        sql = f"""
            SELECT cluster_id, label, description, error_type, sample_count,
                   representative_sample_id, ai_generated, created_at
            FROM error_clusters 
            WHERE {where_clause}
            ORDER BY sample_count DESC
        """
        
        rows = AppDatabaseService.execute_query(sql, tuple(params) if params else None)
        
        clusters = []
        for row in rows:
            clusters.append({
                'cluster_id': row['cluster_id'],
                'label': row['label'],
                'description': row.get('description', ''),
                'error_type': row.get('error_type'),
                'sample_count': row['sample_count'],
                'representative_sample_id': row.get('representative_sample_id'),
                'ai_generated': bool(row.get('ai_generated')),
                'created_at': row['created_at'].isoformat() if row.get('created_at') else ''
            })
        
        return clusters
    
    @staticmethod
    def get_cluster_samples(
        cluster_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取聚类下的样本列表 (US-27.3)"""
        # 查询总数
        count_sql = "SELECT COUNT(*) as total FROM error_samples WHERE cluster_id = %s"
        count_result = AppDatabaseService.execute_one(count_sql, (cluster_id,))
        total = count_result['total'] if count_result else 0
        
        # 查询列表
        offset = (page - 1) * page_size
        list_sql = """
            SELECT sample_id, task_id, homework_id, book_name, page_num,
                   question_index, error_type, base_answer, base_user, hw_user,
                   status, created_at
            FROM error_samples 
            WHERE cluster_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        rows = AppDatabaseService.execute_query(list_sql, (cluster_id, page_size, offset))
        
        items = []
        for row in rows:
            items.append({
                'sample_id': row['sample_id'],
                'task_id': row['task_id'],
                'homework_id': row['homework_id'],
                'book_name': row.get('book_name', ''),
                'page_num': row.get('page_num'),
                'question_index': row['question_index'],
                'error_type': row['error_type'],
                'base_answer': row.get('base_answer', ''),
                'base_user': row.get('base_user', ''),
                'hw_user': row.get('hw_user', ''),
                'status': row['status'],
                'created_at': row['created_at'].isoformat() if row.get('created_at') else ''
            })
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }

    @staticmethod
    def merge_clusters(cluster_ids: List[str], new_label: str) -> str:
        """合并聚类 (US-27.4)"""
        if len(cluster_ids) < 2:
            raise ValueError('至少需要2个聚类才能合并')
        
        # 创建新聚类
        new_cluster_id = str(uuid.uuid4())[:8]
        
        # 获取所有样本数
        placeholders = ','.join(['%s'] * len(cluster_ids))
        count_sql = f"""
            SELECT COUNT(*) as total FROM error_samples 
            WHERE cluster_id IN ({placeholders})
        """
        count_result = AppDatabaseService.execute_one(count_sql, tuple(cluster_ids))
        total_samples = count_result['total'] if count_result else 0
        
        # 获取主要错误类型
        type_sql = f"""
            SELECT error_type, COUNT(*) as cnt FROM error_samples 
            WHERE cluster_id IN ({placeholders})
            GROUP BY error_type ORDER BY cnt DESC LIMIT 1
        """
        type_result = AppDatabaseService.execute_one(type_sql, tuple(cluster_ids))
        main_error_type = type_result['error_type'] if type_result else None
        
        # 插入新聚类
        insert_sql = """
            INSERT INTO error_clusters 
            (cluster_id, label, error_type, sample_count, ai_generated)
            VALUES (%s, %s, %s, %s, 0)
        """
        AppDatabaseService.execute_insert(insert_sql, (
            new_cluster_id, new_label, main_error_type, total_samples
        ))
        
        # 更新样本的聚类ID
        update_sql = f"""
            UPDATE error_samples 
            SET cluster_id = %s, cluster_label = %s
            WHERE cluster_id IN ({placeholders})
        """
        AppDatabaseService.execute_update(
            update_sql, 
            tuple([new_cluster_id, new_label] + cluster_ids)
        )
        
        # 删除旧聚类
        delete_sql = f"DELETE FROM error_clusters WHERE cluster_id IN ({placeholders})"
        AppDatabaseService.execute_update(delete_sql, tuple(cluster_ids))
        
        return new_cluster_id
    
    @staticmethod
    def update_cluster_label(cluster_id: str, label: str) -> bool:
        """更新聚类标签 (US-27.5)"""
        # 更新聚类表
        sql = "UPDATE error_clusters SET label = %s WHERE cluster_id = %s"
        result = AppDatabaseService.execute_update(sql, (label, cluster_id))
        
        # 同步更新样本表
        if result > 0:
            update_sql = "UPDATE error_samples SET cluster_label = %s WHERE cluster_id = %s"
            AppDatabaseService.execute_update(update_sql, (label, cluster_id))
        
        return result > 0
    
    @staticmethod
    def delete_cluster(cluster_id: str) -> bool:
        """删除聚类"""
        # 清除样本的聚类关联
        update_sql = """
            UPDATE error_samples 
            SET cluster_id = NULL, cluster_label = NULL
            WHERE cluster_id = %s
        """
        AppDatabaseService.execute_update(update_sql, (cluster_id,))
        
        # 删除聚类
        delete_sql = "DELETE FROM error_clusters WHERE cluster_id = %s"
        result = AppDatabaseService.execute_update(delete_sql, (cluster_id,))
        
        return result > 0
    
    @staticmethod
    def _generate_cluster_prompt(samples: List[Dict]) -> str:
        """生成聚类分析的 Prompt"""
        # 简化样本数据
        simplified = []
        for i, s in enumerate(samples[:50]):  # 最多50个样本
            simplified.append({
                'index': i,
                'error_type': s['error_type'],
                'base': s.get('base_answer', '')[:50],
                'user': s.get('base_user', '')[:50],
                'ai': s.get('hw_user', '')[:50]
            })
        
        return f"""请分析以下AI批改错误样本，将相似的错误归类，并为每个类别生成简短的标签。

错误样本（共{len(samples)}个，展示前{len(simplified)}个）：
{json.dumps(simplified, ensure_ascii=False, indent=2)}

请返回JSON格式（不要包含markdown代码块标记）：
{{
    "clusters": [
        {{
            "label": "聚类标签（简短描述）",
            "description": "聚类描述（详细说明这类错误的特征）",
            "sample_indices": [0, 1, 2]
        }}
    ]
}}

要求：
1. 每个样本只能属于一个聚类
2. 标签要简洁明了，不超过20字
3. 相似的错误模式归为一类"""
    
    @staticmethod
    def _parse_cluster_response(response: str) -> Dict[str, Any]:
        """解析AI聚类响应"""
        try:
            # 尝试提取JSON
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])
            
            return json.loads(response)
        except:
            return {'clusters': []}
    
    @staticmethod
    def _fallback_clustering(samples: List[Dict]) -> Dict[str, Any]:
        """降级聚类：按错误类型分组"""
        groups = {}
        for i, sample in enumerate(samples):
            error_type = sample['error_type']
            if error_type not in groups:
                groups[error_type] = []
            groups[error_type].append(i)
        
        clusters = []
        for error_type, indices in groups.items():
            clusters.append({
                'label': error_type,
                'description': f'错误类型为"{error_type}"的样本',
                'sample_indices': indices
            })
        
        return {'clusters': clusters}
