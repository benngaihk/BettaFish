# -*- coding: utf-8 -*-
"""
EPRC 数据存储实现
"""

import asyncio
from decimal import Decimal
from typing import Dict, Optional

from tools.async_file_writer import AsyncFileWriter
from base.base_crawler import AbstractStore
from tools import utils
from var import crawler_type_var
import config


def parse_price(price_str: str) -> Optional[Decimal]:
    """
    解析价格字符串，返回 Decimal 数值

    Args:
        price_str: 价格字符串，如 "12,345", "$12345", "12345.50*"

    Returns:
        Decimal: 解析后的数值，失败返回 None

    Examples:
        >>> parse_price("12,345")
        Decimal('12345.00')
        >>> parse_price("$12,345.50*")
        Decimal('12345.50')
        >>> parse_price("")
        None
    """
    if not price_str or not isinstance(price_str, str):
        return None

    try:
        # 移除逗号、星号、货币符号、空格等
        clean_str = price_str.replace(',', '').replace('*', '').replace('$', '').replace('HK$', '').strip()

        # 尝试转换为 Decimal
        if clean_str and clean_str.replace('.', '').replace('-', '').isdigit():
            return Decimal(clean_str).quantize(Decimal('0.01'))

        return None
    except Exception as e:
        utils.logger.warning(f"解析价格失败: {price_str} -> {e}")
        return None


