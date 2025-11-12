"""
相关性分析节点
判断数据源是否与问题相关
"""

import json
from typing import Dict, Any
from json.decoder import JSONDecodeError
from loguru import logger

from .base_node import BaseNode
from ..prompts import SYSTEM_PROMPT_RELEVANCE_ANALYSIS
from ..state.state import RelevanceAnalysis


class RelevanceAnalysisNode(BaseNode):
    """相关性分析节点"""
    
    def __init__(self, llm_client, threshold: float = 0.6):
        """
        初始化相关性分析节点
        
        Args:
            llm_client: LLM客户端
            threshold: 相关性阈值（默认0.6）
        """
        super().__init__(llm_client, "RelevanceAnalysisNode")
        self.threshold = threshold
    
    def run(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        分析数据源与问题的相关性
        
        Args:
            input_data: 包含query、source_id、data_preview的字典
            **kwargs: 额外参数
            
        Returns:
            包含relevance_score、is_relevant、reasoning等的字典
        """
        try:
            query = input_data.get("query", "")
            source_id = input_data.get("source_id", "")
            data_preview = input_data.get("data_preview", {})
            data_text = input_data.get("data_text", "")
            
            if not query or not source_id:
                raise ValueError("输入数据必须包含query和source_id")
            
            # 构建提示词（限制数据文本长度避免token过多）
            data_text_limited = data_text[:3000] if len(data_text) > 3000 else data_text
            user_prompt = f"""问题：{query}

数据源ID：{source_id}
数据预览：
{data_text_limited}
"""
            
            logger.info(f"正在分析数据源 {source_id} 的相关性...")
            
            # 调用LLM
            response = self.llm_client.invoke(
                SYSTEM_PROMPT_RELEVANCE_ANALYSIS,
                user_prompt,
                temperature=0.3
            )
            
            # 处理响应
            result = self.process_output(response, source_id)
            
            logger.info(f"数据源 {source_id} 相关性评分: {result.get('relevance_score', 0.0)}")
            return result
            
        except Exception as e:
            logger.exception(f"相关性分析失败: {str(e)}")
            # 返回默认结果（不相关）
            return {
                "source_id": input_data.get("source_id", ""),
                "relevance_score": 0.0,
                "is_relevant": False,
                "reasoning": f"分析失败: {str(e)}",
                "key_matches": [],
                "usage_recommendation": "无法使用此数据源"
            }
    
    def process_output(self, output: str, source_id: str) -> Dict[str, Any]:
        """
        处理LLM输出，提取相关性分析结果
        
        Args:
            output: LLM原始输出
            source_id: 数据源ID
            
        Returns:
            包含相关性分析结果的字典
        """
        try:
            # 尝试解析JSON
            try:
                result = json.loads(output)
            except JSONDecodeError:
                # 如果不是JSON，尝试提取关键信息
                result = self._extract_from_text(output)
            
            # 提取字段
            relevance_score = float(result.get("relevance_score", 0.0))
            reasoning = result.get("reasoning", "")
            key_matches = result.get("key_matches", [])
            usage_recommendation = result.get("usage_recommendation", "")
            
            # 确保评分在0-1之间
            relevance_score = max(0.0, min(1.0, relevance_score))
            
            # 判断是否相关
            is_relevant = relevance_score >= self.threshold
            
            return {
                "source_id": source_id,
                "relevance_score": relevance_score,
                "is_relevant": is_relevant,
                "reasoning": reasoning,
                "key_matches": key_matches if isinstance(key_matches, list) else [],
                "usage_recommendation": usage_recommendation
            }
            
        except Exception as e:
            logger.error(f"处理相关性分析输出失败: {str(e)}")
            return {
                "source_id": source_id,
                "relevance_score": 0.0,
                "is_relevant": False,
                "reasoning": f"处理输出失败: {str(e)}",
                "key_matches": [],
                "usage_recommendation": "无法使用此数据源"
            }
    
    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取相关性信息
        
        Args:
            text: LLM输出文本
            
        Returns:
            提取的信息字典
        """
        result = {
            "relevance_score": 0.0,
            "reasoning": text,
            "key_matches": [],
            "usage_recommendation": ""
        }
        
        # 尝试提取评分
        import re
        score_match = re.search(r'(?:相关性|评分|score)[：:]\s*([0-9.]+)', text)
        if score_match:
            try:
                score = float(score_match.group(1))
                # 如果是0-100的评分，转换为0-1
                if score > 1.0:
                    score = score / 100.0
                result["relevance_score"] = score
            except ValueError:
                pass
        
        return result
    
    def create_analysis(self, result: Dict[str, Any]) -> RelevanceAnalysis:
        """
        创建RelevanceAnalysis对象
        
        Args:
            result: 分析结果字典
            
        Returns:
            RelevanceAnalysis对象
        """
        return RelevanceAnalysis(
            source_id=result.get("source_id", ""),
            relevance_score=result.get("relevance_score", 0.0),
            is_relevant=result.get("is_relevant", False),
            reasoning=result.get("reasoning", ""),
            key_matches=result.get("key_matches", []),
            usage_recommendation=result.get("usage_recommendation", "")
        )

