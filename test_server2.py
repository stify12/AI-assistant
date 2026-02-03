from utils.text_utils import normalize_answer_science
print('3 ->', repr(normalize_answer_science('3')))
print('6 ->', repr(normalize_answer_science('6')))
print('2 ->', repr(normalize_answer_science('2')))
print('$3$ ->', repr(normalize_answer_science('$3$')))
print('$6$ ->', repr(normalize_answer_science('$6$')))
