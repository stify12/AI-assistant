"""
物理学科评估模块
提供 LaTeX/Markdown 公式转换为纯文本的功能
用于物理学科(subject_id=3)的答案比较前预处理
"""
import re


# ========== 希腊字母映射 ==========
GREEK_LETTERS = {
    r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
    r'\epsilon': 'ε', r'\varepsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η',
    r'\theta': 'θ', r'\vartheta': 'θ', r'\iota': 'ι', r'\kappa': 'κ',
    r'\lambda': 'λ', r'\mu': 'μ', r'\nu': 'ν', r'\xi': 'ξ',
    r'\pi': 'π', r'\varpi': 'π', r'\rho': 'ρ', r'\varrho': 'ρ',
    r'\sigma': 'σ', r'\varsigma': 'ς', r'\tau': 'τ', r'\upsilon': 'υ',
    r'\phi': 'φ', r'\varphi': 'φ', r'\chi': 'χ', r'\psi': 'ψ', r'\omega': 'ω',
    r'\Alpha': 'Α', r'\Beta': 'Β', r'\Gamma': 'Γ', r'\Delta': 'Δ',
    r'\Epsilon': 'Ε', r'\Zeta': 'Ζ', r'\Eta': 'Η', r'\Theta': 'Θ',
    r'\Iota': 'Ι', r'\Kappa': 'Κ', r'\Lambda': 'Λ', r'\Mu': 'Μ',
    r'\Nu': 'Ν', r'\Xi': 'Ξ', r'\Pi': 'Π', r'\Rho': 'Ρ',
    r'\Sigma': 'Σ', r'\Tau': 'Τ', r'\Upsilon': 'Υ', r'\Phi': 'Φ',
    r'\Chi': 'Χ', r'\Psi': 'Ψ', r'\Omega': 'Ω',
}

# ========== 数学运算符映射 ==========
MATH_OPERATORS = {
    r'\times': '×', r'\div': '÷', r'\pm': '±', r'\mp': '∓',
    r'\cdot': '·', r'\ast': '*', r'\star': '★',
    r'\leq': '≤', r'\le': '≤', r'\geq': '≥', r'\ge': '≥',
    r'\neq': '≠', r'\ne': '≠', r'\approx': '≈', r'\equiv': '≡',
    r'\propto': '∝', r'\sim': '~', r'\simeq': '≃',
    r'\ll': '≪', r'\gg': '≫',
    r'\subset': '⊂', r'\supset': '⊃', r'\subseteq': '⊆', r'\supseteq': '⊇',
    r'\in': '∈', r'\notin': '∉', r'\ni': '∋',
    r'\cup': '∪', r'\cap': '∩', r'\setminus': '\\',
    r'\emptyset': '∅', r'\varnothing': '∅',
    r'\forall': '∀', r'\exists': '∃', r'\nexists': '∄',
    r'\neg': '¬', r'\land': '∧', r'\lor': '∨',
}

# ========== 箭头映射 ==========
ARROWS = {
    r'\rightarrow': '→', r'\to': '→', r'\leftarrow': '←', r'\gets': '←',
    r'\leftrightarrow': '↔', r'\longrightarrow': '→', r'\longleftarrow': '←',
    r'\Rightarrow': '⇒', r'\Leftarrow': '⇐', r'\Leftrightarrow': '⇔',
    r'\Longrightarrow': '⇒', r'\Longleftarrow': '⇐', r'\Longleftrightarrow': '⇔',
    r'\uparrow': '↑', r'\downarrow': '↓', r'\updownarrow': '↕',
    r'\Uparrow': '⇑', r'\Downarrow': '⇓', r'\Updownarrow': '⇕',
    r'\nearrow': '↗', r'\searrow': '↘', r'\swarrow': '↙', r'\nwarrow': '↖',
    r'\mapsto': '↦', r'\longmapsto': '↦',
}

# ========== 特殊符号映射 ==========
SPECIAL_SYMBOLS = {
    r'\infty': '∞', r'\partial': '∂', r'\nabla': '∇',
    r'\degree': '°', r'\circ': '°', r'\prime': '′', r'\dprime': '″',
    r'\angle': '∠', r'\measuredangle': '∡',
    r'\perp': '⊥', r'\parallel': '∥',
    r'\triangle': '△', r'\square': '□', r'\diamond': '◇',
    r'\bullet': '•', r'\cdots': '···', r'\ldots': '...', r'\dots': '...',
    r'\vdots': '⋮', r'\ddots': '⋱',
    r'\aleph': 'ℵ', r'\hbar': 'ℏ', r'\ell': 'ℓ',
    r'\Re': 'ℜ', r'\Im': 'ℑ', r'\wp': '℘',
}

