# Design Document

## Overview

本设计文档描述了批量评估模块Excel导出功能的优化方案。当前导出功能已包含7个工作表，但存在数据不完整、缺少关键统计、样式不统一等问题。本次优化将：

1. 补全所有字段的数据（错误详情表的基准答案、AI答案等）
2. 新增4个统计工作表（按学生、按页码、按题型、英语作文评分）
3. 统一样式为黑白简洁风格
4. 优化图表展示和数据可读性
5. 提升大数据量导出性能
6. 保持向后兼容性

核心原则：
- 保持现有7个工作表不变，只做增强
- 所有新增功能向后兼容旧数据
- 遵循项目的黑白简洁UI风格
- 优化性能，支持大数据量导出

## Architecture

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Flask Route Layer                        │
│  /api/batch/tasks/<task_id>/export                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Excel Export Service                            │
│  - export_batch_excel(task_id)                              │
│  - 数据提取和转换                                             │
│  - 工作表创建和样式设置                                        │
│  - 图表生成                                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Data Extract │ │ Worksheet    │ │ Chart        │
│ Module       │ │ Generator    │ │ Generator    │
│              │ │              │ │              │
│ - 基准效果   │ │ - 评估总结   │ │ - 饼图       │
│ - AI结果     │ │ - 错误分析   │ │ - 柱状图     │
│ - 学生信息   │ │ - 作业明细   │ │ - 折线图     │
│ - 数据集信息 │ │ - 题目明细   │ │ - 雷达图     │
│ - 作文评分   │ │ - 错误详情   │ │              │
│              │ │ - 按学生统计 │ │              │
│              │ │ - 按页码统计 │ │              │
│              │ │ - 按题型统计 │ │              │
│              │ │ - 作文评分   │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                ┌──────────────────┐
                │  openpyxl        │
                │  - Workbook      │
                │  - Worksheet     │
                │  - Chart         │
                │  - Styles        │
                └──────────────────┘
```

### 数据流

```
Task Data (JSON)
    │
    ├─> Homework Items
    │   ├─> homework_result (AI批改结果)
    │   ├─> data_value (题目类型信息)
    │   ├─> evaluation (评估结果)
    │   └─> matched_dataset (关联数据集)
    │
    ├─> Dataset Info
    │   ├─> dataset_id
    │   ├─> dataset_name
    │   ├─> description
    │   └─> base_effects (基准效果)
    │
    └─> Overall Report
        ├─> overall_accuracy
        ├─> by_question_type
        ├─> by_book
        ├─> error_distribution
        └─> ai_analysis

        ↓ Extract & Transform

Excel Workbook
    ├─> 评估总结 (Summary)
    ├─> 错误分析 (Error Analysis)
    ├─> 可视化图表 (Charts)
    ├─> 作业明细 (Homework Details)
    ├─> 题目明细 (Question Details)
    ├─> 错误详情 (Error Details)
    ├─> AI分析报告 (AI Report)
    ├─> 按学生统计 (By Student) [NEW]
    ├─> 按页码统计 (By Page) [NEW]
    ├─> 按题型统计 (By Type) [NEW]
    └─> 英语作文评分 (Essay Scores) [NEW, 条件性]
```

## Components and Interfaces

### 1. Data Extraction Module

负责从任务数据中提取和转换所需的数据。

```python
class DataExtractor:
    """数据提取器"""
    
    @staticmethod
    def extract_error_details(homework_items, task_data):
        """
        提取完整的错误详情数据
        
        Returns:
            List[Dict]: 错误详情列表，包含：
            - homework_id: 作业ID
            - book_name: 书本名称
            - page_num: 页码
            - student_name: 学生姓名
            - student_id: 学生ID
            - index: 题号
            - error_type: 错误类型
            - base_user_answer: 基准用户答案
            - ai_user_answer: AI识别答案
            - base_correct: 基准判断结果
            - ai_correct: AI判断结果
            - standard_answer: 标准答案
            - similarity: 相似度（如有）
            - severity: 严重程度
            - explanation: 详细说明
        """
        pass
    
    @staticmethod
    def extract_student_statistics(homework_items):
        """
        按学生统计数据
        
        Returns:
            List[Dict]: 学生统计列表，包含：
            - student_name: 学生姓名
            - student_id: 学生ID
            - homework_count: 作业数
            - total_questions: 总题数
            - correct_count: 正确数
            - error_count: 错误数
            - accuracy: 准确率
            - choice_accuracy: 选择题准确率
            - fill_accuracy: 客观填空题准确率
            - subjective_accuracy: 主观题准确率
        """
        pass
    
    @staticmethod
    def extract_page_statistics(homework_items):
        """
        按页码统计数据
        
        Returns:
            List[Dict]: 页码统计列表
        """
        pass

    
    @staticmethod
    def extract_type_statistics(homework_items):
        """
        按题型统计数据
        
        Returns:
            List[Dict]: 题型统计列表
        """
        pass
    
    @staticmethod
    def extract_essay_scores(homework_items, subject_id):
        """
        提取英语作文评分数据
        
        Args:
            homework_items: 作业列表
            subject_id: 学科ID
        
        Returns:
            Dict: {
                'has_essay': bool,
                'essays': List[Dict],
                'stats': Dict
            }
        """
        pass
    
    @staticmethod
    def extract_dataset_info(task_data):
        """
        提取数据集信息
        
        Returns:
            Dict or None: 数据集信息
        """
        pass
    
    @staticmethod
    def get_base_effect_for_homework(homework_item, task_data):
        """
        获取作业的基准效果数据
        
        Returns:
            List[Dict]: 基准效果列表
        """
        pass
