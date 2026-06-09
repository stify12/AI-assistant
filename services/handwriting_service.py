"""
模拟手写服务模块
基于 handright 库实现手写体文字生成，支持自定义背景图片和框选区域渲染
"""
import os
import io
import base64
import time
import tempfile
import shutil
import logging
import gc
import requests

from PIL import Image, ImageFont, ImageDraw

logger = logging.getLogger(__name__)

# 字体资源目录（优先使用 handwriting-web 的字体）
FONT_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'handwriting-web', 'backend', 'font_assets')
# 备用字体目录
FONT_ASSETS_FALLBACK = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font_assets')

# 项目临时目录
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp_handwriting')
os.makedirs(TEMP_DIR, exist_ok=True)

# 尝试导入 handright
try:
    from handright import Template, handwrite
    HANDRIGHT_AVAILABLE = True
except ImportError:
    HANDRIGHT_AVAILABLE = False
    logger.warning("handright 库未安装，手写生成功能不可用。请安装：pip install handright 或 pip install handrightbeta")


def get_font_dir():
    """获取可用的字体目录"""
    if os.path.isdir(FONT_ASSETS_DIR):
        fonts = [f for f in os.listdir(FONT_ASSETS_DIR) if f.endswith('.ttf')]
        if fonts:
            return FONT_ASSETS_DIR
    
    os.makedirs(FONT_ASSETS_FALLBACK, exist_ok=True)
    return FONT_ASSETS_FALLBACK


def list_fonts():
    """列出所有可用字体"""
    font_dir = get_font_dir()
    fonts = []
    if os.path.isdir(font_dir):
        for f in sorted(os.listdir(font_dir)):
            if f.lower().endswith('.ttf'):
                fonts.append({
                    'name': os.path.splitext(f)[0],
                    'filename': f,
                    'path': os.path.join(font_dir, f)
                })
    return fonts


def create_background_with_lines(width, height, line_spacing, top_margin, bottom_margin, 
                                  left_margin, right_margin, font_size, show_lines=True):
    """创建带横线的笔记本背景图"""
    image = Image.new('RGB', (width, height), 'white')
    if show_lines:
        draw = ImageDraw.Draw(image)
        y = top_margin + line_spacing
        while y < height - bottom_margin:
            draw.line((left_margin, y, width - right_margin, y), fill='#cccccc', width=1)
            y += line_spacing
    return image