# ========== 积分/求和符号映射 ==========
CALCULUS_SYMBOLS = {
    r'\int': '∫', r'\iint': '∬', r'\iiint': '∭', r'\oint': '∮',
    r'\sum': 'Σ', r'\prod': 'Π', r'\coprod': '∐',
    r'\bigcup': '⋃', r'\bigcap': '⋂', r'\bigoplus': '⊕', r'\bigotimes': '⊗',
}

# ========== 函数名映射 ==========
FUNCTIONS = {
    r'\sin': 'sin', r'\cos': 'cos', r'\tan': 'tan',
    r'\cot': 'cot', r'\sec': 'sec', r'\csc': 'csc',
    r'\arcsin': 'arcsin', r'\arccos': 'arccos', r'\arctan': 'arctan',
    r'\sinh': 'sinh', r'\cosh': 'cosh', r'\tanh': 'tanh',
    r'\log': 'log', r'\ln': 'ln', r'\lg': 'lg', r'\exp': 'exp',
    r'\lim': 'lim', r'\limsup': 'lim sup', r'\liminf': 'lim inf',
    r'\max': 'max', r'\min': 'min', r'\sup': 'sup', r'\inf': 'inf',
    r'\det': 'det', r'\dim': 'dim', r'\ker': 'ker', r'\hom': 'hom',
    r'\arg': 'arg', r'\deg': 'deg', r'\gcd': 'gcd', r'\lcm': 'lcm',
    r'\mod': 'mod', r'\bmod': 'mod',
}

# ========== 括号映射 ==========
BRACKETS = {
    r'\left(': '(', r'\right)': ')',
    r'\left[': '[', r'\right]': ']',
    r'\left\{': '{', r'\right\}': '}',
    r'\left|': '|', r'\right|': '|',
    r'\left.': '', r'\right.': '',
    r'\langle': '⟨', r'\rangle': '⟩',
    r'\lvert': '|', r'\rvert': '|',
    r'\lVert': '‖', r'\rVert': '‖',
    r'\lceil': '⌈', r'\rceil': '⌉',
    r'\lfloor': '⌊', r'\rfloor': '⌋',
    r'\{': '{', r'\}': '}',
    r'\|': '‖',
}

# ========== 上标字符映射 ==========
SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
    'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
    'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
    'A': 'ᴬ', 'B': 'ᴮ', 'D': 'ᴰ', 'E': 'ᴱ', 'G': 'ᴳ',
    'H': 'ᴴ', 'I': 'ᴵ', 'J': 'ᴶ', 'K': 'ᴷ', 'L': 'ᴸ',
    'M': 'ᴹ', 'N': 'ᴺ', 'O': 'ᴼ', 'P': 'ᴾ', 'R': 'ᴿ',
    'T': 'ᵀ', 'U': 'ᵁ', 'V': 'ⱽ', 'W': 'ᵂ',
}

# ========== 下标字符映射 ==========
SUBSCRIPT_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
    'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
    'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
    'v': 'ᵥ', 'x': 'ₓ',
}

# ========== n次根号前缀映射 ==========
ROOT_PREFIX_MAP = {
    '2': '√', '3': '³√', '4': '⁴√', '5': '⁵√',
    '6': '⁶√', '7': '⁷√', '8': '⁸√', '9': '⁹√',
    'n': 'ⁿ√',
}


def _convert_superscript(text):
    """将文本转换为上标形式"""
    return ''.join(SUPERSCRIPT_MAP.get(c, c) for c in text)


def _convert_subscript(text):
    """将文本转换为下标形式"""
    return ''.join(SUBSCRIPT_MAP.get(c, c) for c in text)


