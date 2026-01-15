"""
语义级评估服务测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json
from hypothesis import given, strategies as st, settings

from services.semantic_eval_service import SemanticEvalService


class TestRuleBasedPrecheck:
    """规则预筛测试"""
    
    def test_exact_match_pass(self):
        """完全一致应该通过"""
        base_item = {
            'userAnswer': '3/4',
            'correct': 'yes',
            'answer': '3/4'
        }
        ai_item = {
            'userAnswer': '3/4',
            'correct': 'yes'
        }
        
        certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
        
        assert certainty == 'high'
        assert result['verdict'] == 'PASS'
        assert result['error_type'] == '完全正确'
        assert result['severity'] == 'none'
    
    def test_judgment_mismatch_fail(self):
        """判断不一致应该失败"""
        base_item = {
            'userAnswer': '3/4',
            'correct': 'yes',
            'answer': '3/4'
        }
        ai_item = {
            'userAnswer': '3/4',
            'correct': 'no'
        }
        
        certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
        
        assert certainty == 'high'
        assert result['verdict'] == 'FAIL'
        assert result['error_type'] == '识别正确-判断错误'
        assert result['severity'] == 'high'
    
    def test_hallucination_detection(self):
        """AI 幻觉检测"""
        base_item = {
            'userAnswer': '2/3',  # 学生写的错误答案
            'correct': 'no',      # 人工判断为错
            'answer': '3/4'       # 标准答案
        }
        ai_item = {
            'userAnswer': '3/4',  # AI 识别成了标准答案（幻觉）
            'correct': 'yes'      # AI 判断为对
        }
        
        certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
        
        assert certainty == 'high'
        assert result['verdict'] == 'FAIL'
        assert result['error_type'] == 'AI幻觉'
        assert result['severity'] == 'critical'
        assert result['hallucination']['detected'] == True
    
    def test_uncertain_case(self):
        """不确定情况应该返回 low certainty"""
        base_item = {
            'userAnswer': '3/4',
            'correct': 'yes',
            'answer': '3/4'
        }
        ai_item = {
            'userAnswer': '0.75',  # 不同表达但可能语义等价
            'correct': 'yes'
        }
        
        certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
        
        assert certainty == 'low'
        assert result is None
    
    def test_correct_field_normalization(self):
        """correct 字段标准化测试"""
        # 测试布尔值
        base_item = {'userAnswer': 'A', 'correct': True, 'answer': 'A'}
        ai_item = {'userAnswer': 'A', 'correct': 'yes'}
        
        certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
        assert certainty == 'high'
        assert result['verdict'] == 'PASS'
        
        # 测试字符串 'true'
        base_item = {'userAnswer': 'A', 'correct': 'true', 'answer': 'A'}
        ai_item = {'userAnswer': 'A', 'correct': 'YES'}
        
        certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
        assert certainty == 'high'
        assert result['verdict'] == 'PASS'


class TestGenerateSummary:
    """汇总报告生成测试"""
    
    def test_all_pass_summary(self):
        """全部通过的汇总"""
        results = [
            {'verdict': 'PASS', 'error_type': '完全正确', 'severity': 'none',
             'recognition': {'status': '一致'}, 'judgment': {'status': '一致'},
             'hallucination': {'detected': False}},
            {'verdict': 'PASS', 'error_type': '完全正确', 'severity': 'none',
             'recognition': {'status': '一致'}, 'judgment': {'status': '一致'},
             'hallucination': {'detected': False}},
        ]
        
        summary = SemanticEvalService._generate_summary(results)
        
        assert summary['overview']['total'] == 2
        assert summary['overview']['passed'] == 2
        assert summary['overview']['failed'] == 0
        assert summary['overview']['pass_rate'] == 100.0
        assert summary['capability_scores']['recognition'] == 100.0
        assert summary['capability_scores']['judgment'] == 100.0
        assert summary['hallucination_rate'] == 0
    
    def test_mixed_results_summary(self):
        """混合结果的汇总"""
        results = [
            {'verdict': 'PASS', 'error_type': '完全正确', 'severity': 'none',
             'recognition': {'status': '一致'}, 'judgment': {'status': '一致'},
             'hallucination': {'detected': False}},
            {'verdict': 'FAIL', 'error_type': '识别正确-判断错误', 'severity': 'high',
             'recognition': {'status': '一致'}, 'judgment': {'status': '不一致'},
             'hallucination': {'detected': False}},
            {'verdict': 'FAIL', 'error_type': 'AI幻觉', 'severity': 'critical',
             'recognition': {'status': '不一致'}, 'judgment': {'status': '不一致'},
             'hallucination': {'detected': True}},
        ]
        
        summary = SemanticEvalService._generate_summary(results)
        
        assert summary['overview']['total'] == 3
        assert summary['overview']['passed'] == 1
        assert summary['overview']['failed'] == 2
        assert summary['error_distribution']['完全正确'] == 1
        assert summary['error_distribution']['识别正确-判断错误'] == 1
        assert summary['error_distribution']['AI幻觉'] == 1
        assert summary['severity_distribution']['none'] == 1
        assert summary['severity_distribution']['high'] == 1
        assert summary['severity_distribution']['critical'] == 1
        assert summary['hallucination_rate'] > 0
    
    def test_empty_results_summary(self):
        """空结果的汇总"""
        results = []
        
        summary = SemanticEvalService._generate_summary(results)
        
        assert summary['overview']['total'] == 0
        assert summary['overview']['pass_rate'] == 0
        assert summary['hallucination_rate'] == 0


class TestPropertyBased:
    """属性测试"""
    
    @given(
        user_answer=st.text(min_size=0, max_size=50),
        correct=st.sampled_from(['yes', 'no', True, False, 'true', 'false'])
    )
    @settings(max_examples=50)
    def test_exact_match_always_pass(self, user_answer, correct):
        """
        属性：完全相同的输入应该总是通过
        """
        base_item = {
            'userAnswer': user_answer,
            'correct': correct,
            'answer': user_answer
        }
        ai_item = {
            'userAnswer': user_answer,
            'correct': correct
        }
        
        certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
        
        assert certainty == 'high'
        assert result['verdict'] == 'PASS'
    
    @given(
        base_correct=st.sampled_from(['yes', 'no']),
        ai_correct=st.sampled_from(['yes', 'no'])
    )
    @settings(max_examples=20)
    def test_judgment_mismatch_always_fail(self, base_correct, ai_correct):
        """
        属性：判断不一致时应该总是失败（除非是语义等价情况）
        """
        if base_correct == ai_correct:
            return  # 跳过相同的情况
        
        base_item = {
            'userAnswer': 'A',
            'correct': base_correct,
            'answer': 'A'
        }
        ai_item = {
            'userAnswer': 'A',
            'correct': ai_correct
        }
        
        certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
        
        assert certainty == 'high'
        assert result['verdict'] == 'FAIL'
    
    @given(
        results=st.lists(
            st.fixed_dictionaries({
                'verdict': st.sampled_from(['PASS', 'FAIL']),
                'error_type': st.sampled_from(['完全正确', '语义等价', '识别正确-判断错误', 
                                               '识别错误-判断正确', '识别错误-判断错误', 'AI幻觉']),
                'severity': st.sampled_from(['none', 'low', 'medium', 'high', 'critical']),
                'recognition': st.fixed_dictionaries({
                    'status': st.sampled_from(['一致', '语义等价', '不一致'])
                }),
                'judgment': st.fixed_dictionaries({
                    'status': st.sampled_from(['一致', '不一致'])
                }),
                'hallucination': st.fixed_dictionaries({
                    'detected': st.booleans()
                })
            }),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=30)
    def test_summary_consistency(self, results):
        """
        属性：汇总报告的数据应该一致
        - passed + failed = total
        - 各错误类型数量之和 = total
        - 各严重程度数量之和 = total
        """
        summary = SemanticEvalService._generate_summary(results)
        
        # passed + failed = total
        assert summary['overview']['passed'] + summary['overview']['failed'] == summary['overview']['total']
        
        # 错误分布之和 = total
        error_sum = sum(summary['error_distribution'].values())
        assert error_sum == summary['overview']['total']
        
        # 严重程度分布之和 = total
        severity_sum = sum(summary['severity_distribution'].values())
        assert severity_sum == summary['overview']['total']
        
        # pass_rate 在 0-100 之间
        assert 0 <= summary['overview']['pass_rate'] <= 100
        
        # hallucination_rate 在 0-100 之间
        assert 0 <= summary['hallucination_rate'] <= 100
        
        # 能力评分在 0-100 之间
        assert 0 <= summary['capability_scores']['recognition'] <= 100
        assert 0 <= summary['capability_scores']['judgment'] <= 100
        assert 0 <= summary['capability_scores']['overall'] <= 100


class TestIntegration:
    """集成测试（需要 API Key）"""
    
    @pytest.mark.skip(reason="需要配置 DeepSeek API Key")
    def test_evaluate_single_with_llm(self):
        """单题 LLM 评估测试"""
        result = SemanticEvalService.evaluate_single(
            subject='数学',
            question_type='填空题',
            index='1',
            standard_answer='3/4',
            base_user_answer='0.75',
            base_correct='yes',
            ai_user_answer='0.75',
            ai_correct='yes'
        )
        
        assert 'verdict' in result
        assert result['verdict'] in ('PASS', 'FAIL', 'ERROR')
    
    @pytest.mark.skip(reason="需要配置 DeepSeek API Key")
    def test_evaluate_batch_with_llm(self):
        """批量 LLM 评估测试"""
        items = [
            {
                'index': '1',
                'standard_answer': '3/4',
                'base_user_answer': '0.75',
                'base_correct': 'yes',
                'ai_user_answer': '0.75',
                'ai_correct': 'yes'
            },
            {
                'index': '2',
                'standard_answer': 'A',
                'base_user_answer': 'A',
                'base_correct': 'yes',
                'ai_user_answer': 'B',
                'ai_correct': 'no'
            }
        ]
        
        result = SemanticEvalService.evaluate_batch(
            subject='数学',
            question_type='选择题',
            items=items
        )
        
        assert 'results' in result
        assert 'summary' in result
        assert len(result['results']) == 2
