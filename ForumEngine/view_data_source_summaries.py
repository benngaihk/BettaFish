"""
查看数据源文件摘要和关键字
快速预览所有数据源文件的内容，帮助判断是否相关
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from DataSourceEngine import get_data_source_summaries, generate_file_summary
import json


def main():
    """主函数"""
    print("="*70)
    print("数据源文件摘要和关键字预览")
    print("="*70)
    
    # 获取所有文件的摘要（使用缓存）
    summaries = get_data_source_summaries(force_regenerate=False)
    
    if not summaries:
        print("\n没有找到任何数据源文件")
        return
    
    print(f"\n找到 {len(summaries)} 个数据源文件\n")
    
    # 显示每个文件的摘要
    for i, summary in enumerate(summaries, 1):
        print("-"*70)
        print(f"【文件 {i}】{summary['file_name']}")
        print("-"*70)
        print(f"文件大小: {summary['file_size']:,} 字节")
        print(f"数据类型: {summary['data_type']}")
        
        if 'item_count' in summary:
            print(f"项目数量: {summary['item_count']}")
        
        if 'data_structure' in summary:
            print(f"数据结构: {summary['data_structure']}")
        
        if 'short_description' in summary:
            print(f"\n简短描述:")
            print(f"  {summary['short_description']}")
        
        if 'keywords' in summary and summary['keywords']:
            print(f"\n关键字 ({len(summary['keywords'])} 个):")
            keywords = summary['keywords'][:15]  # 只显示前15个
            print(f"  {', '.join(keywords)}")
            if len(summary['keywords']) > 15:
                print(f"  ... 还有 {len(summary['keywords']) - 15} 个关键字")
        
        if 'summary' in summary:
            print(f"\n详细摘要:")
            summary_text = summary['summary']
            # 显示前500个字符
            if len(summary_text) > 500:
                print(f"  {summary_text[:500]}...")
            else:
                print(f"  {summary_text}")
        
        if 'cached_at' in summary:
            print(f"\n摘要生成时间: {summary['cached_at']}")
        
        print()
    
    print("="*70)
    print("提示: 摘要已缓存，下次查看会更快")
    print("="*70)


if __name__ == "__main__":
    main()

