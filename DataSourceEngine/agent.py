"""
DataSource Agent主类
用于判断外部数据源是否与问题相关，并决定如何使用这些数据
"""

import os
from typing import Optional, Dict, Any, List, Union
from loguru import logger
import json

from .llms import LLMClient
from .nodes import RelevanceAnalysisNode, UsageStrategyNode, DataAnalysisNode
from .state import State, DataSourceItem, RelevanceAnalysis
from .tools import DataLoader, get_registry
from .utils.config import settings, Settings


class DataSourceAgent:
    """DataSource Agent主类"""
    
    def __init__(self, config: Optional[Settings] = None):
        """
        初始化DataSource Agent
        
        Args:
            config: 可选配置对象（不填则用全局settings）
        """
        self.config = config or settings
        
        # 初始化LLM客户端
        self.llm_client = self._initialize_llm()
        
        # 初始化数据加载器
        self.data_loader = DataLoader()
        
        # 初始化节点
        self._initialize_nodes()
        
        # 状态
        self.state = State()
        
        # 确保输出目录存在
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        
        # 设置日志输出到文件（符合ForumEngine规范）
        self._setup_logging()
        
        logger.info(f"DataSource Agent已初始化")
        logger.info(f"使用LLM: {self.llm_client.get_model_info()}")
        logger.info(f"相关性阈值: {self.config.MAX_RELEVANCE_SCORE_THRESHOLD}")
    
    def _setup_logging(self):
        """设置日志输出到文件（符合ForumEngine规范）"""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "datasource.log")
        
        # 添加日志文件处理器（只添加一次）
        logger.add(
            log_file,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8"
        )
    
    def _initialize_llm(self) -> LLMClient:
        """初始化LLM客户端（如果未配置，回退到使用Insight Engine的配置）"""
        # 使用配置对象的辅助方法获取配置（会自动回退到全局配置）
        api_key = self.config.get_api_key()
        model_name = self.config.get_model_name()
        base_url = self.config.get_base_url()
        
        if not api_key or not model_name:
            raise ValueError(
                "DataSource Engine LLM配置缺失。请设置 DATA_SOURCE_ENGINE_API_KEY 和 DATA_SOURCE_ENGINE_MODEL_NAME，"
                "或者设置 INSIGHT_ENGINE_API_KEY 和 INSIGHT_ENGINE_MODEL_NAME 作为回退配置。"
            )
        
        return LLMClient(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
        )
    
    def _initialize_nodes(self):
        """初始化处理节点"""
        self.relevance_node = RelevanceAnalysisNode(
            self.llm_client,
            threshold=self.config.MAX_RELEVANCE_SCORE_THRESHOLD
        )
        self.strategy_node = UsageStrategyNode(self.llm_client)
        self.analysis_node = DataAnalysisNode(self.llm_client)
    
    def add_data_source(self, source_id: str, source_type: str, source_path: str, 
                       metadata: Optional[Dict[str, Any]] = None):
        """
        添加数据源
        
        Args:
            source_id: 数据源唯一标识
            source_type: 数据源类型（json_file, api, database等）
            source_path: 数据源路径或标识
            metadata: 可选的元数据
        """
        # 加载数据预览
        data_preview = {}
        if source_type == "json_file":
            try:
                loaded_data = self.data_loader.load_json_file(
                    source_path,
                    max_samples=self.config.MAX_DATA_SAMPLES_FOR_ANALYSIS
                )
                data_preview = loaded_data
            except Exception as e:
                logger.error(f"加载数据源 {source_id} 失败: {str(e)}")
                data_preview = {"error": str(e)}
        
        # 创建数据源项
        source_item = DataSourceItem(
            source_id=source_id,
            source_type=source_type,
            source_path=source_path,
            data_preview=data_preview,
            metadata=metadata or {}
        )
        
        # 添加到状态
        self.state.add_data_source(source_item)
        logger.info(f"已添加数据源: {source_id} ({source_type})")
    
    def analyze_relevance(self, query: str, save_results: bool = True) -> Dict[str, Any]:
        """
        分析所有数据源与问题的相关性
        
        Args:
            query: 用户查询
            save_results: 是否保存结果到文件
            
        Returns:
            分析结果字典
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"开始相关性分析: {query}")
        logger.info(f"{'='*60}")
        
        try:
            # 设置查询
            self.state.query = query
            
            # 分析每个数据源
            for source in self.state.data_sources:
                logger.info(f"\n分析数据源: {source.source_id}")
                
                # 提取数据文本用于分析
                data_text = self.data_loader.extract_text_content(
                    source.data_preview,
                    max_length=3000
                )
                
                # 准备输入
                input_data = {
                    "query": query,
                    "source_id": source.source_id,
                    "data_preview": source.data_preview,
                    "data_text": data_text
                }
                
                # 执行相关性分析
                analysis_result = self.relevance_node.run(input_data)
                
                # 创建RelevanceAnalysis对象
                relevance_analysis = self.relevance_node.create_analysis(analysis_result)
                
                # 添加到状态
                self.state.add_relevance_analysis(relevance_analysis)
                
                logger.info(f"  相关性评分: {relevance_analysis.relevance_score:.2f}")
                logger.info(f"  是否相关: {'是' if relevance_analysis.is_relevant else '否'}")
                logger.info(f"  判断理由: {relevance_analysis.reasoning[:100]}...")
            
            # 生成使用策略
            logger.info(f"\n生成数据使用策略...")
            strategy_input = {
                "query": query,
                "relevance_analyses": [analysis.to_dict() for analysis in self.state.relevance_analyses]
            }
            
            strategy_result = self.strategy_node.run(strategy_input)
            self.state = self.strategy_node.mutate_state(strategy_result, self.state)

            logger.info(f"使用策略: {self.state.usage_strategy[:200]}...")

            # 步骤 4: 对相关数据源进行深度分析 ✨ 新增
            logger.info(f"\n开始对相关数据源进行深度分析...")
            if self.state.filtered_data_sources:
                analysis_result = self._analyze_relevant_data(query)
                self.state.data_analysis = analysis_result
                logger.info(f"数据分析完成: {len(analysis_result.get('key_findings', []))} 个关键发现")
            else:
                logger.warning("没有相关数据源，跳过数据分析")
                self.state.data_analysis = {
                    "analysis_summary": "没有找到相关数据源",
                    "key_findings": [],
                    "insights": [],
                    "recommendations": []
                }

            # 生成符合ForumEngine规范的输出（类似SummaryNode的输出格式）
            self._output_to_forum_format(query)
            
            # 标记完成
            self.state.mark_completed()
            
            # 保存结果
            if save_results:
                self._save_results()

            # 注册相关数据源到共享存储（供其他 Engine 使用）
            self._register_relevant_data_sources()

            logger.info("\n相关性分析完成！")

            return self._get_analysis_summary()
        except Exception as e:
            logger.exception(f"相关性分析过程中出错: {str(e)}")
            raise
    
    def _output_to_forum_format(self, query: str):
        """
        输出符合ForumEngine规范的格式（类似SummaryNode的输出）
        格式：清理后的输出: {"paragraph_latest_state": "..."}
        """
        try:
            # 构建总结内容
            summary_parts = []
            summary_parts.append(f"数据源相关性分析总结（问题：{query}）\n")
            
            # 添加相关性分析结果
            summary_parts.append("=" * 60)
            summary_parts.append("相关性分析结果")
            summary_parts.append("=" * 60)
            
            for i, analysis in enumerate(self.state.relevance_analyses, 1):
                summary_parts.append(f"\n【数据源 {i}】{analysis.source_id}")
                summary_parts.append(f"相关性评分: {analysis.relevance_score:.2f}")
                summary_parts.append(f"是否相关: {'是' if analysis.is_relevant else '否'}")
                summary_parts.append(f"判断理由: {analysis.reasoning}")
                if analysis.key_matches:
                    summary_parts.append(f"关键匹配点: {', '.join(analysis.key_matches)}")
                summary_parts.append(f"使用建议: {analysis.usage_recommendation}")
                summary_parts.append("")
            
            # 添加使用策略
            summary_parts.append("=" * 60)
            summary_parts.append("数据使用策略")
            summary_parts.append("=" * 60)
            summary_parts.append(self.state.usage_strategy)

            # 添加数据分析结果 ✨ 新增
            if self.state.data_analysis:
                summary_parts.append("")
                summary_parts.append("=" * 60)
                summary_parts.append("数据深度分析")
                summary_parts.append("=" * 60)

                # 分析总结
                summary_parts.append("\n【分析总结】")
                summary_parts.append(self.state.data_analysis.get("analysis_summary", "无"))

                # 关键发现
                key_findings = self.state.data_analysis.get("key_findings", [])
                if key_findings:
                    summary_parts.append("\n【关键发现】")
                    for i, finding in enumerate(key_findings, 1):
                        summary_parts.append(f"{i}. {finding}")

                # 洞察
                insights = self.state.data_analysis.get("insights", [])
                if insights:
                    summary_parts.append("\n【深度洞察】")
                    for i, insight in enumerate(insights, 1):
                        if isinstance(insight, dict):
                            summary_parts.append(f"{i}. {insight.get('title', '洞察')}")
                            summary_parts.append(f"   {insight.get('description', '')}")
                        else:
                            summary_parts.append(f"{i}. {insight}")

                # 建议
                recommendations = self.state.data_analysis.get("recommendations", [])
                if recommendations:
                    summary_parts.append("\n【行动建议】")
                    for i, rec in enumerate(recommendations, 1):
                        if isinstance(rec, dict):
                            priority = rec.get('priority', 'medium')
                            action = rec.get('action', '')
                            summary_parts.append(f"{i}. [{priority.upper()}] {action}")
                        else:
                            summary_parts.append(f"{i}. {rec}")

            # 组合成完整总结
            paragraph_content = "\n".join(summary_parts)
            
            # 输出符合ForumEngine规范的JSON格式
            output_json = {
                "paragraph_latest_state": paragraph_content
            }
            
            # 使用loguru的logger输出，格式与SummaryNode一致
            # 添加节点标识，让ForumEngine能够识别（类似FirstSummaryNode）
            logger.info(f"[DataSourceEngine.nodes.summary_node] 正在生成数据源相关性分析总结")
            logger.info(f"清理后的输出: {json.dumps(output_json, ensure_ascii=False)}")
            
        except Exception as e:
            logger.exception(f"输出ForumEngine格式失败: {str(e)}")
    
    def _get_analysis_summary(self) -> Dict[str, Any]:
        """
        获取分析摘要

        Returns:
            分析摘要字典
        """
        return {
            "query": self.state.query,
            "total_sources": len(self.state.data_sources),
            "relevant_sources": len(self.state.filtered_data_sources),
            "relevance_analyses": [analysis.to_dict() for analysis in self.state.relevance_analyses],
            "usage_strategy": self.state.usage_strategy,
            "relevant_source_ids": self.state.filtered_data_sources,
            "data_analysis": self.state.data_analysis  # ✨ 新增：包含数据分析结果
        }
    
    def _save_results(self):
        """保存分析结果到文件"""
        from datetime import datetime
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_safe = "".join(c for c in self.state.query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        query_safe = query_safe.replace(' ', '_')[:30]
        
        # 保存状态
        if self.config.SAVE_INTERMEDIATE_STATES:
            state_filename = f"data_source_state_{query_safe}_{timestamp}.json"
            state_filepath = os.path.join(self.config.OUTPUT_DIR, state_filename)
            self.state.save_to_file(state_filepath)
            logger.info(f"状态已保存到: {state_filepath}")
        
        # 保存摘要报告
        summary_filename = f"data_source_summary_{query_safe}_{timestamp}.json"
        summary_filepath = os.path.join(self.config.OUTPUT_DIR, summary_filename)
        
        summary = self._get_analysis_summary()
        import json
        with open(summary_filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分析摘要已保存到: {summary_filepath}")

    def _analyze_relevant_data(self, query: str) -> Dict[str, Any]:
        """
        对相关数据源进行深度分析

        Args:
            query: 用户查询

        Returns:
            分析结果字典
        """
        try:
            # 准备相关数据源列表
            relevant_sources = []
            for source_id in self.state.filtered_data_sources:
                # 查找对应的数据源项
                source_item = None
                for source in self.state.data_sources:
                    if source.source_id == source_id:
                        source_item = source
                        break

                if source_item is None:
                    continue

                # 获取相关性分析
                analysis = self.state.get_relevance_analysis(source_id)

                # 构建数据源信息
                source_info = {
                    "source_id": source_id,
                    "relevance_score": analysis.relevance_score if analysis else 0.0,
                    "reasoning": analysis.reasoning if analysis else "",
                    "key_matches": analysis.key_matches if analysis else [],
                    "usage_recommendation": analysis.usage_recommendation if analysis else "",
                    # 包含完整数据
                    "data": source_item.data_preview.get("data") if "data" in source_item.data_preview else None,
                    # 包含数据预览
                    "data_preview": source_item.data_preview.get("preview") if "preview" in source_item.data_preview else source_item.data_preview
                }

                relevant_sources.append(source_info)

            # 调用分析节点
            analysis_input = {
                "query": query,
                "relevant_sources": relevant_sources,
                "usage_strategy": self.state.usage_strategy
            }

            analysis_result = self.analysis_node.run(analysis_input)

            return analysis_result

        except Exception as e:
            logger.exception(f"数据分析失败: {str(e)}")
            return {
                "analysis_summary": f"分析失败: {str(e)}",
                "key_findings": [],
                "insights": [],
                "recommendations": []
            }

    def _register_relevant_data_sources(self):
        """将相关数据源注册到共享存储（供其他 Engine 使用）"""
        try:
            # 获取全局注册表
            registry = get_registry()

            # 准备相关数据源列表
            relevant_sources = []
            for source_id in self.state.filtered_data_sources:
                # 查找对应的数据源项
                source_item = None
                for source in self.state.data_sources:
                    if source.source_id == source_id:
                        source_item = source
                        break

                if source_item is None:
                    continue

                # 获取相关性分析
                analysis = self.state.get_relevance_analysis(source_id)

                # 构建数据源信息
                source_info = {
                    "source_id": source_id,
                    "source_type": source_item.source_type,
                    "source_path": source_item.source_path,
                    "relevance_score": analysis.relevance_score if analysis else 0.0,
                    "reasoning": analysis.reasoning if analysis else "",
                    "key_matches": analysis.key_matches if analysis else [],
                    "usage_recommendation": analysis.usage_recommendation if analysis else "",
                    "metadata": source_item.metadata,
                    # 包含完整数据（如果需要）
                    "full_data": source_item.data_preview.get("data") if "data" in source_item.data_preview else None,
                    # 包含数据预览
                    "data_preview": source_item.data_preview.get("preview") if "preview" in source_item.data_preview else source_item.data_preview
                }

                relevant_sources.append(source_info)

            # 注册到共享存储
            registration_id = registry.register_relevant_sources(
                query=self.state.query,
                relevant_sources=relevant_sources,
                usage_strategy=self.state.usage_strategy,
                metadata={
                    "total_sources": len(self.state.data_sources),
                    "relevant_sources": len(self.state.filtered_data_sources),
                    "threshold": self.config.MAX_RELEVANCE_SCORE_THRESHOLD
                }
            )

            logger.info(f"已将 {len(relevant_sources)} 个相关数据源注册到共享存储，注册ID: {registration_id}")

        except Exception as e:
            logger.exception(f"注册相关数据源到共享存储失败: {str(e)}")
            # 不抛出异常，避免影响主流程

    def get_relevant_sources(self) -> List[str]:
        """
        获取相关数据源ID列表
        
        Returns:
            相关数据源ID列表
        """
        return self.state.get_relevant_sources()
    
    def get_relevance_analysis(self, source_id: str) -> Optional[RelevanceAnalysis]:
        """
        获取指定数据源的相关性分析
        
        Args:
            source_id: 数据源ID
            
        Returns:
            RelevanceAnalysis对象，如果不存在则返回None
        """
        return self.state.get_relevance_analysis(source_id)
    
    def get_usage_strategy(self) -> str:
        """
        获取数据使用策略
        
        Returns:
            使用策略字符串
        """
        return self.state.usage_strategy
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        return self.state.get_progress_summary()
    
    def load_state(self, filepath: str):
        """从文件加载状态"""
        self.state = State.load_from_file(filepath)
        logger.info(f"状态已从 {filepath} 加载")
    
    def save_state(self, filepath: str):
        """保存状态到文件"""
        self.state.save_to_file(filepath)
        logger.info(f"状态已保存到 {filepath}")


def create_agent(config_file: Optional[str] = None) -> DataSourceAgent:
    """
    创建DataSource Agent实例的便捷函数
    
    Args:
        config_file: 配置文件路径（暂未使用）
        
    Returns:
        DataSourceAgent实例
    """
    config = Settings()  # 从环境变量初始化
    return DataSourceAgent(config)