class EPRCCsvStoreImplement(AbstractStore):
    """CSV存储实现"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="eprc", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        """存储内容到CSV"""
        await self.writer.write_to_csv(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        """存储评论到CSV（EPRC通常没有评论）"""
        await self.writer.write_to_csv(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        """存储创作者信息"""
        await self.writer.write_to_csv(item_type="creators", item=creator)


class EPRCDbStoreImplement(AbstractStore):
    """数据库存储实现"""
    async def store_content(self, content_item: Dict):
        """存储内容到数据库（根据source_keyword判断存储到哪个表）"""
        try:
            source_keyword = content_item.get("source_keyword", "")
            
            # 根据source_keyword判断存储到哪个表
            if source_keyword == "交易分析" or source_keyword == "赚蚀分析":
                await self.store_profit_loss(content_item)
            elif source_keyword == "成交排行榜":
                await self.store_ranking(content_item)
            else:
                # 其他类型数据存储到eprc_content表（需要过滤掉不支持的字段）
                await self.store_general_content(content_item)
        except Exception as e:
            utils.logger.error(f"存储EPRC数据到数据库失败: {e}")
            # 如果存储失败，尝试根据数据字段判断类型
            try:
                if "rank" in content_item or "highest_price" in content_item:
                    # 看起来是成交排行榜数据
                    content_item["source_keyword"] = "成交排行榜"
                    await self.store_ranking(content_item)
                elif "profit_cases" in content_item or "loss_cases" in content_item:
                    # 看起来是赚蚀分析数据
                    content_item["source_keyword"] = "交易分析"
                    await self.store_profit_loss(content_item)
            except Exception as e2:
                utils.logger.error(f"尝试根据字段判断类型存储失败: {e2}")
    
    async def store_profit_loss(self, content_item: Dict):
        """存储赚蚀分析数据到eprc_profit_loss表"""
        try:
            from database.db_session import get_session
            from database.models import EPRCProfitLoss
            from sqlalchemy import select
            import time

            async with get_session() as session:
                if session is None:
                    utils.logger.warning("数据库会话不可用，跳过数据库存储")
                    return

                # 准备数据
                profit_loss_data = {
                    "content_id": content_item.get("content_id", ""),
                    "region": content_item.get("region", ""),
                    "estate_name": content_item.get("estate_name", ""),
                    "profit_cases": content_item.get("profit_cases", 0),
                    "profit_range": content_item.get("profit_range", ""),
                    "loss_cases": content_item.get("loss_cases", 0),
                    "loss_range": content_item.get("loss_range", ""),
                    "title": content_item.get("title", ""),
                    "content_text": content_item.get("content_text", ""),
                    "content_url": content_item.get("content_url", ""),
                    "page_num": content_item.get("page_num", 1),
                    "record_date": content_item.get("data_date", "") or content_item.get("record_date", ""),  # 兼容旧字段名
                    "created_time": str(int(time.time())),
                    "add_ts": utils.get_current_timestamp(),
                    "last_modify_ts": utils.get_current_timestamp(),
                }

                result = await session.execute(
                    select(EPRCProfitLoss).where(
                        EPRCProfitLoss.content_id == profit_loss_data["content_id"]
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # 更新
                    for key, value in profit_loss_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                else:
                    # 插入
                    profit_loss = EPRCProfitLoss(**profit_loss_data)
                    session.add(profit_loss)

                await session.commit()
        except Exception as e:
            utils.logger.error(f"存储赚蚀分析数据到数据库失败: {e}")
    
    async def store_ranking(self, content_item: Dict):
        """存储成交排行榜数据到eprc_ranking表"""
        try:
            from database.db_session import get_session
            from database.models import EPRCRanking
            from sqlalchemy import select
            import time

            async with get_session() as session:
                if session is None:
                    utils.logger.warning("数据库会话不可用，跳过数据库存储")
                    return

                # 解析排名（可能是字符串，需要提取数字）
                rank_str = content_item.get("rank", "") or ""
                rank = 0
                if rank_str:
                    import re
                    rank_match = re.search(r'\d+', str(rank_str))
                    if rank_match:
                        rank = int(rank_match.group())

                # 解析价格字段（转换为 Decimal）
                highest_price = parse_price(content_item.get("highest_price", ""))
                lowest_price = parse_price(content_item.get("lowest_price", ""))
                avg_price = parse_price(
                    content_item.get("avg_price", "") or content_item.get("price", "")
                )

                # 准备数据
                ranking_data = {
                    "content_id": content_item.get("content_id", ""),
                    "rank": rank,
                    "estate_name": content_item.get("estate_name", ""),
                    "region": content_item.get("region", ""),
                    "transaction_count": content_item.get("transaction_count", 0),
                    "highest_price": highest_price,  # Decimal 类型
                    "lowest_price": lowest_price,    # Decimal 类型
                    "avg_price": avg_price,          # Decimal 类型
                    "title": content_item.get("title", ""),
                    "content_text": content_item.get("content_text", ""),
                    "content_url": content_item.get("content_url", ""),
                    "page_num": content_item.get("page_num", 1),
                    "record_date": content_item.get("data_date", "") or content_item.get("record_date", ""),  # 兼容旧字段名
                    "created_time": str(int(time.time())),
                    "add_ts": utils.get_current_timestamp(),
                    "last_modify_ts": utils.get_current_timestamp(),
                }

                result = await session.execute(
                    select(EPRCRanking).where(
                        EPRCRanking.content_id == ranking_data["content_id"]
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # 更新
                    for key, value in ranking_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                else:
                    # 插入
                    ranking = EPRCRanking(**ranking_data)
                    session.add(ranking)

                await session.commit()
        except Exception as e:
            utils.logger.error(f"存储成交排行榜数据到数据库失败: {e}")
    
    async def store_general_content(self, content_item: Dict):
        """存储其他类型数据到eprc_content表（只保存通用字段）"""
        try:
            from database.db_session import get_session
            from database.models import EPRCContent
            from sqlalchemy import select
            import time

            async with get_session() as session:
                if session is None:
                    utils.logger.warning("数据库会话不可用，跳过数据库存储")
                    return

                # 只保留通用字段
                general_fields = {
                    "content_id": content_item.get("content_id", ""),
                    "title": content_item.get("title", ""),
                    "content_text": content_item.get("content_text", ""),
                    "content_url": content_item.get("content_url", ""),
                    "record_date": content_item.get("data_date", "") or content_item.get("record_date", ""),  # 兼容旧字段名
                    "source_keyword": content_item.get("source_keyword", ""),  # 来源关键词
                    "created_time": str(int(time.time())),
                    "add_ts": utils.get_current_timestamp(),
                    "last_modify_ts": utils.get_current_timestamp(),
                }

                result = await session.execute(
                    select(EPRCContent).where(
                        EPRCContent.content_id == general_fields.get("content_id", "")
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # 更新
                    for key, value in general_fields.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                else:
                    # 插入
                    content = EPRCContent(**general_fields)
                    session.add(content)

                await session.commit()
        except Exception as e:
            utils.logger.error(f"存储EPRC通用数据到数据库失败: {e}")

    async def store_comment(self, comment_item: Dict):
        """存储评论（EPRC通常没有评论）"""
        pass

    async def store_creator(self, creator: Dict):
        """存储创作者信息"""
        pass


# Store类已移至__init__.py中的Factory模式

