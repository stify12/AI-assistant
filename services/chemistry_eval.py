"""
化学学科评估模块
提供 LaTeX 化学式/方程式转换为纯文本的功能
用于化学学科(subject_id=4)的答案显示和比较前预处理
"""
import re

# 复用物理模块的通用映射
from services.physics_eval import (
    GREEK_LETTERS, MATH_OPERATORS, ARROWS, SPECIAL_SYMBOLS,
    CALCULUS_SYMBOLS, FUNCTIONS, BRACKETS,
    SUBSCRIPT_MAP, SUPERSCRIPT_MAP,
    _convert_subscript, _convert_superscript
)


# ========== 化学专用符号映射 ==========
CHEMISTRY_SYMBOLS = {
    # 可逆反应
    r'\rightleftharpoons': '⇌',
    r'\leftrightharpoons': '⇌',
    r'\equilibrium': '⇌',
    r'\rightleftarrows': '⇌',
    # 反应条件上下标注
    r'\xlongequal': '══',
    r'\xrightarrow': '→',
    r'\xleftarrow': '←',
    # mhchem 包命令
    r'\ce': '',
    r'\chem': '',
    # 状态符号
    r'\uparrow': '↑',      # 气体
    r'\downarrow': '↓',    # 沉淀
    # 加热符号
    r'\Delta': 'Δ',
    r'\triangle': 'Δ',
    # 点燃/燃烧
    r'\circ': '°',
}

# ========== 反应条件映射 ==========
REACTION_CONDITIONS = {
    # 中文条件
    '高温': '高温',
    '加热': '加热',
    '点燃': '点燃',
    '催化剂': '催化剂',
    '光照': '光照',
    '通电': '通电',
    '加压': '加压',
    '常温': '常温',
    # 英文/符号条件
    'heat': '加热',
    'heating': '加热',
    'high temp': '高温',
    'high temperature': '高温',
    'catalyst': '催化剂',
    'cat.': '催化剂',
    'light': '光照',
    'electricity': '通电',
    'electrolysis': '电解',
    'MnO2': 'MnO₂',
    'MnO_2': 'MnO₂',
    'Fe': 'Fe',
    'Pt': 'Pt',
    'Ni': 'Ni',
    'Cu': 'Cu',
}


def _process_reaction_condition(condition_text):
    """处理反应条件文本"""
    if not condition_text:
        return ''
    
    condition_text = condition_text.strip()
    
    # 先处理下标
    condition_text = re.sub(r'_(\d+)', lambda m: _convert_subscript(m.group(1)), condition_text)
    condition_text = re.sub(r'_\{([^{}]*)\}', lambda m: _convert_subscript(m.group(1)), condition_text)
    
    # 查找已知条件映射
    for key, value in REACTION_CONDITIONS.items():
        if key.lower() in condition_text.lower():
            condition_text = condition_text.replace(key, value)
    
    return condition_text


