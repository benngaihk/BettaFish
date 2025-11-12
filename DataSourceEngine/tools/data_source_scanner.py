"""
数据源文件夹扫描器
用于扫描 DataSourceEngine/data_source 文件夹中的所有 JSON 文件
支持生成文件摘要和关键字，并缓存结果以提高效率
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger


class DataSourceScanner:
    """数据源文件夹扫描器"""
    
    def __init__(self, data_source_dir: Optional[str] = None):
        """
        初始化扫描器
        
        Args:
            data_source_dir: 数据源文件夹路径，默认为 DataSourceEngine/data_source
        """
        if data_source_dir is None:
            # 默认使用 DataSourceEngine/data_source
            current_dir = Path(__file__).parent.parent  # tools -> DataSourceEngine
            self.data_source_dir = current_dir / "data_source"
        else:
            self.data_source_dir = Path(data_source_dir)
        
        # 确保文件夹存在
        self.data_source_dir.mkdir(parents=True, exist_ok=True)
        
        # 摘要缓存目录
        self.summary_cache_dir = self.data_source_dir / ".summaries"
        self.summary_cache_dir.mkdir(exist_ok=True)
        
        logger.info(f"数据源文件夹路径: {self.data_source_dir}")
        logger.info(f"摘要缓存目录: {self.summary_cache_dir}")
    
    def scan_json_files(self) -> List[Dict[str, Any]]:
        """
        扫描文件夹中的所有 JSON 文件
        
        Returns:
            包含文件信息的列表，每个元素包含：
            - file_path: 文件路径
            - file_name: 文件名
            - file_size: 文件大小（字节）
            - is_valid: 是否为有效的 JSON 文件
            - error: 如果无效，错误信息
        """
        json_files = []
        
        if not self.data_source_dir.exists():
            logger.warning(f"数据源文件夹不存在: {self.data_source_dir}")
            return json_files
        
        # 扫描所有 .json 文件
        for file_path in self.data_source_dir.glob("*.json"):
            file_info = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "is_valid": False,
                "error": None
            }
            
            # 验证 JSON 文件是否有效
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                file_info["is_valid"] = True
                logger.debug(f"发现有效的 JSON 文件: {file_path.name}")
            except json.JSONDecodeError as e:
                file_info["error"] = f"JSON 格式错误: {str(e)}"
                logger.warning(f"JSON 文件格式错误 {file_path.name}: {str(e)}")
            except Exception as e:
                file_info["error"] = f"读取文件失败: {str(e)}"
                logger.error(f"读取文件失败 {file_path.name}: {str(e)}")
            
            json_files.append(file_info)
        
        logger.info(f"扫描完成，发现 {len(json_files)} 个 JSON 文件，其中 {sum(1 for f in json_files if f['is_valid'])} 个有效")
        return json_files
    
    def get_valid_json_files(self) -> List[str]:
        """
        获取所有有效的 JSON 文件路径
        
        Returns:
            有效的 JSON 文件路径列表
        """
        files = self.scan_json_files()
        return [f["file_path"] for f in files if f["is_valid"]]
    
    def get_file_summary(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件的摘要信息（不加载完整数据）
        
        Args:
            file_path: JSON 文件路径
            
        Returns:
            文件摘要信息，包含：
            - file_name: 文件名
            - file_size: 文件大小
            - data_type: 数据类型（list/dict/other）
            - item_count: 如果是列表，项目数量
            - sample_keys: 如果是字典，示例键
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return None
            
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            summary = {
                "file_name": file_path_obj.name,
                "file_size": file_path_obj.stat().st_size,
                "data_type": type(data).__name__
            }
            
            if isinstance(data, list):
                summary["item_count"] = len(data)
                if len(data) > 0 and isinstance(data[0], dict):
                    summary["sample_keys"] = list(data[0].keys())[:5]
            elif isinstance(data, dict):
                summary["sample_keys"] = list(data.keys())[:10]
            
            return summary
            
        except Exception as e:
            logger.error(f"获取文件摘要失败 {file_path}: {str(e)}")
            return None
    
    def _get_file_hash(self, file_path: Path) -> str:
        """计算文件的 MD5 哈希值，用于检测文件是否更新"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return file_hash
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {str(e)}")
            return ""
    
    def _get_summary_cache_path(self, file_path: Path) -> Path:
        """获取摘要缓存文件路径"""
        file_name = file_path.stem
        return self.summary_cache_dir / f"{file_name}.summary.json"
    
    def _load_cached_summary(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载缓存的摘要"""
        cache_path = self._get_summary_cache_path(file_path)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # 检查文件是否已更新（通过文件大小和修改时间）
            current_size = file_path.stat().st_size
            current_mtime = file_path.stat().st_mtime
            
            if (cached_data.get("file_size") == current_size and 
                cached_data.get("file_mtime") == current_mtime):
                logger.debug(f"使用缓存的摘要: {file_path.name}")
                return cached_data
            else:
                logger.debug(f"文件已更新，需要重新生成摘要: {file_path.name}")
                return None
        except Exception as e:
            logger.warning(f"加载缓存摘要失败 {cache_path}: {str(e)}")
            return None
    
    def _save_summary_cache(self, file_path: Path, summary: Dict[str, Any]):
        """保存摘要到缓存"""
        cache_path = self._get_summary_cache_path(file_path)
        try:
            # 添加文件元信息
            summary["file_size"] = file_path.stat().st_size
            summary["file_mtime"] = file_path.stat().st_mtime
            summary["cached_at"] = datetime.now().isoformat()
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            logger.debug(f"摘要已缓存: {cache_path.name}")
        except Exception as e:
            logger.error(f"保存摘要缓存失败 {cache_path}: {str(e)}")
    
    def _extract_text_content(self, data: Any, max_length: int = 2000) -> str:
        """从数据中提取文本内容（用于生成摘要）"""
        text_parts = []
        
        if isinstance(data, dict):
            for key, value in list(data.items())[:20]:  # 限制键的数量
                if isinstance(value, str) and value:
                    text_parts.append(f"{key}: {value[:200]}")
                elif isinstance(value, (int, float)):
                    text_parts.append(f"{key}: {value}")
                elif isinstance(value, list) and len(value) > 0:
                    # 处理列表的前几个元素
                    for item in value[:3]:
                        if isinstance(item, str):
                            text_parts.append(f"{key}: {item[:100]}")
                        elif isinstance(item, dict):
                            for k, v in list(item.items())[:3]:
                                if isinstance(v, str) and v:
                                    text_parts.append(f"{k}: {v[:100]}")
        elif isinstance(data, list):
            for item in data[:10]:  # 只取前10个
                if isinstance(item, dict):
                    for key, value in list(item.items())[:5]:
                        if isinstance(value, str) and value:
                            text_parts.append(f"{key}: {value[:150]}")
                elif isinstance(item, str):
                    text_parts.append(item[:200])
        
        combined_text = "\n".join(text_parts)
        if len(combined_text) > max_length:
            combined_text = combined_text[:max_length] + "..."
        
        return combined_text
    
    def _extract_keywords(self, data: Any, max_keywords: int = 20) -> List[str]:
        """从数据中提取关键字"""
        keywords = set()
        
        def extract_from_value(value: Any, depth: int = 0):
            """递归提取关键字"""
            if depth > 3:  # 限制递归深度
                return
            
            if isinstance(value, str):
                # 提取中文关键词（长度大于1的中文字符串）
                if len(value) > 1 and any('\u4e00' <= char <= '\u9fff' for char in value):
                    # 提取2-6字的中文词组
                    words = []
                    for i in range(len(value) - 1):
                        for length in [2, 3, 4]:
                            if i + length <= len(value):
                                word = value[i:i+length]
                                if all('\u4e00' <= char <= '\u9fff' for char in word):
                                    words.append(word)
                    keywords.update(words[:max_keywords])
            elif isinstance(value, dict):
                # 键名可能是关键字
                for key in list(value.keys())[:10]:
                    if isinstance(key, str) and len(key) > 1:
                        keywords.add(key)
                    extract_from_value(value[key], depth + 1)
            elif isinstance(value, list):
                for item in value[:5]:
                    extract_from_value(item, depth + 1)
        
        extract_from_value(data)
        
        # 返回排序后的关键字列表（按长度和频率）
        return sorted(list(keywords), key=lambda x: (-len(x), x))[:max_keywords]
    
    def generate_file_summary(self, file_path: str, force_regenerate: bool = False) -> Optional[Dict[str, Any]]:
        """
        生成文件的详细摘要和关键字
        
        Args:
            file_path: JSON 文件路径
            force_regenerate: 是否强制重新生成（忽略缓存）
            
        Returns:
            包含摘要信息的字典：
            - file_name: 文件名
            - file_size: 文件大小
            - data_type: 数据类型
            - item_count: 项目数量（如果是列表）
            - sample_keys: 示例键
            - summary: 数据摘要文本
            - keywords: 关键字列表
            - data_structure: 数据结构描述
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return None
        
        # 检查缓存
        if not force_regenerate:
            cached = self._load_cached_summary(file_path_obj)
            if cached:
                return cached
        
        try:
            # 加载 JSON 数据
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            summary = {
                "file_name": file_path_obj.name,
                "file_size": file_path_obj.stat().st_size,
                "data_type": type(data).__name__,
                "generated_at": datetime.now().isoformat()
            }
            
            # 提取基本信息
            if isinstance(data, list):
                summary["item_count"] = len(data)
                if len(data) > 0:
                    if isinstance(data[0], dict):
                        summary["sample_keys"] = list(data[0].keys())[:10]
                    summary["summary"] = self._extract_text_content(data[:5], max_length=1500)
                    summary["keywords"] = self._extract_keywords(data[:10])
                    summary["data_structure"] = f"列表，包含 {len(data)} 个项目"
            elif isinstance(data, dict):
                summary["sample_keys"] = list(data.keys())[:15]
                summary["summary"] = self._extract_text_content(data, max_length=1500)
                summary["keywords"] = self._extract_keywords(data)
                
                # 尝试识别主要数据结构
                if "districts" in data:
                    summary["data_structure"] = "按地区组织的数据"
                elif "items" in data:
                    summary["data_structure"] = "包含项目列表的数据"
                else:
                    summary["data_structure"] = "字典结构"
            
            # 生成简短描述
            if "summary" in summary:
                summary_text = summary["summary"]
                # 提取前几行作为简短描述
                lines = summary_text.split("\n")[:5]
                summary["short_description"] = " | ".join(lines[:3])
            
            # 保存缓存
            self._save_summary_cache(file_path_obj, summary)
            
            logger.info(f"已生成文件摘要: {file_path_obj.name}")
            return summary
            
        except Exception as e:
            logger.error(f"生成文件摘要失败 {file_path}: {str(e)}")
            return None
    
    def list_all_files_summary(self, force_regenerate: bool = False) -> List[Dict[str, Any]]:
        """
        列出所有文件的详细摘要信息
        
        Args:
            force_regenerate: 是否强制重新生成所有摘要
            
        Returns:
            文件摘要列表
        """
        summaries = []
        valid_files = self.get_valid_json_files()
        
        for file_path in valid_files:
            summary = self.generate_file_summary(file_path, force_regenerate=force_regenerate)
            if summary:
                summaries.append(summary)
        
        return summaries
    
    def get_file_summary(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件的摘要信息（兼容旧接口，现在返回详细摘要）
        
        Args:
            file_path: JSON 文件路径
            
        Returns:
            文件摘要信息
        """
        return self.generate_file_summary(file_path)


# 创建全局实例
_scanner_instance = None


def get_scanner() -> DataSourceScanner:
    """获取全局扫描器实例"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = DataSourceScanner()
    return _scanner_instance


def scan_data_source_files() -> List[str]:
    """
    扫描数据源文件夹中的所有有效 JSON 文件
    
    Returns:
        有效的 JSON 文件路径列表
    """
    return get_scanner().get_valid_json_files()


def get_data_source_summaries(force_regenerate: bool = False) -> List[Dict[str, Any]]:
    """
    获取所有数据源文件的详细摘要信息（包含摘要文本和关键字）
    
    Args:
        force_regenerate: 是否强制重新生成所有摘要（忽略缓存）
    
    Returns:
        文件摘要列表，每个摘要包含：
        - file_name: 文件名
        - file_size: 文件大小
        - data_type: 数据类型
        - summary: 数据摘要文本
        - keywords: 关键字列表
        - short_description: 简短描述
        - data_structure: 数据结构描述
    """
    return get_scanner().list_all_files_summary(force_regenerate=force_regenerate)


def generate_file_summary(file_path: str, force_regenerate: bool = False) -> Optional[Dict[str, Any]]:
    """
    为单个文件生成详细摘要和关键字
    
    Args:
        file_path: JSON 文件路径
        force_regenerate: 是否强制重新生成（忽略缓存）
    
    Returns:
        文件摘要字典
    """
    return get_scanner().generate_file_summary(file_path, force_regenerate=force_regenerate)

