"""
策略执行器 (Strategy Executor)
根据 DataSourceEngine 的使用策略，实际调用相应的 Engine 并传递数据
"""

import re
from typing import Dict, Any, List, Optional
from loguru import logger
from DataSourceEngine.tools import get_registry


class StrategyExecutor:
    """
    策略执行器
    负责解析 DataSourceEngine 的使用策略并执行
    """

    def __init__(self):
        """初始化策略执行器"""
        self.registry = get_registry()

        # Engine 关键词映射
        self.engine_keywords = {
            "insight": ["Insight Agent", "InsightEngine", "舆情", "数据库", "结构化数据"],
            "query": ["Query Agent", "QueryEngine", "搜索", "查询", "检索"],
            "media": ["Media Agent", "MediaEngine", "媒体", "多模态", "图片", "视频"]
        }

        logger.info("StrategyExecutor 已初始化")

    def parse_strategy(self, usage_strategy: str) -> Dict[str, Any]:
        """
        解析使用策略文本，提取应该调用哪些 Engine

        Args:
            usage_strategy: 使用策略文本

        Returns:
            解析结果，包含应该调用的 Engine 列表
        """
        result = {
            "engines_to_call": [],
            "priority": {},
            "recommendations": {}
        }

        # 检查策略中提到了哪些 Engine
        for engine_name, keywords in self.engine_keywords.items():
            for keyword in keywords:
                if keyword.lower() in usage_strategy.lower():
                    if engine_name not in result["engines_to_call"]:
                        result["engines_to_call"].append(engine_name)
                    break

        # 提取优先级信息
        if "主要数据源" in usage_strategy or "高度相关" in usage_strategy or "评分0.9" in usage_strategy or "评分0.8" in usage_strategy:
            # 高优先级
            for engine in result["engines_to_call"]:
                result["priority"][engine] = "high"
        elif "补充数据" in usage_strategy or "中度相关" in usage_strategy:
            # 中优先级
            for engine in result["engines_to_call"]:
                if engine not in result["priority"]:
                    result["priority"][engine] = "medium"

        # 提取具体建议
        for engine_name in result["engines_to_call"]:
            # 尝试提取与该 Engine 相关的建议
            for keyword in self.engine_keywords[engine_name]:
                pattern = f"{keyword}[^。]*。?"
                matches = re.findall(pattern, usage_strategy, re.IGNORECASE)
                if matches:
                    result["recommendations"][engine_name] = " ".join(matches)
                    break

        logger.info(f"策略解析结果: 需要调用 {len(result['engines_to_call'])} 个 Engine")
        return result

    def prepare_data_for_engine(self, engine_name: str, registration_id: Optional[str] = None) -> Dict[str, Any]:
        """
        为特定 Engine 准备数据

        Args:
            engine_name: Engine 名称（query, media, insight）
            registration_id: 注册ID（可选）

        Returns:
            为该 Engine 准备的数据包
        """
        # 从共享存储获取数据
        engine_data = self.registry.get_data_for_engine(engine_name, registration_id)

        if not engine_data.get("has_data"):
            logger.warning(f"没有为 {engine_name} 准备的数据")
            return {
                "has_data": False,
                "sources": [],
                "prepared_data": None
            }

        # 准备数据包
        prepared_data = {
            "query": engine_data.get("query", ""),
            "usage_strategy": engine_data.get("usage_strategy", ""),
            "is_recommended": engine_data.get("is_recommended", False),
            "relevant_sources": []
        }

        # 处理每个相关数据源
        for source in engine_data.get("sources", []):
            source_info = {
                "source_id": source.get("source_id"),
                "relevance_score": source.get("relevance_score", 0.0),
                "reasoning": source.get("reasoning", ""),
                "usage_recommendation": source.get("usage_recommendation", ""),
                "data": source.get("full_data") or source.get("data_preview")
            }
            prepared_data["relevant_sources"].append(source_info)

        logger.info(f"为 {engine_name} 准备了 {len(prepared_data['relevant_sources'])} 个数据源")

        return {
            "has_data": True,
            "sources": engine_data.get("sources", []),
            "prepared_data": prepared_data
        }

    def execute_strategy(self, registration_id: Optional[str] = None) -> Dict[str, Any]:
        """
        执行策略：解析策略并调用相应的 Engine

        Args:
            registration_id: 注册ID（可选，不提供则使用最新的）

        Returns:
            执行结果
        """
        # 获取注册数据
        registry_data = self.registry.get_relevant_sources(registration_id)

        if not registry_data.get("relevant_sources"):
            logger.warning("没有找到相关数据源")
            return {
                "success": False,
                "message": "没有找到相关数据源"
            }

        usage_strategy = registry_data.get("usage_strategy", "")
        query = registry_data.get("query", "")

        logger.info(f"开始执行策略: {query}")
        logger.info(f"策略内容: {usage_strategy[:200]}...")

        # 解析策略
        parsed_strategy = self.parse_strategy(usage_strategy)

        if not parsed_strategy["engines_to_call"]:
            logger.warning("策略中未明确指定要调用的 Engine")
            # 默认都调用
            parsed_strategy["engines_to_call"] = ["query", "media", "insight"]
            logger.info("将调用所有 Engine")

        # 为每个 Engine 准备数据
        execution_plan = {
            "query": query,
            "strategy": usage_strategy,
            "engines": {}
        }

        for engine_name in parsed_strategy["engines_to_call"]:
            # 准备数据
            data_package = self.prepare_data_for_engine(engine_name, registration_id)

            execution_plan["engines"][engine_name] = {
                "should_call": True,
                "has_data": data_package["has_data"],
                "priority": parsed_strategy["priority"].get(engine_name, "normal"),
                "recommendation": parsed_strategy["recommendations"].get(engine_name, ""),
                "data_package": data_package["prepared_data"],
                "status": "pending"
            }

        logger.info(f"执行计划已生成，将调用 {len(execution_plan['engines'])} 个 Engine")

        return {
            "success": True,
            "execution_plan": execution_plan,
            "parsed_strategy": parsed_strategy
        }

    def get_execution_instructions(self, engine_name: str, execution_plan: Dict[str, Any]) -> str:
        """
        获取给特定 Engine 的执行指令（人类可读格式）

        Args:
            engine_name: Engine 名称
            execution_plan: 执行计划

        Returns:
            执行指令文本
        """
        if engine_name not in execution_plan.get("engines", {}):
            return f"{engine_name} 不在执行计划中"

        engine_info = execution_plan["engines"][engine_name]

        instructions = f"""
=== {engine_name.upper()} Engine 执行指令 ===

查询问题: {execution_plan['query']}

优先级: {engine_info['priority']}

是否有相关数据: {'是' if engine_info['has_data'] else '否'}

数据源数量: {len(engine_info.get('data_package', {}).get('relevant_sources', []))}

使用建议: {engine_info['recommendation']}

整体策略: {execution_plan['strategy'][:200]}...

数据包详情:
"""

        if engine_info['has_data'] and engine_info['data_package']:
            for i, source in enumerate(engine_info['data_package'].get('relevant_sources', []), 1):
                instructions += f"\n  数据源 {i}:"
                instructions += f"\n    ID: {source['source_id']}"
                instructions += f"\n    相关性: {source['relevance_score']:.2f}"
                instructions += f"\n    理由: {source['reasoning'][:100]}..."
                instructions += f"\n    建议: {source['usage_recommendation'][:100]}..."

        instructions += "\n\n=== 执行指令结束 ==="

        return instructions


def create_executor() -> StrategyExecutor:
    """创建策略执行器实例"""
    return StrategyExecutor()


# 演示如何使用
if __name__ == "__main__":
    from loguru import logger
    import sys

    logger.remove()
    logger.add(sys.stdout, level="INFO")

    # 创建执行器
    executor = StrategyExecutor()

    # 执行策略
    result = executor.execute_strategy()

    if result["success"]:
        execution_plan = result["execution_plan"]

        print("\n" + "="*80)
        print("策略执行计划")
        print("="*80)
        print(f"查询: {execution_plan['query']}")
        print(f"需要调用的 Engine: {list(execution_plan['engines'].keys())}")

        # 显示每个 Engine 的执行指令
        for engine_name in execution_plan["engines"].keys():
            instructions = executor.get_execution_instructions(engine_name, execution_plan)
            print(instructions)
    else:
        print(f"策略执行失败: {result.get('message')}")
