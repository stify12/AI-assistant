"""测试数学答案标准化修复"""
from services.math_eval import normalize_math_answer, normalize_math_markdown

# 测试用例
test_cases = [
    ('6', '$6$'),
    ('1', '$1$'),
    ('-3 2', '$a=-3$；$b=2$'),
]

print("=" * 60)
print("测试 normalize_math_answer 修复效果")
print("=" * 60)

for base, ai in test_cases:
    norm_base = normalize_math_answer(base)
    norm_ai = normalize_math_answer(ai)
    match = norm_base == norm_ai
    
    print(f"\n基准: {repr(base)} -> {repr(norm_base)}")
    print(f"AI:   {repr(ai)} -> {repr(norm_ai)}")
    print(f"匹配: {match}")
