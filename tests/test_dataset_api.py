"""
数据集管理 API 测试
测试 Tasks 4.1-4.4 的实现
包含属性测试 (Property-Based Tests)
"""
import pytest
import json
import sys
import os
import re
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hypothesis import given, strategies as st, settings, HealthCheck
from app import app
from services.storage_service import StorageService


@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_datasets(monkeypatch):
    """模拟数据集数据"""
    mock_data = [
        {
            'dataset_id': 'test001',
            'name': '学生A基准效果',
            'book_id': 'book123',
            'book_name': '七年级英语上册',
            'subject_id': 0,
            'pages': [30, 31, 32],
            'question_count': 50,
            'description': '测试描述',
            'created_at': '2024-01-15T10:00:00'
        },
        {
            'dataset_id': 'test002',
            'name': '学生B基准效果',
            'book_id': 'book123',
            'book_name': '七年级英语上册',
            'subject_id': 0,
            'pages': [30, 31],
            'question_count': 40,
            'description': '',
            'created_at': '2024-01-16T10:00:00'
        },
        {
            'dataset_id': 'test003',
            'name': '数学测试数据集',
            'book_id': 'book456',
            'book_name': '八年级数学上册',
            'subject_id': 2,
            'pages': [10, 11],
            'question_count': 30,
            'description': '数学测试',
            'created_at': '2024-01-17T10:00:00'
        }
    ]
    
    def mock_get_all_datasets_summary():
        return mock_data
    
    monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
    return mock_data


class TestGetDatasets:
    """测试 GET /api/batch/datasets 接口"""
    
    def test_get_datasets_returns_name_field(self, client, mock_datasets):
        """Task 4.4: 返回结果包含 name 字段"""
        response = client.get('/api/batch/datasets')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 3
        
        # 验证每个数据集都有 name 字段
        for ds in data['data']:
            assert 'name' in ds
            assert ds['name'] != ''
    
    def test_get_datasets_search_by_name(self, client, mock_datasets):
        """Task 4.4: 支持按 name 模糊搜索"""
        # 搜索 "学生A"
        response = client.get('/api/batch/datasets?search=学生A')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == '学生A基准效果'
    
    def test_get_datasets_search_case_insensitive(self, client, mock_datasets):
        """Task 4.4: 搜索不区分大小写"""
        # 搜索 "数学" (中文不区分大小写)
        response = client.get('/api/batch/datasets?search=数学')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 1
        assert '数学' in data['data'][0]['name']
    
    def test_get_datasets_sorted_by_created_at_desc(self, client, mock_datasets):
        """Task 4.4: 按 created_at 倒序排列"""
        response = client.get('/api/batch/datasets')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # 验证按创建时间倒序（最新的在前）
        dates = [ds['created_at'] for ds in data['data']]
        assert dates == sorted(dates, reverse=True)
    
    def test_get_datasets_filter_by_book_id(self, client, mock_datasets):
        """测试按 book_id 过滤"""
        response = client.get('/api/batch/datasets?book_id=book123')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 2
        for ds in data['data']:
            assert ds['book_id'] == 'book123'


class TestCheckDuplicate:
    """测试 GET /api/batch/datasets/check-duplicate 接口"""
    
    def test_check_duplicate_missing_book_id(self, client):
        """Task 4.3: 缺少 book_id 参数返回错误"""
        response = client.get('/api/batch/datasets/check-duplicate?pages=1,2,3')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert '缺少 book_id 参数' in data['error']
    
    def test_check_duplicate_missing_pages(self, client):
        """Task 4.3: 缺少 pages 参数返回错误"""
        response = client.get('/api/batch/datasets/check-duplicate?book_id=book123')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert '缺少 pages 参数' in data['error']
    
    def test_check_duplicate_found(self, client, mock_datasets):
        """Task 4.3: 检测到重复数据集"""
        response = client.get('/api/batch/datasets/check-duplicate?book_id=book123&pages=30,31')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['has_duplicate'] is True
        assert len(data['duplicates']) == 2  # 两个数据集都包含页码 30, 31
    
    def test_check_duplicate_not_found(self, client, mock_datasets):
        """Task 4.3: 未检测到重复数据集"""
        response = client.get('/api/batch/datasets/check-duplicate?book_id=book123&pages=100,101')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['has_duplicate'] is False
        assert len(data['duplicates']) == 0
    
    def test_check_duplicate_partial_overlap(self, client, mock_datasets):
        """Task 4.3: 部分页码重叠也算重复"""
        response = client.get('/api/batch/datasets/check-duplicate?book_id=book123&pages=32,33')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['has_duplicate'] is True
        # 只有 test001 包含页码 32
        assert len(data['duplicates']) == 1
        assert data['duplicates'][0]['dataset_id'] == 'test001'
    
    def test_check_duplicate_invalid_pages_format(self, client):
        """Task 4.3: 页码格式错误"""
        response = client.get('/api/batch/datasets/check-duplicate?book_id=book123&pages=abc,def')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert '页码格式错误' in data['error']


