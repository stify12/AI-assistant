"""
统一调度服务模块 (重构版)

合并原 ScheduleService 和 AutomationService，提供：
- APScheduler 定时调度
- 测试计划自动执行
- 日报/统计快照自动生成
- 执行日志记录
- 失败重试机制

创建时间: 2026-01-26
"""
import uuid
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

# APScheduler 导入
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.jobstores.base import JobLookupError
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    print("[UnifiedScheduleService] APScheduler 未安装，调度功能将不可用")

from .database_service import AppDatabaseService


# 学科映射
SUBJECT_MAP = {
    0: '英语', 1: '语文', 2: '数学', 3: '物理',
    4: '化学', 5: '生物', 6: '地理'
}


class UnifiedScheduleService:
    """
    统一调度服务类
    
    整合测试计划调度、日报生成、统计快照等所有自动化任务。
    使用 APScheduler 实现真正的定时触发。
    
    Attributes:
        scheduler: APScheduler BackgroundScheduler 实例
        _initialized: 调度器是否已初始化
        _paused: 是否全局暂停
    """
    
    # 调度器实例
    scheduler = None
    _initialized = False
    _paused = False
    
    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 60
    
    # 任务类型定义
    TASK_TYPES = {
        'test_plan': {
            'name': '测试计划执行',
            'description': '定时执行测试计划的批量评估',
            'trigger_type': 'cron'
        },
        'daily_report': {
            'name': '日报自动生成',
            'description': '每天18:00自动生成测试日报',
            'trigger_type': 'cron',
            'default_cron': '0 18 * * *'
        },
        'stats_snapshot': {
            'name': '统计快照',
            'description': '每天00:00保存统计数据快照',
            'trigger_type': 'cron',
            'default_cron': '0 0 * * *'
        },
        'ai_analysis': {
            'name': 'AI数据分析',
            'description': '批量评估完成后自动分析错误模式',
            'trigger_type': 'event'
        }
    }
    
    # ========== 初始化方法 ==========
    
    @classmethod
    def init_scheduler(cls) -> bool:
        """
        初始化调度器
        
        创建并启动 APScheduler BackgroundScheduler。
        如果调度器已经初始化，则跳过。
        
        Returns:
            bool: 初始化是否成功
        """
        if not APSCHEDULER_AVAILABLE:
            print("[UnifiedSchedule] APScheduler 未安装，无法初始化调度器")
            return False
        
        if cls._initialized and cls.scheduler:
            print("[UnifiedSchedule] 调度器已初始化，跳过")
            return True
        
        try:
            cls.scheduler = BackgroundScheduler(
                timezone='Asia/Shanghai',
                job_defaults={
                    'coalesce': True,
                    'max_instances': 1,
                    'misfire_grace_time': 60 * 60
                }
            )
            
            cls.scheduler.start()
            cls._initialized = True
            
            # 恢复已有的调度任务
            cls._restore_all_scheduled_jobs()
            
            print("[UnifiedSchedule] 调度器初始化成功")
            return True
            
        except Exception as e:
            print(f"[UnifiedSchedule] 调度器初始化失败: {e}")
            return False

    @classmethod
    def _restore_all_scheduled_jobs(cls) -> None:
        """恢复所有调度任务"""
        try:
            # 1. 恢复测试计划调度
            cls._restore_test_plan_jobs()
            
            # 2. 添加日报自动生成调度
            cls._add_system_job('daily_report', '0 18 * * *', cls._execute_daily_report)
            
            # 3. 添加统计快照调度
            cls._add_system_job('stats_snapshot', '0 0 * * *', cls._execute_stats_snapshot)
            
        except Exception as e:
            print(f"[UnifiedSchedule] 恢复调度任务失败: {e}")
    
    @classmethod
    def _restore_test_plan_jobs(cls) -> None:
        """恢复测试计划调度任务"""
        try:
            sql = """
                SELECT plan_id, name, schedule_config 
                FROM test_plans 
                WHERE schedule_config IS NOT NULL 
                AND JSON_EXTRACT(schedule_config, '$.enabled') = true
                AND status IN ('draft', 'active')
            """
            results = AppDatabaseService.execute_query(sql)
            
            if not results:
                return
            
            restored_count = 0
            for row in results:
                plan_id = row.get('plan_id')
                schedule_config = row.get('schedule_config')
                
                if not plan_id or not schedule_config:
                    continue
                
                if isinstance(schedule_config, str):
                    try:
                        schedule_config = json.loads(schedule_config)
                    except:
                        continue
                
                try:
                    cls._add_plan_job(plan_id, schedule_config)
                    restored_count += 1
                except Exception as e:
                    print(f"[UnifiedSchedule] 恢复计划 {plan_id} 调度失败: {e}")
            
            if restored_count > 0:
                print(f"[UnifiedSchedule] 已恢复 {restored_count} 个测试计划调度任务")
                
        except Exception as e:
            print(f"[UnifiedSchedule] 恢复测试计划调度失败: {e}")
    
    @classmethod
    def _add_system_job(cls, job_id: str, cron_expr: str, func) -> None:
        """添加系统级调度任务"""
        if not cls.scheduler:
            return
        
        try:
            existing = cls.scheduler.get_job(job_id)
            if existing:
                return
            
            # 解析 cron 表达式
            parts = cron_expr.split()
            if len(parts) >= 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2] if parts[2] != '*' else None,
                    month=parts[3] if parts[3] != '*' else None,
                    day_of_week=parts[4] if parts[4] != '*' else None
                )
                
                cls.scheduler.add_job(
                    func=func,
                    trigger=trigger,
                    id=job_id,
                    name=cls.TASK_TYPES.get(job_id, {}).get('name', job_id),
                    replace_existing=True
                )
                print(f"[UnifiedSchedule] 已添加系统任务: {job_id}")
        except Exception as e:
            print(f"[UnifiedSchedule] 添加系统任务 {job_id} 失败: {e}")

    @classmethod
    def _add_plan_job(cls, plan_id: str, config: Dict[str, Any]) -> None:
        """添加测试计划调度任务"""
        if not cls.scheduler:
            return
        
        cls._remove_plan_job(plan_id)
        
        schedule_type = config.get('type', 'daily')
        time_str = config.get('time', '09:00')
        hour, minute = map(int, time_str.split(':'))
        
        if schedule_type == 'daily':
            trigger = CronTrigger(hour=hour, minute=minute)
        elif schedule_type == 'weekly':
            day_of_week = config.get('day_of_week', 0)
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
        elif schedule_type == 'cron':
            cron_expr = config.get('cron', f'{minute} {hour} * * *')
            trigger = CronTrigger.from_crontab(cron_expr)
        else:
            return
        
        job_id = f'plan_{plan_id}'
        cls.scheduler.add_job(
            func=cls.execute_test_plan,
            trigger=trigger,
            args=[plan_id],
            id=job_id,
            name=f'测试计划: {plan_id}',
            replace_existing=True
        )
        print(f"[UnifiedSchedule] 已添加计划调度: {job_id}")
    
    @classmethod
    def _remove_plan_job(cls, plan_id: str) -> None:
        """移除测试计划调度任务"""
        if not cls.scheduler:
            return
        job_id = f'plan_{plan_id}'
        try:
            cls.scheduler.remove_job(job_id)
        except JobLookupError:
            pass
    
    # ========== 日志记录方法 ==========
    
    @classmethod
    def log_execution(
        cls,
        task_type: str,
        related_id: Optional[str],
        status: str,
        message: str = '',
        details: Dict[str, Any] = None,
        duration_seconds: int = None,
        retry_count: int = 0
    ) -> str:
        """
        记录执行日志到 automation_logs 表
        
        Returns:
            str: 日志ID
        """
        log_id = str(uuid.uuid4())[:8]
        try:
            sql = """
                INSERT INTO automation_logs 
                (log_id, task_type, related_id, status, message, details, 
                 duration_seconds, retry_count, created_at, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            now = datetime.now()
            completed_at = now if status in ('completed', 'failed', 'skipped') else None
            
            AppDatabaseService.execute_insert(sql, (
                log_id, task_type, related_id, status, message,
                json.dumps(details or {}, ensure_ascii=False, default=str),
                duration_seconds, retry_count, now, completed_at
            ))
        except Exception as e:
            print(f"[UnifiedSchedule] 记录日志失败: {e}")
        
        return log_id

    # ========== 核心执行方法 ==========
    
    @classmethod
    def execute_test_plan(cls, plan_id: str, retry_count: int = 0) -> Dict[str, Any]:
        """
        执行测试计划 - 真正调用 create_batch_task_from_plan
        
        这是定时任务触发时调用的核心方法，会：
        1. 创建批量评估任务
        2. 执行评估
        3. 记录日志
        4. 失败时自动重试
        
        Args:
            plan_id: 测试计划ID
            retry_count: 当前重试次数
            
        Returns:
            dict: 执行结果
        """
        print(f"[UnifiedSchedule] 开始执行测试计划: plan_id={plan_id}, retry={retry_count}")
        
        start_time = time.time()
        result = {
            'plan_id': plan_id,
            'task_id': None,
            'status': 'pending',
            'message': '',
            'executed_at': datetime.now().isoformat(),
            'retry_count': retry_count
        }
        
        # 检查是否暂停
        if cls._paused:
            result['status'] = 'skipped'
            result['message'] = '调度已暂停'
            cls.log_execution('test_plan', plan_id, 'skipped', result['message'])
            return result
        
        try:
            # 1. 获取计划信息
            sql = "SELECT * FROM test_plans WHERE plan_id = %s"
            plan_results = AppDatabaseService.execute_query(sql, (plan_id,))
            
            if not plan_results:
                result['status'] = 'failed'
                result['message'] = '测试计划不存在'
                cls.log_execution('test_plan', plan_id, 'failed', result['message'])
                return result
            
            plan = plan_results[0]
            plan_name = plan.get('name', '')
            
            # 2. 检查计划状态
            if plan.get('status') not in ['draft', 'active']:
                result['status'] = 'skipped'
                result['message'] = f'计划状态为 {plan.get("status")}，跳过执行'
                cls.log_execution('test_plan', plan_id, 'skipped', result['message'])
                return result
            
            # 3. 调用 create_batch_task_from_plan 创建并执行批量评估
            from services.test_plan_service import create_batch_task_from_plan
            
            task_result = create_batch_task_from_plan(plan_id)
            
            if not task_result.get('success'):
                error_msg = task_result.get('error', '创建批量任务失败')
                result['status'] = 'failed'
                result['message'] = error_msg
                
                # 检查是否需要重试
                if retry_count < cls.MAX_RETRIES and cls._should_retry(error_msg):
                    print(f"[UnifiedSchedule] 任务失败，{cls.RETRY_DELAY_SECONDS}秒后重试 ({retry_count + 1}/{cls.MAX_RETRIES})")
                    cls.log_execution('test_plan', plan_id, 'failed', 
                                     f'{error_msg}，准备重试', retry_count=retry_count)
                    
                    # 延迟重试
                    time.sleep(cls.RETRY_DELAY_SECONDS)
                    return cls.execute_test_plan(plan_id, retry_count + 1)
                
                duration = int(time.time() - start_time)
                cls.log_execution('test_plan', plan_id, 'failed', error_msg,
                                 details=task_result, duration_seconds=duration,
                                 retry_count=retry_count)
                return result
            
            # 4. 任务创建成功
            task_id = task_result.get('task_id')
            result['task_id'] = task_id
            result['status'] = 'completed'
            result['message'] = f'已创建批量评估任务 {task_id}，包含 {task_result.get("homework_count", 0)} 个作业'
            result['homework_count'] = task_result.get('homework_count', 0)
            result['matched_count'] = task_result.get('matched_count', 0)
            
            duration = int(time.time() - start_time)
            
            # 5. 记录成功日志
            cls.log_execution('test_plan', plan_id, 'completed', result['message'],
                             details={'task_id': task_id, 'plan_name': plan_name,
                                     'homework_count': result['homework_count']},
                             duration_seconds=duration, retry_count=retry_count)
            
            # 6. 更新计划状态
            cls._update_plan_after_execution(plan_id, task_id)
            
            print(f"[UnifiedSchedule] 测试计划执行成功: plan_id={plan_id}, task_id={task_id}")
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"[UnifiedSchedule] 执行测试计划异常: {e}")
            import traceback
            traceback.print_exc()
            
            result['status'] = 'failed'
            result['message'] = error_msg
            
            # 异常情况下的重试
            if retry_count < cls.MAX_RETRIES:
                print(f"[UnifiedSchedule] 异常后重试 ({retry_count + 1}/{cls.MAX_RETRIES})")
                time.sleep(cls.RETRY_DELAY_SECONDS)
                return cls.execute_test_plan(plan_id, retry_count + 1)
            
            duration = int(time.time() - start_time)
            cls.log_execution('test_plan', plan_id, 'failed', error_msg,
                             duration_seconds=duration, retry_count=retry_count)
            return result

    @classmethod
    def _should_retry(cls, error_msg: str) -> bool:
        """判断是否应该重试"""
        # 这些错误不需要重试
        no_retry_errors = [
            '测试计划不存在',
            '尚未匹配作业发布',
            '没有关联数据集',
            '计划状态为'
        ]
        for err in no_retry_errors:
            if err in error_msg:
                return False
        return True
    
    @classmethod
    def _update_plan_after_execution(cls, plan_id: str, task_id: str) -> None:
        """执行成功后更新计划状态"""
        try:
            # 更新计划状态为 active
            sql = """
                UPDATE test_plans 
                SET status = 'active', 
                    completed_count = completed_count + 1,
                    updated_at = %s
                WHERE plan_id = %s AND status = 'draft'
            """
            AppDatabaseService.execute_update(sql, (datetime.now(), plan_id))
            
            # 更新工作流状态
            from services.test_plan_service import update_workflow_status
            update_workflow_status(plan_id, 'evaluation', {
                'status': 'in_progress',
                'task_id': task_id,
                'started_at': datetime.now().isoformat()
            })
        except Exception as e:
            print(f"[UnifiedSchedule] 更新计划状态失败: {e}")
    
    # ========== 系统任务执行方法 ==========
    
    @classmethod
    def _execute_daily_report(cls) -> None:
        """执行日报自动生成"""
        print(f"[UnifiedSchedule] 开始自动生成日报: {datetime.now()}")
        start_time = time.time()
        
        try:
            from services.report_service import ReportService
            
            today = datetime.now().strftime('%Y-%m-%d')
            report = ReportService.generate_daily_report(date=today, generated_by='auto')
            
            duration = int(time.time() - start_time)
            cls.log_execution('daily_report', report.get('report_id'), 'completed',
                             f'日报生成成功: {today}', duration_seconds=duration)
            
            # 清理过期日报
            ReportService.delete_old_reports(days=30)
            
            print(f"[UnifiedSchedule] 日报生成成功: {report.get('report_id')}")
            
        except Exception as e:
            duration = int(time.time() - start_time)
            cls.log_execution('daily_report', None, 'failed', str(e), duration_seconds=duration)
            print(f"[UnifiedSchedule] 日报生成失败: {e}")
    
    @classmethod
    def _execute_stats_snapshot(cls) -> None:
        """执行统计快照"""
        print(f"[UnifiedSchedule] 开始生成统计快照: {datetime.now()}")
        start_time = time.time()
        
        try:
            from services.dashboard_service import DashboardService
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            DashboardService.generate_daily_statistics_snapshot(yesterday)
            
            duration = int(time.time() - start_time)
            cls.log_execution('stats_snapshot', yesterday, 'completed',
                             f'统计快照生成成功: {yesterday}', duration_seconds=duration)
            
            print(f"[UnifiedSchedule] 统计快照生成成功: {yesterday}")
            
        except Exception as e:
            duration = int(time.time() - start_time)
            cls.log_execution('stats_snapshot', None, 'failed', str(e), duration_seconds=duration)
            print(f"[UnifiedSchedule] 统计快照生成失败: {e}")

    # ========== 计划调度配置方法 ==========
    
    @classmethod
    def set_plan_schedule(cls, plan_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置测试计划调度配置
        
        Args:
            plan_id: 测试计划ID
            config: 调度配置 {type, time, day_of_week, cron, enabled}
            
        Returns:
            dict: {next_run, enabled}
        """
        if not plan_id:
            raise ValueError('计划ID不能为空')
        if not config:
            raise ValueError('调度配置不能为空')
        
        schedule_type = config.get('type', 'daily')
        if schedule_type not in ['daily', 'weekly', 'cron']:
            raise ValueError(f'无效的调度类型: {schedule_type}')
        
        # 验证时间格式
        time_str = config.get('time', '09:00')
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except:
            raise ValueError(f'无效的时间格式: {time_str}')
        
        enabled = config.get('enabled', True)
        
        try:
            # 更新数据库
            sql = """
                UPDATE test_plans 
                SET schedule_config = %s, updated_at = %s
                WHERE plan_id = %s
            """
            AppDatabaseService.execute_update(sql, (
                json.dumps(config), datetime.now(), plan_id
            ))
            
            # 更新调度器
            if enabled:
                cls._add_plan_job(plan_id, config)
            else:
                cls._remove_plan_job(plan_id)
            
            next_run = cls.get_next_run_time(plan_id)
            
            cls.log_execution('test_plan', plan_id, 'completed',
                             f'调度配置已更新: {schedule_type} {time_str}',
                             details={'config': config, 'next_run': next_run})
            
            return {'next_run': next_run, 'enabled': enabled}
            
        except Exception as e:
            raise ValueError(f'设置调度失败: {str(e)}')
    
    @classmethod
    def disable_schedule(cls, plan_id: str) -> bool:
        """禁用计划调度"""
        try:
            sql = """
                UPDATE test_plans 
                SET schedule_config = JSON_SET(COALESCE(schedule_config, '{}'), '$.enabled', false),
                    updated_at = %s
                WHERE plan_id = %s
            """
            AppDatabaseService.execute_update(sql, (datetime.now(), plan_id))
            cls._remove_plan_job(plan_id)
            cls.log_execution('test_plan', plan_id, 'completed', '调度已禁用')
            return True
        except Exception as e:
            print(f"[UnifiedSchedule] 禁用调度失败: {e}")
            return False
    
    @classmethod
    def get_next_run_time(cls, plan_id: str) -> Optional[str]:
        """获取下次执行时间"""
        if cls.scheduler:
            job_id = f'plan_{plan_id}'
            try:
                job = cls.scheduler.get_job(job_id)
                if job and job.next_run_time:
                    return job.next_run_time.isoformat()
            except:
                pass
        
        # 从配置计算
        return cls._calculate_next_run(plan_id)
    
    @classmethod
    def _calculate_next_run(cls, plan_id: str) -> Optional[str]:
        """从配置计算下次执行时间"""
        try:
            sql = "SELECT schedule_config FROM test_plans WHERE plan_id = %s"
            results = AppDatabaseService.execute_query(sql, (plan_id,))
            
            if not results or not results[0].get('schedule_config'):
                return None
            
            config = results[0]['schedule_config']
            if isinstance(config, str):
                config = json.loads(config)
            
            if not config.get('enabled', False):
                return None
            
            time_str = config.get('time', '09:00')
            hour, minute = map(int, time_str.split(':'))
            now = datetime.now()
            
            schedule_type = config.get('type', 'daily')
            
            if schedule_type == 'daily':
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run.isoformat()
            
            elif schedule_type == 'weekly':
                day_of_week = config.get('day_of_week', 0)
                days_ahead = day_of_week - now.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                elif days_ahead == 0:
                    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if target <= now:
                        days_ahead = 7
                next_run = now + timedelta(days=days_ahead)
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return next_run.isoformat()
            
            return None
        except:
            return None

    # ========== 任务管理方法 (原 AutomationService) ==========
    
    @classmethod
    def get_all_tasks(cls) -> List[Dict[str, Any]]:
        """获取所有自动化任务列表"""
        tasks = []
        
        for task_type, task_info in cls.TASK_TYPES.items():
            stats = cls._get_task_stats(task_type)
            last_run = cls._get_last_run(task_type)
            
            # 计算下次执行时间
            next_run = None
            if task_info['trigger_type'] == 'cron' and not cls._paused:
                if task_type == 'daily_report':
                    next_run = cls._get_system_job_next_run('daily_report')
                elif task_type == 'stats_snapshot':
                    next_run = cls._get_system_job_next_run('stats_snapshot')
            
            # 确定状态
            if cls._paused:
                status = 'paused'
            else:
                status = 'enabled'
            
            tasks.append({
                'task_type': task_type,
                'name': task_info['name'],
                'description': task_info['description'],
                'trigger_type': task_info['trigger_type'],
                'status': status,
                'last_run': last_run.get('created_at') if last_run else None,
                'last_result': last_run.get('status') if last_run else None,
                'next_run': next_run,
                'stats': stats
            })
        
        return tasks
    
    @classmethod
    def _get_system_job_next_run(cls, job_id: str) -> Optional[str]:
        """获取系统任务下次执行时间"""
        if not cls.scheduler:
            return None
        try:
            job = cls.scheduler.get_job(job_id)
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except:
            pass
        return None
    
    @classmethod
    def _get_task_stats(cls, task_type: str) -> Dict[str, int]:
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
            print(f"[UnifiedSchedule] 获取统计失败: {e}")
        
        return {'today': 0, 'week': 0, 'month': 0}
    
    @classmethod
    def _get_last_run(cls, task_type: str) -> Optional[Dict[str, Any]]:
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
        except:
            pass
        return None
    
    @classmethod
    def get_task_history(cls, task_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取任务执行历史"""
        try:
            sql = """
                SELECT log_id, related_id, status, message, duration_seconds, 
                       retry_count, created_at, completed_at
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
                    'retry_count': row['retry_count'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None
                })
            return history
        except Exception as e:
            print(f"[UnifiedSchedule] 获取历史失败: {e}")
        return []

    # ========== 全局控制方法 ==========
    
    @classmethod
    def pause_all(cls) -> bool:
        """暂停所有自动任务"""
        cls._paused = True
        cls.log_execution('system', None, 'completed', '所有自动任务已暂停')
        print("[UnifiedSchedule] 所有自动任务已暂停")
        return True
    
    @classmethod
    def resume_all(cls) -> bool:
        """恢复所有自动任务"""
        cls._paused = False
        cls.log_execution('system', None, 'completed', '所有自动任务已恢复')
        print("[UnifiedSchedule] 所有自动任务已恢复")
        return True
    
    @classmethod
    def is_paused(cls) -> bool:
        """检查是否暂停"""
        return cls._paused
    
    @classmethod
    def get_scheduler_status(cls) -> Dict[str, Any]:
        """获取调度器状态"""
        status = {
            'initialized': cls._initialized,
            'paused': cls._paused,
            'scheduler_running': False,
            'job_count': 0,
            'jobs': []
        }
        
        if cls.scheduler:
            status['scheduler_running'] = cls.scheduler.running
            jobs = cls.scheduler.get_jobs()
            status['job_count'] = len(jobs)
            for job in jobs:
                status['jobs'].append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                })
        
        return status
    
    @classmethod
    def shutdown_scheduler(cls) -> None:
        """关闭调度器"""
        if cls.scheduler and cls._initialized:
            try:
                cls.scheduler.shutdown(wait=False)
                cls._initialized = False
                print("[UnifiedSchedule] 调度器已关闭")
            except Exception as e:
                print(f"[UnifiedSchedule] 关闭调度器失败: {e}")
    
    # ========== 兼容旧接口 ==========
    
    @classmethod
    def schedule_daily_report(cls) -> bool:
        """兼容旧接口：添加日报调度"""
        return cls._add_system_job('daily_report', '0 18 * * *', cls._execute_daily_report) is None
    
    @classmethod
    def schedule_daily_statistics_snapshot(cls) -> bool:
        """兼容旧接口：添加统计快照调度"""
        return cls._add_system_job('stats_snapshot', '0 0 * * *', cls._execute_stats_snapshot) is None
    
    @classmethod
    def execute_scheduled_task(cls, plan_id: str) -> Dict[str, Any]:
        """兼容旧接口：执行定时任务"""
        return cls.execute_test_plan(plan_id)
    
    @classmethod
    def get_plan_logs(cls, plan_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取计划执行日志"""
        result = {
            'logs': [],
            'pagination': {'page': page, 'page_size': page_size, 'total': 0, 'total_pages': 0}
        }
        
        try:
            # 查询总数
            count_sql = """
                SELECT COUNT(*) as total FROM automation_logs 
                WHERE task_type = 'test_plan' AND related_id = %s
            """
            count_result = AppDatabaseService.execute_query(count_sql, (plan_id,))
            total = count_result[0]['total'] if count_result else 0
            
            result['pagination']['total'] = total
            result['pagination']['total_pages'] = (total + page_size - 1) // page_size if page_size > 0 else 0
            
            # 查询日志
            offset = (page - 1) * page_size
            sql = """
                SELECT log_id, related_id as plan_id, status, message, details,
                       duration_seconds, retry_count, created_at, completed_at
                FROM automation_logs
                WHERE task_type = 'test_plan' AND related_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            logs = AppDatabaseService.execute_query(sql, (plan_id, page_size, offset))
            
            for log in logs or []:
                details = log.get('details')
                if details and isinstance(details, str):
                    try:
                        log['details'] = json.loads(details)
                    except:
                        pass
                log['created_at'] = log['created_at'].isoformat() if log.get('created_at') else None
                log['completed_at'] = log['completed_at'].isoformat() if log.get('completed_at') else None
                # 兼容旧字段名
                log['action'] = 'scheduled_run'
                log['task_id'] = log.get('details', {}).get('task_id') if isinstance(log.get('details'), dict) else None
                result['logs'].append(log)
                
        except Exception as e:
            print(f"[UnifiedSchedule] 获取计划日志失败: {e}")
        
        return result
    
    @classmethod
    def get_schedule_status(cls, plan_id: str) -> Dict[str, Any]:
        """获取计划调度状态"""
        result = {
            'plan_id': plan_id,
            'has_schedule': False,
            'enabled': False,
            'config': None,
            'next_run': None,
            'job_active': False
        }
        
        try:
            sql = "SELECT schedule_config FROM test_plans WHERE plan_id = %s"
            results = AppDatabaseService.execute_query(sql, (plan_id,))
            
            if results and results[0].get('schedule_config'):
                config = results[0]['schedule_config']
                if isinstance(config, str):
                    config = json.loads(config)
                
                result['has_schedule'] = True
                result['config'] = config
                result['enabled'] = config.get('enabled', False)
                result['next_run'] = cls.get_next_run_time(plan_id)
                
                if cls.scheduler:
                    job = cls.scheduler.get_job(f'plan_{plan_id}')
                    result['job_active'] = job is not None
        except Exception as e:
            print(f"[UnifiedSchedule] 获取调度状态失败: {e}")
        
        return result


# 为了向后兼容，创建别名
ScheduleService = UnifiedScheduleService
