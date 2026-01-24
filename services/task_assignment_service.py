"""
测试任务分配服务 (US-13)

支持:
- 任务分配给团队成员
- 查看分配状态
- 任务评论
"""
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from .database_service import AppDatabaseService


class TaskAssignmentService:
    """任务分配服务"""
    
    @staticmethod
    def assign_task(
        plan_id: str,
        task_id: str,
        assignee_id: str,
        assignee_name: str,
        assigned_by: str = 'system'
    ) -> Dict[str, Any]:
        """
        分配任务 (US-13.1)
        """
        try:
            # 检查是否已分配
            existing = AppDatabaseService.execute_one(
                "SELECT id FROM test_plan_assignments WHERE plan_id=%s AND task_id=%s",
                (plan_id, task_id)
            )
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if existing:
                # 更新分配
                AppDatabaseService.execute_update(
                    """UPDATE test_plan_assignments 
                       SET assignee_id=%s, assignee_name=%s, assigned_by=%s, assigned_at=%s
                       WHERE plan_id=%s AND task_id=%s""",
                    (assignee_id, assignee_name, assigned_by, now, plan_id, task_id)
                )
            else:
                # 新建分配
                AppDatabaseService.execute_insert(
                    """INSERT INTO test_plan_assignments 
                       (plan_id, task_id, assignee_id, assignee_name, assigned_by, assigned_at, status)
                       VALUES (%s, %s, %s, %s, %s, %s, 'pending')""",
                    (plan_id, task_id, assignee_id, assignee_name, assigned_by, now)
                )
            
            return {
                'success': True,
                'plan_id': plan_id,
                'task_id': task_id,
                'assignee_id': assignee_id,
                'assignee_name': assignee_name
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def batch_assign(
        plan_id: str,
        assignments: List[Dict],
        assigned_by: str = 'system'
    ) -> Dict[str, Any]:
        """
        批量分配任务 (US-13.2)
        
        Args:
            assignments: [{task_id, assignee_id, assignee_name}, ...]
        """
        success_count = 0
        errors = []
        
        for item in assignments:
            result = TaskAssignmentService.assign_task(
                plan_id,
                item.get('task_id'),
                item.get('assignee_id'),
                item.get('assignee_name', ''),
                assigned_by
            )
            if result.get('success'):
                success_count += 1
            else:
                errors.append({'task_id': item.get('task_id'), 'error': result.get('error')})
        
        return {
            'success': len(errors) == 0,
            'total': len(assignments),
            'success_count': success_count,
            'errors': errors
        }
    
    @staticmethod
    def get_assignments(
        plan_id: str = None,
        assignee_id: str = None,
        status: str = None
    ) -> List[Dict]:
        """
        获取任务分配列表 (US-13.3)
        """
        try:
            sql = "SELECT * FROM test_plan_assignments WHERE 1=1"
            params = []
            
            if plan_id:
                sql += " AND plan_id=%s"
                params.append(plan_id)
            if assignee_id:
                sql += " AND assignee_id=%s"
                params.append(assignee_id)
            if status:
                sql += " AND status=%s"
                params.append(status)
            
            sql += " ORDER BY assigned_at DESC"
            
            rows = AppDatabaseService.execute_query(sql, tuple(params) if params else None)
            return rows or []
        except Exception:
            return []
    
    @staticmethod
    def update_status(
        plan_id: str,
        task_id: str,
        status: str,
        comment: str = None
    ) -> Dict[str, Any]:
        """
        更新任务状态 (US-13.4)
        
        status: pending | in_progress | completed | blocked
        """
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if status == 'completed':
                AppDatabaseService.execute_update(
                    """UPDATE test_plan_assignments 
                       SET status=%s, completed_at=%s
                       WHERE plan_id=%s AND task_id=%s""",
                    (status, now, plan_id, task_id)
                )
            else:
                AppDatabaseService.execute_update(
                    """UPDATE test_plan_assignments 
                       SET status=%s
                       WHERE plan_id=%s AND task_id=%s""",
                    (status, plan_id, task_id)
                )
            
            # 添加评论
            if comment:
                TaskAssignmentService.add_comment(plan_id, task_id, 'system', comment)
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def add_comment(
        plan_id: str,
        task_id: str,
        user_id: str,
        content: str
    ) -> Dict[str, Any]:
        """
        添加任务评论
        """
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            AppDatabaseService.execute_insert(
                """INSERT INTO test_plan_comments 
                   (plan_id, task_id, user_id, content, created_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (plan_id, task_id, user_id, content, now)
            )
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_comments(plan_id: str, task_id: str) -> List[Dict]:
        """获取任务评论"""
        try:
            rows = AppDatabaseService.execute_query(
                """SELECT * FROM test_plan_comments 
                   WHERE plan_id=%s AND task_id=%s
                   ORDER BY created_at DESC""",
                (plan_id, task_id)
            )
            return rows or []
        except Exception:
            return []
    
    @staticmethod
    def get_workload_summary(plan_id: str = None) -> Dict[str, Any]:
        """
        获取工作量统计 (US-13.5)
        """
        try:
            sql = """
                SELECT 
                    assignee_id,
                    assignee_name,
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status='in_progress' THEN 1 ELSE 0 END) as in_progress,
                    SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status='blocked' THEN 1 ELSE 0 END) as blocked
                FROM test_plan_assignments
            """
            params = []
            
            if plan_id:
                sql += " WHERE plan_id=%s"
                params.append(plan_id)
            
            sql += " GROUP BY assignee_id, assignee_name"
            
            rows = AppDatabaseService.execute_query(sql, tuple(params) if params else None)
            
            return {
                'members': rows or [],
                'total_assigned': sum(r.get('total_tasks', 0) for r in (rows or []))
            }
        except Exception as e:
            return {'members': [], 'total_assigned': 0, 'error': str(e)}
