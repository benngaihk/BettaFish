# EPRC 数据提取优化说明

## ✅ 已完成的优化

### 1. **动态列映射**
   - 不再硬编码列索引（cells[0], cells[1]等）
   - 根据表头动态识别列位置
   - 支持表格列顺序变化

### 2. **表头识别**
   - 成交排行榜：识别包含"排名"、"屋苑"、"成交"、"呎價"、"地區"的表头
   - 赚蚀分析：识别包含"地区"、"赚"、"蚀"、"宗"、"幅度"的表头

### 3. **列映射逻辑**

#### 成交排行榜列映射：
- `排名` / `rank` → `rank`
- `屋苑` / `estate` / `名稱` → `estate_name`
- `地區` / `region` / `district` → `region`
- `成交` + `宗` → `transaction_count`
- `最高` + `呎` / `price` → `highest_price`
- `最低` + `呎` / `price` → `lowest_price`
- `平均` + `呎` / `price` → `avg_price`

#### 赚蚀分析列映射：
- `地區` / `region` / `district` → `region`
- `代表性` / `物業` / `estate` / `屋苑` → `estate_name`
- `賺` + `宗` / `cases` → `profit_cases`
- `賺` + `幅度` / `range` → `profit_range`
- `蝕` + `宗` / `cases` → `loss_cases`
- `蝕` + `幅度` / `range` → `loss_range`

### 4. **调试日志**
   - 添加了 `utils.logger.debug()` 输出列映射和表头信息
   - 便于排查数据提取问题

## 🔍 问题分析

根据数据库中的数据，发现以下问题：

### eprc_profit_loss 表问题：
- `region` 列包含了类似 "嘉湖山莊(第02期)賞湖居(第03座) 中" 的数据
  - 这看起来是屋苑名称+期数+座数+层数，而不是地区
- `estate_name` 列似乎和 `region` 混在一起
- `profit_range` 显示数值如 458, 640（应该是幅度范围）
- `loss_range` 显示年份如 1996, 2002（应该是幅度范围）

### eprc_ranking 表问题：
- `estate_name` 列只有单个字母如 G, D, A, B（应该是完整的屋苑名称）
- `region` 列显示 "低"、"高"、"中"（这看起来是层数，而不是地区）
- `highest_price` 和 `lowest_price` 显示的是日期而不是价格

## 💡 解决方案

使用动态列映射后，代码会：
1. 先读取表头
2. 根据表头内容识别每列的含义
3. 动态映射到正确的字段
4. 即使表格列顺序变化，也能正确提取数据

## 🚀 下一步

运行爬虫时，查看日志中的列映射信息：
```
[EPRCCrawler] 成交排行榜列映射: {'rank': 0, 'estate_name': 1, ...}
[EPRCCrawler] 表头: ['排名', '屋苑名稱', '地區', ...]
```

如果映射不正确，可以根据实际表头调整映射逻辑。

