# DataSource Engine - 外部数据源相关性判断和使用决策 Agent

## 概述

DataSource Engine 是一个独立的 AI Agent，专门用于：
1. **判断外部数据源与问题的相关性**：分析提前抓取的数据是否与用户问题相关
2. **决定如何使用这些数据**：根据相关性分析结果，制定数据使用策略，包括如何传递给其他 Agent

## 功能特点

- ✅ **智能相关性判断**：使用 LLM 分析数据源与问题的相关性，给出 0-1 的评分
- ✅ **多数据源支持**：支持同时分析多个数据源（JSON文件、API、数据库等）
- ✅ **使用策略生成**：自动生成数据使用策略，包括数据优先级和处理方式
- ✅ **Agent 集成建议**：根据数据特点，建议传递给哪些 Agent（Insight Agent、Media Agent、Query Agent、Report Agent）
- ✅ **状态管理**：完整的状态保存和加载功能

## 架构设计

```
DataSourceEngine/
├── agent.py              # Agent主类
├── llms/                 # LLM客户端
│   └── base.py
├── nodes/                # 处理节点
│   ├── base_node.py
│   ├── relevance_node.py    # 相关性分析节点
│   └── strategy_node.py     # 使用策略节点
├── tools/                # 工具集
│   └── data_loader.py       # 数据加载器
├── state/                # 状态管理
│   └── state.py
├── prompts/              # 提示词模板
│   └── prompts.py
└── utils/               # 工具函数
    └── config.py            # 配置管理
```

## 快速开始

### 1. 环境配置

在 `.env` 文件中添加以下配置：

```bash
# DataSource Engine LLM配置
DATA_SOURCE_ENGINE_API_KEY=your_api_key
DATA_SOURCE_ENGINE_MODEL_NAME=your_model_name
DATA_SOURCE_ENGINE_BASE_URL=your_base_url  # 可选

# 相关性阈值（0-1，默认0.6）
MAX_RELEVANCE_SCORE_THRESHOLD=0.6

# 用于分析的最大数据样本数
MAX_DATA_SAMPLES_FOR_ANALYSIS=50

# 输出目录
OUTPUT_DIR=data_source_reports
```

### 2. 基本使用

```python
from DataSourceEngine import DataSourceAgent

# 创建 Agent
agent = DataSourceAgent()

# 添加数据源（JSON文件）
agent.add_data_source(
    source_id="crawl_data_1",
    source_type="json_file",
    source_path="/path/to/your/data.json",
    metadata={"description": "爬取的数据"}
)

# 执行相关性分析
query = "分析相关的舆情信息"
result = agent.analyze_relevance(query, save_results=True)

# 查看结果
print(f"相关数据源数: {result['relevant_sources']}")
print(f"使用策略: {result['usage_strategy']}")

# 获取相关数据源ID列表
relevant_sources = agent.get_relevant_sources()
```

### 3. 完整示例

参考 `example_data_source_analysis.py` 文件查看完整示例。

## API 文档

### DataSourceAgent

#### `__init__(config: Optional[Settings] = None)`
初始化 DataSource Agent。

#### `add_data_source(source_id: str, source_type: str, source_path: str, metadata: Optional[Dict[str, Any]] = None)`
添加数据源。

**参数：**
- `source_id`: 数据源唯一标识
- `source_type`: 数据源类型（目前支持 `json_file`）
- `source_path`: 数据源路径
- `metadata`: 可选的元数据字典

#### `analyze_relevance(query: str, save_results: bool = True) -> Dict[str, Any]`
分析所有数据源与问题的相关性。

**参数：**
- `query`: 用户查询问题
- `save_results`: 是否保存结果到文件

**返回：**
```python
{
    "query": "用户查询",
    "total_sources": 2,
    "relevant_sources": 1,
    "relevance_analyses": [
        {
            "source_id": "crawl_data_1",
            "relevance_score": 0.85,
            "is_relevant": True,
            "reasoning": "相关性判断理由",
            "key_matches": ["关键词1", "关键词2"],
            "usage_recommendation": "使用建议"
        }
    ],
    "usage_strategy": "数据使用策略",
    "relevant_source_ids": ["crawl_data_1"]
}
```

#### `get_relevant_sources() -> List[str]`
获取相关数据源ID列表。

#### `get_relevance_analysis(source_id: str) -> Optional[RelevanceAnalysis]`
获取指定数据源的相关性分析结果。

#### `get_usage_strategy() -> str`
获取数据使用策略。

## 相关性评分标准

- **0.8-1.0**: 高度相关，数据直接回答问题的核心内容
- **0.6-0.8**: 中度相关，数据部分相关，有一定参考价值
- **0.4-0.6**: 低度相关，数据与问题有间接关联
- **0.0-0.4**: 不相关，数据与问题无关

默认阈值：0.6（可通过 `MAX_RELEVANCE_SCORE_THRESHOLD` 配置）

## 与其他 Agent 的集成

DataSource Agent 可以与其他 Agent 配合使用：

- **Insight Agent**: 适合结构化数据、数据库查询
- **Media Agent**: 适合多模态内容（图片、视频）
- **Query Agent**: 适合需要进一步搜索的信息
- **Report Agent**: 适合需要生成报告的场景

使用策略会自动建议将相关数据传递给合适的 Agent。

## 状态管理

Agent 支持状态保存和加载：

```python
# 保存状态
agent.save_state("state.json")

# 加载状态
agent.load_state("state.json")
```

## 输出文件

分析结果会保存到配置的输出目录（默认：`data_source_reports`）：

- `data_source_state_{query}_{timestamp}.json`: 完整状态文件
- `data_source_summary_{query}_{timestamp}.json`: 分析摘要

## 注意事项

1. 确保 LLM API 配置正确
2. JSON 文件需要是有效的 JSON 格式
3. 大数据文件会自动采样（默认最多 50 个样本）用于相关性分析
4. 数据文本会被截断到 3000 字符以避免 token 过多

## 未来扩展

- [ ] 支持更多数据源类型（API、数据库等）
- [ ] 支持数据预处理和过滤
- [ ] 支持批量数据源添加
- [ ] 支持自定义相关性判断标准
- [ ] 支持数据源优先级设置

