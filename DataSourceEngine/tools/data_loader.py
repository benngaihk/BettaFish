"""
数据源加载器
支持从多种数据源加载数据（JSON文件、API、数据库等）
"""

import json
import os
from typing import Dict, Any, List, Optional
from loguru import logger


class DataLoader:
    """数据源加载器"""
    
    @staticmethod
    def load_json_file(file_path: str, max_samples: int = 50) -> Dict[str, Any]:
        """
        从JSON文件加载数据
        
        Args:
            file_path: JSON文件路径
            max_samples: 最大样本数（用于预览）
            
        Returns:
            包含数据和元数据的字典
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 如果是列表，取前max_samples个作为预览
            if isinstance(data, list):
                preview_data = data[:max_samples] if len(data) > max_samples else data
                return {
                    "data": data,
                    "preview": preview_data,
                    "total_count": len(data),
                    "preview_count": len(preview_data),
                    "data_type": "list"
                }
            elif isinstance(data, dict):
                # 如果是字典，尝试提取一些键值对作为预览
                preview_items = {}
                count = 0
                for key, value in data.items():
                    if count >= max_samples:
                        break
                    preview_items[key] = value
                    count += 1
                
                return {
                    "data": data,
                    "preview": preview_items,
                    "total_count": len(data),
                    "preview_count": len(preview_items),
                    "data_type": "dict"
                }
            else:
                return {
                    "data": data,
                    "preview": data,
                    "total_count": 1,
                    "preview_count": 1,
                    "data_type": type(data).__name__
                }
                
        except Exception as e:
            logger.error(f"加载JSON文件失败: {str(e)}")
            raise
    
    @staticmethod
    def get_data_structure(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取数据结构信息
        
        Args:
            data: 数据字典
            
        Returns:
            结构信息字典
        """
        structure_info = {
            "data_type": data.get("data_type", "unknown"),
            "total_count": data.get("total_count", 0),
            "preview_count": data.get("preview_count", 0)
        }
        
        # 如果是列表，分析第一个元素的结构
        if data.get("data_type") == "list" and data.get("preview"):
            preview = data.get("preview", [])
            if preview and isinstance(preview, list) and len(preview) > 0:
                first_item = preview[0]
                if isinstance(first_item, dict):
                    structure_info["sample_keys"] = list(first_item.keys())
                    structure_info["sample_values"] = {k: str(v)[:100] for k, v in list(first_item.items())[:5]}
        
        # 如果是字典，分析键的结构
        elif data.get("data_type") == "dict" and data.get("preview"):
            preview = data.get("preview", {})
            if isinstance(preview, dict):
                structure_info["sample_keys"] = list(preview.keys())[:10]
                structure_info["sample_values"] = {k: str(v)[:100] for k, v in list(preview.items())[:5]}
        
        return structure_info
    
    @staticmethod
    def extract_text_content(data: Dict[str, Any], max_length: int = 5000) -> str:
        """
        从数据中提取文本内容（用于相关性分析）
        
        Args:
            data: 数据字典
            max_length: 最大文本长度
            
        Returns:
            提取的文本内容
        """
        text_parts = []
        
        preview = data.get("preview", {})
        
        if isinstance(preview, list):
            for item in preview[:10]:  # 只取前10个
                if isinstance(item, dict):
                    # 提取字典中的字符串值
                    for key, value in item.items():
                        if isinstance(value, str) and value:
                            text_parts.append(f"{key}: {value[:200]}")
                elif isinstance(item, str):
                    text_parts.append(item[:200])
        elif isinstance(preview, dict):
            for key, value in preview.items():
                if isinstance(value, str) and value:
                    text_parts.append(f"{key}: {value[:200]}")
                elif isinstance(value, (dict, list)):
                    text_parts.append(f"{key}: {str(value)[:200]}")
        
        combined_text = "\n".join(text_parts)
        if len(combined_text) > max_length:
            combined_text = combined_text[:max_length] + "..."
        
        return combined_text

