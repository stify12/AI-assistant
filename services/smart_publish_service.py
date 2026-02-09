"""
智能发布作业服务 - 极简作业发布
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from services.database_service import DatabaseService
from services.homework_publish_service import HomeworkPublishService

logger = logging.getLogger(__name__)

# 统一密码
DEFAULT_PASSWORD = '123456zp.'

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'sessions', 'smart_publish_config.json')


class SmartPublishService:
    """智能发布作业服务"""
    
    @classmethod
    def _ensure_config_dir(cls):
        """确保配置目录存在"""
        config_dir = os.path.dirname(CONFIG_FILE)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """获取配置"""
        cls._ensure_config_dir()
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"[SmartPublish] 读取配置失败: {e}")
        return {'last_teacher_id': None, 'last_book_id': None, 'history': []}
    
    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> bool:
        """保存配置"""
        cls._ensure_config_dir()
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"[SmartPublish] 保存配置失败: {e}")
            return False
    
    @classmethod
    def get_books(cls) -> Dict[str, Any]:
        """获取书本列表"""
        try:
            sql = """
                SELECT id, book_name, subject_id, grade_id
                FROM zp_make_book 
                WHERE status = 1 
                ORDER BY update_time DESC
                LIMIT 100
            """
            rows = DatabaseService.execute_query(sql)
            
            # 学科映射
            subject_map = {
                0: '英语', 1: '语文', 2: '数学', 3: '物理',
                4: '化学', 5: '生物', 6: '地理'
            }
            
            books = []
            for row in rows:
                books.append({
                    'id': row['id'],
                    'book_name': row['book_name'],
                    'subject_id': row['subject_id'],
                    'subject_name': subject_map.get(row['subject_id'], '未知'),
                    'grade_id': row['grade_id']
                })
            
            return {'success': True, 'data': books}
        except Exception as e:
            logger.error(f"[SmartPublish] 获取书本列表失败: {e}")
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def get_teachers_by_book(cls, book_id: str) -> Dict[str, Any]:
        """根据书本ID获取绑定的老师列表（展开多班级）"""
        if not book_id:
            return {'success': False, 'error': '书本ID不能为空'}
        
        try:
            # 先获取老师基本信息
            sql = """
                SELECT t.id, t.teacher_name, t.class_id, t.subject_id
                FROM zp_teacher t
                WHERE FIND_IN_SET(%s, t.book_id)
            """
            rows = DatabaseService.execute_query(sql, (book_id,))
            
            if not rows:
                return {'success': True, 'data': {'teachers': [], 'need_select': False, 'selected_teacher': None}}
            
            # 收集所有班级ID
            all_class_ids = set()
            for row in rows:
                class_ids = row.get('class_id', '').split(',')
                for cid in class_ids:
                    if cid.strip():
                        all_class_ids.add(cid.strip())
            
            # 批量查询班级信息
            class_map = {}
            if all_class_ids:
                placeholders = ','.join(['%s'] * len(all_class_ids))
                class_sql = f"SELECT id, name, grade_id FROM zp_class WHERE id IN ({placeholders})"
                class_rows = DatabaseService.execute_query(class_sql, tuple(all_class_ids))
                for c in class_rows:
                    class_map[c['id']] = {'name': c['name'], 'grade_id': c.get('grade_id', '')}
            
            # 展开老师-班级组合
            teachers = []
            for row in rows:
                class_ids = row.get('class_id', '').split(',')
                for cid in class_ids:
                    cid = cid.strip()
                    if not cid:
                        continue
                    class_info = class_map.get(cid, {'name': '', 'grade_id': ''})
                    teachers.append({
                        'id': row['id'],
                        'teacher_name': row['teacher_name'],
                        'class_id': cid,
                        'class_name': class_info['name'],
                        'grade_id': class_info['grade_id'],
                        'subject_id': row['subject_id']
                    })
            
            # 判断是否需要用户选择
            need_select = len(teachers) > 1
            
            # 如果只有一个老师，或者有上次选择的老师，自动选中
            config = cls.get_config()
            selected_teacher = None
            
            if len(teachers) == 1:
                selected_teacher = teachers[0]
            elif config.get('last_teacher_id'):
                for t in teachers:
                    if t['id'] == config['last_teacher_id']:
                        selected_teacher = t
                        break
            
            return {
                'success': True,
                'data': {
                    'teachers': teachers,
                    'need_select': need_select,
                    'selected_teacher': selected_teacher
                }
            }
        except Exception as e:
            logger.error(f"[SmartPublish] 获取老师列表失败: {e}")
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def get_book_pages(cls, book_id: str) -> Dict[str, Any]:
        """获取书本页码列表"""
        if not book_id:
            return {'success': False, 'error': '书本ID不能为空'}
        
        try:
            # 方法1: 从 zp_book_chapter 获取有题目的页码
            sql = """
                SELECT DISTINCT page_num 
                FROM zp_book_chapter 
                WHERE book_id = %s AND page_num IS NOT NULL
                ORDER BY page_num
            """
            rows = DatabaseService.execute_query(sql, (book_id,))
            
            if rows:
                pages = [row['page_num'] for row in rows]
                return {'success': True, 'data': {'pages': pages, 'total': len(pages)}}
            
            # 方法2: 从 zp_make_book.imgs_path 计算页数
            sql2 = "SELECT imgs_path FROM zp_make_book WHERE id = %s"
            book_row = DatabaseService.execute_one(sql2, (book_id,))
            
            if book_row and book_row.get('imgs_path'):
                imgs = book_row['imgs_path'].split(',')
                total = len(imgs)
                pages = list(range(1, total + 1))
                return {'success': True, 'data': {'pages': pages, 'total': total}}
            
            return {'success': True, 'data': {'pages': [], 'total': 0}}
        except Exception as e:
            logger.error(f"[SmartPublish] 获取页码列表失败: {e}")
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _get_teacher_username(cls, teacher_id: str) -> Optional[str]:
        """根据老师ID获取登录用户名"""
        try:
            # 从 sys_user 表查询（通过 id 关联）
            sql = """
                SELECT u.username
                FROM sys_user u
                WHERE u.id = %s
                LIMIT 1
            """
            row = DatabaseService.execute_one(sql, (teacher_id,))
            if row and row.get('username'):
                return row['username']
            
            return None
        except Exception as e:
            logger.error(f"[SmartPublish] 获取老师用户名失败: {e}")
            return None
    
    @classmethod
    def publish(cls, book_id: str, teacher_id: str, class_id: str, pages: str) -> Dict[str, Any]:
        """
        一键发布作业
        
        Args:
            book_id: 书本ID
            teacher_id: 老师ID
            class_id: 班级ID
            pages: 页码，如 "1" 或 "1,2,3" 或 "1-5"
        """
        if not book_id:
            return {'success': False, 'error': '请选择书本'}
        if not teacher_id:
            return {'success': False, 'error': '请选择老师'}
        if not class_id:
            return {'success': False, 'error': '请选择班级'}
        if not pages:
            return {'success': False, 'error': '请输入页码'}
        
        try:
            # 1. 获取老师信息
            sql = "SELECT id, teacher_name, subject_id FROM zp_teacher WHERE id = %s"
            teacher = DatabaseService.execute_one(sql, (teacher_id,))
            if not teacher:
                return {'success': False, 'error': '老师不存在'}
            
            # 2. 获取班级信息
            sql_class = "SELECT name, grade_id FROM zp_class WHERE id = %s"
            class_info = DatabaseService.execute_one(sql_class, (class_id,))
            class_name = class_info.get('name', '') if class_info else ''
            
            # 3. 获取书本信息
            sql2 = "SELECT book_name, subject_id FROM zp_make_book WHERE id = %s"
            book = DatabaseService.execute_one(sql2, (book_id,))
            if not book:
                return {'success': False, 'error': '书本不存在'}
            
            # 4. 获取老师登录用户名
            username = cls._get_teacher_username(teacher_id)
            if not username:
                username = teacher['teacher_name']
            
            logger.info(f"[SmartPublish] 使用账号登录: {username}")
            
            # 5. 登录获取 token
            login_result = HomeworkPublishService.login(username, DEFAULT_PASSWORD)
            if not login_result.get('success'):
                return {'success': False, 'error': f"登录失败: {login_result.get('error', '未知错误')}"}
            
            token = login_result.get('token')
            
            # 6. 生成作业名称
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            homework_name = f"自动测试P{pages}_{timestamp}"
            
            # 7. 调用发布 API
            publish_result = HomeworkPublishService.publish_homework(
                token=token,
                book_id=book_id,
                class_id=class_id,
                subject_id=teacher['subject_id'],
                page_region=pages,
                content=homework_name
            )
            
            # 8. 记录历史
            if publish_result.get('success'):
                cls._add_history({
                    'book_id': book_id,
                    'book_name': book['book_name'],
                    'pages': pages,
                    'homework_name': homework_name,
                    'teacher_id': teacher_id,
                    'teacher_name': teacher['teacher_name'],
                    'class_name': class_name,
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'success': True
                })
                
                # 保存上次选择
                config = cls.get_config()
                config['last_teacher_id'] = teacher_id
                config['last_class_id'] = class_id
                config['last_book_id'] = book_id
                cls.save_config(config)
                
                return {
                    'success': True,
                    'data': {
                        'homework_name': homework_name,
                        'teacher_name': teacher['teacher_name'],
                        'class_name': class_name,
                        'pages': pages
                    }
                }
            else:
                cls._add_history({
                    'book_id': book_id,
                    'book_name': book['book_name'],
                    'pages': pages,
                    'homework_name': homework_name,
                    'teacher_id': teacher_id,
                    'teacher_name': teacher['teacher_name'],
                    'class_name': class_name,
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'success': False,
                    'error': publish_result.get('error', '发布失败')
                })
                return {'success': False, 'error': publish_result.get('error', '发布失败')}
                
        except Exception as e:
            logger.error(f"[SmartPublish] 发布失败: {e}")
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _add_history(cls, record: Dict[str, Any]):
        """添加发布历史"""
        try:
            config = cls.get_config()
            history = config.get('history', [])
            history.insert(0, record)
            # 最多保留50条
            config['history'] = history[:50]
            cls.save_config(config)
        except Exception as e:
            logger.error(f"[SmartPublish] 保存历史失败: {e}")
    
    @classmethod
    def get_history(cls, limit: int = 20) -> Dict[str, Any]:
        """获取发布历史"""
        try:
            config = cls.get_config()
            history = config.get('history', [])[:limit]
            return {'success': True, 'data': history}
        except Exception as e:
            logger.error(f"[SmartPublish] 获取历史失败: {e}")
            return {'success': False, 'error': str(e)}


# 单例
smart_publish_service = SmartPublishService()
