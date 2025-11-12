"""
测试 DataSourceAgent - 使用 ForumEngine/data_source 文件夹中的数据
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from DataSourceEngine import DataSourceAgent, scan_data_source_files, get_data_source_summaries
from loguru import logger

def main():
    """主函数"""
    print("="*60)
    print("DataSourceAgent 测试")
    print("="*60)
    
    # 创建 Agent
    print("\n1. 初始化 DataSourceAgent...")
    try:
        agent = DataSourceAgent()
        print("✓ Agent 初始化成功")
    except Exception as e:
        print(f"✗ Agent 初始化失败: {str(e)}")
        sys.exit(1)
    
    # 自动扫描数据源文件夹
    print("\n2. 扫描数据源文件夹...")
    json_files = scan_data_source_files()
    
    if not json_files:
        print("✗ 数据源文件夹中没有找到有效的 JSON 文件")
        print("请将 JSON 数据文件放入 ForumEngine/data_source 文件夹")
        sys.exit(1)
    
    print(f"✓ 发现 {len(json_files)} 个有效的 JSON 文件")
    
    # 显示文件摘要
    summaries = get_data_source_summaries()
    print("\n数据源文件摘要:")
    for summary in summaries:
        print(f"  - {summary['file_name']}: {summary['data_type']}, "
              f"大小: {summary['file_size']:,} 字节")
        if 'item_count' in summary:
            print(f"    项目数量: {summary['item_count']}")
        if 'sample_keys' in summary:
            keys = summary['sample_keys'][:5]
            print(f"    示例键: {', '.join(keys)}")
    
    # 自动添加所有找到的数据源
    print("\n3. 添加数据源到 Agent...")
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
            print(f"✓ 已添加数据源: {source_id} ({file_name})")
        except Exception as e:
            print(f"✗ 添加数据源失败 {file_name}: {str(e)}")
            logger.exception(f"添加数据源失败: {e}")
    
    if len(agent.state.data_sources) == 0:
        print("✗ 没有成功添加任何数据源")
        sys.exit(1)
    
    # 执行相关性分析
    query = "未来香港房地产的走向"
    
    print("\n" + "="*60)
    print(f"4. 执行相关性分析")
    print("="*60)
    print(f"问题: {query}")
    print(f"数据源数量: {len(agent.state.data_sources)}")
    print()
    
    try:
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
        
        print("\n" + "="*60)
        print("详细相关性分析")
        print("="*60)
        for i, analysis in enumerate(result['relevance_analyses'], 1):
            print(f"\n【数据源 {i}】{analysis['source_id']}")
            print(f"  相关性评分: {analysis['relevance_score']:.2f}")
            print(f"  是否相关: {'是' if analysis['is_relevant'] else '否'}")
            print(f"  判断理由: {analysis['reasoning']}")
            if analysis.get('key_matches'):
                print(f"  关键匹配点: {', '.join(analysis['key_matches'])}")
            print(f"  使用建议: {analysis['usage_recommendation']}")
        
        print("\n" + "="*60)
        print("数据使用策略")
        print("="*60)
        print(result['usage_strategy'])
        
        # 获取相关数据源
        relevant_sources = agent.get_relevant_sources()
        print(f"\n相关数据源列表: {relevant_sources}")
        
        print("\n" + "="*60)
        print("测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ 分析过程中出错: {str(e)}")
        logger.exception(f"分析失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

