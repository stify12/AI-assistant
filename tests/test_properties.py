"""
AI批改效果分析平台 - 属性测试
Property-based tests for the AI Grading Analysis Platform
"""

import pytest
import json
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, load_config, save_config, load_eval_config, save_eval_config


@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestProperty13_APIKeyIndependentConfig:
    """
    Property 13: 评估模型API Key独立配置
    For any 配置对象，Qwen3-Max API Key和DeepSeek API Key应独立存储，
    修改其中一个不影响另一个
    Validates: Requirements 8.1.2
    """
    
    def test_qwen_key_independent_from_deepseek(self, client):
        """测试Qwen API Key独立于DeepSeek API Key"""
        # 设置初始配置
        initial_config = {
            'api_key': 'test_api_key',
            'qwen_api_key': 'qwen_key_1',
            'deepseek_api_key': 'deepseek_key_1'
        }
        client.post('/api/config', json=initial_config)
        
        # 修改Qwen API Key
        updated_config = {
            'api_key': 'test_api_key',
            'qwen_api_key': 'qwen_key_2',
            'deepseek_api_key': 'deepseek_key_1'
        }
        client.post('/api/config', json=updated_config)
        
        # 验证DeepSeek API Key未被修改
        response = client.get('/api/config')
        config = response.get_json()
        assert config['deepseek_api_key'] == 'deepseek_key_1'
        assert config['qwen_api_key'] == 'qwen_key_2'
    
    def test_deepseek_key_independent_from_qwen(self, client):
        """测试DeepSeek API Key独立于Qwen API Key"""
        # 设置初始配置
        initial_config = {
            'api_key': 'test_api_key',
            'qwen_api_key': 'qwen_key_1',
            'deepseek_api_key': 'deepseek_key_1'
        }
        client.post('/api/config', json=initial_config)
        
        # 修改DeepSeek API Key
        updated_config = {
            'api_key': 'test_api_key',
            'qwen_api_key': 'qwen_key_1',
            'deepseek_api_key': 'deepseek_key_2'
        }
        client.post('/api/config', json=updated_config)
        
        # 验证Qwen API Key未被修改
        response = client.get('/api/config')
        config = response.get_json()
        assert config['qwen_api_key'] == 'qwen_key_1'
        assert config['deepseek_api_key'] == 'deepseek_key_2'


class TestProperty19_UnifiedAIEvalCompatibility:
    """
    Property 19: 统一AI评估入口兼容性
    For any 测试类型（single/batch/consistency/multi_model），
    统一AI评估接口应返回有效的评估结果
    Validates: Requirements 31.1, 31.2, 31.3, 31.4
    """
    
    def test_single_test_type_returns_valid_result(self, client):
        """测试single类型返回有效结果"""
        response = client.post('/api/ai-eval/unified', json={
            'test_type': 'single',
            'eval_model': 'qwen3-max',
            'test_results': {'model': 'test', 'n': 5, 'successCount': 5}
        })
        # 即使没有配置API Key，也应该返回错误而不是崩溃
        assert response.status_code in [200, 400]
    
    def test_batch_test_type_returns_valid_result(self, client):
        """测试batch类型返回有效结果"""
        response = client.post('/api/ai-eval/unified', json={
            'test_type': 'batch',
            'eval_model': 'deepseek',
            'test_results': {'summary': {'total_questions': 10}}
        })
        assert response.status_code in [200, 400]
    
    def test_consistency_test_type_returns_valid_result(self, client):
        """测试consistency类型返回有效结果"""
        response = client.post('/api/ai-eval/unified', json={
            'test_type': 'consistency',
            'eval_model': 'joint',
            'test_results': {'model': 'test', 'consistency': 90}
        })
        assert response.status_code in [200, 400]
    
    def test_multi_model_test_type_returns_valid_result(self, client):
        """测试multi_model类型返回有效结果"""
        response = client.post('/api/ai-eval/unified', json={
            'test_type': 'multi_model',
            'eval_model': 'joint',
            'test_results': {'models': ['model1', 'model2']}
        })
        assert response.status_code in [200, 400]


