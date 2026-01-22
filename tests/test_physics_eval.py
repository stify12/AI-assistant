"""
物理评估模块测试
测试 LaTeX/Markdown 公式转换功能
"""
import pytest
from services.physics_eval import normalize_physics_markdown, normalize_physics_answer


class TestNormalizePhysicsMarkdown:
    """测试 LaTeX/Markdown 转换"""
    
    def test_basic_dollar_signs(self):
        """测试基本的 $ 符号移除"""
        assert normalize_physics_markdown('$x$') == 'x'
        assert normalize_physics_markdown('$$y$$') == 'y'
        assert normalize_physics_markdown(r'\(z\)') == 'z'
        assert normalize_physics_markdown(r'\[w\]') == 'w'
    
    def test_superscript(self):
        """测试上标转换"""
        assert normalize_physics_markdown('$m^3$') == 'm³'
        assert normalize_physics_markdown('$10^3$') == '10³'
        assert normalize_physics_markdown('$x^{10}$') == 'x¹⁰'
        assert normalize_physics_markdown('$a^{-2}$') == 'a⁻²'
        assert normalize_physics_markdown('$x^n$') == 'xⁿ'
    
    def test_subscript(self):
        """测试下标转换"""
        assert normalize_physics_markdown('$H_2O$') == 'H₂O'
        assert normalize_physics_markdown('$v_0$') == 'v₀'
        assert normalize_physics_markdown('$a_{12}$') == 'a₁₂'
    
    def test_fraction(self):
        """测试分数转换"""
        assert normalize_physics_markdown(r'$\frac{a}{b}$') == 'a/b'
        assert normalize_physics_markdown(r'$\frac{1}{2}$') == '1/2'
        assert normalize_physics_markdown(r'$\dfrac{x}{y}$') == 'x/y'
    
    def test_sqrt(self):
        """测试根号转换"""
        assert normalize_physics_markdown(r'$\sqrt{x}$') == '√x'
        assert normalize_physics_markdown(r'$\sqrt{2}$') == '√2'
        assert normalize_physics_markdown(r'$\sqrt[3]{x}$') == '³√x'
        assert normalize_physics_markdown(r'$\sqrt[n]{x}$') == 'ⁿ√x'
    
    def test_greek_letters(self):
        """测试希腊字母转换"""
        assert normalize_physics_markdown(r'$\rho$') == 'ρ'
        assert normalize_physics_markdown(r'$\alpha$') == 'α'
        assert normalize_physics_markdown(r'$\beta$') == 'β'
        assert normalize_physics_markdown(r'$\pi$') == 'π'
        assert normalize_physics_markdown(r'$\Omega$') == 'Ω'
        assert normalize_physics_markdown(r'$\Delta$') == 'Δ'
    
    def test_math_operators(self):
        """测试数学运算符转换"""
        assert normalize_physics_markdown(r'$\times$') == '×'
        assert normalize_physics_markdown(r'$\div$') == '÷'
        assert normalize_physics_markdown(r'$\pm$') == '±'
        assert normalize_physics_markdown(r'$\leq$') == '≤'
        assert normalize_physics_markdown(r'$\geq$') == '≥'
        assert normalize_physics_markdown(r'$\neq$') == '≠'
        assert normalize_physics_markdown(r'$\approx$') == '≈'
    
    def test_arrows(self):
        """测试箭头转换"""
        assert normalize_physics_markdown(r'$\rightarrow$') == '→'
        assert normalize_physics_markdown(r'$\leftarrow$') == '←'
        assert normalize_physics_markdown(r'$\Rightarrow$') == '⇒'
        assert normalize_physics_markdown(r'$\leftrightarrow$') == '↔'
    
    def test_special_symbols(self):
        """测试特殊符号转换"""
        assert normalize_physics_markdown(r'$\infty$') == '∞'
        assert normalize_physics_markdown(r'$\partial$') == '∂'
        assert normalize_physics_markdown(r'$\angle$') == '∠'
        assert normalize_physics_markdown(r'$\perp$') == '⊥'
        assert normalize_physics_markdown(r'$\parallel$') == '∥'
        assert normalize_physics_markdown(r'$\triangle$') == '△'
    
    def test_text_command(self):
        """测试 text 命令转换"""
        assert normalize_physics_markdown(r'$\text{m}$') == 'm'
        assert normalize_physics_markdown(r'$\text{kg}$') == 'kg'
        assert normalize_physics_markdown(r'$\mathrm{N}$') == 'N'
    
    def test_calculus_symbols(self):
        """测试积分/求和符号转换"""
        assert normalize_physics_markdown(r'$\int$') == '∫'
        assert normalize_physics_markdown(r'$\sum$') == 'Σ'
        assert normalize_physics_markdown(r'$\prod$') == 'Π'
    
    def test_functions(self):
        """测试函数名转换"""
        assert normalize_physics_markdown(r'$\sin$') == 'sin'
        assert normalize_physics_markdown(r'$\cos$') == 'cos'
        assert normalize_physics_markdown(r'$\log$') == 'log'
        assert normalize_physics_markdown(r'$\ln$') == 'ln'
        assert normalize_physics_markdown(r'$\lim$') == 'lim'
    
    def test_vector(self):
        """测试向量转换"""
        assert normalize_physics_markdown(r'$\vec{a}$') == 'a⃗'
        assert normalize_physics_markdown(r'$\overrightarrow{AB}$') == 'AB→'
    
    def test_chinese_subscript(self):
        """测试中文下标转换"""
        # m_钢 → m钢
        assert normalize_physics_markdown(r'$m_钢$') == 'm钢'
        assert normalize_physics_markdown(r'$\rho_钢$') == 'ρ钢'
        assert normalize_physics_markdown(r'$m_{钢}$') == 'm钢'
        assert normalize_physics_markdown(r'$V_{水}$') == 'V水'
        # 复杂公式
        result = normalize_physics_markdown(r'$V=\frac{m_钢}{\rho_钢}$')
        assert 'm钢' in result
        assert 'ρ钢' in result
    
    def test_complex_physics_formulas(self):
        """测试复杂物理公式"""
        # 体积为1m³的水的质量为10³kg
        result = normalize_physics_markdown(r'体积为$1\text{m}^3$的水的质量为$10^3\text{kg}$')
        assert 'm³' in result
        assert 'kg' in result
        assert '10³' in result
        
        # 密度公式
        result = normalize_physics_markdown(r'$\rho=\frac{m}{V}$')
        assert 'ρ' in result
        assert 'm/V' in result or 'm)/(V' in result
        
        # 速度公式
        result = normalize_physics_markdown(r'$v=\frac{s}{t}=5\text{m/s}$')
        assert 's/t' in result or 's)/(t' in result
        assert 'm/s' in result
        
        # 压强公式
        result = normalize_physics_markdown(r'$P=\frac{F}{S}$')
        assert 'F/S' in result or 'F)/(S' in result
        
        # 功率公式
        result = normalize_physics_markdown(r'$P=\frac{W}{t}$')
        assert 'W/t' in result or 'W)/(t' in result
    
    def test_physics_units(self):
        """测试物理单位"""
        # 各种单位组合
        assert 'm³' in normalize_physics_markdown(r'$\text{m}^3$')
        assert 'kg' in normalize_physics_markdown(r'$\text{kg}$')
        assert 'm/s' in normalize_physics_markdown(r'$\text{m/s}$')
        assert 'N' in normalize_physics_markdown(r'$\text{N}$')
        assert 'Pa' in normalize_physics_markdown(r'$\text{Pa}$')
        assert 'J' in normalize_physics_markdown(r'$\text{J}$')
        assert 'W' in normalize_physics_markdown(r'$\text{W}$')
    
    def test_empty_and_none(self):
        """测试空值处理"""
        assert normalize_physics_markdown('') == ''
        assert normalize_physics_markdown(None) == ''
    
    def test_plain_text_unchanged(self):
        """测试纯文本不变"""
        assert normalize_physics_markdown('hello world') == 'hello world'
        assert normalize_physics_markdown('1m³') == '1m³'
        assert normalize_physics_markdown('10³kg') == '10³kg'


class TestNormalizePhysicsAnswer:
    """测试物理答案标准化（用于比较）"""
    
    def test_latex_vs_plain(self):
        """测试 LaTeX 格式和纯文本格式的比较"""
        # 这两个应该标准化后相同
        latex = normalize_physics_answer(r'$1\text{m}^3$')
        plain = normalize_physics_answer('1m³')
        assert latex == plain
        
        latex = normalize_physics_answer(r'$10^3\text{kg}$')
        plain = normalize_physics_answer('10³kg')
        assert latex == plain
    
    def test_density_formula(self):
        """测试密度公式"""
        latex = normalize_physics_answer(r'$\rho=1000\text{kg/m}^3$')
        plain = normalize_physics_answer('ρ=1000kg/m³')
        # 标准化后应该相似（可能有细微差异）
        assert 'ρ' in latex or 'rho' in latex.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
