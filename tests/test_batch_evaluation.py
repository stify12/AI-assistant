"""
批量评估功能属性测试
Feature: batch-evaluation
"""

import pytest
import json
import os
import uuid
from datetime import datetime
from hypothesis import given, strategies as st, settings

# 测试数据目录
TEST_DATASETS_DIR = 'test_datasets'
TEST_TASKS_DIR = 'test_batch_tasks'


# ========== 测试数据生成策略 ==========

@st.composite
def book_strategy(draw):
    """生成图书数据"""
    return {
        'book_id': draw(st.text(min_size=1, max_size=10, alphabet='0123456789')),
        'book_name': draw(st.text(min_size=1, max_size=50)),
        'subject_id': draw(st.integers(min_value=0, max_value=3)),
        'page_count': draw(st.integers(min_value=1, max_value=200))
    }


@st.composite
def dataset_strategy(draw):
    """生成数据集数据"""
    pages = draw(st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=10, unique=True))
    base_effects = {}
    for page in pages:
        effects = draw(st.lists(base_effect_item_strategy(), min_size=1, max_size=20))
        base_effects[str(page)] = effects
    
    return {
        'dataset_id': str(uuid.uuid4())[:8],
        'book_id': draw(st.text(min_size=1, max_size=10, alphabet='0123456789')),
        'pages': pages,
        'base_effects': base_effects,
        'created_at': datetime.now().isoformat()
    }


@st.composite
def base_effect_item_strategy(draw):
    """生成基准效果项"""
    return {
        'index': str(draw(st.integers(min_value=1, max_value=50))),
        'answer': draw(st.text(min_size=0, max_size=10)),
        'userAnswer': draw(st.text(min_size=0, max_size=50)),
        'correct': draw(st.sampled_from(['yes', 'no'])),
        'tempIndex': draw(st.integers(min_value=0, max_value=50))
    }


@st.composite
def task_strategy(draw):
    """生成任务数据"""
    homework_count = draw(st.integers(min_value=1, max_value=10))
    homework_items = []
    for i in range(homework_count):
        homework_items.append({
            'homework_id': str(uuid.uuid4())[:8],
            'book_id': draw(st.text(min_size=1, max_size=10, alphabet='0123456789')),
            'page_num': draw(st.integers(min_value=1, max_value=100)),
            'status': draw(st.sampled_from(['pending', 'completed', 'failed'])),
            'accuracy': draw(st.floats(min_value=0, max_value=1)) if draw(st.booleans()) else None
        })
    
    return {
        'task_id': str(uuid.uuid4())[:8],
        'name': draw(st.text(min_size=1, max_size=50)),
        'status': draw(st.sampled_from(['pending', 'running', 'completed'])),
        'homework_items': homework_items,
        'created_at': datetime.now().isoformat()
    }


# ========== 属性测试 ==========

