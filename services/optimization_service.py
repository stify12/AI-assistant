"""
优化建议服务模块 (US-28)

使用AI分析错误样本，生成针对性的优化建议。
"""
import uuid
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from .database_service import AppDatabaseService
from .llm_service import LLMService
from .storage_service import StorageService


class OptimizationService:
    """优化建议服务类"""
    
    @staticmethod
    def generate_suggestions(
        sample_ids: List[str] = None,
        error_type: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        生成优化建议 (US-28.1, US-28.2)
        
        AI分析错误样本，识别主要问题并生成优化方案。
        
        Args:
            sample_ids: 指定样本ID列表
            error_type: 限定错误类型
            limit: 最大样本数
            
        Returns:
            dict: {suggestions: list, analyzed_samples: int}
        """
        # 获取样本数据
        if sample_ids:
            placeholders = ','.join(['%s'] * len(sample_ids))
            sql = f"""
                SELECT sample_id, error_type, base_answer, base_user, hw_user,
                       book_name, question_index, subject_id
                FROM error_samples 
                WHERE sample_id IN ({placeholders})
            """
            rows = AppDatabaseService.execute_query(sql, tuple(sample_ids))
        else:
            where_clause = "1=1"
            params = []
            
            if error_type:
                where_clause += " AND error_type = %s"
                params.append(error_type)
            
            sql = f"""
                SELECT sample_id, error_type, base_answer, base_user, hw_user,
                       book_name, question_index, subject_id
                FROM error_samples 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            """
            params.append(limit)
            rows = AppDatabaseService.execute_query(sql, tuple(params))
        
        if not rows:
            return {'suggestions': [], 'analyzed_samples': 0}
        
        # 统计错误分布
        error_distribution = {}
        subject_distribution = {}
        samples = []
        
        for row in rows:
            et = row['error_type']
            error_distribution[et] = error_distribution.get(et, 0) + 1
            
            sid = row.get('subject_id')
            if sid is not None:
                subject_distribution[sid] = subject_distribution.get(sid, 0) + 1
            
            samples.append({
                'error_type': et,
                'base_answer': row.get('base_answer', ''),
                'base_user': row.get('base_user', ''),
                'hw_user': row.get('hw_user', ''),
                'book_name': row.get('book_name', ''),
                'question_index': row.get('question_index', '')
            })

        # 调用AI生成建议
        prompt = OptimizationService._generate_optimization_prompt(
            samples, error_distribution, subject_distribution
        )
        
        try:
            response = LLMService.call_deepseek(prompt, model='deepseek-v3.2')
            suggestion_result = OptimizationService._parse_suggestion_response(response)
        except Exception as e:
            print(f'[Optimization] AI生成建议失败: {e}')
            # 降级：生成基础建议
            suggestion_result = OptimizationService._fallback_suggestions(
                error_distribution, subject_distribution
            )
        
        # 保存建议到数据库
        saved_suggestions = []
        for suggestion_data in suggestion_result.get('suggestions', []):
            suggestion_id = str(uuid.uuid4())[:8]
            
            try:
                sql = """
                    INSERT INTO optimization_suggestions 
                    (suggestion_id, title, problem_description, affected_subjects,
                     affected_question_types, sample_count, suggestion_content,
                     priority, ai_model)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                AppDatabaseService.execute_insert(sql, (
                    suggestion_id,
                    suggestion_data.get('title', '优化建议'),
                    suggestion_data.get('problem_description', ''),
                    json.dumps(suggestion_data.get('affected_subjects', []), ensure_ascii=False),
                    json.dumps(suggestion_data.get('affected_question_types', []), ensure_ascii=False),
                    len(samples),
                    suggestion_data.get('suggestion_content', ''),
                    suggestion_data.get('priority', 'medium'),
                    'deepseek-v3.2'
                ))
                
                saved_suggestions.append({
                    'suggestion_id': suggestion_id,
                    **suggestion_data
                })
            except Exception as e:
                print(f'[Optimization] 保存建议失败: {e}')
        
        return {
            'suggestions': saved_suggestions,
            'analyzed_samples': len(samples)
        }
    
    @staticmethod
    def get_suggestions(
        status: str = None,
        priority: str = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取优化建议列表 (US-28.5)"""
        where_clauses = ['1=1']
        params = []
        
        if status:
            where_clauses.append('status = %s')
            params.append(status)
        
        if priority:
            where_clauses.append('priority = %s')
            params.append(priority)
        
        where_sql = ' AND '.join(where_clauses)
        
        # 查询总数
        count_sql = f'SELECT COUNT(*) as total FROM optimization_suggestions WHERE {where_sql}'
        count_result = AppDatabaseService.execute_one(count_sql, tuple(params) if params else None)
        total = count_result['total'] if count_result else 0
        
        # 查询列表
        offset = (page - 1) * page_size
        list_sql = f"""
            SELECT suggestion_id, title, problem_description, affected_subjects,
                   affected_question_types, sample_count, suggestion_content,
                   priority, status, ai_model, created_at, updated_at
            FROM optimization_suggestions 
            WHERE {where_sql}
            ORDER BY 
                CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        rows = AppDatabaseService.execute_query(list_sql, tuple(params))
        
        items = []
        for row in rows:
            items.append({
                'suggestion_id': row['suggestion_id'],
                'title': row['title'],
                'problem_description': row.get('problem_description', ''),
                'affected_subjects': json.loads(row['affected_subjects']) if row.get('affected_subjects') else [],
                'affected_question_types': json.loads(row['affected_question_types']) if row.get('affected_question_types') else [],
                'sample_count': row.get('sample_count', 0),
                'suggestion_content': row.get('suggestion_content', ''),
                'priority': row['priority'],
                'status': row['status'],
                'ai_model': row.get('ai_model'),
                'created_at': row['created_at'].isoformat() if row.get('created_at') else '',
                'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else ''
            })
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }

    @staticmethod
    def update_status(suggestion_id: str, status: str) -> bool:
        """更新建议状态 (US-28.3)"""
        valid_statuses = ['pending', 'in_progress', 'completed', 'rejected']
        if status not in valid_statuses:
            raise ValueError(f'无效状态: {status}')
        
        sql = "UPDATE optimization_suggestions SET status = %s WHERE suggestion_id = %s"
        result = AppDatabaseService.execute_update(sql, (status, suggestion_id))
        return result > 0
    
    @staticmethod
    def get_suggestion_detail(suggestion_id: str) -> Optional[Dict[str, Any]]:
        """获取建议详情"""
        sql = """
            SELECT suggestion_id, title, problem_description, affected_subjects,
                   affected_question_types, sample_count, suggestion_content,
                   priority, status, ai_model, created_at, updated_at
            FROM optimization_suggestions 
            WHERE suggestion_id = %s
        """
        row = AppDatabaseService.execute_one(sql, (suggestion_id,))
        
        if not row:
            return None
        
        return {
            'suggestion_id': row['suggestion_id'],
            'title': row['title'],
            'problem_description': row.get('problem_description', ''),
            'affected_subjects': json.loads(row['affected_subjects']) if row.get('affected_subjects') else [],
            'affected_question_types': json.loads(row['affected_question_types']) if row.get('affected_question_types') else [],
            'sample_count': row.get('sample_count', 0),
            'suggestion_content': row.get('suggestion_content', ''),
            'priority': row['priority'],
            'status': row['status'],
            'ai_model': row.get('ai_model'),
            'created_at': row['created_at'].isoformat() if row.get('created_at') else '',
            'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else ''
        }
    
    @staticmethod
    def export_suggestions(
        suggestion_ids: List[str] = None,
        format: str = 'md'
    ) -> str:
        """导出优化建议报告 (US-28.4)"""
        # 获取建议
        if suggestion_ids:
            placeholders = ','.join(['%s'] * len(suggestion_ids))
            sql = f"""
                SELECT * FROM optimization_suggestions 
                WHERE suggestion_id IN ({placeholders})
                ORDER BY priority, created_at DESC
            """
            rows = AppDatabaseService.execute_query(sql, tuple(suggestion_ids))
        else:
            sql = """
                SELECT * FROM optimization_suggestions 
                ORDER BY priority, created_at DESC
                LIMIT 50
            """
            rows = AppDatabaseService.execute_query(sql)
        
        # 生成报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'md':
            content = OptimizationService._generate_md_report(rows)
            filename = f'optimization_report_{timestamp}.md'
        else:
            content = OptimizationService._generate_txt_report(rows)
            filename = f'optimization_report_{timestamp}.txt'
        
        # 保存文件
        export_dir = StorageService.EXPORTS_DIR
        StorageService.ensure_dir(export_dir)
        filepath = os.path.join(export_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    @staticmethod
    def delete_suggestion(suggestion_id: str) -> bool:
        """删除建议"""
        sql = "DELETE FROM optimization_suggestions WHERE suggestion_id = %s"
        result = AppDatabaseService.execute_update(sql, (suggestion_id,))
        return result > 0
    
    @staticmethod
    def _generate_optimization_prompt(
        samples: List[Dict],
        error_distribution: Dict[str, int],
        subject_distribution: Dict[int, int]
    ) -> str:
        """生成优化建议的 Prompt"""
        # 学科名称映射
        subject_names = {
            0: '英语', 1: '语文', 2: '数学', 3: '物理',
            4: '化学', 5: '生物', 6: '地理'
        }
        
        subject_dist_named = {
            subject_names.get(k, f'学科{k}'): v 
            for k, v in subject_distribution.items()
        }
        
        # 取前10个样本作为示例
        sample_examples = []
        for s in samples[:10]:
            sample_examples.append({
                'error_type': s['error_type'],
                'base': s.get('base_answer', '')[:100],
                'user': s.get('base_user', '')[:100],
                'ai': s.get('hw_user', '')[:100]
            })
        
        return f"""请分析以下AI批改系统的错误样本，识别主要问题并提供优化建议。

## 错误类型分布
{json.dumps(error_distribution, ensure_ascii=False, indent=2)}

## 学科分布
{json.dumps(subject_dist_named, ensure_ascii=False, indent=2)}

## 错误样本示例（共{len(samples)}个，展示前10个）
{json.dumps(sample_examples, ensure_ascii=False, indent=2)}

请返回JSON格式（不要包含markdown代码块标记）：
{{
    "suggestions": [
        {{
            "title": "问题标题（简短）",
            "problem_description": "问题描述（详细说明问题现象和原因）",
            "affected_subjects": [0, 2],
            "affected_question_types": ["填空题", "选择题"],
            "suggestion_content": "具体优化建议（包括技术方案和实施步骤）",
            "priority": "high"
        }}
    ]
}}

要求：
1. 优先级分为 high/medium/low
2. 建议要具体可执行
3. 最多返回5条建议"""

    @staticmethod
    def _parse_suggestion_response(response: str) -> Dict[str, Any]:
        """解析AI建议响应"""
        try:
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])
            
            return json.loads(response)
        except:
            return {'suggestions': []}
    
    @staticmethod
    def _fallback_suggestions(
        error_distribution: Dict[str, int],
        subject_distribution: Dict[int, int]
    ) -> Dict[str, Any]:
        """降级建议生成"""
        suggestions = []
        
        # 按错误类型生成建议
        for error_type, count in sorted(error_distribution.items(), key=lambda x: -x[1])[:3]:
            if '识别错误' in error_type:
                suggestions.append({
                    'title': f'优化{error_type}问题',
                    'problem_description': f'系统存在{count}个{error_type}类型的错误',
                    'affected_subjects': list(subject_distribution.keys()),
                    'affected_question_types': [],
                    'suggestion_content': '建议优化OCR识别模型，增加训练数据，提高识别准确率',
                    'priority': 'high' if count > 10 else 'medium'
                })
            elif '判断错误' in error_type:
                suggestions.append({
                    'title': f'优化{error_type}问题',
                    'problem_description': f'系统存在{count}个{error_type}类型的错误',
                    'affected_subjects': list(subject_distribution.keys()),
                    'affected_question_types': [],
                    'suggestion_content': '建议优化答案判断逻辑，增加答案等价性判断规则',
                    'priority': 'high' if count > 10 else 'medium'
                })
        
        return {'suggestions': suggestions}
    
    @staticmethod
    def _generate_md_report(rows: List[Dict]) -> str:
        """生成Markdown格式报告"""
        lines = [
            '# AI批改系统优化建议报告',
            f'\n生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'\n共 {len(rows)} 条建议\n',
            '---\n'
        ]
        
        priority_labels = {'high': '高', 'medium': '中', 'low': '低'}
        status_labels = {'pending': '待处理', 'in_progress': '处理中', 'completed': '已完成', 'rejected': '已拒绝'}
        
        for i, row in enumerate(rows, 1):
            priority = priority_labels.get(row['priority'], row['priority'])
            status = status_labels.get(row['status'], row['status'])
            
            lines.append(f'## {i}. {row["title"]}')
            lines.append(f'\n**优先级**: {priority} | **状态**: {status}\n')
            
            if row.get('problem_description'):
                lines.append(f'### 问题描述\n{row["problem_description"]}\n')
            
            if row.get('suggestion_content'):
                lines.append(f'### 优化建议\n{row["suggestion_content"]}\n')
            
            lines.append('---\n')
        
        return '\n'.join(lines)
    
    @staticmethod
    def _generate_txt_report(rows: List[Dict]) -> str:
        """生成纯文本格式报告"""
        lines = [
            'AI批改系统优化建议报告',
            f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'共 {len(rows)} 条建议',
            '=' * 50
        ]
        
        for i, row in enumerate(rows, 1):
            lines.append(f'\n{i}. {row["title"]}')
            lines.append(f'   优先级: {row["priority"]} | 状态: {row["status"]}')
            
            if row.get('problem_description'):
                lines.append(f'   问题: {row["problem_description"]}')
            
            if row.get('suggestion_content'):
                lines.append(f'   建议: {row["suggestion_content"]}')
            
            lines.append('-' * 50)
        
        return '\n'.join(lines)
