"""
NFC App API - 为 Android NFC 应用提供数据接口
"""
from flask import Blueprint, request, jsonify
from services.database_service import DatabaseService
import time
import json
import os
import hashlib

nfc_api_bp = Blueprint('nfc_api', __name__, url_prefix='/api/nfc')

db = DatabaseService()

# 文件缓存目录（多 worker 共享）
CACHE_DIR = '/tmp/nfc_cache'
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_path(key):
    """生成缓存文件路径"""
    safe_key = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{safe_key}.json")

def get_cached(key, ttl_seconds=300):
    """获取文件缓存"""
    try:
        path = _cache_path(key)
        if not os.path.exists(path):
            print(f"[NFC Cache] 缓存不存在: {key}")
            return None
        # 检查过期
        if time.time() - os.path.getmtime(path) > ttl_seconds:
            os.remove(path)
            print(f"[NFC Cache] 缓存过期: {key}")
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[NFC Cache] 命中缓存: {key}")
            return data
    except Exception as e:
        print(f"[NFC Cache] 读取失败: {key}, 错误: {e}")
        return None

def set_cached(key, value, ttl_seconds=300):
    """设置文件缓存"""
    try:
        path = _cache_path(key)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False)
        print(f"[NFC Cache] 写入缓存: {key} -> {path}")
    except Exception as e:
        print(f"[NFC Cache] 写入失败: {key}, 错误: {e}")


@nfc_api_bp.route('/ping', methods=['GET'])
def ping():
    """测试连接"""
    return jsonify({'success': True, 'message': 'pong'})


@nfc_api_bp.route('/grades', methods=['GET'])
def get_grades():
    """获取年级列表"""
    try:
        sql = "SELECT DISTINCT grade FROM zp_student WHERE grade > 0 ORDER BY grade"
        result = db.execute_query(sql)
        
        grade_map = {
            1: "一年级", 2: "二年级", 3: "三年级",
            4: "四年级", 5: "五年级", 6: "六年级",
            7: "七年级", 8: "八年级", 9: "九年级",
            10: "高一", 11: "高二", 12: "高三"
        }
        
        grades = []
        for row in result:
            grade_id = row['grade']
            grades.append({
                'id': grade_id,
                'name': grade_map.get(grade_id, f"{grade_id}年级")
            })
        
        return jsonify({'success': True, 'data': grades})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@nfc_api_bp.route('/teachers', methods=['GET'])
def get_teachers():
    """获取老师列表 - 带缓存"""
    try:
        # 老师列表变化少，缓存 10 分钟
        cache_key = "teachers_list"
        cached = get_cached(cache_key, ttl_seconds=600)
        if cached:
            return jsonify({'success': True, 'data': cached})
        
        sql = """
            SELECT id, teacher_name, subject_id 
            FROM zp_teacher 
            WHERE teacher_name IS NOT NULL AND teacher_name != ''
            ORDER BY teacher_name
            LIMIT 200
        """
        result = db.execute_query(sql)
        
        teachers = []
        for row in result:
            teachers.append({
                'id': row['id'],
                'name': row['teacher_name'],
                'subject_id': row.get('subject_id', 0)
            })
        
        set_cached(cache_key, teachers, ttl_seconds=600)
        return jsonify({'success': True, 'data': teachers})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@nfc_api_bp.route('/classes', methods=['GET'])
