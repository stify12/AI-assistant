import re
with open('routes/batch_evaluation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 evaluation = item.get('evaluation', {})
content = content.replace("evaluation = item.get('evaluation', {})", "evaluation = item.get('evaluation') or {}")

# 替换 by_type = evaluation.get('by_question_type', {})
content = content.replace("by_type = evaluation.get('by_question_type', {})", "by_type = evaluation.get('by_question_type') or {}")

# 替换 by_bvalue = evaluation.get('by_bvalue', {})
content = content.replace("by_bvalue = evaluation.get('by_bvalue', {})", "by_bvalue = evaluation.get('by_bvalue') or {}")

# 替换 by_combined = evaluation.get('by_combined', {})
content = content.replace("by_combined = evaluation.get('by_combined', {})", "by_combined = evaluation.get('by_combined') or {}")

with open('routes/batch_evaluation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