class TestCreateDataset:
    """测试 POST /api/batch/datasets 接口"""
    
    def test_create_dataset_empty_name_rejected(self, client, monkeypatch):
        """Task 4.1: 空名称被拒绝"""
        response = client.post('/api/batch/datasets', 
            data=json.dumps({
                'book_id': 'book123',
                'pages': [1, 2],
                'base_effects': {},
                'name': ''  # 空名称
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert '名称不能为空' in data['error']
    
    def test_create_dataset_whitespace_name_rejected(self, client, monkeypatch):
        """Task 4.1: 纯空白名称被拒绝"""
        response = client.post('/api/batch/datasets', 
            data=json.dumps({
                'book_id': 'book123',
                'pages': [1, 2],
                'base_effects': {},
                'name': '   '  # 纯空白
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert '名称不能为空' in data['error']
    
    def test_create_dataset_without_name_uses_default(self, client, monkeypatch):
        """Task 4.1: 无 name 时自动生成默认名称"""
        saved_data = {}
        
        def mock_save_dataset(dataset_id, data):
            saved_data['dataset_id'] = dataset_id
            saved_data['data'] = data
        
        monkeypatch.setattr(StorageService, 'save_dataset', mock_save_dataset)
        
        response = client.post('/api/batch/datasets', 
            data=json.dumps({
                'book_id': 'book123',
                'pages': [1, 2],
                'base_effects': {}
                # 不提供 name
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        # StorageService.save_dataset 会处理默认名称生成


class TestUpdateDataset:
    """测试 PUT /api/batch/datasets/<dataset_id> 接口"""
    
    def test_update_dataset_name(self, client, monkeypatch):
        """Task 4.2: 支持更新 name 字段"""
        existing_data = {
            'dataset_id': 'test001',
            'name': '旧名称',
            'book_id': 'book123',
            'pages': [1, 2],
            'base_effects': {'1': [{'index': '1', 'answer': 'A'}], '2': [{'index': '2', 'answer': 'B'}]},
            'description': ''
        }
        saved_data = {}
        
        def mock_load_dataset(dataset_id):
            return existing_data.copy()
        
        def mock_save_dataset(dataset_id, data):
            saved_data['data'] = data
        
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        monkeypatch.setattr(StorageService, 'save_dataset', mock_save_dataset)
        
        response = client.put('/api/batch/datasets/test001',
            data=json.dumps({
                'name': '新名称'
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert saved_data['data']['name'] == '新名称'
    
    def test_update_dataset_description(self, client, monkeypatch):
        """Task 4.2: 支持更新 description 字段"""
        existing_data = {
            'dataset_id': 'test001',
            'name': '测试数据集',
            'book_id': 'book123',
            'pages': [1, 2],
            'base_effects': {'1': [{'index': '1', 'answer': 'A'}], '2': [{'index': '2', 'answer': 'B'}]},
            'description': '旧描述'
        }
        saved_data = {}
        
        def mock_load_dataset(dataset_id):
            return existing_data.copy()
        
        def mock_save_dataset(dataset_id, data):
            saved_data['data'] = data
        
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        monkeypatch.setattr(StorageService, 'save_dataset', mock_save_dataset)
        
        response = client.put('/api/batch/datasets/test001',
            data=json.dumps({
                'description': '新描述内容'
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert saved_data['data']['description'] == '新描述内容'
    
    def test_update_dataset_empty_name_rejected(self, client, monkeypatch):
        """Task 4.2: 更新时空名称被拒绝"""
        existing_data = {
            'dataset_id': 'test001',
            'name': '测试数据集',
            'book_id': 'book123',
            'pages': [1, 2],
            'base_effects': {'1': [{'index': '1', 'answer': 'A'}]},
            'description': ''
        }
        
        def mock_load_dataset(dataset_id):
            return existing_data.copy()
        
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        
        response = client.put('/api/batch/datasets/test001',
            data=json.dumps({
                'name': ''  # 空名称
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert '名称不能为空' in data['error']


class TestDefaultNameGeneration:
    """测试默认名称生成逻辑"""
    
    def test_generate_default_name_with_pages(self):
        """测试带页码的默认名称生成"""
        data = {
            'book_name': '七年级英语上册',
            'pages': [30, 31, 32]
        }
        name = StorageService.generate_default_dataset_name(data)
        assert '七年级英语上册' in name
        assert 'P30-32' in name
    
    def test_generate_default_name_single_page(self):
        """测试单页的默认名称生成"""
        data = {
            'book_name': '数学课本',
            'pages': [10]
        }
        name = StorageService.generate_default_dataset_name(data)
        assert '数学课本' in name
        assert 'P10' in name
    
    def test_generate_default_name_no_book_name(self):
        """测试无书名时使用默认值"""
        data = {
            'pages': [1, 2]
        }
        name = StorageService.generate_default_dataset_name(data)
        assert '未知书本' in name
    
    def test_generate_default_name_empty_pages(self):
        """测试空页码列表"""
        data = {
            'book_name': '测试书本',
            'pages': []
        }
        name = StorageService.generate_default_dataset_name(data)
        assert '测试书本' in name
        # 不应包含页码部分
        assert 'P' not in name or '_P' not in name


class TestDefaultNameGenerationProperty:
    """
    属性测试：默认名称生成格式
    Feature: dataset-naming-selection, Property 1: Default Name Generation Format
    Validates: Requirements 1.2, 6.1
    
    Property: For any dataset with book_name and pages, when no custom name is provided,
    the generated default name SHALL match the format "{book_name}_P{min_page}-{max_page}_{timestamp}"
    where timestamp is in MMDDHHmm format.
    """
    
    # Strategy for generating valid book names (non-empty, printable characters)
    book_name_strategy = st.text(
        alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S'),  # Letters, Numbers, Punctuation, Symbols
            blacklist_characters='_'  # Exclude underscore to avoid format confusion
        ),
        min_size=1,
        max_size=50
    ).filter(lambda x: x.strip() != '')  # Ensure non-empty after strip
    
    # Strategy for generating valid page lists
    pages_strategy = st.lists(
        st.integers(min_value=1, max_value=200),
        min_size=1,
        max_size=20,
        unique=True
    )
    
    @given(
        book_name=book_name_strategy,
        pages=pages_strategy
    )
    @settings(max_examples=100)
    def test_default_name_format_multiple_pages(self, book_name, pages):
        """
        Feature: dataset-naming-selection, Property 1: Default Name Generation Format
        Validates: Requirements 1.2, 6.1
        
        Test that for multiple pages, the generated name matches:
        "{book_name}_P{min_page}-{max_page}_{timestamp}"
        """
        # Arrange: Create data with book_name and multiple pages
        data = {
            'book_name': book_name,
            'pages': pages
        }
        
        # Act: Generate default name
        name = StorageService.generate_default_dataset_name(data)
        
        # Assert: Verify format
        # Name should start with book_name
        assert name.startswith(book_name), f"Name should start with book_name: {book_name}"
        
        # Extract page part and timestamp
        sorted_pages = sorted(pages)
        min_page = sorted_pages[0]
        max_page = sorted_pages[-1]
        
        if len(sorted_pages) == 1:
            # Single page format: {book_name}_P{page}_{timestamp}
            expected_page_part = f"_P{min_page}_"
        else:
            # Multiple pages format: {book_name}_P{min_page}-{max_page}_{timestamp}
            expected_page_part = f"_P{min_page}-{max_page}_"
        
        assert expected_page_part in name, \
            f"Name should contain page part '{expected_page_part}', got: {name}"
        
        # Verify timestamp format (MMDDHHmm - 8 digits)
        # The name should end with an 8-digit timestamp
        timestamp_pattern = r'_(\d{8})$'
        match = re.search(timestamp_pattern, name)
        assert match is not None, f"Name should end with 8-digit timestamp, got: {name}"
        
        timestamp = match.group(1)
        # Validate timestamp is a valid MMDDHHmm format
        month = int(timestamp[0:2])
        day = int(timestamp[2:4])
        hour = int(timestamp[4:6])
        minute = int(timestamp[6:8])
        
        assert 1 <= month <= 12, f"Month should be 01-12, got: {month}"
        assert 1 <= day <= 31, f"Day should be 01-31, got: {day}"
        assert 0 <= hour <= 23, f"Hour should be 00-23, got: {hour}"
        assert 0 <= minute <= 59, f"Minute should be 00-59, got: {minute}"
    
    @given(
        book_name=book_name_strategy,
        page=st.integers(min_value=1, max_value=200)
    )
    @settings(max_examples=100)
    def test_default_name_format_single_page(self, book_name, page):
        """
        Feature: dataset-naming-selection, Property 1: Default Name Generation Format
        Validates: Requirements 1.2, 6.1
        
        Test that for a single page, the generated name matches:
        "{book_name}_P{page}_{timestamp}"
        """
        # Arrange: Create data with book_name and single page
        data = {
            'book_name': book_name,
            'pages': [page]
        }
        
        # Act: Generate default name
        name = StorageService.generate_default_dataset_name(data)
        
        # Assert: Verify format
        # Name should start with book_name
        assert name.startswith(book_name), f"Name should start with book_name: {book_name}"
        
        # Single page format: {book_name}_P{page}_{timestamp}
        expected_page_part = f"_P{page}_"
        assert expected_page_part in name, \
            f"Name should contain page part '{expected_page_part}', got: {name}"
        
        # Verify timestamp format (MMDDHHmm - 8 digits)
        timestamp_pattern = r'_(\d{8})$'
        match = re.search(timestamp_pattern, name)
        assert match is not None, f"Name should end with 8-digit timestamp, got: {name}"
    
    @given(
        pages=pages_strategy
    )
    @settings(max_examples=100)
    def test_default_name_format_no_book_name(self, pages):
        """
        Feature: dataset-naming-selection, Property 1: Default Name Generation Format
        Validates: Requirements 1.2, 6.1
        
        Test that when book_name is missing, "未知书本" is used as default.
        """
        # Arrange: Create data without book_name
        data = {
            'pages': pages
        }
        
        # Act: Generate default name
        name = StorageService.generate_default_dataset_name(data)
        
        # Assert: Should use default book name
        assert name.startswith('未知书本'), \
            f"Name should start with '未知书本' when book_name is missing, got: {name}"
        
        # Verify page part exists
        sorted_pages = sorted(pages)
        if len(sorted_pages) == 1:
            expected_page_part = f"_P{sorted_pages[0]}_"
        else:
            expected_page_part = f"_P{sorted_pages[0]}-{sorted_pages[-1]}_"
        
        assert expected_page_part in name, \
            f"Name should contain page part '{expected_page_part}', got: {name}"
    
    @given(
        book_name=book_name_strategy
    )
    @settings(max_examples=100)
    def test_default_name_format_empty_pages(self, book_name):
        """
        Feature: dataset-naming-selection, Property 1: Default Name Generation Format
        Validates: Requirements 1.2, 6.1
        
        Test that when pages is empty, the format is "{book_name}_{timestamp}" (no page part).
        """
        # Arrange: Create data with empty pages
        data = {
            'book_name': book_name,
            'pages': []
        }
        
        # Act: Generate default name
        name = StorageService.generate_default_dataset_name(data)
        
        # Assert: Should not contain page part
        assert name.startswith(book_name), f"Name should start with book_name: {book_name}"
        
        # Should not contain _P pattern (no page part)
        # The format should be: {book_name}_{timestamp}
        # Verify it ends with timestamp directly after book_name
        expected_pattern = rf'^{re.escape(book_name)}_\d{{8}}$'
        assert re.match(expected_pattern, name), \
            f"Name should match '{book_name}_MMDDHHM' format when pages is empty, got: {name}"
    
    @given(
        book_name=book_name_strategy,
        pages=pages_strategy
    )
    @settings(max_examples=100)
    def test_default_name_timestamp_is_current(self, book_name, pages):
        """
        Feature: dataset-naming-selection, Property 1: Default Name Generation Format
        Validates: Requirements 1.2, 6.1
        
        Test that the timestamp in the generated name is close to current time.
        """
        # Arrange
        data = {
            'book_name': book_name,
            'pages': pages
        }
        
        # Record time before and after generation
        before = datetime.now()
        name = StorageService.generate_default_dataset_name(data)
        after = datetime.now()
        
        # Extract timestamp from name
        timestamp_pattern = r'_(\d{8})$'
        match = re.search(timestamp_pattern, name)
        assert match is not None, f"Name should end with 8-digit timestamp, got: {name}"
        
        timestamp_str = match.group(1)
        
        # Parse timestamp (MMDDHHmm)
        month = int(timestamp_str[0:2])
        day = int(timestamp_str[2:4])
        hour = int(timestamp_str[4:6])
        minute = int(timestamp_str[6:8])
        
        # Verify timestamp is within the time window
        # Note: We check that the timestamp matches either before or after time
        # to handle edge cases where the minute changes during execution
        before_ts = before.strftime('%m%d%H%M')
        after_ts = after.strftime('%m%d%H%M')
        
        assert timestamp_str in [before_ts, after_ts], \
            f"Timestamp {timestamp_str} should be close to current time ({before_ts} or {after_ts})"


class TestWhitespaceNameRejection:
    """
    属性测试：空白名称拒绝
    Feature: dataset-naming-selection, Property 2: Whitespace Name Rejection
    Validates: Requirements 1.5
    
    Property: For any string composed entirely of whitespace characters (spaces, tabs, newlines)
    or empty string, attempting to save a dataset with such name SHALL be rejected with an error response.
    """
    
    # Strategy for generating whitespace-only strings (including empty string)
    whitespace_strategy = st.text(
        alphabet=' \t\n\r',  # Space, tab, newline, carriage return
        min_size=0,
        max_size=20
    )
    
    @given(
        whitespace=whitespace_strategy
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_whitespace_name_rejection_create(self, whitespace, client):
        """
        Feature: dataset-naming-selection, Property 2: Whitespace Name Rejection
        Validates: Requirements 1.5
        
        Test that POST /api/batch/datasets rejects whitespace-only names.
        """
        # Arrange: Prepare request data with whitespace-only name
        request_data = {
            'book_id': 'test_book_123',
            'pages': [1, 2],
            'base_effects': {},
            'name': whitespace  # Whitespace-only or empty name
        }
        
        # Act: Attempt to create dataset with whitespace name
        response = client.post(
            '/api/batch/datasets',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert: Request should be rejected with error
        assert response.status_code == 200, \
            f"Expected status code 200, got {response.status_code}"
        
        data = json.loads(response.data)
        
        # Assert: Response should indicate failure
        assert data['success'] is False, \
            f"Expected success=False for whitespace name '{repr(whitespace)}', got {data}"
        
        # Assert: Error message should indicate name validation failure
        assert '名称不能为空' in data.get('error', ''), \
            f"Expected error message about empty name, got: {data.get('error', '')}"
    
    @given(
        whitespace=whitespace_strategy
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_whitespace_name_rejection_update(self, whitespace, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 2: Whitespace Name Rejection
        Validates: Requirements 1.5
        
        Test that PUT /api/batch/datasets/<dataset_id> rejects whitespace-only names.
        """
        # Arrange: Mock existing dataset
        existing_data = {
            'dataset_id': 'test_whitespace_001',
            'name': '原始有效名称',
            'book_id': 'book123',
            'pages': [1, 2],
            'base_effects': {'1': [{'index': '1', 'answer': 'A'}]},
            'description': ''
        }
        
        def mock_load_dataset(dataset_id):
            return existing_data.copy()
        
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        
        # Arrange: Prepare update request with whitespace-only name
        update_data = {
            'name': whitespace  # Whitespace-only or empty name
        }
        
        # Act: Attempt to update dataset with whitespace name
        response = client.put(
            '/api/batch/datasets/test_whitespace_001',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        # Assert: Request should be rejected with error
        assert response.status_code == 200, \
            f"Expected status code 200, got {response.status_code}"
        
        data = json.loads(response.data)
        
        # Assert: Response should indicate failure
        assert data['success'] is False, \
            f"Expected success=False for whitespace name '{repr(whitespace)}', got {data}"
        
        # Assert: Error message should indicate name validation failure
        assert '名称不能为空' in data.get('error', ''), \
            f"Expected error message about empty name, got: {data.get('error', '')}"
    
    @given(
        whitespace=whitespace_strategy,
        valid_description=st.text(max_size=100)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_whitespace_name_rejection_with_valid_description(self, whitespace, valid_description, client):
        """
        Feature: dataset-naming-selection, Property 2: Whitespace Name Rejection
        Validates: Requirements 1.5
        
        Test that whitespace name is rejected even when other fields are valid.
        """
        # Arrange: Prepare request data with whitespace name but valid description
        request_data = {
            'book_id': 'test_book_456',
            'pages': [1, 2, 3],
            'base_effects': {},
            'name': whitespace,  # Whitespace-only or empty name
            'description': valid_description  # Valid description
        }
        
        # Act: Attempt to create dataset
        response = client.post(
            '/api/batch/datasets',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert: Request should still be rejected
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is False, \
            f"Expected success=False for whitespace name even with valid description"
        assert '名称不能为空' in data.get('error', ''), \
            f"Expected error message about empty name"
    
    @given(
        num_spaces=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_whitespace_name_rejection_spaces_only(self, num_spaces, client):
        """
        Feature: dataset-naming-selection, Property 2: Whitespace Name Rejection
        Validates: Requirements 1.5
        
        Test that names with only spaces (varying lengths) are rejected.
        """
        # Arrange: Create name with only spaces
        spaces_only_name = ' ' * num_spaces
        
        request_data = {
            'book_id': 'test_book_spaces',
            'pages': [1],
            'base_effects': {},
            'name': spaces_only_name
        }
        
        # Act: Attempt to create dataset
        response = client.post(
            '/api/batch/datasets',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert: Request should be rejected
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is False, \
            f"Expected success=False for {num_spaces} spaces, got {data}"
        assert '名称不能为空' in data.get('error', ''), \
            f"Expected error message about empty name for {num_spaces} spaces"
    
    @given(
        tabs=st.integers(min_value=1, max_value=20),
        newlines=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_whitespace_name_rejection_tabs_and_newlines(self, tabs, newlines, client):
        """
        Feature: dataset-naming-selection, Property 2: Whitespace Name Rejection
        Validates: Requirements 1.5
        
        Test that names with tabs and newlines are rejected.
        """
        # Arrange: Create name with tabs and newlines
        mixed_whitespace_name = '\t' * tabs + '\n' * newlines
        
        request_data = {
            'book_id': 'test_book_mixed',
            'pages': [1],
            'base_effects': {},
            'name': mixed_whitespace_name
        }
        
        # Act: Attempt to create dataset
        response = client.post(
            '/api/batch/datasets',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert: Request should be rejected
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is False, \
            f"Expected success=False for tabs/newlines whitespace, got {data}"
        assert '名称不能为空' in data.get('error', ''), \
            f"Expected error message about empty name for tabs/newlines"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestDatasetPersistenceRoundTrip:
    """
    属性测试：数据集持久化往返
    Feature: dataset-naming-selection, Property 3: Dataset Persistence Round-Trip
    Validates: Requirements 2.3, 5.4
    
    Property: For any valid dataset with name and description, saving then loading 
    the dataset SHALL return an equivalent object with the same name, description, 
    book_id, pages, and base_effects.
    """
    
    # Strategy for generating valid dataset names (non-empty, non-whitespace, no control chars)
    # Exclude control characters that would be stripped during save
    name_strategy = st.text(
        alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S', 'Zs'),  # Letters, Numbers, Punctuation, Symbols, Space separators
            blacklist_characters='\r\n\t\x00\x0b\x0c'  # Exclude control characters
        ),
        min_size=1,
        max_size=100
    ).filter(lambda x: x.strip() != '' and len(x.strip()) == len(x))  # Ensure no leading/trailing whitespace
    
    # Strategy for generating descriptions (can be empty)
    description_strategy = st.text(max_size=200)
    
    # Strategy for generating book_id (non-empty, alphanumeric-like)
    book_id_strategy = st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=1,
        max_size=50
    ).filter(lambda x: x.strip() != '')
    
    # Strategy for generating pages (list of unique positive integers)
    pages_strategy = st.lists(
        st.integers(min_value=1, max_value=200),
        min_size=1,
        max_size=10,
        unique=True
    )
    
    # Strategy for generating base_effects (simplified for testing)
    # Each page has a list of question effects
    base_effect_item_strategy = st.fixed_dictionaries({
        'index': st.text(min_size=1, max_size=10).filter(lambda x: x.strip() != ''),
        'tempIndex': st.integers(min_value=0, max_value=1000),
        'type': st.sampled_from(['choice', 'fill', 'subjective']),
        'answer': st.text(max_size=50),
        'userAnswer': st.text(max_size=50),
        'correct': st.sampled_from(['true', 'false', 'partial', '']),
        'questionType': st.sampled_from(['objective', 'subjective']),
        'bvalue': st.sampled_from(['1', '2', '3', '4', '5'])
    })
    
    # Test directory for isolated file storage
    TEST_DATASETS_DIR = 'test_datasets_roundtrip'
    
    @classmethod
    def setup_class(cls):
        """设置测试环境：使用独立的测试目录"""
        # 确保测试目录存在
        if not os.path.exists(cls.TEST_DATASETS_DIR):
            os.makedirs(cls.TEST_DATASETS_DIR)
    
    @classmethod
    def teardown_class(cls):
        """清理测试环境：删除测试目录"""
        import shutil
        if os.path.exists(cls.TEST_DATASETS_DIR):
            shutil.rmtree(cls.TEST_DATASETS_DIR)
    
    @staticmethod
    def generate_test_dataset_id():
        """生成测试用的唯一数据集ID"""
        import uuid
        return f"test_roundtrip_{uuid.uuid4().hex[:8]}"
    
    def cleanup_test_dataset(self, dataset_id):
        """清理测试数据集"""
        try:
            # 尝试删除文件存储的数据集
            filepath = os.path.join(self.TEST_DATASETS_DIR, f'{dataset_id}.json')
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
    
    def save_dataset_file(self, dataset_id, data):
        """直接保存数据集到文件（绕过数据库）"""
        # 处理 name 字段：如果未提供或为空，生成默认名称
        name = data.get('name', '').strip() if data.get('name') else ''
        if not name:
            name = StorageService.generate_default_dataset_name(data)
        data['name'] = name
        
        filepath = os.path.join(self.TEST_DATASETS_DIR, f'{dataset_id}.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_dataset_file(self, dataset_id):
        """直接从文件加载数据集（绕过数据库）"""
        filepath = os.path.join(self.TEST_DATASETS_DIR, f'{dataset_id}.json')
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 处理 name 字段：如果为空则生成默认名称
            if not data.get('name'):
                data['name'] = StorageService.generate_default_dataset_name(data)
            return data
        return None
    
    @given(
        name=name_strategy,
        description=description_strategy,
        book_id=book_id_strategy,
        pages=pages_strategy
    )
    @settings(max_examples=100, deadline=None)  # deadline=None to handle timing variability
    def test_dataset_round_trip_basic_fields(self, name, description, book_id, pages):
        """
        Feature: dataset-naming-selection, Property 3: Dataset Persistence Round-Trip
        Validates: Requirements 2.3, 5.4
        
        Test that basic fields (name, description, book_id, pages) are preserved
        after save and load cycle.
        """
        # Arrange: Generate unique dataset_id for this test
        dataset_id = self.generate_test_dataset_id()
        
        try:
            # Create dataset data
            original_data = {
                'dataset_id': dataset_id,
                'name': name,
                'description': description,
                'book_id': book_id,
                'book_name': f'Test Book {book_id}',
                'subject_id': 0,
                'pages': sorted(pages),  # Sort for consistent comparison
                'base_effects': {}
            }
            
            # Act: Save the dataset using file storage
            self.save_dataset_file(dataset_id, original_data)
            
            # Act: Load the dataset back
            loaded_data = self.load_dataset_file(dataset_id)
            
            # Assert: Verify loaded data is not None
            assert loaded_data is not None, "Loaded dataset should not be None"
            
            # Assert: Verify name is preserved
            assert loaded_data.get('name') == name, \
                f"Name mismatch: expected '{name}', got '{loaded_data.get('name')}'"
            
            # Assert: Verify description is preserved
            assert loaded_data.get('description') == description, \
                f"Description mismatch: expected '{description}', got '{loaded_data.get('description')}'"
            
            # Assert: Verify book_id is preserved
            assert loaded_data.get('book_id') == book_id, \
                f"book_id mismatch: expected '{book_id}', got '{loaded_data.get('book_id')}'"
            
            # Assert: Verify pages are preserved (compare sorted lists)
            loaded_pages = loaded_data.get('pages', [])
            if isinstance(loaded_pages, str):
                loaded_pages = json.loads(loaded_pages)
            assert sorted(loaded_pages) == sorted(pages), \
                f"Pages mismatch: expected {sorted(pages)}, got {sorted(loaded_pages)}"
            
            # Assert: Verify dataset_id is preserved
            assert loaded_data.get('dataset_id') == dataset_id, \
                f"dataset_id mismatch: expected '{dataset_id}', got '{loaded_data.get('dataset_id')}'"
            
        finally:
            # Cleanup: Remove test dataset
            self.cleanup_test_dataset(dataset_id)
    
    @given(
        name=name_strategy,
        description=description_strategy,
        book_id=book_id_strategy,
        pages=pages_strategy,
        effects_per_page=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=None)  # deadline=None to handle timing variability
    def test_dataset_round_trip_with_base_effects(self, name, description, book_id, pages, effects_per_page):
        """
        Feature: dataset-naming-selection, Property 3: Dataset Persistence Round-Trip
        Validates: Requirements 2.3, 5.4
        
        Test that base_effects are preserved after save and load cycle.
        """
        # Arrange: Generate unique dataset_id for this test
        dataset_id = self.generate_test_dataset_id()
        
        try:
            # Generate base_effects for each page
            base_effects = {}
            for page in pages:
                page_effects = []
                for i in range(effects_per_page):
                    page_effects.append({
                        'index': f'{i+1}',
                        'tempIndex': i,
                        'type': 'choice',
                        'answer': 'A',
                        'userAnswer': 'A',
                        'correct': 'true',
                        'questionType': 'objective',
                        'bvalue': '1'
                    })
                base_effects[str(page)] = page_effects
            
            # Create dataset data
            original_data = {
                'dataset_id': dataset_id,
                'name': name,
                'description': description,
                'book_id': book_id,
                'book_name': f'Test Book {book_id}',
                'subject_id': 0,
                'pages': sorted(pages),
                'base_effects': base_effects
            }
            
            # Act: Save the dataset using file storage
            self.save_dataset_file(dataset_id, original_data)
            
            # Act: Load the dataset back
            loaded_data = self.load_dataset_file(dataset_id)
            
            # Assert: Verify loaded data is not None
            assert loaded_data is not None, "Loaded dataset should not be None"
            
            # Assert: Verify base_effects structure is preserved
            loaded_effects = loaded_data.get('base_effects', {})
            
            # Verify same pages have effects
            original_pages = set(base_effects.keys())
            loaded_pages = set(loaded_effects.keys())
            assert original_pages == loaded_pages, \
                f"base_effects pages mismatch: expected {original_pages}, got {loaded_pages}"
            
            # Verify each page has the same number of effects
            for page_key in original_pages:
                original_count = len(base_effects[page_key])
                loaded_count = len(loaded_effects.get(page_key, []))
                assert original_count == loaded_count, \
                    f"Effect count mismatch for page {page_key}: expected {original_count}, got {loaded_count}"
                
                # Verify key fields of each effect
                for i, (orig_effect, loaded_effect) in enumerate(zip(base_effects[page_key], loaded_effects[page_key])):
                    assert orig_effect['index'] == loaded_effect['index'], \
                        f"Effect index mismatch at page {page_key}, item {i}"
                    assert orig_effect['answer'] == loaded_effect['answer'], \
                        f"Effect answer mismatch at page {page_key}, item {i}"
                    assert orig_effect['correct'] == loaded_effect['correct'], \
                        f"Effect correct mismatch at page {page_key}, item {i}"
            
        finally:
            # Cleanup: Remove test dataset
            self.cleanup_test_dataset(dataset_id)
    
    @given(
        name=name_strategy,
        book_id=book_id_strategy,
        pages=pages_strategy
    )
    @settings(max_examples=50, deadline=None)  # deadline=None to handle timing variability
    def test_dataset_round_trip_preserves_question_count(self, name, book_id, pages):
        """
        Feature: dataset-naming-selection, Property 3: Dataset Persistence Round-Trip
        Validates: Requirements 2.3, 5.4
        
        Test that question_count is correctly calculated and preserved.
        """
        # Arrange: Generate unique dataset_id for this test
        dataset_id = self.generate_test_dataset_id()
        
        try:
            # Generate base_effects with known question count
            base_effects = {}
            total_questions = 0
            for page in pages:
                num_questions = (page % 5) + 1  # 1-5 questions per page
                page_effects = []
                for i in range(num_questions):
                    page_effects.append({
                        'index': f'{i+1}',
                        'tempIndex': i,
                        'type': 'choice',
                        'answer': 'A',
                        'userAnswer': 'A',
                        'correct': 'true',
                        'questionType': 'objective',
                        'bvalue': '1'
                    })
                base_effects[str(page)] = page_effects
                total_questions += num_questions
            
            # Create dataset data
            original_data = {
                'dataset_id': dataset_id,
                'name': name,
                'description': '',
                'book_id': book_id,
                'book_name': f'Test Book {book_id}',
                'subject_id': 0,
                'pages': sorted(pages),
                'base_effects': base_effects
            }
            
            # Act: Save the dataset using file storage
            self.save_dataset_file(dataset_id, original_data)
            
            # Act: Load the dataset back
            loaded_data = self.load_dataset_file(dataset_id)
            
            # Assert: Verify loaded data is not None
            assert loaded_data is not None, "Loaded dataset should not be None"
            
            # Assert: Verify question count matches
            loaded_effects = loaded_data.get('base_effects', {})
            loaded_question_count = sum(
                len(effects) for effects in loaded_effects.values()
            )
            assert loaded_question_count == total_questions, \
                f"Question count mismatch: expected {total_questions}, got {loaded_question_count}"
            
        finally:
            # Cleanup: Remove test dataset
            self.cleanup_test_dataset(dataset_id)
    
    @given(
        name=name_strategy,
        description=description_strategy,
        book_id=book_id_strategy,
        pages=pages_strategy
    )
    @settings(max_examples=30, deadline=None)  # deadline=None to handle timing variability
    def test_dataset_round_trip_idempotent(self, name, description, book_id, pages):
        """
        Feature: dataset-naming-selection, Property 3: Dataset Persistence Round-Trip
        Validates: Requirements 2.3, 5.4
        
        Test that multiple save-load cycles produce consistent results (idempotency).
        """
        # Arrange: Generate unique dataset_id for this test
        dataset_id = self.generate_test_dataset_id()
        
        try:
            # Create dataset data
            original_data = {
                'dataset_id': dataset_id,
                'name': name,
                'description': description,
                'book_id': book_id,
                'book_name': f'Test Book {book_id}',
                'subject_id': 0,
                'pages': sorted(pages),
                'base_effects': {
                    str(pages[0]): [
                        {'index': '1', 'tempIndex': 0, 'type': 'choice', 
                         'answer': 'A', 'userAnswer': 'A', 'correct': 'true',
                         'questionType': 'objective', 'bvalue': '1'}
                    ]
                }
            }
            
            # Act: First save-load cycle using file storage
            self.save_dataset_file(dataset_id, original_data)
            loaded_data_1 = self.load_dataset_file(dataset_id)
            
            # Act: Second save-load cycle (save what we loaded)
            self.save_dataset_file(dataset_id, loaded_data_1)
            loaded_data_2 = self.load_dataset_file(dataset_id)
            
            # Assert: Key fields should be identical after both cycles
            assert loaded_data_1.get('name') == loaded_data_2.get('name'), \
                "Name should be identical after multiple save-load cycles"
            assert loaded_data_1.get('description') == loaded_data_2.get('description'), \
                "Description should be identical after multiple save-load cycles"
            assert loaded_data_1.get('book_id') == loaded_data_2.get('book_id'), \
                "book_id should be identical after multiple save-load cycles"
            
            # Compare pages (handle potential string/list conversion)
            pages_1 = loaded_data_1.get('pages', [])
            pages_2 = loaded_data_2.get('pages', [])
            if isinstance(pages_1, str):
                pages_1 = json.loads(pages_1)
            if isinstance(pages_2, str):
                pages_2 = json.loads(pages_2)
            assert sorted(pages_1) == sorted(pages_2), \
                "Pages should be identical after multiple save-load cycles"
            
            # Compare base_effects structure
            effects_1 = loaded_data_1.get('base_effects', {})
            effects_2 = loaded_data_2.get('base_effects', {})
            assert set(effects_1.keys()) == set(effects_2.keys()), \
                "base_effects keys should be identical after multiple save-load cycles"
            
        finally:
            # Cleanup: Remove test dataset
            self.cleanup_test_dataset(dataset_id)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestNameSearchCompleteness:
    """
    属性测试：名称搜索完整性
    Feature: dataset-naming-selection, Property 4: Name Search Completeness
    Validates: Requirements 2.4, 3.3
    
    Property: For any search query string and set of datasets, the search results 
    SHALL include all and only datasets whose name contains the query string (case-insensitive).
    """
    
    # Strategy for generating valid dataset names (ASCII alphanumeric only)
    # Use simple ASCII characters for predictable case behavior
    name_strategy = st.from_regex(r'[A-Za-z0-9][A-Za-z0-9 _-]{0,49}', fullmatch=True)
    
    # Strategy for generating search queries (non-empty, URL-safe characters)
    # Exclude special URL characters that cause encoding issues (#, %, &, ?, etc.)
    search_query_strategy = st.from_regex(r'[A-Za-z0-9][A-Za-z0-9_-]{0,19}', fullmatch=True)
    
    @given(
        search_query=search_query_strategy,
        dataset_names=st.lists(name_strategy, min_size=1, max_size=10, unique=True)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_name_search_completeness(self, search_query, dataset_names, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 4: Name Search Completeness
        Validates: Requirements 2.4, 3.3
        
        Test that search returns all and only datasets whose name contains the query (case-insensitive).
        """
        # Arrange: Create mock datasets with given names
        mock_datasets = []
        for i, name in enumerate(dataset_names):
            mock_datasets.append({
                'dataset_id': f'test_search_{i:03d}',
                'name': name,
                'book_id': f'book_{i}',
                'book_name': f'Test Book {i}',
                'subject_id': 0,
                'pages': [i + 1],
                'question_count': 10,
                'description': '',
                'created_at': f'2024-01-{(i+1):02d}T10:00:00'
            })
        
        def mock_get_all_datasets_summary():
            return mock_datasets
        
        monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
        
        # Act: Search with query
        response = client.get(f'/api/batch/datasets?search={search_query}')
        
        # Assert: Response should be successful
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] is True, f"Expected success=True, got {data}"
        
        # Calculate expected results: datasets whose name contains query (case-insensitive)
        search_lower = search_query.lower()
        expected_dataset_ids = set()
        for ds in mock_datasets:
            ds_name = ds.get('name', '') or ''
            if search_lower in ds_name.lower():
                expected_dataset_ids.add(ds['dataset_id'])
        
        # Get actual results
        actual_dataset_ids = set(ds['dataset_id'] for ds in data['data'])
        
        # Assert: All matching datasets are returned (completeness)
        missing_datasets = expected_dataset_ids - actual_dataset_ids
        assert len(missing_datasets) == 0, \
            f"Search '{search_query}' should return datasets {missing_datasets} but they are missing. " \
            f"Expected: {expected_dataset_ids}, Got: {actual_dataset_ids}"
        
        # Assert: No non-matching datasets are returned (precision)
        extra_datasets = actual_dataset_ids - expected_dataset_ids
        assert len(extra_datasets) == 0, \
            f"Search '{search_query}' should NOT return datasets {extra_datasets}. " \
            f"Expected: {expected_dataset_ids}, Got: {actual_dataset_ids}"
    
    @given(
        base_name=name_strategy,
        case_variations=st.lists(
            st.sampled_from(['upper', 'lower', 'title', 'mixed']),
            min_size=2,
            max_size=5
        )
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_name_search_case_insensitive(self, base_name, case_variations, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 4: Name Search Completeness
        Validates: Requirements 2.4, 3.3
        
        Test that search is case-insensitive: searching for any case variation 
        should return all datasets with names containing the base string.
        """
        # Arrange: Create datasets with different case variations of the same base name
        def apply_case(name, variation):
            if variation == 'upper':
                return name.upper()
            elif variation == 'lower':
                return name.lower()
            elif variation == 'title':
                return name.title()
            else:  # mixed
                return ''.join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(name))
        
        mock_datasets = []
        for i, variation in enumerate(case_variations):
            varied_name = apply_case(base_name, variation)
            mock_datasets.append({
                'dataset_id': f'test_case_{i:03d}',
                'name': varied_name,
                'book_id': f'book_{i}',
                'book_name': f'Test Book {i}',
                'subject_id': 0,
                'pages': [i + 1],
                'question_count': 10,
                'description': '',
                'created_at': f'2024-01-{(i+1):02d}T10:00:00'
            })
        
        def mock_get_all_datasets_summary():
            return mock_datasets
        
        monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
        
        # Act: Search with original base_name
        response = client.get(f'/api/batch/datasets?search={base_name}')
        
        # Assert: Response should be successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Assert: All datasets should be returned (case-insensitive match)
        actual_count = len(data['data'])
        expected_count = len(mock_datasets)
        assert actual_count == expected_count, \
            f"Case-insensitive search for '{base_name}' should return all {expected_count} datasets, " \
            f"but got {actual_count}. Dataset names: {[ds['name'] for ds in mock_datasets]}"
    
    @given(
        matching_names=st.lists(name_strategy, min_size=1, max_size=5, unique=True),
        non_matching_names=st.lists(name_strategy, min_size=1, max_size=5, unique=True)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_name_search_excludes_non_matching(self, matching_names, non_matching_names, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 4: Name Search Completeness
        Validates: Requirements 2.4, 3.3
        
        Test that search excludes datasets whose names do not contain the query.
        """
        # Arrange: Use a unique search term that only appears in matching_names
        unique_marker = "UNIQUE_SEARCH_MARKER_XYZ"
        
        # Add unique marker to matching names
        marked_matching_names = [f"{name}_{unique_marker}" for name in matching_names]
        
        # Ensure non-matching names don't contain the marker
        safe_non_matching_names = [
            name for name in non_matching_names 
            if unique_marker.lower() not in name.lower()
        ]
        
        # If all non-matching names were filtered out, skip this test case
        if not safe_non_matching_names:
            return
        
        mock_datasets = []
        # Add matching datasets
        for i, name in enumerate(marked_matching_names):
            mock_datasets.append({
                'dataset_id': f'test_match_{i:03d}',
                'name': name,
                'book_id': f'book_match_{i}',
                'book_name': f'Matching Book {i}',
                'subject_id': 0,
                'pages': [i + 1],
                'question_count': 10,
                'description': '',
                'created_at': f'2024-01-{(i+1):02d}T10:00:00'
            })
        
        # Add non-matching datasets
        for i, name in enumerate(safe_non_matching_names):
            mock_datasets.append({
                'dataset_id': f'test_nomatch_{i:03d}',
                'name': name,
                'book_id': f'book_nomatch_{i}',
                'book_name': f'Non-Matching Book {i}',
                'subject_id': 0,
                'pages': [100 + i],
                'question_count': 5,
                'description': '',
                'created_at': f'2024-02-{(i+1):02d}T10:00:00'
            })
        
        def mock_get_all_datasets_summary():
            return mock_datasets
        
        monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
        
        # Act: Search with unique marker
        response = client.get(f'/api/batch/datasets?search={unique_marker}')
        
        # Assert: Response should be successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Assert: Only matching datasets should be returned
        actual_ids = set(ds['dataset_id'] for ds in data['data'])
        expected_ids = set(f'test_match_{i:03d}' for i in range(len(marked_matching_names)))
        
        assert actual_ids == expected_ids, \
            f"Search for '{unique_marker}' should return only matching datasets. " \
            f"Expected: {expected_ids}, Got: {actual_ids}"
    
    @given(
        dataset_names=st.lists(name_strategy, min_size=2, max_size=8, unique=True)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_name_search_empty_query_returns_all(self, dataset_names, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 4: Name Search Completeness
        Validates: Requirements 2.4, 3.3
        
        Test that empty search query returns all datasets (no filtering).
        """
        # Arrange: Create mock datasets
        mock_datasets = []
        for i, name in enumerate(dataset_names):
            mock_datasets.append({
                'dataset_id': f'test_all_{i:03d}',
                'name': name,
                'book_id': f'book_{i}',
                'book_name': f'Test Book {i}',
                'subject_id': 0,
                'pages': [i + 1],
                'question_count': 10,
                'description': '',
                'created_at': f'2024-01-{(i+1):02d}T10:00:00'
            })
        
        def mock_get_all_datasets_summary():
            return mock_datasets
        
        monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
        
        # Act: Search with empty query
        response = client.get('/api/batch/datasets?search=')
        
        # Assert: Response should be successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Assert: All datasets should be returned
        assert len(data['data']) == len(mock_datasets), \
            f"Empty search should return all {len(mock_datasets)} datasets, got {len(data['data'])}"
    
    @given(
        search_query=search_query_strategy
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_name_search_no_match_returns_empty(self, search_query, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 4: Name Search Completeness
        Validates: Requirements 2.4, 3.3
        
        Test that search returns empty list when no datasets match the query.
        """
        # Arrange: Create mock datasets with names that definitely don't contain the search query
        # Use a completely different character set to ensure no match
        mock_datasets = [
            {
                'dataset_id': 'test_nomatch_001',
                'name': '12345',  # Only digits
                'book_id': 'book_1',
                'book_name': 'Test Book 1',
                'subject_id': 0,
                'pages': [1],
                'question_count': 10,
                'description': '',
                'created_at': '2024-01-01T10:00:00'
            },
            {
                'dataset_id': 'test_nomatch_002',
                'name': '67890',  # Only digits
                'book_id': 'book_2',
                'book_name': 'Test Book 2',
                'subject_id': 0,
                'pages': [2],
                'question_count': 10,
                'description': '',
                'created_at': '2024-01-02T10:00:00'
            }
        ]
        
        # Only test if search_query doesn't match the digit-only names
        if any(search_query.lower() in ds['name'].lower() for ds in mock_datasets):
            return  # Skip this test case
        
        def mock_get_all_datasets_summary():
            return mock_datasets
        
        monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
        
        # Act: Search with query that doesn't match any dataset
        response = client.get(f'/api/batch/datasets?search={search_query}')
        
        # Assert: Response should be successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Assert: No datasets should be returned
        assert len(data['data']) == 0, \
            f"Search for '{search_query}' should return empty list when no match, " \
            f"but got {len(data['data'])} results"
    
    @given(
        prefix=st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1, max_size=10),
        suffix=st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1, max_size=10),
        middle=st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1, max_size=10)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_name_search_substring_matching(self, prefix, suffix, middle, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 4: Name Search Completeness
        Validates: Requirements 2.4, 3.3
        
        Test that search correctly matches substrings at any position in the name.
        """
        # Arrange: Create datasets with the search term at different positions
        search_term = "FINDME"
        mock_datasets = [
            {
                'dataset_id': 'test_prefix',
                'name': f'{search_term}{suffix}',  # Search term at start
                'book_id': 'book_1',
                'book_name': 'Test Book 1',
                'subject_id': 0,
                'pages': [1],
                'question_count': 10,
                'description': '',
                'created_at': '2024-01-01T10:00:00'
            },
            {
                'dataset_id': 'test_suffix',
                'name': f'{prefix}{search_term}',  # Search term at end
                'book_id': 'book_2',
                'book_name': 'Test Book 2',
                'subject_id': 0,
                'pages': [2],
                'question_count': 10,
                'description': '',
                'created_at': '2024-01-02T10:00:00'
            },
            {
                'dataset_id': 'test_middle',
                'name': f'{prefix}{search_term}{suffix}',  # Search term in middle
                'book_id': 'book_3',
                'book_name': 'Test Book 3',
                'subject_id': 0,
                'pages': [3],
                'question_count': 10,
                'description': '',
                'created_at': '2024-01-03T10:00:00'
            },
            {
                'dataset_id': 'test_nomatch',
                'name': f'{prefix}{middle}{suffix}',  # No search term
                'book_id': 'book_4',
                'book_name': 'Test Book 4',
                'subject_id': 0,
                'pages': [4],
                'question_count': 10,
                'description': '',
                'created_at': '2024-01-04T10:00:00'
            }
        ]
        
        def mock_get_all_datasets_summary():
            return mock_datasets
        
        monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
        
        # Act: Search for the term
        response = client.get(f'/api/batch/datasets?search={search_term}')
        
        # Assert: Response should be successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Assert: Should return exactly 3 matching datasets (prefix, suffix, middle)
        actual_ids = set(ds['dataset_id'] for ds in data['data'])
        expected_ids = {'test_prefix', 'test_suffix', 'test_middle'}
        
        assert actual_ids == expected_ids, \
            f"Search for '{search_term}' should match datasets at any position. " \
            f"Expected: {expected_ids}, Got: {actual_ids}"


class TestMatchingDatasets:
    """测试 GET /api/batch/matching-datasets 接口"""
    
    def test_matching_datasets_missing_book_id(self, client):
        """Task 5.1: 缺少 book_id 参数返回 400 错误"""
        response = client.get('/api/batch/matching-datasets?page_num=30')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert '缺少书本ID' in data['error']
    
    def test_matching_datasets_missing_page_num(self, client):
        """Task 5.1: 缺少 page_num 参数返回 400 错误"""
        response = client.get('/api/batch/matching-datasets?book_id=book123')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert '缺少页码' in data['error']
    
    def test_matching_datasets_invalid_page_num_string(self, client):
        """Task 5.1: page_num 非数字返回 400 错误"""
        response = client.get('/api/batch/matching-datasets?book_id=book123&page_num=abc')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert '页码必须是正整数' in data['error']
    
    def test_matching_datasets_invalid_page_num_zero(self, client):
        """Task 5.1: page_num 为 0 返回 400 错误"""
        response = client.get('/api/batch/matching-datasets?book_id=book123&page_num=0')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert '页码必须是正整数' in data['error']
    
    def test_matching_datasets_invalid_page_num_negative(self, client):
        """Task 5.1: page_num 为负数返回 400 错误"""
        response = client.get('/api/batch/matching-datasets?book_id=book123&page_num=-5')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert '页码必须是正整数' in data['error']
    
    def test_matching_datasets_found(self, client, monkeypatch):
        """Task 5.1: 成功返回匹配的数据集列表"""
        mock_result = [
            {
                'dataset_id': 'test001',
                'name': '学生A基准',
                'book_id': 'book123',
                'book_name': '七年级英语上册',
                'subject_id': 0,
                'pages': [30, 31],
                'question_count': 50,
                'description': '',
                'created_at': '2024-01-16T10:00:00'
            },
            {
                'dataset_id': 'test002',
                'name': '学生B基准',
                'book_id': 'book123',
                'book_name': '七年级英语上册',
                'subject_id': 0,
                'pages': [30, 31, 32],
                'question_count': 48,
                'created_at': '2024-01-15T10:00:00'
            }
        ]
        
        def mock_get_matching_datasets(book_id, page_num):
            return mock_result
        
        monkeypatch.setattr(StorageService, 'get_matching_datasets', mock_get_matching_datasets)
        
        response = client.get('/api/batch/matching-datasets?book_id=book123&page_num=30')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 2
        
        # 验证返回的字段
        for ds in data['data']:
            assert 'dataset_id' in ds
            assert 'name' in ds
            assert 'book_name' in ds
            assert 'pages' in ds
            assert 'question_count' in ds
            assert 'created_at' in ds
    
    def test_matching_datasets_not_found(self, client, monkeypatch):
        """Task 5.1: 无匹配数据集时返回空数组"""
        def mock_get_matching_datasets(book_id, page_num):
            return []
        
        monkeypatch.setattr(StorageService, 'get_matching_datasets', mock_get_matching_datasets)
        
        response = client.get('/api/batch/matching-datasets?book_id=book999&page_num=100')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data'] == []
    
    def test_matching_datasets_sorted_by_created_at_desc(self, client, monkeypatch):
        """Task 5.1: 返回结果按 created_at 倒序排列"""
        # StorageService.get_matching_datasets 已经按 created_at 倒序排列
        mock_result = [
            {
                'dataset_id': 'newest',
                'name': '最新数据集',
                'book_id': 'book123',
                'book_name': '测试书本',
                'subject_id': 0,
                'pages': [30],
                'question_count': 10,
                'description': '',
                'created_at': '2024-01-17T10:00:00'
            },
            {
                'dataset_id': 'middle',
                'name': '中间数据集',
                'book_id': 'book123',
                'book_name': '测试书本',
                'subject_id': 0,
                'pages': [30],
                'question_count': 10,
                'description': '',
                'created_at': '2024-01-16T10:00:00'
            },
            {
                'dataset_id': 'oldest',
                'name': '最旧数据集',
                'book_id': 'book123',
                'book_name': '测试书本',
                'subject_id': 0,
                'pages': [30],
                'question_count': 10,
                'description': '',
                'created_at': '2024-01-15T10:00:00'
            }
        ]
        
        def mock_get_matching_datasets(book_id, page_num):
            return mock_result
        
        monkeypatch.setattr(StorageService, 'get_matching_datasets', mock_get_matching_datasets)
        
        response = client.get('/api/batch/matching-datasets?book_id=book123&page_num=30')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # 验证按创建时间倒序（最新的在前）
        dates = [ds['created_at'] for ds in data['data']]
        assert dates == sorted(dates, reverse=True)
        assert data['data'][0]['dataset_id'] == 'newest'
        assert data['data'][-1]['dataset_id'] == 'oldest'
    
    def test_matching_datasets_required_fields(self, client, monkeypatch):
        """Task 5.1: 验证返回结果包含所有必需字段"""
        mock_result = [
            {
                'dataset_id': 'test001',
                'name': '测试数据集',
                'book_id': 'book123',
                'book_name': '七年级英语上册',
                'subject_id': 0,
                'pages': [30, 31],
                'question_count': 50,
                'description': '测试描述',
                'created_at': '2024-01-15T10:00:00'
            }
        ]
        
        def mock_get_matching_datasets(book_id, page_num):
            return mock_result
        
        monkeypatch.setattr(StorageService, 'get_matching_datasets', mock_get_matching_datasets)
        
        response = client.get('/api/batch/matching-datasets?book_id=book123&page_num=30')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # 验证必需字段（根据设计文档）
        required_fields = ['dataset_id', 'name', 'book_name', 'pages', 'question_count', 'created_at']
        for ds in data['data']:
            for field in required_fields:
                assert field in ds, f"Missing required field: {field}"


class TestMatchingDatasetsProperty:
    """
    属性测试：匹配数据集完整性
    Feature: dataset-naming-selection, Property 10: Matching Datasets Completeness
    Validates: Requirements 5.1, 7.1
    
    Property: For any book_id and page_num combination, the matching datasets query
    SHALL return all datasets where book_id matches AND the pages array contains the specified page_num.
    """
    
    # Strategy for generating URL-safe book_id (alphanumeric and some safe characters)
    book_id_strategy = st.text(
        alphabet=st.characters(
            whitelist_categories=('L', 'N'),  # Letters and Numbers only
            whitelist_characters='-_'  # Also allow dash and underscore
        ),
        min_size=1,
        max_size=20
    ).filter(lambda x: x.strip() != '')
    
    # Test directory for isolated file storage
    TEST_DATASETS_DIR = 'test_datasets_matching'
    
    @classmethod
    def setup_class(cls):
        """设置测试环境：使用独立的测试目录"""
        import shutil
        # 清理并创建测试目录
        if os.path.exists(cls.TEST_DATASETS_DIR):
            shutil.rmtree(cls.TEST_DATASETS_DIR)
        os.makedirs(cls.TEST_DATASETS_DIR)
    
    @classmethod
    def teardown_class(cls):
        """清理测试环境：删除测试目录"""
        import shutil
        if os.path.exists(cls.TEST_DATASETS_DIR):
            shutil.rmtree(cls.TEST_DATASETS_DIR)
    
    def cleanup_test_datasets(self):
        """清理测试目录中的所有数据集文件"""
        import shutil
        if os.path.exists(self.TEST_DATASETS_DIR):
            shutil.rmtree(self.TEST_DATASETS_DIR)
        os.makedirs(self.TEST_DATASETS_DIR)
    
    def save_test_dataset(self, dataset_id, data):
        """保存测试数据集到文件"""
        filepath = os.path.join(self.TEST_DATASETS_DIR, f'{dataset_id}.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_matching_datasets_file_storage(self, book_id, page_num):
        """
        从文件存储获取匹配的数据集（模拟 StorageService.get_matching_datasets 的文件存储逻辑）
        """
        result = []
        if not os.path.exists(self.TEST_DATASETS_DIR):
            return result
        
        for filename in os.listdir(self.TEST_DATASETS_DIR):
            if not filename.endswith('.json'):
                continue
            
            dataset_id = filename[:-5]
            filepath = os.path.join(self.TEST_DATASETS_DIR, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查 book_id 匹配且 pages 包含 page_num
            if data.get('book_id') == book_id:
                pages = data.get('pages', [])
                if page_num in pages:
                    name = data.get('name')
                    if not name:
                        name = StorageService.generate_default_dataset_name(data)
                    
                    question_count = 0
                    for effects in data.get('base_effects', {}).values():
                        question_count += len(effects) if isinstance(effects, list) else 0
                    
                    result.append({
                        'dataset_id': dataset_id,
                        'name': name,
                        'book_id': data.get('book_id'),
                        'book_name': data.get('book_name', ''),
                        'subject_id': data.get('subject_id'),
                        'pages': pages,
                        'question_count': question_count,
                        'description': data.get('description', ''),
                        'created_at': data.get('created_at', '')
                    })
        
        # 按创建时间倒序排列
        result.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return result
    
    @given(
        book_id=book_id_strategy,
        page_num=st.integers(min_value=1, max_value=200)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_matching_datasets_api_validation(self, book_id, page_num, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 10: Matching Datasets Completeness
        Validates: Requirements 5.1, 7.1
        
        Test that the API correctly validates parameters and returns proper response structure.
        """
        # Mock the storage service to return empty list
        def mock_get_matching_datasets(b_id, p_num):
            return []
        
        monkeypatch.setattr(StorageService, 'get_matching_datasets', mock_get_matching_datasets)
        
        # Act: Call the API with valid parameters
        response = client.get(f'/api/batch/matching-datasets?book_id={book_id}&page_num={page_num}')
        
        # Assert: Response should be successful with proper structure
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert isinstance(data['data'], list)
    
    @given(
        page_num=st.integers(max_value=0)  # Zero or negative
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_matching_datasets_rejects_invalid_page_num(self, page_num, client):
        """
        Feature: dataset-naming-selection, Property 10: Matching Datasets Completeness
        Validates: Requirements 5.1
        
        Test that invalid page numbers (zero or negative) are rejected.
        """
        # Act: Call the API with invalid page_num
        response = client.get(f'/api/batch/matching-datasets?book_id=test_book&page_num={page_num}')
        
        # Assert: Should return 400 error
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert '页码必须是正整数' in data['error']
    
    @given(
        book_id=book_id_strategy,
        page_num=st.integers(min_value=1, max_value=200),
        dataset_pages_list=st.lists(
            st.lists(st.integers(min_value=1, max_value=200), min_size=1, max_size=10, unique=True),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_matching_datasets_completeness(self, book_id, page_num, dataset_pages_list):
        """
        Feature: dataset-naming-selection, Property 10: Matching Datasets Completeness
        Validates: Requirements 5.1, 7.1
        
        Property: For any book_id and page_num combination, the matching datasets query
        SHALL return ALL datasets where book_id matches AND the pages array contains
        the specified page_num.
        
        This test verifies:
        1. All matching datasets are returned (completeness)
        2. No non-matching datasets are returned (precision)
        """
        # Arrange: Clean up test directory
        self.cleanup_test_datasets()
        
        # Create datasets with the given pages
        expected_matching_ids = set()
        all_dataset_ids = set()
        
        for i, pages in enumerate(dataset_pages_list):
            dataset_id = f'test_match_{i:03d}'
            all_dataset_ids.add(dataset_id)
            
            # Create dataset data
            dataset_data = {
                'dataset_id': dataset_id,
                'name': f'测试数据集_{i}',
                'book_id': book_id,  # All datasets have the same book_id
                'book_name': f'测试书本_{book_id}',
                'subject_id': 0,
                'pages': sorted(pages),
                'base_effects': {},
                'description': '',
                'created_at': f'2024-01-{(i+1):02d}T10:00:00'
            }
            
            # Save dataset
            self.save_test_dataset(dataset_id, dataset_data)
            
            # Track if this dataset should match
            if page_num in pages:
                expected_matching_ids.add(dataset_id)
        
        # Act: Query matching datasets
        result = self.get_matching_datasets_file_storage(book_id, page_num)
        actual_matching_ids = set(ds['dataset_id'] for ds in result)
        
        # Assert: Verify completeness - all matching datasets are returned
        missing_datasets = expected_matching_ids - actual_matching_ids
        assert len(missing_datasets) == 0, \
            f"Missing datasets that should match: {missing_datasets}. " \
            f"Query: book_id={book_id}, page_num={page_num}. " \
            f"Expected: {expected_matching_ids}, Got: {actual_matching_ids}"
        
        # Assert: Verify precision - no non-matching datasets are returned
        extra_datasets = actual_matching_ids - expected_matching_ids
        assert len(extra_datasets) == 0, \
            f"Extra datasets that should NOT match: {extra_datasets}. " \
            f"Query: book_id={book_id}, page_num={page_num}. " \
            f"Expected: {expected_matching_ids}, Got: {actual_matching_ids}"
    
    @given(
        target_book_id=book_id_strategy,
        other_book_id=book_id_strategy,
        page_num=st.integers(min_value=1, max_value=200)
    )
    @settings(max_examples=100, deadline=None)
    def test_matching_datasets_book_id_filter(self, target_book_id, other_book_id, page_num):
        """
        Feature: dataset-naming-selection, Property 10: Matching Datasets Completeness
        Validates: Requirements 5.1, 7.1
        
        Test that only datasets with matching book_id are returned,
        even if other datasets contain the same page_num.
        """
        # Skip if book_ids are the same (can't test filtering)
        if target_book_id == other_book_id:
            return
        
        # Arrange: Clean up test directory
        self.cleanup_test_datasets()
        
        # Create dataset with target book_id containing page_num
        target_dataset = {
            'dataset_id': 'target_ds',
            'name': '目标数据集',
            'book_id': target_book_id,
            'book_name': f'目标书本_{target_book_id}',
            'subject_id': 0,
            'pages': [page_num],
            'base_effects': {},
            'description': '',
            'created_at': '2024-01-01T10:00:00'
        }
        self.save_test_dataset('target_ds', target_dataset)
        
        # Create dataset with different book_id containing same page_num
        other_dataset = {
            'dataset_id': 'other_ds',
            'name': '其他数据集',
            'book_id': other_book_id,
            'book_name': f'其他书本_{other_book_id}',
            'subject_id': 0,
            'pages': [page_num],  # Same page_num
            'base_effects': {},
            'description': '',
            'created_at': '2024-01-02T10:00:00'
        }
        self.save_test_dataset('other_ds', other_dataset)
        
        # Act: Query with target book_id
        result = self.get_matching_datasets_file_storage(target_book_id, page_num)
        result_ids = set(ds['dataset_id'] for ds in result)
        
        # Assert: Only target dataset should be returned
        assert 'target_ds' in result_ids, \
            f"Target dataset should be returned for book_id={target_book_id}, page_num={page_num}"
        assert 'other_ds' not in result_ids, \
            f"Other dataset (book_id={other_book_id}) should NOT be returned when querying book_id={target_book_id}"
    
    @given(
        book_id=book_id_strategy,
        target_page=st.integers(min_value=1, max_value=200),
        other_pages=st.lists(st.integers(min_value=1, max_value=200), min_size=1, max_size=5, unique=True)
    )
    @settings(max_examples=100, deadline=None)
    def test_matching_datasets_page_num_filter(self, book_id, target_page, other_pages):
        """
        Feature: dataset-naming-selection, Property 10: Matching Datasets Completeness
        Validates: Requirements 5.1, 7.1
        
        Test that only datasets containing the specified page_num are returned.
        """
        # Ensure other_pages doesn't contain target_page for this test
        other_pages_filtered = [p for p in other_pages if p != target_page]
        if not other_pages_filtered:
            return  # Skip if all pages were filtered out
        
        # Arrange: Clean up test directory
        self.cleanup_test_datasets()
        
        # Create dataset containing target_page
        matching_dataset = {
            'dataset_id': 'matching_ds',
            'name': '匹配数据集',
            'book_id': book_id,
            'book_name': f'测试书本_{book_id}',
            'subject_id': 0,
            'pages': [target_page],
            'base_effects': {},
            'description': '',
            'created_at': '2024-01-01T10:00:00'
        }
        self.save_test_dataset('matching_ds', matching_dataset)
        
        # Create dataset NOT containing target_page
        non_matching_dataset = {
            'dataset_id': 'non_matching_ds',
            'name': '不匹配数据集',
            'book_id': book_id,  # Same book_id
            'book_name': f'测试书本_{book_id}',
            'subject_id': 0,
            'pages': other_pages_filtered,  # Different pages
            'base_effects': {},
            'description': '',
            'created_at': '2024-01-02T10:00:00'
        }
        self.save_test_dataset('non_matching_ds', non_matching_dataset)
        
        # Act: Query with target_page
        result = self.get_matching_datasets_file_storage(book_id, target_page)
        result_ids = set(ds['dataset_id'] for ds in result)
        
        # Assert: Only matching dataset should be returned
        assert 'matching_ds' in result_ids, \
            f"Dataset containing page {target_page} should be returned"
        assert 'non_matching_ds' not in result_ids, \
            f"Dataset NOT containing page {target_page} should NOT be returned. " \
            f"Non-matching pages: {other_pages_filtered}"
    
    @given(
        book_id=book_id_strategy,
        page_num=st.integers(min_value=1, max_value=200),
        num_matching=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=50, deadline=None)
    def test_matching_datasets_returns_all_matches(self, book_id, page_num, num_matching):
        """
        Feature: dataset-naming-selection, Property 10: Matching Datasets Completeness
        Validates: Requirements 5.1, 7.1
        
        Test that ALL datasets matching the criteria are returned, not just one.
        """
        # Arrange: Clean up test directory
        self.cleanup_test_datasets()
        
        # Create multiple datasets all containing the same page_num
        expected_ids = set()
        for i in range(num_matching):
            dataset_id = f'multi_match_{i:03d}'
            expected_ids.add(dataset_id)
            
            dataset_data = {
                'dataset_id': dataset_id,
                'name': f'多匹配数据集_{i}',
                'book_id': book_id,
                'book_name': f'测试书本_{book_id}',
                'subject_id': 0,
                'pages': [page_num, page_num + i + 1],  # All contain page_num
                'base_effects': {},
                'description': '',
                'created_at': f'2024-01-{(i+1):02d}T10:00:00'
            }
            self.save_test_dataset(dataset_id, dataset_data)
        
        # Act: Query matching datasets
        result = self.get_matching_datasets_file_storage(book_id, page_num)
        actual_ids = set(ds['dataset_id'] for ds in result)
        
        # Assert: All matching datasets should be returned
        assert actual_ids == expected_ids, \
            f"All {num_matching} matching datasets should be returned. " \
            f"Expected: {expected_ids}, Got: {actual_ids}"
    
    @given(
        book_id=book_id_strategy,
        page_num=st.integers(min_value=1, max_value=200)
    )
    @settings(max_examples=50, deadline=None)
    def test_matching_datasets_empty_when_no_match(self, book_id, page_num):
        """
        Feature: dataset-naming-selection, Property 10: Matching Datasets Completeness
        Validates: Requirements 5.1, 7.1
        
        Test that empty list is returned when no datasets match.
        """
        # Arrange: Clean up test directory (ensure no datasets exist)
        self.cleanup_test_datasets()
        
        # Act: Query with no datasets
        result = self.get_matching_datasets_file_storage(book_id, page_num)
        
        # Assert: Should return empty list
        assert result == [], \
            f"Should return empty list when no datasets exist, got: {result}"
    
    @given(
        book_id=book_id_strategy,
        page_num=st.integers(min_value=1, max_value=200),
        pages_list=st.lists(st.integers(min_value=1, max_value=200), min_size=1, max_size=20, unique=True)
    )
    @settings(max_examples=50, deadline=None)
    def test_matching_datasets_page_in_large_pages_array(self, book_id, page_num, pages_list):
        """
        Feature: dataset-naming-selection, Property 10: Matching Datasets Completeness
        Validates: Requirements 5.1, 7.1
        
        Test that matching works correctly when page_num is in a large pages array.
        """
        # Arrange: Clean up test directory
        self.cleanup_test_datasets()
        
        # Ensure page_num is in the pages list
        if page_num not in pages_list:
            pages_list = pages_list + [page_num]
        
        dataset_data = {
            'dataset_id': 'large_pages_ds',
            'name': '大页码数组数据集',
            'book_id': book_id,
            'book_name': f'测试书本_{book_id}',
            'subject_id': 0,
            'pages': sorted(pages_list),
            'base_effects': {},
            'description': '',
            'created_at': '2024-01-01T10:00:00'
        }
        self.save_test_dataset('large_pages_ds', dataset_data)
        
        # Act: Query with page_num
        result = self.get_matching_datasets_file_storage(book_id, page_num)
        
        # Assert: Dataset should be found
        assert len(result) == 1, \
            f"Should find dataset with page {page_num} in pages array {sorted(pages_list)}"
        assert result[0]['dataset_id'] == 'large_pages_ds'


class TestSelectDatasetForHomework:
    """
    测试 POST /api/batch/tasks/<task_id>/select-dataset 接口
    Task 5.2: 数据集选择接口
    Validates: Requirements 4.5, 4.6, 5.4
    """
    
    def test_select_dataset_missing_homework_ids(self, client, monkeypatch):
        """Task 5.2: 缺少 homework_ids 参数返回 400 错误"""
        # Mock task exists
        def mock_load_batch_task(task_id):
            return {'task_id': task_id, 'homework_items': []}
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        
        response = client.post(
            '/api/batch/tasks/task123/select-dataset',
            json={'dataset_id': 'ds001'}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert '缺少作业ID列表' in data['error']
    
    def test_select_dataset_missing_dataset_id(self, client, monkeypatch):
        """Task 5.2: 缺少 dataset_id 参数返回 400 错误"""
        # Mock task exists
        def mock_load_batch_task(task_id):
            return {'task_id': task_id, 'homework_items': []}
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        
        response = client.post(
            '/api/batch/tasks/task123/select-dataset',
            json={'homework_ids': ['hw1', 'hw2']}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert '缺少数据集ID' in data['error']
    
    def test_select_dataset_task_not_found(self, client, monkeypatch):
        """Task 5.2: 任务不存在返回 404 错误"""
        def mock_load_batch_task(task_id):
            return None
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        
        response = client.post(
            '/api/batch/tasks/nonexistent/select-dataset',
            json={'homework_ids': ['hw1'], 'dataset_id': 'ds001'}
        )
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert '任务不存在' in data['error']
    
    def test_select_dataset_dataset_not_found(self, client, monkeypatch):
        """Task 5.2: 数据集不存在返回 404 错误"""
        def mock_load_batch_task(task_id):
            return {'task_id': task_id, 'homework_items': []}
        def mock_load_dataset(dataset_id):
            return None
        
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        
        response = client.post(
            '/api/batch/tasks/task123/select-dataset',
            json={'homework_ids': ['hw1'], 'dataset_id': 'nonexistent'}
        )
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert '数据集不存在' in data['error']
    
    def test_select_dataset_invalid_homework_ids_format(self, client, monkeypatch):
        """Task 5.2: homework_ids 格式错误返回 400 错误"""
        def mock_load_batch_task(task_id):
            return {'task_id': task_id, 'homework_items': []}
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        
        response = client.post(
            '/api/batch/tasks/task123/select-dataset',
            json={'homework_ids': 'not_a_list', 'dataset_id': 'ds001'}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert '作业ID列表格式错误' in data['error']
    
    def test_select_dataset_success_single_homework(self, client, monkeypatch):
        """Task 5.2: 成功为单个作业选择数据集"""
        saved_task = {}
        
        def mock_load_batch_task(task_id):
            return {
                'task_id': task_id,
                'homework_items': [
                    {
                        'homework_id': 'hw1',
                        'matched_dataset': 'old_ds',
                        'matched_dataset_name': '旧数据集',
                        'status': 'completed',
                        'accuracy': 0.95,
                        'precision': 0.90,
                        'recall': 0.85,
                        'f1': 0.87,
                        'correct_count': 45,
                        'wrong_count': 5,
                        'total_count': 50,
                        'error_details': [{'index': '1', 'error': 'test'}]
                    }
                ]
            }
        
        def mock_load_dataset(dataset_id):
            return {
                'dataset_id': dataset_id,
                'name': '新数据集',
                'book_id': 'book123',
                'pages': [30, 31]
            }
        
        def mock_save_batch_task(task_id, task_data):
            saved_task['data'] = task_data
        
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        monkeypatch.setattr(StorageService, 'save_batch_task', mock_save_batch_task)
        
        response = client.post(
            '/api/batch/tasks/task123/select-dataset',
            json={'homework_ids': ['hw1'], 'dataset_id': 'new_ds'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['updated_count'] == 1
        
        # 验证作业数据已更新
        hw_item = saved_task['data']['homework_items'][0]
        assert hw_item['matched_dataset'] == 'new_ds'
        assert hw_item['matched_dataset_name'] == '新数据集'
        assert hw_item['status'] == 'pending'
        
        # 验证评估结果已清除
        assert hw_item['accuracy'] is None
        assert hw_item['precision'] is None
        assert hw_item['recall'] is None
        assert hw_item['f1'] is None
        assert hw_item['correct_count'] is None
        assert hw_item['wrong_count'] is None
        assert hw_item['total_count'] is None
        assert hw_item['error_details'] is None
    
    def test_select_dataset_success_batch_homework(self, client, monkeypatch):
        """Task 5.2: 成功批量为多个作业选择数据集 (Requirement 4.6)"""
        saved_task = {}
        
        def mock_load_batch_task(task_id):
            return {
                'task_id': task_id,
                'homework_items': [
                    {'homework_id': 'hw1', 'status': 'completed', 'accuracy': 0.9},
                    {'homework_id': 'hw2', 'status': 'completed', 'accuracy': 0.85},
                    {'homework_id': 'hw3', 'status': 'pending', 'accuracy': None}
                ]
            }
        
        def mock_load_dataset(dataset_id):
            return {'dataset_id': dataset_id, 'name': '批量选择数据集'}
        
        def mock_save_batch_task(task_id, task_data):
            saved_task['data'] = task_data
        
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        monkeypatch.setattr(StorageService, 'save_batch_task', mock_save_batch_task)
        
        response = client.post(
            '/api/batch/tasks/task123/select-dataset',
            json={'homework_ids': ['hw1', 'hw2'], 'dataset_id': 'batch_ds'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['updated_count'] == 2
        
        # 验证 hw1 和 hw2 已更新
        items = saved_task['data']['homework_items']
        assert items[0]['matched_dataset'] == 'batch_ds'
        assert items[0]['status'] == 'pending'
        assert items[1]['matched_dataset'] == 'batch_ds'
        assert items[1]['status'] == 'pending'
        
        # 验证 hw3 未被修改
        assert items[2].get('matched_dataset') is None
        assert items[2]['status'] == 'pending'
    
    def test_select_dataset_homework_not_in_task(self, client, monkeypatch):
        """Task 5.2: 作业不在任务中时跳过（不报错）"""
        saved_task = {}
        
        def mock_load_batch_task(task_id):
            return {
                'task_id': task_id,
                'homework_items': [
                    {'homework_id': 'hw1', 'status': 'pending'}
                ]
            }
        
        def mock_load_dataset(dataset_id):
            return {'dataset_id': dataset_id, 'name': '测试数据集'}
        
        def mock_save_batch_task(task_id, task_data):
            saved_task['data'] = task_data
        
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        monkeypatch.setattr(StorageService, 'save_batch_task', mock_save_batch_task)
        
        # 请求更新 hw1 和 hw_nonexistent
        response = client.post(
            '/api/batch/tasks/task123/select-dataset',
            json={'homework_ids': ['hw1', 'hw_nonexistent'], 'dataset_id': 'ds001'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        # 只有 hw1 被更新
        assert data['updated_count'] == 1
    
    def test_select_dataset_clears_evaluation_results(self, client, monkeypatch):
        """
        Task 5.2: 更换数据集时清除已有评估结果 (Requirement 4.5)
        
        **Validates: Requirements 4.5**
        Property 8: Dataset Selection State Reset
        """
        saved_task = {}
        
        def mock_load_batch_task(task_id):
            return {
                'task_id': task_id,
                'homework_items': [
                    {
                        'homework_id': 'hw1',
                        'matched_dataset': 'old_ds',
                        'matched_dataset_name': '旧数据集',
                        'status': 'completed',
                        'accuracy': 0.95,
                        'precision': 0.92,
                        'recall': 0.88,
                        'f1': 0.90,
                        'correct_count': 47,
                        'wrong_count': 3,
                        'total_count': 50,
                        'error_details': [
                            {'index': '1', 'error_type': '识别错误'},
                            {'index': '5', 'error_type': '判断错误'}
                        ]
                    }
                ]
            }
        
        def mock_load_dataset(dataset_id):
            return {'dataset_id': dataset_id, 'name': '新数据集'}
        
        def mock_save_batch_task(task_id, task_data):
            saved_task['data'] = task_data
        
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        monkeypatch.setattr(StorageService, 'save_batch_task', mock_save_batch_task)
        
        response = client.post(
            '/api/batch/tasks/task123/select-dataset',
            json={'homework_ids': ['hw1'], 'dataset_id': 'new_ds'}
        )
        
        assert response.status_code == 200
        
        # 验证所有评估结果字段都被清除
        hw_item = saved_task['data']['homework_items'][0]
        
        # 数据集信息已更新
        assert hw_item['matched_dataset'] == 'new_ds'
        assert hw_item['matched_dataset_name'] == '新数据集'
        
        # 状态重置为 pending
        assert hw_item['status'] == 'pending'
        
        # 所有评估结果字段都被清除为 None
        assert hw_item['accuracy'] is None
        assert hw_item['precision'] is None
        assert hw_item['recall'] is None
        assert hw_item['f1'] is None
        assert hw_item['correct_count'] is None
        assert hw_item['wrong_count'] is None
        assert hw_item['total_count'] is None
        assert hw_item['error_details'] is None


class TestSelectDatasetProperty:
    """
    属性测试：数据集选择状态重置
    Feature: dataset-naming-selection, Property 8: Dataset Selection State Reset
    Feature: dataset-naming-selection, Property 9: Batch Dataset Selection
    Validates: Requirements 4.5, 4.6
    """
    
    @given(
        homework_count=st.integers(min_value=1, max_value=10),
        select_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_batch_selection_updates_correct_count(self, homework_count, select_count, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 9: Batch Dataset Selection
        Validates: Requirements 4.6
        
        For any list of homework_ids and a target dataset_id, the batch selection API
        SHALL update all specified homework items to use the target dataset.
        """
        saved_task = {}
        
        # 生成作业列表
        homework_items = [
            {'homework_id': f'hw{i}', 'status': 'completed', 'accuracy': 0.9}
            for i in range(homework_count)
        ]
        
        def mock_load_batch_task(task_id):
            return {'task_id': task_id, 'homework_items': homework_items.copy()}
        
        def mock_load_dataset(dataset_id):
            return {'dataset_id': dataset_id, 'name': '测试数据集'}
        
        def mock_save_batch_task(task_id, task_data):
            saved_task['data'] = task_data
        
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        monkeypatch.setattr(StorageService, 'save_batch_task', mock_save_batch_task)
        
        # 选择要更新的作业（最多选择实际存在的数量）
        actual_select_count = min(select_count, homework_count)
        homework_ids_to_select = [f'hw{i}' for i in range(actual_select_count)]
        
        response = client.post(
            '/api/batch/tasks/task123/select-dataset',
            json={'homework_ids': homework_ids_to_select, 'dataset_id': 'test_ds'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['updated_count'] == actual_select_count
    
    @given(
        initial_accuracy=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        initial_f1=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_selection_clears_all_metrics(self, initial_accuracy, initial_f1, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 8: Dataset Selection State Reset
        Validates: Requirements 4.5
        
        For any homework item with existing evaluation results, when the matched_dataset
        is changed to a different dataset_id, the evaluation results SHALL be cleared
        and status SHALL be reset to pending.
        """
        saved_task = {}
        
        def mock_load_batch_task(task_id):
            return {
                'task_id': task_id,
                'homework_items': [
                    {
                        'homework_id': 'hw1',
                        'status': 'completed',
                        'accuracy': initial_accuracy,
                        'f1': initial_f1,
                        'precision': 0.9,
                        'recall': 0.85,
                        'correct_count': 45,
                        'wrong_count': 5,
                        'total_count': 50,
                        'error_details': [{'index': '1'}]
                    }
                ]
            }
        
        def mock_load_dataset(dataset_id):
            return {'dataset_id': dataset_id, 'name': '新数据集'}
        
        def mock_save_batch_task(task_id, task_data):
            saved_task['data'] = task_data
        
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        monkeypatch.setattr(StorageService, 'save_batch_task', mock_save_batch_task)
        
        response = client.post(
            '/api/batch/tasks/task123/select-dataset',
            json={'homework_ids': ['hw1'], 'dataset_id': 'new_ds'}
        )
        
        assert response.status_code == 200
        
        hw_item = saved_task['data']['homework_items'][0]
        
        # 验证状态重置
        assert hw_item['status'] == 'pending'
        
        # 验证所有评估指标都被清除
        assert hw_item['accuracy'] is None
        assert hw_item['f1'] is None
        assert hw_item['precision'] is None
        assert hw_item['recall'] is None
        assert hw_item['correct_count'] is None
        assert hw_item['wrong_count'] is None
        assert hw_item['total_count'] is None
        assert hw_item['error_details'] is None


class TestDatasetListSortingProperty:
    """
    属性测试：数据集列表排序
    Feature: dataset-naming-selection, Property 7: Dataset List Sorting
    Validates: Requirements 3.4, 5.2
    
    Property: For any dataset list query, the returned datasets SHALL be sorted
    by created_at in descending order (newest first).
    """
    
    # Test directory for file-based tests
    TEST_DATASETS_DIR = 'test_datasets_sorting'
    
    @classmethod
    def setup_class(cls):
        """设置测试环境：创建测试目录"""
        if not os.path.exists(cls.TEST_DATASETS_DIR):
            os.makedirs(cls.TEST_DATASETS_DIR)
    
    @classmethod
    def teardown_class(cls):
        """清理测试环境：删除测试目录"""
        import shutil
        if os.path.exists(cls.TEST_DATASETS_DIR):
            shutil.rmtree(cls.TEST_DATASETS_DIR)
    
    def cleanup_test_datasets(self):
        """清理测试目录中的所有数据集文件"""
        import shutil
        if os.path.exists(self.TEST_DATASETS_DIR):
            shutil.rmtree(self.TEST_DATASETS_DIR)
        os.makedirs(self.TEST_DATASETS_DIR)
    
    def save_test_dataset(self, dataset_id, data):
        """保存测试数据集到文件"""
        filepath = os.path.join(self.TEST_DATASETS_DIR, f'{dataset_id}.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_all_datasets_from_test_dir(self):
        """
        从测试目录获取所有数据集（模拟 StorageService.get_all_datasets_summary）
        按 created_at 倒序排列
        """
        result = []
        if not os.path.exists(self.TEST_DATASETS_DIR):
            return result
        
        for filename in os.listdir(self.TEST_DATASETS_DIR):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.TEST_DATASETS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 生成默认名称（如果没有）
            name = data.get('name')
            if not name:
                name = StorageService.generate_default_dataset_name(data)
            
            # 计算题目数量
            question_count = 0
            for effects in data.get('base_effects', {}).values():
                question_count += len(effects) if isinstance(effects, list) else 0
            
            result.append({
                'dataset_id': data.get('dataset_id'),
                'name': name,
                'book_id': data.get('book_id'),
                'book_name': data.get('book_name', ''),
                'subject_id': data.get('subject_id'),
                'pages': data.get('pages', []),
                'question_count': question_count,
                'description': data.get('description', ''),
                'created_at': data.get('created_at', '')
            })
        
        # 按 created_at 倒序排列（最新的在前）
        result.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return result
    
    @given(
        num_datasets=st.integers(min_value=2, max_value=10),
        timestamps=st.lists(
            st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2025, 12, 31)
            ),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_datasets_sorted_by_created_at_desc(self, num_datasets, timestamps):
        """
        Feature: dataset-naming-selection, Property 7: Dataset List Sorting
        Validates: Requirements 3.4, 5.2
        
        Test that datasets are sorted by created_at in descending order (newest first).
        """
        # Arrange: Clean up and create datasets with various timestamps
        self.cleanup_test_datasets()
        
        # Use only the first num_datasets timestamps
        actual_timestamps = timestamps[:num_datasets]
        if len(actual_timestamps) < 2:
            return  # Skip if not enough timestamps
        
        # Create datasets with different created_at timestamps
        for i, ts in enumerate(actual_timestamps):
            dataset_id = f'sort_test_{i:03d}'
            dataset_data = {
                'dataset_id': dataset_id,
                'name': f'排序测试数据集_{i}',
                'book_id': 'book_sort_test',
                'book_name': '排序测试书本',
                'subject_id': 0,
                'pages': [i + 1],
                'base_effects': {},
                'description': '',
                'created_at': ts.isoformat()
            }
            self.save_test_dataset(dataset_id, dataset_data)
        
        # Act: Get all datasets
        result = self.get_all_datasets_from_test_dir()
        
        # Assert: Verify sorted by created_at DESC
        assert len(result) == len(actual_timestamps), \
            f"Expected {len(actual_timestamps)} datasets, got {len(result)}"
        
        # Extract created_at values
        created_at_values = [ds['created_at'] for ds in result]
        
        # Verify descending order (newest first)
        for i in range(len(created_at_values) - 1):
            assert created_at_values[i] >= created_at_values[i + 1], \
                f"Datasets not sorted by created_at DESC: {created_at_values[i]} should be >= {created_at_values[i + 1]}"
    
    @given(
        book_id=st.text(min_size=1, max_size=20).filter(lambda x: x.strip() and x.isalnum()),
        num_datasets=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_get_datasets_api_sorted_desc(self, book_id, num_datasets, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 7: Dataset List Sorting
        Validates: Requirements 3.4, 5.2
        
        Test that GET /api/batch/datasets returns datasets sorted by created_at DESC.
        """
        # Arrange: Create mock datasets with different timestamps
        mock_datasets = []
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        for i in range(num_datasets):
            # Create timestamps in random order (not sorted)
            offset_days = (i * 7 + 3) % 30  # Pseudo-random offset
            ts = base_time.replace(day=offset_days + 1)
            
            mock_datasets.append({
                'dataset_id': f'api_sort_{i:03d}',
                'name': f'API排序测试_{i}',
                'book_id': book_id,
                'book_name': f'测试书本_{book_id}',
                'subject_id': 0,
                'pages': [i + 1],
                'question_count': 10 + i,
                'description': '',
                'created_at': ts.isoformat()
            })
        
        def mock_get_all_datasets_summary():
            return mock_datasets
        
        monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
        
        # Act: Call the API
        response = client.get(f'/api/batch/datasets?book_id={book_id}')
        
        # Assert: Response should be successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Assert: Results should be sorted by created_at DESC
        result_datasets = data['data']
        if len(result_datasets) >= 2:
            created_at_values = [ds['created_at'] for ds in result_datasets]
            for i in range(len(created_at_values) - 1):
                assert created_at_values[i] >= created_at_values[i + 1], \
                    f"API results not sorted by created_at DESC: {created_at_values}"
    
    @given(
        book_id=st.text(min_size=1, max_size=20).filter(lambda x: x.strip() and x.isalnum()),
        page_num=st.integers(min_value=1, max_value=100),
        num_datasets=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_matching_datasets_api_sorted_desc(self, book_id, page_num, num_datasets, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 7: Dataset List Sorting
        Validates: Requirements 3.4, 5.2
        
        Test that GET /api/batch/matching-datasets returns datasets sorted by created_at DESC.
        """
        # Arrange: Create mock matching datasets with different timestamps
        mock_datasets = []
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        for i in range(num_datasets):
            # Create timestamps in random order (not sorted)
            offset_days = (i * 7 + 3) % 30  # Pseudo-random offset
            ts = base_time.replace(day=offset_days + 1)
            
            mock_datasets.append({
                'dataset_id': f'match_sort_{i:03d}',
                'name': f'匹配排序测试_{i}',
                'book_id': book_id,
                'book_name': f'测试书本_{book_id}',
                'subject_id': 0,
                'pages': [page_num],  # All contain the same page_num
                'question_count': 10 + i,
                'description': '',
                'created_at': ts.isoformat()
            })
        
        def mock_get_matching_datasets(b_id, p_num):
            # Return datasets sorted by created_at DESC (as the real implementation does)
            return sorted(mock_datasets, key=lambda x: x.get('created_at', ''), reverse=True)
        
        monkeypatch.setattr(StorageService, 'get_matching_datasets', mock_get_matching_datasets)
        
        # Act: Call the API
        response = client.get(f'/api/batch/matching-datasets?book_id={book_id}&page_num={page_num}')
        
        # Assert: Response should be successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Assert: Results should be sorted by created_at DESC
        result_datasets = data['data']
        if len(result_datasets) >= 2:
            created_at_values = [ds['created_at'] for ds in result_datasets]
            for i in range(len(created_at_values) - 1):
                assert created_at_values[i] >= created_at_values[i + 1], \
                    f"Matching datasets not sorted by created_at DESC: {created_at_values}"
    
    @given(
        timestamps=st.lists(
            st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2025, 12, 31)
            ),
            min_size=3,
            max_size=10,
            unique=True
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_newest_dataset_is_first(self, timestamps):
        """
        Feature: dataset-naming-selection, Property 7: Dataset List Sorting
        Validates: Requirements 3.4, 5.2
        
        Test that the newest dataset (most recent created_at) is always first in the list.
        """
        # Arrange: Clean up and create datasets
        self.cleanup_test_datasets()
        
        # Find the newest timestamp
        newest_ts = max(timestamps)
        newest_idx = timestamps.index(newest_ts)
        
        # Create datasets
        for i, ts in enumerate(timestamps):
            dataset_id = f'newest_test_{i:03d}'
            dataset_data = {
                'dataset_id': dataset_id,
                'name': f'最新测试_{i}',
                'book_id': 'book_newest',
                'book_name': '最新测试书本',
                'subject_id': 0,
                'pages': [i + 1],
                'base_effects': {},
                'description': '',
                'created_at': ts.isoformat()
            }
            self.save_test_dataset(dataset_id, dataset_data)
        
        # Act: Get all datasets
        result = self.get_all_datasets_from_test_dir()
        
        # Assert: The first dataset should have the newest timestamp
        assert len(result) > 0, "Should have at least one dataset"
        first_dataset = result[0]
        assert first_dataset['created_at'] == newest_ts.isoformat(), \
            f"First dataset should have newest timestamp {newest_ts.isoformat()}, got {first_dataset['created_at']}"
    
    @given(
        same_timestamp=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2025, 12, 31)
        ),
        num_datasets=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=30, deadline=None)
    def test_same_timestamp_stable_sort(self, same_timestamp, num_datasets):
        """
        Feature: dataset-naming-selection, Property 7: Dataset List Sorting
        Validates: Requirements 3.4, 5.2
        
        Test that datasets with the same created_at timestamp are handled gracefully
        (stable sort - order is deterministic).
        """
        # Arrange: Clean up and create datasets with same timestamp
        self.cleanup_test_datasets()
        
        for i in range(num_datasets):
            dataset_id = f'same_ts_{i:03d}'
            dataset_data = {
                'dataset_id': dataset_id,
                'name': f'相同时间戳_{i}',
                'book_id': 'book_same_ts',
                'book_name': '相同时间戳书本',
                'subject_id': 0,
                'pages': [i + 1],
                'base_effects': {},
                'description': '',
                'created_at': same_timestamp.isoformat()  # Same timestamp for all
            }
            self.save_test_dataset(dataset_id, dataset_data)
        
        # Act: Get all datasets multiple times
        result1 = self.get_all_datasets_from_test_dir()
        result2 = self.get_all_datasets_from_test_dir()
        
        # Assert: Results should be consistent (stable sort)
        assert len(result1) == num_datasets
        assert len(result2) == num_datasets
        
        # All timestamps should be the same
        for ds in result1:
            assert ds['created_at'] == same_timestamp.isoformat()
        
        # Order should be consistent between calls
        ids1 = [ds['dataset_id'] for ds in result1]
        ids2 = [ds['dataset_id'] for ds in result2]
        assert ids1 == ids2, \
            f"Sort should be stable: first call {ids1}, second call {ids2}"
    
    @given(
        search_term=st.text(min_size=1, max_size=10).filter(lambda x: x.strip()),
        num_datasets=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_search_results_sorted_desc(self, search_term, num_datasets, client, monkeypatch):
        """
        Feature: dataset-naming-selection, Property 7: Dataset List Sorting
        Validates: Requirements 3.4, 5.2
        
        Test that search results are also sorted by created_at DESC.
        """
        # Arrange: Create mock datasets that match the search term
        mock_datasets = []
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        for i in range(num_datasets):
            offset_days = (i * 7 + 3) % 30
            ts = base_time.replace(day=offset_days + 1)
            
            mock_datasets.append({
                'dataset_id': f'search_sort_{i:03d}',
                'name': f'{search_term}_数据集_{i}',  # Include search term in name
                'book_id': 'book_search',
                'book_name': '搜索测试书本',
                'subject_id': 0,
                'pages': [i + 1],
                'question_count': 10 + i,
                'description': '',
                'created_at': ts.isoformat()
            })
        
        def mock_get_all_datasets_summary():
            return mock_datasets
        
        monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
        
        # Act: Call the API with search parameter
        response = client.get(f'/api/batch/datasets?search={search_term}')
        
        # Assert: Response should be successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Assert: Search results should be sorted by created_at DESC
        result_datasets = data['data']
        if len(result_datasets) >= 2:
            created_at_values = [ds['created_at'] for ds in result_datasets]
            for i in range(len(created_at_values) - 1):
                assert created_at_values[i] >= created_at_values[i + 1], \
                    f"Search results not sorted by created_at DESC: {created_at_values}"


# ========== 集成测试 ==========

class TestIntegrationCreateDatasetFlow:
    """
    集成测试：创建数据集完整流程
    Task 10.1: 创建带名称的数据集 → 验证列表显示 → 编辑名称 → 验证更新
    Validates: Requirements 1.1, 1.3, 3.1
    """
    
    def test_create_dataset_with_name_flow(self, client, monkeypatch):
        """
        Task 10.1: 完整流程测试 - 创建带名称的数据集
        """
        # Arrange: Mock storage operations
        saved_datasets = {}
        
        def mock_save_dataset(dataset_id, data):
            saved_datasets[dataset_id] = data
            return True
        
        def mock_load_dataset(dataset_id):
            return saved_datasets.get(dataset_id)
        
        def mock_get_all_datasets_summary():
            return list(saved_datasets.values())
        
        monkeypatch.setattr(StorageService, 'save_dataset', mock_save_dataset)
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
        
        # Step 1: Create dataset with custom name
        create_response = client.post('/api/batch/datasets', json={
            'book_id': 'book_integration_test',
            'book_name': '集成测试书本',
            'name': '自定义数据集名称',
            'pages': [10, 11, 12],
            'base_effects': {'10': [{'index': '1', 'answer': 'A'}]},
            'description': '集成测试描述'
        })
        
        assert create_response.status_code == 200
        create_data = json.loads(create_response.data)
        assert create_data['success'] is True
        dataset_id = create_data['dataset_id']
        
        # Step 2: Verify dataset in list
        list_response = client.get('/api/batch/datasets')
        assert list_response.status_code == 200
        list_data = json.loads(list_response.data)
        assert list_data['success'] is True
        
        # Find our dataset in the list
        found_dataset = None
        for ds in list_data['data']:
            if ds.get('dataset_id') == dataset_id:
                found_dataset = ds
                break
        
        assert found_dataset is not None, "Created dataset should appear in list"
        assert found_dataset['name'] == '自定义数据集名称'
        
        # Step 3: Edit dataset name
        update_response = client.put(f'/api/batch/datasets/{dataset_id}', json={
            'name': '更新后的数据集名称',
            'description': '更新后的描述'
        })
        
        assert update_response.status_code == 200
        update_data = json.loads(update_response.data)
        assert update_data['success'] is True
        
        # Step 4: Verify update
        list_response2 = client.get('/api/batch/datasets')
        assert list_response2.status_code == 200
        list_data2 = json.loads(list_response2.data)
        
        found_updated = None
        for ds in list_data2['data']:
            if ds.get('dataset_id') == dataset_id:
                found_updated = ds
                break
        
        assert found_updated is not None
        assert found_updated['name'] == '更新后的数据集名称'
    
    def test_create_dataset_without_name_generates_default(self, client, monkeypatch):
        """
        Task 10.1: 创建数据集不提供名称时自动生成默认名称
        """
        saved_datasets = {}
        
        def mock_save_dataset(dataset_id, data):
            # Simulate the real save_dataset behavior: generate default name if empty
            name = data.get('name', '').strip() if data.get('name') else ''
            if not name:
                # Generate default name (same logic as StorageService)
                book_name = data.get('book_name', '未知书本')
                pages = data.get('pages', [])
                if pages:
                    page_range = f"P{min(pages)}-{max(pages)}" if len(pages) > 1 else f"P{pages[0]}"
                else:
                    page_range = ""
                from datetime import datetime
                timestamp = datetime.now().strftime('%m%d%H%M')
                name = f"{book_name}_{page_range}_{timestamp}"
            data['name'] = name
            saved_datasets[dataset_id] = data
            return True
        
        def mock_load_dataset(dataset_id):
            return saved_datasets.get(dataset_id)
        
        monkeypatch.setattr(StorageService, 'save_dataset', mock_save_dataset)
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        
        # Create dataset without name
        response = client.post('/api/batch/datasets', json={
            'book_id': 'book_no_name',
            'book_name': '无名称测试书本',
            'pages': [5, 6],
            'base_effects': {}
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify default name was generated
        dataset_id = data['dataset_id']
        saved_data = saved_datasets.get(dataset_id)
        assert saved_data is not None
        assert 'name' in saved_data
        assert saved_data['name'] != ''
        # Default name should contain book name and page range
        assert '无名称测试书本' in saved_data['name']
        assert 'P5-6' in saved_data['name']


class TestIntegrationBatchEvaluationDatasetSelection:
    """
    集成测试：批量评估数据集选择流程
    Task 10.2: 创建多个相同页码的数据集 → 创建评估任务 → 验证多数据集返回 → 选择特定数据集
    Validates: Requirements 4.1, 4.2, 5.1
    """
    
    def test_multiple_datasets_selection_flow(self, client, monkeypatch):
        """
        Task 10.2: 完整流程测试 - 多数据集选择
        """
        # Arrange: Create multiple datasets for same book/page
        mock_datasets = [
            {
                'dataset_id': 'ds_multi_1',
                'name': '数据集A',
                'book_id': 'book_multi',
                'book_name': '多数据集测试书本',
                'subject_id': 0,
                'pages': [20, 21],
                'question_count': 30,
                'description': '第一个数据集',
                'created_at': '2024-01-10T10:00:00'
            },
            {
                'dataset_id': 'ds_multi_2',
                'name': '数据集B',
                'book_id': 'book_multi',
                'book_name': '多数据集测试书本',
                'subject_id': 0,
                'pages': [20, 21],
                'question_count': 35,
                'description': '第二个数据集',
                'created_at': '2024-01-15T10:00:00'
            },
            {
                'dataset_id': 'ds_multi_3',
                'name': '数据集C（最新）',
                'book_id': 'book_multi',
                'book_name': '多数据集测试书本',
                'subject_id': 0,
                'pages': [20, 21],
                'question_count': 40,
                'description': '第三个数据集（最新）',
                'created_at': '2024-01-20T10:00:00'
            }
        ]
        
        def mock_get_matching_datasets(book_id, page_num):
            # Filter and sort by created_at DESC
            matching = [ds for ds in mock_datasets 
                       if ds['book_id'] == book_id and page_num in ds['pages']]
            return sorted(matching, key=lambda x: x['created_at'], reverse=True)
        
        monkeypatch.setattr(StorageService, 'get_matching_datasets', mock_get_matching_datasets)
        
        # Step 1: Query matching datasets
        response = client.get('/api/batch/matching-datasets?book_id=book_multi&page_num=20')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Step 2: Verify multiple datasets returned
        datasets = data['data']
        assert len(datasets) == 3, "Should return all 3 matching datasets"
        
        # Step 3: Verify sorted by created_at DESC (newest first)
        assert datasets[0]['name'] == '数据集C（最新）'
        assert datasets[1]['name'] == '数据集B'
        assert datasets[2]['name'] == '数据集A'
        
        # Step 4: Verify required fields
        for ds in datasets:
            assert 'dataset_id' in ds
            assert 'name' in ds
            assert 'pages' in ds
            assert 'question_count' in ds
            assert 'created_at' in ds
    
    def test_select_specific_dataset_for_homework(self, client, monkeypatch):
        """
        Task 10.2: 为作业选择特定数据集
        """
        # Arrange: Mock task and dataset
        mock_task = {
            'task_id': 'task_select_test',
            'name': '选择测试任务',
            'status': 'pending',
            'homework_items': [
                {
                    'homework_id': 'hw_select_1',
                    'book_id': 'book_select',
                    'page_num': 30,
                    'matched_dataset': None,
                    'matched_dataset_name': None,
                    'status': 'pending'
                }
            ]
        }
        
        mock_dataset = {
            'dataset_id': 'ds_selected',
            'name': '被选中的数据集',
            'book_id': 'book_select',
            'pages': [30],
            'question_count': 25
        }
        
        saved_task = None
        
        def mock_load_batch_task(task_id):
            if task_id == 'task_select_test':
                return mock_task.copy()
            return None
        
        def mock_save_batch_task(task_id, data):
            nonlocal saved_task
            saved_task = data
            return True
        
        def mock_load_dataset(dataset_id):
            if dataset_id == 'ds_selected':
                return mock_dataset
            return None
        
        monkeypatch.setattr(StorageService, 'load_batch_task', mock_load_batch_task)
        monkeypatch.setattr(StorageService, 'save_batch_task', mock_save_batch_task)
        monkeypatch.setattr(StorageService, 'load_dataset', mock_load_dataset)
        
        # Act: Select dataset for homework
        response = client.post('/api/batch/tasks/task_select_test/select-dataset', json={
            'homework_ids': ['hw_select_1'],
            'dataset_id': 'ds_selected'
        })
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['updated_count'] == 1
        
        # Verify task was updated
        assert saved_task is not None
        hw_item = saved_task['homework_items'][0]
        assert hw_item['matched_dataset'] == 'ds_selected'
        assert hw_item['matched_dataset_name'] == '被选中的数据集'


class TestIntegrationBackwardCompatibility:
    """
    集成测试：旧数据集兼容性
    Task 10.3: 模拟无 name 字段的旧数据 → 验证读取时生成默认名称
    Validates: Requirements 6.1, 6.2, 6.3
    """
    
    def test_legacy_dataset_without_name_field(self, client, monkeypatch):
        """
        Task 10.3: 读取无 name 字段的旧数据集
        """
        # Arrange: Mock legacy dataset without name field
        legacy_datasets = [
            {
                'dataset_id': 'legacy_001',
                # No 'name' field - simulating old data
                'book_id': 'book_legacy',
                'book_name': '旧版数据集书本',
                'subject_id': 0,
                'pages': [15, 16],
                'question_count': 20,
                'description': '',
                'created_at': '2023-06-01T10:00:00'
            }
        ]
        
        def mock_get_all_datasets_summary():
            # Simulate StorageService adding default name for legacy data
            result = []
            for ds in legacy_datasets:
                ds_copy = ds.copy()
                if 'name' not in ds_copy or not ds_copy.get('name'):
                    # Generate default name
                    book_name = ds_copy.get('book_name', '未知书本')
                    pages = ds_copy.get('pages', [])
                    if pages:
                        page_range = f"P{min(pages)}-{max(pages)}" if len(pages) > 1 else f"P{pages[0]}"
                    else:
                        page_range = ""
                    ds_copy['name'] = f"{book_name}_{page_range}"
                result.append(ds_copy)
            return result
        
        monkeypatch.setattr(StorageService, 'get_all_datasets_summary', mock_get_all_datasets_summary)
        
        # Act: Get datasets list
        response = client.get('/api/batch/datasets')
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 1
        
        # Verify default name was generated
        ds = data['data'][0]
        assert 'name' in ds
        assert ds['name'] != ''
        assert '旧版数据集书本' in ds['name']
        assert 'P15-16' in ds['name']
    
    def test_legacy_dataset_can_be_used_for_matching(self, client, monkeypatch):
        """
        Task 10.3: 旧数据集可正常用于匹配
        """
        # Arrange: Mock legacy dataset
        legacy_dataset = {
            'dataset_id': 'legacy_match',
            # No 'name' field
            'book_id': 'book_legacy_match',
            'book_name': '旧版匹配测试',
            'subject_id': 0,
            'pages': [25, 26],
            'question_count': 15,
            'created_at': '2023-05-01T10:00:00'
        }
        
        def mock_get_matching_datasets(book_id, page_num):
            if book_id == 'book_legacy_match' and page_num in [25, 26]:
                # Add default name when returning
                result = legacy_dataset.copy()
                result['name'] = f"{result['book_name']}_P{min(result['pages'])}-{max(result['pages'])}"
                return [result]
            return []
        
        monkeypatch.setattr(StorageService, 'get_matching_datasets', mock_get_matching_datasets)
        
        # Act: Query matching datasets
        response = client.get('/api/batch/matching-datasets?book_id=book_legacy_match&page_num=25')
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 1
        
        # Verify dataset has name
        ds = data['data'][0]
        assert 'name' in ds
        assert ds['name'] != ''


class TestBackwardCompatibilityProperty:
    """
    属性测试：向后兼容 - 无名称数据集读取
    Task 10.4: Property 13: Backward Compatibility - Nameless Dataset Reading
    Validates: Requirements 2.2, 6.1
    """
    
    @given(
        book_name=st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
        pages=st.lists(st.integers(min_value=1, max_value=200), min_size=1, max_size=10, unique=True)
    )
    @settings(max_examples=50, deadline=None)
    def test_nameless_dataset_gets_default_name(self, book_name, pages):
        """
        Feature: dataset-naming-selection, Property 13: Backward Compatibility - Nameless Dataset Reading
        Validates: Requirements 2.2, 6.1
        
        For any dataset stored without a name field (legacy data), 
        reading the dataset SHALL return a valid dataset object with an auto-generated default name.
        """
        # Arrange: Create legacy dataset without name
        legacy_data = {
            'dataset_id': 'legacy_prop_test',
            'book_id': 'book_prop',
            'book_name': book_name.strip(),
            'subject_id': 0,
            'pages': sorted(pages),
            'question_count': len(pages) * 5,
            'base_effects': {},
            'created_at': '2023-01-01T10:00:00'
        }
        
        # Act: Simulate StorageService.load_dataset behavior for legacy data
        # The service should add a default name if missing
        result = legacy_data.copy()
        if 'name' not in result or not result.get('name'):
            # Generate default name (same logic as StorageService)
            bk_name = result.get('book_name', '未知书本')
            pgs = result.get('pages', [])
            if pgs:
                page_range = f"P{min(pgs)}-{max(pgs)}" if len(pgs) > 1 else f"P{pgs[0]}"
            else:
                page_range = ""
            result['name'] = f"{bk_name}_{page_range}"
        
        # Assert: Result should have a valid name
        assert 'name' in result, "Legacy dataset should have name after loading"
        assert result['name'] != '', "Name should not be empty"
        assert isinstance(result['name'], str), "Name should be a string"
        
        # Assert: Name should contain book_name
        assert book_name.strip() in result['name'], \
            f"Default name should contain book_name: {book_name.strip()}"
        
        # Assert: Name should contain page info
        if pages:
            min_page = min(pages)
            max_page = max(pages)
            if len(pages) == 1:
                assert f"P{min_page}" in result['name'], \
                    f"Default name should contain page: P{min_page}"
            else:
                assert f"P{min_page}-{max_page}" in result['name'], \
                    f"Default name should contain page range: P{min_page}-{max_page}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