def get_classes():
    """获取班级列表（支持筛选）- 简化版，不统计 rfid_count"""
    try:
        grade = request.args.get('grade', type=int)
        teacher_id = request.args.get('teacher_id', type=int)
        keyword = request.args.get('keyword', '')
        
        # 缓存检查
        cache_key = f"classes_{grade}_{teacher_id}_{keyword}"
        cached = get_cached(cache_key, ttl_seconds=180)
        if cached:
            return jsonify({'success': True, 'data': cached})
        
        conditions = ["1=1"]
        params = []
        
        if grade and grade > 0:
            conditions.append("c.grade_id = %s")
            params.append(str(grade))
        if keyword:
            conditions.append("c.name LIKE %s")
            params.append(f"%{keyword}%")
        
        where_clause = " AND ".join(conditions)
        
        # 简化查询：只统计学生数，不统计 rfid_count（太慢）
        sql = f"""
            SELECT c.id, c.name, c.grade_id,
                   COUNT(s.id) as student_count
            FROM zp_class c
            LEFT JOIN zp_student s ON c.id = s.class_id
            WHERE {where_clause}
            GROUP BY c.id, c.name, c.grade_id
            HAVING student_count > 0
            ORDER BY c.grade_id, c.name
            LIMIT 100
        """
        
        result = db.execute_query(sql, params if params else None)
        
        classes = []
        for row in result:
            grade_id = row.get('grade_id')
            if isinstance(grade_id, str) and grade_id.isdigit():
                grade_id = int(grade_id)
            classes.append({
                'id': row['id'],
                'name': row['name'],
                'grade': grade_id,
                'student_count': row.get('student_count', 0),
                'rfid_count': 0  # 不再统计，由客户端缓存
            })
        
        set_cached(cache_key, classes, ttl_seconds=180)
        return jsonify({'success': True, 'data': classes})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@nfc_api_bp.route('/books', methods=['GET'])
