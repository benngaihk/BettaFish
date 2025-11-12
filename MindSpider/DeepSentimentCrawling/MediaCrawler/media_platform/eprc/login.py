# -*- coding: utf-8 -*-
"""
EPRC 登录模块（如果需要登录）
EPRC网站通常不需要登录，但保留此模块以备后用
"""

from typing import Optional
from playwright.async_api import BrowserContext, Page

import config
from base.base_crawler import AbstractLogin
from tools import utils


class EPRCLogin(AbstractLogin):
    """EPRC登录类（通常不需要登录）"""

    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = ""):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    async def begin(self):
        """开始登录"""
        utils.logger.info("[EPRCLogin.begin] EPRC网站通常不需要登录")
        if config.LOGIN_TYPE == "cookie" and self.cookie_str:
            await self.login_by_cookies()
        # EPRC网站主要是公开数据，通常不需要登录

    async def login_by_qrcode(self):
        """二维码登录（EPRC通常不需要）"""
        utils.logger.info("[EPRCLogin.login_by_qrcode] EPRC网站通常不需要登录")
        pass

    async def login_by_mobile(self):
        """手机号登录（EPRC通常不需要）"""
        utils.logger.info("[EPRCLogin.login_by_mobile] EPRC网站通常不需要登录")
        pass

    async def login_by_cookies(self):
        """Cookie登录"""
        if not self.cookie_str:
            utils.logger.warning("[EPRCLogin.login_by_cookies] Cookie字符串为空")
            return
        
        try:
            cookies = utils.convert_str_cookie_to_dict(self.cookie_str)
            await self.browser_context.add_cookies(cookies)
            utils.logger.info("[EPRCLogin.login_by_cookies] Cookie登录成功")
        except Exception as e:
            utils.logger.error(f"[EPRCLogin.login_by_cookies] Cookie登录失败: {e}")

