"""
测试用例生成服务
AI 自动生成基准效果，用于系统性测试 AI 批改准确性
"""
import json
import re
from typing import List, Dict, Optional
from .database_service import DatabaseService, AppDatabaseService
from .llm_service import LLMService


# 数学学科预设模板
MATH_TEMPLATES = {
    "math_baseline": {
        "name": "基准测试",
        "tags": ["答案正确", "工整书写"],
        "correct": "yes",
        "score_ratio": 1.0,
        "prompt_hint": "工整、规范地书写正确答案，笔画清晰，位置居中"
    },
    "math_wrong_common": {
        "name": "常见错误",
        "tags": ["答案错误", "计算错误"],
        "correct": "no",
        "score_ratio": 0,
        "prompt_hint": "根据题目类型生成常见的计算错误或概念混淆错误"
    },
    "math_wrong_careless": {
        "name": "粗心错误",
        "tags": ["答案错误", "粗心错误"],
        "correct": "no",
        "score_ratio": 0,
        "prompt_hint": "生成抄错数字、漏写符号、正负号错误等粗心错误"
    },
    "math_digit_confuse": {
        "name": "数字混淆",
        "tags": ["答案正确", "数字混淆"],
        "correct": "yes",
        "score_ratio": 1.0,
        "prompt_hint": "答案正确，但数字书写潦草：1的竖线带钩像7、0写得扁像6、6的圈没闭合像0、9的尾巴短像4。AI应正确识别"
    },
    "math_symbol_confuse": {
        "name": "符号混淆",
        "tags": ["答案正确", "符号混淆"],
        "correct": "yes",
        "score_ratio": 1.0,
        "prompt_hint": "答案正确，但符号书写潦草：×的交叉像x、+的横短像t、=的两横不平行。AI应正确识别"
    },
    "math_similar_looking": {
        "name": "形近干扰",
        "tags": ["答案错误", "形近干扰"],
        "correct": "no",
        "score_ratio": 0,
        "prompt_hint": "答案错误，写成了形近的错误内容：把1写成7、把6写成0、小数点位置错误(37.5→375)。AI应判错误"
    },
    "math_equivalent": {
        "name": "等价表达",
        "tags": ["答案正确", "等价表达"],
        "correct": "yes",
        "score_ratio": 1.0,
        "prompt_hint": "数学等价的不同表达：小数↔分数(0.5=1/2)、分数↔百分数(1/2=50%)"
    },
    "math_fraction": {
        "name": "分数书写",
        "tags": ["答案正确", "分数"],
        "correct": "yes",
        "score_ratio": 1.0,
        "prompt_hint": "分数书写测试：分数线长度、上下数字对齐、约分形式"
    },
    "math_messy": {
        "name": "潦草书写",
        "tags": ["答案正确", "潦草书写"],
        "correct": "yes",
        "score_ratio": 1.0,
        "prompt_hint": "正确答案但字迹潦草：倾斜、连笔、大小不一"
    },
    "math_crossed": {
        "name": "涂改痕迹",
        "tags": ["答案正确", "涂改痕迹"],
        "correct": "yes",
        "score_ratio": 1.0,
        "prompt_hint": "有涂改痕迹但最终答案正确：划掉重写、涂黑修改"
    },
    "math_partial": {
        "name": "部分正确",
        "tags": ["部分正确"],
        "correct": "partial",
        "score_ratio": 0.5,
        "prompt_hint": "多步骤解答题，部分步骤正确，部分步骤错误"
    },
    "math_blank": {
        "name": "空白未答",
        "tags": ["空白"],
        "correct": "no",
        "score_ratio": 0,
        "prompt_hint": "完全空白，未作答"
    },
    # 概念错误类
    "math_formula_error": {
        "name": "公式记错",
        "tags": ["答案错误", "概念错误", "公式错误"],
        "correct": "no",
        "score_ratio": 0,
        "prompt_hint": "公式应用错误：如圆面积用2πr（应为πr²）、球体积用4πr²（应为4/3πr³）、勾股定理a+b=c（应为a²+b²=c²）"
    },
    "math_order_error": {
        "name": "运算顺序错",
        "tags": ["答案错误", "概念错误", "运算顺序"],
        "correct": "no",
        "score_ratio": 0,
        "prompt_hint": "运算顺序错误：如2+3×4=20（应为14，先乘后加）、8÷2×4=1（应为16，从左到右）"
    },
    "math_bracket_error": {
        "name": "括号处理错",
        "tags": ["答案错误", "概念错误", "括号展开"],
        "correct": "no",
        "score_ratio": 0,
        "prompt_hint": "括号展开错误：如(a+b)²=a²+b²（应为a²+2ab+b²）、-(a-b)=-a-b（应为-a+b）、2(x+3)=2x+3（应为2x+6）"
    },
    "math_fraction_op": {
        "name": "分数运算错",
        "tags": ["答案错误", "概念错误", "分数运算"],
        "correct": "no",
        "score_ratio": 0,
        "prompt_hint": "分数运算错误：如1/2+1/3=2/5（应为5/6，通分后相加）、1/2×1/3=1/5（应为1/6）、1/2÷1/3=1/6（应为3/2）"
    }
}

