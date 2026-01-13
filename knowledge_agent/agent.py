"""
HomeworkAgent - 作业知识点智能体

协调图片解析、知识点提取和类题生成的完整工作流
支持：多题识别、自定义提示词、并行处理
"""

import base64
import os
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import (
    ParsedQuestion, KnowledgePoint, SimilarQuestion,
    DedupeResult, AgentTask, TaskConfig, TaskProgress, ImageInfo
)
from .services import ModelService, SimilarityService, StorageService
from .tools import ImageParserTool, KnowledgeExtractorTool, QuestionGeneratorTool, get_default_prompts


class HomeworkAgent:
    """作业知识点智能体"""
    
    def __init__(self, 
                 multimodal_model: str = None,
                 text_model: str = None,
                 config_path: str = "config.json"):
        """
        初始化智能体
        """
        self.model_service = ModelService(config_path)
        self.similarity_service = SimilarityService()
        self.storage_service = StorageService()
        
        # 加载用户偏好
        preferences = self.storage_service.load_preferences()
        self.multimodal_model = multimodal_model or preferences.get('multimodal_model', 'doubao-seed-1-8-251228')
        self.text_model = text_model or preferences.get('text_model', 'deepseek-v3.2')
        
        # 初始化工具
        self.image_parser = ImageParserTool(self.model_service, self.multimodal_model)
        self.knowledge_extractor = KnowledgeExtractorTool(self.model_service, self.text_model)
        self.question_generator = QuestionGeneratorTool(self.model_service, self.text_model)
        
        # 当前任务
        self.current_task: Optional[AgentTask] = None
        self.progress_callback: Optional[Callable[[TaskProgress], None]] = None
        
        # 自定义提示词
        self.custom_prompts = {}
    
    def set_prompts(self, prompts: Dict[str, str]):
        """
        设置自定义提示词
        
        Args:
            prompts: 提示词字典，可包含 parse, extract, generate
        """
        self.custom_prompts = prompts
        
        if 'parse' in prompts:
            self.image_parser.set_prompt(prompts['parse'])
        if 'extract' in prompts:
            self.knowledge_extractor.set_prompt(prompts['extract'])
        if 'generate' in prompts:
            self.question_generator.set_prompt(prompts['generate'])
    
    def get_default_prompts(self) -> Dict[str, str]:
        """获取默认提示词"""
        return get_default_prompts()
    
    def set_progress_callback(self, callback: Callable[[TaskProgress], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def _update_progress(self, current: int, total: int, status: str, message: str):
        """更新进度"""
        if self.progress_callback and self.current_task:
            progress = TaskProgress(
                task_id=self.current_task.task_id,
                current_step=current,
                total_steps=total,
                status=status,
                message=message,
                progress_percent=(current / total * 100) if total > 0 else 0
            )
            self.progress_callback(progress)
    
    def create_task(self, config: TaskConfig = None) -> AgentTask:
        """创建新任务"""
        self.current_task = AgentTask(
            config=config or TaskConfig(
                multimodal_model=self.multimodal_model,
                text_model=self.text_model
            )
        )
        return self.current_task
    
    def add_images(self, image_paths: List[str]) -> List[ImageInfo]:
        """添加图片到当前任务"""
        if not self.current_task:
            self.create_task()
        
        images = []
        for path in image_paths:
            if os.path.exists(path):
                filename = os.path.basename(path)
                img_info = ImageInfo(filename=filename, path=path)
                images.append(img_info)
                self.current_task.images.append(img_info)
        
        return images
    
    def _parse_single_image(self, img_info: ImageInfo) -> List[ParsedQuestion]:
        """解析单张图片，返回多道题目"""
        try:
            with open(img_info.path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            # 解析图片（可能返回多道题）
            questions = self.image_parser._run(image_base64, img_info.filename)
            return questions
        except Exception as e:
            return [ParsedQuestion(
                image_source=img_info.filename,
                content=f"解析失败: {str(e)}"
            )]
    
    def _extract_knowledge_for_question(self, question: ParsedQuestion) -> ParsedQuestion:
        """为单道题目提取知识点"""
        if question.content.startswith("解析失败"):
            return question
        
        try:
            knowledge_points = self.knowledge_extractor._run(
                question.content, question.subject
            )
            question.knowledge_points = knowledge_points
        except Exception as e:
            question.knowledge_points = [KnowledgePoint(primary="提取失败", analysis=str(e))]
        
        return question
    
    def parse_images(self, image_paths: List[str] = None, parallel: bool = True) -> List[ParsedQuestion]:
        """
        批量解析图片
        
        Args:
            image_paths: 图片路径列表
            parallel: 是否并行处理
        """
        if not self.current_task:
            self.create_task()
        
        if image_paths:
            self.add_images(image_paths)
        
        images = self.current_task.images
        total = len(images)
        all_questions = []
        
        # 第一阶段：解析图片识别题目
        self._update_progress(0, total * 2, "processing", "正在识别题目...")
        
        if parallel and total > 1:
            # 并行解析图片
            with ThreadPoolExecutor(max_workers=min(4, total)) as executor:
                futures = {executor.submit(self._parse_single_image, img): img for img in images}
                for idx, future in enumerate(as_completed(futures)):
                    questions = future.result()
                    all_questions.extend(questions)
                    self._update_progress(idx + 1, total * 2, "processing", f"已解析 {idx + 1}/{total} 张图片")
        else:
            # 串行解析
            for idx, img_info in enumerate(images):
                questions = self._parse_single_image(img_info)
                all_questions.extend(questions)
                self._update_progress(idx + 1, total * 2, "processing", f"已解析 {idx + 1}/{total} 张图片")
        
        # 第二阶段：提取知识点
        question_count = len(all_questions)
        self._update_progress(total, total * 2, "processing", f"正在提取知识点（共{question_count}道题）...")
        
        if parallel and question_count > 1:
            # 并行提取知识点
            with ThreadPoolExecutor(max_workers=min(4, question_count)) as executor:
                futures = {executor.submit(self._extract_knowledge_for_question, q): q for q in all_questions}
                processed = []
                for idx, future in enumerate(as_completed(futures)):
                    q = future.result()
                    processed.append(q)
                    self._update_progress(total + idx + 1, total + question_count, "processing", 
                                         f"已提取 {idx + 1}/{question_count} 道题的知识点")
                all_questions = processed
        else:
            # 串行提取
            for idx, question in enumerate(all_questions):
                self._extract_knowledge_for_question(question)
                self._update_progress(total + idx + 1, total + question_count, "processing",
                                     f"已提取 {idx + 1}/{question_count} 道题的知识点")
        
        self.current_task.parsed_questions = all_questions
        self._update_progress(total * 2, total * 2, "completed", f"解析完成，共识别 {question_count} 道题目")
        
        return all_questions
    
    def dedupe_knowledge_points(self, threshold: float = None) -> tuple:
        """知识点去重"""
        if not self.current_task or not self.current_task.parsed_questions:
            return [], []
        
        if threshold is None:
            threshold = self.current_task.config.similarity_threshold
        
        unique_points, dedupe_results = self.similarity_service.dedupe_knowledge_points(
            self.current_task.parsed_questions, threshold
        )
        
        self.current_task.dedupe_results = dedupe_results
        
        return unique_points, dedupe_results
    
    def _generate_for_knowledge_point(self, kp: KnowledgePoint, difficulty: str, 
                                       question_type: str, count: int) -> List[SimilarQuestion]:
        """为单个知识点生成类题"""
        questions = self.question_generator._run(
            kp.primary, kp.analysis, difficulty, question_type, count
        )
        for sq in questions:
            sq.knowledge_point_id = kp.id
        return questions
    
    def generate_similar_questions(self, 
                                    knowledge_points: List[KnowledgePoint] = None,
                                    count_per_point: int = None,
                                    parallel: bool = True) -> List[SimilarQuestion]:
        """
        生成类题
        
        Args:
            knowledge_points: 知识点列表
            count_per_point: 每个知识点生成的类题数量
            parallel: 是否并行处理
        """
        if not self.current_task:
            return []
        
        if count_per_point is None:
            count_per_point = self.current_task.config.questions_per_point
        
        count_per_point = max(1, min(5, count_per_point))
        
        # 收集知识点
        if knowledge_points is None:
            knowledge_points = []
            seen = set()
            for question in self.current_task.parsed_questions:
                for kp in question.knowledge_points:
                    if kp.primary not in seen and not kp.primary.startswith("提取失败"):
                        seen.add(kp.primary)
                        knowledge_points.append(kp)
        
        total = len(knowledge_points)
        if total == 0:
            return []
        
        # 构建知识点到题目信息的映射
        kp_to_question_info = {}
        for question in self.current_task.parsed_questions:
            for kp in question.knowledge_points:
                if kp.id not in kp_to_question_info:
                    kp_to_question_info[kp.id] = {
                        'difficulty': question.difficulty.value,
                        'question_type': question.question_type.value
                    }
        
        similar_questions = []
        
        if parallel and total > 1:
            # 并行生成
            with ThreadPoolExecutor(max_workers=min(4, total)) as executor:
                futures = {}
                for kp in knowledge_points:
                    info = kp_to_question_info.get(kp.id, {'difficulty': '中等', 'question_type': '简答题'})
                    future = executor.submit(
                        self._generate_for_knowledge_point,
                        kp, info['difficulty'], info['question_type'], count_per_point
                    )
                    futures[future] = kp
                
                for idx, future in enumerate(as_completed(futures)):
                    questions = future.result()
                    similar_questions.extend(questions)
                    self._update_progress(idx + 1, total, "processing", f"已生成 {idx + 1}/{total} 个知识点的类题")
        else:
            # 串行生成
            for idx, kp in enumerate(knowledge_points):
                self._update_progress(idx, total, "processing", f"正在生成类题 {idx + 1}/{total}")
                
                info = kp_to_question_info.get(kp.id, {'difficulty': '中等', 'question_type': '简答题'})
                questions = self._generate_for_knowledge_point(
                    kp, info['difficulty'], info['question_type'], count_per_point
                )
                similar_questions.extend(questions)
        
        self.current_task.similar_questions = similar_questions
        self._update_progress(total, total, "completed", f"类题生成完成，共生成 {len(similar_questions)} 道")
        
        return similar_questions
    
    def regenerate_question(self, knowledge_point_id: str) -> List[SimilarQuestion]:
        """重新生成指定知识点的类题"""
        if not self.current_task:
            return []
        
        # 查找知识点
        target_kp = None
        difficulty = "中等"
        question_type = "简答题"
        
        for question in self.current_task.parsed_questions:
            for kp in question.knowledge_points:
                if kp.id == knowledge_point_id:
                    target_kp = kp
                    difficulty = question.difficulty.value
                    question_type = question.question_type.value
                    break
            if target_kp:
                break
        
        if not target_kp:
            return []
        
        # 移除旧的类题
        self.current_task.similar_questions = [
            sq for sq in self.current_task.similar_questions
            if sq.knowledge_point_id != knowledge_point_id
        ]
        
        # 生成新类题
        new_questions = self._generate_for_knowledge_point(
            target_kp, difficulty, question_type,
            self.current_task.config.questions_per_point
        )
        
        self.current_task.similar_questions.extend(new_questions)
        
        return new_questions
    
    def save_task(self) -> str:
        """保存当前任务"""
        if not self.current_task:
            return ""
        return self.storage_service.save_task(self.current_task)
    
    def load_task(self, task_id: str) -> Optional[AgentTask]:
        """加载任务"""
        task = self.storage_service.load_task(task_id)
        if task:
            self.current_task = task
        return task
    
    def get_available_models(self) -> Dict[str, List[Dict[str, str]]]:
        """获取可用模型列表"""
        return self.model_service.get_available_models()
    
    def set_models(self, multimodal_model: str = None, text_model: str = None):
        """设置使用的模型"""
        if multimodal_model:
            self.multimodal_model = multimodal_model
            self.image_parser.model_name = multimodal_model
        
        if text_model:
            self.text_model = text_model
            self.knowledge_extractor.model_name = text_model
            self.question_generator.model_name = text_model
        
        # 保存偏好
        self.storage_service.save_preferences({
            "multimodal_model": self.multimodal_model,
            "text_model": self.text_model,
            "similarity_threshold": self.current_task.config.similarity_threshold if self.current_task else 0.85,
            "questions_per_point": self.current_task.config.questions_per_point if self.current_task else 1
        })
