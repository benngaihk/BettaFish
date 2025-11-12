"""
数据源共享工具
用于在多个 Engine 之间共享 DataSourceEngine 分析后的数据
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from pathlib import Path


class DataSourceRegistry:
    """
    数据源注册表
    用于跨 Engine 共享 DataSourceEngine 分析后的相关数据源
    """

    def __init__(self, storage_dir: str = "shared_data"):
        """
        初始化数据源注册表

        Args:
            storage_dir: 共享数据存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.registry_file = self.storage_dir / "data_source_registry.json"

        logger.info(f"DataSourceRegistry 已初始化，存储目录: {self.storage_dir}")

    def register_relevant_sources(
        self,
        query: str,
        relevant_sources: List[Dict[str, Any]],
        usage_strategy: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        注册相关数据源

        Args:
            query: 用户查询
            relevant_sources: 相关数据源列表，每个包含:
                - source_id: 数据源ID
                - source_path: 数据源路径
                - source_type: 数据源类型
                - relevance_score: 相关性评分
                - data_preview: 数据预览（可选）
                - full_data: 完整数据（可选）
            usage_strategy: 数据使用策略
            metadata: 额外的元数据

        Returns:
            注册ID（基于时间戳）
        """
        try:
            # 生成注册ID
            registration_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 构建注册数据
            registry_data = {
                "registration_id": registration_id,
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "relevant_sources": relevant_sources,
                "usage_strategy": usage_strategy,
                "metadata": metadata or {},
                "total_relevant_count": len(relevant_sources)
            }

            # 保存到文件
            registry_file_path = self.storage_dir / f"registry_{registration_id}.json"
            with open(registry_file_path, 'w', encoding='utf-8') as f:
                json.dump(registry_data, f, ensure_ascii=False, indent=2)

            # 更新主注册文件（记录所有注册）
            self._update_main_registry(registration_id, query, len(relevant_sources))

            logger.info(f"已注册 {len(relevant_sources)} 个相关数据源，注册ID: {registration_id}")
            return registration_id

        except Exception as e:
            logger.exception(f"注册数据源失败: {str(e)}")
            raise

    def _update_main_registry(self, registration_id: str, query: str, source_count: int):
        """更新主注册文件"""
        try:
            # 读取现有注册记录
            main_registry = []
            if self.registry_file.exists():
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    main_registry = json.load(f)

            # 添加新记录
            main_registry.append({
                "registration_id": registration_id,
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "source_count": source_count
            })

            # 只保留最近10条记录
            main_registry = main_registry[-10:]

            # 保存
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(main_registry, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"更新主注册文件失败: {str(e)}")

    def get_relevant_sources(self, registration_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取相关数据源

        Args:
            registration_id: 注册ID，如果不指定则获取最新的

        Returns:
            注册数据字典
        """
        try:
            # 如果没有指定ID，获取最新的
            if registration_id is None:
                registration_id = self._get_latest_registration_id()
                if registration_id is None:
                    logger.warning("没有找到任何注册记录")
                    return {
                        "relevant_sources": [],
                        "usage_strategy": "",
                        "query": "",
                        "total_relevant_count": 0
                    }

            # 读取注册文件
            registry_file_path = self.storage_dir / f"registry_{registration_id}.json"
            if not registry_file_path.exists():
                logger.error(f"注册文件不存在: {registry_file_path}")
                return {
                    "relevant_sources": [],
                    "usage_strategy": "",
                    "query": "",
                    "total_relevant_count": 0
                }

            with open(registry_file_path, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)

            logger.info(f"已加载注册数据，ID: {registration_id}, 数据源数量: {len(registry_data.get('relevant_sources', []))}")
            return registry_data

        except Exception as e:
            logger.exception(f"获取相关数据源失败: {str(e)}")
            return {
                "relevant_sources": [],
                "usage_strategy": "",
                "query": "",
                "total_relevant_count": 0
            }

    def _get_latest_registration_id(self) -> Optional[str]:
        """获取最新的注册ID"""
        try:
            if not self.registry_file.exists():
                return None

            with open(self.registry_file, 'r', encoding='utf-8') as f:
                main_registry = json.load(f)

            if not main_registry:
                return None

            # 返回最新的注册ID
            return main_registry[-1]["registration_id"]

        except Exception as e:
            logger.error(f"获取最新注册ID失败: {str(e)}")
            return None

    def get_data_for_engine(self, engine_name: str, registration_id: Optional[str] = None) -> Dict[str, Any]:
        """
        为特定 Engine 获取相关数据

        Args:
            engine_name: Engine 名称（query, media, insight）
            registration_id: 注册ID，如果不指定则获取最新的

        Returns:
            为该 Engine 定制的数据字典
        """
        try:
            # 获取注册数据
            registry_data = self.get_relevant_sources(registration_id)

            if not registry_data.get("relevant_sources"):
                logger.warning(f"没有找到相关数据源供 {engine_name} 使用")
                return {
                    "has_data": False,
                    "sources": [],
                    "usage_strategy": "",
                    "query": ""
                }

            # 根据使用策略过滤数据源（如果策略中提到了特定 Engine）
            relevant_sources = registry_data["relevant_sources"]
            usage_strategy = registry_data.get("usage_strategy", "")

            # 简单的策略解析：检查策略中是否提到了该 Engine
            engine_keywords = {
                "query": ["Query Agent", "QueryEngine", "搜索", "查询"],
                "media": ["Media Agent", "MediaEngine", "媒体", "多模态"],
                "insight": ["Insight Agent", "InsightEngine", "舆情", "数据库"]
            }

            is_mentioned = any(keyword.lower() in usage_strategy.lower()
                             for keyword in engine_keywords.get(engine_name, []))

            # 构建返回数据
            result = {
                "has_data": len(relevant_sources) > 0,
                "sources": relevant_sources,
                "usage_strategy": usage_strategy,
                "query": registry_data.get("query", ""),
                "is_recommended": is_mentioned,  # 策略中是否推荐该 Engine 使用
                "total_count": len(relevant_sources)
            }

            logger.info(f"为 {engine_name} 准备了 {len(relevant_sources)} 个数据源，推荐使用: {is_mentioned}")
            return result

        except Exception as e:
            logger.exception(f"为 {engine_name} 获取数据失败: {str(e)}")
            return {
                "has_data": False,
                "sources": [],
                "usage_strategy": "",
                "query": ""
            }

    def clear_old_registrations(self, keep_recent: int = 5):
        """
        清理旧的注册数据

        Args:
            keep_recent: 保留最近的N条记录
        """
        try:
            # 读取主注册文件
            if not self.registry_file.exists():
                return

            with open(self.registry_file, 'r', encoding='utf-8') as f:
                main_registry = json.load(f)

            if len(main_registry) <= keep_recent:
                return

            # 获取要删除的注册ID
            to_delete = main_registry[:-keep_recent]

            # 删除旧的注册文件
            for record in to_delete:
                registration_id = record["registration_id"]
                registry_file_path = self.storage_dir / f"registry_{registration_id}.json"
                if registry_file_path.exists():
                    registry_file_path.unlink()

            # 更新主注册文件
            main_registry = main_registry[-keep_recent:]
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(main_registry, f, ensure_ascii=False, indent=2)

            logger.info(f"已清理旧的注册数据，保留最近 {keep_recent} 条")

        except Exception as e:
            logger.exception(f"清理旧注册数据失败: {str(e)}")


# 全局注册表实例
_global_registry = None


def get_registry(storage_dir: str = "shared_data") -> DataSourceRegistry:
    """
    获取全局注册表实例

    Args:
        storage_dir: 存储目录

    Returns:
        DataSourceRegistry 实例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = DataSourceRegistry(storage_dir)
    return _global_registry