def generate_handwriting_image(params):
    """
    生成手写图片
    
    Args:
        params: dict 包含以下字段:
            - text: 要生成的文字
            - font_name: 字体文件名
            - font_size: 字号
            - line_spacing: 行间距
            - left_margin, right_margin, top_margin, bottom_margin: 边距
            - word_spacing: 字间距
            - background_image_base64: 背景图片base64（可选）
            - render_region: 渲染区域 {x, y, width, height}（可选）
            - show_lines: 是否显示横线
            - width, height: 画布尺寸（无背景图时使用）
            - 各种 sigma 参数
    
    Returns:
        dict: { status, images: [base64...], message }
    """
    if not HANDRIGHT_AVAILABLE:
        return {
            'status': 'error',
            'message': 'handright 库未安装，无法生成手写图片。请在服务器执行：pip install handrightbeta'
        }
    
    text = params.get('text', '')
    if not text.strip():
        return {'status': 'error', 'message': '请输入要生成的文字'}
    
    # 字体
    font_name = params.get('font_name', '')
    font_size = int(params.get('font_size', 80))
    
    fonts = list_fonts()
    if not fonts:
        return {'status': 'error', 'message': '没有可用的字体文件，请将 .ttf 字体放入 font_assets 目录'}
    
    font_path = None
    for f in fonts:
        if f['filename'] == font_name or f['name'] == font_name:
            font_path = f['path']
            break
    if not font_path:
        font_path = fonts[0]['path']
    
    try:
        with open(font_path, 'rb') as f:
            font_content = f.read()
        font = ImageFont.truetype(io.BytesIO(font_content), size=font_size)
    except Exception as e:
        return {'status': 'error', 'message': f'字体加载出了点问题：{str(e)}'}
    
    # 边距和间距
    line_spacing = int(params.get('line_spacing', 120))
    left_margin = int(params.get('left_margin', 50))
    right_margin = int(params.get('right_margin', 50))
    top_margin = int(params.get('top_margin', 50))
    bottom_margin = int(params.get('bottom_margin', 50))
    word_spacing = int(params.get('word_spacing', 1))
    show_lines = params.get('show_lines', True)
    
    # 背景图片处理
    background_image_b64 = params.get('background_image_base64', '')
    background_image_url = params.get('background_image_url', '')
    render_region = params.get('render_region', None)
    
    original_bg = None
    if background_image_b64:
        # 使用用户上传的背景图（base64）
        try:
            if ',' in background_image_b64:
                background_image_b64 = background_image_b64.split(',', 1)[1]
            img_data = base64.b64decode(background_image_b64)
            original_bg = Image.open(io.BytesIO(img_data))
        except Exception as e:
            return {'status': 'error', 'message': f'背景图片处理出了点问题：{str(e)}'}
    elif background_image_url:
        # 从 URL 下载背景图
        try:
            resp = requests.get(background_image_url, timeout=15)
            resp.raise_for_status()
            original_bg = Image.open(io.BytesIO(resp.content))
        except Exception as e:
            return {'status': 'error', 'message': f'背景图片下载失败：{str(e)}'}
    
    if original_bg is not None:
        try:
            if original_bg.mode in ('RGBA', 'LA'):
                original_bg = original_bg.convert('RGB')
            
            if render_region:
                # 有框选区域：在指定区域内渲染手写文字
                rx = int(render_region.get('x', 0))
                ry = int(render_region.get('y', 0))
                rw = int(render_region.get('width', original_bg.width))
                rh = int(render_region.get('height', original_bg.height))
                
                # 创建渲染区域大小的白色背景
                region_bg = Image.new('RGB', (rw, rh), 'white')
                if show_lines:
                    draw = ImageDraw.Draw(region_bg)
                    y = top_margin + line_spacing
                    while y < rh - bottom_margin:
                        draw.line((left_margin, y, rw - right_margin, y), fill='#cccccc', width=1)
                        y += line_spacing
                
                background_image = region_bg
            else:
                # 无框选区域：直接在整个背景图上渲染
                background_image = original_bg
        except Exception as e:
            return {'status': 'error', 'message': f'背景图片处理出了点问题：{str(e)}'}
    else:
        # 无背景图，创建白色画布
        canvas_width = int(params.get('width', 2481))
        canvas_height = int(params.get('height', 3507))
        background_image = create_background_with_lines(
            canvas_width, canvas_height, line_spacing,
            top_margin, bottom_margin, left_margin, right_margin,
            font_size, show_lines
        )
    
    # sigma 参数
    line_spacing_sigma = int(params.get('line_spacing_sigma', 0))
    font_size_sigma = int(params.get('font_size_sigma', 2))
    word_spacing_sigma = int(params.get('word_spacing_sigma', 2))
    perturb_x_sigma = int(params.get('perturb_x_sigma', 3))
    perturb_y_sigma = int(params.get('perturb_y_sigma', 3))
    perturb_theta_sigma = float(params.get('perturb_theta_sigma', 0.05))
    
    try:
        template = Template(
            background=background_image,
            font=font,
            line_spacing=line_spacing,
            left_margin=left_margin,
            top_margin=top_margin,
            right_margin=right_margin - word_spacing * 2,
            bottom_margin=bottom_margin,
            word_spacing=word_spacing,
            line_spacing_sigma=line_spacing_sigma,
            font_size_sigma=font_size_sigma,
            word_spacing_sigma=word_spacing_sigma,
            end_chars="，。",
            perturb_x_sigma=perturb_x_sigma,
            perturb_y_sigma=perturb_y_sigma,
            perturb_theta_sigma=perturb_theta_sigma,
        )
        
        images = handwrite(text, template)
        
        result_images = []
        for i, im in enumerate(images):
            if original_bg and render_region:
                # 将手写结果合成回原始背景图
                composite = original_bg.copy()
                rx = int(render_region.get('x', 0))
                ry = int(render_region.get('y', 0))
                composite.paste(im, (rx, ry))
                im = composite
            
            buf = io.BytesIO()
            im.save(buf, format='PNG')
            buf.seek(0)
            b64 = base64.b64encode(buf.read()).decode('utf-8')
            result_images.append(b64)
            del im
            
            # 限制最多生成 20 页
            if i >= 19:
                break
        
        gc.collect()
        
        return {
            'status': 'success',
            'images': result_images,
            'page_count': len(result_images),
            'message': f'已生成 {len(result_images)} 页手写图片'
        }
        
    except Exception as e:
        logger.error(f"手写生成出错: {e}", exc_info=True)
        return {'status': 'error', 'message': f'生成过程中出了点问题：{str(e)}'}


