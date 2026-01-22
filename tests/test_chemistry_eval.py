"""
化学评估模块测试
"""
import pytest
from services.chemistry_eval import (
    normalize_chemistry_markdown,
    normalize_chemistry_answer,
    _process_reaction_condition
)


class TestNormalizeChemistryMarkdown:
    """测试化学公式标准化"""
    
    def test_basic_formula(self):
        """测试基本化学式"""
        assert 'H₂O' in normalize_chemistry_markdown('H_2O')
        assert 'H₂O' in normalize_chemistry_markdown('$H_2O$')
        assert 'CO₂' in normalize_chemistry_markdown('CO_2')
        assert 'H₂SO₄' in normalize_chemistry_markdown('H_2SO_4')
        assert 'MgCl₂' in normalize_chemistry_markdown('MgCl_2')
    
    def test_equation_with_arrow(self):
        """测试带箭头的方程式"""
        result = normalize_chemistry_markdown(r'$Mg + 2HCl = MgCl_2 + H_2 \uparrow$')
        assert 'MgCl₂' in result
        assert 'H₂' in result
        assert '↑' in result
        assert '=' in result
    
    def test_precipitation_symbol(self):
        """测试沉淀符号"""
        result = normalize_chemistry_markdown(r'CaCO_3 \downarrow')
        assert 'CaCO₃' in result
        assert '↓' in result
    
    def test_reversible_reaction(self):
        """测试可逆反应符号"""
        result = normalize_chemistry_markdown(r'N_2 + 3H_2 \rightleftharpoons 2NH_3')
        assert 'N₂' in result
        assert 'H₂' in result
        assert '⇌' in result
        assert 'NH₃' in result
    
    def test_html_tags_removal(self):
        """测试HTML标签移除"""
        text = 'H_2O<br>CO_2<br/>NaCl'
        result = normalize_chemistry_markdown(text)
        assert '<br>' not in result
        assert '<br/>' not in result
        assert 'H₂O' in result
        assert 'CO₂' in result
    
    def test_reaction_condition_xrightarrow(self):
        """测试反应条件箭头"""
        # 带条件的箭头
        result = normalize_chemistry_markdown(r'2H_2O \xrightarrow{通电} 2H_2 + O_2')
        assert 'H₂O' in result
        assert '通电' in result
        assert 'H₂' in result
        assert 'O₂' in result
    
    def test_reaction_condition_catalyst(self):
        """测试催化剂条件"""
        result = normalize_chemistry_markdown(r'2H_2O_2 \xrightarrow{MnO_2} 2H_2O + O_2')
        assert 'H₂O₂' in result
        assert 'MnO₂' in result
        assert 'H₂O' in result
        assert 'O₂' in result
    
    def test_heating_condition(self):
        """测试加热条件"""
        result = normalize_chemistry_markdown(r'CaCO_3 \xrightarrow{高温} CaO + CO_2')
        assert 'CaCO₃' in result
        assert '高温' in result
        assert 'CaO' in result
        assert 'CO₂' in result
    
    def test_delta_symbol(self):
        """测试加热符号Δ"""
        result = normalize_chemistry_markdown(r'2KClO_3 \xrightarrow{\Delta} 2KCl + 3O_2')
        assert 'KClO₃' in result
        assert 'Δ' in result or '加热' in result
    
    def test_complex_equation(self):
        """测试复杂方程式（用户提供的示例）"""
        base_answer = r'$Mg + 2HCl = MgCl_2 + H_2 \uparrow$'
        result = normalize_chemistry_markdown(base_answer)
        
        # 验证关键部分
        assert 'Mg' in result
        assert '2HCl' in result
        assert 'MgCl₂' in result
        assert 'H₂' in result
        assert '↑' in result
    
    def test_multiple_equations_with_br(self):
        """测试多个方程式（带<br>分隔）"""
        text = r'''$Mg + 2HCl = MgCl_2 + H_2 \uparrow$
<br>$Zn + 2HCl = ZnCl_2 + H_2 \uparrow$'''
        result = normalize_chemistry_markdown(text)
        
        assert 'MgCl₂' in result
        assert 'ZnCl₂' in result
        assert '↑' in result
    
    def test_empty_input(self):
        """测试空输入"""
        assert normalize_chemistry_markdown('') == ''
        assert normalize_chemistry_markdown(None) == ''
    
    def test_plain_text(self):
        """测试纯文本（无LaTeX）"""
        result = normalize_chemistry_markdown('大量 较多 少量 浅绿')
        assert '大量' in result
        assert '较多' in result
        assert '少量' in result
        assert '浅绿' in result
    
    def test_ce_command(self):
        """测试mhchem的\\ce命令"""
        result = normalize_chemistry_markdown(r'\ce{H2O}')
        assert 'H' in result
        assert 'O' in result
    
    def test_superscript_charge(self):
        """测试离子电荷上标"""
        result = normalize_chemistry_markdown(r'Fe^{2+}')
        assert 'Fe' in result
        assert '²⁺' in result or '2+' in result
    
    def test_sulfuric_acid_equation(self):
        """测试硫酸方程式"""
        result = normalize_chemistry_markdown(r'$Mg + H_2SO_4 = MgSO_4 + H_2 \uparrow$')
        assert 'H₂SO₄' in result
        assert 'MgSO₄' in result
        assert 'H₂' in result
        assert '↑' in result


