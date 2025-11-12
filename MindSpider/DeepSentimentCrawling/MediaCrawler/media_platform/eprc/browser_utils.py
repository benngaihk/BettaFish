# -*- coding: utf-8 -*-
"""
EPRC 浏览器工具函数
提供浏览器操作的辅助函数
"""

import asyncio
from typing import Optional
from playwright.async_api import BrowserContext, BrowserType, Page
from tools import utils


async def launch_browser_context(
    chromium: BrowserType,
    playwright_proxy: Optional[dict] = None,
    user_agent: Optional[str] = None,
    headless: bool = True,
    save_login_state: bool = False
) -> BrowserContext:
    """
    启动浏览器上下文

    Args:
        chromium: Playwright Chromium 浏览器类型
        playwright_proxy: 代理配置
        user_agent: User Agent
        headless: 是否无头模式
        save_login_state: 是否保存登录状态

    Returns:
        BrowserContext: 浏览器上下文
    """
    utils.logger.info("[browser_utils.launch_browser_context] 创建浏览器上下文...")

    if save_login_state:
        # 使用持久化上下文保存登录状态
        import os
        user_data_dir = os.path.join(os.getcwd(), "browser_data", "eprc")
        browser_context = await chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            accept_downloads=True,
            headless=headless,
            proxy=playwright_proxy,
            viewport={"width": 1920, "height": 1080},
            user_agent=user_agent,
            ignore_https_errors=True,
        )
    else:
        # 使用非持久化上下文
        browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
        browser_context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=user_agent,
            ignore_https_errors=True
        )

    return browser_context


async def wait_for_page_load(page: Page, timeout: int = 60000) -> None:
    """
    等待页面加载完成

    Args:
        page: Playwright Page 对象
        timeout: 超时时间（毫秒）
    """
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
        await asyncio.sleep(2)  # 额外等待JavaScript执行
    except Exception as e:
        utils.logger.warning(f"[browser_utils] 等待页面加载超时: {e}")


async def get_rendered_html(page: Page, check_frames: bool = True) -> str:
    """
    获取渲染后的HTML内容

    Args:
        page: Playwright Page 对象
        check_frames: 是否检查frame

    Returns:
        str: HTML内容
    """
    try:
        # 检查是否有frame
        if check_frames:
            frames = page.frames
            if len(frames) > 1:
                utils.logger.info(f"[browser_utils] 检测到 {len(frames)} 个frame")

                # 尝试访问主要内容frame
                for frame in frames:
                    if frame.name == "topFrame" or "main" in frame.url.lower():
                        utils.logger.info(f"[browser_utils] 访问frame: {frame.name}, URL: {frame.url}")
                        await frame.wait_for_load_state("networkidle", timeout=30000)
                        await asyncio.sleep(2)
                        return await frame.content()

                # 如果没有找到特定frame，使用第一个非主frame
                for frame in frames[1:]:
                    utils.logger.info(f"[browser_utils] 访问frame: {frame.name}, URL: {frame.url}")
                    await frame.wait_for_load_state("networkidle", timeout=30000)
                    await asyncio.sleep(2)
                    return await frame.content()

        # 没有frame或frame访问失败，使用主页面
        return await page.content()

    except Exception as e:
        utils.logger.error(f"[browser_utils] 获取HTML内容失败: {e}")
        return await page.content()


async def click_next_page(page: Page) -> bool:
    """
    点击"下一页"按钮

    Args:
        page: Playwright Page 对象

    Returns:
        bool: 是否成功点击
    """
    try:
        # 尝试多种选择器
        next_selectors = [
            "a:has-text('下一頁')",
            "text=下一頁",
            "button:has-text('下一頁')",
            "[class*='next']",
            "[class*='下一页']"
        ]

        for selector in next_selectors:
            try:
                next_button = await page.query_selector(selector)
                if next_button:
                    # 检查按钮是否可点击
                    is_disabled = await next_button.evaluate(
                        "el => el.disabled || el.classList.contains('disabled')"
                    )
                    if not is_disabled:
                        await next_button.click()
                        await asyncio.sleep(3)
                        await page.wait_for_load_state("networkidle")
                        return True
                    else:
                        utils.logger.info("[browser_utils] 下一页按钮已禁用")
                        return False
            except:
                continue

        utils.logger.info("[browser_utils] 未找到下一页按钮")
        return False

    except Exception as e:
        utils.logger.warning(f"[browser_utils] 点击下一页失败: {e}")
        return False


async def click_page_number(page: Page, page_num: int) -> bool:
    """
    点击指定页码按钮

    Args:
        page: Playwright Page 对象
        page_num: 页码

    Returns:
        bool: 是否成功点击
    """
    try:
        page_selectors = [
            f"a:has-text('{page_num}')",
            f"button:has-text('{page_num}')"
        ]

        for selector in page_selectors:
            try:
                page_links = await page.query_selector_all(selector)
                if page_links:
                    await page_links[0].click()
                    await asyncio.sleep(3)
                    await page.wait_for_load_state("networkidle")
                    return True
            except:
                continue

        return False

    except Exception as e:
        utils.logger.warning(f"[browser_utils] 点击页码 {page_num} 失败: {e}")
        return False


async def extract_table_rows(page: Page, table_keywords: list) -> list:
    """
    提取表格行数据（Playwright模式）

    Args:
        page: Playwright Page 对象
        table_keywords: 表格关键词列表

    Returns:
        list: 行数据列表
    """
    try:
        # 等待表格加载
        await page.wait_for_selector("table", timeout=10000)

        tables = await page.query_selector_all("table")

        for table in tables:
            rows = await table.query_selector_all("tr")
            if len(rows) < 2:
                continue

            # 检查表头
            header_row = rows[0]
            header_cells = await header_row.query_selector_all("th, td")
            header_texts = [await cell.inner_text() for cell in header_cells]
            header_text = ' '.join(header_texts)

            if any(keyword in header_text for keyword in table_keywords):
                return rows, header_texts

        return [], []

    except Exception as e:
        utils.logger.error(f"[browser_utils] 提取表格行失败: {e}")
        return [], []