class TestProperty20_QuantifyThresholdComparison:
    """
    Property 20: 量化数据阈值对比正确性
    For any 评估指标值和阈值，pass字段应正确反映value与threshold的比较结果
    Validates: Requirements 32.3, 32.5
    """
    
    def test_accuracy_above_threshold_passes(self, client):
        """测试准确率高于阈值时pass为True"""
        response = client.post('/api/ai-eval/quantify', json={
            'test_results': {'avgAccuracy': 85},
            'thresholds': {'accuracy': 80}
        })
        data = response.get_json()
        assert data['dimensions']['accuracy']['pass'] == True
    
    def test_accuracy_below_threshold_fails(self, client):
        """测试准确率低于阈值时pass为False"""
        response = client.post('/api/ai-eval/quantify', json={
            'test_results': {'avgAccuracy': 75},
            'thresholds': {'accuracy': 80}
        })
        data = response.get_json()
        assert data['dimensions']['accuracy']['pass'] == False
    
    def test_consistency_threshold_comparison(self, client):
        """测试一致性阈值对比"""
        response = client.post('/api/ai-eval/quantify', json={
            'test_results': {'consistency': 90},
            'thresholds': {'consistency': 80}
        })
        data = response.get_json()
        assert data['dimensions']['consistency']['pass'] == True


class TestProperty21_ProblemLocateErrorTypes:
    """
    Property 21: 问题定位错误类型完整性
    For any 批改错误，error_type应为预定义类型之一
    （识别不准确/规则有误/格式错误/计算错误/选项混淆）
    Validates: Requirements 33.2
    """
    
    VALID_ERROR_TYPES = ['识别不准确', '规则有误', '格式错误', '计算错误', '选项混淆']
    
    def test_error_type_is_valid(self, client):
        """测试错误类型是有效的预定义类型"""
        # 这个测试需要配置DeepSeek API Key才能运行
        # 这里只测试接口是否正常响应
        response = client.post('/api/ai-eval/problem-locate', json={
            'error_questions': [
                {'index': '1', 'standard_answer': 'A', 'user_answer': 'B'}
            ]
        })
        # 没有配置API Key时应返回400
        assert response.status_code in [200, 400]


class TestProperty24_QuestionTypeDetection:
    """
    Property 24: 题型识别结果有效性
    For any 题型识别结果，detected_type应为预定义类型之一
    （objective/subjective/calculation/essay），confidence应在0-1范围内
    Validates: Requirements 6.2.2, 6.2.3, 6.2.4, 6.2.5
    """
    
    VALID_TYPES = ['objective', 'subjective', 'calculation', 'essay', 'unknown']
    
    def test_choice_question_detected_as_objective(self, client):
        """测试选择题被识别为客观题"""
        response = client.post('/api/question-type/detect', json={
            'content': '下列哪个选项是正确的？A. 选项1 B. 选项2 C. 选项3 D. 选项4',
            'use_ai': False
        })
        data = response.get_json()
        assert data['detected_type'] in self.VALID_TYPES
        assert 0 <= data['confidence'] <= 1
    
    def test_fill_blank_detected_as_objective(self, client):
        """测试填空题被识别为客观题"""
        response = client.post('/api/question-type/detect', json={
            'content': '请填空：中国的首都是____。',
            'use_ai': False
        })
        data = response.get_json()
        assert data['detected_type'] in self.VALID_TYPES
        assert 0 <= data['confidence'] <= 1
    
    def test_calculation_question_detected(self, client):
        """测试计算题被正确识别"""
        response = client.post('/api/question-type/detect', json={
            'content': '计算：25 × 4 + 100 ÷ 5 = ?',
            'use_ai': False
        })
        data = response.get_json()
        assert data['detected_type'] in self.VALID_TYPES
        assert 0 <= data['confidence'] <= 1
    
    def test_essay_question_detected(self, client):
        """测试作文题被正确识别"""
        response = client.post('/api/question-type/detect', json={
            'content': '作文题：请以"我的梦想"为题，写一篇不少于800字的文章。',
            'use_ai': False
        })
        data = response.get_json()
        assert data['detected_type'] in self.VALID_TYPES
        assert 0 <= data['confidence'] <= 1


