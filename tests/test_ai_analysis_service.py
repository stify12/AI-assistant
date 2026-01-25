"""
AI 智能分析服务测试
测试 Phase 2 核心服务实现
包含属性测试 (Property-Based Tests)
"""
import pytest
import json
import sys
import os
import time
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hypothesis import given, strategies as st, settings, HealthCheck
from services.ai_analysis_service import AIAnalysisService


# ============================================
# 测试数据生成策略
# ============================================

# 错误类型策略
error_type_strategy = st.sampled_from([
    '识别错误-判断错误',
    '识别正确-判断错误',
    '缺失题目',
    'AI识别幻觉',
    '答案不匹配'
])

# 学科ID策略
subject_id_strategy = st.integers(min_value=0, max_value=6)

# 页码策略
page_num_strategy = st.integers(min_value=1, max_value=200)

# 题目索引策略
question_index_strategy = st.integers(min_value=1, max_value=50)

# 错误样本策略
error_sample_strategy = st.fixed_dictionaries({
    'homework_id': st.text(min_size=8, max_size=16, alphabet='abcdef0123456789'),
    'book_name': st.sampled_from(['数学八上', '物理八上', '化学八上', '英语七上', '语文七下']),
    'page_num': page_num_strategy,
    'subject_id': subject_id_strategy,
    'question_index': question_index_strategy,
    'error_type': error_type_strategy,
    'ai_answer': st.text(min_size=1, max_size=100),
    'expected_answer': st.text(min_size=1, max_size=100),
    'description': st.text(max_size=200)
})

# 错误样本列表策略
error_samples_list_strategy = st.lists(error_sample_strategy, min_size=1, max_size=100)


# ============================================
# 单元测试
# ============================================

class TestQuickStats:
    """测试快速统计功能"""
    
    def test_quick_stats_returns_required_fields(self):
        """测试快速统计返回必需字段"""
        # 创建模拟任务数据
        mock_task_data = {
            'task_id': 'test_task_001',
            'homework_items': [
                {
                    'homework_id': 'hw001',
                    'book_name': '数学八上',
                    'page_num': 10,
                    'subject_id': 2,
                    'status': 'completed',
                    'evaluation': {
                        'total_questions': 10,
                        'errors': [
                            {'question_index': 1, 'error_type': '识别错误-判断错误', 'ai_answer': 'A', 'expected_answer': 'B'},
                            {'question_index': 3, 'error_type': '缺失题目', 'ai_answer': '', 'expected_answer': 'C'}
                        ]
                    }
                }
            ]
        }
        
        with patch.object(AIAnalysisService, '_load_task', return_value=mock_task_data):
            result = AIAnalysisService.get_quick_stats('test_task_001')
        
        # 验证必需字段
        assert 'total_errors' in result
        assert 'total_questions' in result
        assert 'error_rate' in result
        assert 'error_type_distribution' in result
        assert 'subject_distribution' in result
        assert 'book_distribution' in result
        assert 'clusters' in result
        assert 'duration_ms' in result
    
    def test_quick_stats_response_time(self):
        """测试快速统计响应时间 < 100ms"""
        # 创建较大的模拟数据
        mock_task_data = {
            'task_id': 'test_task_002',
            'homework_items': []
        }
        
        # 生成 100 个作业项
        for i in range(100):
            mock_task_data['homework_items'].append({
                'homework_id': f'hw{i:03d}',
                'book_name': f'书本{i % 5}',
                'page_num': i % 50 + 1,
                'subject_id': i % 7,
                'status': 'completed',
                'evaluation': {
                    'total_questions': 10,
                    'errors': [
                        {'question_index': j, 'error_type': '识别错误-判断错误', 'ai_answer': 'A', 'expected_answer': 'B'}
                        for j in range(i % 5)
                    ]
                }
            })
        
        with patch.object(AIAnalysisService, '_load_task', return_value=mock_task_data):
            start_time = time.time()
            result = AIAnalysisService.get_quick_stats('test_task_002')
            duration_ms = (time.time() - start_time) * 1000
        
        # 验证响应时间
        assert duration_ms < 100, f"快速统计响应时间 {duration_ms:.2f}ms 超过 100ms 限制"
        assert result.get('duration_ms', 0) < 100
    
    def test_quick_stats_task_not_found(self):
        """测试任务不存在时的处理"""
        with patch.object(AIAnalysisService, '_load_task', return_value=None):
            result = AIAnalysisService.get_quick_stats('nonexistent_task')
        
        assert 'error' in result
        assert result['total_errors'] == 0
        assert result['total_questions'] == 0


