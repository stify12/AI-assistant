"""检查处理后图片的上下边缘亮度"""
import cv2
import numpy as np

img = cv2.imread("test_output/v2_gentle.jpg", cv2.IMREAD_GRAYSCALE)
h, w = img.shape

print(f"图片尺寸: {w}x{h}")
print("\n顶部边缘亮度（前20行）：")
for row in range(0, 20, 2):
    line = img[row, :]
    print(f"  行{row}: mean={line.mean():.1f}, min={line.min()}, max={line.max()}")

print("\n底部边缘亮度（后20行）：")
for row in range(h-20, h, 2):
    line = img[row, :]
    print(f"  行{row}: mean={line.mean():.1f}, min={line.min()}, max={line.max()}")
