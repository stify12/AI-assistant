"""
数据模型定义

包含知识点智能体所需的所有数据结构
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import json
import uuid
from datetime import datetime


class DifficultyLevel(Enum):
    """难度等级"""
    EASY = "简单"
    MEDIUM = "中等"
    HARD = "困难"
    
    @classmethod
    def from_string(cls, value: str) -> 'DifficultyLevel':
        """从字符串转换为枚举"""
        for level in cls:
            if level.value == value:
                return level
        return cls.MEDIUM  # 默认中等难度


class QuestionType(Enum):
    """题目类型"""
    CHOICE = "选择题"
    FILL_BLANK = "填空题"
    CALCULATION = "计算题"
    PROOF = "证明题"
    SHORT_ANSWER = "简答题"
    APPLICATION = "应用题"
    
    @classmethod
    def from_string(cls, value: str) -> 'QuestionType':
        """从字符串转换为枚举"""
        for qtype in cls:
            if qtype.value == value:
                return qtype
        return cls.SHORT_ANSWER  # 默认简答题


@dataclass
class KnowledgePoint:
    """知识点"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    primary: str = ""           # 一级知识点（≤20字符）
    secondary: str = ""         # 二级知识点
    analysis: str = ""          # 知识点解析（详细）
    
    def __post_init__(self):
        # 确保一级知识点不超过20字符
        if len(self.primary) > 20:
            self.primary = self.primary[:20]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgePoint':
        return cls(**data)


@dataclass
class ParsedQuestion:
    """解析后的题目"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    image_source: str = ""      # 图片来源
    content: str = ""           # 题目内容
    subject: str = ""           # 学科分类
    question_type: QuestionType = QuestionType.SHORT_ANSWER
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    knowledge_points: List[KnowledgePoint] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'image_source': self.image_source,
            'content': self.content,
            'subject': self.subject,
            'question_type': self.question_type.value,
            'difficulty': self.difficulty.value,
            'knowledge_points': [kp.to_dict() for kp in self.knowledge_points]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedQuestion':
        knowledge_points = [KnowledgePoint.from_dict(kp) for kp in data.get('knowledge_points', [])]
        return cls(
            id=data.get('id', str(uuid.uuid4())[:8]),
            image_source=data.get('image_source', ''),
            content=data.get('content', ''),
            subject=data.get('subject', ''),
            question_type=QuestionType.from_string(data.get('question_type', '简答题')),
            difficulty=DifficultyLevel.from_string(data.get('difficulty', '中等')),
            knowledge_points=knowledge_points
        )


@dataclass
class SimilarQuestion:
    """类题"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    knowledge_point_id: str = ""
    primary: str = ""           # 一级知识点
    secondary: str = ""         # 二级知识点
    content: str = ""           # 类题内容
    answer: str = ""            # 标准答案
    solution_steps: str = ""    # 解题步骤
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    question_type: QuestionType = QuestionType.SHORT_ANSWER
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'knowledge_point_id': self.knowledge_point_id,
            'primary': self.primary,
            'secondary': self.secondary,
            'content': self.content,
            'answer': self.answer,
            'solution_steps': self.solution_steps,
            'difficulty': self.difficulty.value,
            'question_type': self.question_type.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimilarQuestion':
        return cls(
            id=data.get('id', str(uuid.uuid4())[:8]),
            knowledge_point_id=data.get('knowledge_point_id', ''),
            primary=data.get('primary', ''),
            secondary=data.get('secondary', ''),
            content=data.get('content', ''),
            answer=data.get('answer', ''),
            solution_steps=data.get('solution_steps', ''),
            difficulty=DifficultyLevel.from_string(data.get('difficulty', '中等')),
            question_type=QuestionType.from_string(data.get('question_type', '简答题'))
        )


@dataclass
class DedupeResult:
    """去重结果"""
    original_point: str = ""
    merged_point: str = ""
    similarity_score: float = 0.0
    is_merged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DedupeResult':
        return cls(**data)


@dataclass
class TaskProgress:
    """任务进度"""
    task_id: str = ""
    current_step: int = 0
    total_steps: int = 0
    status: str = "pending"     # pending, processing, completed, error
    message: str = ""
    progress_percent: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskProgress':
        return cls(**data)


@dataclass
class TaskConfig:
    """任务配置"""
    multimodal_model: str = "doubao-1-5-vision-pro-32k-250115"
    text_model: str = "deepseek-v3.2"
    similarity_threshold: float = 0.85
    questions_per_point: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskConfig':
        return cls(**data)


@dataclass
class ImageInfo:
    """图片信息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    filename: str = ""
    path: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageInfo':
        return cls(**data)


@dataclass
class AgentTask:
    """智能体任务"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"
    config: TaskConfig = field(default_factory=TaskConfig)
    images: List[ImageInfo] = field(default_factory=list)
    parsed_questions: List[ParsedQuestion] = field(default_factory=list)
    dedupe_results: List[DedupeResult] = field(default_factory=list)
    similar_questions: List[SimilarQuestion] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'created_at': self.created_at,
            'status': self.status,
            'config': self.config.to_dict(),
            'images': [img.to_dict() for img in self.images],
            'parsed_questions': [pq.to_dict() for pq in self.parsed_questions],
            'dedupe_results': [dr.to_dict() for dr in self.dedupe_results],
            'similar_questions': [sq.to_dict() for sq in self.similar_questions]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentTask':
        return cls(
            task_id=data.get('task_id', str(uuid.uuid4())[:8]),
            created_at=data.get('created_at', datetime.now().isoformat()),
            status=data.get('status', 'pending'),
            config=TaskConfig.from_dict(data.get('config', {})),
            images=[ImageInfo.from_dict(img) for img in data.get('images', [])],
            parsed_questions=[ParsedQuestion.from_dict(pq) for pq in data.get('parsed_questions', [])],
            dedupe_results=[DedupeResult.from_dict(dr) for dr in data.get('dedupe_results', [])],
            similar_questions=[SimilarQuestion.from_dict(sq) for sq in data.get('similar_questions', [])]
        )
    
    def to_json(self) -> str:
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentTask':
        """从JSON字符串反序列化"""
        data = json.loads(json_str)
        return cls.from_dict(data)
