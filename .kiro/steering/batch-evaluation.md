# 批量评估数据流程

## 数据来源

### 数据库字段
- `zp_homework.homework_result`: AI批改结果（JSON数组），包含识别的答案和判断结果
- `zp_homework.data_value`: 题目原始数据（JSON数组），包含题目类型信息（`bvalue`, `questionType`）

### 关键区别
| 字段 | 内容 | 类型信息 |
|------|------|----------|
| `homework_result` | AI批改结果（answer, userAnswer, correct） | 无 |
| `data_value` | 题目原始数据 | 有（bvalue, questionType） |

## 题目类型分类

### bvalue 映射
| bvalue | 类型 | 分类 |
|--------|------|------|
| 1 | 单选题 | 选择题 |
| 2 | 多选题 | 选择题 |
| 3 | 判断题 | 选择题 |
| 4 | 填空题 | 客观填空题（需 questionType='objective'） |
| 5 | 解答题 | 主观题 |
| 8 | 英语作文 | 主观题 |

### 三类互斥分类
1. **选择题** (`choice`): bvalue=1,2,3
2. **客观填空题** (`objective_fill`): questionType='objective' 且 bvalue='4'
3. **主观题** (`subjective`): 其他所有（bvalue=5 或无 bvalue）

### 分类函数
```python
def classify_question_type(question_data):
    bvalue = str(question_data.get('bvalue', ''))
    question_type = question_data.get('questionType', '')
    
    is_choice = bvalue in ('1', '2', '3')
    is_fill = (question_type == 'objective' and bvalue == '4')
    is_subjective = not is_choice and not is_fill
```

## 任务创建流程

### SQL 查询
```sql
SELECT h.id, h.homework_result, h.data_value, ...
FROM zp_homework h
WHERE h.id IN (...)
```

### 保存到任务
```python
homework_items.append({
    'homework_id': row['id'],
    'homework_result': row.get('homework_result', '[]'),
    'data_value': row.get('data_value', '[]'),  # 题目类型信息来源
    ...
})
```

## 评估流程

### 1. 获取基准效果 (base_effect)
优先级：
1. 从匹配的数据集获取（已包含类型信息）
2. 从 baseline_effects 文件获取（可能无类型信息）

### 2. 构建类型映射 (type_map)
从 `data_value` 构建，支持递归处理 children：
```python
type_map = {}
for item in data_value:
    add_to_type_map(item)  # 递归添加题目及子题

# 按 index 和 tempIndex 两种方式索引
type_map[f'idx_{normalized_idx}'] = type_info
type_map[f'temp_{temp_idx}'] = type_info
```

### 3. 获取题目类型
优先级：
1. 从 `type_map`（data_value）获取
2. 从 `base_item`（基准效果）获取
3. 从 `hw_item`（AI批改结果）获取
4. 默认归类为主观题

```python
type_info = type_map.get(f'idx_{normalized_idx}')
if not type_info:
    type_info = type_map.get(f'temp_{base_temp_idx}')
```

## 注意事项

### 旧任务兼容
- 旧任务没有 `data_value` 字段，需要重新创建任务
- 重新创建后会自动获取 `data_value`

### 数据集 vs 直接评估
- 有数据集：类型信息已在创建数据集时通过 `enrich_base_effects_with_question_types` 补充
- 无数据集：从任务的 `data_value` 获取类型信息

### 语文学科特殊处理
- 语文(subject_id=1)使用题号(index)匹配
- 其他学科使用 tempIndex 匹配
- 语文非选择题支持模糊匹配（默认阈值 85%）
