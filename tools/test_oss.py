"""
阿里云OSS连接测试脚本
测试OSS配置是否正确，包括连接、列举bucket内容等
"""
import os
import oss2
from datetime import datetime

OSS_CONFIG = {
    'access_key_id': os.environ.get('OSS_ACCESS_KEY_ID', ''),
    'access_key_secret': os.environ.get('OSS_ACCESS_KEY_SECRET', ''),
    'endpoint': 'oss-cn-guangzhou.aliyuncs.com',
    'bucket_name': 'zpsmart',
    'static_domain': 'https://img.gzzhengpu.cn'
}


def test_oss_connection():
    """测试OSS连接"""
    print("=" * 50)
    print("阿里云OSS连接测试")
    print("=" * 50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Endpoint: {OSS_CONFIG['endpoint']}")
    print(f"Bucket: {OSS_CONFIG['bucket_name']}")
    print(f"Static Domain: {OSS_CONFIG['static_domain']}")
    print("-" * 50)
    
    try:
        # 创建Auth对象
        auth = oss2.Auth(
            OSS_CONFIG['access_key_id'],
            OSS_CONFIG['access_key_secret']
        )
        
        # 创建Bucket对象
        bucket = oss2.Bucket(
            auth,
            OSS_CONFIG['endpoint'],
            OSS_CONFIG['bucket_name']
        )
        
        print("[1/4] 认证对象创建成功 ✓")
        
        # 测试bucket是否存在
        try:
            bucket_info = bucket.get_bucket_info()
            print(f"[2/4] Bucket存在 ✓")
            print(f"      - 创建时间: {bucket_info.creation_date}")
            print(f"      - 存储类型: {bucket_info.storage_class}")
            print(f"      - 地域: {bucket_info.location}")
        except oss2.exceptions.NoSuchBucket:
            print(f"[2/4] Bucket不存在 ✗")
            return False
        except Exception as e:
            print(f"[2/4] 获取Bucket信息失败: {e}")
        
        # 列举部分文件（仅获取元信息，不下载内容）
        print("[3/4] 列举Bucket中的文件（仅元信息，不下载）...")
        file_count = 0
        for obj in oss2.ObjectIterator(bucket, max_keys=3):
            file_count += 1
            size_kb = obj.size / 1024
            print(f"      - {obj.key} ({size_kb:.2f} KB)")
        
        if file_count > 0:
            print(f"      共列举 {file_count} 个文件 ✓")
        else:
            print("      Bucket为空或无读取权限")
        
        # 测试上传权限（上传一个测试文件然后删除）
        print("[4/4] 测试上传权限...")
        test_key = f"_test_connection_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        test_content = f"OSS连接测试 - {datetime.now()}"
        
        try:
            bucket.put_object(test_key, test_content)
            print(f"      上传测试文件成功: {test_key} ✓")
            
            # 删除测试文件
            bucket.delete_object(test_key)
            print(f"      删除测试文件成功 ✓")
        except oss2.exceptions.AccessDenied:
            print("      无上传权限 (可能是只读配置)")
        except Exception as e:
            print(f"      上传测试失败: {e}")
        
        print("-" * 50)
        print("OSS连接测试完成 ✓")
        print(f"静态访问域名: {OSS_CONFIG['static_domain']}")
        print("=" * 50)
        return True
        
    except oss2.exceptions.ServerError as e:
        print(f"[错误] 服务器错误: {e}")
        return False
    except oss2.exceptions.RequestError as e:
        print(f"[错误] 请求错误 (网络问题): {e}")
        return False
    except Exception as e:
        print(f"[错误] 未知错误: {e}")
        return False


if __name__ == '__main__':
    success = test_oss_connection()
    exit(0 if success else 1)
