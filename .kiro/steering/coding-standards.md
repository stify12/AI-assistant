# AI 编码规范

## 核心原则
- 命名清晰、结构自解释
- 假设输入不可信
- 最小改动

---

## Python

```python
# 函数必须有 docstring
def func(param):
    """说明"""
    if not param:
        return {'success': False, 'error': '参数为空'}
    try:
        return {'success': True, 'data': result}
    except Exception as e:
        print(f"[Module] 失败: {e}")
        return {'success': False, 'error': str(e)}

# SQL 参数化，禁止 f-string
sql = "SELECT * FROM t WHERE id = %s"
execute_query(sql, (id,))
```

## JavaScript

```javascript
// API 调用统一封装
async function apiCall(url, options = {}) {
    const res = await fetch(url, {headers: {'Content-Type': 'application/json'}, ...options});
    const result = await res.json();
    if (!result.success) throw new Error(result.error);
    return result.data;
}

// DOM 必须转义用户输入
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

## 命名

| Python | JavaScript |
|--------|------------|
| snake_case 函数/变量 | camelCase 函数/变量 |
| PascalCase 类 | UPPER_SNAKE 常量 |
| UPPER_SNAKE 常量 | kebab-case CSS类 |

## API 返回格式

```python
{'success': True, 'data': {...}}
{'success': True, 'data': {'items': [], 'total': 0, 'page': 1}}
{'success': False, 'error': '错误信息'}
```

## 检查清单
- [ ] 有 docstring
- [ ] 参数验证
- [ ] 异常捕获+日志
- [ ] SQL 参数化
- [ ] 无硬编码密钥
