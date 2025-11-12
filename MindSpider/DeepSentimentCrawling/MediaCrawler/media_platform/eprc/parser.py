# -*- coding: utf-8 -*-
"""
EPRC 数据解析模块
公共的表格解析逻辑，支持浏览器和 BeautifulSoup 两种模式
"""

import re
from typing import Dict, List, Optional
from tools import utils


def parse_number(text: str) -> int:
    """
    解析数字字符串

    Args:
        text: 包含数字的字符串，如 "12,345", "-100"

    Returns:
        int: 解析后的整数，失败返回 0

    Examples:
        >>> parse_number("12,345")
        12345
        >>> parse_number("-100")
        -100
    """
    if not text:
        return 0
    # 移除逗号和其他非数字字符（保留负号）
    numbers = re.findall(r'-?\d+', text.replace(',', ''))
    return int(numbers[0]) if numbers else 0


def parse_rank(rank_str: str) -> int:
    """
    解析排名字符串，提取数字

    Args:
        rank_str: 排名字符串，如 "1", "第1名", "No.1"

    Returns:
        int: 排名数字
    """
    if not rank_str:
        return 0
    rank_match = re.search(r'\d+', str(rank_str))
    return int(rank_match.group()) if rank_match else 0


def map_table_columns(header_texts: List[str], column_keywords: Dict[str, List[str]]) -> Dict[str, int]:
    """
    动态映射表格列索引

    Args:
        header_texts: 表头文本列表
        column_keywords: 列名关键词映射，如 {'rank': ['排名', 'rank'], 'estate_name': ['屋苑', 'estate']}

    Returns:
        Dict[str, int]: 列名到索引的映射

    Examples:
        >>> header_texts = ['排名', '屋苑名称', '地区']
        >>> keywords = {'rank': ['排名'], 'estate_name': ['屋苑'], 'region': ['地区']}
        >>> map_table_columns(header_texts, keywords)
        {'rank': 0, 'estate_name': 1, 'region': 2}
    """
    col_map = {}
    for idx, header in enumerate(header_texts):
        header_lower = header.lower().strip()
        for col_name, keywords in column_keywords.items():
            if any(kw in header or kw in header_lower for kw in keywords):
                col_map[col_name] = idx
                break
    return col_map


def get_ranking_column_keywords() -> Dict[str, List[str]]:
    """获取成交排行榜表格的列关键词映射"""
    return {
        'rank': ['排名', 'rank'],
        'estate_name': ['屋苑', 'estate', '名稱'],
        'region': ['地區', 'region', 'district'],
        'transaction_count': ['成交', '宗'],
        'highest_price': ['最高', '呎', 'price'],
        'lowest_price': ['最低', '呎', 'price'],
        'avg_price': ['平均', '呎', 'price']
    }


def get_profit_loss_column_keywords() -> Dict[str, List[str]]:
    """获取赚蚀分析表格的列关键词映射"""
    return {
        'region': ['地區', 'region', 'district'],
        'estate_name': ['代表性', '物業', 'estate', '屋苑'],
        'profit_cases': ['賺', 'profit', '宗'],
        'profit_range': ['賺', 'profit', '幅度'],
        'loss_cases': ['蝕', 'loss', '宗'],
        'loss_range': ['蝕', 'loss', '幅度']
    }


def is_valid_data_row(cells: List, min_cells: int = 5) -> bool:
    """
    检查是否是有效的数据行

    Args:
        cells: 单元格列表
        min_cells: 最小单元格数量

    Returns:
        bool: 是否有效
    """
    return len(cells) >= min_cells


def contains_table_keywords(header_text: str, keywords: List[str]) -> bool:
    """
    检查表头是否包含关键词

    Args:
        header_text: 表头文本
        keywords: 关键词列表

    Returns:
        bool: 是否包含任意一个关键词
    """
    return any(keyword in header_text for keyword in keywords)


def clean_cell_text(text: str) -> str:
    """
    清理单元格文本

    Args:
        text: 原始文本

    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    return text.strip()


def is_navigation_text(text: str) -> bool:
    """
    检查是否是导航文本（需要过滤）

    Args:
        text: 文本内容

    Returns:
        bool: 是否是导航文本
    """
    navigation_keywords = ['下一頁', '上一頁', '首页', '尾页', '...', 'Next', 'Previous']
    return any(kw in text for kw in navigation_keywords)


def validate_estate_data(estate_name: str, region: str = "", min_length: int = 2) -> bool:
    """
    验证屋苑数据的有效性

    Args:
        estate_name: 屋苑名称
        region: 地区（可选）
        min_length: 最小长度

    Returns:
        bool: 数据是否有效
    """
    # 检查屋苑名称
    if not estate_name or len(estate_name.strip()) < min_length:
        return False

    # 检查是否是表头
    if estate_name in ['排名', '屋苑', 'Estate', 'Rank']:
        return False

    # 检查是否是导航文本
    if is_navigation_text(estate_name):
        return False

    # 如果提供了地区，也检查地区
    if region:
        if len(region.strip()) < min_length:
            return False
        if is_navigation_text(region):
            return False

    return True
