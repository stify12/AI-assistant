# 编码规范

## 开发准则

| 原则 | 实践 |
|------|------|
| 接口处理 | 先查文档，不猜接口 |
| 执行确认 | 先问清边界，不糊涂干活 |
| 业务理解 | 先对齐需求，不臆测 |
| 代码复用 | 先找现有，不造轮子 |
| 质量保证 | 先写用例，不跳验证 |
| 架构规范 | 先守红线，不乱动 |
| 诚信沟通 | 坦白不会，不装懂 |
| 代码修改 | 谨慎评估，不盲改 |

---

## 设计原则

- KISS：追求极致简洁，避免不必要的复杂性
- YAGNI：仅实现当前所需，抵制过度设计
- DRY：消除重复模式，提升复用性
- 向后兼容：不破坏现有功能

---

## Python 规范

```python
def func(param):
    """一句话说明功能"""
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

## JavaScript 规范

```javascript
// API 调用统一封装
async function apiCall(url, options = {}) {
    const res = await fetch(url, {
        headers: {'Content-Type': 'application/json'},
        ...options
    });
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

## 命名规范

| Python | JavaScript |
|--------|------------|
| snake_case 函数/变量 | camelCase 函数/变量 |
| PascalCase 类 | UPPER_SNAKE 常量 |
| UPPER_SNAKE 常量 | kebab-case CSS类 |

## API 返回格式

```python
# 成功
{'success': True, 'data': {...}}
{'success': True, 'data': {'items': [], 'total': 0, 'page': 1}}

# 失败
{'success': False, 'error': '错误信息'}
```

---

## 检查清单

- [ ] 有 docstring
- [ ] 参数验证
- [ ] 异常捕获 + 日志（print `[Module]` 前缀）
- [ ] SQL 参数化（禁止 f-string 拼接）
- [ ] 无硬编码密钥
- [ ] 复用现有服务（先查 services/ 目录）
- [ ] 边界情况处理
