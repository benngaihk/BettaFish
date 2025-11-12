"""
DataSource Agent 使用示例
演示如何使用 DataSourceAgent 判断外部数据源与问题的相关性
"""

from DataSourceEngine import DataSourceAgent
from loguru import logger

def main():
    """主函数"""
    # 创建 Agent
    agent = DataSourceAgent()
    
    # 添加数据源（示例：JSON文件）
    # 假设你有一些提前抓取的数据文件
    agent.add_data_source(
        source_id="crawl_data_1",
        source_type="json_file",
        source_path="/Users/admin/Downloads/PythonProject/crawl_results.json",
        metadata={"description": "爬取的阿里云数据"}
    )
    
    # 可以添加多个数据源
    # agent.add_data_source(
    #     source_id="crawl_data_2",
    #     source_type="json_file",
    #     source_path="/path/to/another/data.json",
    #     metadata={"description": "另一个数据源"}
    # )
    
    # 执行相关性分析
    query = "分析阿里云相关的舆情信息"
    
    logger.info(f"问题: {query}")
    logger.info(f"数据源数量: {len(agent.state.data_sources)}")
    
    # 分析相关性
    result = agent.analyze_relevance(query, save_results=True)
    
    # 输出结果
    print("\n" + "="*60)
    print("分析结果摘要")
    print("="*60)
    print(f"问题: {result['query']}")
    print(f"总数据源数: {result['total_sources']}")
    print(f"相关数据源数: {result['relevant_sources']}")
    print(f"\n相关数据源ID: {result['relevant_source_ids']}")
    print(f"\n使用策略:\n{result['usage_strategy']}")
    
    print("\n" + "="*60)
    print("详细相关性分析")
    print("="*60)
    for analysis in result['relevance_analyses']:
        print(f"\n数据源ID: {analysis['source_id']}")
        print(f"  相关性评分: {analysis['relevance_score']:.2f}")
        print(f"  是否相关: {'是' if analysis['is_relevant'] else '否'}")
        print(f"  判断理由: {analysis['reasoning']}")
        print(f"  关键匹配点: {', '.join(analysis['key_matches'])}")
        print(f"  使用建议: {analysis['usage_recommendation']}")
    
    # 获取相关数据源
    relevant_sources = agent.get_relevant_sources()
    print(f"\n相关数据源列表: {relevant_sources}")
    
    # 获取使用策略
    strategy = agent.get_usage_strategy()
    print(f"\n数据使用策略:\n{strategy}")


if __name__ == "__main__":
    main()

