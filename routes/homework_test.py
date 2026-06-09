# -*- coding: utf-8 -*-
"""作业测试工具 - 后端API（解耦牨7步流程版）"""

from flask import Blueprint, request, jsonify, render_template
import oss2
import pymysql
import requests
import os
import json
import uuid
import random
import string
import time
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading
from services.homework_publish_service import HomeworkPublishService

logger = logging.getLogger(__name__)
homework_test_bp = Blueprint('homework_test', __name__)

# 配置（从环境变量读取敏感信息）
import os
OSS_CONFIG = {
    'access_key_id': os.environ.get('OSS_ACCESS_KEY_ID', ''),
    'access_key_secret': os.environ.get('OSS_ACCESS_KEY_SECRET', ''),
    'endpoint': 'oss-cn-guangzhou.aliyuncs.com',
    'bucket_name': 'zpsmart'
}

DB_CONFIG = {
    'host': '47.113.230.78',
    'port': 3306,
    'user': 'zpsmart',
    'password': 'rootyouerkj!',
    'database': 'zpsmart',
    'charset': 'utf8mb4'
}

DEVICE_API_URL = 'https://cms.test.gzzhengpu.cn/api/v1/device'

# 全局状态
task_status = {}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def get_oss_bucket():
    auth = oss2.Auth(OSS_CONFIG['access_key_id'], OSS_CONFIG['access_key_secret'])
    return oss2.Bucket(auth, OSS_CONFIG['endpoint'], OSS_CONFIG['bucket_name'])

@homework_test_bp.route('/homework-test')
def homework_test_page():
    """作业测试工具页面"""
    return render_template('homework_test.html')

