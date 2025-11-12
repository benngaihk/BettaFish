"""
DataSource Agent状态管理
定义所有状态数据结构和操作方法
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
from datetime import datetime


@dataclass
class DataSourceItem:
    """单个数据源项"""
    source_id: str = ""                    # 数据源ID
    source_type: str = ""                  # 数据源类型（json_file, api, database等）
    source_path: str = ""                  # 数据源路径或标识
    data_preview: Dict[str, Any] = field(default_factory=dict)  # 数据预览
    metadata: Dict[str, Any] = field(default_factory=dict)       # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "data_preview": self.data_preview,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataSourceItem":
        """从字典创建DataSourceItem对象"""
        return cls(
            source_id=data.get("source_id", ""),
            source_type=data.get("source_type", ""),
            source_path=data.get("source_path", ""),
            data_preview=data.get("data_preview", {}),
            metadata=data.get("metadata", {})
        )


@dataclass
class RelevanceAnalysis:
    """相关性分析结果"""
    source_id: str = ""                    # 数据源ID
    relevance_score: float = 0.0          # 相关性评分（0-1）
    is_relevant: bool = False             # 是否相关
    reasoning: str = ""                   # 相关性判断理由
    key_matches: List[str] = field(default_factory=list)  # 关键匹配点
    usage_recommendation: str = ""        # 使用建议
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "source_id": self.source_id,
            "relevance_score": self.relevance_score,
            "is_relevant": self.is_relevant,
            "reasoning": self.reasoning,
            "key_matches": self.key_matches,
            "usage_recommendation": self.usage_recommendation,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelevanceAnalysis":
        """从字典创建RelevanceAnalysis对象"""
        return cls(
            source_id=data.get("source_id", ""),
            relevance_score=data.get("relevance_score", 0.0),
            is_relevant=data.get("is_relevant", False),
            reasoning=data.get("reasoning", ""),
            key_matches=data.get("key_matches", []),
            usage_recommendation=data.get("usage_recommendation", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat())
        )


@dataclass
class State:
    """DataSource Agent状态"""
    query: str = ""                        # 用户查询
    data_sources: List[DataSourceItem] = field(default_factory=list)  # 数据源列表
    relevance_analyses: List[RelevanceAnalysis] = field(default_factory=list)  # 相关性分析结果
    filtered_data_sources: List[str] = field(default_factory=list)  # 过滤后的相关数据源ID列表
    usage_strategy: str = ""              # 数据使用策略
    is_completed: bool = False            # 是否完成分析
    
    def add_data_source(self, source: DataSourceItem):
        """添加数据源"""
        self.data_sources.append(source)
    
    def add_relevance_analysis(self, analysis: RelevanceAnalysis):
        """添加相关性分析"""
        self.relevance_analyses.append(analysis)
        # 如果相关，添加到过滤后的列表
        if analysis.is_relevant:
            if analysis.source_id not in self.filtered_data_sources:
                self.filtered_data_sources.append(analysis.source_id)
    
    def mark_completed(self):
        """标记为完成"""
        self.is_completed = True
    
    def get_relevant_sources(self) -> List[str]:
        """获取相关数据源ID列表"""
        return self.filtered_data_sources
    
    def get_relevance_analysis(self, source_id: str) -> Optional[RelevanceAnalysis]:
        """根据source_id获取相关性分析"""
        for analysis in self.relevance_analyses:
            if analysis.source_id == source_id:
                return analysis
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "query": self.query,
            "data_sources": [source.to_dict() for source in self.data_sources],
            "relevance_analyses": [analysis.to_dict() for analysis in self.relevance_analyses],
            "filtered_data_sources": self.filtered_data_sources,
            "usage_strategy": self.usage_strategy,
            "is_completed": self.is_completed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "State":
        """从字典创建State对象"""
        data_sources = [DataSourceItem.from_dict(source_data) for source_data in data.get("data_sources", [])]
        relevance_analyses = [RelevanceAnalysis.from_dict(analysis_data) for analysis_data in data.get("relevance_analyses", [])]
        return cls(
            query=data.get("query", ""),
            data_sources=data_sources,
            relevance_analyses=relevance_analyses,
            filtered_data_sources=data.get("filtered_data_sources", []),
            usage_strategy=data.get("usage_strategy", ""),
            is_completed=data.get("is_completed", False)
        )
    
    def save_to_file(self, filepath: str):
        """保存状态到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> "State":
        """从文件加载状态"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        return {
            "query": self.query,
            "total_sources": len(self.data_sources),
            "analyzed_sources": len(self.relevance_analyses),
            "relevant_sources": len(self.filtered_data_sources),
            "is_completed": self.is_completed
        }

