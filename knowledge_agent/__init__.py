"""
Knowledge Agent - 作业知识点提取与类题生成智能体

基于LangChain构建的智能体，用于：
1. 解析作业图片，提取题目内容
2. 提取知识点和详细解析
3. 根据知识点生成类似题目
4. 导出Excel格式结果
"""

from .models import (
    DifficultyLevel,
    QuestionType,
    KnowledgePoint,
    ParsedQuestion,
    SimilarQuestion,
    DedupeResult,
    TaskProgress,
    TaskConfig,
    AgentTask
)

from .services import (
    ModelService,
    SimilarityService,
    ExcelService,
    StorageService,
    validate_image_format,
    validate_image_size
)

from .agent import HomeworkAgent

__all__ = [
    'DifficultyLevel',
    'QuestionType', 
    'KnowledgePoint',
    'ParsedQuestion',
    'SimilarQuestion',
    'DedupeResult',
    'TaskProgress',
    'TaskConfig',
    'AgentTask',
    'ModelService',
    'SimilarityService',
    'ExcelService',
    'StorageService',
    'validate_image_format',
    'validate_image_size',
    'HomeworkAgent'
]
