"""
智能发布作业 API 路由
（页面已整合到自动化模拟页面）
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from services.smart_publish_service import SmartPublishService
from services.database_service import DatabaseService
from services.rfid_simulator_service import rfid_simulator_service

logger = logging.getLogger(__name__)

smart_publish_bp = Blueprint('smart_publish', __name__)


@smart_publish_bp.route('/api/smart-publish/books', methods=['GET'])
def get_books():
    """获取书本列表"""
    try:
        result = SmartPublishService.get_books()
        return jsonify(result)
    except Exception as e:
        logger.error(f"[SmartPublish] 获取书本列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@smart_publish_bp.route('/api/smart-publish/teachers', methods=['GET'])
def get_teachers():
    """根据书本ID获取老师列表"""
    try:
        book_id = request.args.get('book_id', '')
        if not book_id:
            return jsonify({'success': False, 'error': '缺少 book_id 参数'})
        
        result = SmartPublishService.get_teachers_by_book(book_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"[SmartPublish] 获取老师列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@smart_publish_bp.route('/api/smart-publish/pages', methods=['GET'])
def get_pages():
    """获取书本页码列表"""
    try:
        book_id = request.args.get('book_id', '')
        if not book_id:
            return jsonify({'success': False, 'error': '缺少 book_id 参数'})
        
        result = SmartPublishService.get_book_pages(book_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"[SmartPublish] 获取页码列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@smart_publish_bp.route('/api/smart-publish/publish', methods=['POST'])
def publish():
    """一键发布作业（发布成功后自动触发提交流程）"""
    try:
        data = request.get_json() or {}
        book_id = data.get('book_id', '')
        teacher_id = data.get('teacher_id', '')
        class_id = data.get('class_id', '')
        pages = data.get('pages', '')
        auto_submit = data.get('auto_submit', True)  # 默认自动提交
        
        # 1. 发布作业
        result = SmartPublishService.publish(book_id, teacher_id, class_id, pages)
        
        if not result.get('success'):
            return jsonify(result)
        
        # 2. 发布成功后自动触发提交流程
        submit_triggered = False
        submit_error = None
        
        if auto_submit:
            try:
                submit_triggered = _trigger_submit_workflow(book_id, class_id)
            except Exception as e:
                submit_error = str(e)
                logger.error(f"[SmartPublish] 触发提交流程失败: {e}")
        
        # 在返回数据中附加提交状态
        result['data']['submit_triggered'] = submit_triggered
        if submit_error:
            result['data']['submit_error'] = submit_error
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"[SmartPublish] 发布失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


def _trigger_submit_workflow(book_id: str, class_id: str) -> bool:
    """发布成功后触发提交作业流程"""
    # 1. 检查 ADB 客户端连接
    ws = rfid_simulator_service.get_active_websocket()
    if not ws:
        logger.warning("[SmartPublish] 没有 ADB 客户端连接，跳过自动提交")
        return False
    
    # 2. 查询班级学生（复用 nfc_api 的查询逻辑）
    sql = """
        SELECT s.id, s.name, s.stu_num,
               br.rfid_no,
               s.sub_representative
        FROM zp_bind_rfid br
        JOIN zp_student s ON br.student_id = s.id
        WHERE br.book_id = %s AND s.class_id = %s
              AND br.rfid_no IS NOT NULL AND br.rfid_no != ''
        ORDER BY 
            CASE WHEN s.sub_representative IS NOT NULL AND s.sub_representative != '' THEN 0 ELSE 1 END,
            s.stu_num, s.name
    """
    rows = DatabaseService.execute_query(sql, (book_id, class_id))
    
    if not rows:
        logger.warning("[SmartPublish] 没有找到有 RFID 的学生，跳过自动提交")
        return False
    
    # 3. 分离课代表和普通学生
    representative = None
    students = []
    
    for row in rows:
        sub_rep = row.get('sub_representative')
        is_rep = sub_rep is not None and sub_rep != ''
        
        student_data = {
            'name': row['name'],
            'rfid_no': row['rfid_no']
        }
        
        if is_rep and representative is None:
            representative = student_data
        else:
            students.append(student_data)
    
    # 4. 发送 run_workflow 给 ADB 客户端
    ws.send(json.dumps({
        'type': 'run_workflow',
        'workflow_id': 'submit_homework',
        'students': students,
        'representative': representative,
        'photo_interval': 2,
        'enable_double_page': True,
        'timestamp': datetime.now().isoformat()
    }))
    
    total = len(students) + (1 if representative else 0)
    rfid_simulator_service._add_log('info', f'发布成功，自动触发提交流程，学生数: {total}')
    logger.info(f"[SmartPublish] 自动触发提交流程，课代表: {representative is not None}，学生: {len(students)}")
    
    return True


@smart_publish_bp.route('/api/smart-publish/history', methods=['GET'])
def get_history():
    """获取发布历史"""
    try:
        limit = request.args.get('limit', 20, type=int)
        result = SmartPublishService.get_history(limit)
        return jsonify(result)
    except Exception as e:
        logger.error(f"[SmartPublish] 获取历史失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@smart_publish_bp.route('/api/smart-publish/config', methods=['GET'])
def get_config():
    """获取配置"""
    try:
        config = SmartPublishService.get_config()
        return jsonify({'success': True, 'data': config})
    except Exception as e:
        logger.error(f"[SmartPublish] 获取配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
