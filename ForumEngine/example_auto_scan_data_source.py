"""
自动扫描 DataSourceEngine/data_source 文件夹并使用 DataSourceAgent 的示例
演示如何自动发现数据源文件夹中的所有 JSON 文件并进行分析
"""

from DataSourceEngine import DataSourceAgent, scan_data_source_files, get_data_source_summaries
from loguru import logger


def main():
    """主函数 - 自动扫描数据源文件夹"""
    # 创建 Agent
    agent = DataSourceAgent()
    
    # 自动扫描 DataSourceEngine/data_source 文件夹中的所有 JSON 文件
    logger.info("正在扫描数据源文件夹...")
    json_files = scan_data_source_files()
    
    if not json_files:
        logger.warning("数据源文件夹中没有找到有效的 JSON 文件")
        logger.info("请将 JSON 数据文件放入 DataSourceEngine/data_source 文件夹")
        return
    
    logger.info(f"发现 {len(json_files)} 个有效的 JSON 文件")
    
    # 获取文件摘要信息
    summaries = get_data_source_summaries()
    logger.info("\n数据源文件摘要:")
    for summary in summaries:
        logger.info(f"  - {summary['file_name']}: {summary['data_type']}, "
                   f"大小: {summary['file_size']} 字节")
        if 'item_count' in summary:
            logger.info(f"    项目数量: {summary['item_count']}")
        if 'sample_keys' in summary:
            logger.info(f"    示例键: {', '.join(summary['sample_keys'][:5])}")
    
    # 自动添加所有找到的数据源
    logger.info("\n正在添加数据源...")
    for i, file_path in enumerate(json_files, 1):
        file_name = file_path.split('/')[-1]
        source_id = f"data_source_{i}_{file_name.replace('.json', '')}"
        
        try:
            agent.add_data_source(
                source_id=source_id,
                source_type="json_file",
                source_path=file_path,
                metadata={
                    "description": f"从 data_source 文件夹自动发现的文件: {file_name}",
                    "auto_scanned": True
                }
            )
            logger.info(f"✓ 已添加数据源: {source_id} ({file_name})")
        except Exception as e:
            logger.error(f"✗ 添加数据源失败 {file_name}: {str(e)}")
    
    # 执行相关性分析
    query = "分析数据源中的相关信息"
    
    logger.info(f"\n问题: {query}")
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
        if analysis.get('key_matches'):
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

