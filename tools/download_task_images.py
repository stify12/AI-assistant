"""
下载指定任务的所有学生作业图片
直接从OSS按路径规则下载图片
"""
import os
import oss2
from datetime import datetime

# OSS配置（从环境变量读取）
import os
OSS_CONFIG = {
    'access_key_id': os.environ.get('OSS_ACCESS_KEY_ID', ''),
    'access_key_secret': os.environ.get('OSS_ACCESS_KEY_SECRET', ''),
    'endpoint': 'oss-cn-guangzhou.aliyuncs.com',
    'bucket_name': 'zpsmart',
    'static_domain': 'https://img.gzzhengpu.cn',
    'oss_url': 'https://oss.gzzhengpu.cn'
}

# 任务信息
TASK_INFO = {
    'id': '2009075740562776066',
    'content': '袁崇焕中学校本作业.同步导学练.物理.八上',
    'bookId': '1997848714229166082',
    'pageRegion': '102,103,104,105,106,107,108',
    'studentCount': 53,
    'submitCount': 48
}


def get_bucket():
    """获取OSS Bucket对象"""
    auth = oss2.Auth(OSS_CONFIG['access_key_id'], OSS_CONFIG['access_key_secret'])
    return oss2.Bucket(auth, OSS_CONFIG['endpoint'], OSS_CONFIG['bucket_name'])


def download_task_images_from_oss(task_id, output_dir='./task_images', dry_run=False):
    """
    直接从OSS按任务ID搜索并下载图片
    搜索路径格式: homework/{task_id}/ 或 task/{task_id}/
    """
    print("=" * 60)
    print("从OSS下载任务图片")
    print("=" * 60)
    print(f"任务ID: {task_id}")
    print(f"任务名称: {TASK_INFO['content']}")
    print(f"页码范围: {TASK_INFO['pageRegion']}")
    print(f"模式: {'预览' if dry_run else '下载'}")
    print(f"保存目录: {output_dir}")
    print("-" * 60)
    
    bucket = get_bucket()
    
    # 可能的路径前缀
    prefixes = [
        f'homework/{task_id}/',
        f'task/{task_id}/',
        f'homeworks/{task_id}/',
        f'tasks/{task_id}/',
        f'zp/homework/{task_id}/',
    ]
    
    # 图片扩展名
    image_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')
    
    # 统计
    stats = {
        'total_found': 0,
        'downloaded': 0,
        'skipped': 0,
        'error': 0
    }
    
    # 创建输出目录
    task_output_dir = os.path.join(output_dir, task_id)
    if not dry_run and not os.path.exists(task_output_dir):
        os.makedirs(task_output_dir)
    
    print("\n[1/2] 搜索OSS中的图片...")
    all_images = []
    
    for prefix in prefixes:
        print(f"  搜索前缀: {prefix}")
        count = 0
        for obj in oss2.ObjectIterator(bucket, prefix=prefix):
            if obj.key.lower().endswith(image_exts):
                all_images.append(obj)
                count += 1
        if count > 0:
            print(f"    找到 {count} 张图片")
    
    stats['total_found'] = len(all_images)
    
    if not all_images:
        print("\n未找到图片，尝试搜索全部路径...")
        # 尝试搜索包含task_id的任意路径
        print(f"  搜索包含 {task_id} 的路径...")
        for obj in oss2.ObjectIterator(bucket):
            if task_id in obj.key and obj.key.lower().endswith(image_exts):
                all_images.append(obj)
                if len(all_images) >= 500:  # 限制搜索数量
                    print("    达到搜索上限(500)")
                    break
        stats['total_found'] = len(all_images)
    
    print(f"\n共找到 {len(all_images)} 张图片")
    
    if not all_images:
        print("未找到任何图片")
        return stats
    
    # 下载图片
    print(f"\n[2/2] {'预览' if dry_run else '下载'}图片...")
    for i, obj in enumerate(all_images):
        # 构建本地路径（保持目录结构）
        local_path = os.path.join(task_output_dir, obj.key.replace('/', os.sep))
        size_kb = obj.size / 1024
        
        if dry_run:
            print(f"  [{i+1}/{len(all_images)}] {obj.key} ({size_kb:.2f} KB)")
            continue
        
        # 检查是否已存在
        if os.path.exists(local_path):
            stats['skipped'] += 1
            print(f"  [{i+1}/{len(all_images)}] - {obj.key} (已存在)")
            continue
        
        # 创建目录
        local_dir = os.path.dirname(local_path)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
        
        # 下载
        try:
            bucket.get_object_to_file(obj.key, local_path)
            stats['downloaded'] += 1
            print(f"  [{i+1}/{len(all_images)}] ✓ {obj.key} ({size_kb:.2f} KB)")
        except Exception as e:
            stats['error'] += 1
            print(f"  [{i+1}/{len(all_images)}] ✗ {obj.key}: {e}")
    
    # 输出统计
    print("-" * 60)
    print("完成!")
    print(f"  找到图片: {stats['total_found']}")
    if not dry_run:
        print(f"  已下载: {stats['downloaded']}")
        print(f"  跳过: {stats['skipped']}")
        print(f"  错误: {stats['error']}")
        print(f"  保存位置: {task_output_dir}")
    print("=" * 60)
    
    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='从OSS下载任务图片')
    parser.add_argument('--task-id', type=str, default=TASK_INFO['id'], help='任务ID')
    parser.add_argument('--output', type=str, default='./task_images', help='保存目录')
    parser.add_argument('--dry-run', action='store_true', help='仅预览不下载')
    
    args = parser.parse_args()
    download_task_images_from_oss(args.task_id, args.output, dry_run=args.dry_run)
