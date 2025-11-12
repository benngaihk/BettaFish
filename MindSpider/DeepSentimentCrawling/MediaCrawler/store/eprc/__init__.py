# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

# -*- coding: utf-8 -*-
from typing import Dict
import config
from base.base_crawler import AbstractStore
from ._store_impl import EPRCCsvStoreImplement, EPRCDbStoreImplement
from tools import utils
from var import source_keyword_var


class EPRCStoreFactory:
    STORES = {
        "csv": EPRCCsvStoreImplement,
        "db": EPRCDbStoreImplement,
        "json": EPRCCsvStoreImplement,  # JSON使用CSV实现
        "sqlite": EPRCCsvStoreImplement,  # SQLite使用CSV实现
        "postgresql": EPRCDbStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = EPRCStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[EPRCStoreFactory.create_store] Invalid save option")
        return store_class()


async def update_eprc_content(content_item: Dict):
    """更新EPRC内容"""
    # 优先使用数据中已有的source_keyword，如果没有则使用全局变量
    if "source_keyword" not in content_item or not content_item.get("source_keyword"):
        content_item["source_keyword"] = source_keyword_var.get()
    content_item.update({"last_modify_ts": utils.get_current_timestamp()})
    utils.logger.info(f"[store.eprc.update_eprc_content] eprc content: {content_item}")
    await EPRCStoreFactory.create_store().store_content(content_item)


async def update_eprc_comment(comment_item: Dict):
    """更新EPRC评论"""
    comment_item.update({"last_modify_ts": utils.get_current_timestamp()})
    utils.logger.info(f"[store.eprc.update_eprc_comment] eprc comment: {comment_item}")
    await EPRCStoreFactory.create_store().store_comment(comment_item)


async def save_eprc_creator(creator: Dict):
    """保存EPRC创作者信息"""
    if not creator:
        return
    creator.update({"last_modify_ts": utils.get_current_timestamp()})
    await EPRCStoreFactory.create_store().store_creator(creator)


# 为了兼容性，提供store_content等函数
async def store_content(content_item: Dict):
    """存储内容"""
    await update_eprc_content(content_item)


async def store_comment(comment_item: Dict):
    """存储评论"""
    await update_eprc_comment(comment_item)


async def store_creator(creator: Dict):
    """存储创作者"""
    await save_eprc_creator(creator)

