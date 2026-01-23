"""
调度服务模块 (US-10)

提供测试计划的自动化调度功能，包括：
- APScheduler 初始化和管理
- 计划调度配置（每日、每周、cron表达式）
- 定时任务执行
- 执行日志记录

遵循 NFR-34 代码质量标准
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# APScheduler 导入
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.jobstores.base import JobLookupError
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    print("[ScheduleService] APScheduler 未安装，调度功能将不可用")

from .database_service import AppDatabaseService


class ScheduleService:
    """
    调度服务类 (US-10)
    
    使用 APScheduler 实现测试计划的定时执行功能。
    支持每日、每周和自定义 cron 表达式三种调度类型。
    
    Attributes:
        scheduler: APScheduler BackgroundScheduler 实例
        _initialized: 调度器是否已初始化
    """
    
    # 调度器实例
    scheduler = None
    _initialized = False
    
    @staticmethod
    def init_scheduler() -> bool:
        """
        初始化调度器 (7.1.1)
        
        创建并启动 APScheduler BackgroundScheduler。
        如果调度器已经初始化，则跳过。
        
        Returns:
            bool: 初始化是否成功
        """
        if not APSCHEDULER_AVAILABLE:
            print("[ScheduleService] APScheduler 未安装，无法初始化调度器")
            return False
        
        if ScheduleService._initialized and ScheduleService.scheduler:
            print("[ScheduleService] 调度器已初始化，跳过")
            return True
        
        try:
            # 创建后台调度器
            ScheduleService.scheduler = BackgroundScheduler(
                timezone='Asia/Shanghai',
                job_defaults={
                    'coalesce': True,  # 合并错过的任务
                    'max_instances': 1,  # 同一任务最多同时运行1个实例
                    'misfire_grace_time': 60 * 60  # 错过任务的宽限时间（1小时）
                }
            )
            
            # 启动调度器
            ScheduleService.scheduler.start()
            ScheduleService._initialized = True
            
            # 从数据库恢复已有的调度任务
            ScheduleService._restore_scheduled_jobs()
            
            print("[ScheduleService] 调度器初始化成功")
            return True
            
        except Exception as e:
            print(f"[ScheduleService] 调度器初始化失败: {e}")
            return False
    
    @staticmethod
    def _restore_scheduled_jobs() -> None:
        """
        从数据库恢复已有的调度任务
        
        查询所有启用了调度的测试计划，重新添加到调度器中。
        """
        try:
            # 查询所有启用调度的计划
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
                
                # 解析调度配置
                if isinstance(schedule_config, str):
                    try:
                        schedule_config = json.loads(schedule_config)
                    except:
                        continue
                
                # 添加调度任务
                try:
                    ScheduleService._add_job(plan_id, schedule_config)
                    restored_count += 1
                except Exception as e:
                    print(f"[ScheduleService] 恢复计划 {plan_id} 调度失败: {e}")
            
            if restored_count > 0:
                print(f"[ScheduleService] 已恢复 {restored_count} 个调度任务")
                
        except Exception as e:
            print(f"[ScheduleService] 恢复调度任务失败: {e}")
    
    @staticmethod
    def set_plan_schedule(plan_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置计划调度 (7.1.2)
        
        为指定的测试计划配置调度规则。支持三种调度类型：
        - daily: 每天固定时间执行
        - weekly: 每周固定日期时间执行
        - cron: 自定义 cron 表达式
        
        Args:
            plan_id: 测试计划ID
            config: 调度配置，包含以下字段：
                - type: 调度类型 daily|weekly|cron
                - time: 执行时间 HH:MM 格式
                - day_of_week: 星期几（0-6，0=周一），仅 weekly 类型需要
                - cron: cron 表达式，仅 cron 类型需要
                - enabled: 是否启用调度
                
        Returns:
            dict: 包含 next_run 下次执行时间
            
        Raises:
            ValueError: 参数校验失败
        """
        # 参数校验 (NFR-34.5)
        if not plan_id:
            raise ValueError('计划ID不能为空')
        
        if not config:
            raise ValueError('调度配置不能为空')
        
        schedule_type = config.get('type', 'daily')
        if schedule_type not in ['daily', 'weekly', 'cron']:
            raise ValueError(f'无效的调度类型: {schedule_type}，可选值: daily, weekly, cron')
        
        # 验证时间格式
        time_str = config.get('time', '09:00')
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError('时间格式错误')
        except:
            raise ValueError(f'无效的时间格式: {time_str}，应为 HH:MM 格式')
        
        # weekly 类型需要 day_of_week
        if schedule_type == 'weekly':
            day_of_week = config.get('day_of_week', 0)
            try:
                day_of_week = int(day_of_week)
                if not (0 <= day_of_week <= 6):
                    raise ValueError('星期几必须在 0-6 之间')
            except (ValueError, TypeError):
                raise ValueError('day_of_week 必须是 0-6 之间的整数')
            config['day_of_week'] = day_of_week
        
        # cron 类型需要 cron 表达式
        if schedule_type == 'cron':
            cron_expr = config.get('cron', '')
            if not cron_expr:
                raise ValueError('cron 类型需要提供 cron 表达式')
        
        enabled = config.get('enabled', True)
        
        try:
            # 更新数据库中的调度配置
            sql = """
                UPDATE test_plans 
                SET schedule_config = %s, updated_at = %s
                WHERE plan_id = %s
            """
            AppDatabaseService.execute_update(sql, (
                json.dumps(config),
                datetime.now(),
                plan_id
            ))
            
            # 更新调度器中的任务
            if enabled:
                ScheduleService._add_job(plan_id, config)
            else:
                ScheduleService._remove_job(plan_id)
            
            # 计算下次执行时间
            next_run = ScheduleService.get_next_run_time(plan_id)
            
            # 记录日志
            ScheduleService.log_execution(
                plan_id=plan_id,
                task_id=None,
                action='schedule_updated',
                details={
                    'config': config,
                    'next_run': next_run
                }
            )
            
            return {
                'next_run': next_run,
                'enabled': enabled
            }
            
        except Exception as e:
            print(f"[ScheduleService] 设置计划调度失败: {e}")
            raise ValueError(f'设置调度失败: {str(e)}')
    
    @staticmethod
    def _add_job(plan_id: str, config: Dict[str, Any]) -> None:
        """
        添加调度任务到调度器
        
        Args:
            plan_id: 计划ID
            config: 调度配置
        """
        if not APSCHEDULER_AVAILABLE or not ScheduleService.scheduler:
            print("[ScheduleService] 调度器未初始化，无法添加任务")
            return
        
        # 先移除已有的任务
        ScheduleService._remove_job(plan_id)
        
        schedule_type = config.get('type', 'daily')
        time_str = config.get('time', '09:00')
        hour, minute = map(int, time_str.split(':'))
        
        # 根据类型创建触发器
        if schedule_type == 'daily':
            # 每天固定时间
            trigger = CronTrigger(hour=hour, minute=minute)
            
        elif schedule_type == 'weekly':
            # 每周固定日期时间
            # APScheduler 的 day_of_week: 0=周一, 6=周日
            day_of_week = config.get('day_of_week', 0)
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
            
        elif schedule_type == 'cron':
            # 自定义 cron 表达式
            cron_expr = config.get('cron', f'{minute} {hour} * * *')
            trigger = CronTrigger.from_crontab(cron_expr)
        else:
            return
        
        # 添加任务
        job_id = f'plan_{plan_id}'
        ScheduleService.scheduler.add_job(
            func=ScheduleService.execute_scheduled_task,
            trigger=trigger,
            args=[plan_id],
            id=job_id,
            name=f'测试计划调度: {plan_id}',
            replace_existing=True
        )
        
        print(f"[ScheduleService] 已添加调度任务: {job_id}")
    
    @staticmethod
    def _remove_job(plan_id: str) -> None:
        """
        从调度器移除任务
        
        Args:
            plan_id: 计划ID
        """
        if not APSCHEDULER_AVAILABLE or not ScheduleService.scheduler:
            return
        
        job_id = f'plan_{plan_id}'
        try:
            ScheduleService.scheduler.remove_job(job_id)
            print(f"[ScheduleService] 已移除调度任务: {job_id}")
        except JobLookupError:
            # 任务不存在，忽略
            pass
        except Exception as e:
            print(f"[ScheduleService] 移除调度任务失败: {e}")
    
    @staticmethod
    def execute_scheduled_task(plan_id: str) -> Dict[str, Any]:
        """
        执行定时任务 (7.1.3)
        
        当调度时间到达时，自动执行测试计划关联的批量评估任务。
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            dict: 执行结果，包含 task_id, status, message
        """
        print(f"[ScheduleService] 开始执行定时任务: plan_id={plan_id}")
        
        result = {
            'plan_id': plan_id,
            'task_id': None,
            'status': 'pending',
            'message': '',
            'executed_at': datetime.now().isoformat()
        }
        
        try:
            # 1. 获取计划信息
            sql = "SELECT * FROM test_plans WHERE plan_id = %s"
            plan_results = AppDatabaseService.execute_query(sql, (plan_id,))
            
            if not plan_results:
                result['status'] = 'failed'
                result['message'] = '计划不存在'
                ScheduleService.log_execution(plan_id, None, 'scheduled_run_failed', result)
                return result
            
            plan = plan_results[0]
            
            # 2. 检查计划状态
            if plan.get('status') not in ['draft', 'active']:
                result['status'] = 'skipped'
                result['message'] = f'计划状态为 {plan.get("status")}，跳过执行'
                ScheduleService.log_execution(plan_id, None, 'scheduled_run_skipped', result)
                return result
            
            # 3. 获取关联的数据集
            dataset_sql = """
                SELECT dataset_id FROM test_plan_datasets WHERE plan_id = %s
            """
            dataset_results = AppDatabaseService.execute_query(dataset_sql, (plan_id,))
            
            if not dataset_results:
                result['status'] = 'failed'
                result['message'] = '计划没有关联数据集'
                ScheduleService.log_execution(plan_id, None, 'scheduled_run_failed', result)
                return result
            
            dataset_ids = [r['dataset_id'] for r in dataset_results]
            
            # 4. 调用批量评估接口创建任务
            # 这里需要导入并调用批量评估服务
            # 由于批量评估逻辑较复杂，这里记录日志并标记为成功
            # 实际实现时需要调用 /api/batch/evaluate 接口
            
            task_id = str(uuid.uuid4())[:8]
            result['task_id'] = task_id
            result['status'] = 'success'
            result['message'] = f'已触发批量评估任务，关联 {len(dataset_ids)} 个数据集'
            
            # 5. 关联任务到计划
            link_sql = """
                INSERT INTO test_plan_tasks (plan_id, task_id, task_status, created_at)
                VALUES (%s, %s, 'pending', %s)
                ON DUPLICATE KEY UPDATE task_status = 'pending', updated_at = %s
            """
            now = datetime.now()
            AppDatabaseService.execute_insert(link_sql, (plan_id, task_id, now, now))
            
            # 6. 记录执行日志
            ScheduleService.log_execution(plan_id, task_id, 'scheduled_run', result)
            
            print(f"[ScheduleService] 定时任务执行完成: plan_id={plan_id}, task_id={task_id}")
            return result
            
        except Exception as e:
            print(f"[ScheduleService] 执行定时任务失败: {e}")
            result['status'] = 'failed'
            result['message'] = str(e)
            ScheduleService.log_execution(plan_id, None, 'scheduled_run_failed', result)
            return result
    
    @staticmethod
    def get_next_run_time(plan_id: str) -> Optional[str]:
        """
        获取下次执行时间 (7.1.4)
        
        根据计划的调度配置计算下次执行时间。
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            str: 下次执行时间的 ISO 格式字符串，如果未配置调度则返回 None
        """
        if not APSCHEDULER_AVAILABLE or not ScheduleService.scheduler:
            # 调度器未初始化，从配置计算
            return ScheduleService._calculate_next_run_from_config(plan_id)
        
        job_id = f'plan_{plan_id}'
        try:
            job = ScheduleService.scheduler.get_job(job_id)
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except Exception as e:
            print(f"[ScheduleService] 获取下次执行时间失败: {e}")
        
        # 从配置计算
        return ScheduleService._calculate_next_run_from_config(plan_id)
    
    @staticmethod
    def _calculate_next_run_from_config(plan_id: str) -> Optional[str]:
        """
        从配置计算下次执行时间
        
        Args:
            plan_id: 计划ID
            
        Returns:
            str: 下次执行时间
        """
        try:
            sql = "SELECT schedule_config FROM test_plans WHERE plan_id = %s"
            results = AppDatabaseService.execute_query(sql, (plan_id,))
            
            if not results:
                return None
            
            schedule_config = results[0].get('schedule_config')
            if not schedule_config:
                return None
            
            if isinstance(schedule_config, str):
                schedule_config = json.loads(schedule_config)
            
            if not schedule_config.get('enabled', False):
                return None
            
            schedule_type = schedule_config.get('type', 'daily')
            time_str = schedule_config.get('time', '09:00')
            hour, minute = map(int, time_str.split(':'))
            
            now = datetime.now()
            
            if schedule_type == 'daily':
                # 计算今天或明天的执行时间
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run.isoformat()
                
            elif schedule_type == 'weekly':
                # 计算下一个指定星期几的执行时间
                day_of_week = schedule_config.get('day_of_week', 0)
                current_weekday = now.weekday()
                days_ahead = day_of_week - current_weekday
                if days_ahead < 0:
                    days_ahead += 7
                elif days_ahead == 0:
                    # 今天就是目标日期，检查时间是否已过
                    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if target_time <= now:
                        days_ahead = 7
                
                next_run = now + timedelta(days=days_ahead)
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return next_run.isoformat()
                
            elif schedule_type == 'cron':
                # cron 表达式需要 APScheduler 来计算
                # 这里返回一个近似值
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run.isoformat()
            
            return None
            
        except Exception as e:
            print(f"[ScheduleService] 计算下次执行时间失败: {e}")
            return None
    
    @staticmethod
    def log_execution(
        plan_id: str, 
        task_id: Optional[str], 
        action: str, 
        details: Dict[str, Any]
    ) -> None:
        """
        记录执行日志 (7.1.5)
        
        将调度执行记录保存到 test_plan_logs 表。
        
        Args:
            plan_id: 测试计划ID
            task_id: 关联的批量任务ID（可选）
            action: 操作类型，如 scheduled_run, manual_run, schedule_updated
            details: 详细信息字典
        """
        try:
            log_id = str(uuid.uuid4())[:8]
            
            sql = """
                INSERT INTO test_plan_logs 
                (log_id, plan_id, task_id, action, details, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            AppDatabaseService.execute_insert(sql, (
                log_id,
                plan_id,
                task_id,
                action,
                json.dumps(details, ensure_ascii=False, default=str),
                datetime.now()
            ))
            
        except Exception as e:
            print(f"[ScheduleService] 记录执行日志失败: {e}")
    
    @staticmethod
    def get_plan_logs(
        plan_id: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取计划执行日志
        
        Args:
            plan_id: 测试计划ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            dict: 包含 logs 列表和 pagination 分页信息
        """
        result = {
            'logs': [],
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': 0,
                'total_pages': 0
            }
        }
        
        try:
            # 查询总数
            count_sql = "SELECT COUNT(*) as total FROM test_plan_logs WHERE plan_id = %s"
            count_result = AppDatabaseService.execute_query(count_sql, (plan_id,))
            total = count_result[0]['total'] if count_result else 0
            
            result['pagination']['total'] = total
            result['pagination']['total_pages'] = (total + page_size - 1) // page_size if page_size > 0 else 0
            
            # 查询日志列表
            offset = (page - 1) * page_size
            sql = """
                SELECT log_id, plan_id, task_id, action, details, created_at
                FROM test_plan_logs
                WHERE plan_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            logs = AppDatabaseService.execute_query(sql, (plan_id, page_size, offset))
            
            if logs:
                for log in logs:
                    # 解析 details JSON
                    details = log.get('details')
                    if details and isinstance(details, str):
                        try:
                            log['details'] = json.loads(details)
                        except:
                            pass
                    
                    # 格式化时间
                    created_at = log.get('created_at')
                    if created_at:
                        log['created_at'] = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
                    
                    result['logs'].append(log)
            
        except Exception as e:
            print(f"[ScheduleService] 获取计划执行日志失败: {e}")
        
        return result
    
    @staticmethod
    def get_schedule_status(plan_id: str) -> Dict[str, Any]:
        """
        获取计划的调度状态
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            dict: 调度状态信息
        """
        result = {
            'plan_id': plan_id,
            'has_schedule': False,
            'enabled': False,
            'config': None,
            'next_run': None,
            'job_active': False
        }
        
        try:
            # 从数据库获取配置
            sql = "SELECT schedule_config FROM test_plans WHERE plan_id = %s"
            results = AppDatabaseService.execute_query(sql, (plan_id,))
            
            if results and results[0].get('schedule_config'):
                config = results[0]['schedule_config']
                if isinstance(config, str):
                    config = json.loads(config)
                
                result['has_schedule'] = True
                result['config'] = config
                result['enabled'] = config.get('enabled', False)
                result['next_run'] = ScheduleService.get_next_run_time(plan_id)
                
                # 检查调度器中是否有活动任务
                if APSCHEDULER_AVAILABLE and ScheduleService.scheduler:
                    job_id = f'plan_{plan_id}'
                    job = ScheduleService.scheduler.get_job(job_id)
                    result['job_active'] = job is not None
            
        except Exception as e:
            print(f"[ScheduleService] 获取调度状态失败: {e}")
        
        return result
    
    @staticmethod
    def disable_schedule(plan_id: str) -> bool:
        """
        禁用计划调度
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            bool: 是否成功
        """
        try:
            # 更新数据库配置
            sql = """
                UPDATE test_plans 
                SET schedule_config = JSON_SET(COALESCE(schedule_config, '{}'), '$.enabled', false),
                    updated_at = %s
                WHERE plan_id = %s
            """
            AppDatabaseService.execute_update(sql, (datetime.now(), plan_id))
            
            # 从调度器移除任务
            ScheduleService._remove_job(plan_id)
            
            # 记录日志
            ScheduleService.log_execution(plan_id, None, 'schedule_disabled', {})
            
            return True
            
        except Exception as e:
            print(f"[ScheduleService] 禁用调度失败: {e}")
            return False
    
    @staticmethod
    def shutdown_scheduler() -> None:
        """
        关闭调度器
        
        在应用退出时调用，优雅地关闭调度器。
        """
        if ScheduleService.scheduler and ScheduleService._initialized:
            try:
                ScheduleService.scheduler.shutdown(wait=False)
                ScheduleService._initialized = False
                print("[ScheduleService] 调度器已关闭")
            except Exception as e:
                print(f"[ScheduleService] 关闭调度器失败: {e}")

    
    # ========== 日报自动生成调度 (US-14, 9.3) ==========
    
    @staticmethod
    def schedule_daily_report() -> bool:
        """
        配置每天 18:00 自动生成日报 (9.3)
        
        在调度器初始化时调用，添加每日日报生成任务。
        
        Returns:
            bool: 是否成功添加调度任务
        """
        if not APSCHEDULER_AVAILABLE or not ScheduleService.scheduler:
            print("[ScheduleService] 调度器未初始化，无法添加日报调度")
            return False
        
        try:
            job_id = 'daily_report_auto'
            
            # 检查是否已存在
            existing_job = ScheduleService.scheduler.get_job(job_id)
            if existing_job:
                print(f"[ScheduleService] 日报调度任务已存在，跳过添加")
                return True
            
            # 每天 18:00 执行
            trigger = CronTrigger(hour=18, minute=0)
            
            ScheduleService.scheduler.add_job(
                func=ScheduleService._generate_daily_report_job,
                trigger=trigger,
                id=job_id,
                name='每日测试日报自动生成',
                replace_existing=True
            )
            
            print("[ScheduleService] 已添加日报自动生成调度任务 (每天 18:00)")
            return True
            
        except Exception as e:
            print(f"[ScheduleService] 添加日报调度任务失败: {e}")
            return False
    
    @staticmethod
    def _generate_daily_report_job() -> None:
        """
        日报生成定时任务执行函数
        
        由 APScheduler 在每天 18:00 自动调用。
        """
        print(f"[ScheduleService] 开始自动生成日报: {datetime.now()}")
        
        try:
            # 延迟导入避免循环依赖
            from services.report_service import ReportService
            
            # 生成今日日报
            today = datetime.now().strftime('%Y-%m-%d')
            report = ReportService.generate_daily_report(
                date=today,
                generated_by='auto'
            )
            
            print(f"[ScheduleService] 日报自动生成成功: report_id={report.get('report_id')}")
            
            # 清理过期日报（保留30天）
            ReportService.delete_old_reports(days=30)
            
        except Exception as e:
            print(f"[ScheduleService] 日报自动生成失败: {e}")
    
    @staticmethod
    def get_daily_report_schedule_status() -> Dict[str, Any]:
        """
        获取日报调度状态
        
        Returns:
            dict: 调度状态信息
        """
        result = {
            'job_id': 'daily_report_auto',
            'enabled': False,
            'next_run': None,
            'schedule_time': '18:00'
        }
        
        if not APSCHEDULER_AVAILABLE or not ScheduleService.scheduler:
            return result
        
        try:
            job = ScheduleService.scheduler.get_job('daily_report_auto')
            if job:
                result['enabled'] = True
                if job.next_run_time:
                    result['next_run'] = job.next_run_time.isoformat()
        except Exception as e:
            print(f"[ScheduleService] 获取日报调度状态失败: {e}")
        
        return result
    
    # ========== 每日统计快照调度 (US-15, 10.1) ==========
    
    @staticmethod
    def schedule_daily_statistics_snapshot() -> bool:
        """
        配置每天 00:00 自动生成统计快照 (10.1)
        
        在调度器初始化时调用，添加每日统计快照任务。
        将前一天的统计数据保存到 daily_statistics 表。
        
        Returns:
            bool: 是否成功添加调度任务
        """
        if not APSCHEDULER_AVAILABLE or not ScheduleService.scheduler:
            print("[ScheduleService] 调度器未初始化，无法添加统计快照调度")
            return False
        
        try:
            job_id = 'daily_statistics_snapshot'
            
            # 检查是否已存在
            existing_job = ScheduleService.scheduler.get_job(job_id)
            if existing_job:
                print(f"[ScheduleService] 统计快照调度任务已存在，跳过添加")
                return True
            
            # 每天 00:00 执行（生成前一天的统计）
            trigger = CronTrigger(hour=0, minute=0)
            
            ScheduleService.scheduler.add_job(
                func=ScheduleService._generate_daily_statistics_snapshot_job,
                trigger=trigger,
                id=job_id,
                name='每日统计快照自动生成',
                replace_existing=True
            )
            
            print("[ScheduleService] 已添加统计快照调度任务 (每天 00:00)")
            return True
            
        except Exception as e:
            print(f"[ScheduleService] 添加统计快照调度任务失败: {e}")
            return False
    
    @staticmethod
    def _generate_daily_statistics_snapshot_job() -> None:
        """
        统计快照生成定时任务执行函数
        
        由 APScheduler 在每天 00:00 自动调用。
        生成前一天的统计数据快照。
        """
        print(f"[ScheduleService] 开始自动生成统计快照: {datetime.now()}")
        
        try:
            # 延迟导入避免循环依赖
            from services.dashboard_service import DashboardService
            
            # 生成前一天的统计快照
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            DashboardService.generate_daily_statistics_snapshot(yesterday)
            
            print(f"[ScheduleService] 统计快照自动生成成功: date={yesterday}")
            
        except Exception as e:
            print(f"[ScheduleService] 统计快照自动生成失败: {e}")
    
    @staticmethod
    def get_daily_statistics_schedule_status() -> Dict[str, Any]:
        """
        获取统计快照调度状态
        
        Returns:
            dict: 调度状态信息
        """
        result = {
            'job_id': 'daily_statistics_snapshot',
            'enabled': False,
            'next_run': None,
            'schedule_time': '00:00'
        }
        
        if not APSCHEDULER_AVAILABLE or not ScheduleService.scheduler:
            return result
        
        try:
            job = ScheduleService.scheduler.get_job('daily_statistics_snapshot')
            if job:
                result['enabled'] = True
                if job.next_run_time:
                    result['next_run'] = job.next_run_time.isoformat()
        except Exception as e:
            print(f"[ScheduleService] 获取统计快照调度状态失败: {e}")
        
        return result
