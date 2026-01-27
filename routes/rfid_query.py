"""
RFID查询路由模块
提供RFID信息查询功能
"""
import json
from flask import Blueprint, request, jsonify
from services.database_service import DatabaseService

rfid_query_bp = Blueprint('rfid_query', __name__)

# 学科ID映射
SUBJECT_MAP = {
    0: '英语',
    1: '语文',
    2: '数学',
    3: '物理',
    4: '化学',
    5: '生物',
    6: '地理'
}

# 年级ID映射
GRADE_MAP = {
    1: '一年级', 2: '二年级', 3: '三年级',
    4: '四年级', 5: '五年级', 6: '六年级',
    7: '七年级', 8: '八年级', 9: '九年级',
    10: '高一', 11: '高二', 12: '高三'
}

# RFID类型映射
RFID_TYPE_MAP = {
    'H': '作业本',
    'P': '错题本'
}


@rfid_query_bp.route('/api/rfid/classmates', methods=['GET'])
def get_classmates():
    """获取班级同学列表"""
    class_id = request.args.get('class_id', '').strip()
    
    if not class_id:
        return jsonify({'success': False, 'error': '缺少班级ID'})
    
    try:
        sql = """
            SELECT s.id, s.name, s.sex, s.stu_num, s.grade,
                   c.name AS class_name
            FROM zp_student s
            LEFT JOIN zp_class c ON s.class_id = c.id
            WHERE s.class_id = %s
            ORDER BY s.stu_num, s.name
        """
        rows = DatabaseService.execute_query(sql, (class_id,))
        
        students = []
        for row in rows:
            students.append({
                'id': row['id'],
                'name': row['name'],
                'sex': '男' if row['sex'] == 1 else '女',
                'stu_num': row.get('stu_num', ''),
                'grade': row['grade'],
                'grade_name': GRADE_MAP.get(row['grade'], f"{row['grade']}年级"),
                'class_name': row.get('class_name', '')
            })
        
        return jsonify({
            'success': True,
            'data': students,
            'total': len(students)
        })
    
    except Exception as e:
        print(f"[GetClassmates] Error: {str(e)}")
        return jsonify({'success': False, 'error': f'查询失败: {str(e)}'})


