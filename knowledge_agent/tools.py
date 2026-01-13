"""
LangChain工具定义

包含图片解析、知识点提取、类题生成等工具
支持：多题识别、自定义提示词、并行处理
"""

import json
import re
from typing import List, Optional, Type, Union
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from .models import (
    ParsedQuestion, KnowledgePoint, SimilarQuestion,
    DifficultyLevel, QuestionType
)
from .services import ModelService


def safe_json_loads(text: str) -> Union[dict, list]:
    """安全地解析JSON，处理无效的转义序列（如LaTeX公式）"""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # 修复无效的转义序列：\( \) \frac 等
        fixed_text = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\\1', text)
        try:
            return json.loads(fixed_text)
        except json.JSONDecodeError:
            # 更激进的修复
            cleaned = text.replace('\\', '\\\\')
            cleaned = cleaned.replace('\\\\"', '\\"')
            cleaned = cleaned.replace('\\\\n', '\\n')
            cleaned = cleaned.replace('\\\\r', '\\r')
            cleaned = cleaned.replace('\\\\t', '\\t')
            try:
                return json.loads(cleaned)
            except:
                raise e


def extract_json_from_response(response: str, expect_array: bool = False) -> Union[dict, list, None]:
    """从模型响应中提取JSON"""
    if expect_array:
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            return safe_json_loads(json_match.group())
        return []
    else:
        # 先尝试数组
        array_match = re.search(r'\[[\s\S]*\]', response)
        if array_match:
            try:
                return safe_json_loads(array_match.group())
            except:
                pass
        # 再尝试对象
        obj_match = re.search(r'\{[\s\S]*\}', response)
        if obj_match:
            return safe_json_loads(obj_match.group())
        return None


# ============ 优化后的提示词模板 ============

DEFAULT_PROMPTS = {
    "parse": """你是一个专业的作业识别助手。请仔细分析这张作业图片，识别其中的所有题目。

【输出格式】JSON数组，每道题一个对象：
```json
[
    {
        "content": "完整题目内容，包括题号、选项、条件等",
        "subject": "数学",
        "question_type": "选择题",
        "difficulty": "中等"
    }
]
```

【字段说明】
- content: 题目完整内容，保留原始格式，数学公式用LaTeX表示
- subject: 学科（数学/物理/化学/语文/英语/生物/地理/历史/政治）
- question_type: 题型（选择题/填空题/计算题/证明题/简答题/应用题）
- difficulty: 难度（简单/中等/困难）

【重要要求】
1. 每道题必须单独识别，不要合并
2. 保留题目的完整信息，包括所有选项和条件
3. 数学符号用LaTeX格式，如 x^2, \\frac{a}{b}, \\sqrt{x}
4. 只输出JSON数组，不要任何解释文字""",

    "extract": """你是一个专业的教育知识点分析专家。请分析以下题目，提取其核心知识点。

【题目信息】
内容：{content}
学科：{subject}

【输出格式】只输出一个知识点对象：
```json
{
    "primary": "一级知识点",
    "secondary": "二级知识点详细描述",
    "solution_approach": "解题思路"
}
```

【字段说明】
- primary: 一级知识点，精炼概括，不超过10个字（如：一元二次方程、三角函数、力的合成）
- secondary: 二级知识点，详细描述具体考查内容（如：求根公式的应用、判别式的意义）
- solution_approach: 解题思路，包含解题步骤、关键公式、注意事项

【重要要求】
1. 每道题只提取一个最核心的知识点
2. 一级知识点必须精炼，便于分类和检索
3. 二级知识点要具体，说明考查的具体内容
4. 解题思路要清晰，包含关键步骤
5. 只输出JSON对象，不要任何解释文字""",

    "generate": """你是一个专业的题目生成专家。请根据以下知识点信息，生成{count}道类似的练习题。

【知识点信息】
一级知识点：{primary}
二级知识点：{secondary}
解题思路：{solution_approach}
难度要求：{difficulty}
题型要求：{type}

【输出格式】JSON数组：
```json
[
    {
        "primary": "一级知识点",
        "secondary": "二级知识点",
        "content": "题目内容",
        "answer": "标准答案",
        "solution_steps": "详细解题步骤"
    }
]
```

【重要要求】
1. 题目必须考查相同的知识点
2. 难度与原题保持一致
3. 题型与要求一致
4. 答案必须正确，解题步骤清晰
5. 数学公式用LaTeX格式
6. 每道题都要包含primary和secondary字段
7. 只输出JSON数组，不要任何解释文字"""
}


# ============ 工具输入模型 ============

class ImageParserInput(BaseModel):
    image_base64: str = Field(description="Base64编码的图片")
    image_source: str = Field(description="图片来源/文件名")


class KnowledgeExtractorInput(BaseModel):
    question_content: str = Field(description="题目内容")
    subject: str = Field(default="", description="学科分类")


class QuestionGeneratorInput(BaseModel):
    primary: str = Field(description="一级知识点")
    secondary: str = Field(description="二级知识点")
    solution_approach: str = Field(description="解题思路")
    difficulty: str = Field(default="中等", description="难度等级")
    question_type: str = Field(default="简答题", description="题目类型")
    count: int = Field(default=1, description="生成数量")


# ============ LangChain工具 ============

