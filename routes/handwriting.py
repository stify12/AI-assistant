"""
模拟手写路由模块
提供手写生成页面和 API
"""
import logging
from flask import Blueprint, request, jsonify, render_template

from services.handwriting_service import list_fonts, generate_handwriting_image, generate_answers_on_regions, HANDRIGHT_AVAILABLE
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

handwriting_bp = Blueprint('handwriting', __name__)

SUBJECT_MAP = {
    0: '英语', 1: '语文', 2: '数学', 3: '物理',
    4: '化学', 5: '生物', 6: '地理'
}


@handwriting_bp.route('/handwriting')
def handwriting_page():
    """模拟手写工具页面"""
    return render_template('handwriting.html')


@handwriting_bp.route('/api/handwriting/fonts', methods=['GET'])
def get_fonts():
    """获取可用字体列表"""
    fonts = list_fonts()
    return jsonify({
        'status': 'success',
        'fonts': fonts,
        'handright_available': HANDRIGHT_AVAILABLE
    })


@handwriting_bp.route('/api/handwriting/generate', methods=['POST'])
def generate():
    """生成手写图片"""
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': '请提供参数'}), 400
    
    result = generate_handwriting_image(data)
    
    if result['status'] == 'error':
        return jsonify(result), 400
    
    return jsonify(result)


