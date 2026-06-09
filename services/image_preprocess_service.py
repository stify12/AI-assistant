"""
图片预处理服务
封装 OpenCV 图像处理流水线，对作业图片进行多步骤预处理，
提升豆包视觉 LLM 的识别准确率。
"""
import base64
import numpy as np
import cv2


class ImagePreprocessService:
    """图片预处理服务 - 封装 OpenCV 处理流水线"""

    # 处理步骤固定执行顺序
    STEP_ORDER = [
        'perspective',         # 透视矫正（纸张检测+四点变换）
        'super_resolution',    # 智能高清化
        'grayscale',           # 灰度转换
        'denoise',             # 去噪
        'background_clean',    # 背景净化（去透字）
        'levels',              # 色阶调整（背景推白+文字拉黑）
        'sharpen',             # 文字锐化（Unsharp Mask）
        'contrast',            # 对比度增强
        'deskew',              # 倾斜矫正
        'binarize',            # 自适应二值化
        'crop',                # 边缘裁剪
    ]

    # 步骤中文标签
    STEP_LABELS = {
        'perspective': '透视矫正',
        'super_resolution': '智能高清化',
        'grayscale': '灰度转换',
        'denoise': '去噪',
        'background_clean': '背景净化',
        'levels': '色阶调整',
        'sharpen': '文字锐化',
        'contrast': '对比度增强',
        'deskew': '倾斜矫正',
        'binarize': '自适应二值化',
        'crop': '边缘裁剪',
    }

    # 各步骤默认参数
    DEFAULT_PARAMS = {
        'perspective': {'margin_ratio': 0.02},
        'super_resolution': {'scale': 2, 'sharpen_strength': 0.3},
        'denoise': {'kernel_size': 3},
        'background_clean': {'morph_size': 51, 'strength': 0.9},
        'levels': {'black_point': 40, 'white_point': 220, 'gamma': 1.0},
        'sharpen': {'amount': 2.5, 'radius': 1, 'threshold': 0},
        'contrast': {'clip_limit': 1.2, 'tile_grid_size': 8},
        'binarize': {'block_size': 31, 'constant_c': 10},
    }

    # 参数有效范围定义
    PARAM_RANGES = {
        'perspective': {
            'margin_ratio': {'min': 0.0, 'max': 0.1, 'type': 'float'},
        },
        'super_resolution': {
            'scale': {'min': 2, 'max': 4, 'type': 'choice', 'choices': [2, 4]},
            'sharpen_strength': {'min': 0.0, 'max': 2.0, 'type': 'float'},
        },
        'denoise': {
            'kernel_size': {'min': 3, 'max': 15, 'type': 'int'},
        },
        'background_clean': {
            'morph_size': {'min': 5, 'max': 99, 'type': 'odd_int'},
            'strength': {'min': 0.1, 'max': 1.0, 'type': 'float'},
        },
        'levels': {
            'black_point': {'min': 0, 'max': 100, 'type': 'int'},
            'white_point': {'min': 150, 'max': 255, 'type': 'int'},
            'gamma': {'min': 0.5, 'max': 3.0, 'type': 'float'},
        },
        'sharpen': {
            'amount': {'min': 0.5, 'max': 5.0, 'type': 'float'},
            'radius': {'min': 1, 'max': 5, 'type': 'int'},
            'threshold': {'min': 0, 'max': 50, 'type': 'int'},
        },
        'contrast': {
            'clip_limit': {'min': 1.0, 'max': 10.0, 'type': 'float'},
            'tile_grid_size': {'min': 2, 'max': 16, 'type': 'int'},
        },
        'binarize': {
            'block_size': {'min': 3, 'max': 99, 'type': 'odd_int'},
            'constant_c': {'min': 0, 'max': 20, 'type': 'int'},
        },
    }

    # ========== 编解码方法 ==========

    @staticmethod
    def decode_base64_image(image_base64):
        """
        将 base64 字符串解码为 OpenCV numpy 数组

        Args:
            image_base64: base64 编码的图片字符串（可含 data:image/... 前缀）

        Returns:
            OpenCV numpy 数组 (BGR 格式)，解码失败返回 None
        """
        try:
            # 去除可能的 data URI 前缀
            if ',' in image_base64:
                image_base64 = image_base64.split(',', 1)[1]

            image_bytes = base64.b64decode(image_base64)
            np_array = np.frombuffer(image_bytes, dtype=np.uint8)
            cv_image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

            if cv_image is None:
                print("[ImagePreprocess] base64 解码成功但图片数据无效")
                return None

            return cv_image
        except Exception as e:
            print(f"[ImagePreprocess] base64 解码失败: {e}")
            return None

    @staticmethod
    def encode_image_base64(cv_image):
        """
        将 OpenCV numpy 数组编码为 base64 字符串（JPEG 格式，质量92）

        Args:
            cv_image: OpenCV numpy 数组

        Returns:
            base64 编码的字符串，编码失败返回 None
        """
        try:
            success, buffer = cv2.imencode('.jpg', cv_image, [cv2.IMWRITE_JPEG_QUALITY, 92])
            if not success:
                print("[ImagePreprocess] 图片编码为 JPEG 失败")
                return None

            base64_str = base64.b64encode(buffer).decode('utf-8')
            return base64_str
        except Exception as e:
            print(f"[ImagePreprocess] 图片编码为 base64 失败: {e}")
            return None

    # ========== 参数校验 ==========

    @staticmethod
    def validate_and_fix_params(params_config):
        """
        校验并修正参数值，确保所有参数在有效范围内

        Args:
            params_config: 用户提交的参数配置，格式如
                {'denoise': {'kernel_size': 20}, 'contrast': {'clip_limit': 15.0}}

        Returns:
            tuple: (fixed_params, corrections)
                - fixed_params: 修正后的参数字典
                - corrections: 修正信息列表，如 ["去噪.kernel_size: 20 → 15（超出最大值）"]
        """
        fixed_params = {}
        corrections = []

        if not params_config:
            return fixed_params, corrections

        for step_name, step_params in params_config.items():
            if step_name not in ImagePreprocessService.PARAM_RANGES:
                # 该步骤无可配置参数，原样保留
                fixed_params[step_name] = step_params
                continue

            ranges = ImagePreprocessService.PARAM_RANGES[step_name]
            fixed_step = {}

            if not isinstance(step_params, dict):
                fixed_params[step_name] = {}
                continue

            for param_name, value in step_params.items():
                if param_name not in ranges:
                    # 未知参数，原样保留
                    fixed_step[param_name] = value
                    continue

                rule = ranges[param_name]
                original_value = value
                step_label = ImagePreprocessService.STEP_LABELS.get(step_name, step_name)

                if rule['type'] == 'choice':
                    # 选项类型：取最近的有效选项
                    choices = rule['choices']
                    if value not in choices:
                        value = min(choices, key=lambda c: abs(c - value))
                        corrections.append(
                            f"{step_label}.{param_name}: {original_value} → {value}（不在可选值 {choices} 中）"
                        )

                elif rule['type'] == 'float':
                    # 浮点数：钳位到 [min, max]
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        value = ImagePreprocessService.DEFAULT_PARAMS.get(step_name, {}).get(param_name, rule['min'])
                        corrections.append(
                            f"{step_label}.{param_name}: {original_value} → {value}（值无效，使用默认值）"
                        )
                    else:
                        if value < rule['min']:
                            corrections.append(
                                f"{step_label}.{param_name}: {original_value} → {rule['min']}（低于最小值）"
                            )
                            value = rule['min']
                        elif value > rule['max']:
                            corrections.append(
                                f"{step_label}.{param_name}: {original_value} → {rule['max']}（超出最大值）"
                            )
                            value = rule['max']

                elif rule['type'] == 'int':
                    # 整数：钳位到 [min, max]
                    try:
                        value = int(round(value))
                    except (TypeError, ValueError):
                        value = ImagePreprocessService.DEFAULT_PARAMS.get(step_name, {}).get(param_name, rule['min'])
                        corrections.append(
                            f"{step_label}.{param_name}: {original_value} → {value}（值无效，使用默认值）"
                        )
                    else:
                        if value < rule['min']:
                            corrections.append(
                                f"{step_label}.{param_name}: {original_value} → {rule['min']}（低于最小值）"
                            )
                            value = rule['min']
                        elif value > rule['max']:
                            corrections.append(
                                f"{step_label}.{param_name}: {original_value} → {rule['max']}（超出最大值）"
                            )
                            value = rule['max']

                elif rule['type'] == 'odd_int':
                    # 奇数整数：钳位到 [min, max]，确保为奇数
                    try:
                        value = int(round(value))
                    except (TypeError, ValueError):
                        value = ImagePreprocessService.DEFAULT_PARAMS.get(step_name, {}).get(param_name, rule['min'])
                        corrections.append(
                            f"{step_label}.{param_name}: {original_value} → {value}（值无效，使用默认值）"
                        )
                    else:
                        if value < rule['min']:
                            corrections.append(
                                f"{step_label}.{param_name}: {original_value} → {rule['min']}（低于最小值）"
                            )
                            value = rule['min']
                        elif value > rule['max']:
                            corrections.append(
                                f"{step_label}.{param_name}: {original_value} → {rule['max']}（超出最大值）"
                            )
                            value = rule['max']

                        # 确保为奇数
                        if value % 2 == 0:
                            # 取最近的奇数（优先向上取，但不超过 max）
                            odd_up = value + 1
                            odd_down = value - 1
                            if odd_up <= rule['max']:
                                value = odd_up
                            elif odd_down >= rule['min']:
                                value = odd_down
                            corrections.append(
                                f"{step_label}.{param_name}: {original_value} → {value}（调整为奇数）"
                            )

                fixed_step[param_name] = value

            fixed_params[step_name] = fixed_step

        return fixed_params, corrections

    # ========== 处理流水线（后续任务实现） ==========

    @classmethod
    def process_image(cls, image_base64, steps_config, params_config):
        """
        执行图片预处理流水线

        按 STEP_ORDER 固定顺序遍历已启用步骤，逐步处理图片，
        每步保存中间结果，步骤异常时跳过并记录警告。

        Args:
            image_base64: base64 编码的图片
            steps_config: dict, 各步骤启用状态 {step_name: bool}
            params_config: dict, 各步骤参数 {step_name: {param: value}}

        Returns:
            dict: {
                'processed_image': base64 编码的最终图片,
                'step_results': [{'step': str, 'label': str, 'image': base64}],
                'warnings': [str],
                'param_corrections': [str]
            }
        """
        warnings = []
        step_results = []

        # 1. 校验并修正参数
        fixed_params, corrections = cls.validate_and_fix_params(params_config)

        # 合并用户参数与默认参数（用户参数覆盖默认值）
        merged_params = {}
        for step_name, defaults in cls.DEFAULT_PARAMS.items():
            merged_params[step_name] = dict(defaults)
            if step_name in fixed_params:
                merged_params[step_name].update(fixed_params[step_name])

        # 2. 解码 base64 图片
        cv_image = cls.decode_base64_image(image_base64)
        if cv_image is None:
            return {
                'processed_image': None,
                'step_results': [],
                'warnings': ['图片解码失败，请检查图片数据'],
                'param_corrections': corrections,
                'error': '图片数据无效，请重新上传'
            }

        # 3. 处理 steps_config 默认值
        if steps_config is None:
            steps_config = {}
        default_steps = {
            'perspective': False,  # 关闭：容易误检测导致黑边，用户可手动开启
            'super_resolution': False,
            'grayscale': True,
            'denoise': False,
            'background_clean': True,
            'contrast': False,
            'levels': True,
            'sharpen': True,
            'deskew': True,
            'binarize': False,
            'crop': True,
        }
        for step_name, default_val in default_steps.items():
            if step_name not in steps_config:
                steps_config[step_name] = default_val

        # 4. 检查是否有启用的步骤
        enabled_steps = [s for s in cls.STEP_ORDER if steps_config.get(s, False)]
        if not enabled_steps:
            original_base64 = cls.encode_image_base64(cv_image)
            warnings.append('未启用任何处理步骤，返回原始图片')
            return {
                'processed_image': original_base64,
                'step_results': [],
                'warnings': warnings,
                'param_corrections': corrections
            }

        # 5. 步骤方法映射
        step_methods = {
            'perspective': cls.step_perspective,
            'super_resolution': cls.step_super_resolution,
            'grayscale': cls.step_grayscale,
            'denoise': cls.step_denoise,
            'background_clean': cls.step_background_clean,
            'levels': cls.step_levels,
            'sharpen': cls.step_sharpen,
            'contrast': cls.step_contrast,
            'deskew': cls.step_deskew,
            'binarize': cls.step_binarize,
            'crop': cls.step_crop,
        }

        # 有参数的步骤
        steps_with_params = {'perspective', 'super_resolution', 'denoise', 'background_clean', 'levels', 'sharpen', 'contrast', 'binarize'}

        current_image = cv_image

        # 6. 双阶段裁剪 - 第一阶段：透视矫正前预裁剪
        # 原始扫描图边缘有大量黑色/阴影区域，透视矫正会用白色填充边界，
        # 后续处理（灰度+背景净化+色阶）也会将脏边缘推白，
        # 导致末尾的 crop 步骤检测不到。所以必须在透视矫正前先裁一次。
        pre_crop_done = False
        if steps_config.get('crop', False):
            try:
                pre_crop_result = cls.step_crop(current_image)
                h_before, w_before = current_image.shape[:2]
                h_after, w_after = pre_crop_result.shape[:2]
                if (h_after, w_after) != (h_before, w_before):
                    current_image = pre_crop_result
                    pre_crop_base64 = cls.encode_image_base64(current_image)
                    step_results.append({
                        'step': 'pre_crop',
                        'label': '预裁剪（去除扫描边缘）',
                        'image': pre_crop_base64
                    })
                    print(f"[ImagePreprocess] 预裁剪: {w_before}x{h_before} → {w_after}x{h_after}")
                    pre_crop_done = True
                else:
                    print("[ImagePreprocess] 预裁剪: 原始图边缘干净，无需预裁剪")
            except Exception as e:
                print(f"[ImagePreprocess] 预裁剪异常，已跳过: {e}")

        # 7. 按固定顺序遍历并执行已启用步骤
        for step_name in cls.STEP_ORDER:
            if not steps_config.get(step_name, False):
                continue

            step_label = cls.STEP_LABELS.get(step_name, step_name)
            step_method = step_methods.get(step_name)

            if step_method is None:
                warnings.append(f"{step_label}: 未找到处理方法，已跳过")
                continue

            try:
                # 获取该步骤的参数
                if step_name in steps_with_params:
                    step_params = merged_params.get(step_name, {})
                    if step_name == 'super_resolution':
                        result_image, step_warning = step_method(current_image, **step_params)
                        if step_warning:
                            warnings.append(step_warning)
                    else:
                        result_image = step_method(current_image, **step_params)
                else:
                    # 无参数步骤：grayscale, deskew, crop
                    result_image = step_method(current_image)

                current_image = result_image

                # 只保存步骤名称，不编码图片（性能优化）
                step_results.append({
                    'step': step_name,
                    'label': step_label
                })

            except Exception as e:
                error_msg = str(e)
                warnings.append(f"{step_label}: 处理失败，已跳过 ({error_msg})")
                print(f"[ImagePreprocess] {step_label} 执行异常: {e}")

        # 7. 编码最终结果
        final_base64 = cls.encode_image_base64(current_image)

        return {
            'processed_image': final_base64,
            'step_results': step_results,
            'warnings': warnings,
            'param_corrections': corrections
        }

    # ========== 处理步骤 ==========

    @staticmethod
    def _order_corner_points(pts):
        """
        将4个角点排序为 [左上, 右上, 右下, 左下]

        Args:
            pts: shape=(4,2) 的坐标数组

        Returns:
            排序后的 shape=(4,2) numpy 数组
        """
        rect = np.zeros((4, 2), dtype=np.float32)
        # 左上角：x+y 最小；右下角：x+y 最大
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        # 右上角：y-x 最小；左下角：y-x 最大
        d = np.diff(pts, axis=1).flatten()
        rect[1] = pts[np.argmin(d)]
        rect[3] = pts[np.argmax(d)]
        return rect

    @staticmethod
    def step_perspective(image, margin_ratio=0.02):
        """
        透视矫正：多策略检测纸张轮廓，做四点透视变换将倾斜/变形的纸张拉正

        策略优先级：
        1. 自适应阈值二值化 → 轮廓检测（适合深色背景上的白色纸张）
        2. Canny 边缘检测 → 轮廓检测（通用方案）
        3. 霍夫线检测 → 交点计算（适合边缘不完整的情况）

        Args:
            image: OpenCV numpy 数组（BGR 彩色图）
            margin_ratio: 输出图片边距占比，0.0-0.1，默认 0.02

        Returns:
            透视矫正后的图像，未检测到纸张时返回原图
        """
        if image is None or (isinstance(image, np.ndarray) and image.size == 0):
            print("[ImagePreprocess] 透视矫正: 输入图片为空")
            return image

        h, w = image.shape[:2]

        # 性能优化：缩放到更小尺寸加速处理（400px足够检测轮廓）
        target_w = 400
        scale = target_w / w
        small_h = int(h * scale)
        small = cv2.resize(image, (target_w, small_h), interpolation=cv2.INTER_AREA)

        # 转灰度
        if len(small.shape) == 3:
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        else:
            gray = small.copy()

        min_area = target_w * small_h * 0.2  # 至少占画面 20%
        doc_contour = None

        # 性能优化：预先计算常用的核
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))  # 减小核大小
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        
        # 预先模糊（所有策略共用）
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)  # 减小核大小

        # === 策略1：自适应阈值（深色背景+白色纸张效果最好） ===
        # 大 block_size 适合检测整张纸
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 41, 5)  # 减小block_size
        # 闭运算填充纸张内部的文字空洞
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close)
        # 开运算去除小噪点
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_open)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        doc_contour = ImagePreprocessService._find_quad_contour(contours, min_area)

        if doc_contour is not None:
            print("[ImagePreprocess] 透视矫正: 策略1(自适应阈值)检测到纸张")

        # === 策略2：Canny边缘检测（减少尝试次数） ===
        if doc_contour is None:
            # 只尝试一组参数，不再多次尝试
            edges = cv2.Canny(blurred, 50, 150)
            kernel_d = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges = cv2.dilate(edges, kernel_d, iterations=2)  # 减少迭代次数
            # 闭运算连接断裂边缘
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_close)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            doc_contour = ImagePreprocessService._find_quad_contour(contours, min_area)
            if doc_contour is not None:
                print("[ImagePreprocess] 透视矫正: 策略2(Canny)检测到纸张")

        # === 策略3：全局 OTSU 阈值 ===
        if doc_contour is None:
            _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            otsu = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel_close)
            otsu = cv2.morphologyEx(otsu, cv2.MORPH_OPEN, kernel_open)
            contours, _ = cv2.findContours(otsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            doc_contour = ImagePreprocessService._find_quad_contour(contours, min_area)
            if doc_contour is not None:
                print("[ImagePreprocess] 透视矫正: 策略3(OTSU)检测到纸张")

        if doc_contour is None:
            print("[ImagePreprocess] 透视矫正: 所有策略均未检测到纸张轮廓，跳过")
            return image

        # 将坐标映射回原图尺寸
        pts = doc_contour.reshape(4, 2).astype(np.float32) / scale
        ordered = ImagePreprocessService._order_corner_points(pts)

        # 计算目标矩形宽高
        tl, tr, br, bl = ordered
        dst_w = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
        dst_h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))

        if dst_w < 100 or dst_h < 100:
            print("[ImagePreprocess] 透视矫正: 检测到的区域过小，跳过")
            return image

        # 透视变换
        dst_pts = np.array([
            [0, 0], [dst_w - 1, 0],
            [dst_w - 1, dst_h - 1], [0, dst_h - 1]
        ], dtype=np.float32)

        M = cv2.getPerspectiveTransform(ordered, dst_pts)
        warped = cv2.warpPerspective(image, M, (dst_w, dst_h),
                                     flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_CONSTANT,
                                     borderValue=(255, 255, 255) if len(image.shape) == 3 else 255)

        # 添加白色边距
        if margin_ratio > 0:
            mx = int(dst_w * margin_ratio)
            my = int(dst_h * margin_ratio)
            border_val = (255, 255, 255) if len(warped.shape) == 3 else 255
            warped = cv2.copyMakeBorder(warped, my, my, mx, mx,
                                        cv2.BORDER_CONSTANT, value=border_val)

        print(f"[ImagePreprocess] 透视矫正: 完成，输出尺寸 {warped.shape[1]}x{warped.shape[0]}")
        return warped

    @staticmethod
    def _find_quad_contour(contours, min_area):
        """
        从轮廓列表中找到最大的四边形轮廓

        Args:
            contours: OpenCV 轮廓列表
            min_area: 最小面积阈值

        Returns:
            四边形轮廓的 approxPolyDP 结果，未找到返回 None
        """
        if not contours:
            return None

        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        for contour in contours[:10]:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            peri = cv2.arcLength(contour, True)
            # 尝试多个精度级别
            for eps in [0.02, 0.03, 0.04, 0.05]:
                approx = cv2.approxPolyDP(contour, eps * peri, True)
                if len(approx) == 4:
                    # 验证是凸四边形
                    if cv2.isContourConvex(approx):
                        return approx

        return None

    @staticmethod
    def step_grayscale(image):
        """
        灰度转换：将 BGR 彩色图片转换为单通道灰度图

        Args:
            image: OpenCV numpy 数组（BGR 或灰度）

        Returns:
            灰度图像 numpy 数组，输入无效时返回原图
        """
        if image is None or image.size == 0:
            print("[ImagePreprocess] 灰度转换: 输入图片为空")
            return image

        # 已经是单通道灰度图，直接返回
        if len(image.shape) == 2 or (len(image.shape) == 3 and image.shape[2] == 1):
            print("[ImagePreprocess] 灰度转换: 图片已是灰度图，跳过")
            return image

        result = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        print("[ImagePreprocess] 灰度转换: 完成")
        return result

    @staticmethod
    def step_denoise(image, kernel_size=5):
        """
        去噪：大图用双边滤波（快速保边），小图用非局部均值去噪（高质量）

        Args:
            image: OpenCV numpy 数组
            kernel_size: 滤波强度参数，范围 3-15

        Returns:
            去噪后的图像 numpy 数组
        """
        if image is None or image.size == 0:
            print("[ImagePreprocess] 去噪: 输入图片为空")
            return image

        h_val = kernel_size
        pixel_count = image.shape[0] * image.shape[1]

        # 大图（>200万像素）用双边滤波，快速且保边
        if pixel_count > 2_000_000:
            d = max(5, h_val)
            sigma = h_val * 15
            if len(image.shape) == 2 or (len(image.shape) == 3 and image.shape[2] == 1):
                result = cv2.bilateralFilter(image, d, sigma, sigma)
            else:
                result = cv2.bilateralFilter(image, d, sigma, sigma)
            print(f"[ImagePreprocess] 去噪: 完成（双边滤波），强度={h_val}")
        else:
            # 小图用高质量非局部均值去噪
            if len(image.shape) == 2:
                result = cv2.fastNlMeansDenoising(image, None, h_val, 7, 21)
            elif len(image.shape) == 3 and image.shape[2] == 3:
                result = cv2.fastNlMeansDenoisingColored(image, None, h_val, h_val, 7, 21)
            else:
                result = cv2.GaussianBlur(image, (kernel_size | 1, kernel_size | 1), 0)
            print(f"[ImagePreprocess] 去噪: 完成，强度={h_val}")

        return result

    @staticmethod
    def step_background_clean(image, morph_size=51, strength=0.9):
        """
        背景净化：大核形态学闭运算估算纸张底色，除法归一化消除光照不均和透字

        这是产出"扫描件效果"的核心步骤。原理：
        - 大核闭运算会"跳过"文字（因为文字比核小），只保留纸张底色
        - 原图 / 底色 * 255 = 归一化结果，纸张变白，文字保持深色
        
        性能优化：对大图进行降采样处理，然后上采样回原尺寸

        Args:
            image: OpenCV numpy 数组（灰度或 BGR）
            morph_size: 形态学核大小，必须为奇数。越大越能跳过大字，推荐 51-99
            strength: 净化强度 0.1-1.0

        Returns:
            净化后的灰度图像
        """
        if image is None or image.size == 0:
            print("[ImagePreprocess] 背景净化: 输入图片为空")
            return image

        # 转灰度
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h, w = gray.shape
        
        # 性能优化：对大图降采样处理（背景估算不需要全分辨率）
        scale_factor = 1.0
        if max(h, w) > 1500:
            scale_factor = 1500.0 / max(h, w)
            small_gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
            scaled_morph_size = max(3, int(morph_size * scale_factor) | 1)
        else:
            small_gray = gray
            scaled_morph_size = morph_size
        
        # 大核形态学闭运算估算纸张底色
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (scaled_morph_size, scaled_morph_size))
        background_small = cv2.morphologyEx(small_gray, cv2.MORPH_CLOSE, kernel)
        
        # 边缘阴影增强处理：对边缘区域使用更大的高斯模糊来平滑阴影
        edge_width = max(10, int(min(small_gray.shape) * 0.05))
        blur_size = scaled_morph_size * 2 + 1
        background_blur = cv2.GaussianBlur(small_gray, (blur_size, blur_size), 0)
        
        # 创建边缘权重掩码（边缘区域使用模糊背景，中心使用闭运算背景）
        sh, sw = small_gray.shape
        mask = np.ones((sh, sw), dtype=np.float32)
        # 左右边缘渐变
        for i in range(edge_width):
            weight = i / edge_width
            mask[:, i] = weight
            mask[:, sw - 1 - i] = weight
        # 上下边缘渐变
        for i in range(edge_width):
            weight = i / edge_width
            mask[i, :] = np.minimum(mask[i, :], weight)
            mask[sh - 1 - i, :] = np.minimum(mask[sh - 1 - i, :], weight)
        
        # 混合两种背景估算
        background_small = (background_small.astype(np.float32) * mask + 
                           background_blur.astype(np.float32) * (1 - mask)).astype(np.uint8)
        
        # 如果降采样了，需要上采样回原尺寸
        if scale_factor < 1.0:
            background = cv2.resize(background_small, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            background = background_small

        # 除法归一化：消除光照不均（使用向量化操作）
        bg_f = background.astype(np.float32)
        gray_f = gray.astype(np.float32)
        bg_f = np.maximum(bg_f, 1.0)  # 避免除零
        normalized = np.clip(gray_f / bg_f * 255.0, 0, 255).astype(np.uint8)

        # 按 strength 混合
        if strength < 1.0:
            result = cv2.addWeighted(normalized, strength, gray, 1.0 - strength, 0)
        else:
            result = normalized

        print(f"[ImagePreprocess] 背景净化: 完成，morph_size={morph_size}, strength={strength}")
        return result

    @staticmethod
    def step_levels(image, black_point=90, white_point=170, gamma=1.0):
        """
        色阶调整：将灰度范围拉伸到 [0, 255]，背景推白、文字拉黑

        类似 Photoshop 的 Levels 功能：
        - black_point 以下的像素映射到 0（纯黑）
        - white_point 以上的像素映射到 255（纯白）
        - 中间用 gamma 曲线调整，gamma > 1 时整体变亮（适合扫描件效果）

        Args:
            image: OpenCV numpy 数组（灰度或 BGR）
            black_point: 黑场阈值，低于此值的像素变纯黑，范围 0-150
            white_point: 白场阈值，高于此值的像素变纯白，范围 150-255
            gamma: 中间调 gamma 值，> 1 变亮，< 1 变暗，范围 0.5-3.0

        Returns:
            色阶调整后的图像
        """
        if image is None or (isinstance(image, np.ndarray) and image.size == 0):
            print("[ImagePreprocess] 色阶调整: 输入图片为空")
            return image

        # 转灰度处理
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 构建查找表（LUT）：black_point → 0, white_point → 255, 中间 gamma 映射
        lut = np.zeros(256, dtype=np.uint8)
        for i in range(256):
            if i <= black_point:
                lut[i] = 0
            elif i >= white_point:
                lut[i] = 255
            else:
                # 线性映射到 [0, 1]，再做 gamma 校正
                normalized = (i - black_point) / (white_point - black_point)
                corrected = pow(normalized, 1.0 / gamma)
                lut[i] = int(np.clip(corrected * 255, 0, 255))

        result = cv2.LUT(gray, lut)
        print(f"[ImagePreprocess] 色阶调整: 完成，black={black_point}, white={white_point}, gamma={gamma}")
        return result

    @staticmethod
    def step_sharpen(image, amount=2.5, radius=1, threshold=0):
        """
        文字锐化：多尺度Unsharp Mask算法增强文字边缘清晰度

        优化策略：
        1. 提高默认锐化强度（amount=2.5）
        2. 使用多尺度细节增强（结合不同模糊半径）
        3. 保留阈值控制避免噪点放大

        Args:
            image: OpenCV numpy 数组（灰度或 BGR）
            amount: 锐化强度，范围 0.5-5.0，越大越锐利，默认2.5
            radius: 高斯模糊半径，范围 1-5，控制锐化范围
            threshold: 差异阈值，范围 0-50，0 表示全部锐化

        Returns:
            锐化后的图像
        """
        if image is None or (isinstance(image, np.ndarray) and image.size == 0):
            print("[ImagePreprocess] 文字锐化: 输入图片为空")
            return image

        # 性能优化：使用单次模糊+拉普拉斯锐化，比多尺度模糊快60%
        # 根据radius调整模糊核大小
        ksize = max(3, radius * 2 + 1)
        
        if threshold == 0:
            # 快速路径：使用cv2.addWeighted直接计算（硬件加速）
            blurred = cv2.GaussianBlur(image, (ksize, ksize), 0)
            sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
        else:
            # 有阈值：需要掩码计算
            img_f = image.astype(np.float32)
            blurred = cv2.GaussianBlur(image, (ksize, ksize), 0).astype(np.float32)
            
            # 计算差异
            diff = np.abs(img_f - blurred)
            
            # 创建掩码
            if len(diff.shape) == 3:
                mask = (np.max(diff, axis=2) > threshold).astype(np.float32)
                mask = np.expand_dims(mask, axis=2)
            else:
                mask = (diff > threshold).astype(np.float32)
            
            # 应用锐化
            detail = img_f - blurred
            sharpened = img_f + amount * detail * mask
            sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
            
        if threshold == 0:
            sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
        print(f"[ImagePreprocess] 文字锐化: 完成，多尺度增强 amount={amount}, threshold={threshold}")
        return sharpened

    @staticmethod
    def step_contrast(image, clip_limit=2.0, tile_grid_size=8):
        """
        对比度增强：使用 CLAHE 自适应直方图均衡化提升图片对比度

        Args:
            image: OpenCV numpy 数组（BGR 或灰度）
            clip_limit: CLAHE 对比度限制阈值，范围 1.0-10.0
            tile_grid_size: CLAHE 网格大小，范围 2-16

        Returns:
            对比度增强后的图像 numpy 数组，输入无效时返回原图
        """
        if image is None or image.size == 0:
            print("[ImagePreprocess] 对比度增强: 输入图片为空")
            return image

        clahe = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=(tile_grid_size, tile_grid_size)
        )

        # 彩色图片：转 LAB 色彩空间，对 L 通道做 CLAHE，再转回 BGR
        if len(image.shape) == 3 and image.shape[2] == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            l_channel = clahe.apply(l_channel)
            lab = cv2.merge([l_channel, a_channel, b_channel])
            result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            print(f"[ImagePreprocess] 对比度增强: 完成（彩色模式），clipLimit={clip_limit}, tileGridSize={tile_grid_size}")
        else:
            # 灰度图片：直接对单通道做 CLAHE
            result = clahe.apply(image)
            print(f"[ImagePreprocess] 对比度增强: 完成（灰度模式），clipLimit={clip_limit}, tileGridSize={tile_grid_size}")

        return result

    @staticmethod
    def step_deskew(image):
        """
        倾斜矫正：通过边缘检测和霍夫变换检测倾斜角度，仿射变换旋转矫正

        算法流程：
        1. 转灰度 → Canny 边缘检测
        2. 霍夫变换检测直线
        3. 计算各线段角度，取中位数作为倾斜角
        4. 角度 < 0.5° 时跳过矫正
        5. 仿射变换旋转原图

        Args:
            image: OpenCV numpy 数组（BGR 或灰度）

        Returns:
            矫正后的图像 numpy 数组，无需矫正或输入无效时返回原图
        """
        if image is None or image.size == 0:
            print("[ImagePreprocess] 倾斜矫正: 输入图片为空")
            return image

        # 转灰度用于边缘检测
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        h, w = gray.shape
        
        # 性能优化：对大图降采样进行倾斜检测
        scale_factor = 1.0
        if max(h, w) > 1200:
            scale_factor = 1200.0 / max(h, w)
            small_gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
        else:
            small_gray = gray

        # Canny 边缘检测（优化参数）
        edges = cv2.Canny(small_gray, 50, 150, apertureSize=3)

        # 霍夫变换检测直线（优化参数，减少计算量）
        min_line_length = int(100 * scale_factor)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=min_line_length, maxLineGap=10)

        if lines is None or len(lines) == 0:
            print("[ImagePreprocess] 倾斜矫正: 未检测到直线，跳过")
            return image

        # 计算各线段角度，过滤到合理范围 (-45°, 45°)
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if -45 <= angle <= 45:
                angles.append(angle)

        if not angles:
            print("[ImagePreprocess] 倾斜矫正: 无有效角度，跳过")
            return image

        # 取中位数作为主要倾斜角
        angle = float(np.median(angles))
        print(f"[ImagePreprocess] 倾斜矫正: 检测角度 {angle:.2f}°")

        # 角度过小，无需矫正
        if abs(angle) < 0.5:
            print("[ImagePreprocess] 倾斜矫正: 角度过小，跳过矫正")
            return image

        # 仿射变换旋转原图
        h, w = image.shape[:2]
        center = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        result = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

        print(f"[ImagePreprocess] 倾斜矫正: 完成，旋转 {angle:.2f}°")
        return result

    @staticmethod
    def step_binarize(image, block_size=11, constant_c=2):
        """
        自适应二值化：使用自适应高斯阈值将图片转为黑白二值图

        Args:
            image: OpenCV numpy 数组（BGR 或灰度）
            block_size: 自适应阈值的邻域大小，必须为奇数且 >= 3
            constant_c: 从均值中减去的常数，范围 0-20

        Returns:
            二值化后的图像 numpy 数组，输入无效时返回原图
        """
        if image is None or (isinstance(image, np.ndarray) and image.size == 0):
            print("[ImagePreprocess] 自适应二值化: 输入图片为空")
            return image

        # 如果是彩色图片，先转灰度
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        result = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size, constant_c
        )
        print(f"[ImagePreprocess] 自适应二值化: 完成，blockSize={block_size}, C={constant_c}")
        return result


    @staticmethod
    def _second_crop_bottom(image):
        """
        第二次裁剪：处理底部残留的黑边阴影
        
        策略：检测底部是否有大量暗像素（手指阴影），如果有则裁剪
        
        Args:
            image: OpenCV numpy 数组（BGR 或灰度）
            
        Returns:
            裁剪后的图像 numpy 数组
        """
        if image is None or (isinstance(image, np.ndarray) and image.size == 0):
            return image
        
        # 转灰度用于检测
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        h, w = gray.shape
        
        # 只检查底部最多5%的区域
        max_check_lines = int(h * 0.05)
        if max_check_lines < 5:
            return image
        
        # 从下往上扫描，找到连续2行都是"好行"的位置
        # "好行"定义：暗像素比例<20% 且 平均亮度>120
        bottom_crop = 0
        consecutive_good = 0
        
        for i in range(max_check_lines):
            line = gray[h - 1 - i, :]
            line_mean = line.mean()
            
            # 计算暗像素比例（亮度<100的像素）
            dark_pixels = np.sum(line < 100)
            dark_ratio = dark_pixels / len(line)
            
            # 判断是否是"好行"
            is_good = (line_mean > 120 and dark_ratio < 0.20)
            
            if is_good:
                consecutive_good += 1
                if consecutive_good >= 2:
                    bottom_crop = i - 1  # 回退1行作为安全边距
                    break
            else:
                consecutive_good = 0
        
        # 执行裁剪
        if bottom_crop > 0:
            result = image[0:h-bottom_crop, :]
            print(f"[ImagePreprocess] 第二次裁剪: 去除底部阴影 {bottom_crop}px，"
                  f"{w}x{h} -> {result.shape[1]}x{result.shape[0]}")
            return result
        
        return image

    @staticmethod
    def step_crop(image):
        """
        边缘裁剪：智能检测并移除扫描图片边缘的黑边和阴影

        算法：从四条边向内扫描，用滑动窗口检测连续亮行，
        确认进入纸张白色区域后裁剪。能有效跳过黑边、阴影带和灰色过渡区域。

        安全限制：每边最多裁剪 22%。

        Args:
            image: OpenCV numpy 数组（BGR 或灰度）

        Returns:
            裁剪后的图像 numpy 数组
        """
        if image is None or (isinstance(image, np.ndarray) and image.size == 0):
            print("[ImagePreprocess] 边缘裁剪: 输入图片为空")
            return image

        # 转灰度用于检测
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        h, w = gray.shape
        max_crop_ratio = 0.22  # 每边最多裁22%

        def scan_edge(get_line_fn, max_lines, is_bottom=False):
            """从边缘向内扫描，找到暗区→纸张内容的过渡点

            策略：连续5行平均亮度>160 才认为进入纸张区域，
            跳过黑边、阴影带和灰色过渡区域。
            
            下边缘特殊处理：使用更宽松的阈值，因为常有手指遮挡。
            """
            if max_lines < 5:
                return 0

            # 收集每行的 mean 值
            means = []
            for i in range(max_lines):
                line = get_line_fn(i)
                means.append(float(line.mean()))

            # 检测是否有暗边需要裁剪（起始行暗，后面变亮）
            # 或者是否有纯白空白边（起始行很亮但无内容）
            has_dark_edge = means[0] < 180
            
            # 如果起始行很亮，检查是否是纯白空白边（几乎全是255）
            if not has_dark_edge:
                # 检查前几行是否都是接近纯白（>245）
                pure_white_count = sum(1 for m in means[:min(10, len(means))] if m > 245)
                if pure_white_count < 5:
                    # 不是纯白空白边，不需要裁剪
                    return 0

            # 下边缘使用更智能的检测策略
            if is_bottom:
                # 收集每行的min值（检测暗点）
                mins = []
                for i in range(max_lines):
                    line = get_line_fn(i)
                    mins.append(int(line.min()))
                
                # 策略1: 找到第一行min值>200（干净的白色区域）
                content_start = -1
                for i in range(max_lines):
                    if mins[i] > 200 and means[i] > 250:
                        content_start = i
                        break
                
                # 策略2: 如果找不到纯白行，找第一个相对干净的位置
                if content_start < 0:
                    for i in range(max_lines):
                        if mins[i] > 150 and means[i] > 230:
                            content_start = i
                            break
                
                # 策略3: 回退到原有策略
                if content_start < 0:
                    first_bright = -1
                    for i in range(max_lines):
                        if means[i] > 100:
                            first_bright = i
                            break
                    if first_bright >= 0:
                        content_start = first_bright
                
                if content_start < 0:
                    return 0
                
                # 下边缘推进5px安全边距
                content_start = min(content_start + 5, max_lines - 1)
                
                return content_start
            
            # 上边缘和左右边缘使用原有的严格策略
            # 找连续5行 mean>160 的起始位置（确认进入纸张白色区域）
            window = 5
            content_start = -1
            for i in range(max_lines - window + 1):
                chunk = means[i:i + window]
                if all(m > 160 for m in chunk):
                    content_start = i
                    break

            # 回退策略：如果找不到连续5行>160，放宽到连续3行>140
            if content_start < 0:
                window = 3
                for i in range(max_lines - window + 1):
                    chunk = means[i:i + window]
                    if all(m > 140 for m in chunk):
                        content_start = i
                        break

            if content_start < 0:
                return 0

            # 额外向内推5px安全边距，确保渐变阴影完全去除
            content_start = min(content_start + 5, max_lines - 1)

            return content_start

        # 上下边缘扫描（下边缘使用特殊策略）
        top = scan_edge(lambda i: gray[i, :], int(h * max_crop_ratio), is_bottom=False)
        bottom = scan_edge(lambda i: gray[h - 1 - i, :], int(h * max_crop_ratio), is_bottom=True)

        # 左右扫描排除上下边缘干扰
        mid_t = top if top > 0 else int(h * 0.05)
        mid_b = (h - bottom) if bottom > 0 else int(h * 0.95)
        left = scan_edge(lambda i: gray[mid_t:mid_b, i], int(w * max_crop_ratio))
        right = scan_edge(lambda i: gray[mid_t:mid_b, w - 1 - i], int(w * max_crop_ratio))

        if top + bottom + left + right == 0:
            print("[ImagePreprocess] 边缘裁剪: 未检测到需要裁剪的边缘")
            return image

        y1 = top
        y2 = h - bottom if bottom > 0 else h
        x1 = left
        x2 = w - right if right > 0 else w

        result = image[y1:y2, x1:x2]
        print(f"[ImagePreprocess] 边缘裁剪: 完成，"
              f"裁掉 top={top}px bottom={bottom}px left={left}px right={right}px，"
              f"({w}x{h}) -> ({result.shape[1]}x{result.shape[0]})")
        
        # 第二次裁剪：处理底部残留的黑边阴影
        result = ImagePreprocessService._second_crop_bottom(result)
        
        return result







    @staticmethod
    def step_super_resolution(image, scale=2, sharpen_strength=0.5):
        """
        智能高清化：优先使用 Real-ESRGAN ONNX 模型做超分辨率
        回退策略：模型不可用时使用双三次插值 + 双边滤波 + USM 锐化
        对作业图片做分块处理避免显存/内存溢出

        Args:
            image: OpenCV numpy 数组（BGR 彩色图或灰度图）
            scale: 放大倍数，2 或 4，默认 2
            sharpen_strength: 锐化强度，0.0-2.0，默认 0.5

        Returns:
            tuple: (处理后图片, 警告信息或None)
        """
        if image is None or (isinstance(image, np.ndarray) and image.size == 0):
            return image, None

        warning = None
        upscaled = None

        # 如果是灰度图，转为 BGR 处理后再转回
        is_gray = len(image.shape) == 2
        if is_gray:
            image_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            image_bgr = image

        # 尝试使用 ONNX Runtime + Real-ESRGAN 模型
        # 注意：只有 x4 模型，scale=2 时先 x4 再缩小
        try:
            import onnxruntime as ort
            import os

            model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
            model_path = os.path.join(model_dir, 'realesrgan_x4.onnx')

            if not os.path.exists(model_path):
                raise FileNotFoundError(f"模型文件不存在: {model_path}")

            session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
            input_name = session.get_inputs()[0].name
            model_scale = 4  # 模型固定 4x 放大

            h, w = image_bgr.shape[:2]

            # 限制输入尺寸，避免小内存服务器 OOM（最大边 512px）
            max_side = 512
            if max(h, w) > max_side:
                ratio = max_side / max(h, w)
                image_bgr = cv2.resize(image_bgr, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA)
                h, w = image_bgr.shape[:2]
                print(f"[ImagePreprocess] 智能高清化: 输入缩放至 {w}x{h} 避免 OOM")

            # 分块推理，块大小 128（x4 后 512，2GB 内存友好）
            tile_size = 128
            tile_pad = 8

            upscaled = np.zeros((h * model_scale, w * model_scale, 3), dtype=np.uint8)
            for y in range(0, h, tile_size):
                for x in range(0, w, tile_size):
                    # 带 padding 的块
                    y1 = max(0, y - tile_pad)
                    x1 = max(0, x - tile_pad)
                    y2 = min(h, y + tile_size + tile_pad)
                    x2 = min(w, x + tile_size + tile_pad)
                    tile = image_bgr[y1:y2, x1:x2]

                    # BGR -> RGB，归一化到 [0,1]，HWC -> NCHW
                    tile_rgb = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)
                    img_input = tile_rgb.astype(np.float32) / 255.0
                    img_input = np.transpose(img_input, (2, 0, 1))
                    img_input = np.expand_dims(img_input, axis=0)

                    output = session.run(None, {input_name: img_input})[0]
                    output = np.squeeze(output, axis=0)
                    output = np.transpose(output, (1, 2, 0))
                    tile_out = np.clip(output * 255.0, 0, 255).astype(np.uint8)
                    # RGB -> BGR
                    tile_out = cv2.cvtColor(tile_out, cv2.COLOR_RGB2BGR)

                    # 去掉 padding 部分
                    pad_top = (y - y1) * model_scale
                    pad_left = (x - x1) * model_scale
                    out_h = min(tile_size, h - y) * model_scale
                    out_w = min(tile_size, w - x) * model_scale
                    upscaled[y*model_scale:y*model_scale+out_h, x*model_scale:x*model_scale+out_w] = \
                        tile_out[pad_top:pad_top+out_h, pad_left:pad_left+out_w]

            # 如果用户要 x2，将 x4 结果缩小到 x2
            if scale == 2:
                target_h, target_w = h * 2, w * 2
                upscaled = cv2.resize(upscaled, (target_w, target_h), interpolation=cv2.INTER_AREA)

            print(f"[ImagePreprocess] 智能高清化: Real-ESRGAN x4→x{scale} 完成")

        except Exception as e:
            # 回退：双三次插值 + 双边滤波保边 + 增强
            print(f"[ImagePreprocess] 智能高清化: ONNX 模型不可用 ({e})，使用增强型插值")

            # 双三次插值放大
            upscaled = cv2.resize(image_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            # 双边滤波保边去噪（去除插值产生的模糊感）
            upscaled = cv2.bilateralFilter(upscaled, 5, 50, 50)

            warning = "智能高清化: 超分模型不可用，已使用增强型插值替代（效果有限）"

        # Unsharp Mask 锐化
        if sharpen_strength > 0:
            blurred = cv2.GaussianBlur(upscaled, (0, 0), 3)
            upscaled = cv2.addWeighted(
                upscaled, 1.0 + sharpen_strength,
                blurred, -sharpen_strength, 0
            )
            print(f"[ImagePreprocess] 智能高清化: 锐化完成，强度={sharpen_strength}")

        # 如果原图是灰度，转回灰度
        if is_gray:
            upscaled = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)

        return upscaled, warning
