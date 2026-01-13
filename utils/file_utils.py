"""
文件工具模块
提供文件路径、唯一ID生成等工具函数
"""
import os
import re
import uuid


def get_file_path(directory, filename):
    """获取文件完整路径"""
    return os.path.join(directory, filename)


def generate_unique_id(length=8):
    """生成唯一ID"""
    return str(uuid.uuid4())[:length]


def safe_filename(name):
    """清理文件名中的非法字符"""
    if not name:
        return ''
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def ensure_directory(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def file_exists(filepath):
    """检查文件是否存在"""
    return os.path.exists(filepath)


def get_file_size(filepath):
    """获取文件大小（字节）"""
    if os.path.exists(filepath):
        return os.path.getsize(filepath)
    return 0


def list_files(directory, extension=None):
    """列出目录下的文件"""
    if not os.path.exists(directory):
        return []
    
    files = []
    for filename in os.listdir(directory):
        if extension is None or filename.endswith(extension):
            files.append(filename)
    return files


def delete_file(filepath):
    """删除文件"""
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def get_file_extension(filename):
    """获取文件扩展名"""
    if not filename:
        return ''
    _, ext = os.path.splitext(filename)
    return ext.lower()


def is_valid_file_type(filename, allowed_extensions):
    """检查文件类型是否有效"""
    ext = get_file_extension(filename)
    return ext in allowed_extensions
