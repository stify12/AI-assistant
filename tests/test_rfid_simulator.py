#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RFID 模拟器测试文件
测试服务层和路由层功能
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# 导入被测模块
from services.rfid_simulator_service import (
    RfidSimulatorService, 
    ClientStatus, 
    AdbClient, 
    SimulationTask
)


class TestRfidSimulatorService:
    """RFID 模拟器服务测试"""
    
    def setup_method(self):
        """每个测试前重置服务"""
        self.service = RfidSimulatorService()
    
    # ==================== 命令构建测试 ====================
    
    def test_build_char_command_digit(self):
        """测试数字字符命令构建"""
        cmd = self.service.build_char_command('0', '/dev/input/event2')
        assert cmd is not None
        assert 'sendevent /dev/input/event2' in cmd
        assert '458783' in cmd  # 数字 0 的事件码
    
    def test_build_char_command_enter(self):
        """测试回车命令构建"""
        cmd = self.service.build_char_command('enter', '/dev/input/event2')
        assert cmd is not None
        assert '458784' in cmd  # 回车的事件码
        assert '28' in cmd  # 回车的键码
    
    def test_build_char_command_invalid(self):
        """测试无效字符返回 None"""
        cmd = self.service.build_char_command('a', '/dev/input/event2')
        assert cmd is None
    
    def test_build_rfid_commands(self):
        """测试完整 RFID 命令序列构建"""
        commands = self.service.build_rfid_commands('123', '/dev/input/event2', True)
        
        # 3 个数字 + 1 个回车 = 4 条命令
        assert len(commands) == 4
        
        # 验证每条命令都包含设备路径
        for cmd in commands:
            assert '/dev/input/event2' in cmd
    
    def test_build_rfid_commands_no_enter(self):
        """测试不发送回车的命令序列"""
        commands = self.service.build_rfid_commands('123', '/dev/input/event2', False)
        
        # 只有 3 个数字
        assert len(commands) == 3
    
    # ==================== 客户端管理测试 ====================
    
    def test_register_client(self):
        """测试客户端注册"""
        mock_ws = Mock()
        client = self.service.register_client(
            'test_client', 
            '192.168.1.100', 
            mock_ws,
            {'model': 'Test Device'}
        )
        
        assert client.client_id == 'test_client'
        assert client.ip_address == '192.168.1.100'
        assert client.status == ClientStatus.ONLINE
        assert client.device_info['model'] == 'Test Device'
    
    def test_unregister_client(self):
        """测试客户端注销"""
        mock_ws = Mock()
        self.service.register_client('test_client', '192.168.1.100', mock_ws)
        
        self.service.unregister_client('test_client')
        
        status = self.service.get_client_status()
        assert status['connected'] is False
    
    def test_get_client_status_no_client(self):
        """测试无客户端时的状态"""
        status = self.service.get_client_status()
        
        assert status['connected'] is False
        assert status['client'] is None
    
    def test_get_client_status_with_client(self):
        """测试有客户端时的状态"""
        mock_ws = Mock()
        self.service.register_client('test_client', '192.168.1.100', mock_ws)
        
        status = self.service.get_client_status()
        
        assert status['connected'] is True
        assert status['client']['client_id'] == 'test_client'
    
    def test_update_heartbeat(self):
        """测试心跳更新"""
        mock_ws = Mock()
        self.service.register_client('test_client', '192.168.1.100', mock_ws)
        
        old_heartbeat = self.service._clients['test_client'].last_heartbeat
        
        import time
        time.sleep(0.01)
        
        self.service.update_heartbeat('test_client', {'model': 'Updated'})
        
        new_heartbeat = self.service._clients['test_client'].last_heartbeat
        assert new_heartbeat >= old_heartbeat
        assert self.service._clients['test_client'].device_info['model'] == 'Updated'
    
    def test_get_active_websocket(self):
        """测试获取活跃 WebSocket"""
        mock_ws = Mock()
        self.service.register_client('test_client', '192.168.1.100', mock_ws)
        
        ws = self.service.get_active_websocket()
        assert ws == mock_ws
    
    def test_get_active_websocket_no_client(self):
        """测试无客户端时返回 None"""
        ws = self.service.get_active_websocket()
        assert ws is None
    
    # ==================== 日志管理测试 ====================
    
    def test_add_log(self):
        """测试添加日志"""
        self.service._add_log('info', '测试消息')
        
        logs = self.service.get_logs()
        assert len(logs) == 1
        assert logs[0]['level'] == 'info'
        assert logs[0]['message'] == '测试消息'
    
    def test_log_limit(self):
        """测试日志数量限制"""
        for i in range(150):
            self.service._add_log('info', f'消息 {i}')
        
        logs = self.service.get_logs()
        assert len(logs) <= self.service._max_logs
    
    def test_clear_logs(self):
        """测试清空日志"""
        self.service._add_log('info', '测试消息')
        self.service.clear_logs()
        
        logs = self.service.get_logs()
        assert len(logs) == 0
    
    # ==================== 任务管理测试 ====================
    
    def test_create_task(self):
        """测试创建任务"""
        cards = [
            {'name': '张三', 'cardNumber': '123456'},
            {'name': '李四', 'cardNumber': '654321'}
        ]
        
        task = self.service.create_task(cards, 5, True, '/dev/input/event2')
        
        assert task.task_id is not None
        assert len(task.cards) == 2
        assert task.interval_seconds == 5
        assert task.send_enter is True
        assert task.status == 'pending'
    
    def test_get_current_task(self):
        """测试获取当前任务"""
        cards = [{'name': '张三', 'cardNumber': '123456'}]
        self.service.create_task(cards, 5, True, '/dev/input/event2')
        
        task = self.service.get_current_task()
        
        assert task is not None
        assert task['total_count'] == 1
    
    def test_update_task_status(self):
        """测试更新任务状态"""
        cards = [{'name': '张三', 'cardNumber': '123456'}]
        self.service.create_task(cards, 5, True, '/dev/input/event2')
        
        self.service.update_task_status('running', 0, True)
        
        task = self.service.get_current_task()
        assert task['status'] == 'running'
        assert task['success_count'] == 1
    
    def test_pause_resume_task(self):
        """测试暂停和恢复任务"""
        cards = [{'name': '张三', 'cardNumber': '123456'}]
        self.service.create_task(cards, 5, True, '/dev/input/event2')
        self.service._current_task.status = 'running'
        
        self.service.pause_task()
        assert self.service._current_task.status == 'paused'
        
        self.service.resume_task()
        assert self.service._current_task.status == 'running'
    
    def test_stop_task(self):
        """测试停止任务"""
        cards = [{'name': '张三', 'cardNumber': '123456'}]
        self.service.create_task(cards, 5, True, '/dev/input/event2')
        
        self.service.stop_task()
        
        assert self.service._current_task.status == 'stopped'


