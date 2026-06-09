"""
AI调研员 (AI Research Agent) - 全流程行业调研智能体

基于LLM构建的自动化行业调研Agent，覆盖：
1. 需求拆解 → 自动生成调研提纲和数据采集计划
2. 数据采集 → 联网搜索 + 公开API + 用户上传文件
3. 清洗校验 → 去重、过滤、反幻觉校验、冲突检测
4. 分析洞察 → SWOT/波特五力/PEST等标准分析框架
5. 报告生成 → Markdown/Word/PPT大纲多格式输出
6. 迭代优化 → 基于用户反馈多轮修改

技术栈：
- LLM: DeepSeek V3.2 (默认) / GPT / 豆包
- 搜索: DuckDuckGo (免费，无需API Key)
- 框架: Flask Blueprint + SSE流式
- 存储: JSON文件持久化

作者: AI调研员团队
版本: 1.0.0
"""

from .models import (
    ResearchTask, TaskStatus, ResearchOutline, OutlineItem,
    CollectedData, DataSource, DataSourceType, CredibilityLevel,
    AnalysisResult, AnalysisModelType, ResearchReport, ReportFormat,
    TaskProgress
)

from .agent import ResearchAgent

from .services import (
    ModelService, SearchService, DataCleanService,
    FileParseService, ReportService, StorageService
)

from .analysis_models import (
    recommend_models, get_all_models, prepare_analysis_data, MODEL_INFO
)

__all__ = [
    # 核心Agent
    'ResearchAgent',
    
    # 数据模型
    'ResearchTask', 'TaskStatus', 'ResearchOutline', 'OutlineItem',
    'CollectedData', 'DataSource', 'DataSourceType', 'CredibilityLevel',
    'AnalysisResult', 'AnalysisModelType', 'ResearchReport', 'ReportFormat',
    'TaskProgress',
    
    # 服务
    'ModelService', 'SearchService', 'DataCleanService',
    'FileParseService', 'ReportService', 'StorageService',
    
    # 分析模型
    'recommend_models', 'get_all_models', 'prepare_analysis_data', 'MODEL_INFO',
]

__version__ = '1.0.0'
