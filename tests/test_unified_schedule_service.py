"""
统一调度服务测试模块

测试 UnifiedScheduleService 的核心功能：
- 调度器初始化
- 测试计划执行
- 日志记录
- 重试机制
- 调度配置管理

运行方式:
    USE_DB_STORAGE=false pytest tests/test_unified_schedule_service.py -v
"""
import os
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# 设置测试环境
os.environ['USE_DB_STORAGE'] = 'false'

# 导入被测模块
from services.unified_schedule_service import UnifiedScheduleService, APSCHEDULER_AVAILABLE


class TestUnifiedScheduleServiceInit:
    """测试调度器初始化"""
    
    def test_init_scheduler_without_apscheduler(self):
        """测试 APScheduler 未安装时的初始化"""
        with patch.object(UnifiedScheduleService, 'scheduler', None):
            with patch('services.unified_schedule_service.APSCHEDULER_AVAILABLE', False):
                # 重置状态
                UnifiedScheduleService._initialized = False
                result = UnifiedScheduleService.init_scheduler()
                assert result == False
    
    def test_scheduler_already_initialized(self):
        """测试调度器已初始化时跳过"""
        UnifiedScheduleService._initialized = True
        UnifiedScheduleService.scheduler = MagicMock()
        
        result = UnifiedScheduleService.init_scheduler()
        assert result == True
        
        # 清理
        UnifiedScheduleService._initialized = False
        UnifiedScheduleService.scheduler = None


class TestExecuteTestPlan:
    """测试测试计划执行"""
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_execute_plan_not_found(self, mock_db):
        """测试计划不存在的情况"""
        mock_db.execute_query.return_value = []
        
        result = UnifiedScheduleService.execute_test_plan('nonexistent_plan')
        
        assert result['status'] == 'failed'
        assert '不存在' in result['message']
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_execute_plan_skipped_when_paused(self, mock_db):
        """测试暂停时跳过执行"""
        UnifiedScheduleService._paused = True
        
        result = UnifiedScheduleService.execute_test_plan('test_plan_id')
        
        assert result['status'] == 'skipped'
        assert '暂停' in result['message']
        
        # 清理
        UnifiedScheduleService._paused = False
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_execute_plan_skipped_for_completed_status(self, mock_db):
        """测试已完成状态的计划跳过执行"""
        mock_db.execute_query.return_value = [{
            'plan_id': 'test_plan',
            'name': 'Test Plan',
            'status': 'completed'
        }]
        
        result = UnifiedScheduleService.execute_test_plan('test_plan')
        
        assert result['status'] == 'skipped'
        assert 'completed' in result['message']
    
    @patch('services.test_plan_service.create_batch_task_from_plan')
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_execute_plan_success(self, mock_db, mock_create_task):
        """测试成功执行计划"""
        mock_db.execute_query.return_value = [{
            'plan_id': 'test_plan',
            'name': 'Test Plan',
            'status': 'draft'
        }]
        mock_db.execute_insert.return_value = None
        mock_db.execute_update.return_value = None
        
        mock_create_task.return_value = {
            'success': True,
            'task_id': 'task_123',
            'homework_count': 10,
            'matched_count': 8
        }
        
        with patch.object(UnifiedScheduleService, '_update_plan_after_execution'):
            result = UnifiedScheduleService.execute_test_plan('test_plan')
        
        assert result['status'] == 'completed'
        assert result['task_id'] == 'task_123'
        assert result['homework_count'] == 10


class TestRetryMechanism:
    """测试重试机制"""
    
    def test_should_retry_for_transient_error(self):
        """测试临时错误应该重试"""
        assert UnifiedScheduleService._should_retry('Connection timeout') == True
        assert UnifiedScheduleService._should_retry('Database error') == True
    
    def test_should_not_retry_for_permanent_error(self):
        """测试永久错误不应该重试"""
        assert UnifiedScheduleService._should_retry('测试计划不存在') == False
        assert UnifiedScheduleService._should_retry('尚未匹配作业发布') == False
        assert UnifiedScheduleService._should_retry('没有关联数据集') == False
        assert UnifiedScheduleService._should_retry('计划状态为 completed') == False


