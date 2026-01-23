"""
测试 parse_page_region 函数
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.test_plans import parse_page_region


def test_single_pages():
    """测试单个页码"""
    assert parse_page_region('97') == [97]
    assert parse_page_region('1') == [1]
    assert parse_page_region('100') == [100]


def test_comma_separated():
    """测试逗号分隔的页码"""
    assert parse_page_region('97,98') == [97, 98]
    assert parse_page_region('97, 98, 99') == [97, 98, 99]
    assert parse_page_region('1,3,5') == [1, 3, 5]


def test_range_format():
    """测试范围格式"""
    assert parse_page_region('97-100') == [97, 98, 99, 100]
    assert parse_page_region('1-5') == [1, 2, 3, 4, 5]


def test_mixed_format():
    """测试混合格式"""
    assert parse_page_region('97-99,101') == [97, 98, 99, 101]
    assert parse_page_region('1,3-5,7') == [1, 3, 4, 5, 7]


def test_chinese_wave():
    """测试中文波浪号"""
    assert parse_page_region('97～99') == [97, 98, 99]
    assert parse_page_region('97～99,101') == [97, 98, 99, 101]


def test_english_tilde():
    """测试英文波浪号"""
    assert parse_page_region('97~99') == [97, 98, 99]


def test_reversed_range():
    """测试反向范围（自动纠正）"""
    assert parse_page_region('100-97') == [97, 98, 99, 100]


def test_empty_input():
    """测试空输入"""
    assert parse_page_region('') == []
    assert parse_page_region(None) == []


def test_deduplication():
    """测试去重"""
    assert parse_page_region('97,97,98') == [97, 98]
    assert parse_page_region('97-99,98') == [97, 98, 99]


def test_sorting():
    """测试排序"""
    assert parse_page_region('99,97,98') == [97, 98, 99]
    assert parse_page_region('101,97-99') == [97, 98, 99, 101]


if __name__ == '__main__':
    # 运行所有测试
    test_single_pages()
    print('PASS: test_single_pages')
    
    test_comma_separated()
    print('PASS: test_comma_separated')
    
    test_range_format()
    print('PASS: test_range_format')
    
    test_mixed_format()
    print('PASS: test_mixed_format')
    
    test_chinese_wave()
    print('PASS: test_chinese_wave')
    
    test_english_tilde()
    print('PASS: test_english_tilde')
    
    test_reversed_range()
    print('PASS: test_reversed_range')
    
    test_empty_input()
    print('PASS: test_empty_input')
    
    test_deduplication()
    print('PASS: test_deduplication')
    
    test_sorting()
    print('PASS: test_sorting')
    
    print('\nAll tests passed!')