class TestClusterGeneration:
    """测试聚类生成功能"""
    
    def test_generate_quick_clusters_groups_correctly(self):
        """测试快速聚类正确分组"""
        error_samples = [
            {'error_type': '识别错误-判断错误', 'book_name': '数学八上', 'page_num': 10},
            {'error_type': '识别错误-判断错误', 'book_name': '数学八上', 'page_num': 15},
            {'error_type': '缺失题目', 'book_name': '数学八上', 'page_num': 10},
            {'error_type': '识别错误-判断错误', 'book_name': '物理八上', 'page_num': 10},
        ]
        
        clusters = AIAnalysisService._generate_quick_clusters(error_samples)
        
        # 验证聚类数量
        assert len(clusters) >= 2  # 至少有 2 个不同的聚类
        
        # 验证聚类结构
        for cluster in clusters:
            assert 'cluster_key' in cluster
            assert 'error_type' in cluster
            assert 'book_name' in cluster
            assert 'page_range' in cluster
            assert 'sample_count' in cluster
            assert 'samples' in cluster
    
    def test_generate_quick_clusters_sorted_by_count(self):
        """测试聚类按样本数排序"""
        error_samples = [
            {'error_type': '识别错误-判断错误', 'book_name': '数学八上', 'page_num': 10},
            {'error_type': '识别错误-判断错误', 'book_name': '数学八上', 'page_num': 11},
            {'error_type': '识别错误-判断错误', 'book_name': '数学八上', 'page_num': 12},
            {'error_type': '缺失题目', 'book_name': '物理八上', 'page_num': 10},
        ]
        
        clusters = AIAnalysisService._generate_quick_clusters(error_samples)
        
        # 验证按样本数降序排列
        counts = [c['sample_count'] for c in clusters]
        assert counts == sorted(counts, reverse=True)


class TestAnomalyDetection:
    """测试异常检测功能"""
    
    def test_detect_inconsistent_grading(self):
        """测试批改不一致检测"""
        mock_task_data = {
            'task_id': 'test_task_003',
            'homework_items': [
                {
                    'homework_id': 'hw001',
                    'status': 'completed',
                    'evaluation': {
                        'questions': [
                            {'question_index': 1, 'base_user': '3.14', 'is_correct': True, 'ai_answer': '3.14', 'expected_answer': '3.14'},
                        ]
                    }
                },
                {
                    'homework_id': 'hw002',
                    'status': 'completed',
                    'evaluation': {
                        'questions': [
                            {'question_index': 1, 'base_user': '3.14', 'is_correct': False, 'ai_answer': '3.14', 'expected_answer': '3.14'},
                        ]
                    }
                },
                {
                    'homework_id': 'hw003',
                    'status': 'completed',
                    'evaluation': {
                        'questions': [
                            {'question_index': 1, 'base_user': '3.14', 'is_correct': True, 'ai_answer': '3.14', 'expected_answer': '3.14'},
                        ]
                    }
                }
            ]
        }
        
        with patch.object(AIAnalysisService, '_load_task', return_value=mock_task_data):
            anomalies = AIAnalysisService.detect_anomalies('test_task_003')
        
        # 应该检测到批改不一致
        inconsistent = [a for a in anomalies if a['anomaly_type'] == 'inconsistent_grading']
        assert len(inconsistent) > 0
        
        # 验证异常结构
        anomaly = inconsistent[0]
        assert 'anomaly_id' in anomaly
        assert 'severity' in anomaly
        assert 'base_user_answer' in anomaly
        assert 'correct_cases' in anomaly
        assert 'incorrect_cases' in anomaly
        assert 'inconsistency_rate' in anomaly