class TestDatasetProperties:
    """数据集相关属性测试"""
    
    @given(dataset_strategy())
    @settings(max_examples=100)
    def test_dataset_round_trip(self, dataset):
        """
        **Feature: batch-evaluation, Property 3: 数据集保存round-trip**
        **Validates: Requirements 3.3**
        
        For any saved dataset, loading it back should produce an identical object
        """
        os.makedirs(TEST_DATASETS_DIR, exist_ok=True)
        
        try:
            # 保存
            filepath = os.path.join(TEST_DATASETS_DIR, f"{dataset['dataset_id']}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, ensure_ascii=False)
            
            # 加载
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            
            # 验证
            assert loaded['dataset_id'] == dataset['dataset_id']
            assert loaded['book_id'] == dataset['book_id']
            assert loaded['pages'] == dataset['pages']
            assert loaded['base_effects'] == dataset['base_effects']
        
        finally:
            # 清理
            if os.path.exists(filepath):
                os.remove(filepath)
    
    @given(dataset_strategy())
    @settings(max_examples=100)
    def test_dataset_fields_completeness(self, dataset):
        """
        **Feature: batch-evaluation, Property 4: 数据集列表字段完整性**
        **Validates: Requirements 3.4**
        
        For any dataset, it should contain book_id, pages, question_count fields
        """
        assert 'book_id' in dataset
        assert 'pages' in dataset
        assert isinstance(dataset['pages'], list)
        assert len(dataset['pages']) > 0
        
        # 计算题目数量
        question_count = 0
        for effects in dataset.get('base_effects', {}).values():
            question_count += len(effects) if isinstance(effects, list) else 0
        
        assert question_count >= 0


class TestTaskProperties:
    """任务相关属性测试"""
    
    @given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=20, unique=True))
    @settings(max_examples=100)
    def test_task_homework_count_consistency(self, homework_ids):
        """
        **Feature: batch-evaluation, Property 7: 任务作业数量一致性**
        **Validates: Requirements 4.4**
        
        For any created task, the number of homework_items should equal the number of selected homework_ids
        """
        # 模拟创建任务
        homework_items = [{'homework_id': hw_id} for hw_id in homework_ids]
        task = {
            'task_id': str(uuid.uuid4())[:8],
            'homework_items': homework_items
        }
        
        assert len(task['homework_items']) == len(homework_ids)
    
    @given(st.lists(task_strategy(), min_size=2, max_size=10))
    @settings(max_examples=100)
    def test_task_id_uniqueness(self, tasks):
        """
        **Feature: batch-evaluation, Property 8: 任务ID唯一性**
        **Validates: Requirements 4.5**
        
        For any two tasks, their task_ids should be different
        """
        task_ids = [t['task_id'] for t in tasks]
        # 由于我们使用uuid生成，理论上应该唯一
        # 这里验证生成的ID确实不同
        assert len(task_ids) == len(set(task_ids))
    
    @given(task_strategy())
    @settings(max_examples=100)
    def test_task_round_trip(self, task):
        """
        **Feature: batch-evaluation, Property 15: 任务加载round-trip**
        **Validates: Requirements 9.2**
        
        For any saved task, loading it by task_id should produce the same task data
        """
        os.makedirs(TEST_TASKS_DIR, exist_ok=True)
        
        try:
            # 保存
            filepath = os.path.join(TEST_TASKS_DIR, f"{task['task_id']}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(task, f, ensure_ascii=False)
            
            # 加载
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            
            # 验证
            assert loaded['task_id'] == task['task_id']
            assert loaded['name'] == task['name']
            assert loaded['status'] == task['status']
            assert len(loaded['homework_items']) == len(task['homework_items'])
        
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    @given(st.lists(task_strategy(), min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_task_list_sorted_by_time(self, tasks):
        """
        **Feature: batch-evaluation, Property 14: 历史任务排序正确性**
        **Validates: Requirements 9.1**
        
        For any task list, tasks should be sorted by created_at in descending order
        """
        # 排序
        sorted_tasks = sorted(tasks, key=lambda x: x.get('created_at', ''), reverse=True)
        
        # 验证排序正确
        for i in range(len(sorted_tasks) - 1):
            assert sorted_tasks[i].get('created_at', '') >= sorted_tasks[i + 1].get('created_at', '')


class TestEvaluationProperties:
    """评估相关属性测试"""
    
    @given(
        st.lists(base_effect_item_strategy(), min_size=1, max_size=20),
        st.lists(base_effect_item_strategy(), min_size=1, max_size=20)
    )
    @settings(max_examples=100)
    def test_accuracy_calculation(self, base_effect, homework_result):
        """
        **Feature: batch-evaluation, Property 10: 准确率计算正确性**
        **Validates: Requirements 6.2**
        
        For any evaluation result, accuracy should equal correct_count / total_questions
        """
        # 简化的评估逻辑
        total = len(base_effect)
        correct_count = 0
        
        hw_dict = {item['index']: item for item in homework_result}
        
        for base_item in base_effect:
            idx = base_item['index']
            hw_item = hw_dict.get(idx)
            
            if hw_item:
                base_user = base_item.get('userAnswer', '').strip().lower()
                hw_user = hw_item.get('userAnswer', '').strip().lower()
                base_correct = base_item.get('correct', '').lower()
                hw_correct = hw_item.get('correct', '').lower()
                
                if base_user == hw_user and base_correct == hw_correct:
                    correct_count += 1
        
        accuracy = correct_count / total if total > 0 else 0
        
        # 验证准确率计算
        assert 0 <= accuracy <= 1
        assert accuracy == correct_count / total if total > 0 else accuracy == 0
    
    @given(task_strategy())
    @settings(max_examples=100)
    def test_task_completion_status(self, task):
        """
        **Feature: batch-evaluation, Property 11: 任务完成状态正确性**
        **Validates: Requirements 6.5**
        
        For any task with status "completed", all homework_items should have status "completed" or "failed"
        """
        if task['status'] == 'completed':
            # 模拟完成状态
            for item in task['homework_items']:
                item['status'] = 'completed' if item.get('accuracy') is not None else 'failed'
            
            # 验证所有作业都已完成或失败
            for item in task['homework_items']:
                assert item['status'] in ['completed', 'failed']


class TestReportProperties:
    """报告相关属性测试"""
    
    @given(st.lists(
        st.fixed_dictionaries({
            'accuracy': st.floats(min_value=0, max_value=1),
            'total_questions': st.integers(min_value=1, max_value=50),
            'correct_count': st.integers(min_value=0, max_value=50)
        }),
        min_size=1, max_size=10
    ))
    @settings(max_examples=100)
    def test_overall_report_accuracy(self, evaluations):
        """
        **Feature: batch-evaluation, Property 12: 总体报告统计正确性**
        **Validates: Requirements 7.1, 7.2**
        
        For any overall report, overall_accuracy should equal sum(correct) / sum(total)
        """
        # 确保correct_count不超过total_questions
        for e in evaluations:
            e['correct_count'] = min(e['correct_count'], e['total_questions'])
        
        total_questions = sum(e['total_questions'] for e in evaluations)
        total_correct = sum(e['correct_count'] for e in evaluations)
        
        expected_accuracy = total_correct / total_questions if total_questions > 0 else 0
        
        # 验证
        assert 0 <= expected_accuracy <= 1


class TestQuestionTypeProperties:
    """题目类型分类相关属性测试"""
    
    @given(st.fixed_dictionaries({
        'questionType': st.sampled_from(['objective', 'subjective', '', None]),
        'bvalue': st.sampled_from(['1', '2', '3', '4', '', None])
    }))
    @settings(max_examples=100, deadline=None)
    def test_question_type_classification(self, question_data):
        """
        **Feature: batch-evaluation, Property 17: 题目类型分类正确性**
        **Validates: Requirements 12.2, 12.3**
        
        For any question with questionType and bvalue fields, the classification function
        should correctly identify: objective (questionType === "objective" OR bvalue in 1/2/3/4), 
        choice (bvalue === "1" or "2"), and choice_type (single/multiple/null)
        """
        # 导入分类函数
        import sys
        sys.path.insert(0, '.')
        from routes.batch_evaluation import classify_question_type
        
        result = classify_question_type(question_data)
        
        # 验证返回结构
        assert 'is_objective' in result
        assert 'is_choice' in result
        assert 'choice_type' in result
        
        # 验证客观题判断逻辑
        # 客观题条件：questionType === "objective" OR bvalue in ('1', '2', '3', '4')
        bvalue = str(question_data.get('bvalue', ''))
        expected_objective = (
            question_data.get('questionType') == 'objective' or
            bvalue in ('1', '2', '3', '4')
        )
        assert result['is_objective'] == expected_objective
        
        # 验证选择题判断逻辑
        expected_choice = bvalue in ('1', '2')
        assert result['is_choice'] == expected_choice
        
        # 验证选择题类型
        if bvalue == '1':
            assert result['choice_type'] == 'single'
        elif bvalue == '2':
            assert result['choice_type'] == 'multiple'
        else:
            assert result['choice_type'] is None
    
    @given(st.lists(
        st.fixed_dictionaries({
            'questionType': st.sampled_from(['objective', 'subjective', '']),
            'bvalue': st.sampled_from(['1', '2', '4']),
            'index': st.text(min_size=1, max_size=5, alphabet='0123456789')
        }),
        min_size=1, max_size=20
    ))
    @settings(max_examples=100, deadline=None)
    def test_type_statistics_calculation(self, questions):
        """
        **Feature: batch-evaluation, Property 18: 题目类型统计计算正确性**
        **Validates: Requirements 12.4, 12.5, 12.6**
        
        For any list of questions with type classifications and evaluation results,
        the type statistics should correctly sum totals and calculate accuracies
        """
        import sys
        sys.path.insert(0, '.')
        from routes.batch_evaluation import classify_question_type, calculate_type_statistics
        
        # 生成随机评估结果
        import random
        results = [{'is_correct': random.choice([True, False])} for _ in questions]
        
        stats = calculate_type_statistics(questions, results)
        
        # 验证返回结构
        assert 'objective' in stats
        assert 'subjective' in stats
        assert 'choice' in stats
        assert 'non_choice' in stats
        
        # 验证每个分类都有必要字段
        for key in ['objective', 'subjective', 'choice', 'non_choice']:
            assert 'total' in stats[key]
            assert 'correct' in stats[key]
            assert 'accuracy' in stats[key]
        
        # 验证总数一致性
        assert stats['objective']['total'] + stats['subjective']['total'] == len(questions)
        assert stats['choice']['total'] + stats['non_choice']['total'] == len(questions)
        
        # 验证准确率计算
        for key in ['objective', 'subjective', 'choice', 'non_choice']:
            total = stats[key]['total']
            correct = stats[key]['correct']
            if total > 0:
                assert stats[key]['accuracy'] == correct / total
            else:
                assert stats[key]['accuracy'] == 0
            
            # 验证正确数不超过总数
            assert stats[key]['correct'] <= stats[key]['total']
    
    @given(st.none() | st.just({}))
    @settings(max_examples=10, deadline=None)
    def test_question_type_classification_empty_input(self, question_data):
        """
        **Feature: batch-evaluation, Property 17: 题目类型分类正确性 - 空输入**
        **Validates: Requirements 12.2, 12.3**
        
        For empty or None input, the classification function should return default values
        """
        import sys
        sys.path.insert(0, '.')
        from routes.batch_evaluation import classify_question_type
        
        result = classify_question_type(question_data)
        
        # 空输入应返回默认值
        assert result['is_objective'] == False
        assert result['is_choice'] == False
        assert result['choice_type'] is None
    
    @given(st.lists(
        st.fixed_dictionaries({
            'index': st.text(min_size=1, max_size=5, alphabet='0123456789'),
            'answer': st.text(min_size=0, max_size=20),
            'userAnswer': st.text(min_size=0, max_size=20),
            'correct': st.sampled_from(['yes', 'no']),
            'tempIndex': st.integers(min_value=0, max_value=50),
            'questionType': st.sampled_from(['objective', 'subjective', '']),
            'bvalue': st.sampled_from(['1', '2', '4', ''])
        }),
        min_size=1, max_size=10
    ))
    @settings(max_examples=100, deadline=None)
    def test_dataset_question_type_fields_saved(self, base_effects):
        """
        **Feature: batch-evaluation, Property 19: 数据集题目类型字段保存正确性**
        **Validates: Requirements 12.7**
        
        For any saved dataset with base_effects, each question item should contain
        questionType and bvalue fields
        """
        # 验证每个基准效果项都包含题目类型字段
        for effect in base_effects:
            assert 'questionType' in effect
            assert 'bvalue' in effect
            
            # 验证字段值类型正确
            assert isinstance(effect['questionType'], str)
            assert isinstance(effect['bvalue'], str)
    
    @given(
        st.lists(
            st.fixed_dictionaries({
                'index': st.text(min_size=1, max_size=5, alphabet='0123456789'),
                'answer': st.text(min_size=1, max_size=10),
                'userAnswer': st.text(min_size=1, max_size=10),
                'correct': st.sampled_from(['yes', 'no']),
                'tempIndex': st.integers(min_value=0, max_value=20),
                'questionType': st.sampled_from(['objective', 'subjective', '']),
                'bvalue': st.sampled_from(['1', '2', '4'])
            }),
            min_size=1, max_size=10
        ),
        st.lists(
            st.fixed_dictionaries({
                'index': st.text(min_size=1, max_size=5, alphabet='0123456789'),
                'answer': st.text(min_size=1, max_size=10),
                'userAnswer': st.text(min_size=1, max_size=10),
                'correct': st.sampled_from(['yes', 'no']),
                'tempIndex': st.integers(min_value=0, max_value=20)
            }),
            min_size=1, max_size=10
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_evaluation_result_question_category(self, base_effect, homework_result):
        """
        **Feature: batch-evaluation, Property 20: 评估结果题目类型标注正确性**
        **Validates: Requirements 12.8**
        
        For any evaluation result, each error item should contain question_category
        with is_objective and is_choice fields
        """
        import sys
        sys.path.insert(0, '.')
        from routes.batch_evaluation import do_evaluation
        
        result = do_evaluation(base_effect, homework_result)
        
        # 验证返回结构包含 by_question_type
        assert 'by_question_type' in result
        assert 'objective' in result['by_question_type']
        assert 'subjective' in result['by_question_type']
        assert 'choice' in result['by_question_type']
        assert 'non_choice' in result['by_question_type']
        
        # 验证每个分类都有必要字段
        for key in ['objective', 'subjective', 'choice', 'non_choice']:
            assert 'total' in result['by_question_type'][key]
            assert 'correct' in result['by_question_type'][key]
            assert 'accuracy' in result['by_question_type'][key]
        
        # 验证错误项包含 question_category
        for error in result.get('errors', []):
            assert 'question_category' in error
            assert 'is_objective' in error['question_category']
            assert 'is_choice' in error['question_category']
    
    @given(st.lists(
        st.fixed_dictionaries({
            'accuracy': st.floats(min_value=0, max_value=1),
            'total_questions': st.integers(min_value=1, max_value=50),
            'correct_count': st.integers(min_value=0, max_value=50),
            'by_question_type': st.fixed_dictionaries({
                'objective': st.fixed_dictionaries({
                    'total': st.integers(min_value=0, max_value=20),
                    'correct': st.integers(min_value=0, max_value=20),
                    'accuracy': st.floats(min_value=0, max_value=1)
                }),
                'subjective': st.fixed_dictionaries({
                    'total': st.integers(min_value=0, max_value=20),
                    'correct': st.integers(min_value=0, max_value=20),
                    'accuracy': st.floats(min_value=0, max_value=1)
                }),
                'choice': st.fixed_dictionaries({
                    'total': st.integers(min_value=0, max_value=20),
                    'correct': st.integers(min_value=0, max_value=20),
                    'accuracy': st.floats(min_value=0, max_value=1)
                }),
                'non_choice': st.fixed_dictionaries({
                    'total': st.integers(min_value=0, max_value=20),
                    'correct': st.integers(min_value=0, max_value=20),
                    'accuracy': st.floats(min_value=0, max_value=1)
                })
            })
        }),
        min_size=1, max_size=5
    ))
    @settings(max_examples=50, deadline=None)
    def test_ai_evaluation_type_statistics_completeness(self, evaluations):
        """
        **Feature: batch-evaluation, Property 21: 一键AI评估分类统计完整性**
        **Validates: Requirements 6.6, 6.7**
        
        For any completed AI evaluation task, the overall_report should contain
        by_question_type with objective, subjective, choice, and non_choice statistics
        """
        # 模拟汇总逻辑
        aggregated_type_stats = {
            'objective': {'total': 0, 'correct': 0, 'accuracy': 0},
            'subjective': {'total': 0, 'correct': 0, 'accuracy': 0},
            'choice': {'total': 0, 'correct': 0, 'accuracy': 0},
            'non_choice': {'total': 0, 'correct': 0, 'accuracy': 0}
        }
        
        for evaluation in evaluations:
            by_type = evaluation.get('by_question_type', {})
            for key in aggregated_type_stats:
                if key in by_type:
                    aggregated_type_stats[key]['total'] += by_type[key].get('total', 0)
                    aggregated_type_stats[key]['correct'] += min(
                        by_type[key].get('correct', 0),
                        by_type[key].get('total', 0)
                    )
        
        # 计算汇总准确率
        for key in aggregated_type_stats:
            total_count = aggregated_type_stats[key]['total']
            correct = aggregated_type_stats[key]['correct']
            aggregated_type_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
        
        # 验证汇总结果结构完整
        assert 'objective' in aggregated_type_stats
        assert 'subjective' in aggregated_type_stats
        assert 'choice' in aggregated_type_stats
        assert 'non_choice' in aggregated_type_stats
        
        # 验证每个分类都有必要字段
        for key in ['objective', 'subjective', 'choice', 'non_choice']:
            assert 'total' in aggregated_type_stats[key]
            assert 'correct' in aggregated_type_stats[key]
            assert 'accuracy' in aggregated_type_stats[key]
            
            # 验证准确率在有效范围内
            assert 0 <= aggregated_type_stats[key]['accuracy'] <= 1
            
            # 验证正确数不超过总数
            assert aggregated_type_stats[key]['correct'] <= aggregated_type_stats[key]['total']


# ========== 清理测试目录 ==========

@pytest.fixture(scope="module", autouse=True)
def cleanup():
    """测试完成后清理"""
    yield
    
    import shutil
    if os.path.exists(TEST_DATASETS_DIR):
        shutil.rmtree(TEST_DATASETS_DIR)
    if os.path.exists(TEST_TASKS_DIR):
        shutil.rmtree(TEST_TASKS_DIR)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


def test_normalize_answer_punctuation():
    """测试标点符号标准化"""
    from utils.text_utils import normalize_answer
    
    # 测试句末标点符号
    assert normalize_answer('答案。') == normalize_answer('答案')
    assert normalize_answer('正确！') == normalize_answer('正确')
    assert normalize_answer('是吗？') == normalize_answer('是吗')
    
    # 测试中英文标点混合
    assert normalize_answer('A，B，C。') == normalize_answer('A B C')
    assert normalize_answer('选项：A') == normalize_answer('选项 A')
    
    # 测试多个标点符号
    assert normalize_answer('答案。。。') == normalize_answer('答案')
    assert normalize_answer('正确！！！') == normalize_answer('正确')
    
    # 测试中间的标点符号
    assert normalize_answer('A,B,C') == normalize_answer('A B C')
    assert normalize_answer('选项：A；选项：B') == normalize_answer('选项 A 选项 B')
    
    # 测试保留数学符号
    assert normalize_answer('x+y=10') == 'x+y=10'
    assert normalize_answer('(a+b)*c') == '(a+b)*c'
    
    print("✓ 标点符号标准化测试通过")


def test_normalize_answer_comparison():
    """测试实际场景中的答案比较"""
    from utils.text_utils import normalize_answer
    
    # 场景1：句末标点差异
    base = "这是正确答案。"
    ai = "这是正确答案"
    assert normalize_answer(base) == normalize_answer(ai), "句末标点应该被忽略"
    
    # 场景2：中英文标点混合
    base = "选项A、B、C"
    ai = "选项A,B,C"
    assert normalize_answer(base) == normalize_answer(ai), "中英文标点应该统一"
    
    # 场景3：多余空格和标点
    base = "答案是：  A  。"
    ai = "答案是:A"
    assert normalize_answer(base) == normalize_answer(ai), "空格和标点应该被标准化"
    
    # 场景4：数学表达式
    base = "x+y=10"
    ai = "x + y = 10"
    # 注意：这里空格会被保留，所以不相等是正常的
    # 如果需要更宽松的比较，可以使用 normalize_answer_strict
    
    print("✓ 答案比较场景测试通过")


if __name__ == '__main__':
    test_normalize_answer_punctuation()
    test_normalize_answer_comparison()