def search_books():
    """搜索书本（支持科目筛选）- 带缓存"""
    try:
        keyword = request.args.get('keyword', '')
        subject_id = request.args.get('subject_id', type=int)
        
        # 缓存 3 分钟
        cache_key = f"books_{keyword}_{subject_id}"
        cached = get_cached(cache_key, ttl_seconds=180)
        if cached:
            return jsonify({'success': True, 'data': cached})
        
        conditions = ["status = 1"]
        params = []
        
        if keyword:
            conditions.append("(book_name LIKE %s OR book_sn LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if subject_id is not None:
            conditions.append("subject_id = %s")
            params.append(subject_id)
        
        where_clause = " AND ".join(conditions)
        
        sql = f"""
            SELECT id, book_sn, book_name, subject_id, grade_id, publishing
            FROM zp_make_book
            WHERE {where_clause}
            ORDER BY create_time DESC
            LIMIT 50
        """
        
        result = db.execute_query(sql, params if params else None)
        
        subject_map = {
            0: '英语', 1: '语文', 2: '数学',
            3: '物理', 4: '化学', 5: '生物', 6: '地理'
        }
        grade_map = {
            1: "一年级", 2: "二年级", 3: "三年级",
            4: "四年级", 5: "五年级", 6: "六年级",
            7: "七年级", 8: "八年级", 9: "九年级",
            10: "高一", 11: "高二", 12: "高三"
        }
        
        books = []
        for row in result:
            books.append({
                'id': row['id'],
                'book_sn': row.get('book_sn'),
                'book_name': row['book_name'],
                'subject_id': row.get('subject_id'),
                'subject_name': subject_map.get(row.get('subject_id'), ''),
                'grade_id': row.get('grade_id'),
                'grade_name': grade_map.get(row.get('grade_id'), ''),
                'publishing': row.get('publishing', '')
            })
        
        set_cached(cache_key, books, ttl_seconds=180)
        return jsonify({'success': True, 'data': books})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@nfc_api_bp.route('/book/<book_id>/classes', methods=['GET'])
def get_book_classes(book_id):
    """获取书本关联的班级列表"""
    try:
        sql = """
            SELECT c.id, c.name, c.grade_id,
                   COUNT(DISTINCT br.student_id) as student_count
            FROM zp_bind_rfid br
            JOIN zp_student s ON br.student_id = s.id
            JOIN zp_class c ON s.class_id = c.id
            WHERE br.book_id = %s AND br.rfid_no IS NOT NULL AND br.rfid_no != ''
            GROUP BY c.id, c.name, c.grade_id
            ORDER BY student_count DESC
        """
        
        result = db.execute_query(sql, (book_id,))
        
        grade_map = {
            1: "一年级", 2: "二年级", 3: "三年级",
            4: "四年级", 5: "五年级", 6: "六年级",
            7: "七年级", 8: "八年级", 9: "九年级",
            10: "高一", 11: "高二", 12: "高三"
        }
        
        classes = []
        for row in result:
            grade_id = row.get('grade_id')
            # grade_id 可能是字符串
            if isinstance(grade_id, str):
                grade_id = int(grade_id) if grade_id.isdigit() else 0
            classes.append({
                'id': str(row['id']),
                'name': row['name'],
                'grade_id': grade_id,
                'grade_name': grade_map.get(grade_id, ''),
                'student_count': row.get('student_count', 0)
            })
        
        return jsonify({'success': True, 'data': classes})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@nfc_api_bp.route('/book/<book_id>/class/<class_id>/students', methods=['GET'])
def get_book_class_students(book_id, class_id):
    """获取班级学生的书本RFID"""
    try:
        sql = """
            SELECT s.id, s.name, s.stu_num, s.sex,
                   c.name as class_name,
                   br.rfid_no,
                   s.sub_representative
            FROM zp_bind_rfid br
            JOIN zp_student s ON br.student_id = s.id
            JOIN zp_class c ON s.class_id = c.id
            WHERE br.book_id = %s AND s.class_id = %s
                  AND br.rfid_no IS NOT NULL AND br.rfid_no != ''
            ORDER BY 
                CASE WHEN s.sub_representative IS NOT NULL AND s.sub_representative != '' THEN 0 ELSE 1 END,
                s.stu_num, s.name
        """
        
        result = db.execute_query(sql, (book_id, class_id))
        
        subject_map = {
            '0': '英语', '1': '语文', '2': '数学',
            '3': '物理', '4': '化学', '5': '生物', '6': '地理'
        }
        
        students = []
        for row in result:
            sub_rep = row.get('sub_representative')
            is_representative = sub_rep is not None and sub_rep != ''
            
            students.append({
                'id': str(row['id']),
                'name': row['name'],
                'stu_num': row.get('stu_num'),
                'sex': row.get('sex', 0),
                'class_name': row.get('class_name'),
                'rfid_no': row.get('rfid_no'),
                'is_representative': is_representative,
                'subject_name': subject_map.get(str(sub_rep), '') if is_representative else None
            })
        
        return jsonify({'success': True, 'data': students})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@nfc_api_bp.route('/class/<int:class_id>/students', methods=['GET'])
def get_class_students(class_id):
    """获取班级学生及其 RFID，课代表优先排序 - 带缓存"""
    try:
        # 缓存 5 分钟
        cache_key = f"class_students_{class_id}"
        cached = get_cached(cache_key, ttl_seconds=300)
        if cached:
            return jsonify({'success': True, 'data': cached})
        
        sql = """
            SELECT s.id, s.name, s.stu_num, s.sex, s.class_id,
                   c.name as class_name,
                   b.rfid_no,
                   s.sub_representative
            FROM zp_student s
            LEFT JOIN zp_class c ON s.class_id = c.id
            LEFT JOIN zp_bind_rfid b ON s.id = b.student_id
            WHERE s.class_id = %s
            ORDER BY 
                CASE WHEN s.sub_representative IS NOT NULL AND s.sub_representative != '' THEN 0 ELSE 1 END,
                s.sub_representative,
                s.stu_num, s.name
        """
        
        result = db.execute_query(sql, (class_id,))
        
        # 学科映射
        subject_map = {
            '0': '英语', '1': '语文', '2': '数学',
            '3': '物理', '4': '化学', '5': '生物', '6': '地理'
        }
        
        students = []
        for row in result:
            sub_rep = row.get('sub_representative')
            is_representative = sub_rep is not None and sub_rep != ''
            subject_name = subject_map.get(str(sub_rep), '') if is_representative else None
            
            students.append({
                'id': row['id'],
                'name': row['name'],
                'stu_num': row.get('stu_num'),
                'sex': row.get('sex', 0),
                'class_id': row.get('class_id'),
                'class_name': row.get('class_name'),
                'rfid_no': row.get('rfid_no'),
                'is_representative': is_representative,
                'subject_id': sub_rep if is_representative else None,
                'subject_name': subject_name
            })
        
        set_cached(cache_key, students, ttl_seconds=300)
        return jsonify({'success': True, 'data': students})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