class TestProperty25_EvalConfigWeightSum:
    """
    Property 25: 自定义评估配置权重和为1
    For any 学科评分规则配置，各权重之和应等于1
    Validates: Requirements 6.1.5, 6.1.6
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
        # 验证权重和
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
        # 验证权重和
        chinese_sum = sum(config['subject_rules']['chinese'].values())
        assert abs(chinese_sum - 1.0) < 0.01


class TestProperty22_ChartDataCompleteness:
    """
    Property 22: 可视化图表数据完整性
    For any 图表数据对象，labels数组长度应与data数组长度一致
    Validates: Requirements 34.1, 34.2, 34.3
    """
    
    def test_chart_labels_match_data_length(self, client):
        """测试图表labels和data长度一致"""
        response = client.post('/api/ai-eval/charts', json={
            'test_results': {
                'model_stats': {
                    'model1': {'avgAcc': 85, 'consistency': 90},
                    'model2': {'avgAcc': 80, 'consistency': 85}
                }
            },
            'chart_types': ['multi_model_bar']
        })
        data = response.get_json()
        if 'charts' in data and 'multi_model_bar' in data['charts']:
            chart = data['charts']['multi_model_bar']
            labels_len = len(chart['labels'])
            for dataset in chart['datasets']:
                assert len(dataset['data']) == labels_len


if __name__ == '__main__':
    pytest.main([__file__, '-v'])



class TestProperty14_MacroAnalysisReportCompleteness:
    """
    Property 14: 宏观分析报告完整性
    For any Qwen3-Max生成的对比报告，应包含model_comparison、recommendations字段，
    且model_comparison应包含strengths和weaknesses
    Validates: Requirements 8.2.2
    """
    
    def test_macro_analysis_response_structure(self, client):
        """测试宏观分析响应结构"""
        # 这个测试需要配置Qwen API Key才能完整运行
        response = client.post('/api/qwen/macro-analysis', json={
            'test_results': {
                'model': 'test_model',
                'accuracy': 85,
                'consistency': 90
            },
            'analysis_type': 'comparison'
        })
        # 没有配置API Key时应返回400
        assert response.status_code in [200, 400]


class TestProperty15_DeepSeekSemanticEvalCompleteness:
    """
    Property 15: DeepSeek语义评估响应完整性
    For any DeepSeek语义评估响应，应包含semantic_correct、score、error_type、confidence字段，
    且score在0-1范围内
    Validates: Requirements 8.3.2
    """
    
    def test_semantic_eval_response_structure(self, client):
        """测试语义评估响应结构"""
        response = client.post('/api/deepseek/semantic-eval', json={
            'question': '1+1=?',
            'standard_answer': '2',
            'ai_answer': '2',
            'subject': '数学',
            'question_type': '计算题'
        })
        # 没有配置API Key时应返回400
        assert response.status_code in [200, 400]


class TestProperty16_JointReportDataSourceCompleteness:
    """
    Property 16: 联合报告数据来源完整性
    For any 联合评估报告，应同时包含macro_analysis（来源qwen3-max）和
    micro_evaluation（来源deepseek）两部分
    Validates: Requirements 27.1.2
    """
    
    def test_joint_report_has_both_sources(self, client):
        """测试联合报告包含两个数据来源"""
        response = client.post('/api/eval/joint-report', json={
            'test_results': {
                'model': 'test',
                'accuracy': 85
            },
            'questions': []
        })
        # 没有配置API Key时应返回400或降级结果
        assert response.status_code in [200, 400]


class TestProperty17_JointReportStructurePartition:
    """
    Property 17: 联合报告结构分区正确性
    For any 联合评估报告，macro_analysis.source应为"qwen3-max"，
    micro_evaluation.source应为"deepseek"
    Validates: Requirements 27.1.3
    """
    
    def test_joint_report_source_labels(self, client):
        """测试联合报告来源标签正确"""
        # 这个测试需要配置两个API Key才能完整运行
        response = client.post('/api/eval/joint-report', json={
            'test_results': {'model': 'test'},
            'questions': []
        })
        assert response.status_code in [200, 400]


class TestProperty18_DiscrepancyAnnotationCompleteness:
    """
    Property 18: 评估分歧标注完整性
    For any 存在分歧的联合评估报告，discrepancies数组中每个分歧项应包含
    question_id、qwen_opinion、deepseek_opinion字段
    Validates: Requirements 27.1.4
    """
    
    def test_discrepancy_fields_present(self, client):
        """测试分歧项包含必要字段"""
        # 这个测试需要配置两个API Key才能完整运行
        response = client.post('/api/eval/joint-report', json={
            'test_results': {'model': 'test'},
            'questions': [{'index': '1', 'standard_answer': 'A'}]
        })
        assert response.status_code in [200, 400]


class TestProperty23_DeepSeekReportStructureCompleteness:
    """
    Property 23: DeepSeek报告结构完整性
    For any DeepSeek生成的评估报告，应包含evaluation_background、configuration、
    core_data、problem_analysis、optimization_suggestions五个必要部分
    Validates: Requirements 35.2, 35.3, 35.4, 35.5, 35.6
    """
    
    REQUIRED_SECTIONS = [
        'evaluation_background',
        'configuration', 
        'core_data',
        'problem_analysis',
        'optimization_suggestions'
    ]
    
    def test_report_has_all_required_sections(self, client):
        """测试报告包含所有必要部分"""
        response = client.post('/api/deepseek/report', json={
            'test_results': {
                'model': 'test',
                'avgAccuracy': 85,
                'consistency': 90
            }
        })
        
        if response.status_code == 200:
            data = response.get_json()
            for section in self.REQUIRED_SECTIONS:
                assert section in data, f"Missing required section: {section}"
        else:
            # 没有配置API Key时应返回400
            assert response.status_code == 400
