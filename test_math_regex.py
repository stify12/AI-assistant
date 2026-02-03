"""测试数学正则表达式"""
import re

# 测试 $...$ 移除
test_cases = [
    '$6$',
    '$a=-3$；$b=2$',
    '-3 2',
    '6',
]

for text in test_cases:
    print(f"Input: {repr(text)}")
    
    # 移除 $...$
    result = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.DOTALL)
    result = re.sub(r'\$(.*?)\$', r'\1', result)
    result = result.replace('$', '')
    
    print(f"After removing $: {repr(result)}")
    print()

# 测试完整的 normalize_math_answer
print("=" * 50)
print("Testing normalize_math_answer:")
from services.math_eval import normalize_math_markdown, normalize_math_answer

for text in test_cases:
    print(f"Input: {repr(text)}")
    print(f"normalize_math_markdown: {repr(normalize_math_markdown(text))}")
    print(f"normalize_math_answer: {repr(normalize_math_answer(text))}")
    print()
