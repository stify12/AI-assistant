"""
阿里云OSS图片下载脚本
按时间段下载图片到本地
"""
import os
import oss2
from datetime import datetime, timedelta
import argparse

OSS_CONFIG = {
    'access_key_id': os.environ.get('OSS_ACCESS_KEY_ID', ''),
    'access_key_secret': os.environ.get('OSS_ACCESS_KEY_SECRET', ''),
    'endpoint': 'oss-cn-guangzhou.aliyuncs.com',
    'bucket_name': 'zpsmart',
    'static_domain': 'https://img.gzzhengpu.cn'
}


def get_bucket():
    """获取OSS Bucket对象"""
    auth = oss2.Auth(
        OSS_CONFIG['access_key_id'],
        OSS_CONFIG['access_key_secret']
    )
    return oss2.Bucket(
        auth,
        OSS_CONFIG['endpoint'],
        OSS_CONFIG['bucket_name']
    )


def download_by_time_range(
    start_time: datetime,
    end_time: datetime,
    prefix: str = '',
    output_dir: str = './oss_downloads',
    extensions: list = None,
    dry_run: bool = False,
    max_files: int = None
):
    """
    按时间段下载OSS中的文件
    
    Args:
        start_time: 开始时间
        end_time: 结束时间
        prefix: 文件路径前缀（如 'books/' 或 'homework/'）
        output_dir: 本地保存目录
        extensions: 文件扩展名过滤（如 ['.jpg', '.png', '.bmp']）
        dry_run: 仅预览不下载
        max_files: 最大下载文件数（None表示不限制）
    
    Returns:
        下载结果统计
    """
    bucket = get_bucket()
    
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']
    
    # 确保扩展名小写
    extensions = [ext.lower() for ext in extensions]
    
    print("=" * 60)
    print("OSS图片下载")
    print("=" * 60)
    print(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"路径前缀: {prefix or '(全部)'}")
    print(f"文件类型: {', '.join(extensions)}")
    print(f"保存目录: {output_dir}")
    print(f"模式: {'预览（不下载）' if dry_run else '下载'}")
    if max_files:
        print(f"最大文件数: {max_files}")
    print("-" * 60)
    
    # 创建输出目录
    if not dry_run and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 统计
    total_count = 0
    matched_count = 0
    downloaded_count = 0
    total_size = 0
    skipped_count = 0
    
    # 遍历文件
    for obj in oss2.ObjectIterator(bucket, prefix=prefix):
        total_count += 1
        
        # 检查扩展名
        file_ext = os.path.splitext(obj.key)[1].lower()
        if file_ext not in extensions:
            continue
        
        # 检查时间（OSS返回的是UTC时间）
        last_modified = datetime.fromtimestamp(obj.last_modified)
        if not (start_time <= last_modified <= end_time):
            continue
        
        matched_count += 1
        
        # 检查最大文件数
        if max_files and matched_count > max_files:
            print(f"\n已达到最大文件数限制 ({max_files})，停止...")
            break
        
        # 文件大小
        size_kb = obj.size / 1024
        total_size += obj.size
        
        # 构建本地路径（保持目录结构）
        local_path = os.path.join(output_dir, obj.key)
        local_dir = os.path.dirname(local_path)
        
        if dry_run:
            print(f"[预览] {obj.key} ({size_kb:.2f} KB) - {last_modified.strftime('%Y-%m-%d %H:%M')}")
        else:
            # 检查文件是否已存在
            if os.path.exists(local_path):
                skipped_count += 1
                print(f"[跳过] {obj.key} (已存在)")
                continue
            
            # 创建目录
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            
            # 下载文件
            try:
                bucket.get_object_to_file(obj.key, local_path)
                downloaded_count += 1
                print(f"[下载] {obj.key} ({size_kb:.2f} KB)")
            except Exception as e:
                print(f"[错误] {obj.key}: {e}")
    
    # 输出统计
    print("-" * 60)
    print(f"扫描文件总数: {total_count}")
    print(f"符合条件: {matched_count}")
    if not dry_run:
        print(f"已下载: {downloaded_count}")
        print(f"跳过（已存在）: {skipped_count}")
    print(f"总大小: {total_size / 1024 / 1024:.2f} MB")
    print("=" * 60)
    
    return {
        'total_scanned': total_count,
        'matched': matched_count,
        'downloaded': downloaded_count,
        'skipped': skipped_count,
        'total_size': total_size
    }


def download_today(prefix: str = '', output_dir: str = './oss_downloads', dry_run: bool = False):
    """下载今天的图片"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    return download_by_time_range(today, tomorrow, prefix, output_dir, dry_run=dry_run)


def download_recent_days(days: int = 7, prefix: str = '', output_dir: str = './oss_downloads', dry_run: bool = False):
    """下载最近N天的图片"""
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    return download_by_time_range(start_time, end_time, prefix, output_dir, dry_run=dry_run)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='阿里云OSS图片下载工具')
    parser.add_argument('--start', type=str, help='开始时间 (格式: YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', type=str, help='结束时间 (格式: YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--days', type=int, help='下载最近N天的图片')
    parser.add_argument('--today', action='store_true', help='下载今天的图片')
    parser.add_argument('--prefix', type=str, default='', help='路径前缀过滤 (如 books/ 或 homework/)')
    parser.add_argument('--output', type=str, default='./oss_downloads', help='本地保存目录')
    parser.add_argument('--ext', type=str, nargs='+', default=['.jpg', '.png', '.bmp'], help='文件扩展名')
    parser.add_argument('--max', type=int, help='最大下载文件数')
    parser.add_argument('--dry-run', action='store_true', help='仅预览不下载')
    
    args = parser.parse_args()
    
    # 解析时间
    def parse_time(time_str):
        if not time_str:
            return None
        try:
            if len(time_str) == 10:  # YYYY-MM-DD
                return datetime.strptime(time_str, '%Y-%m-%d')
            else:
                return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            print(f"时间格式错误: {time_str}")
            exit(1)
    
    if args.today:
        download_today(args.prefix, args.output, dry_run=args.dry_run)
    elif args.days:
        download_recent_days(args.days, args.prefix, args.output, dry_run=args.dry_run)
    elif args.start and args.end:
        start = parse_time(args.start)
        end = parse_time(args.end)
        download_by_time_range(
            start, end, 
            prefix=args.prefix, 
            output_dir=args.output,
            extensions=args.ext,
            dry_run=args.dry_run,
            max_files=args.max
        )
    else:
        print("请指定时间范围:")
        print("  --today              下载今天的图片")
        print("  --days N             下载最近N天的图片")
        print("  --start DATE --end DATE  指定时间范围")
        print("")
        print("示例:")
        print("  python oss_download.py --today --prefix books/ --dry-run")
        print("  python oss_download.py --days 7 --output ./downloads")
        print("  python oss_download.py --start 2026-03-01 --end 2026-03-04 --prefix homework/")
        print("  python oss_download.py --start 2026-03-01 --end 2026-03-04 --max 100 --dry-run")
