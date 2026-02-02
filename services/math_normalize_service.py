"""
数学答案标准化服务
将 LaTeX/Markdown 数学符号转换为可读文本，用于答案比对
"""
import re


# LaTeX 符号到 Unicode 的映射表
LATEX_TO_UNICODE = {
    # 希腊字母
    r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
    r'\epsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η', r'\theta': 'θ',
    r'\iota': 'ι', r'\kappa': 'κ', r'\lambda': 'λ', r'\mu': 'μ',
    r'\nu': 'ν', r'\xi': 'ξ', r'\pi': 'π', r'\rho': 'ρ',
    r'\sigma': 'σ', r'\tau': 'τ', r'\upsilon': 'υ', r'\phi': 'φ',
    r'\chi': 'χ', r'\psi': 'ψ', r'\omega': 'ω',
    # 大写希腊字母
    r'\Gamma': 'Γ', r'\Delta': 'Δ', r'\Theta': 'Θ', r'\Lambda': 'Λ',
    r'\Xi': 'Ξ', r'\Pi': 'Π', r'\Sigma': 'Σ', r'\Phi': 'Φ',
    r'\Psi': 'Ψ', r'\Omega': 'Ω',
    # 关系符号
    r'\in': '∈', r'\notin': '∉', r'\subset': '⊂', r'\supset': '⊃',
    r'\subseteq': '⊆', r'\supseteq': '⊇', r'\cap': '∩', r'\cup': '∪',
    r'\emptyset': '∅', r'\varnothing': '∅',
    # 比较符号
    r'\leq': '≤', r'\le': '≤', r'\geq': '≥', r'\ge': '≥',
    r'\neq': '≠', r'\ne': '≠', r'\approx': '≈', r'\equiv': '≡',
    r'\sim': '∼', r'\propto': '∝',
    # 运算符号
    r'\times': '×', r'\div': '÷', r'\pm': '±', r'\mp': '∓',
    r'\cdot': '·', r'\ast': '*', r'\star': '★',
    # 箭头
    r'\to': '→', r'\rightarrow': '→', r'\leftarrow': '←',
    r'\Rightarrow': '⇒', r'\Leftarrow': '⇐', r'\Leftrightarrow': '⇔',
    r'\implies': '⇒', r'\iff': '⇔',
    # 其他数学符号
    r'\infty': '∞', r'\partial': '∂', r'\nabla': '∇',
    r'\forall': '∀', r'\exists': '∃', r'\neg': '¬',
    r'\land': '∧', r'\lor': '∨', r'\oplus': '⊕',
    r'\sqrt': '√', r'\sum': '∑', r'\prod': '∏', r'\int': '∫',
    r'\angle': '∠', r'\perp': '⊥', r'\parallel': '∥',
    r'\triangle': '△', r'\square': '□', r'\circ': '°',
    r'\degree': '°', r'\prime': '′', r'\dprime': '″',
    # 集合符号
    r'\mathbb{R}': 'ℝ', r'\mathbb{N}': 'ℕ', r'\mathbb{Z}': 'ℤ',
    r'\mathbb{Q}': 'ℚ', r'\mathbb{C}': 'ℂ',
    r'\R': 'ℝ', r'\N': 'ℕ', r'\Z': 'ℤ', r'\Q': 'ℚ', r'\C': 'ℂ',
    # 括号
    r'\{': '{', r'\}': '}', r'\lbrace': '{', r'\rbrace': '}',
    r'\langle': '⟨', r'\rangle': '⟩',
    r'\lfloor': '⌊', r'\rfloor': '⌋', r'\lceil': '⌈', r'\rceil': '⌉',
    # 点号
    r'\ldots': '…', r'\cdots': '⋯', r'\vdots': '⋮', r'\ddots': '⋱',
    r'\dots': '…',
    # 空格和格式
    r'\quad': ' ', r'\qquad': '  ', r'\,': ' ', r'\;': ' ', r'\:': ' ',
    r'\ ': ' ', r'\!': '',
    # 分数线
    r'\mid': '|', r'\vert': '|', r'\Vert': '‖',
    # 常用缩写
    r'\therefore': '∴', r'\because': '∵',
}

# 需要移除的 LaTeX 命令（格式命令，不影响语义）
LATEX_COMMANDS_TO_REMOVE = [
    r'\mathbf', r'\mathit', r'\mathrm', r'\mathsf', r'\mathtt', r'\mathcal',
    r'\mathbb', r'\mathfrak', r'\mathscr',
    r'\textbf', r'\textit', r'\textrm', r'\textsf', r'\texttt',
    r'\bf', r'\it', r'\rm', r'\sf', r'\tt',
    r'\boldsymbol', r'\bm',
    r'\left', r'\right', r'\big', r'\Big', r'\bigg', r'\Bigg',
    r'\displaystyle', r'\textstyle', r'\scriptstyle',
    r'\begin', r'\end',
    r'\hspace', r'\vspace', r'\kern', r'\mkern',
]