class TestProcessReactionCondition:
    """测试反应条件处理"""
    
    def test_chinese_conditions(self):
        """测试中文条件"""
        assert '高温' in _process_reaction_condition('高温')
        assert '催化剂' in _process_reaction_condition('催化剂')
        assert '点燃' in _process_reaction_condition('点燃')
    
    def test_catalyst_formula(self):
        """测试催化剂化学式"""
        result = _process_reaction_condition('MnO_2')
        assert 'MnO₂' in result
    
    def test_empty_condition(self):
        """测试空条件"""
        assert _process_reaction_condition('') == ''
        assert _process_reaction_condition(None) == ''


class TestNormalizeChemistryAnswer:
    """测试化学答案标准化（用于比较）"""
    
    def test_answer_comparison_ready(self):
        """测试答案比较准备"""
        base = r'$Mg + 2HCl = MgCl_2 + H_2 \uparrow$'
        ai = 'Mg+2HCl=MgCl₂+H₂↑'
        
        base_normalized = normalize_chemistry_answer(base)
        ai_normalized = normalize_chemistry_answer(ai)
        
        # 标准化后应该更接近（normalize_answer会转小写）
        assert 'mgcl' in base_normalized
        assert 'mgcl' in ai_normalized


class TestRealWorldExamples:
    """测试真实世界示例"""
    
    def test_user_provided_example(self):
        """测试用户提供的示例数据"""
        base_answer = """大量 大量    $Mg + 2HCl = MgCl_2 + H_2 \\uparrow$         $Mg + H_2SO_4 = MgSO_4 + H_2 \\uparrow$ 
<br>较多  较多   $Zn + 2HCl = ZnCl_2 + H_2 \\uparrow$               $Zn + H_2SO_4 = ZnSO_4 + H_2 \\uparrow$
<br> 少量 浅绿 少量    $Fe + 2HCl = FeCl_2 + H_2 \\uparrow$      $Fe + H_2SO_4 = FeSO_4 + H_2 \\uparrow$
 <br>强"""
        
        result = normalize_chemistry_markdown(base_answer)
        
        # 验证文字部分
        assert '大量' in result
        assert '较多' in result
        assert '少量' in result
        assert '浅绿' in result
        assert '强' in result
        
        # 验证化学式
        assert 'MgCl₂' in result
        assert 'MgSO₄' in result
        assert 'ZnCl₂' in result
        assert 'ZnSO₄' in result
        assert 'FeCl₂' in result
        assert 'FeSO₄' in result
        
        # 验证箭头
        assert '↑' in result
        
        # 验证HTML标签已移除
        assert '<br>' not in result
    
    def test_simple_fill_answer(self):
        """测试简单填空答案"""
        base_answer = "另一种单质 另一种化合物\n"
        result = normalize_chemistry_markdown(base_answer)
        
        assert '另一种单质' in result
        assert '另一种化合物' in result
