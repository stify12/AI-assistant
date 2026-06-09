# -*- coding: utf-8 -*-
"""
拉取指定教师班级的所有学生作业图片到本地
支持按 教师 / 班级 / 学生 分类存储
"""

import os
import re
import json
import time
import pymysql
import oss2
from datetime import datetime

# ==================== 配置 ====================

# 目标教师列表
TARGET_TEACHERS = ['叶绍眉', '钟爱华']

# 本地保存根目录（可修改）
OUTPUT_DIR = r'd:\ZP\teacher_homework_images'

# 数据库配置（正式库，只读查询）
DB_CONFIG = {
    'host': '47.113.230.78',
    'port': 3306,
    'user': 'zpsmart',
    'password': 'rootyouerkj!',
    'database': 'zpsmart',
    'charset': 'utf8mb4'
}

# OSS 配置（从环境变量读取，更安全）
import os
OSS_CONFIG = {
    'access_key_id': os.environ.get('OSS_ACCESS_KEY_ID', ''),
    'access_key_secret': os.environ.get('OSS_ACCESS_KEY_SECRET', ''),
    'endpoint': 'oss-cn-guangzhou.aliyuncs.com',
    'bucket_name': 'zpsmart'
}

# 过滤时间范围（留空则不过滤）
DATE_START = ''   # 格式: '2026-01-01'
DATE_END   = ''   # 格式: '2026-04-30'

# ==================== 工具函数 ====================

def get_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def get_bucket():
    auth = oss2.Auth(OSS_CONFIG['access_key_id'], OSS_CONFIG['access_key_secret'])
    return oss2.Bucket(auth, OSS_CONFIG['endpoint'], OSS_CONFIG['bucket_name'])

def safe_filename(name):
    """去掉文件名非法字符"""
    return re.sub(r'[\\/:*?"<>|]', '_', name)

# ==================== 核心逻辑 ====================

def query_teacher_classes():
    """
    查询目标教师的班级和学生信息
    
    策略：
    1. 先尝试从 zp_teacher / zp_user_class 等关联表查
    2. 备用：从 zp_homework_publish.create_by 字段找到该教师发布过作业的班级
    """
    conn = get_db()
    cursor = conn.cursor()

    result = {}  # {teacher_name: {class_id: {class_name, students:[{id, name, stu_num}]}}}

    for teacher in TARGET_TEACHERS:
        print(f'\n🔍 查找教师 [{teacher}] 的班级...')
        result[teacher] = {}

        # 策略1: 从作业发布表找该教师的班级（create_by 字段存的是账号或姓名）
        cursor.execute('''
            SELECT DISTINCT class_id, create_by
            FROM zp_homework_publish
            WHERE create_by LIKE %s
            ORDER BY create_time DESC
        ''', (f'%{teacher}%',))
        rows = cursor.fetchall()

        class_ids = [r['class_id'] for r in rows]

        if not class_ids:
            print(f'  ⚠ 从发布记录未找到 [{teacher}] 的班级，尝试从用户表查询...')
            # 策略2: 尝试 sys_user / zp_teacher 表
            try:
                cursor.execute('''
                    SELECT DISTINCT uc.class_id
                    FROM zp_user_class uc
                    JOIN sys_user u ON u.id = uc.user_id
                    WHERE u.realname LIKE %s
                ''', (f'%{teacher}%',))
                rows2 = cursor.fetchall()
                class_ids = [r['class_id'] for r in rows2]
            except Exception:
                pass

        if not class_ids:
            print(f'  ❌ 找不到 [{teacher}] 的班级，请手动指定')
            continue

        print(f'  ✅ 找到 {len(class_ids)} 个班级: {class_ids}')

        # 查询每个班级的名称和学生
        for class_id in class_ids:
            cursor.execute('SELECT id, name FROM zp_class WHERE id = %s', (class_id,))
            cls = cursor.fetchone()
            class_name = cls['name'] if cls else str(class_id)

            cursor.execute('''
                SELECT id, name, stu_num
                FROM zp_student
                WHERE class_id = %s AND del_flag = 0 AND (remark IS NULL OR remark != 'virtual_test')
                ORDER BY stu_num
            ''', (class_id,))
            students = cursor.fetchall()

            result[teacher][class_id] = {
                'class_name': class_name,
                'students': students
            }
            print(f'    班级 [{class_name}]: {len(students)} 名学生')

    conn.close()
    return result


