from services.math_eval import normalize_math_answer
print('3 ->', repr(normalize_math_answer('3')))
print('$3$ ->', repr(normalize_math_answer('$3$')))
print('2 ->', repr(normalize_math_answer('2')))
print('$2$ ->', repr(normalize_math_answer('$2$')))
