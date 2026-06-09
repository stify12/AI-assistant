"""
AI调研员 - 数据模型定义

定义调研任务全流程所需的数据结构：
- 调研任务（ResearchTask）
- 调研提纲（ResearchOutline）
- 数据源与采集结果（DataSource, CollectedData）
- 分析结果（AnalysisResult）
- 调研报告（ResearchReport）
"""

import uuid
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


# ============ 枚举类型 ============

class TaskStatus(Enum):
    """任务状态"""
    CREATED = "created"              # 已创建
    PARSING = "parsing"              # 正在解析需求
    COLLECTING = "collecting"        # 正在采集数据
    CLEANING = "cleaning"            # 正在清洗数据
    ANALYZING = "analyzing"          # 正在分析
    GENERATING = "generating"        # 正在生成报告
    COMPLETED = "completed"          # 已完成
    ITERATING = "iterating"          # 迭代修改中
    FAILED = "failed"                # 失败


class DataSourceType(Enum):
    """数据源类型"""
    WEB_SEARCH = "web_search"        # 联网搜索
    PUBLIC_API = "public_api"        # 公开数据API
    USER_UPLOAD = "user_upload"      # 用户上传文件
    KNOWLEDGE_BASE = "knowledge_base"  # 内置知识库


class AnalysisModelType(Enum):
    """分析模型类型"""
    SWOT = "swot"                    # SWOT分析
    PORTER_FIVE = "porter_five"      # 波特五力模型
    PEST = "pest"                    # PEST分析
    USER_SEGMENTATION = "user_segmentation"  # 用户分层模型
    VALUE_CHAIN = "value_chain"      # 价值链分析
    MARKET_SIZE = "market_size"      # 市场规模估算
    COMPETITIVE = "competitive"      # 竞争格局分析
    CUSTOM = "custom"                # 自定义分析


class ReportFormat(Enum):
    """报告输出格式"""
    MARKDOWN = "markdown"
    WORD = "word"
    PPT_OUTLINE = "ppt_outline"


class CredibilityLevel(Enum):
    """数据可信度等级"""
    HIGH = "high"          # 权威机构官方数据
    MEDIUM = "medium"      # 知名媒体/行业报告
    LOW = "low"            # 非权威来源
    UNVERIFIED = "unverified"  # 未验证
    NO_SOURCE = "no_source"    # 暂无公开数据支撑


# ============ 数据模型 ============

@dataclass
class DataSource:
    """数据源信息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_type: DataSourceType = DataSourceType.WEB_SEARCH
    name: str = ""           # 来源名称（如"国家统计局"）
    url: str = ""            # 来源URL
    publisher: str = ""      # 发布机构
    publish_date: str = ""   # 发布日期
    credibility: CredibilityLevel = CredibilityLevel.UNVERIFIED
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_type": self.source_type.value,
            "name": self.name,
            "url": self.url,
            "publisher": self.publisher,
            "publish_date": self.publish_date,
            "credibility": self.credibility.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DataSource':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            source_type=DataSourceType(data.get("source_type", "web_search")),
            name=data.get("name", ""),
            url=data.get("url", ""),
            publisher=data.get("publisher", ""),
            publish_date=data.get("publish_date", ""),
            credibility=CredibilityLevel(data.get("credibility", "unverified"))
        )


@dataclass
class CollectedData:
    """采集到的数据条目"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""              # 数据标题
    content: str = ""            # 数据内容
    source: DataSource = field(default_factory=DataSource)
    is_verified: bool = False    # 是否已校验
    is_conflicting: bool = False # 是否与其他数据冲突
    conflict_note: str = ""      # 冲突说明
    tags: List[str] = field(default_factory=list)  # 数据标签
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source": self.source.to_dict(),
            "is_verified": self.is_verified,
            "is_conflicting": self.is_conflicting,
            "conflict_note": self.conflict_note,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CollectedData':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            title=data.get("title", ""),
            content=data.get("content", ""),
            source=DataSource.from_dict(data.get("source", {})),
            is_verified=data.get("is_verified", False),
            is_conflicting=data.get("is_conflicting", False),
            conflict_note=data.get("conflict_note", ""),
            tags=data.get("tags", [])
        )


