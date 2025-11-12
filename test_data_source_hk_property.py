"""
测试 DataSource Agent 对香港楼盘数据的相关性分析
使用 test_property_result.json 文件测试"未来香港楼盘的趋势分析"问题
"""

import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 如果没有 dotenv，跳过

from DataSourceEngine import DataSourceAgent
from loguru import logger

def main():
    """主函数"""
    print("="*80)
    print("DataSource Agent 测试 - 香港楼盘趋势分析")
    print("="*80)
    
    # 检查环境变量（DataSource Engine 或 Insight Engine 的配置都可以）
    import os
    has_ds_config = os.getenv("DATA_SOURCE_ENGINE_API_KEY") and os.getenv("DATA_SOURCE_ENGINE_MODEL_NAME")
    has_insight_config = os.getenv("INSIGHT_ENGINE_API_KEY") and os.getenv("INSIGHT_ENGINE_MODEL_NAME")
    
    if not has_ds_config and not has_insight_config:
        print("\n⚠️  警告: 缺少LLM配置")
        print("\n请至少配置以下环境变量之一:")
        print("\n选项1: DataSource Engine 专用配置")
        print("  DATA_SOURCE_ENGINE_API_KEY=your_api_key")
        print("  DATA_SOURCE_ENGINE_MODEL_NAME=your_model_name")
        print("  DATA_SOURCE_ENGINE_BASE_URL=your_base_url  # 可选")
        print("\n选项2: 使用 Insight Engine 的配置（作为回退）")
        print("  INSIGHT_ENGINE_API_KEY=your_api_key")
        print("  INSIGHT_ENGINE_MODEL_NAME=your_model_name")
        print("  INSIGHT_ENGINE_BASE_URL=your_base_url  # 可选")
        return
    
    try:
        # 创建 Agent
        logger.info("正在初始化 DataSource Agent...")
        agent = DataSourceAgent()
        
        # 添加数据源（香港楼盘数据）
        json_file_path = "/Users/admin/Downloads/PythonProject/test_property_result.json"
        
        if not os.path.exists(json_file_path):
            logger.error(f"文件不存在: {json_file_path}")
            print(f"\n❌ 错误: 文件不存在: {json_file_path}")
            return
        
        logger.info(f"正在添加数据源: {json_file_path}")
        agent.add_data_source(
            source_id="hk_property_data",
            source_type="json_file",
            source_path=json_file_path,
            metadata={
                "description": "香港楼盘交易数据",
                "data_type": "房地产交易记录",
                "region": "香港",
                "source": "EPRC - 專業用戶網"
            }
        )
        
        print(f"\n✅ 已添加数据源: hk_property_data")
        print(f"   文件路径: {json_file_path}")
        print(f"   数据源数量: {len(agent.state.data_sources)}")
        
        # 执行相关性分析
        query = "未来香港楼盘的趋势分析"
        
        print(f"\n{'='*80}")
        print(f"问题: {query}")
        print(f"{'='*80}\n")
        
        logger.info(f"开始相关性分析...")
        result = agent.analyze_relevance(query, save_results=True)
        
        # 输出结果
        print("\n" + "="*80)
        print("📊 分析结果摘要")
        print("="*80)
        print(f"问题: {result['query']}")
        print(f"总数据源数: {result['total_sources']}")
        print(f"相关数据源数: {result['relevant_sources']}")
        print(f"\n相关数据源ID: {result['relevant_source_ids']}")
        
        print("\n" + "="*80)
        print("📋 详细相关性分析")
        print("="*80)
        for i, analysis in enumerate(result['relevance_analyses'], 1):
            print(f"\n【数据源 {i}】")
            print(f"  数据源ID: {analysis['source_id']}")
            print(f"  相关性评分: {analysis['relevance_score']:.2f} {'⭐' * int(analysis['relevance_score'] * 5)}")
            print(f"  是否相关: {'✅ 是' if analysis['is_relevant'] else '❌ 否'}")
            print(f"  判断理由:")
            print(f"    {analysis['reasoning']}")
            if analysis.get('key_matches'):
                print(f"  关键匹配点: {', '.join(analysis['key_matches'])}")
            print(f"  使用建议:")
            print(f"    {analysis['usage_recommendation']}")
        
        print("\n" + "="*80)
        print("🎯 数据使用策略")
        print("="*80)
        print(result['usage_strategy'])
        
        print("\n" + "="*80)
        print("✅ 测试完成！")
        print("="*80)
        
        # 获取相关数据源
        relevant_sources = agent.get_relevant_sources()
        if relevant_sources:
            print(f"\n📌 相关数据源列表: {relevant_sources}")
        else:
            print(f"\n⚠️  未找到相关数据源")
        
        # 显示保存的文件路径
        if hasattr(agent.config, 'OUTPUT_DIR'):
            output_dir = agent.config.OUTPUT_DIR
            print(f"\n💾 结果已保存到目录: {output_dir}")
        
    except Exception as e:
        logger.exception(f"测试过程中发生错误: {str(e)}")
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