def normalize_latex(text):
    """
    将 LaTeX 数学符号转换为 Unicode 可读文本
    
    Args:
        text: 包含 LaTeX 符号的文本
        
    Returns:
        str: 转换后的可读文本
    """
    if not text:
        return ''
    
    text = str(text)
    
    # 1. 移除 $...$ 和 $$...$$ 数学环境标记
    text = re.sub(r'\$\$([^$]+)\$\$', r'\1', text)
    text = re.sub(r'\$([^$]+)\$', r'\1', text)
    
    # 2. 移除 \(...\) 和 \[...\] 数学环境标记
    text = re.sub(r'\\\(([^)]+)\\\)', r'\1', text)
    text = re.sub(r'\\\[([^\]]+)\\\]', r'\1', text)
    
    # 3. 保护集合花括号：\{ 和 \} 转为占位符
    text = text.replace(r'\{', '⟨LBRACE⟩')
    text = text.replace(r'\}', '⟨RBRACE⟩')
    
    # 4. 处理 \frac{a}{b} -> a/b
    text = re.sub(r'\\frac\s*\{([^}]*)\}\s*\{([^}]*)\}', r'(\1)/(\2)', text)
    
    # 5. 处理 \sqrt{x} -> √(x) 和 \sqrt[n]{x} -> n√(x)
    text = re.sub(r'\\sqrt\s*\[([^\]]*)\]\s*\{([^}]*)\}', r'\1√(\2)', text)
    text = re.sub(r'\\sqrt\s*\{([^}]*)\}', r'√(\1)', text)
    
    # 6. 处理上下标 x^{2} -> x², x_{i} -> x_i
    # 简单处理：移除花括号
    text = re.sub(r'\^{([^}]*)}', r'^(\1)', text)
    text = re.sub(r'_{([^}]*)}', r'_(\1)', text)
    
    # 7. 移除格式命令（如 \mathbf{N} -> N）
    for cmd in LATEX_COMMANDS_TO_REMOVE:
        # 处理 \cmd{content} 格式
        pattern = re.escape(cmd) + r'\s*\{([^}]*)\}'
        text = re.sub(pattern, r'\1', text)
        # 处理 \cmd 后直接跟字母的格式（如 \mathbfN）
        pattern = re.escape(cmd) + r'([A-Za-z])'
        text = re.sub(pattern, r'\1', text)
    
    # 8. 替换 LaTeX 符号为 Unicode
    for latex, unicode_char in LATEX_TO_UNICODE.items():
        text = text.replace(latex, unicode_char)
    
    # 9. 清理残留的反斜杠命令（未知命令）
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    
    # 10. 清理多余的花括号（非集合用途）
    text = re.sub(r'\{([^{}]*)\}', r'\1', text)
    
    # 11. 还原集合花括号
    text = text.replace('⟨LBRACE⟩', '{')
    text = text.replace('⟨RBRACE⟩', '}')
    
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def normalize_math_answer(text):
    """
    数学答案标准化（用于比对）
    1. 先转换 LaTeX 符号
    2. 再进行通用标准化
    
    Args:
        text: 数学答案文本
        
    Returns:
        str: 标准化后的文本
    """
    if not text:
        return ''
    
    # 1. 转换 LaTeX 符号
    text = normalize_latex(text)
    
    # 2. 统一大小写
    text = text.lower()
    
    # 3. 移除 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 4. 移除换行符
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # 5. 统一数学符号
    symbol_map = {
        '×': '*', '÷': '/', '−': '-', '＋': '+',
        '＝': '=', '～': '~',
        # 全角转半角
        '（': '(', '）': ')', '【': '[', '】': ']',
        '，': ',', '。': '.', '；': ';', '：': ':',
    }
    for old, new in symbol_map.items():
        text = text.replace(old, new)
    
    # 6. 移除残留的 $ 符号（LaTeX 数学标记）
    text = text.replace('$', '')
    
    # 7. 移除所有空白字符
    text = re.sub(r'\s+', '', text)
    
    return text


def latex_to_readable(text):
    """
    将 LaTeX 转换为可读文本（用于前端显示）
    与 normalize_latex 相同，但保留空格便于阅读
    
    Args:
        text: 包含 LaTeX 符号的文本
        
    Returns:
        str: 可读文本
    """
    return normalize_latex(text)