class TestQueueManagement:
    """测试队列管理功能"""
    
    def test_trigger_analysis_adds_to_queue(self):
        """测试触发分析添加到队列"""
        # 清空队列
        AIAnalysisService._queue.clear()
        AIAnalysisService._running.clear()
        
        with patch.object(AIAnalysisService, '_try_process_queue'):
            result = AIAnalysisService.trigger_analysis('test_task_004', 'medium')
        
        assert result['queued'] is True
        assert result['position'] >= 1
        assert result['job_id'] is not None
    
    def test_trigger_analysis_priority_ordering(self):
        """测试优先级排序"""
        # 清空队列
        AIAnalysisService._queue.clear()
        AIAnalysisService._running.clear()
        
        with patch.object(AIAnalysisService, '_try_process_queue'):
            AIAnalysisService.trigger_analysis('task_low', 'low')
            AIAnalysisService.trigger_analysis('task_high', 'high')
            AIAnalysisService.trigger_analysis('task_medium', 'medium')
        
        # 验证高优先级在前
        queue = AIAnalysisService._queue
        assert queue[0]['task_id'] == 'task_high'
    
    def test_cancel_analysis_removes_from_queue(self):
        """测试取消分析从队列移除"""
        # 清空队列
        AIAnalysisService._queue.clear()
        AIAnalysisService._running.clear()
        
        with patch.object(AIAnalysisService, '_try_process_queue'):
            result = AIAnalysisService.trigger_analysis('test_task_005', 'medium')
        
        job_id = result['job_id']
        
        # 取消任务
        cancel_result = AIAnalysisService.cancel_analysis(job_id)
        
        assert cancel_result['success'] is True
        
        # 验证已从队列移除
        queue_status = AIAnalysisService.get_analysis_queue_status()
        task_ids = [t['task_id'] for t in queue_status['waiting_tasks']]
        assert 'test_task_005' not in task_ids


class TestCacheManagement:
    """测试缓存管理功能"""
    
    def test_compute_data_hash_consistency(self):
        """测试数据哈希一致性"""
        data1 = {'a': 1, 'b': 2}
        data2 = {'b': 2, 'a': 1}  # 相同数据，不同顺序
        data3 = {'a': 1, 'b': 3}  # 不同数据
        
        hash1 = AIAnalysisService._compute_data_hash(data1)
        hash2 = AIAnalysisService._compute_data_hash(data2)
        hash3 = AIAnalysisService._compute_data_hash(data3)
        
        # 相同数据应该产生相同哈希
        assert hash1 == hash2
        # 不同数据应该产生不同哈希
        assert hash1 != hash3


# ============================================
# 属性测试
# ============================================

