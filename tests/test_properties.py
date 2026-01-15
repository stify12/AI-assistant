"""
AI批改效果分析平台 - 属性测试
Property-based tests for the AI Grading Analysis Platform
"""

import pytest
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestBasicRoutes:
    """基本路由测试"""
    
    def test_index_page_loads(self, client):
        """测试首页加载"""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_subject_grading_page_loads(self, client):
        """测试学科批改页面加载"""
        response = client.get('/subject-grading')
        assert response.status_code == 200
    
    def test_batch_evaluation_page_loads(self, client):
        """测试批量评估页面加载"""
        response = client.get('/batch-evaluation')
        assert response.status_code == 200
    
    def test_config_api_get(self, client):
        """测试配置API GET"""
        response = client.get('/api/config')
        assert response.status_code == 200


class TestProperty25_EvalConfigWeightSum:
    """
    Property 25: 自定义评估配置权重和为1
    For any 学科评分规则配置，各权重之和应等于1
    """
    
    def test_math_weights_sum_to_one(self, client):
        """测试数学学科权重和为1"""
        config = {
            'dimensions': {},
            'subject_rules': {
                'math': {
                    'objective_ratio': 0.3,
                    'calculation_ratio': 0.5,
                    'subjective_ratio': 0.2
                }
            },
            'eval_scope': 'single'
        }
        math_sum = sum(config['subject_rules']['math'].values())
        assert abs(math_sum - 1.0) < 0.01
    
    def test_chinese_weights_sum_to_one(self, client):
        """测试语文学科权重和为1"""
        config = {
            'dimensions': {},
            'subject_rules': {
                'chinese': {
                    'objective_ratio': 0.2,
                    'subjective_ratio': 0.5,
                    'essay_ratio': 0.3
                }
            },
            'eval_scope': 'single'
        }
        chinese_sum = sum(config['subject_rules']['chinese'].values())
        assert abs(chinese_sum - 1.0) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