class TestLogExecution:
    """测试日志记录"""
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_log_execution_success(self, mock_db):
        """测试成功记录日志"""
        mock_db.execute_insert.return_value = None
        
        log_id = UnifiedScheduleService.log_execution(
            task_type='test_plan',
            related_id='plan_123',
            status='completed',
            message='执行成功',
            details={'task_id': 'task_456'},
            duration_seconds=30,
            retry_count=0
        )
        
        assert log_id is not None
        assert len(log_id) == 8
        mock_db.execute_insert.assert_called_once()
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_log_execution_handles_error(self, mock_db):
        """测试日志记录失败时不抛异常"""
        mock_db.execute_insert.side_effect = Exception('DB Error')
        
        # 不应该抛出异常
        log_id = UnifiedScheduleService.log_execution(
            task_type='test_plan',
            related_id='plan_123',
            status='failed',
            message='执行失败'
        )
        
        assert log_id is not None


class TestScheduleConfig:
    """测试调度配置管理"""
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_set_plan_schedule_invalid_type(self, mock_db):
        """测试无效的调度类型"""
        with pytest.raises(ValueError) as exc_info:
            UnifiedScheduleService.set_plan_schedule('plan_123', {
                'type': 'invalid_type',
                'time': '09:00'
            })
        
        assert '无效的调度类型' in str(exc_info.value)
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_set_plan_schedule_invalid_time(self, mock_db):
        """测试无效的时间格式"""
        with pytest.raises(ValueError) as exc_info:
            UnifiedScheduleService.set_plan_schedule('plan_123', {
                'type': 'daily',
                'time': '25:00'
            })
        
        assert '无效的时间格式' in str(exc_info.value)
    
    def test_set_plan_schedule_empty_plan_id(self):
        """测试空计划ID"""
        with pytest.raises(ValueError) as exc_info:
            UnifiedScheduleService.set_plan_schedule('', {'type': 'daily', 'time': '09:00'})
        
        assert '计划ID不能为空' in str(exc_info.value)
    
    def test_set_plan_schedule_empty_config(self):
        """测试空配置"""
        with pytest.raises(ValueError) as exc_info:
            UnifiedScheduleService.set_plan_schedule('plan_123', None)
        
        assert '调度配置不能为空' in str(exc_info.value)


class TestGetScheduleStatus:
    """测试获取调度状态"""
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_get_schedule_status_no_config(self, mock_db):
        """测试无调度配置的情况"""
        mock_db.execute_query.return_value = [{'schedule_config': None}]
        
        result = UnifiedScheduleService.get_schedule_status('plan_123')
        
        assert result['plan_id'] == 'plan_123'
        assert result['has_schedule'] == False
        assert result['enabled'] == False
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_get_schedule_status_with_config(self, mock_db):
        """测试有调度配置的情况"""
        mock_db.execute_query.return_value = [{
            'schedule_config': json.dumps({
                'type': 'daily',
                'time': '09:00',
                'enabled': True
            })
        }]
        
        result = UnifiedScheduleService.get_schedule_status('plan_123')
        
        assert result['plan_id'] == 'plan_123'
        assert result['has_schedule'] == True
        assert result['enabled'] == True
        assert result['config']['type'] == 'daily'


class TestDisableSchedule:
    """测试禁用调度"""
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_disable_schedule_success(self, mock_db):
        """测试成功禁用调度"""
        mock_db.execute_update.return_value = None
        mock_db.execute_insert.return_value = None
        
        result = UnifiedScheduleService.disable_schedule('plan_123')
        
        assert result == True
        mock_db.execute_update.assert_called_once()