def download_student_images(bucket, student_id, student_name, save_dir, stats):
    """下载某个学生的所有 OSS 作业图片"""
    prefix = f'temp/homework/{student_id}/'
    downloaded = 0
    skipped = 0

    os.makedirs(save_dir, exist_ok=True)

    for obj in oss2.ObjectIterator(bucket, prefix=prefix):
        if not obj.key.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        # 时间过滤
        if DATE_START:
            start_ts = datetime.strptime(DATE_START, '%Y-%m-%d').timestamp()
            if obj.last_modified < start_ts:
                skipped += 1
                continue
        if DATE_END:
            from datetime import timedelta
            end_ts = (datetime.strptime(DATE_END, '%Y-%m-%d') + timedelta(days=1)).timestamp()
            if obj.last_modified >= end_ts:
                skipped += 1
                continue

        # 从路径提取 book_id 和文件名
        parts = obj.key.split('/')
        # 格式: temp/homework/{student_id}/{book_id}/{filename}
        if len(parts) >= 5:
            book_id = parts[3]
            filename = parts[4]
        else:
            filename = parts[-1]
            book_id = 'unknown'

        # 从文件名提取页码: {book_id}_{page_num}_{random}.jpg
        page_num = 'p?'
        name_parts = filename.rsplit('.', 1)[0].split('_')
        if len(name_parts) >= 2:
            page_num = f'p{name_parts[1]}'

        # 保存文件名: {student_name}_{page_num}_{book_id[:8]}.jpg
        save_filename = f'{safe_filename(student_name)}_{page_num}_{book_id[:8]}_{filename}'
        local_path = os.path.join(save_dir, save_filename)

        if os.path.exists(local_path):
            skipped += 1
            continue

        try:
            bucket.get_object_to_file(obj.key, local_path)
            downloaded += 1
            stats['total_downloaded'] += 1
            print(f'      ✓ {save_filename}')
        except Exception as e:
            print(f'      ✗ 下载失败 {obj.key}: {e}')
            stats['total_failed'] += 1

        time.sleep(0.05)  # 避免请求过快

    return downloaded, skipped


def run():
    print('=' * 60)
    print('📥 教师作业图片批量拉取工具')
    print(f'   目标教师: {", ".join(TARGET_TEACHERS)}')
    print(f'   保存目录: {OUTPUT_DIR}')
    print(f'   时间范围: {DATE_START or "不限"} ~ {DATE_END or "不限"}')
    print('=' * 60)

    # 1. 查询教师班级学生信息
    teacher_data = query_teacher_classes()

    if not any(teacher_data.values()):
        print('\n❌ 未找到任何教师的班级数据，退出')
        return

    # 2. 初始化 OSS
    print('\n🔌 连接OSS...')
    bucket = get_bucket()

    # 3. 统计信息
    stats = {
        'total_students': 0,
        'total_downloaded': 0,
        'total_failed': 0,
        'manifest': []
    }

    # 4. 逐教师 → 逐班级 → 逐学生下载
    for teacher_name, classes in teacher_data.items():
        teacher_dir = os.path.join(OUTPUT_DIR, safe_filename(teacher_name))

        for class_id, class_info in classes.items():
            class_name = class_info['class_name']
            students = class_info['students']
            class_dir = os.path.join(teacher_dir, safe_filename(class_name))

            print(f'\n📁 {teacher_name} / {class_name} ({len(students)}人)')

            for student in students:
                student_id = str(student['id'])
                student_name = student['name']
                stu_num = student.get('stu_num', '')

                # 学生目录名: {stu_num}_{student_name}
                dir_name = f'{safe_filename(stu_num)}_{safe_filename(student_name)}' if stu_num else safe_filename(student_name)
                student_dir = os.path.join(class_dir, dir_name)

                print(f'  👤 {student_name} (id={student_id})')
                downloaded, skipped = download_student_images(
                    bucket, student_id, student_name, student_dir, stats
                )

                stats['total_students'] += 1
                stats['manifest'].append({
                    'teacher': teacher_name,
                    'class': class_name,
                    'student_id': student_id,
                    'student_name': student_name,
                    'stu_num': stu_num,
                    'local_dir': student_dir,
                    'downloaded': downloaded,
                    'skipped': skipped
                })

                if downloaded == 0 and skipped == 0:
                    print(f'    (无图片)')

    # 5. 保存清单
    manifest_path = os.path.join(OUTPUT_DIR, f'manifest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(stats['manifest'], f, ensure_ascii=False, indent=2)

    # 6. 打印汇总
    print('\n' + '=' * 60)
    print('✅ 下载完成')
    print(f'   处理学生数: {stats["total_students"]}')
    print(f'   下载图片数: {stats["total_downloaded"]}')
    print(f'   失败数:     {stats["total_failed"]}')
    print(f'   清单文件:   {manifest_path}')
    print('=' * 60)

    # 7. 打印目录结构预览
    print('\n📂 输出目录结构:')
    print(f'{OUTPUT_DIR}/')
    for teacher_name in teacher_data:
        print(f'  ├── {teacher_name}/')
        for cid, cinfo in teacher_data[teacher_name].items():
            print(f'  │   ├── {cinfo["class_name"]}/')
            for s in cinfo['students'][:3]:
                print(f'  │   │   ├── {s.get("stu_num","")}_{s["name"]}/')
            if len(cinfo['students']) > 3:
                print(f'  │   │   └── ... ({len(cinfo["students"])-3} 更多)')
    print()


if __name__ == '__main__':
    run()
