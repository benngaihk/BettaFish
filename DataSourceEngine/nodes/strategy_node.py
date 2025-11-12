"""
使用策略节点
根据相关性分析结果，决定如何使用数据
"""

import json
from typing import Dict, Any, List
from json.decoder import JSONDecodeError
from loguru import logger

from .base_node import StateMutationNode
from ..prompts import SYSTEM_PROMPT_USAGE_STRATEGY
from ..state.state import State


class UsageStrategyNode(StateMutationNode):
    """使用策略节点"""
    
    def __init__(self, llm_client):
        """
        初始化使用策略节点
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "UsageStrategyNode")
    
    def run(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        生成数据使用策略
        
        Args:
            input_data: 包含query和relevance_analyses的字典
            **kwargs: 额外参数
            
        Returns:
            包含usage_strategy的字典
        """
        try:
            query = input_data.get("query", "")
            relevance_analyses = input_data.get("relevance_analyses", [])
            
            if not query:
                raise ValueError("输入数据必须包含query")
            
            # 构建提示词
            analyses_summary = []
            for analysis in relevance_analyses:
                analyses_summary.append({
                    "source_id": analysis.get("source_id", ""),
                    "relevance_score": analysis.get("relevance_score", 0.0),
                    "is_relevant": analysis.get("is_relevant", False),
                    "reasoning": analysis.get("reasoning", ""),
                    "usage_recommendation": analysis.get("usage_recommendation", "")
                })
            
            user_prompt = f"""问题：{query}

相关性分析结果：
{json.dumps(analyses_summary, ensure_ascii=False, indent=2)}
"""
            
            logger.info("正在生成数据使用策略...")
            
            # 调用LLM
            response = self.llm_client.invoke(
                SYSTEM_PROMPT_USAGE_STRATEGY,
                user_prompt,
                temperature=0.5
            )
            
            # 处理响应
            result = self.process_output(response)
            
            logger.info("数据使用策略生成完成")
            return result
            
        except Exception as e:
            logger.exception(f"生成使用策略失败: {str(e)}")
            return {
                "usage_strategy": f"策略生成失败: {str(e)}"
            }
    
    def process_output(self, output: str) -> Dict[str, Any]:
        """
        处理LLM输出，提取使用策略
        
        Args:
            output: LLM原始输出
            
        Returns:
            包含usage_strategy的字典
        """
        try:
            # 尝试解析JSON
            try:
                result = json.loads(output)
                usage_strategy = result.get("usage_strategy", output)
            except JSONDecodeError:
                # 如果不是JSON，直接使用文本
                usage_strategy = output.strip()
            
            return {
                "usage_strategy": usage_strategy
            }
            
        except Exception as e:
            logger.error(f"处理使用策略输出失败: {str(e)}")
            return {
                "usage_strategy": f"处理输出失败: {str(e)}"
            }
    
    def mutate_state(self, input_data: Dict[str, Any], state: State, **kwargs) -> State:
        """
        更新状态中的使用策略
        
        Args:
            input_data: 输入数据（包含usage_strategy）
            state: 当前状态
            **kwargs: 额外参数
            
        Returns:
            更新后的状态
        """
        usage_strategy = input_data.get("usage_strategy", "")
        if usage_strategy:
            state.usage_strategy = usage_strategy
        return state