```

### 2. Worksheet Generator Module

负责创建和填充各个工作表。

```python
class WorksheetGenerator:
    """工作表生成器"""
    
    def __init__(self, workbook, style_config):
        self.wb = workbook
        self.styles = style_config
    
    def create_summary_sheet(self, task_data, dataset_info):
        """创建评估总结表"""
        pass
    
    def create_error_analysis_sheet(self, error_data):
        """创建错误分析表"""
        pass
    
    def create_homework_details_sheet(self, homework_items):
        """创建作业明细表"""
        pass
    
    def create_question_details_sheet(self, homework_items, task_data):
        """创建题目明细表（增强版）"""
        pass
    
    def create_error_details_sheet(self, error_details):
        """创建错误详情表（完整版）"""
        pass
    
    def create_student_statistics_sheet(self, student_stats):
        """创建按学生统计表 [NEW]"""
        pass
    
    def create_page_statistics_sheet(self, page_stats):
        """创建按页码统计表 [NEW]"""
        pass
    
    def create_type_statistics_sheet(self, type_stats):
        """创建按题型统计表 [NEW]"""
        pass
    
    def create_essay_scores_sheet(self, essay_data):
        """创建英语作文评分表 [NEW]"""
        pass
```

### 3. Chart Generator Module

负责创建各种图表。

```python
class ChartGenerator:
    """图表生成器"""
    
    @staticmethod
    def create_pie_chart(worksheet, data_range, title, position):
        """创建饼图"""
        pass
    
    @staticmethod
    def create_bar_chart(worksheet, data_range, title, position):
        """创建柱状图"""
        pass
    
    @staticmethod
    def create_line_chart(worksheet, data_range, title, position):
        """创建折线图"""
        pass
    
    @staticmethod
    def create_radar_chart(worksheet, data_range, title, position):
        """创建雷达图"""
        pass
    
    @staticmethod
    def limit_data_points(data, max_points=50):
        """限制图表数据点数量"""
        pass
```

### 4. Style Configuration

统一的样式配置。

```python
class StyleConfig:
    """样式配置"""
    
    # 颜色定义（黑白简洁风格）
    COLOR_BLACK = "1D1D1F"
    COLOR_WHITE = "FFFFFF"
    COLOR_GRAY_LIGHT = "F5F5F7"
    COLOR_GRAY_BORDER = "D2D2D7"
    
    # 状态颜色
    COLOR_SUCCESS = "E3F9E5"  # 绿色背景
    COLOR_WARNING = "FFF3E0"  # 黄色背景
    COLOR_ERROR = "FFEEF0"    # 红色背景
    COLOR_INFO = "E3F2FD"     # 蓝色背景
    
    # 字体
    FONT_TITLE = Font(bold=True, size=16, color=COLOR_BLACK)
    FONT_SUBTITLE = Font(bold=True, size=14, color=COLOR_BLACK)
    FONT_HEADER = Font(bold=True, size=12, color=COLOR_WHITE)
    FONT_NORMAL = Font(size=11, color=COLOR_BLACK)
    
    # 填充
    FILL_HEADER = PatternFill(start_color=COLOR_BLACK, end_color=COLOR_BLACK, fill_type="solid")
    FILL_SUCCESS = PatternFill(start_color=COLOR_SUCCESS, end_color=COLOR_SUCCESS, fill_type="solid")
    FILL_WARNING = PatternFill(start_color=COLOR_WARNING, end_color=COLOR_WARNING, fill_type="solid")
    FILL_ERROR = PatternFill(start_color=COLOR_ERROR, end_color=COLOR_ERROR, fill_type="solid")
    
    # 对齐
    ALIGN_CENTER = Alignment(horizontal='center', vertical='center')
    ALIGN_LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
    
    # 边框
    BORDER_THIN = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
