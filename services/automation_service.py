"""
自动化任务管理服务

提供自动化任务的管理功能，包括：
- 任务列表查询
- 任务配置管理
- 执行历史查询
- 队列状态监控
- 全局控制（暂停/恢复）
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .database_service import AppDatabaseService
from .ai_analysis_service import AIAnalysisService


class AutomationService:
    """自动化任务管理服务"""
    
    CONFIG_PATH = 'automation_config.json'
    
    # 任务类型定义
    TASK_TYPES = {
        'ai_analysis': {
            'name': 'AI 数据分析',
            'description': '批量评估完成后自动分析错误模式和根因',
            'trigger_type': 'event'
        },
        'daily_report': {
            'name': '日报自动生成',
            'description': '每天定时自动生成测试日报',
            'trigger_type': 'cron'
        },
        'stats_snapshot': {
            'name': '统计快照',
            'description': '每天定时保存统计数据快照',
            'trigger_type': 'cron'
        }
    }
    
    @classmethod
    def _load_config(cls) -> dict:
        """加载配置"""
        try:
            if os.path.exists(cls.CONFIG_PATH):
                with open(cls.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[Automation] 加载配置失败: {e}")
        return {}
    
    @classmethod
    def _save_config(cls, config: dict):
        """保存配置"""
        try:
            with open(cls.CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[Automation] 保存配置失败: {e}")
    
    @classmethod
    def get_all_tasks(cls) -> List[dict]:
        """获取所有自动化任务列表"""
        config = cls._load_config()
        global_config = config.get('global', {})
        is_paused = global_config.get('paused', False)
        
        tasks = []
        
        for task_type, task_info in cls.TASK_TYPES.items():
            task_config = config.get(task_type, {})
            enabled = task_config.get('enabled', True)
            
            # 获取执行统计
            stats = cls._get_task_stats(task_type)
            
            # 获取最近执行记录
            last_run_info = cls._get_last_run(task_type)
            
            # 计算下次执行时间
            next_run = None
            if task_info['trigger_type'] == 'cron' and enabled and not is_paused:
                cron = task_config.get('cron', '')
                next_run = cls._calculate_next_run(cron)
            
            # 确定状态
            if is_paused:
                status = 'paused'
            elif not enabled:
                status = 'disabled'
            elif AIAnalysisService.get_queue_status().get('running') and task_type == 'ai_analysis':
                status = 'running'
            else:
                status = 'enabled'
            
            tasks.append({
                'task_type': task_type,
                'name': task_info['name'],
                'description': task_info['description'],
                'trigger_type': task_info['trigger_type'],
                'status': status,
                'last_run': last_run_info.get('created_at') if last_run_info else None,
                'last_result': last_run_info.get('status') if last_run_info else None,
                'next_run': next_run,
                'stats': stats
            })
        
        return tasks
    
    @classmethod
    def _get_task_stats(cls, task_type: str) -> dict:
        """获取任务执行统计"""
        try:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=now.weekday())
            month_start = today_start.replace(day=1)
            
            sql = """
                SELECT 
                    COUNT(CASE WHEN created_at >= %s THEN 1 END) as today,
                    COUNT(CASE WHEN created_at >= %s THEN 1 END) as week,
                    COUNT(CASE WHEN created_at >= %s THEN 1 END) as month
                FROM automation_logs
                WHERE task_type = %s AND status = 'completed'
            """
            result = AppDatabaseService.execute_query(sql, (
                today_start, week_start, month_start, task_type
            ))
            
            if result:
                return {
                    'today': result[0]['today'] or 0,
                    'week': result[0]['week'] or 0,
                    'month': result[0]['month'] or 0
                }
        except Exception as e:
            print(f"[Automation] 获取统计失败: {e}")
        
        return {'today': 0, 'week': 0, 'month': 0}
    
    @classmethod
    def _get_last_run(cls, task_type: str) -> Optional[dict]:
        """获取最近执行记录"""
        try:
            sql = """
                SELECT log_id, status, message, duration_seconds, created_at
                FROM automation_logs
                WHERE task_type = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            result = AppDatabaseService.execute_query(sql, (task_type,))
            if result:
                row = result[0]
                return {
                    'log_id': row['log_id'],
                    'status': row['status'],
                    'message': row['message'],
                    'duration_seconds': row['duration_seconds'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                }
        except Exception as e:
            print(f"[Automation] 获取最近执行记录失败: {e}")
        return None
    
    @classmethod
    def _calculate_next_run(cls, cron: str) -> Optional[str]:
        """计算下次执行时间（简化实现）"""
        if not cron:
            return None
        
        try:
            # 简单解析 cron: "0 18 * * *" -> 每天 18:00
            parts = cron.split()
            if len(parts) >= 2:
                minute = int(parts[0])
                hour = int(parts[1])
                
                now = datetime.now()
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                return next_run.isoformat()
        except:
            pass
        return None
    
    @classmethod
    def get_task_config(cls, task_type: str) -> dict:
        """获取任务配置"""
        config = cls._load_config()
        return config.get(task_type, {})
    
    @classmethod
    def update_task_config(cls, task_type: str, updates: dict) -> dict:
        """更新任务配置"""
        config = cls._load_config()
        
        if task_type not in config:
            config[task_type] = {}
        
        config[task_type].update(updates)
        cls._save_config(config)
        
        # 如果是 AI 分析配置，同步更新服务
        if task_type == 'ai_analysis':
            AIAnalysisService.update_config(updates)
        
        return config[task_type]
    
    @classmethod
    def get_task_history(cls, task_type: str, limit: int = 50) -> List[dict]:
        """获取任务执行历史"""
        try:
            sql = """
                SELECT log_id, related_id, status, message, duration_seconds, created_at
                FROM automation_logs
                WHERE task_type = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            result = AppDatabaseService.execute_query(sql, (task_type, limit))
            
            history = []
            for row in result:
                history.append({
                    'log_id': row['log_id'],
                    'related_id': row['related_id'],
                    'status': row['status'],
                    'message': row['message'],
                    'duration_seconds': row['duration_seconds'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                })
            return history
        except Exception as e:
            print(f"[Automation] 获取执行历史失败: {e}")
        return []
    
    @classmethod
    def get_queue_status(cls) -> dict:
        """获取队列状态"""
        # 获取 AI 分析队列状态
        ai_queue = AIAnalysisService.get_queue_status()
        
        # 获取最近完成的任务
        recent = []
        try:
            sql = """
                SELECT task_type, related_id, status, duration_seconds, created_at
                FROM automation_logs
                WHERE status IN ('completed', 'failed')
                ORDER BY created_at DESC
                LIMIT 10
            """
            result = AppDatabaseService.execute_query(sql)
            for row in result:
                recent.append({
                    'task_type': row['task_type'],
                    'task_id': row['related_id'],
                    'result': row['status'],
                    'duration': row['duration_seconds'],
                    'completed_at': row['created_at'].isoformat() if row['created_at'] else None
                })
        except Exception as e:
            print(f"[Automation] 获取最近完成任务失败: {e}")
        
        return {
            'waiting': ai_queue.get('waiting', 0),
            'running': ai_queue.get('running', []),
            'recent': recent,
            'paused': ai_queue.get('paused', False)
        }
    
    @classmethod
    def pause_all(cls) -> bool:
        """暂停所有自动任务"""
        config = cls._load_config()
        if 'global' not in config:
            config['global'] = {}
        config['global']['paused'] = True
        cls._save_config(config)
        
        # 暂停 AI 分析
        AIAnalysisService.pause()
        
        return True
    
    @classmethod
    def resume_all(cls) -> bool:
        """恢复所有自动任务"""
        config = cls._load_config()
        if 'global' not in config:
            config['global'] = {}
        config['global']['paused'] = False
        cls._save_config(config)
        
        # 恢复 AI 分析
        AIAnalysisService.resume()
        
        return True
    
    @classmethod
    def clear_queue(cls) -> int:
        """清空等待队列"""
        return AIAnalysisService.clear_queue()
    
    @classmethod
    def is_paused(cls) -> bool:
        """检查是否暂停"""
        config = cls._load_config()
        return config.get('global', {}).get('paused', False)
    
    @classmethod
    def export_config(cls) -> dict:
        """导出配置"""
        return cls._load_config()
    
    @classmethod
    def import_config(cls, config: dict) -> bool:
        """导入配置"""
        try:
            cls._save_config(config)
            return True
        except:
            return False