def normalize_chemistry_markdown(text):
    r"""
    将化学公式的 LaTeX 格式转换为可读纯文本
    
    处理内容：
    1. 移除 HTML 标签 (<br> 等)
    2. 移除 $ 定界符
    3. 处理反应条件标注 (\xrightarrow{条件})
    4. 处理下标 _2 → ₂
    5. 处理上标 ^2 → ²
    6. 处理箭头和化学专用符号
    7. 清理多余空白
    """
    if not text:
        return ''
    
    text = str(text)
    
    # 1. 双反斜杠转单反斜杠（处理 JSON 转义）
    text = text.replace('\\\\', '\\')
    
    # 2. 移除 HTML 标签
    text = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    
    # 3. 移除公式定界符
    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\$(.*?)\$', r'\1', text)
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text, flags=re.DOTALL)
    
    # 4. 处理 \ce{} mhchem 化学式命令
    text = re.sub(r'\\ce\s*\{([^{}]*)\}', r'\1', text)
    
    # 5. 处理带条件的箭头 \xrightarrow{条件} 或 \xrightarrow[下]{上}
    def replace_condition_arrow(match):
        arrow_type = match.group(1)  # xrightarrow, xleftarrow, xlongequal
        below = match.group(2) if match.group(2) else ''
        above = match.group(3) if match.group(3) else ''
        
        below = _process_reaction_condition(below)
        above = _process_reaction_condition(above)
        
        # 确定箭头符号
        if 'equal' in arrow_type:
            arrow = '══'
        elif 'left' in arrow_type:
            arrow = '←'
        else:
            arrow = '→'
        
        # 组合条件和箭头
        conditions = []
        if above:
            conditions.append(above)
        if below:
            conditions.append(below)
        
        if conditions:
            return f" ─{','.join(conditions)}─{arrow} "
        return f" {arrow} "
    
    # 匹配 \xrightarrow[下]{上} 或 \xrightarrow{上}
    text = re.sub(
        r'\\(xrightarrow|xleftarrow|xlongequal)\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}',
        replace_condition_arrow,
        text
    )
    
    # 6. 处理简单条件标注 \overset{条件}{=} 或 \underset{条件}{=}
    def replace_overset(match):
        condition = _process_reaction_condition(match.group(1))
        symbol = match.group(2)
        if symbol == '=' or symbol == '\\to' or symbol == '→':
            return f" ─{condition}─→ "
        return f"{condition}{symbol}"
    
    text = re.sub(r'\\overset\s*\{([^{}]*)\}\s*\{([^{}]*)\}', replace_overset, text)
    text = re.sub(r'\\underset\s*\{([^{}]*)\}\s*\{([^{}]*)\}', replace_overset, text)
    
    # 7. 处理 \text 命令
    for _ in range(5):
        prev = text
        text = re.sub(r'\\text(?:rm|bf|it|sf|tt)?\s*\{([^{}]*)\}', r'\1', text)
        text = re.sub(r'\\mathrm\s*\{([^{}]*)\}', r'\1', text)
        text = re.sub(r'\\mathbf\s*\{([^{}]*)\}', r'\1', text)
        if text == prev:
            break
    
    # 8. 处理下标 _{...}
    def replace_subscript(match):
        content = match.group(1)
        # 中文下标直接保留
        if any('\u4e00' <= c <= '\u9fff' for c in content):
            return content
        return _convert_subscript(content)
    
    for _ in range(5):
        prev = text
        text = re.sub(r'_\{([^{}]*)\}', replace_subscript, text)
        if text == prev:
            break
    # 单字符下标
    text = re.sub(r'_([0-9a-zA-Z])', lambda m: SUBSCRIPT_MAP.get(m.group(1), m.group(1)), text)
    
    # 9. 处理上标 ^{...}
    for _ in range(5):
        prev = text
        text = re.sub(r'\^\{([^{}]*)\}', lambda m: _convert_superscript(m.group(1)), text)
        if text == prev:
            break
    # 单字符上标
    text = re.sub(r'\^([0-9a-zA-Z+\-])', lambda m: SUPERSCRIPT_MAP.get(m.group(1), '^'+m.group(1)), text)
    
    # 10. 替换化学专用符号（优先）
    for latex, symbol in sorted(CHEMISTRY_SYMBOLS.items(), key=lambda x: -len(x[0])):
        text = text.replace(latex, symbol)
    
    # 11. 替换通用符号
    all_symbols = {}
    all_symbols.update(GREEK_LETTERS)
    all_symbols.update(MATH_OPERATORS)
    all_symbols.update(ARROWS)
    all_symbols.update(SPECIAL_SYMBOLS)
    all_symbols.update(CALCULUS_SYMBOLS)
    all_symbols.update(FUNCTIONS)
    all_symbols.update(BRACKETS)
    
    for latex, symbol in sorted(all_symbols.items(), key=lambda x: -len(x[0])):
        text = text.replace(latex, symbol)
    
    # 12. 处理空格命令
    text = text.replace(r'\quad', '  ')
    text = text.replace(r'\qquad', '    ')
    text = text.replace(r'\,', ' ')
    text = text.replace(r'\;', ' ')
    text = text.replace(r'\:', ' ')
    text = text.replace(r'\ ', ' ')
    text = text.replace(r'\!', '')
    
    # 13. 移除剩余的 LaTeX 命令
    text = re.sub(r'\\[a-zA-Z]+\s*(?:\[[^\]]*\])?\s*(?:\{[^{}]*\})?', '', text)
    
    # 14. 清理空白
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    text = text.strip()
    
    return text


def normalize_chemistry_answer(text):
    """化学答案标准化（用于比较）"""
    text = normalize_chemistry_markdown(text)
    from utils.text_utils import normalize_answer
    return normalize_answer(text)