def normalize_physics_markdown(text):
    """
    将物理/数学公式的 LaTeX/Markdown 格式转换为可读纯文本
    
    处理顺序很重要，需要从内到外处理嵌套结构：
    1. 双反斜杠转单反斜杠
    2. 移除 $ 符号
    3. 处理 \text 命令（最内层）
    4. 处理下标 _{...}（消除嵌套花括号）
    5. 处理上标 ^{...}（消除嵌套花括号）
    6. 处理分数 \frac{...}{...}（现在内部没有嵌套花括号了）
    7. 其他符号替换
    """
    if not text:
        return ''
    
    text = str(text)
    
    # 1. 双反斜杠转单反斜杠（处理 JSON 转义）
    text = text.replace('\\\\', '\\')
    
    # 2. 移除公式定界符
    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\$(.*?)\$', r'\1', text)
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text, flags=re.DOTALL)
    
    # 3. 处理 \text 命令（多次处理嵌套）
    for _ in range(5):
        prev = text
        text = re.sub(r'\\text(?:rm|bf|it|sf|tt)?\s*\{([^{}]*)\}', r'\1', text)
        text = re.sub(r'\\mathrm\s*\{([^{}]*)\}', r'\1', text)
        text = re.sub(r'\\mathbf\s*\{([^{}]*)\}', r'\1', text)
        text = re.sub(r'\\boldsymbol\s*\{([^{}]*)\}', r'\1', text)
        if text == prev:
            break
    
    # 4. 处理下标 _{...}（在分数之前处理，消除嵌套花括号）
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
    text = re.sub(r'_([\u4e00-\u9fff])', r'\1', text)
    
    # 5. 处理上标 ^{...}
    for _ in range(5):
        prev = text
        text = re.sub(r'\^\{([^{}]*)\}', lambda m: _convert_superscript(m.group(1)), text)
        if text == prev:
            break
    # 单字符上标
    text = re.sub(r'\^([0-9a-zA-Z+\-])', lambda m: SUPERSCRIPT_MAP.get(m.group(1), '^'+m.group(1)), text)
    
    # 6. 处理分数（现在内部没有嵌套花括号了）
    for _ in range(5):
        prev = text
        text = re.sub(r'\\(?:d|t|c)?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', r'(\1)/(\2)', text)
        if text == prev:
            break
    # 简化括号
    text = re.sub(r'\(([a-zA-Z0-9α-ωΑ-Ω])\)/\(([a-zA-Z0-9α-ωΑ-Ω])\)', r'\1/\2', text)
    text = re.sub(r'\(([a-zA-Z0-9α-ωΑ-Ω])\)/', r'\1/', text)
    text = re.sub(r'/\(([a-zA-Z0-9α-ωΑ-Ω])\)', r'/\1', text)
    
    # 7. 处理根号
    def replace_nth_root(match):
        n, content = match.group(1), match.group(2)
        return ROOT_PREFIX_MAP.get(n, f'{n}√') + content
    text = re.sub(r'\\sqrt\s*\[([^\]]+)\]\s*\{([^{}]*)\}', replace_nth_root, text)
    text = re.sub(r'\\sqrt\s*\{([^{}]*)\}', r'√\1', text)
    
    # 8. 处理向量和修饰符
    text = re.sub(r'\\vec\s*\{([^{}]*)\}', r'\1⃗', text)
    text = re.sub(r'\\overrightarrow\s*\{([^{}]*)\}', r'\1→', text)
    text = re.sub(r'\\overline\s*\{([^{}]*)\}', r'\1̄', text)
    text = re.sub(r'\\bar\s*\{([^{}]*)\}', r'\1̄', text)
    text = re.sub(r'\\hat\s*\{([^{}]*)\}', r'\1̂', text)
    text = re.sub(r'\\tilde\s*\{([^{}]*)\}', r'\1̃', text)
    text = re.sub(r'\\dot\s*\{([^{}]*)\}', r'\1̇', text)
    text = re.sub(r'\\ddot\s*\{([^{}]*)\}', r'\1̈', text)
    
    # 9. 替换所有符号（按长度降序）
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
    
    # 10. 处理空格命令
    text = text.replace(r'\quad', '  ')
    text = text.replace(r'\qquad', '    ')
    text = text.replace(r'\,', ' ')
    text = text.replace(r'\;', ' ')
    text = text.replace(r'\:', ' ')
    text = text.replace(r'\ ', ' ')
    text = text.replace(r'\!', '')
    
    # 11. 移除剩余的 LaTeX 命令
    text = re.sub(r'\\[a-zA-Z]+\s*(?:\[[^\]]*\])?\s*(?:\{[^{}]*\})?', '', text)
    
    # 12. 清理空白
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    text = text.strip()
    
    return text


def normalize_physics_answer(text):
    """物理答案标准化（用于比较）"""
    text = normalize_physics_markdown(text)
    from utils.text_utils import normalize_answer
    return normalize_answer(text)
