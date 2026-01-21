"""
文本工具模块
提供文本处理、JSON解析等工具函数
"""
import re
import json


def normalize_punctuation(text):
    """
    第一层标准化：统一中英文符号（保留标点，只做转换）
    用于需要保留标点语义的场景
    """
    if not text:
        return ''
    
    text = str(text).strip()
    
    # 中英文标点映射表
    punctuation_map = {
        # 括号
        '（': '(', '）': ')',
        '【': '[', '】': ']',
        '｛': '{', '｝': '}',
        '〈': '<', '〉': '>',
        '《': '<', '》': '>',  # 书名号转尖括号
        # 引号
        '"': '"', '"': '"',
        ''': "'", ''': "'",
        '「': '"', '」': '"',
        '『': '"', '』': '"',
        # 标点
        '，': ',', '。': '.',
        '；': ';', '：': ':',
        '！': '!', '？': '?',
        '、': ',',  # 顿号转逗号
        '～': '~', '—': '-',
        '…': '...',
        '·': '.',
        # 数学符号
        '×': '*', '÷': '/',
        '＋': '+', '－': '-', '＝': '=',
        # 全角数字
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
    }
    
    for cn, en in punctuation_map.items():
        text = text.replace(cn, en)
    
    # 全角字母转半角
    result = []
    for char in text:
        code = ord(char)
        # 全角字母 A-Z: 0xFF21-0xFF3A -> 0x0041-0x005A
        # 全角字母 a-z: 0xFF41-0xFF5A -> 0x0061-0x007A
        if 0xFF21 <= code <= 0xFF3A:
            result.append(chr(code - 0xFF21 + 0x41))
        elif 0xFF41 <= code <= 0xFF5A:
            result.append(chr(code - 0xFF41 + 0x61))
        else:
            result.append(char)
    
    return ''.join(result)


def normalize_for_similarity(text):
    """
    第二层标准化：用于相似度计算的完整标准化
    1. 统一中英文符号
    2. 去除所有标点符号
    3. 去除空白字符
    4. 统一大小写
    """
    if not text:
        return ''
    
    # 先统一中英文符号
    text = normalize_punctuation(text)
    
    # 统一大小写
    text = text.lower()
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 移除所有标点符号（只保留中文、字母、数字、常用序号符号）
    text = re.sub(r'[^\u4e00-\u9fff\w①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]', '', text)
    
    return text


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
    计算两个文本的相似度（优化版：先标准化符号再计算）
    
    流程：
    1. 先对两个文本进行完整标准化（统一中英文符号 + 去除标点）
    2. 使用字符n-gram + 序列匹配计算相似度
    
    能识别：
    1. 符号差异："《西游记》" vs "<西游记>" → 相似度 = 1.0
    2. 语义差异："古桥" vs "立交桥" → 较低相似度
    3. 词序差异："①②③" vs "①③②" → 较低相似度
    
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
    
    # 使用专门的相似度标准化函数（统一符号 + 去除标点）
    norm1 = normalize_for_similarity(text1)
    norm2 = normalize_for_similarity(text2)
    
    if norm1 == norm2:
        return 1.0
    
    if not norm1 or not norm2:
        return 0.0
    
    # 短文本直接用序列匹配
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
    
    # 使用相似度专用标准化
    norm1 = normalize_for_similarity(text1)
    norm2 = normalize_for_similarity(text2)
    
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
    print(f"[DEBUG] is_fuzzy_match: text1={text1[:30]}..., text2={text2[:30]}..., similarity={similarity}")
    return similarity >= threshold, similarity
