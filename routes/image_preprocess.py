"""
图片预处理路由模块
提供图片预处理工具页面、图片处理 API 和 LLM 视觉识别对比 API
"""
import base64

from flask import Blueprint, request, jsonify, render_template

from services.image_preprocess_service import ImagePreprocessService
from services.llm_service import LLMService

image_preprocess_bp = Blueprint('image_preprocess', __name__)

# 图片大小上限：10MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# JPG/PNG 魔术字节
MAGIC_BYTES_JPG = b'\xff\xd8\xff'
MAGIC_BYTES_PNG = b'\x89PNG\r\n\x1a\n'


def _validate_image_base64(image_base64):
    """
    校验 base64 图片数据的格式和大小

    Args:
        image_base64: base64 编码的图片字符串（可含 data:image/... 前缀）

    Returns:
        tuple: (is_valid, error_message)
            - is_valid: 校验是否通过
            - error_message: 失败时的错误信息，成功时为 None
    """
    if not image_base64 or not isinstance(image_base64, str):
        return False, '图片数据不能为空'

    # 去除 data URI 前缀
    raw_base64 = image_base64
    if ',' in raw_base64:
        raw_base64 = raw_base64.split(',', 1)[1]

    # 校验大小：base64 字符串长度 * 3/4 ≈ 原始字节数
    estimated_size = len(raw_base64) * 3 / 4
    if estimated_size > MAX_IMAGE_SIZE:
        return False, f'文件大小不能超过 10MB（当前约 {estimated_size / 1024 / 1024:.1f}MB）'

    # 尝试 base64 解码
    try:
        image_bytes = base64.b64decode(raw_base64)
    except Exception:
        return False, '图片数据无效，base64 解码失败'

    # 校验魔术字节：JPG 或 PNG
    if not (image_bytes[:3] == MAGIC_BYTES_JPG or image_bytes[:8] == MAGIC_BYTES_PNG):
        return False, '仅支持 JPG/PNG 格式图片'

    return True, None


# ========== 页面路由 ==========

@image_preprocess_bp.route('/image-preprocess')
def image_preprocess_page():
    """渲染图片预处理工具页面"""
    return render_template('image-preprocess.html')


# ========== API 路由 ==========

@image_preprocess_bp.route('/api/image-preprocess/process', methods=['POST'])
def process_image():
    """
    图片预处理 API

    请求体:
    {
        "image": "base64编码的图片数据",
        "steps": {"grayscale": true, "denoise": true, ...},
        "params": {"denoise": {"kernel_size": 5}, ...}
    }

    返回:
    {
        "success": true,
        "data": {
            "processed_image": "base64...",
            "step_results": [...],
            "warnings": [...],
            "param_corrections": [...],
            "processing_time": 0.123
        }
    }
    """
    import time
    
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'})

        image_base64 = data.get('image', '')
        steps_config = data.get('steps', None)
        params_config = data.get('params', None)

        # 校验图片数据
        is_valid, error_msg = _validate_image_base64(image_base64)
        if not is_valid:
            print(f"[ImagePreprocess] 图片校验失败: {error_msg}")
            return jsonify({'success': False, 'error': error_msg})

        # 计时开始
        start_time = time.time()
        
        # 调用服务层处理
        result = ImagePreprocessService.process_image(image_base64, steps_config, params_config)
        
        # 计时结束
        processing_time = time.time() - start_time
        result['processing_time'] = processing_time
        
        print(f"[ImagePreprocess] 处理完成，耗时: {processing_time*1000:.2f} ms")

        # 检查服务层是否返回错误
        if result.get('error'):
            return jsonify({'success': False, 'error': result['error']})

        return jsonify({'success': True, 'data': result})

    except Exception as e:
        print(f"[ImagePreprocess] 处理异常: {e}")
        return jsonify({'success': False, 'error': str(e)})


@image_preprocess_bp.route('/api/image-preprocess/recognize', methods=['POST'])
def recognize_compare():
    """
    LLM 视觉识别对比 API

    请求体:
    {
        "original_image": "base64...",
        "processed_image": "base64...",
        "prompt": "请识别图片中的作业答案..."
    }

    返回:
    {
        "success": true,
        "data": {
            "original_result": "原图识别文本...",
            "processed_result": "处理后识别文本..."
        }
    }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'})

        original_image = data.get('original_image', '')
        processed_image = data.get('processed_image', '')
        prompt = data.get('prompt', '请识别图片中的作业内容')

        if not original_image:
            return jsonify({'success': False, 'error': '原始图片不能为空'})
        if not processed_image:
            return jsonify({'success': False, 'error': '处理后图片不能为空'})

        # 分别调用 LLM 视觉模型识别，单独 try/except 以支持部分结果返回
        original_result = None
        processed_result = None
        original_error = None
        processed_error = None

        try:
            original_result = LLMService.call_vision_model(original_image, prompt)
            print("[ImagePreprocess] 原图识别完成")
        except Exception as e:
            original_error = f"原图识别失败: {str(e)}"
            print(f"[ImagePreprocess] {original_error}")

        try:
            processed_result = LLMService.call_vision_model(processed_image, prompt)
            print("[ImagePreprocess] 处理后图片识别完成")
        except Exception as e:
            processed_error = f"处理后图片识别失败: {str(e)}"
            print(f"[ImagePreprocess] {processed_error}")

        # 两个都失败
        if original_error and processed_error:
            return jsonify({
                'success': False,
                'error': f"{original_error}；{processed_error}"
            })

        # 构建返回数据
        result_data = {
            'original_result': original_result if original_result else original_error,
            'processed_result': processed_result if processed_result else processed_error,
        }

        return jsonify({'success': True, 'data': result_data})

    except Exception as e:
        print(f"[ImagePreprocess] 识别对比异常: {e}")
        return jsonify({'success': False, 'error': str(e)})