```

## Data Models

### Task Data Structure

```python
{
    "task_id": "uuid",
    "name": "任务名称",
    "created_at": "2024-01-01 12:00:00",
    "status": "completed",
    "subject_id": 0,  # 学科ID
    "subject_name": "英语",
    "test_condition_name": "测试条件名称",
    "fuzzy_threshold": 0.85,  # 模糊匹配阈值
    "homework_items": [
        {
            "homework_id": 12345,
            "student_id": "S001",
            "student_name": "张三",
            "book_id": 100,
            "book_name": "英语必修一",
            "page_num": 30,
            "homework_result": "[...]",  # AI批改结果JSON
            "data_value": "[...]",  # 题目类型信息JSON
            "matched_dataset": "dataset_uuid",
            "matched_dataset_name": "英语必修一_P30_20240101",
            "status": "completed",
            "accuracy": 0.95,
            "evaluation": {
                "total_questions": 10,
                "correct_count": 9,
                "error_count": 1,
                "by_question_type": {
                    "choice": {"total": 5, "correct": 5, "accuracy": 1.0},
                    "objective_fill": {"total": 3, "correct": 3, "accuracy": 1.0},
                    "subjective": {"total": 2, "correct": 1, "accuracy": 0.5}
                },
                "errors": [
                    {
                        "index": "5",
                        "error_type": "识别错误-判断正确",
                        "explanation": "...",
                        "severity": "medium",
                        "similarity": 0.88,
                        "base_result": {...},
                        "ai_result": {...}
                    }
                ]
            }
        }
    ],
    "overall_report": {
        "total_homework": 50,
        "total_questions": 500,
        "correct_questions": 475,
        "overall_accuracy": 0.95,
        "by_question_type": {...},
        "by_book": {...},
        "error_distribution": {...},
        "ai_analysis": {...}
    }
}
```

### Base Effect Structure

```python
{
    "index": "1",
    "tempIndex": 0,
    "answer": "A",  # 标准答案
    "userAnswer": "A",  # 基准用户答案
    "correct": "yes",  # 基准判断结果
    "questionType": "objective",
    "bvalue": "1"  # 题目类型代码
}
```

### AI Result Structure

```python
{
    "index": "1",
    "tempIndex": 0,
    "answer": "A",  # AI识别的标准答案
    "userAnswer": "A",  # AI识别的用户答案
    "correct": "yes",  # AI判断结果
    "mainAnswer": "..."  # 主答案（作文评分等）
}
```

### Essay Score Structure

```python
{
    "homework_id": 12345,
    "student_id": "S001",
    "student_name": "张三",
    "index": "8",
    "score": 18.5,
    "evaluation": "文章结构清晰...",
    "suggestions": "建议加强词汇多样性...",
    "raw": "参考得分：18.5\n综合评价：..."
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 错误详情字段完整性
*For any* 导出的错误详情表，所有错误记录的基准用户答案、AI识别答案、基准判断、AI判断字段都应被正确填充（非空或有默认值）
**Validates: Requirements 1.1, 6.1, 6.2, 6.3, 6.4**

### Property 2: 学生信息传播一致性
*For any* 包含学生信息的作业，该学生信息应在所有相关工作表（作业明细、题目明细、错误详情、按学生统计）中保持一致
**Validates: Requirements 1.2**

### Property 3: 作业ID传播完整性
*For any* 包含作业ID的作业，该作业ID应在题目明细表和错误详情表中出现
**Validates: Requirements 1.3**

### Property 4: 数据集信息展示完整性
*For any* 使用了数据集的任务，评估总结表应包含数据集名称、描述、创建时间、页码列表、题目总数
**Validates: Requirements 1.4, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6**

### Property 5: 英语作文评分提取准确性
*For any* 学科为英语且包含作文评分的任务，所有作文评分数据（得分、评价、建议）应被正确提取
**Validates: Requirements 1.5, 8.2, 8.3, 8.4, 8.5, 8.6**

### Property 6: 相似度数据展示完整性
*For any* 包含相似度数据的错误记录，相似度百分比应在错误详情表中显示
**Validates: Requirements 1.6, 6.6**

### Property 7: 题型分类准确性
*For any* 题目，其题型分类（选择题/客观填空题/主观题）应根据bvalue和questionType正确判断
**Validates: Requirements 1.7, 5.1**

### Property 8: 工作表创建完整性
*For any* 导出操作，Excel应包含所有必需的工作表（评估总结、错误分析、作业明细、题目明细、错误详情、按学生统计、按页码统计、按题型统计）
**Validates: Requirements 2.1, 2.3, 2.5**

### Property 9: 统计表字段完整性
*For any* 统计工作表（按学生/按页码/按题型），所有必需字段应被正确填充
**Validates: Requirements 2.2, 2.4, 2.6**

### Property 10: 英语作文工作表条件创建
*For any* 任务，当且仅当学科为英语且包含作文评分时，应创建"英语作文评分"工作表
**Validates: Requirements 2.7, 8.1**

### Property 11: 样式一致性
*For any* 工作表，所有表头应使用黑色背景和白色文字，所有边框应使用统一的细线样式
**Validates: Requirements 3.1, 3.2**

### Property 12: 准确率条件格式正确性
*For any* 显示准确率的单元格，当准确率>=90%时应为绿色，70-90%时应为黄色，<70%时应为红色
**Validates: Requirements 3.3**

### Property 13: 表格功能完整性
*For any* 工作表，应启用筛选器且冻结首行表头
**Validates: Requirements 3.4, 3.5**

### Property 14: 数值对齐一致性
*For any* 包含数值的单元格，应使用居中对齐
**Validates: Requirements 3.7**

### Property 15: 图表位置合理性
*For any* 创建的图表，应放置在对应数据表的右侧或下方，不遮挡数据
**Validates: Requirements 4.1**

### Property 16: 空数据图表跳过
*For any* 图表数据为空的情况，应跳过图表创建且不报错
**Validates: Requirements 4.6**

### Property 17: 题目明细字段完整性
*For any* 题目明细表记录，应包含题目类型、标准答案、AI判断、基准判断、相似度（如有）、错误类型（如有）
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7**

### Property 18: 错误详情对比信息完整性
*For any* 错误详情记录，应包含基准用户答案、AI识别答案、基准判断、AI判断、标准答案、相似度（如有）、严重程度（如有）
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7**

### Property 19: 图表数据点限制
*For any* 图表，当数据点超过50个时，应限制为前50个数据点
**Validates: Requirements 9.2**

### Property 20: 导出错误处理
*For any* 导出失败的情况，应返回包含明确错误信息的JSON响应
**Validates: Requirements 9.5**

### Property 21: 向后兼容性 - 缺失字段处理
*For any* 旧任务数据缺少某些字段时，应使用合理的默认值填充且不报错
**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7**

## Error Handling

### 1. 数据缺失处理

```python
def safe_get(data, key, default=''):
    """安全获取数据，缺失时返回默认值"""
    return data.get(key, default) if data else default

def safe_get_nested(data, keys, default=''):
    """安全获取嵌套数据"""
    try:
        result = data
        for key in keys:
            result = result[key]
        return result
    except (KeyError, TypeError, IndexError):
        return default
```

### 2. 类型转换错误处理

```python
def safe_float(value, default=0.0):
    """安全转换为浮点数"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """安全转换为整数"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
```

### 3. JSON解析错误处理

```python
def safe_json_loads(json_str, default=None):
    """安全解析JSON"""
    if not json_str:
        return default or []
    try:
        return json.loads(json_str) if isinstance(json_str, str) else json_str
    except json.JSONDecodeError:
        return default or []
```

### 4. 导出错误处理

```python
try:
    # 导出逻辑
    wb.save(output)
    return send_file(...)
except Exception as e:
    return jsonify({
        'success': False,
        'error': f'导出失败: {str(e)}'
    }), 500
```

## Testing Strategy

### 单元测试

使用pytest进行单元测试，重点测试：

1. **数据提取函数**
   - 测试各种数据格式的提取
   - 测试缺失字段的默认值处理
   - 测试边界条件

2. **样式应用函数**
   - 测试条件格式的正确应用
   - 测试样式一致性

3. **图表创建函数**
   - 测试各种图表类型的创建
   - 测试空数据的处理

### 属性测试

使用hypothesis进行属性测试，配置每个测试运行100次以上：

```python
from hypothesis import given, strategies as st
import pytest

@given(
    homework_items=st.lists(
        st.fixed_dictionaries({
            'homework_id': st.integers(min_value=1),
            'student_name': st.text(min_size=1, max_size=20),
            'accuracy': st.floats(min_value=0, max_value=1)
        }),
        min_size=1,
        max_size=100
    )
)
def test_property_student_statistics_completeness(homework_items):
    """
    Property 9: 统计表字段完整性
    Feature: batch-evaluation-excel-export-optimization
    Property 9: For any 统计工作表，所有必需字段应被正确填充
    """
    stats = DataExtractor.extract_student_statistics(homework_items)
    
    for stat in stats:
        assert 'student_name' in stat
        assert 'homework_count' in stat
        assert 'total_questions' in stat
        assert 'correct_count' in stat
        assert 'error_count' in stat
        assert 'accuracy' in stat
        assert isinstance(stat['accuracy'], (int, float))
        assert 0 <= stat['accuracy'] <= 1
```

### 集成测试

测试完整的导出流程：

1. 创建测试任务数据
2. 调用导出函数
3. 验证生成的Excel文件
4. 检查所有工作表和数据

### 性能测试

测试大数据量场景：

1. 1000条作业数据的导出时间
2. 10000条题目数据的导出时间
3. 内存使用情况监控

## Performance Optimization

### 1. 批量写入优化

```python
def batch_write_rows(worksheet, data, start_row=1, batch_size=100):
    """批量写入行数据"""
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        for row_idx, row_data in enumerate(batch, start_row + i):
            for col_idx, value in enumerate(row_data, 1):
                worksheet.cell(row=row_idx, column=col_idx, value=value)
```

### 2. 图表数据点限制

```python
def limit_chart_data(data, max_points=50):
    """限制图表数据点数量"""
    if len(data) <= max_points:
        return data
    
    # 均匀采样
    step = len(data) // max_points
    return data[::step][:max_points]
```

### 3. 延迟计算

```python
def lazy_extract_data(task_data):
    """延迟提取数据，只在需要时计算"""
    return {
        'student_stats': lambda: extract_student_statistics(task_data),
        'page_stats': lambda: extract_page_statistics(task_data),
        'type_stats': lambda: extract_type_statistics(task_data)
    }
```

### 4. 内存优化

```python
def stream_write_large_data(worksheet, data_generator):
    """流式写入大数据"""
    for row_idx, row_data in enumerate(data_generator(), 2):
        for col_idx, value in enumerate(row_data, 1):
            worksheet.cell(row=row_idx, column=col_idx, value=value)
        
        # 每1000行清理一次
        if row_idx % 1000 == 0:
            gc.collect()
```

## Backward Compatibility

### 1. 字段缺失处理

```python
def get_with_fallback(item, keys, default=''):
    """
    尝试多个键获取值，支持向后兼容
    
    Args:
        item: 数据字典
        keys: 键列表，按优先级排序
        default: 默认值
    """
    for key in keys:
        if key in item and item[key]:
            return item[key]
    return default

# 使用示例
student_name = get_with_fallback(
    homework_item,
    ['student_name', 'studentName', 'name'],
    '未知学生'
)
```

### 2. 数据结构兼容

```python
def normalize_homework_result(homework_result):
    """标准化作业结果数据结构"""
    if isinstance(homework_result, str):
        homework_result = safe_json_loads(homework_result, [])
    
    # 兼容旧格式
    if isinstance(homework_result, dict):
        homework_result = [homework_result]
    
    return homework_result
```

### 3. 条件性功能

```python
def should_create_essay_sheet(task_data):
    """判断是否应创建作文评分表"""
    subject_id = task_data.get('subject_id')
    if subject_id != 0:  # 非英语学科
        return False
    
    # 检查是否有作文评分数据
    essay_data = extract_essay_scores(
        task_data.get('homework_items', []),
        subject_id
    )
    return essay_data.get('has_essay', False)
```

### 4. 版本标记

```python
def add_export_metadata(worksheet):
    """添加导出元数据"""
    worksheet['Z1'] = 'Export Version'
    worksheet['Z2'] = '2.0'  # 优化后的版本
    worksheet['Z3'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
```
