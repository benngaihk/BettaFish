# Data Source 文件夹

这个文件夹用于存放 JSON 数据文件。

DataSource Agent 会自动扫描这个文件夹中的所有 JSON 文件，并根据用户查询选择合适的数据源进行分析。

**位置**: `DataSourceEngine/data_source/`

## 使用方法

1. 将 JSON 数据文件放入此文件夹
2. DataSource Agent 会自动发现并加载这些文件
3. Agent 会根据查询内容判断哪些数据源与问题相关

## 文件摘要和关键字功能

每次扫描文件时，系统会自动生成每个文件的摘要和关键字，并缓存到 `.summaries/` 文件夹中。这样可以：

- **快速预览**：无需加载完整文件就能了解文件内容
- **节省时间**：下次扫描时直接使用缓存，无需重新分析
- **智能匹配**：通过关键字快速判断文件是否与查询相关

### 查看文件摘要

运行以下命令查看所有文件的摘要和关键字：

```bash
python3 DataSourceEngine/view_data_source_summaries.py
```

或者使用 Python API：

```python
from DataSourceEngine import get_data_source_summaries

# 获取所有文件的摘要（使用缓存）
summaries = get_data_source_summaries()

# 查看每个文件的摘要信息
for summary in summaries:
    print(f"文件: {summary['file_name']}")
    print(f"关键字: {summary['keywords']}")
    print(f"简短描述: {summary['short_description']}")
```

### 强制重新生成摘要

如果文件已更新，可以强制重新生成摘要：

```python
from ForumEngine import get_data_source_summaries

# 强制重新生成所有摘要
summaries = get_data_source_summaries(force_regenerate=True)
```

## 文件格式

支持标准的 JSON 格式：
- JSON 对象：`{ "key": "value" }`
- JSON 数组：`[{ "item": 1 }, { "item": 2 }]`

## 注意事项

- 文件名应该具有描述性，便于识别数据内容
- 文件大小建议控制在合理范围内，以提高加载速度
- 确保 JSON 文件格式正确，否则可能无法加载
- 摘要缓存文件保存在 `.summaries/` 文件夹中，可以手动删除以强制重新生成