@dataclass
class OutlineItem:
    """调研提纲条目"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""              # 章节标题
    description: str = ""        # 详细说明
    data_requirements: List[str] = field(default_factory=list)  # 需要采集的数据维度
    data_sources: List[str] = field(default_factory=list)       # 推荐数据来源
    sub_items: List['OutlineItem'] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "data_requirements": self.data_requirements,
            "data_sources": self.data_sources,
            "sub_items": [item.to_dict() for item in self.sub_items]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OutlineItem':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            title=data.get("title", ""),
            description=data.get("description", ""),
            data_requirements=data.get("data_requirements", []),
            data_sources=data.get("data_sources", []),
            sub_items=[cls.from_dict(s) for s in data.get("sub_items", [])]
        )


@dataclass
class ResearchOutline:
    """调研提纲"""
    title: str = ""                             # 调研标题
    objective: str = ""                         # 调研目标
    scope: str = ""                             # 调研范围
    methodology: str = ""                       # 调研方法
    items: List[OutlineItem] = field(default_factory=list)
    collection_plan: List[Dict[str, str]] = field(default_factory=list)  # 数据采集计划
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "objective": self.objective,
            "scope": self.scope,
            "methodology": self.methodology,
            "items": [item.to_dict() for item in self.items],
            "collection_plan": self.collection_plan
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ResearchOutline':
        return cls(
            title=data.get("title", ""),
            objective=data.get("objective", ""),
            scope=data.get("scope", ""),
            methodology=data.get("methodology", ""),
            items=[OutlineItem.from_dict(i) for i in data.get("items", [])],
            collection_plan=data.get("collection_plan", [])
        )


@dataclass 
class AnalysisResult:
    """分析结果"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    model_type: AnalysisModelType = AnalysisModelType.SWOT
    title: str = ""              # 分析标题
    content: str = ""            # 分析内容（Markdown格式）
    data_refs: List[str] = field(default_factory=list)  # 引用的数据ID
    source_citations: List[Dict[str, str]] = field(default_factory=list)  # 来源引用
    chart_suggestions: List[Dict[str, str]] = field(default_factory=list)  # 推荐图表
    confidence_note: str = ""    # 可信度说明
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_type": self.model_type.value,
            "title": self.title,
            "content": self.content,
            "data_refs": self.data_refs,
            "source_citations": self.source_citations,
            "chart_suggestions": self.chart_suggestions,
            "confidence_note": self.confidence_note
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AnalysisResult':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            model_type=AnalysisModelType(data.get("model_type", "swot")),
            title=data.get("title", ""),
            content=data.get("content", ""),
            data_refs=data.get("data_refs", []),
            source_citations=data.get("source_citations", []),
            chart_suggestions=data.get("chart_suggestions", []),
            confidence_note=data.get("confidence_note", "")
        )


@dataclass
class ResearchReport:
    """调研报告"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    summary: str = ""            # 执行摘要
    content: str = ""            # 完整报告内容（Markdown）
    sections: List[Dict[str, str]] = field(default_factory=list)  # 各章节
    appendix: List[Dict[str, str]] = field(default_factory=list)  # 附录（数据来源清单等）
    format: ReportFormat = ReportFormat.MARKDOWN
    version: int = 1             # 版本号（支持迭代）
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "sections": self.sections,
            "appendix": self.appendix,
            "format": self.format.value,
            "version": self.version,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ResearchReport':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            content=data.get("content", ""),
            sections=data.get("sections", []),
            appendix=data.get("appendix", []),
            format=ReportFormat(data.get("format", "markdown")),
            version=data.get("version", 1),
            created_at=data.get("created_at", "")
        )


@dataclass
class TaskProgress:
    """任务进度"""
    task_id: str = ""
    current_step: int = 0
    total_steps: int = 0
    status: str = "pending"
    message: str = ""
    progress_percent: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "status": self.status,
            "message": self.message,
            "progress_percent": self.progress_percent
        }


@dataclass
class ResearchTask:
    """调研任务 - 贯穿整个调研流程的核心对象"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: TaskStatus = TaskStatus.CREATED
    query: str = ""                  # 用户输入的调研需求
    industry: str = ""               # 调研行业
    scope: str = ""                  # 调研范围
    
    # 各阶段产出
    outline: Optional[ResearchOutline] = None           # 调研提纲
    collected_data: List[CollectedData] = field(default_factory=list)   # 采集数据
    cleaned_data: List[CollectedData] = field(default_factory=list)     # 清洗后数据
    analysis_results: List[AnalysisResult] = field(default_factory=list)  # 分析结果
    report: Optional[ResearchReport] = None             # 调研报告
    
    # 用户上传的文件
    uploaded_files: List[Dict[str, str]] = field(default_factory=list)
    
    # 迭代历史
    iteration_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    llm_model: str = "deepseek-v3.2"
    total_tokens_used: int = 0
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "query": self.query,
            "industry": self.industry,
            "scope": self.scope,
            "outline": self.outline.to_dict() if self.outline else None,
            "collected_data": [d.to_dict() for d in self.collected_data],
            "cleaned_data": [d.to_dict() for d in self.cleaned_data],
            "analysis_results": [a.to_dict() for a in self.analysis_results],
            "report": self.report.to_dict() if self.report else None,
            "uploaded_files": self.uploaded_files,
            "iteration_history": self.iteration_history,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "llm_model": self.llm_model,
            "total_tokens_used": self.total_tokens_used
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ResearchTask':
        task = cls(
            task_id=data.get("task_id", str(uuid.uuid4())[:8]),
            status=TaskStatus(data.get("status", "created")),
            query=data.get("query", ""),
            industry=data.get("industry", ""),
            scope=data.get("scope", ""),
            uploaded_files=data.get("uploaded_files", []),
            iteration_history=data.get("iteration_history", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            llm_model=data.get("llm_model", "deepseek-v3.2"),
            total_tokens_used=data.get("total_tokens_used", 0)
        )
        
        if data.get("outline"):
            task.outline = ResearchOutline.from_dict(data["outline"])
        if data.get("collected_data"):
            task.collected_data = [CollectedData.from_dict(d) for d in data["collected_data"]]
        if data.get("cleaned_data"):
            task.cleaned_data = [CollectedData.from_dict(d) for d in data["cleaned_data"]]
        if data.get("analysis_results"):
            task.analysis_results = [AnalysisResult.from_dict(a) for a in data["analysis_results"]]
        if data.get("report"):
            task.report = ResearchReport.from_dict(data["report"])
        
        return task