def generate_answers_on_regions(params):
    """
    在背景图的多个热区内分别渲染手写答案，返回合成后的单张图片。
    特点：透明叠加（不覆盖原图内容），字号自适应热区大小。
    
    params:
        - background_image_url / background_image_base64: 背景图
        - font_name: 字体文件名
        - font_size: 基础字号（会根据热区自适应）
        - word_spacing: 字间距
        - show_lines: 是否显示横线
        - sigma 参数
        - modules: [{ answer, regions: [{ x, y, w, h }] }]
          其中 x/y/w/h 为归一化 0~1 比例坐标
    """
    if not HANDRIGHT_AVAILABLE:
        return {'status': 'error', 'message': 'handright 库未安装'}

    from handright import Template, handwrite
    import numpy as np

    modules = params.get('modules', [])
    if not modules:
        return {'status': 'error', 'message': '没有可渲染的小题数据'}

    # 加载背景图
    background_image_url = params.get('background_image_url', '')
    background_image_b64 = params.get('background_image_base64', '')

    original_bg = None
    if background_image_b64:
        try:
            if ',' in background_image_b64:
                background_image_b64 = background_image_b64.split(',', 1)[1]
            img_data = base64.b64decode(background_image_b64)
            original_bg = Image.open(io.BytesIO(img_data))
        except Exception as e:
            return {'status': 'error', 'message': f'背景图片处理失败：{e}'}
    elif background_image_url:
        try:
            resp = requests.get(background_image_url, timeout=15)
            resp.raise_for_status()
            original_bg = Image.open(io.BytesIO(resp.content))
        except Exception as e:
            return {'status': 'error', 'message': f'背景图片下载失败：{e}'}

    if original_bg is None:
        return {'status': 'error', 'message': '请提供背景图片'}

    if original_bg.mode in ('RGBA', 'LA'):
        original_bg = original_bg.convert('RGB')

    img_w, img_h = original_bg.size
    composite = original_bg.convert('RGBA')

    # 字体路径
    font_name = params.get('font_name', '')
    base_font_size = int(params.get('font_size', 60))
    font_path = None
    for d in [FONT_ASSETS_DIR, FONT_ASSETS_FALLBACK]:
        if font_name:
            p = os.path.join(d, font_name)
            if os.path.isfile(p):
                font_path = p
                break
    if not font_path:
        for d in [FONT_ASSETS_DIR, FONT_ASSETS_FALLBACK]:
            if os.path.isdir(d):
                for f in os.listdir(d):
                    if f.endswith('.ttf') or f.endswith('.otf'):
                        font_path = os.path.join(d, f)
                        break
            if font_path:
                break

    if not font_path:
        return {'status': 'error', 'message': '未找到可用字体'}

    # 全局参数
    word_spacing = int(params.get('word_spacing', 1))
    show_lines = params.get('show_lines', False)
    line_spacing_sigma = int(params.get('line_spacing_sigma', 0))
    font_size_sigma = int(params.get('font_size_sigma', 2))
    word_spacing_sigma = int(params.get('word_spacing_sigma', 2))
    perturb_x_sigma = int(params.get('perturb_x_sigma', 3))
    perturb_y_sigma = int(params.get('perturb_y_sigma', 3))
    perturb_theta_sigma = float(params.get('perturb_theta_sigma', 0.05))

    # 墨水颜色（深蓝黑色，模拟钢笔/中性笔）
    ink_color = params.get('ink_color', '#1a1a2e')

    rendered_count = 0
    font_cache = {}

    def get_font(size):
        if size not in font_cache:
            font_cache[size] = ImageFont.truetype(font_path, size=size)
        return font_cache[size]

    def estimate_text_layout(text, fs, avail_w, avail_h):
        """估算文字在给定字号下的行数和所需高度。
        考虑中英文混排：中文/符号占1个字宽，英文/数字占0.55个字宽。"""
        if fs <= 0 or avail_w <= 0:
            return 9999, 9999
        line_sp = int(fs * 1.6)
        # 计算每行可容纳的"等效中文字符数"
        chars_capacity = avail_w / fs
        # 计算文本的"等效中文字符宽度"
        text_width = 0
        num_lines = 1
        for ch in text:
            if ch == '\n':
                num_lines += 1
                text_width = 0
                continue
            # 英文字母、数字、基本标点占约0.55个字宽
            if ch.isascii() and ch not in ('，', '。', '；', '：', '！', '？'):
                cw = 0.55
            else:
                cw = 1.0
            text_width += cw
            if text_width > chars_capacity:
                num_lines += 1
                text_width = cw
        needed_h = num_lines * line_sp
        return num_lines, needed_h

    for mod in modules:
        answer = (mod.get('answer', '') or '').strip()
        if not answer:
            continue

        for region in mod.get('regions', []):
            # 归一化坐标 → 像素坐标
            rx = int(region.get('x', 0) * img_w)
            ry = int(region.get('y', 0) * img_h)
            rw = int(region.get('w', 0.1) * img_w)
            rh = int(region.get('h', 0.05) * img_h)

            if rw < 20 or rh < 20:
                continue

            # ---- 字号自适应（改进版） ----
            # 边距按热区大小自适应，最小10px，最大热区尺寸的5%
            margin = max(10, min(int(min(rw, rh) * 0.05), 30))
            available_w = rw - margin * 2
            available_h = rh - margin * 2

            if available_w < 10 or available_h < 10:
                continue

            # 初始字号：取 base_font_size，但不超过热区高度的40%
            font_size = min(base_font_size, int(rh * 0.4))
            font_size = max(font_size, 14)

            # 用二分法找到能让文字恰好放入热区的最大字号
            _, needed_h = estimate_text_layout(answer, font_size, available_w, available_h)
            if needed_h > available_h:
                lo, hi = 14, font_size
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    _, nh = estimate_text_layout(answer, mid, available_w, available_h)
                    if nh <= available_h:
                        lo = mid
                    else:
                        hi = mid - 1
                font_size = max(lo, 14)

            # 最终行距
            line_sp = int(font_size * 1.6)

            font = get_font(font_size)

            # ---- 在白色背景上渲染手写文字 ----
            region_bg = Image.new('RGB', (rw, rh), 'white')
            if show_lines:
                draw = ImageDraw.Draw(region_bg)
                y = margin + line_sp
                while y < rh - margin:
                    draw.line((margin, y, rw - margin, y), fill='#cccccc', width=1)
                    y += line_sp

            try:
                template = Template(
                    background=region_bg,
                    font=font,
                    line_spacing=line_sp,
                    left_margin=margin,
                    top_margin=margin,
                    right_margin=margin,
                    bottom_margin=margin,
                    word_spacing=word_spacing,
                    line_spacing_sigma=line_spacing_sigma,
                    font_size_sigma=min(font_size_sigma, max(1, font_size // 12)),
                    word_spacing_sigma=min(word_spacing_sigma, max(1, font_size // 15)),
                    end_chars="，。",
                    perturb_x_sigma=min(perturb_x_sigma, max(1, font_size // 10)),
                    perturb_y_sigma=min(perturb_y_sigma, max(1, font_size // 10)),
                    perturb_theta_sigma=min(perturb_theta_sigma, 0.03),
                )

                images = handwrite(answer, template)
                for im in images:
                    # ---- 透明叠加：提取笔迹，不覆盖原图 ----
                    # handwrite 输出是白底黑字的 RGB 图
                    # 将白色区域视为透明，深色区域视为墨水
                    im_arr = np.array(im.convert('L'), dtype=np.float32)
                    # alpha = 白色(255)时全透明(0)，黑色(0)时全不透明(255)
                    alpha = (255.0 - im_arr).clip(0, 255).astype(np.uint8)

                    # 解析墨水颜色
                    ic = ink_color.lstrip('#')
                    ink_r = int(ic[0:2], 16) if len(ic) >= 6 else 26
                    ink_g = int(ic[2:4], 16) if len(ic) >= 6 else 26
                    ink_h = int(ic[4:6], 16) if len(ic) >= 6 else 46

                    # 创建墨水色 RGBA 图层
                    ink_layer = Image.new('RGBA', (rw, rh), (ink_r, ink_g, ink_h, 0))
                    ink_layer.putalpha(Image.fromarray(alpha))

                    # 合成到 composite 的对应位置
                    composite.paste(ink_layer, (rx, ry), ink_layer)
                    rendered_count += 1
                    break  # 只取第一页
            except Exception as e:
                logger.warning(f"渲染小题答案失败: {e}")
                continue

    # 输出为 RGB PNG
    result_img = composite.convert('RGB')
    buf = io.BytesIO()
    result_img.save(buf, format='PNG')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')

    gc.collect()

    return {
        'status': 'success',
        'image': b64,
        'rendered_count': rendered_count,
        'message': f'已在 {rendered_count} 个热区渲染手写答案'
    }
