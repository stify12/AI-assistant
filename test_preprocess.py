"""
本地测试图片预处理效果 - 尝试不同参数组合
"""
import cv2
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.image_preprocess_service import ImagePreprocessService

def test_params(image_path, output_dir="test_output"):
    """测试不同参数组合"""
    
    os.makedirs(output_dir, exist_ok=True)
    image = cv2.imread(image_path)
    if image is None:
        print(f"无法读取图片: {image_path}")
        return
    
    print(f"原图尺寸: {image.shape[1]}x{image.shape[0]}")
    cv2.imwrite(f"{output_dir}/00_original.jpg", image)
    
    # 方案1: 当前默认参数
    print("\n=== 方案1: 当前默认参数 ===")
    test_pipeline(image, output_dir, "v1_current", {
        'levels_black': 60, 'levels_white': 200, 'levels_gamma': 1.0,
        'bg_morph': 51, 'bg_strength': 0.9
    })
    
    # 方案2: 更温和的色阶
    print("\n=== 方案2: 更温和的色阶 ===")
    test_pipeline(image, output_dir, "v2_gentle", {
        'levels_black': 40, 'levels_white': 220, 'levels_gamma': 1.0,
        'bg_morph': 51, 'bg_strength': 0.9
    })
    
    # 方案3: 更强的背景净化
    print("\n=== 方案3: 更强的背景净化 ===")
    test_pipeline(image, output_dir, "v3_strong_bg", {
        'levels_black': 50, 'levels_white': 210, 'levels_gamma': 1.0,
        'bg_morph': 71, 'bg_strength': 1.0
    })
    
    # 方案4: 简化流程（只做背景净化+轻度色阶）
    print("\n=== 方案4: 简化流程 ===")
    test_pipeline(image, output_dir, "v4_simple", {
        'levels_black': 30, 'levels_white': 230, 'levels_gamma': 1.0,
        'bg_morph': 51, 'bg_strength': 0.8
    })
    
    print("\n完成！请比较各方案效果")

def test_pipeline(image, output_dir, name, params):
    """执行完整处理流程"""
    current = image.copy()
    
    # 灰度
    current = ImagePreprocessService.step_grayscale(current)
    
    # 背景净化
    current = ImagePreprocessService.step_background_clean(
        current, 
        morph_size=params['bg_morph'], 
        strength=params['bg_strength']
    )
    
    # 色阶
    current = ImagePreprocessService.step_levels(
        current,
        black_point=params['levels_black'],
        white_point=params['levels_white'],
        gamma=params['levels_gamma']
    )
    
    # 锐化
    current = ImagePreprocessService.step_sharpen(current, amount=2.0, radius=1, threshold=0)
    
    # 裁剪
    current = ImagePreprocessService.step_crop(current)
    
    output_path = f"{output_dir}/{name}.jpg"
    cv2.imwrite(output_path, current)
    print(f"  保存: {output_path}")

if __name__ == "__main__":
    test_params("test-picture/2016082317627400193_14_UC7P9.jpg")
