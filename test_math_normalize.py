"""测试数学标准化函数"""
import re

def test_dollar_removal():
    """测试 $ 符号移除"""
    text = '$3$'
    print(f'原始: {repr(text)}')
    
    # 测试单美元符号正则
    result = re.sub(r'\$(.*?)\$', r'\1', text)
    print(f'单美元符号后: {repr(result)}')
    
    # 测试移除残留 $
    result = result.replace('$', '')
    print(f'移除残留$后: {repr(result)}')

def test_normalize_math_markdown():
    """测试 normalize_math_markdown 函数"""
    from services.math_eval import normalize_math_markdown
    
    test_cases = [
        '$3$',
        '$6$',
        '$1$',
        '3',
        '6',
        '1',
        '$\\frac{1}{2}$',
        '{0,1,2}',
        '${0,1,2}$',
    ]
    
    for case in test_cases:
        result = normalize_math_markdown(case)
        print(f'{repr(case):20} -> {repr(result)}')

def test_normalize_math_answer():
    """测试 normalize_math_answer 函数"""
    from services.math_eval import normalize_math_answer
    
    test_cases = [
        ('$3$', '3'),
        ('$6$', '6'),
        ('$1$', '1'),
        ('3', '3'),
        ('6', '6'),
        ('1', '1'),
        ('{0,1,2}', '012'),
        ('${0,1,2}$', '012'),
    ]
    
    print('\n=== normalize_math_answer 测试 ===')
    for input_val, expected in test_cases:
        result = normalize_math_answer(input_val)
        status = '✓' if result == expected else '✗'
        print(f'{status} {repr(input_val):20} -> {repr(result):15} (期望: {repr(expected)})')

if __name__ == '__main__':
    print('=== $ 符号移除测试 ===')
    test_dollar_removal()
    
    print('\n=== normalize_math_markdown 测试 ===')
    test_normalize_math_markdown()
    
    test_normalize_math_answer()