@handwriting_bp.route('/api/handwriting/books', methods=['GET'])
def get_books():
    """获取书本列表，按学科分组"""
    subject_id = request.args.get('subject_id', type=int)
    try:
        sql = """
            SELECT DISTINCT b.id as book_id, b.book_name, b.subject_id,
                   COUNT(DISTINCT c.page_num) as page_count
            FROM zp_make_book b
            LEFT JOIN zp_book_chapter c ON b.id = c.book_id
            WHERE 1=1
        """
        params = []
        if subject_id is not None:
            sql += " AND b.subject_id = %s"
            params.append(subject_id)
        sql += " GROUP BY b.id, b.book_name, b.subject_id ORDER BY b.subject_id, b.book_name"

        rows = DatabaseService.execute_query(sql, tuple(params) if params else None)

        result = {}
        for row in rows:
            sid = str(row['subject_id'])
            if sid not in result:
                result[sid] = []
            result[sid].append({
                'book_id': str(row['book_id']),
                'book_name': row['book_name'] or '未知书本',
                'subject_id': row['subject_id'],
                'subject_name': SUBJECT_MAP.get(row['subject_id'], '未知'),
                'page_count': row['page_count'] or 0
            })

        return jsonify({'success': True, 'data': result, 'subject_map': SUBJECT_MAP})
    except Exception as e:
        logger.error(f"[Handwriting] 获取书本列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@handwriting_bp.route('/api/handwriting/books/<book_id>/pages', methods=['GET'])
def get_book_pages(book_id):
    """获取书本的页码和对应图片"""
    try:
        sql = """
            SELECT DISTINCT c.page_num, c.pic_path
            FROM zp_book_chapter c
            WHERE c.book_id = %s AND c.page_num IS NOT NULL
            ORDER BY c.page_num
        """
        rows = DatabaseService.execute_query(sql, (book_id,))

        pages = []
        seen = set()
        for row in rows:
            pn = row['page_num']
            if pn and pn not in seen:
                seen.add(pn)
                pages.append({
                    'page_num': pn,
                    'pic_path': row.get('pic_path', '')
                })

        return jsonify({'success': True, 'data': {'book_id': book_id, 'pages': pages}})
    except Exception as e:
        logger.error(f"[Handwriting] 获取页码列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


def _fallback_region(idx, total, answer):
    """当没有 point 坐标时，按答案长度估算热区位置"""
    answer_len = len(answer) if answer else 0
    cols = 2 if total > 4 else 1
    col_w = 0.44 if cols == 2 else 0.90
    col_gap = 0.04
    start_x_list = [0.03, 0.03 + col_w + col_gap] if cols == 2 else [0.05]

    if answer_len <= 5:
        region_h = 0.025
    elif answer_len <= 15:
        region_h = 0.035
    elif answer_len <= 40:
        region_h = 0.05
    elif answer_len <= 80:
        region_h = 0.065
    else:
        region_h = 0.08

    col_idx = idx % cols
    row_idx = idx // cols
    x_start = start_x_list[col_idx]
    y_start = 0.10 + row_idx * (region_h + 0.008)
    if y_start + region_h > 0.95:
        y_start = 0.95 - region_h

    return {'x': round(x_start, 4), 'y': round(y_start, 4),
            'w': round(col_w, 4), 'h': round(region_h, 4)}


@handwriting_bp.route('/api/handwriting/parse-questions', methods=['POST'])
def parse_questions():
    """从数据库 data_value 解析该页的小题结构"""
    data = request.get_json() or {}
    book_id = data.get('book_id', '')
    page_num = data.get('page_num')

    if not book_id or page_num is None:
        return jsonify({'success': False, 'error': '缺少 book_id 或 page_num'}), 400

    try:
        from services.testcase_generator_service import TestcaseGeneratorService
        result = TestcaseGeneratorService.get_questions_from_datavalue(book_id, int(page_num))

        if not result.get('success'):
            return jsonify({'success': False, 'error': result.get('error', '解析失败')})

        raw_questions = result['data'].get('questions', [])
        total = len(raw_questions)

        # 获取原始图片尺寸（用于归一化坐标）
        img_w, img_h = 0, 0
        for q in raw_questions:
            size_str = q.get('size', '')
            if size_str:
                try:
                    parts = str(size_str).split(',')
                    img_w, img_h = float(parts[0]), float(parts[1])
                except:
                    pass
                break

        # 转换为前端热区模块格式
        questions = []

        for i, q in enumerate(raw_questions):
            answer = q.get('answer', '') or ''
            point = q.get('point')

            # 使用 data_value 中的 point 坐标生成精确热区
            if point and img_w > 0 and img_h > 0:
                try:
                    px = float(point.get('start_x', 0))
                    py = float(point.get('start_y', 0))
                    pw = float(point.get('width', 0))
                    ph = float(point.get('height', 0))

                    # 像素坐标 → 归一化坐标 (0~1)
                    nx = max(0, px / img_w)
                    ny = max(0, py / img_h)
                    nw = min(1 - nx, pw / img_w)
                    nh = min(1 - ny, ph / img_h)

                    regions = [{'x': round(nx, 4), 'y': round(ny, 4),
                                'w': round(nw, 4), 'h': round(nh, 4)}]
                except (ValueError, TypeError):
                    regions = [_fallback_region(i, total, answer)]
            else:
                regions = [_fallback_region(i, total, answer)]

            questions.append({
                'id': q.get('index', str(i + 1)),
                'label': f"第{q.get('index', i + 1)}题",
                'content': q.get('content', '') or '',
                'answer': answer,
                'maxScore': q.get('maxScore'),
                'regions': regions
            })

        return jsonify({
            'success': True,
            'questions': questions,
            'total': total,
            'picPath': result['data'].get('picPath', ''),
            'imgSize': {'w': img_w, 'h': img_h} if img_w > 0 else None
        })
    except Exception as e:
        logger.error(f"[Handwriting] 解析小题失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@handwriting_bp.route('/api/handwriting/generate-answers', methods=['POST'])
def generate_answers():
    """在背景图的热区内批量渲染手写答案"""
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': '请提供参数'}), 400

    logger.info(f"[Handwriting] generate-answers 请求: modules={len(data.get('modules', []))}, "
                f"has_url={bool(data.get('background_image_url'))}, has_b64={bool(data.get('background_image_base64'))}")

    result = generate_answers_on_regions(data)

    logger.info(f"[Handwriting] generate-answers 结果: status={result.get('status')}, "
                f"message={result.get('message', '')}")

    if result['status'] == 'error':
        return jsonify(result), 400

    return jsonify(result)