class TestRfidEventMap:
    """RFID 事件映射测试"""
    
    def setup_method(self):
        self.service = RfidSimulatorService()
    
    def test_all_digits_mapped(self):
        """测试所有数字都有映射"""
        for digit in '0123456789':
            assert digit in self.service.RFID_EVENT_MAP
    
    def test_enter_mapped(self):
        """测试回车有映射"""
        assert 'enter' in self.service.RFID_EVENT_MAP
    
    def test_event_format(self):
        """测试事件格式正确"""
        for char, events in self.service.RFID_EVENT_MAP.items():
            # 每个字符应该有 6 个事件（按下 3 个 + 释放 3 个）
            assert len(events) == 6
            
            for event in events:
                # 每个事件是 (type, code, value) 三元组
                assert len(event) == 3
                assert all(isinstance(v, int) for v in event)


class TestAdbClientDataClass:
    """ADB 客户端数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        client = AdbClient(
            client_id='test',
            ip_address='192.168.1.100',
            connected_at=datetime.now(),
            last_heartbeat=datetime.now(),
            status=ClientStatus.ONLINE,
            device_info={'model': 'Test'}
        )
        
        d = client.to_dict()
        
        assert d['client_id'] == 'test'
        assert d['ip_address'] == '192.168.1.100'
        assert d['status'] == 'online'
        assert d['device_info']['model'] == 'Test'


class TestSimulationTaskDataClass:
    """模拟任务数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        task = SimulationTask(
            task_id='abc123',
            cards=[{'name': '张三', 'cardNumber': '123'}],
            interval_seconds=5,
            send_enter=True,
            device_path='/dev/input/event2',
            status='running',
            current_index=0,
            success_count=1,
            failed_count=0,
            created_at=datetime.now()
        )
        
        d = task.to_dict()
        
        assert d['task_id'] == 'abc123'
        assert d['total_count'] == 1
        assert d['interval_seconds'] == 5
        assert d['status'] == 'running'


# ==================== 路由测试 ====================

class TestRfidSimulatorRoutes:
    """RFID 模拟器路由测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_get_status(self, client):
        """测试获取状态 API"""
        response = client.get('/api/rfid-simulator/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'connection' in data['data']
    
    def test_get_logs(self, client):
        """测试获取日志 API"""
        response = client.get('/api/rfid-simulator/logs')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert isinstance(data['data'], list)
    
    def test_send_rfid_no_client(self, client):
        """测试无客户端时发送 RFID"""
        response = client.post(
            '/api/rfid-simulator/send',
            data=json.dumps({'rfid_code': '123456'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert '没有可用的 ADB 客户端' in data['error']
    
    def test_send_rfid_invalid_code(self, client):
        """测试发送无效卡号"""
        response = client.post(
            '/api/rfid-simulator/send',
            data=json.dumps({'rfid_code': 'abc'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert '只能包含数字' in data['error']
    
    def test_send_rfid_empty_code(self, client):
        """测试发送空卡号"""
        response = client.post(
            '/api/rfid-simulator/send',
            data=json.dumps({'rfid_code': ''}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert '不能为空' in data['error']
    
    def test_batch_start_no_cards(self, client):
        """测试空卡片列表开始批量"""
        response = client.post(
            '/api/rfid-simulator/batch/start',
            data=json.dumps({'cards': []}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert '不能为空' in data['error']
    
    def test_clear_logs(self, client):
        """测试清空日志 API"""
        response = client.delete('/api/rfid-simulator/logs')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_page_render(self, client):
        """测试页面渲染"""
        response = client.get('/rfid-simulator')
        
        assert response.status_code == 200
        assert b'RFID' in response.data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