class ImageParserTool(BaseTool):
    """图片解析工具"""
    
    name: str = "image_parser"
    description: str = "解析作业图片，识别所有题目"
    args_schema: Type[BaseModel] = ImageParserInput
    
    model_service: ModelService = None
    model_name: str = "doubao-seed-1-8-251228"
    custom_prompt: str = None
    
    def __init__(self, model_service: ModelService = None, model_name: str = None):
        super().__init__()
        self.model_service = model_service or ModelService()
        if model_name:
            self.model_name = model_name
    
    def set_prompt(self, prompt: str):
        self.custom_prompt = prompt
    
    def _run(self, image_base64: str, image_source: str = "") -> List[ParsedQuestion]:
        prompt = self.custom_prompt or DEFAULT_PROMPTS["parse"]
        
        try:
            response = self.model_service.call_multimodal(
                self.model_name, image_base64, prompt
            )
            data = extract_json_from_response(response)
            questions = []
            
            if isinstance(data, list):
                for item in data:
                    q = ParsedQuestion(
                        image_source=image_source,
                        content=item.get('content', ''),
                        subject=item.get('subject', ''),
                        question_type=QuestionType.from_string(item.get('question_type', '简答题')),
                        difficulty=DifficultyLevel.from_string(item.get('difficulty', '中等'))
                    )
                    questions.append(q)
            elif isinstance(data, dict):
                q = ParsedQuestion(
                    image_source=image_source,
                    content=data.get('content', ''),
                    subject=data.get('subject', ''),
                    question_type=QuestionType.from_string(data.get('question_type', '简答题')),
                    difficulty=DifficultyLevel.from_string(data.get('difficulty', '中等'))
                )
                questions.append(q)
            else:
                questions.append(ParsedQuestion(image_source=image_source, content=response))
            
            return questions
        except Exception as e:
            return [ParsedQuestion(image_source=image_source, content=f"解析失败: {str(e)}")]


class KnowledgeExtractorTool(BaseTool):
    """知识点提取工具 - 每道题只提取一个核心知识点"""
    
    name: str = "knowledge_extractor"
    description: str = "从题目中提取核心知识点"
    args_schema: Type[BaseModel] = KnowledgeExtractorInput
    
    model_service: ModelService = None
    model_name: str = "deepseek-v3.2"
    custom_prompt: str = None
    
    def __init__(self, model_service: ModelService = None, model_name: str = None):
        super().__init__()
        self.model_service = model_service or ModelService()
        if model_name:
            self.model_name = model_name
    
    def set_prompt(self, prompt: str):
        self.custom_prompt = prompt
    
    def _run(self, question_content: str, subject: str = "") -> KnowledgePoint:
        """返回单个知识点"""
        prompt_template = self.custom_prompt or DEFAULT_PROMPTS["extract"]
        prompt = prompt_template.replace("{content}", question_content).replace("{subject}", subject)
        
        try:
            response = self.model_service.call_text_generation(self.model_name, prompt)
            
            # 尝试解析为对象
            obj_match = re.search(r'\{[\s\S]*\}', response)
            if obj_match:
                data = safe_json_loads(obj_match.group())
                if isinstance(data, dict):
                    return KnowledgePoint(
                        primary=str(data.get('primary', ''))[:10],
                        secondary=data.get('secondary', ''),
                        analysis=data.get('solution_approach', data.get('analysis', ''))
                    )
            
            # 兼容数组格式
            array_match = re.search(r'\[[\s\S]*\]', response)
            if array_match:
                data = safe_json_loads(array_match.group())
                if isinstance(data, list) and len(data) > 0:
                    item = data[0]
                    return KnowledgePoint(
                        primary=str(item.get('primary', ''))[:10],
                        secondary=item.get('secondary', ''),
                        analysis=item.get('solution_approach', item.get('analysis', ''))
                    )
            
            return KnowledgePoint(primary="未识别", analysis=response)
        except Exception as e:
            return KnowledgePoint(primary="提取失败", analysis=str(e))


class QuestionGeneratorTool(BaseTool):
    """类题生成工具"""
    
    name: str = "question_generator"
    description: str = "根据知识点生成类题"
    args_schema: Type[BaseModel] = QuestionGeneratorInput
    
    model_service: ModelService = None
    model_name: str = "deepseek-v3.2"
    custom_prompt: str = None
    
    def __init__(self, model_service: ModelService = None, model_name: str = None):
        super().__init__()
        self.model_service = model_service or ModelService()
        if model_name:
            self.model_name = model_name
    
    def set_prompt(self, prompt: str):
        self.custom_prompt = prompt
    
    def _run(self, primary: str, secondary: str, solution_approach: str,
             difficulty: str = "中等", question_type: str = "简答题",
             count: int = 1) -> List[SimilarQuestion]:
        prompt_template = self.custom_prompt or DEFAULT_PROMPTS["generate"]
        prompt = (prompt_template
                  .replace("{primary}", primary)
                  .replace("{secondary}", secondary)
                  .replace("{solution_approach}", solution_approach)
                  .replace("{difficulty}", difficulty)
                  .replace("{type}", question_type)
                  .replace("{count}", str(count)))
        
        try:
            response = self.model_service.call_text_generation(self.model_name, prompt)
            data = extract_json_from_response(response, expect_array=True)
            
            similar_questions = []
            for item in data[:count]:
                if isinstance(item, dict):
                    sq = SimilarQuestion(
                        content=item.get('content', ''),
                        answer=item.get('answer', ''),
                        solution_steps=item.get('solution_steps', ''),
                        difficulty=DifficultyLevel.from_string(difficulty),
                        question_type=QuestionType.from_string(question_type),
                        primary=item.get('primary', primary),
                        secondary=item.get('secondary', secondary)
                    )
                    similar_questions.append(sq)
            
            return similar_questions if similar_questions else [
                SimilarQuestion(content="生成失败：无有效输出", primary=primary, secondary=secondary)
            ]
        except Exception as e:
            return [SimilarQuestion(content=f"生成失败: {str(e)}", primary=primary, secondary=secondary)]


def get_default_prompts() -> dict:
    return DEFAULT_PROMPTS.copy()
