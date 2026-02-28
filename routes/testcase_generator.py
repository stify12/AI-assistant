"""
测试用例生成路由模块
AI 自动生成基准效果
"""
import json
from flask import Blueprint, request, jsonify, render_template
from services.testcase_generator_service import (
    TestcaseGeneratorService, 
    MATH_TEMPLATES, 
    TEMPLATE_COMBINATIONS
)

testcase_generator_bp = Blueprint('testcase_generator', __name__)


@testcase_generator_bp.route('/testcase-generator')
def testcase_generator_page():
    """测试用例生成页面"""
    return render_template('testcase-generator.html')


@testcase_generator_bp.route('/api/testcase/questions', methods=['GET'])
def get_questions():
    """获取指定页码的题目结构"""
    book_id = request.args.get('book_id')
    page_num = request.args.get('page_num', type=int)
    
    if not book_id or page_num is None:
        return jsonify({'success': False, 'error': '缺少必要参数'})
    
    result = TestcaseGeneratorService.get_questions_from_datavalue(book_id, page_num)
    return jsonify(result)


@testcase_generator_bp.route('/api/testcase/scenarios', methods=['GET'])
def get_scenarios():
    """获取默认测试场景配置"""
    subject_id = request.args.get('subject_id', 2, type=int)
    result = TestcaseGeneratorService.get_default_scenarios(subject_id)
    return jsonify(result)


@testcase_generator_bp.route('/api/testcase/generate', methods=['POST'])
def generate_testcases():
    """生成基准效果（单页，每题并行）"""
    try:
        from routes.auth import get_current_user_id
        user_id = get_current_user_id()
    except:
        user_id = None
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'})
    
    questions = data.get('questions', [])
    selected_templates = data.get('selected_templates', [])
    template_ratios = data.get('template_ratios', {})
    
    if not questions:
        return jsonify({'success': False, 'error': '题目列表为空'})
    
    if not selected_templates:
        return jsonify({'success': False, 'error': '未选择测试场景'})
    
    result = TestcaseGeneratorService.generate_base_effects(
        questions=questions,
        selected_templates=selected_templates,
        template_ratios=template_ratios,
        user_id=user_id
    )
    
    return jsonify(result)


@testcase_generator_bp.route('/api/testcase/generate-batch', methods=['POST'])
def generate_batch():
    """多页并行生成基准效果"""
    try:
        from routes.auth import get_current_user_id
        user_id = get_current_user_id()
    except:
        user_id = None
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'})
    
    book_id = data.get('book_id')
    page_nums = data.get('page_nums', [])
    selected_templates = data.get('selected_templates', [])
    template_ratios = data.get('template_ratios', {})
    
    if not book_id:
        return jsonify({'success': False, 'error': '缺少书本ID'})
    if not page_nums:
        return jsonify({'success': False, 'error': '页码列表为空'})
    if not selected_templates:
        return jsonify({'success': False, 'error': '未选择测试场景'})
    
    result = TestcaseGeneratorService.generate_batch_pages(
        book_id=book_id,
        page_nums=page_nums,
        selected_templates=selected_templates,
        template_ratios=template_ratios,
        user_id=user_id
    )
    
    return jsonify(result)


@testcase_generator_bp.route('/api/testcase/save', methods=['POST'])
def save_dataset():
    """保存为数据集（支持多页）"""
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'})
    
    book_id = data.get('book_id')
    book_name = data.get('book_name', '')
    subject_id = data.get('subject_id', 2)
    page_num = data.get('page_num')
    pages = data.get('pages')  # 多页页码列表
    base_effects = data.get('base_effects', [])
    dataset_name = data.get('dataset_name')
    description = data.get('description')
    save_score = data.get('save_score', False)
    
    if not book_id:
        return jsonify({'success': False, 'error': '缺少书本ID'})
    
    if not pages and page_num is None:
        return jsonify({'success': False, 'error': '缺少页码信息'})
    
    if not base_effects:
        return jsonify({'success': False, 'error': '基准效果为空'})
    
    result = TestcaseGeneratorService.save_as_dataset(
        book_id=book_id,
        book_name=book_name,
        subject_id=subject_id,
        page_num=page_num,
        base_effects=base_effects,
        dataset_name=dataset_name,
        description=description,
        save_score=save_score,
        pages=pages
    )
    
    return jsonify(result)


@testcase_generator_bp.route('/api/testcase/regenerate-single', methods=['POST'])
def regenerate_single():
    """单题重新生成基准效果"""
    try:
        from routes.auth import get_current_user_id
        user_id = get_current_user_id()
    except:
        user_id = None
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'})
    
    question = data.get('question')
    template_id = data.get('template_id')
    
    if not question:
        return jsonify({'success': False, 'error': '缺少题目信息'})
    if not template_id:
        return jsonify({'success': False, 'error': '缺少模板ID'})
    
    result = TestcaseGeneratorService.regenerate_single_effect(
        question=question,
        template_id=template_id,
        user_id=user_id
    )
    
    return jsonify(result)


@testcase_generator_bp.route('/api/testcase/templates', methods=['GET'])
def get_templates():
    """获取所有模板配置"""
    return jsonify({
        'success': True,
        'data': {
            'templates': MATH_TEMPLATES,
            'combinations': TEMPLATE_COMBINATIONS
        }
    })
