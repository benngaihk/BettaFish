"""
数据分析节点
对筛选出的相关数据源进行深度分析
"""

import json
from typing import Dict, Any, List
from json.decoder import JSONDecodeError
from loguru import logger

from .base_node import BaseNode


class DataAnalysisNode(BaseNode):
    """
    数据分析节点
    对相关数据源进行深度分析，生成洞察和结论
    """

    def __init__(self, llm_client):
        """
        初始化数据分析节点

        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "DataAnalysisNode")

    def run(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        分析相关数据源

        Args:
            input_data: 包含以下字段的字典:
                - query: 用户查询
                - relevant_sources: 相关数据源列表（包含 source_id, data, relevance_score 等）
                - usage_strategy: 使用策略
            **kwargs: 额外参数

        Returns:
            包含分析结果的字典
        """
        try:
            query = input_data.get("query", "")
            relevant_sources = input_data.get("relevant_sources", [])
            usage_strategy = input_data.get("usage_strategy", "")

            if not query or not relevant_sources:
                raise ValueError("输入数据必须包含 query 和 relevant_sources")

            logger.info(f"开始分析 {len(relevant_sources)} 个相关数据源...")

            # 构建分析提示词
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(query, relevant_sources, usage_strategy)

            # 调用 LLM 进行分析
            logger.info("调用 LLM 进行数据分析...")
            response = self.llm_client.invoke(
                system_prompt,
                user_prompt,
                temperature=0.5
            )

            # 处理响应
            analysis_result = self.process_output(response)

            logger.info("数据分析完成")
            return analysis_result

        except Exception as e:
            logger.exception(f"数据分析失败: {str(e)}")
            return {
                "analysis_summary": f"分析失败: {str(e)}",
                "key_findings": [],
                "insights": [],
                "recommendations": []
            }

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个专业的数据分析专家。你的任务是对提供的数据源进行深度分析，提取关键信息、发现洞察并提供建议。

## 任务说明
1. 仔细分析所有相关数据源的内容
2. 识别数据中的关键模式、趋势和异常
3. 从多个数据源中提取互补信息
4. 生成有价值的洞察和发现
5. 提供可操作的建议

## 输出格式
请以 JSON 格式输出分析结果，包含以下字段：

{
  "analysis_summary": "分析总结（3-5句话，概括核心发现）",
  "key_findings": [
    "关键发现1：具体的数据发现或趋势",
    "关键发现2：...",
    "关键发现3：..."
  ],
  "insights": [
    {
      "title": "洞察标题",
      "description": "详细描述这个洞察，说明为什么重要",
      "supporting_data": "支撑这个洞察的数据证据"
    }
  ],
  "recommendations": [
    {
      "priority": "high|medium|low",
      "action": "建议采取的行动",
      "rationale": "为什么这样建议"
    }
  ],
  "data_quality_notes": "数据质量评估（可选）",
  "limitations": "分析的局限性（可选）"
}

## 分析要求
- 基于数据说话，不要臆测
- 识别数据之间的关联和矛盾
- 考虑数据的时间性和相关性评分
- 提供可验证的结论
- 标注不确定的推断

请严格按照 JSON 格式输出，不要添加任何额外的说明文字。"""

    def _build_user_prompt(self, query: str, relevant_sources: List[Dict[str, Any]], usage_strategy: str) -> str:
        """构建用户提示词"""
        prompt_parts = []

        prompt_parts.append(f"## 用户查询\n{query}\n")

        prompt_parts.append(f"## 使用策略\n{usage_strategy}\n")

        prompt_parts.append(f"## 相关数据源（共 {len(relevant_sources)} 个）\n")

        for i, source in enumerate(relevant_sources, 1):
            prompt_parts.append(f"### 数据源 {i}: {source.get('source_id', f'source_{i}')}")
            prompt_parts.append(f"- 相关性评分: {source.get('relevance_score', 0.0):.2f}")
            prompt_parts.append(f"- 判断理由: {source.get('reasoning', '无')}")

            # 数据内容
            data = source.get('data') or source.get('data_preview') or source.get('full_data')
            if data:
                # 限制数据长度，避免超过token限制
                data_str = json.dumps(data, ensure_ascii=False, indent=2)
                if len(data_str) > 5000:
                    data_str = data_str[:5000] + "\n... (数据已截断)"
                prompt_parts.append(f"- 数据内容:\n```json\n{data_str}\n```")
            else:
                prompt_parts.append("- 数据内容: (无)")

            prompt_parts.append("")

        prompt_parts.append("请基于以上数据源进行深度分析。")

        return "\n".join(prompt_parts)

    def process_output(self, output: str) -> Dict[str, Any]:
        """
        处理 LLM 输出，提取分析结果

        Args:
            output: LLM 原始输出

        Returns:
            分析结果字典
        """
        try:
            # 尝试解析 JSON
            try:
                result = json.loads(output)
                return result
            except JSONDecodeError:
                # 如果不是 JSON，尝试提取内容
                logger.warning("LLM 输出不是有效的 JSON，尝试提取内容")
                return self._extract_from_text(output)

        except Exception as e:
            logger.error(f"处理分析输出失败: {str(e)}")
            return {
                "analysis_summary": output[:500] if output else "分析失败",
                "key_findings": [],
                "insights": [],
                "recommendations": []
            }

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取分析结果（当 JSON 解析失败时的后备方案）

        Args:
            text: LLM 输出文本

        Returns:
            提取的结果字典
        """
        result = {
            "analysis_summary": "",
            "key_findings": [],
            "insights": [],
            "recommendations": []
        }

        # 尝试提取摘要（前几句话）
        lines = text.split('\n')
        summary_lines = []
        for line in lines[:10]:  # 只看前10行
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('{'):
                summary_lines.append(line)
                if len(summary_lines) >= 3:
                    break

        result["analysis_summary"] = ' '.join(summary_lines) if summary_lines else text[:500]

        # 尝试提取关键发现（查找包含"发现"、"Finding"的部分）
        import re
        findings_pattern = r'(?:关键发现|Key Finding|发现)[：:]\s*(.+?)(?:\n|$)'
        findings = re.findall(findings_pattern, text, re.IGNORECASE)
        if findings:
            result["key_findings"] = findings[:5]  # 最多5个

        # 如果没有找到，就把整个文本作为摘要
        if not result["key_findings"]:
            result["key_findings"] = [text[:1000]]

        return result
