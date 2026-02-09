"""
作业发布服务 - 调用 Java 后台 API 发布作业
"""

import requests
import logging
import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class HomeworkPublishService:
    """作业发布服务"""
    
    # 请求超时配置
    CONNECT_TIMEOUT = 10  # 连接超时
    READ_TIMEOUT = 30     # 读取超时
    MAX_RETRIES = 3       # 最大重试次数
    
    # 缓存的 token
    _token: Optional[str] = None
    _token_expire: Optional[datetime] = None
    
    @classmethod
    def _get_base_url(cls) -> str:
        """动态获取后台地址（每次请求时读取配置）"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('java_backend_url', 'https://oss.test.gzzhengpu.cn/jeecg-boot')
        except Exception:
            return 'https://oss.test.gzzhengpu.cn/jeecg-boot'
    
    @classmethod
    def _get_session(cls) -> requests.Session:
        """获取带重试机制的 Session"""
        session = requests.Session()
        try:
            # 新版本 urllib3 (>=1.26.0)
            retry_strategy = Retry(
                total=cls.MAX_RETRIES,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["GET", "POST"]
            )
        except TypeError:
            # 旧版本 urllib3
            retry_strategy = Retry(
                total=cls.MAX_RETRIES,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],
                method_whitelist=["GET", "POST"]
            )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    @classmethod
    def _request(cls, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """统一请求方法，带重试和详细错误信息"""
        # 设置默认超时
        kwargs.setdefault('timeout', (cls.CONNECT_TIMEOUT, cls.READ_TIMEOUT))
        
        session = cls._get_session()
        start_time = time.time()
        
        try:
            logger.info(f"[HomeworkPublish] 请求: {method} {url}")
            resp = session.request(method, url, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"[HomeworkPublish] 响应: {resp.status_code}, 耗时: {elapsed:.2f}s")
            
            return resp.json()
            
        except requests.exceptions.ConnectTimeout:
            base_url = cls._get_base_url()
            error = f"连接超时({cls.CONNECT_TIMEOUT}s)，服务器 {base_url} 可能未启动或端口未开放"
            logger.error(f"[HomeworkPublish] {error}")
            return {'success': False, 'error': error, 'error_type': 'connect_timeout'}
            
        except requests.exceptions.ReadTimeout:
            error = f"读取超时({cls.READ_TIMEOUT}s)，服务器响应过慢"
            logger.error(f"[HomeworkPublish] {error}")
            return {'success': False, 'error': error, 'error_type': 'read_timeout'}
            
        except requests.exceptions.ConnectionError as e:
            base_url = cls._get_base_url()
            error = f"连接失败，请检查服务器 {base_url} 是否可访问: {e}"
            logger.error(f"[HomeworkPublish] {error}")
            return {'success': False, 'error': error, 'error_type': 'connection_error'}
            
        except requests.exceptions.RequestException as e:
            error = f"请求异常: {e}"
            logger.error(f"[HomeworkPublish] {error}")
            return {'success': False, 'error': error, 'error_type': 'request_error'}
            
        except json.JSONDecodeError:
            error = "服务器返回非JSON格式数据"
            logger.error(f"[HomeworkPublish] {error}")
            return {'success': False, 'error': error, 'error_type': 'json_error'}
            
        finally:
            session.close()
    
    @classmethod
    def test_connection(cls) -> Dict[str, Any]:
        """测试与 Java 后台的连接"""
        from urllib.parse import urlparse
        import socket
        
        base_url = cls._get_base_url()
        
        # 解析 URL
        parsed = urlparse(base_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        result = {
            'host': host,
            'port': port,
            'base_url': base_url,
            'tcp_connect': False,
            'http_connect': False,
            'message': ''
        }
        
        # 1. TCP 连接测试
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            # 先解析域名
            ip = socket.gethostbyname(host)
            sock.connect((ip, port))
            sock.close()
            result['tcp_connect'] = True
            result['ip'] = ip
            logger.info(f"[HomeworkPublish] TCP连接成功: {host}:{port} ({ip})")
        except socket.gaierror as e:
            result['message'] = f"域名解析失败: {host}"
            return result
        except socket.timeout:
            result['message'] = f"TCP连接超时，端口 {port} 可能未开放"
            return result
        except Exception as e:
            result['message'] = f"TCP连接失败: {e}"
            return result
        
        # 2. HTTP 请求测试（测试登录接口）
        try:
            test_url = f"{base_url}/sys/mLogin"
            resp = requests.post(test_url, json={'username': '', 'password': ''}, timeout=5)
            result['http_connect'] = True
            result['http_status'] = resp.status_code
            result['message'] = '连接正常'
            logger.info(f"[HomeworkPublish] HTTP连接成功: {resp.status_code}")
        except Exception as e:
            result['message'] = f"HTTP请求失败: {e}"
        
        return result
    
    @classmethod
    def login(cls, username: str, password: str) -> Dict[str, Any]:
        """登录获取 token（使用移动端接口，无需验证码）"""
        if not username or not password:
            return {'success': False, 'error': '用户名或密码不能为空'}
        
        base_url = cls._get_base_url()
        url = f"{base_url}/sys/mLogin"
        payload = {"username": username, "password": password}
        
        logger.info(f"[HomeworkPublish] 登录: {username}")
        result = cls._request('POST', url, json=payload)
        
        # 请求失败（网络问题）
        if 'error_type' in result:
            return result
        
        # 业务逻辑判断
        if result.get('success'):
            token = result.get('result', {}).get('token')
            if token:
                cls._token = token
                cls._token_expire = datetime.now() + timedelta(hours=2)
                logger.info(f"[HomeworkPublish] 登录成功，token: {token[:20]}...")
                return {'success': True, 'token': token, 'data': result.get('result')}
        
        error = result.get('message', '登录失败')
        logger.error(f"[HomeworkPublish] 登录失败: {error}")
        return {'success': False, 'error': error}
    
    @classmethod
    def get_token(cls) -> Optional[str]:
        """获取有效的 token"""
        if cls._token and cls._token_expire and datetime.now() < cls._token_expire:
            return cls._token
        return None
    
    @classmethod
    def get_teacher_info(cls, token: str) -> Dict[str, Any]:
        """获取教师信息（书本列表、班级列表）"""
        if not token:
            return {'success': False, 'error': 'token不能为空'}
        
        base_url = cls._get_base_url()
        url = f"{base_url}/youerkj/zpHomeworkPublish/getTeacherInfo"
        headers = {"X-Access-Token": token}
        
        result = cls._request('GET', url, headers=headers)
        
        if 'error_type' in result:
            return result
        
        if result.get('success'):
            return {'success': True, 'data': result.get('result')}
        
        return {'success': False, 'error': result.get('message', '获取教师信息失败')}
    
    @classmethod
    def publish_homework(cls, token: str, book_id: str, class_id: str, 
                        subject_id: int, page_region: str, 
                        end_time: Optional[str] = None,
                        content: Optional[str] = None) -> Dict[str, Any]:
        """
        发布作业
        
        Args:
            token: 登录 token
            book_id: 书本 ID
            class_id: 班级 ID
            subject_id: 科目 ID (2=数学, 3=物理...)
            page_region: 页码范围 (如 "1-3" 或 "5")
            end_time: 截止时间 (格式: "2026-02-08 23:59:59")
            content: 作业内容/名称 (可选，默认用书本名)
        """
        # 参数验证
        if not token:
            return {'success': False, 'error': 'token不能为空'}
        if not book_id:
            return {'success': False, 'error': '书本ID不能为空'}
        if not class_id:
            return {'success': False, 'error': '班级ID不能为空'}
        if not page_region:
            return {'success': False, 'error': '页码范围不能为空'}
        
        base_url = cls._get_base_url()
        url = f"{base_url}/youerkj/zpHomeworkPublish/add"
        headers = {
            "X-Access-Token": token,
            "Content-Type": "application/json"
        }
        
        # 默认截止时间：明天 23:59:59
        if not end_time:
            tomorrow = datetime.now() + timedelta(days=1)
            end_time = tomorrow.strftime("%Y-%m-%d 23:59:59")
        
        payload = {
            "bookId": book_id,
            "classId": class_id,
            "subjectId": subject_id,
            "pageRegion": page_region,
            "endTime": end_time
        }
        
        if content:
            payload["content"] = content
        
        logger.info(f"[HomeworkPublish] 发布作业: {payload}")
        result = cls._request('POST', url, json=payload, headers=headers)
        
        if 'error_type' in result:
            return result
        
        if result.get('success'):
            logger.info("[HomeworkPublish] 发布成功")
            return {'success': True, 'message': '发布成功', 'data': result.get('result')}
        
        error = result.get('message', '发布失败')
        logger.error(f"[HomeworkPublish] 发布失败: {error}")
        return {'success': False, 'error': error}
    
    @classmethod
    def one_click_publish(cls, username: str, password: str,
                         book_id: str, class_id: str, subject_id: int,
                         page_region: str, end_time: Optional[str] = None) -> Dict[str, Any]:
        """一键发布作业（登录 + 发布）"""
        # 参数验证
        if not username or not password:
            return {'success': False, 'error': '用户名或密码不能为空'}
        
        # 1. 检查是否有有效 token
        token = cls.get_token()
        
        # 2. 没有 token 则登录
        if not token:
            login_result = cls.login(username, password)
            if not login_result.get('success'):
                return login_result
            token = login_result.get('token')
        
        # 3. 发布作业
        return cls.publish_homework(
            token=token,
            book_id=book_id,
            class_id=class_id,
            subject_id=subject_id,
            page_region=page_region,
            end_time=end_time
        )
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """获取服务状态信息"""
        return {
            'base_url': cls._get_base_url(),
            'has_token': cls._token is not None,
            'token_expire': cls._token_expire.isoformat() if cls._token_expire else None,
            'token_valid': cls.get_token() is not None
        }


# 单例
homework_publish_service = HomeworkPublishService()