class TestQuickStatsProperties:
    """
    属性测试：快速统计
    Feature: ai-analysis-enhancement, Property 1: Quick Stats Data Accuracy
    Validates: Requirements 17.2, 17.4
    """
    
    @given(error_samples=error_samples_list_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_error_count_matches_samples(self, error_samples):
        """
        Feature: ai-analysis-enhancement, Property 1: Quick Stats Data Accuracy
        Validates: Requirements 17.2
        
        Property: For any list of error samples, the total_errors count SHALL equal
        the length of the error samples list.
        """
        # 创建模拟任务数据
        mock_task_data = {
            'task_id': 'prop_test_task',
            'homework_items': [
                {
                    'homework_id': f'hw_{i}',
                    'book_name': sample['book_name'],
                    'page_num': sample['page_num'],
                    'subject_id': sample['subject_id'],
                    'status': 'completed',
                    'evaluation': {
                        'total_questions': 10,
                        'errors': [
                            {
                                'question_index': sample['question_index'],
                                'error_type': sample['error_type'],
                                'ai_answer': sample['ai_answer'],
                                'expected_answer': sample['expected_answer'],
                                'description': sample['description']
                            }
                        ]
                    }
                }
                for i, sample in enumerate(error_samples)
            ]
        }
        
        with patch.object(AIAnalysisService, '_load_task', return_value=mock_task_data):
            result = AIAnalysisService.get_quick_stats('prop_test_task')
        
        # 验证错误数等于样本数
        assert result['total_errors'] == len(error_samples), \
            f"Expected {len(error_samples)} errors, got {result['total_errors']}"
    
    @given(error_samples=error_samples_list_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_error_type_distribution_sums_to_total(self, error_samples):
        """
        Feature: ai-analysis-enhancement, Property 2: Cluster Completeness
        Validates: Requirements 2.1
        
        Property: For any list of error samples, the sum of error_type_distribution
        values SHALL equal total_errors.
        """
        mock_task_data = {
            'task_id': 'prop_test_task_2',
            'homework_items': [
                {
                    'homework_id': f'hw_{i}',
                    'book_name': sample['book_name'],
                    'page_num': sample['page_num'],
                    'subject_id': sample['subject_id'],
                    'status': 'completed',
                    'evaluation': {
                        'total_questions': 10,
                        'errors': [
                            {
                                'question_index': sample['question_index'],
                                'error_type': sample['error_type'],
                                'ai_answer': sample['ai_answer'],
                                'expected_answer': sample['expected_answer']
                            }
                        ]
                    }
                }
                for i, sample in enumerate(error_samples)
            ]
        }
        
        with patch.object(AIAnalysisService, '_load_task', return_value=mock_task_data):
            result = AIAnalysisService.get_quick_stats('prop_test_task_2')
        
        # 验证错误类型分布之和等于总错误数
        distribution_sum = sum(result['error_type_distribution'].values())
        assert distribution_sum == result['total_errors'], \
            f"Distribution sum {distribution_sum} != total_errors {result['total_errors']}"


class TestClusterProperties:
    """
    属性测试：聚类完整性
    Feature: ai-analysis-enhancement, Property 6: Cluster Sample Count Consistency
    Validates: Requirements 2.1, 2.4
    """
    
    @given(error_samples=error_samples_list_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_cluster_samples_sum_to_total(self, error_samples):
        """
        Feature: ai-analysis-enhancement, Property 6: Cluster Sample Count Consistency
        Validates: Requirements 2.1, 2.4
        
        Property: For any list of error samples, the sum of all cluster sample_counts
        SHALL equal the total number of error samples.
        """
        clusters = AIAnalysisService._generate_quick_clusters(error_samples)
        
        # 验证聚类样本数之和等于总样本数
        cluster_sum = sum(c['sample_count'] for c in clusters)
        assert cluster_sum == len(error_samples), \
            f"Cluster sum {cluster_sum} != total samples {len(error_samples)}"
    
    @given(error_samples=error_samples_list_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_clusters_sorted_by_count_descending(self, error_samples):
        """
        Feature: ai-analysis-enhancement, Property 7: Top 5 Clusters Ordering
        Validates: Requirements 2.5
        
        Property: Clusters SHALL be sorted by sample_count in descending order.
        """
        clusters = AIAnalysisService._generate_quick_clusters(error_samples)
        
        if len(clusters) > 1:
            counts = [c['sample_count'] for c in clusters]
            assert counts == sorted(counts, reverse=True), \
                f"Clusters not sorted by count: {counts}"


class TestCacheProperties:
    """
    属性测试：缓存一致性
    Feature: ai-analysis-enhancement, Property 3: Cache Hash Consistency
    Validates: Requirements 15.3
    """
    
    @given(
        data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'),
            values=st.one_of(st.integers(), st.text(max_size=50), st.booleans()),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_hash_deterministic(self, data):
        """
        Feature: ai-analysis-enhancement, Property 3: Cache Hash Consistency
        Validates: Requirements 15.3
        
        Property: For any data, computing the hash multiple times SHALL produce
        the same result.
        """
        hash1 = AIAnalysisService._compute_data_hash(data)
        hash2 = AIAnalysisService._compute_data_hash(data)
        hash3 = AIAnalysisService._compute_data_hash(data)
        
        assert hash1 == hash2 == hash3, \
            f"Hash not deterministic: {hash1}, {hash2}, {hash3}"
    
    @given(
        data1=st.dictionaries(
            keys=st.text(min_size=1, max_size=10, alphabet='abc'),
            values=st.integers(min_value=0, max_value=100),
            min_size=1,
            max_size=5
        ),
        data2=st.dictionaries(
            keys=st.text(min_size=1, max_size=10, alphabet='xyz'),
            values=st.integers(min_value=101, max_value=200),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_different_data_different_hash(self, data1, data2):
        """
        Feature: ai-analysis-enhancement, Property 3: Cache Hash Consistency
        Validates: Requirements 15.3
        
        Property: For different data, the hash SHALL (almost always) be different.
        """
        if data1 != data2:
            hash1 = AIAnalysisService._compute_data_hash(data1)
            hash2 = AIAnalysisService._compute_data_hash(data2)
            
            # 不同数据应该产生不同哈希（极小概率碰撞）
            assert hash1 != hash2, \
                f"Different data produced same hash: {data1} vs {data2}"


class TestAnomalyDetectionProperties:
    """
    属性测试：异常检测
    Feature: ai-analysis-enhancement, Property 5: Inconsistency Rate Calculation
    Validates: Requirements 9.2
    """
    
    @given(
        correct_count=st.integers(min_value=1, max_value=50),
        incorrect_count=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100)
    def test_inconsistency_rate_calculation(self, correct_count, incorrect_count):
        """
        Feature: ai-analysis-enhancement, Property 5: Inconsistency Rate Calculation
        Validates: Requirements 9.2
        
        Property: For any set of correct and incorrect cases, the inconsistency_rate
        SHALL equal incorrect_count / (correct_count + incorrect_count).
        """
        total = correct_count + incorrect_count
        expected_rate = incorrect_count / total
        
        # 创建模拟数据
        mock_task_data = {
            'task_id': 'anomaly_test',
            'homework_items': []
        }
        
        # 添加正确案例
        for i in range(correct_count):
            mock_task_data['homework_items'].append({
                'homework_id': f'hw_correct_{i}',
                'status': 'completed',
                'evaluation': {
                    'questions': [
                        {'question_index': 1, 'base_user': 'test_answer', 'is_correct': True, 'ai_answer': 'A', 'expected_answer': 'A'}
                    ]
                }
            })
        
        # 添加错误案例
        for i in range(incorrect_count):
            mock_task_data['homework_items'].append({
                'homework_id': f'hw_incorrect_{i}',
                'status': 'completed',
                'evaluation': {
                    'questions': [
                        {'question_index': 1, 'base_user': 'test_answer', 'is_correct': False, 'ai_answer': 'A', 'expected_answer': 'A'}
                    ]
                }
            })
        
        with patch.object(AIAnalysisService, '_load_task', return_value=mock_task_data):
            anomalies = AIAnalysisService.detect_anomalies('anomaly_test')
        
        # 查找批改不一致异常
        inconsistent = [a for a in anomalies if a['anomaly_type'] == 'inconsistent_grading']
        
        if inconsistent:
            anomaly = inconsistent[0]
            actual_rate = anomaly['inconsistency_rate']
            
            # 验证不一致率计算正确（允许小数精度误差）
            assert abs(actual_rate - expected_rate) < 0.001, \
                f"Expected rate {expected_rate:.4f}, got {actual_rate:.4f}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