class TestGetPlanLogs:
    """测试获取计划日志"""
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_get_plan_logs_empty(self, mock_db):
        """测试无日志的情况"""
        mock_db.execute_query.side_effect = [
            [{'total': 0}],  # count query
            []  # logs query
        ]
        
        result = UnifiedScheduleService.get_plan_logs('plan_123')
        
        assert result['logs'] == []
        assert result['pagination']['total'] == 0
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_get_plan_logs_with_data(self, mock_db):
        """测试有日志的情况"""
        mock_db.execute_query.side_effect = [
            [{'total': 2}],
            [
                {
                    'log_id': 'log_1',
                    'plan_id': 'plan_123',
                    'status': 'completed',
                    'message': '执行成功',
                    'details': '{"task_id": "task_1"}',
                    'duration_seconds': 30,
                    'retry_count': 0,
                    'created_at': datetime.now(),
                    'completed_at': datetime.now()
                }
            ]
        ]
        
        result = UnifiedScheduleService.get_plan_logs('plan_123', page=1, page_size=20)
        
        assert len(result['logs']) == 1
        assert result['pagination']['total'] == 2
        assert result['logs'][0]['log_id'] == 'log_1'


class TestGlobalControl:
    """测试全局控制"""
    
    def test_pause_and_resume(self):
        """测试暂停和恢复"""
        # 初始状态
        UnifiedScheduleService._paused = False
        
        # 暂停
        with patch.object(UnifiedScheduleService, 'log_execution'):
            result = UnifiedScheduleService.pause_all()
        assert result == True
        assert UnifiedScheduleService.is_paused() == True
        
        # 恢复
        with patch.object(UnifiedScheduleService, 'log_execution'):
            result = UnifiedScheduleService.resume_all()
        assert result == True
        assert UnifiedScheduleService.is_paused() == False


class TestGetAllTasks:
    """测试获取所有任务"""
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_get_all_tasks(self, mock_db):
        """测试获取所有自动化任务"""
        mock_db.execute_query.return_value = [{'today': 1, 'week': 5, 'month': 20}]
        
        tasks = UnifiedScheduleService.get_all_tasks()
        
        assert len(tasks) == 4  # test_plan, daily_report, stats_snapshot, ai_analysis
        task_types = [t['task_type'] for t in tasks]
        assert 'test_plan' in task_types
        assert 'daily_report' in task_types


class TestBackwardCompatibility:
    """测试向后兼容性"""
    
    def test_schedule_service_alias(self):
        """测试 ScheduleService 别名"""
        from services.unified_schedule_service import ScheduleService
        assert ScheduleService is UnifiedScheduleService
    
    def test_execute_scheduled_task_alias(self):
        """测试 execute_scheduled_task 别名"""
        with patch.object(UnifiedScheduleService, 'execute_test_plan') as mock_execute:
            mock_execute.return_value = {'status': 'completed'}
            
            result = UnifiedScheduleService.execute_scheduled_task('plan_123')
            
            mock_execute.assert_called_once_with('plan_123')
            assert result['status'] == 'completed'


class TestCalculateNextRun:
    """测试下次执行时间计算"""
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_calculate_next_run_daily(self, mock_db):
        """测试每日调度的下次执行时间"""
        mock_db.execute_query.return_value = [{
            'schedule_config': json.dumps({
                'type': 'daily',
                'time': '09:00',
                'enabled': True
            })
        }]
        
        result = UnifiedScheduleService._calculate_next_run('plan_123')
        
        assert result is not None
        # 验证返回的是 ISO 格式的时间字符串
        datetime.fromisoformat(result)
    
    @patch('services.unified_schedule_service.AppDatabaseService')
    def test_calculate_next_run_disabled(self, mock_db):
        """测试禁用调度时返回 None"""
        mock_db.execute_query.return_value = [{
            'schedule_config': json.dumps({
                'type': 'daily',
                'time': '09:00',
                'enabled': False
            })
        }]
        
        result = UnifiedScheduleService._calculate_next_run('plan_123')
        
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