@rfid_query_bp.route('/api/rfid/query', methods=['GET'])
def query_rfid():
    """查询RFID详细信息 - 优化版：单次联表查询"""
    rfid_no = request.args.get('rfid_no', '').strip()
    
    if not rfid_no:
        return jsonify({'success': False, 'error': '请输入RFID卡号'})
    
    try:
        result = {
            'rfid_no': rfid_no,
            'basic_info': None,
            'bind_info': None,
            'student_info': None,
            'book_info': None,
            'teacher_info': None,
            'school_info': None
        }
        
        # 单次联表查询获取所有信息
        main_sql = """
            SELECT 
                r.id AS rfid_id, r.rfid_no, r.school_id, r.valid_status,
                r.create_time AS rfid_create_time, r.update_time AS rfid_update_time,
                sch.school_name,
                b.id AS bind_id, b.student_id, b.subject_id, b.grade_id,
                b.book_id, b.rfid_type,
                b.create_time AS bind_create_time, b.update_time AS bind_update_time,
                st.id AS student_id_val, st.name AS student_name, st.sex, st.grade AS student_grade,
                st.class_id, st.stu_num, st.teacher_id,
                c.name AS class_name,
                bk.id AS book_id_val, bk.book_sn, bk.book_name, 
                bk.subject_id AS book_subject_id, bk.grade_id AS book_grade_id,
                bk.publishing
            FROM zp_rfid r
            LEFT JOIN zp_school sch ON r.school_id = sch.id
            LEFT JOIN zp_bind_rfid b ON r.rfid_no = b.rfid_no
            LEFT JOIN zp_student st ON b.student_id = st.id
            LEFT JOIN zp_class c ON st.class_id = c.id
            LEFT JOIN zp_make_book bk ON b.book_id = bk.id
            WHERE r.rfid_no = %s
            LIMIT 1
        """
        row = DatabaseService.execute_one(main_sql, (rfid_no,))
        
        if row:
            # 基础信息
            result['basic_info'] = {
                'id': row['rfid_id'],
                'rfid_no': row['rfid_no'],
                'school_id': row['school_id'],
                'school_name': row.get('school_name') or '未知学校',
                'valid_status': row['valid_status'],
                'valid_status_text': '有效' if row['valid_status'] == 1 else '无效',
                'create_time': row['rfid_create_time'].strftime('%Y-%m-%d %H:%M:%S') if row.get('rfid_create_time') else None,
                'update_time': row['rfid_update_time'].strftime('%Y-%m-%d %H:%M:%S') if row.get('rfid_update_time') else None
            }
            result['school_info'] = {
                'school_id': row['school_id'],
                'school_name': row.get('school_name') or '未知学校'
            }
            
            # 绑定信息
            if row.get('bind_id'):
                result['bind_info'] = {
                    'id': row['bind_id'],
                    'student_id': row['student_id'],
                    'subject_id': row['subject_id'],
                    'subject_name': SUBJECT_MAP.get(row['subject_id'], f"学科{row['subject_id']}"),
                    'grade_id': row['grade_id'],
                    'grade_name': GRADE_MAP.get(row['grade_id'], f"{row['grade_id']}年级"),
                    'book_id': row['book_id'],
                    'rfid_type': row['rfid_type'],
                    'rfid_type_text': RFID_TYPE_MAP.get(row['rfid_type'], row['rfid_type']),
                    'create_time': row['bind_create_time'].strftime('%Y-%m-%d %H:%M:%S') if row.get('bind_create_time') else None,
                    'update_time': row['bind_update_time'].strftime('%Y-%m-%d %H:%M:%S') if row.get('bind_update_time') else None
                }
                
                # 学生信息
                if row.get('student_id_val'):
                    result['student_info'] = {
                        'id': row['student_id_val'],
                        'name': row['student_name'],
                        'sex': '男' if row['sex'] == 1 else '女',
                        'grade': row['student_grade'],
                        'grade_name': GRADE_MAP.get(row['student_grade'], f"{row['student_grade']}年级"),
                        'class_id': row['class_id'],
                        'class_name': row.get('class_name') or '未知班级',
                        'stu_num': row.get('stu_num') or '',
                        'teacher_id': row.get('teacher_id') or ''
                    }
                
                # 书本信息
                if row.get('book_id_val'):
                    result['book_info'] = {
                        'id': row['book_id_val'],
                        'book_sn': row.get('book_sn') or '',
                        'book_name': row['book_name'],
                        'subject_id': row['book_subject_id'],
                        'subject_name': SUBJECT_MAP.get(row['book_subject_id'], f"学科{row['book_subject_id']}"),
                        'grade_id': row['book_grade_id'],
                        'grade_name': GRADE_MAP.get(row['book_grade_id'], f"{row['book_grade_id']}年级"),
                        'publishing': row.get('publishing') or ''
                    }
            
            # 老师信息需要单独查询（因为可能是多个）
            if row.get('teacher_id'):
                teacher_ids = [tid.strip() for tid in str(row['teacher_id']).split(',') if tid.strip()]
                if teacher_ids:
                    teacher_sql = """
                        SELECT t.id, t.teacher_name, t.subject_id, u.username, u.phone
                        FROM zp_teacher t
                        LEFT JOIN sys_user u ON t.id = u.id
                        WHERE t.id IN ({})
                    """.format(','.join(['%s'] * len(teacher_ids)))
                    teacher_rows = DatabaseService.execute_query(teacher_sql, tuple(teacher_ids))
                    if teacher_rows:
                        result['teacher_info'] = [{
                            'id': t['id'],
                            'name': t['teacher_name'],
                            'account': t.get('username') or '',
                            'phone': t.get('phone') or '',
                            'subject_id': t['subject_id'],
                            'subject_name': SUBJECT_MAP.get(t['subject_id'], f"学科{t['subject_id']}")
                        } for t in teacher_rows]
        
        has_data = result['basic_info'] is not None
        
        return jsonify({
            'success': True,
            'found': has_data,
            'data': result
        })
    
    except Exception as e:
        print(f"[RFIDQuery] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'查询失败: {str(e)}'})