# 快捷模板组合
TEMPLATE_COMBINATIONS = {
    "full_test": {
        "name": "全面测试",
        "templates": list(MATH_TEMPLATES.keys()),
        "description": "覆盖全部测试场景，完整评估 AI 能力"
    },
    "quick_test": {
        "name": "快速测试",
        "templates": ["math_baseline", "math_wrong_common", "math_wrong_careless", "math_digit_confuse"],
        "description": "快速验证 AI 基础识别和判断能力（错误多于正确）"
    },
    "digit_focus": {
        "name": "数字识别专项",
        "templates": ["math_digit_confuse", "math_symbol_confuse", "math_similar_looking", "math_equivalent"],
        "description": "专项测试数字和符号的识别能力"
    },
    "writing_focus": {
        "name": "书写质量专项",
        "templates": ["math_messy", "math_crossed", "math_baseline"],
        "description": "专项测试对不同书写质量的容忍度"
    },
    "error_focus": {
        "name": "错误判断专项",
        "templates": ["math_wrong_common", "math_wrong_careless", "math_partial", "math_similar_looking", "math_blank"],
        "description": "专项测试错误答案的判断能力（全部错误场景）"
    },
    "concept_error": {
        "name": "概念错误专项",
        "templates": ["math_formula_error", "math_order_error", "math_bracket_error", "math_fraction_op"],
        "description": "专项测试概念性错误的判断能力（公式、运算顺序、括号、分数）"
    }
}


