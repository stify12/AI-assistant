"""
文本工具模块
提供文本处理、JSON解析等工具函数
"""
import re
import json


def normalize_answer(text):
    """
    标准化答案，用于比较AI批改结果和基准效果
    处理：空格、换行、中英文标点、数学符号等
    
    核心原则：移除所有不影响答案语义的标点符号和空白字符
    """
    if not text:
        return ''
    
    text = str(text).strip()
    
    # 1. 统一大小写
    text = text.lower()
    
    # 2. 移除HTML标签（如 <br>）
    text = re.sub(r'<[^>]+>', '', text)
    
    # 3. 将换行符和制表符替换为空格（而不是直接移除）
    text = text.replace('\\n', ' ').replace('\\r', ' ').replace('\\t', ' ')
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # 4. 移除markdown格式标记
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'`([^`]+)`', r'\1', text)        # `code`
    
    # 5. 统一数学符号（保留这些符号，因为它们影响语义）
    math_symbol_map = {
        '×': '*', '÷': '/', '−': '-', '＋': '+',
        '＝': '=', '≠': '!=', '≤': '<=', '≥': '>=',
        '√': 'sqrt', '∞': 'inf', 'π': 'pi',
        '°': 'deg', '′': "'", '″': '"'
    }
    for symbol, replacement in math_symbol_map.items():
        text = text.replace(symbol, replacement)
    
    # 6. 移除所有中英文标点符号（不影响答案语义的）
    # 包括：句号、逗号、分号、冒号、问号、感叹号、引号、括号、顿号等
    punctuation_to_remove = [
        # 中文标点
        '，', '。', '；', '：', '！', '？', '"', '"', ''', ''',
        '（', '）', '【', '】', '《', '》', '、', '～', '—', '…',
        '·', '「', '」', '『', '』', '〈', '〉', '〔', '〕', '｛', '｝',
        # 英文标点
        ',', '.', ';', ':', '!', '?', '"', "'", '(', ')', '[', ']',
        '{', '}', '<', '>', '~', '-', '_', '/', '\\', '|', '@', '#',
        '$', '%', '^', '&', '`'
    ]
    for punct in punctuation_to_remove:
        text = text.replace(punct, '')
    
    # 7. 移除序号标记周围的多余空格（如 ① ② 等）
    text = re.sub(r'\s*([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮])\s*', r'\1', text)
    
    # 8. 移除所有空白字符（空格、换行等不影响答案语义）
    text = re.sub(r'\s+', '', text)
    
    return text


def normalize_answer_strict(text):
    """
    严格标准化答案，只保留核心内容
    用于更宽松的比较场景
    """
    if not text:
        return ''
    
    # 先进行基本标准化
    text = normalize_answer(text)
    
    # 移除所有标点符号
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
    
    return text


def extract_json_from_text(content):
    """从文本中提取 JSON 对象"""
    if not content:
        return None
    
    # 移除思考过程标签
    content = remove_think_tags(content)
    
    try:
        # 尝试直接解析
        return json.loads(content)
    except:
        pass
    
    # 尝试提取 JSON 对象
    try:
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    return None


def extract_json_array(content):
    """从文本中提取 JSON 数组"""
    if not content:
        return None
    
    # 移除思考过程标签
    content = remove_think_tags(content)
    
    try:
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    return None


def remove_think_tags(content):
    """移除思考过程标签"""
    if not content:
        return content
    return re.sub(r'<think>[\s\S]*?</think>', '', content).strip()


def has_format_diff(text1, text2):
    """检查是否存在格式差异（空格、换行符、markdown等）"""
    if not text1 or not text2:
        return False
    # 如果标准化后相同，但原始文本不同，说明存在格式差异
    return normalize_answer(text1) == normalize_answer(text2) and str(text1).strip() != str(text2).strip()


def truncate_text(text, max_length=100, suffix='...'):
    """截断文本"""
    if not text:
        return ''
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def clean_html_tags(html):
    """移除 HTML 标签"""
    if not html:
        return ''
    return re.sub(r'<[^>]+>', '', html)


def extract_score_from_text(content):
    """从文本中提取评分"""
    if not content:
        return None
    
    # 尝试匹配 "评分：X" 或 "评分: X" 格式
    score_match = re.search(r'评分[：:]\s*(\d+)', content)
    if score_match:
        score = int(score_match.group(1))
        return max(1, min(10, score))  # 确保在 1-10 范围内
    
    return None


def extract_reason_from_text(content):
    """从文本中提取理由"""
    if not content:
        return ''
    
    reason_match = re.search(r'理由[：:]\s*(.+)', content, re.DOTALL)
    if reason_match:
        return reason_match.group(1).strip()
    
    return ''


def calculate_similarity(text1, text2):
    """
    计算两个文本的相似度（轻量级方案：字符n-gram + 序列匹配）
    
    不依赖jieba/sklearn，内存占用极低，同时能识别：
    1. 语义差异："古桥" vs "立交桥" → 较低相似度（不同字符）
    2. 词序差异："①②③" vs "①③②" → 较低相似度（序列不同）
    
    算法：使用字符级2-gram的Jaccard相似度 + SequenceMatcher序列相似度
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
        
    Returns:
        float: 相似度值 (0-1)
    """
    from difflib import SequenceMatcher
    
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    
    # 先标准化文本
    norm1 = normalize_answer(text1)
    norm2 = normalize_answer(text2)
    
    if norm1 == norm2:
        return 1.0
    
    # 如果文本太短，直接用序列匹配
    if len(norm1) < 3 or len(norm2) < 3:
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    # 1. 字符级2-gram Jaccard相似度（捕捉局部特征/语义差异）
    def get_ngrams(text, n=2):
        """生成字符级n-gram集合"""
        return set(text[i:i+n] for i in range(len(text) - n + 1))
    
    ngrams1 = get_ngrams(norm1, 2)
    ngrams2 = get_ngrams(norm2, 2)
    
    if not ngrams1 or not ngrams2:
        jaccard_sim = 0.0
    else:
        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)
        jaccard_sim = intersection / union if union > 0 else 0.0
    
    # 2. 序列相似度（捕捉顺序差异）
    seq_sim = SequenceMatcher(None, norm1, norm2).ratio()
    
    # 3. 混合：50% n-gram Jaccard + 50% 序列相似度
    # 这样既能识别内容差异，也能识别顺序差异
    similarity = 0.5 * jaccard_sim + 0.5 * seq_sim
    return float(similarity)


def calculate_char_similarity(text1, text2):
    """
    计算两个文本的字符级相似度（旧方法，保留备用）
    使用 SequenceMatcher 算法，返回 0-1 之间的相似度值
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
        
    Returns:
        float: 相似度值 (0-1)
    """
    from difflib import SequenceMatcher
    
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    
    norm1 = normalize_answer(text1)
    norm2 = normalize_answer(text2)
    
    if norm1 == norm2:
        return 1.0
    
    return SequenceMatcher(None, norm1, norm2).ratio()


def is_fuzzy_match(text1, text2, threshold=0.80):
    """
    判断两个文本是否模糊匹配（语义相似度达到阈值）
    
    使用 TF-IDF 语义相似度，能更好地识别语义差异：
    - "古桥没有很高价值" vs "立交桥没有很高价值" → 不匹配（语义不同）
    - "答案是A" vs "答案是a" → 匹配（语义相同）
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
        threshold: 相似度阈值，默认 0.85 (85%)
        
    Returns:
        tuple: (is_match: bool, similarity: float)
    """
    similarity = calculate_similarity(text1, text2)
    return similarity >= threshold, similarity