@homework_test_bp.route('/api/homework-test/oss/list', methods=['POST'])
def list_oss_images():
    """列出OSS中的图片"""
    try:
        data = request.json
        prefix = data.get('prefix', 'temp/homework/')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        book_id = data.get('book_id')
        page_num = data.get('page_num')
        limit = data.get('limit', 100)
        
        bucket = get_oss_bucket()
        images = []
        count = 0
        
        for obj in oss2.ObjectIterator(bucket, prefix=prefix):
            if not obj.key.endswith(('.jpg', '.jpeg', '.png')):
                continue
            
            # 过滤book_id
            if book_id and book_id not in obj.key:
                continue
            
            # 过滤页码
            if page_num:
                page_pattern = f"_{page_num}_"
                if page_pattern not in obj.key:
                    continue
            
            # 过滤时间
            if start_date or end_date:
                last_modified = obj.last_modified
                if start_date:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    if last_modified < start_dt.timestamp():
                        continue
                if end_date:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                    if last_modified >= end_dt.timestamp():
                        continue
            
            images.append({
                'key': obj.key,
                'size': obj.size,
                'last_modified': datetime.fromtimestamp(obj.last_modified).strftime('%Y-%m-%d %H:%M:%S'),
                'url': f"https://img.gzzhengpu.cn/{obj.key}"
            })
            
            count += 1
            if count >= limit:
                break
        
        return jsonify({'success': True, 'images': images, 'count': len(images)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@homework_test_bp.route('/api/homework-test/books', methods=['GET'])
def get_books():
    """获取书籍列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, book_name, subject_id, grade_id 
            FROM zp_make_book 
            WHERE status = 1 
            ORDER BY create_time DESC 
            LIMIT 50
        ''')
        books = cursor.fetchall()
        conn.close()
        return jsonify({'success': True, 'books': books})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@homework_test_bp.route('/api/homework-test/classes', methods=['GET'])
def get_classes():
    """获取班级列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name as class_name, grade_id 
            FROM zp_class 
            ORDER BY create_time DESC 
            LIMIT 50
        ''')
        classes = cursor.fetchall()
        conn.close()
        return jsonify({'success': True, 'classes': classes})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@homework_test_bp.route('/api/homework-test/students', methods=['GET'])
def get_students():
    """获取学生列表"""
    try:
        class_id = request.args.get('class_id')
        book_id = request.args.get('book_id')
        exclude = request.args.get('exclude', '').split(',')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT s.id, s.name, s.stu_num,
                   (SELECT rfid_no FROM zp_bind_rfid 
                    WHERE student_id = s.id AND book_id = %s 
                    ORDER BY create_time DESC LIMIT 1) as rfid_no
            FROM zp_student s
            WHERE s.class_id = %s
            ORDER BY s.stu_num
        '''
        cursor.execute(query, (book_id, class_id))
        students = cursor.fetchall()
        
        # 过滤排除的学生和没有RFID的学生
        students = [s for s in students if s['rfid_no'] and s['name'] not in exclude]
        
        conn.close()
        return jsonify({'success': True, 'students': students})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@homework_test_bp.route('/api/homework-test/tasks', methods=['GET'])
def get_tasks():
    """获取作业任务列表"""
    try:
        class_id = request.args.get('class_id')
        limit = request.args.get('limit', 20)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT id, content, book_id, page_region, class_id, status, create_time, create_by
            FROM zp_homework_publish
            WHERE class_id = %s
            ORDER BY create_time DESC
            LIMIT %s
        '''
        cursor.execute(query, (class_id, int(limit)))
        tasks = cursor.fetchall()
        
        # 转换datetime为字符串
        for task in tasks:
            if task['create_time']:
                task['create_time'] = task['create_time'].strftime('%Y-%m-%d %H:%M:%S')
        
        conn.close()
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@homework_test_bp.route('/api/homework-test/submit', methods=['POST'])
def submit_homework():
    """提交作业（支持3种分配模式）"""
    try:
        data = request.json
        task_id = data.get('task_id')
        students = data.get('students', [])
        # 新接口参数
        images = data.get('images', [])          # 展开的图片URL列表
        mode = data.get('mode', 'round_robin')   # 分配模式
        page_start = int(data.get('page_start', 1))  # 起始页码
        device_api_url = data.get('device_api_url', DEVICE_API_URL)
        device_mac = data.get('device_mac', '59411cc01588')
        # 兴老接口兼容
        images_by_page = data.get('images_by_page', {})

        if not task_id:
            return jsonify({'success': False, 'message': '缺少 task_id'})
        if not students:
            return jsonify({'success': False, 'message': '缺少 students'})

        # 如果传了新格式的展开图片列表，按mode构建 images_by_page
        if images and not images_by_page:
            images_by_page = _build_images_by_page(images, students, mode, page_start)

        submit_task_id = str(uuid.uuid4())
        task_status[submit_task_id] = {
            'status': 'running',
            'total': 0,
            'completed': 0,
            'success_count': 0,
            'failed_count': 0,
            'logs': []
        }

        thread = threading.Thread(
            target=_submit_homework_task,
            args=(submit_task_id, task_id, students, images_by_page, device_api_url, device_mac)
        )
        thread.start()

        return jsonify({'success': True, 'task_id': submit_task_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


def _build_images_by_page(images, students, mode, page_start):
    """
    根据分配模式构建 images_by_page

    Args:
        images: 展开的图片URL列表
        students: 学生列表
        mode: 'all_to_one' | 'one_to_one' | 'round_robin'
        page_start: 起始页码

    Returns:
        dict: {page_num: [image_url, ...]}
    """
    images_by_page = {}

    if mode == 'all_to_one':
        # 所有图片分配给第一个学生，每张图对应不同页码
        for idx, url in enumerate(images):
            page = page_start + idx
            images_by_page[str(page)] = [url]

    elif mode == 'one_to_one':
        # 每个学生对应一张图，页码相同
        for i, student in enumerate(students):
            if i < len(images):
                images_by_page[str(page_start)] = images_by_page.get(str(page_start), []) + [images[i]]

    else:  # round_robin: 图片循环分配给所有学生
        if images:
            for i in range(len(students)):
                url = images[i % len(images)]
                images_by_page[str(page_start)] = images_by_page.get(str(page_start), []) + [url]

    return images_by_page


def _submit_homework_task(submit_task_id, hw_publish_id, students, images_by_page,
                          device_api_url=None, device_mac='59411cc01588'):
    """后台提交作业任务（流式处理）"""
    if device_api_url is None:
        device_api_url = DEVICE_API_URL

    try:
        status = task_status[submit_task_id]
        pages = sorted([int(p) for p in images_by_page.keys()])
        status['total'] = len(students) * len(pages)

        session = requests.Session()
        student_details = {s['rfid_no']: [] for s in students}

        for page_num in pages:
            page_images = images_by_page.get(str(page_num), [])
            if not page_images:
                status['logs'].append(f"页码 {page_num}: 无图片，跳过")
                continue

            status['logs'].append(f"--- 页码 {page_num} ---")

            for i, student in enumerate(students):
                rfid_no = student['rfid_no']
                name = student.get('name', rfid_no)
                image_url = page_images[i % len(page_images)]

                try:
                    # 流式下载图片
                    img_resp = session.get(image_url, timeout=30)
                    if img_resp.status_code != 200:
                        raise Exception(f"下载图片失败: {img_resp.status_code}")

                    # 流式上传到设备API
                    upload_url = f"{device_api_url}/uploadHomework"
                    filename = image_url.split('/')[-1] or f"{rfid_no}_{page_num}.jpg"
                    files = {'file': (filename, img_resp.content, 'image/jpeg')}
                    form_data = {
                        'rfidNo': rfid_no,
                        'pageNum': page_num,
                        'hwPublishId': hw_publish_id
                    }

                    resp = session.post(upload_url, data=form_data, files=files, timeout=60)
                    result = resp.json()

                    if result.get('success'):
                        status['success_count'] += 1
                        status['logs'].append(f"  [{i+1}/{len(students)}] {name}: ✓ 成功")
                        student_details[rfid_no].append({"count": 1, "error": 0, "rfid": rfid_no})
                    else:
                        status['failed_count'] += 1
                        status['logs'].append(f"  [{i+1}/{len(students)}] {name}: ✗ {result.get('message')}")
                        student_details[rfid_no].append({"count": 1, "error": 1, "rfid": rfid_no})

                except Exception as e:
                    status['failed_count'] += 1
                    status['logs'].append(f"  [{i+1}/{len(students)}] {name}: ✗ {str(e)}")
                    student_details[rfid_no].append({"count": 1, "error": 1, "rfid": rfid_no})

                status['completed'] += 1
                time.sleep(0.2)

        # 提交汇总记录
        status['logs'].append("--- 提交作业记录 ---")
        all_details = []
        for rfid_no, details in student_details.items():
            if details:
                all_details.append({
                    "count": len(details),
                    "error": sum(1 for d in details if d['error'] == 1),
                    "rfid": rfid_no
                })

        record_url = f"{device_api_url}/uploadHomeworkRecord"
        payload = {
            "detail": all_details,
            "hwPublishId": hw_publish_id,
            "mac": device_mac,
            "uuid": str(uuid.uuid4())
        }
        resp = session.post(record_url, json=payload, timeout=60)
        result = resp.json()

        if result.get('success'):
            status['logs'].append("✓ 提交记录成功")
        else:
            status['logs'].append(f"✗ 提交记录失败: {result.get('message')}")

        status['status'] = 'completed'
        logger.info(f'[提交作业] 完成, 成功={status["success_count"]}, 失败={status["failed_count"]}')

    except Exception as e:
        task_status[submit_task_id]['status'] = 'error'
        task_status[submit_task_id]['logs'].append(f"错误: {str(e)}")
        logger.error(f'[提交作业] 异常: {e}')


@homework_test_bp.route('/api/homework-test/submit/status/<task_id>', methods=['GET'])
def get_submit_status(task_id):
    """获取提交任务状态"""
    if task_id not in task_status:
        return jsonify({'success': False, 'message': '任务不存在'})
    return jsonify({'success': True, **task_status[task_id]})

@homework_test_bp.route('/api/homework-test/download-images', methods=['POST'])
def download_images():
    """下载OSS图片到本地"""
    try:
        data = request.json
        images = data.get('images', [])
        book_id = data.get('book_id')
        target_dir = data.get('target_dir', 'd:/ZP/task_images/test')
        
        bucket = get_oss_bucket()
        downloaded = 0
        
        os.makedirs(target_dir, exist_ok=True)
        
        for img in images:
            key = img['key']
            # 提取学生ID
            parts = key.split('/')
            if len(parts) >= 3:
                student_id = parts[2]
                student_dir = os.path.join(target_dir, student_id)
                os.makedirs(student_dir, exist_ok=True)
                
                filename = parts[-1]
                local_path = os.path.join(student_dir, filename)
                
                bucket.get_object_to_file(key, local_path)
                downloaded += 1
        
        return jsonify({'success': True, 'downloaded': downloaded})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ==================== 测试连接 ====================

@homework_test_bp.route('/api/homework-test/test-connection', methods=['POST'])
def test_connection():
    """测试服务器连接"""
    try:
        data = request.json or {}
        device_api_url = data.get('device_api_url', DEVICE_API_URL)
        java_backend_url = data.get('java_backend_url', '')

        results = {}

        # 测试设备API
        try:
            resp = requests.get(device_api_url.rstrip('/').rsplit('/device', 1)[0] + '/health',
                                timeout=5)
            results['device_api'] = resp.status_code < 500
        except Exception:
            # 尝试请求任意一个已知接口
            try:
                resp = requests.post(device_api_url + '/uploadHomeworkRecord',
                                     json={}, timeout=5)
                results['device_api'] = True  # 能连就算通
            except requests.exceptions.ConnectionError:
                results['device_api'] = False
            except Exception:
                results['device_api'] = True

        # 测试Java后台
        if java_backend_url:
            result = HomeworkPublishService.test_connection()
            results['java_backend'] = result.get('http_connect', False)
            results['java_detail'] = result
        else:
            results['java_backend'] = None

        all_ok = results.get('device_api', False)
        return jsonify({
            'success': all_ok,
            'message': '连接正常' if all_ok else '部分服务连接失败',
            'results': results
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ==================== 虚拟学生管理 ====================

@homework_test_bp.route('/api/homework-test/virtual-students/generate', methods=['POST'])
def generate_virtual_students():
    """生成虚拟学生并写入数据库"""
    try:
        data = request.json
        count = min(int(data.get('count', 10)), 30)
        prefix = data.get('prefix', '测试学生')
        book_id = data.get('book_id')
        class_id = data.get('class_id')

        if not book_id or not class_id:
            return jsonify({'success': False, 'message': 'book_id 和 class_id 不能为空'})

        conn = get_db_connection()
        cursor = conn.cursor()
        students = []

        try:
            for i in range(1, count + 1):
                name = f"{prefix}_{i:02d}"
                stu_num = f"VT{int(time.time()) % 100000}{i:02d}"
                # 生成以 99 开头的8位虚拟RFID，避免与真实卡号冲突
                rfid_no = '99' + ''.join(random.choices(string.digits, k=8))

                # 写入学生表
                cursor.execute('''
                    INSERT INTO zp_student (name, stu_num, class_id, remark, create_time, del_flag)
                    VALUES (%s, %s, %s, %s, NOW(), 0)
                ''', (name, stu_num, class_id, 'virtual_test'))
                student_id = cursor.lastrowid

                # 写入RFID绑定表
                cursor.execute('''
                    INSERT INTO zp_bind_rfid (student_id, book_id, rfid_no, create_time, del_flag)
                    VALUES (%s, %s, %s, NOW(), 0)
                ''', (student_id, book_id, rfid_no))

                students.append({
                    'id': student_id,
                    'name': name,
                    'stu_num': stu_num,
                    'rfid_no': rfid_no,
                    '_type': 'virtual'
                })

            conn.commit()
            logger.info(f'[虚拟学生] 生成 {len(students)} 个虚拟学生, class_id={class_id}')
            return jsonify({'success': True, 'students': students, 'count': len(students)})

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    except Exception as e:
        logger.error(f'[虚拟学生] 生成失败: {e}')
        return jsonify({'success': False, 'message': str(e)})


@homework_test_bp.route('/api/homework-test/virtual-students', methods=['GET'])
def get_virtual_students():
    """查询已有虚拟学生"""
    try:
        book_id = request.args.get('book_id')
        class_id = request.args.get('class_id')

        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT s.id, s.name, s.stu_num,
                   (SELECT rfid_no FROM zp_bind_rfid
                    WHERE student_id = s.id AND book_id = %s
                    ORDER BY create_time DESC LIMIT 1) as rfid_no
            FROM zp_student s
            WHERE s.class_id = %s AND s.remark = 'virtual_test' AND s.del_flag = 0
            ORDER BY s.create_time DESC
        '''
        cursor.execute(query, (book_id, class_id))
        students = cursor.fetchall()
        conn.close()

        return jsonify({
            'success': True,
            'students': [dict(s, _type='virtual') for s in students],
            'count': len(students)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@homework_test_bp.route('/api/homework-test/virtual-students', methods=['DELETE'])
def delete_virtual_students():
    """清理虚拟学生"""
    try:
        data = request.json or {}
        class_id = data.get('class_id')
        student_ids = data.get('student_ids', [])

        conn = get_db_connection()
        cursor = conn.cursor()
        deleted = 0

        try:
            if student_ids:
                # 删除指定学生
                placeholders = ','.join(['%s'] * len(student_ids))
                # 删RFID绑定
                cursor.execute(f'DELETE FROM zp_bind_rfid WHERE student_id IN ({placeholders})', student_ids)
                # 删学生
                cursor.execute(f'DELETE FROM zp_student WHERE id IN ({placeholders}) AND remark = %s',
                               student_ids + ['virtual_test'])
                deleted = cursor.rowcount
            elif class_id:
                # 删除该班级所有虚拟学生
                cursor.execute('''
                    SELECT id FROM zp_student
                    WHERE class_id = %s AND remark = 'virtual_test' AND del_flag = 0
                ''', (class_id,))
                rows = cursor.fetchall()
                ids = [r['id'] for r in rows]
                if ids:
                    placeholders = ','.join(['%s'] * len(ids))
                    cursor.execute(f'DELETE FROM zp_bind_rfid WHERE student_id IN ({placeholders})', ids)
                    cursor.execute(f'DELETE FROM zp_student WHERE id IN ({placeholders})', ids)
                    deleted = len(ids)
            else:
                # 删除全部虚拟学生
                cursor.execute("SELECT id FROM zp_student WHERE remark = 'virtual_test' AND del_flag = 0")
                rows = cursor.fetchall()
                ids = [r['id'] for r in rows]
                if ids:
                    placeholders = ','.join(['%s'] * len(ids))
                    cursor.execute(f'DELETE FROM zp_bind_rfid WHERE student_id IN ({placeholders})', ids)
                    cursor.execute(f'DELETE FROM zp_student WHERE id IN ({placeholders})', ids)
                    deleted = len(ids)

            conn.commit()
            logger.info(f'[虚拟学生] 清理 {deleted} 个')
            return jsonify({'success': True, 'deleted': deleted})

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    except Exception as e:
        logger.error(f'[虚拟学生] 清理失败: {e}')
        return jsonify({'success': False, 'message': str(e)})


# ==================== 发布作业 ====================

@homework_test_bp.route('/api/homework-test/publish', methods=['POST'])
def publish_homework_api():
    """发布作业（整合HomeworkPublishService）"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        book_id = str(data.get('book_id', ''))
        class_id = str(data.get('class_id', ''))
        subject_id = int(data.get('subject_id', 2))
        page_region = data.get('page_region')
        content = data.get('content')
        end_time = data.get('end_time')

        if not all([username, password, book_id, class_id, page_region]):
            return jsonify({'success': False, 'message': '缺少必要参数'})

        result = HomeworkPublishService.one_click_publish(
            username=username,
            password=password,
            book_id=book_id,
            class_id=class_id,
            subject_id=subject_id,
            page_region=page_region,
            end_time=end_time
        )

        if result.get('success'):
            hw_publish_id = result.get('data') or result.get('hw_publish_id')
            # data 可能直接是ID字符串或包含 id 的字典
            if isinstance(hw_publish_id, dict):
                hw_publish_id = hw_publish_id.get('id') or hw_publish_id.get('hwPublishId')
            logger.info(f'[发布作业] 成功, hw_publish_id={hw_publish_id}')
            return jsonify({'success': True, 'hw_publish_id': hw_publish_id, 'message': '发布成功'})
        else:
            return jsonify({'success': False, 'message': result.get('error', '发布失败')})

    except Exception as e:
        logger.error(f'[发布作业] 异常: {e}')
        return jsonify({'success': False, 'message': str(e)})