class TestcaseGeneratorService:
    """测试用例生成服务"""
    
    @staticmethod
    def get_questions_from_datavalue(book_id: str, page_num: int) -> Dict:
        """
        从 zp_book_chapter 表获取题目结构（书本页面原始数据）
        """
        try:
            sql = """
                SELECT c.data_value, c.pic_path, b.book_name, b.subject_id
                FROM zp_book_chapter c
                LEFT JOIN zp_make_book b ON c.book_id = b.id
                WHERE c.book_id = %s AND c.page_num = %s
                LIMIT 1
            """
            row = DatabaseService.execute_one(sql, (book_id, page_num))
            
            if not row or not row.get('data_value'):
                return {'success': False, 'error': f'未找到页码 {page_num} 的题目数据'}
            
            data_value = json.loads(row['data_value'])
            questions = TestcaseGeneratorService._extract_questions(data_value)
            
            return {
                'success': True,
                'data': {
                    'book_id': book_id,
                    'book_name': row.get('book_name', ''),
                    'subject_id': row.get('subject_id', 2),
                    'page_num': page_num,
                    'questions': questions,
                    'total': len(questions),
                    'picPath': row.get('pic_path', '')
                }
            }
        except Exception as e:
            print(f"[TestcaseGenerator] 获取题目失败: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _extract_questions(data_value: List[Dict]) -> List[Dict]:
        """
        提取题目
        - 有 children 且有答案：从大题 content 中解析小题内容
        - 没有 children：直接提取大题
        """
        questions = []
        
        for item in data_value:
            children = item.get('children', [])
            parent_content = item.get('content', '') or ''
            parent_index = item.get('index', '')
            
            # 检查 children 是否有答案（jans 或 ans）
            valid_children = [c for c in children if c.get('jans') or c.get('ans')]
            
            if valid_children:
                # 有小题，从大题 content 中解析各小题内容
                for child in valid_children:
                    child_index = child.get('index', '')
                    
                    # 从大题 content 中提取该小题的内容
                    child_content = TestcaseGeneratorService._extract_sub_content(
                        parent_content, child_index, parent_index
                    )
                    
                    # 如果提取失败，显示完整大题内容（不截断）
                    if not child_content:
                        clean_content = re.sub(r'<br\s*/?>', '\n', parent_content)
                        clean_content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'[图:\1]', clean_content)
                        clean_content = re.sub(r'<[^>]+>', '', clean_content)
                        # 完整显示，标注小题序号
                        child_content = f"[第{child_index}小题，完整题目如下]\n{clean_content.strip()}"
                    
                    questions.append(TestcaseGeneratorService._format_question(child, child_content))
            else:
                # 没有有效小题，提取大题本身（如果有答案）
                if item.get('jans') or item.get('ans'):
                    questions.append(TestcaseGeneratorService._format_question(item))
        
        return questions
    
    @staticmethod
    def _extract_sub_content(parent_content: str, child_index: str, parent_index: str = '') -> str:
        """
        从大题 content 中提取指定小题的内容
        多策略匹配，确保提取成功率
        """
        if not parent_content or not child_index:
            return ''
        
        # 圈数字映射
        circle_nums = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']
        # 中文数字映射
        cn_nums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        
        # 提取小题序号数字
        match = re.search(r'\((\d+)\)', child_index)
        if match:
            sub_num = match.group(1)
        else:
            match = re.search(r'(\d+)', child_index)
            sub_num = match.group(1) if match else '1'
        
        sub_int = int(sub_num) if sub_num.isdigit() else 1
        
        # 构建当前小题的匹配模式（按优先级排序）
        patterns = [
            rf'\({sub_num}\)',           # (1)
            rf'（{sub_num}）',            # （1）
            rf'(?<![0-9]){sub_num}\s*[\.、]',  # 1. 或 1、
        ]
        
        # 圈数字
        if 1 <= sub_int <= 10:
            patterns.append(re.escape(circle_nums[sub_int - 1]))
            patterns.append(rf'[\(（]{cn_nums[sub_int - 1]}[\)）]')  # (一)
        
        # 查找起始位置
        start_pos = -1
        matched_pattern = None
        for pattern in patterns:
            match = re.search(pattern, parent_content)
            if match:
                start_pos = match.start()
                matched_pattern = pattern
                break
        
        if start_pos == -1:
            return ''
        
        # 构建下一个小题的匹配模式
        next_num = str(sub_int + 1)
        next_patterns = [
            rf'\({next_num}\)',
            rf'（{next_num}）',
            rf'(?<![0-9]){next_num}\s*[\.、]',
        ]
        if sub_int < 10:
            next_patterns.append(re.escape(circle_nums[sub_int]))
            next_patterns.append(rf'[\(（]{cn_nums[sub_int]}[\)）]')
        
        # 查找结束位置
        end_pos = len(parent_content)
        for pattern in next_patterns:
            match = re.search(pattern, parent_content[start_pos + 1:])
            if match:
                end_pos = start_pos + 1 + match.start()
                break
        
        # 提取内容
        content = parent_content[start_pos:end_pos].strip()
        
        # 清理开头的序号标记
        content = re.sub(r'^[\(（]\d+[\)）]\s*', '', content)
        content = re.sub(r'^[\(（][一二三四五六七八九十][\)）]\s*', '', content)
        content = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', content)
        content = re.sub(r'^\d+\s*[\.、]\s*', '', content)
        
        # 清理 HTML
        content = re.sub(r'<br\s*/?>', '\n', content)
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'[图:\1]', content)
        
        return content.strip()
    
    @staticmethod
    def _latex_to_readable(text: str) -> str:
        """将 LaTeX 公式转换为可读文本"""
        if not text:
            return text
        
        # 去掉 $ 符号
        text = re.sub(r'\$([^$]+)\$', r'\1', text)
        
        # 处理 cases 环境：\begin{cases}...\end{cases} -> 用分号分隔
        text = re.sub(r'\\begin\{cases\}', '', text)
        text = re.sub(r'\\end\{cases\}', '', text)
        text = re.sub(r'\\\\', '; ', text)  # LaTeX 换行符 -> 分号
        
        # 先处理转义括号 \{ \} \[ \] -> 占位符
        text = text.replace(r'\{', '⟨LBRACE⟩')
        text = text.replace(r'\}', '⟨RBRACE⟩')
        text = text.replace(r'\[', '[')
        text = text.replace(r'\]', ']')
        
        # 常用数学符号
        replacements = [
            (r'\\mid\b', ' | '),
            (r'\\angle\s*', '∠'),
            (r'\^\\circ', '°'),
            (r'\\circ', '°'),
            (r'\\therefore\s*', '∴ '),
            (r'\\because\s*', '∵ '),
            (r'\\times', '×'),
            (r'\\div', '÷'),
            (r'\\pm', '±'),
            (r'\\neq', '≠'),
            (r'\\geqslant', '≥'),
            (r'\\leqslant', '≤'),
            (r'\\leq', '≤'),
            (r'\\geq', '≥'),
            (r'\\approx', '≈'),
            (r'\\infty', '∞'),
            (r'\\emptyset', '∅'),
            (r'\\varnothing', '∅'),
            (r'\\in\b', '∈'),
            (r'\\notin', '∉'),
            (r'\\subset', '⊂'),
            (r'\\subseteq', '⊆'),
            (r'\\supset', '⊃'),
            (r'\\supseteq', '⊇'),
            (r'\\cap', '∩'),
            (r'\\cup', '∪'),
            (r'\\sqrt\{([^}]+)\}', r'√(\1)'),
            (r'\\dfrac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)'),
            (r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)'),
            (r'\\pi', 'π'),
            (r'\\alpha', 'α'),
            (r'\\beta', 'β'),
            (r'\\gamma', 'γ'),
            (r'\\delta', 'δ'),
            (r'\\theta', 'θ'),
            (r'\\lambda', 'λ'),
            (r'\\mu', 'μ'),
            (r'\\sigma', 'σ'),
            (r'\\omega', 'ω'),
            (r'\\Delta', 'Δ'),
            (r'\\perp', '⊥'),
            (r'\\parallel', '∥'),
            (r'\\triangle', '△'),
            (r'\\quad', ' '),
            (r'\\,', ' '),
            (r'\\;', ' '),
            (r'\\ ', ' '),
            (r'\\text\{([^}]+)\}', r'\1'),
            (r'\\slant\{?(\d+)\}?', r'\1'),  # \slant{1} 或 \slant1 -> 1
            (r'\\mathit\{([^}]+)\}', r'\1'),  # \mathit{x} -> x
        ]
        
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)
        
        # 清理残留的反斜杠命令
        text = re.sub(r'\\[a-zA-Z]+', '', text)
        
        # 还原集合花括号
        text = text.replace('⟨LBRACE⟩', '{')
        text = text.replace('⟨RBRACE⟩', '}')
        
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def _format_question(item: Dict, parsed_content: str = None) -> Dict:
        """格式化单个题目"""
        # 标准答案：优先取 jans，没有则取 ans、answer
        answer = item.get('jans', '') or item.get('ans', '') or item.get('answer', '') or ''
        
        # 转换 LaTeX 为可读格式
        answer = TestcaseGeneratorService._latex_to_readable(str(answer).strip())
        
        # 分数：注意 datavalue 中字段名是 sorce（拼写错误）
        max_score = item.get('sorce') if item.get('sorce') is not None else item.get('score')
        
        # content：优先使用解析出的内容，否则使用原始 content
        content = parsed_content if parsed_content else (item.get('content', '') or '')
        
        # 清理 content 中的 HTML
        if content and not parsed_content:
            content = re.sub(r'<br\s*/?>', '\n', content)
            content = re.sub(r'<[^>]+>', '', content)
            content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'[图:\1]', content)
        
        return {
            'index': str(item.get('index', '')),
            'tempIndex': item.get('tempIndex', 0),
            'content': content,
            'questionType': item.get('questionType', 'objective'),
            'bvalue': str(item.get('bvalue', '4')),
            'answer': answer,
            'maxScore': max_score
        }
    
    @staticmethod
    def get_default_scenarios(subject_id: int = 2) -> Dict:
        """获取默认测试场景配置"""
        return {
            'success': True,
            'data': {
                'templates': MATH_TEMPLATES,
                'combinations': TEMPLATE_COMBINATIONS,
                'default_combination': 'quick_test'
            }
        }

    
    @staticmethod
    def generate_base_effects(
        questions: List[Dict],
        selected_templates: List[str],
        template_ratios: Dict[str, int] = None,
        user_id: str = None
    ) -> Dict:
        """生成基准效果"""
        if not questions:
            return {'success': False, 'error': '题目列表为空'}
        
        if not selected_templates:
            return {'success': False, 'error': '未选择测试场景'}
        
        try:
            if not template_ratios:
                template_ratios = {t: 100 // len(selected_templates) for t in selected_templates}
            
            assignments = TestcaseGeneratorService._assign_templates(
                questions, selected_templates, template_ratios
            )
            
            prompt = TestcaseGeneratorService._build_generation_prompt(questions, assignments)
            
            result = LLMService.call_deepseek(
                prompt=prompt,
                system_prompt='你是一个专业的 AI 批改系统测试用例设计师，擅长设计各种边界场景的测试用例。请严格按照 JSON 格式输出。',
                model='deepseek-chat',
                timeout=120,
                user_id=user_id
            )
            
            if result.get('error'):
                return {'success': False, 'error': result['error']}
            
            content = result.get('content', '')
            base_effects = LLMService.extract_json_array(content)
            
            if not base_effects:
                return {'success': False, 'error': '无法解析生成结果', 'raw_content': content[:500]}
            
            # 补全 AI 返回数据中缺失的 tags 和 fillGuide 字段
            # 从 assignments 中获取预设的 tags
            assignments_map = {a['question']['index']: a for a in assignments}
            for effect in base_effects:
                idx = effect.get('index', '')
                assignment = assignments_map.get(idx)
                # 如果 AI 没有返回 tags，使用 assignment 中的预设 tags
                if not effect.get('tags') and assignment:
                    effect['tags'] = assignment.get('tags', [])
                # 确保 fillGuide 字段存在
                if not effect.get('fillGuide'):
                    effect['fillGuide'] = ''
            
            summary = TestcaseGeneratorService._summarize_results(base_effects)
            
            return {'success': True, 'data': {'base_effects': base_effects, 'summary': summary}}
            
        except Exception as e:
            print(f"[TestcaseGenerator] 生成失败: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _assign_templates(
        questions: List[Dict],
        selected_templates: List[str],
        template_ratios: Dict[str, int]
    ) -> List[Dict]:
        """按比例分配模板到各题目"""
        total = len(questions)
        assignments = []
        
        total_ratio = sum(template_ratios.get(t, 0) for t in selected_templates)
        if total_ratio == 0:
            total_ratio = 100
        
        template_counts = {}
        assigned = 0
        for i, template_id in enumerate(selected_templates):
            ratio = template_ratios.get(template_id, 100 // len(selected_templates))
            if i == len(selected_templates) - 1:
                count = total - assigned
            else:
                count = round(total * ratio / total_ratio)
            template_counts[template_id] = count
            assigned += count
        
        question_idx = 0
        for template_id in selected_templates:
            count = template_counts.get(template_id, 0)
            template_info = MATH_TEMPLATES.get(template_id, {})
            
            for _ in range(count):
                if question_idx >= total:
                    break
                    
                q = questions[question_idx]
                assignments.append({
                    'question': q,
                    'template_id': template_id,
                    'template_name': template_info.get('name', template_id),
                    'tags': template_info.get('tags', []),
                    'correct': template_info.get('correct', 'yes'),
                    'score_ratio': template_info.get('score_ratio', 1.0),
                    'prompt_hint': template_info.get('prompt_hint', '')
                })
                question_idx += 1
        
        return assignments
    
    @staticmethod
    def _build_generation_prompt(questions: List[Dict], assignments: List[Dict]) -> str:
        """构建 LLM 生成提示词"""
        questions_info = []
        for i, a in enumerate(assignments):
            q = a['question']
            questions_info.append({
                'seq': i + 1,
                'index': q['index'],
                'tempIndex': q['tempIndex'],
                'standardAnswer': q['answer'],  # 明确是标准答案
                'maxScore': q.get('maxScore'),
                'bvalue': q['bvalue'],
                'content': q['content'][:100] if q.get('content') else '',
                'testScenario': a['template_name'],
                'scenarioTags': a['tags'],
                'expectedResult': a['correct'],
                'scenarioHint': a['prompt_hint']
            })
        
        questions_json = json.dumps(questions_info, ensure_ascii=False, indent=2)
        
        prompt = f"""你是一个专业的 AI 批改系统测试用例设计师。请为每道题生成一个测试用例。

## 任务说明
根据每道题的「标准答案」和「测试场景」，生成学生可能书写的「应填答案」。
- 标准答案(standardAnswer)：题目的正确答案
- 应填答案(userAnswer)：学生实际书写的内容，需要根据测试场景生成

## 题目信息（共 {len(assignments)} 道题）
{questions_json}

## 生成规则
1. 每道题只生成一个测试用例
2. **answer 字段**：直接复制 standardAnswer 的值，这是标准答案
3. **userAnswer 字段**：根据测试场景(testScenario)和提示(scenarioHint)生成学生书写的内容
   - 如果是"数字混淆"场景，userAnswer 应该是把数字写得像其他数字（如0写成6）
   - 如果是"常见错误"场景，userAnswer 应该是错误的答案
   - 如果是"基准测试"场景，userAnswer 应该和标准答案相同
4. **correct 字段**：使用 expectedResult 的值
5. **tags 字段**：使用 scenarioTags 的值
6. **fillGuide 字段**：简短描述学生书写的特点（如"数字0写得像6"）

## 输出格式
返回 JSON 数组，每个元素包含：
- index: 题号（复制原值）
- tempIndex: 序号（复制原值）
- answer: 标准答案（复制 standardAnswer）
- userAnswer: 学生书写的答案（根据场景生成）
- correct: 预期结果 yes/no/partial（复制 expectedResult）
- maxScore: 满分（复制原值）
- score: 得分（根据 correct 计算）
- tags: 标签数组（复制 scenarioTags）
- fillGuide: 书写特点描述

## 示例
如果标准答案是 "120"，测试场景是"数字混淆"：
- answer: "120"
- userAnswer: "120"（但书写时0像6）
- fillGuide: "数字0写得像6，需要AI正确识别"

请直接输出 JSON 数组，不要有其他内容。"""
        
        return prompt
    
    @staticmethod
    def _summarize_results(base_effects: List[Dict]) -> Dict:
        """统计生成结果"""
        summary = {
            'total': len(base_effects),
            'by_correct': {'yes': 0, 'no': 0, 'partial': 0},
            'by_tags': {}
        }
        
        for item in base_effects:
            correct = item.get('correct', 'no')
            if correct in summary['by_correct']:
                summary['by_correct'][correct] += 1
            
            tags = item.get('tags', [])
            for tag in tags:
                if tag not in summary['by_tags']:
                    summary['by_tags'][tag] = 0
                summary['by_tags'][tag] += 1
        
        return summary
    
    @staticmethod
    def save_as_dataset(
        book_id: str,
        book_name: str,
        subject_id: int,
        page_num: int,
        base_effects: List[Dict],
        dataset_name: str = None,
        description: str = None,
        save_score: bool = False
    ) -> Dict:
        """保存生成的基准效果为数据集
        
        Args:
            save_score: 是否保存评分字段(score/maxScore)，默认不保存
        """
        import uuid
        
        try:
            dataset_id = str(uuid.uuid4())[:8]
            
            if not dataset_name:
                dataset_name = f"{book_name}P{page_num}-AI生成测试用例"
            
            AppDatabaseService.create_dataset(
                dataset_id=dataset_id,
                book_id=book_id,
                pages=[page_num],
                book_name=book_name,
                subject_id=subject_id,
                question_count=len(base_effects),
                name=dataset_name,
                description=description
            )
            
            # 调试日志：打印第一条数据的完整结构
            if base_effects:
                print(f"[TestcaseGenerator] 第一条数据完整结构: {base_effects[0]}")
                print(f"[TestcaseGenerator] 第一条数据的keys: {list(base_effects[0].keys())}")
            
            for effect in base_effects:
                # 调试日志：检查 tags 和 fillGuide 是否存在
                print(f"[TestcaseGenerator] 保存 effect: index={effect.get('index')}, tags={effect.get('tags')}, fillGuide={effect.get('fillGuide')}")
                
                # 根据 save_score 决定是否保存分数字段
                max_score_val = effect.get('maxScore') if save_score else None
                score_val = effect.get('score') if save_score else None
                
                extra_data = {
                    'questionType': effect.get('questionType', 'objective'),
                    'bvalue': effect.get('bvalue', '4')
                }
                # 仅在保存评分时添加分数到 extra_data
                if save_score:
                    extra_data['maxScore'] = effect.get('maxScore')
                    extra_data['score'] = effect.get('score')
                
                tags = effect.get('tags', [])
                tags_json = json.dumps(tags, ensure_ascii=False) if tags else None
                print(f"[TestcaseGenerator] tags_json={tags_json}")
                
                sql = """
                    INSERT INTO baseline_effects 
                    (dataset_id, page_num, question_index, temp_index, question_type, 
                     answer, user_answer, is_correct, tags, max_score, score, fill_guide, extra_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                AppDatabaseService.execute_insert(sql, (
                    dataset_id,
                    page_num,
                    effect.get('index', ''),
                    effect.get('tempIndex', 0),
                    effect.get('questionType', 'objective'),
                    effect.get('answer', ''),
                    effect.get('userAnswer', ''),
                    effect.get('correct', 'no'),
                    tags_json,
                    max_score_val,
                    score_val,
                    effect.get('fillGuide', ''),
                    json.dumps(extra_data, ensure_ascii=False)
                ))
            
            return {
                'success': True,
                'data': {
                    'dataset_id': dataset_id,
                    'name': dataset_name,
                    'question_count': len(base_effects)
                }
            }
            
        except Exception as e:
            print(f"[TestcaseGenerator] 保存数据集失败: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
