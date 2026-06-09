"""分析图片边缘亮度"""
import cv2
import numpy as np

image = cv2.imread("test_output/03_levels.jpg", cv2.IMREAD_GRAYSCALE)
h, w = image.shape

# 分析左侧边缘前50像素的亮度
print("左侧边缘亮度分析（前50列）：")
for col in range(0, 50, 5):
    line = image[:, col]
    print(f"  列{col}: mean={line.mean():.1f}, min={line.min()}, max={line.max()}")

# 分析处理后图片的左侧边缘
processed = cv2.imread("test_output/06_crop.jpg", cv2.IMREAD_GRAYSCALE)
print("\n处理后图片左侧边缘亮度：")
for col in range(0, 50, 5):
    line = processed[:, col]
    print(f"  列{col}: mean={line.mean():.1f}")
