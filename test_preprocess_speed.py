"""
测试图片预处理速度
"""
import time
import requests
import base64
from services.image_preprocess_service import ImagePreprocessService

def test_preprocess_speed():
    """测试图片预处理的速度"""
    
    # 测试图片URL（使用一个典型的作业图片）
    test_image_url = "http://oss.bnuz.edu.cn/rfid/2024-12-26/1735188349_6.jpg"
    
    print("=" * 60)
    print("图片预处理速度测试")
    print("=" * 60)
    print(f"测试图片: {test_image_url}")
    print()
    
    # 1. 下载图片
    print("[1/3] 下载图片...")
    start_download = time.time()
    response = requests.get(test_image_url, timeout=30)
    response.raise_for_status()
    image_base64 = base64.b64encode(response.content).decode('utf-8')
    download_time = time.time() - start_download
    print(f"  下载耗时: {download_time:.2f}秒")
    print(f"  图片大小: {len(response.content) / 1024:.1f} KB")
    print()
    
    # 2. 执行预处理（使用默认参数）
    print("[2/3] 执行预处理（默认参数）...")
    start_preprocess = time.time()
    
    result = ImagePreprocessService.process_image(
        image_base64,
        steps_config=None,  # 使用默认步骤
        params_config=None   # 使用默认参数
    )
    
    preprocess_time = time.time() - start_preprocess
    print(f"  预处理耗时: {preprocess_time:.2f}秒")
    print()
    
    # 3. 显示各步骤耗时（如果有step_results）
    if result.get('step_results'):
        print("[3/3] 各步骤详情:")
        for step_info in result['step_results']:
            step_name = step_info.get('step', 'unknown')
            step_label = step_info.get('label', step_name)
            print(f"  ✓ {step_label} ({step_name})")
        print()
    
    # 4. 总结
    total_time = download_time + preprocess_time
    print("=" * 60)
    print("测试总结:")
    print(f"  下载时间: {download_time:.2f}秒")
    print(f"  预处理时间: {preprocess_time:.2f}秒")
    print(f"  总耗时: {total_time:.2f}秒")
    print()
    
    if total_time <= 20:
        print(f"  ✓ 性能良好！总耗时 {total_time:.2f}秒 <= 20秒目标")
    else:
        print(f"  ✗ 需要优化！总耗时 {total_time:.2f}秒 > 20秒目标")
        print(f"  需要优化: {total_time - 20:.2f}秒")
    
    print("=" * 60)
    
    return {
        'download_time': download_time,
        'preprocess_time': preprocess_time,
        'total_time': total_time,
        'success': result.get('processed_image') is not None
    }

if __name__ == '__main__':
    try:
        test_preprocess_speed()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
