# -*- coding: utf-8 -*-
"""
EPRC 香港房地产数据网站爬虫
网站: https://eprc.com.hk/index.htm

注意：由于Playwright浏览器在某些macOS系统上可能崩溃，
本爬虫优先使用requests+BeautifulSoup方式（更稳定）
如果需要在浏览器中执行JS，可以设置 USE_BROWSER = True
"""

import asyncio
import re
import time
from typing import Dict, List, Optional

import config
from base.base_crawler import AbstractCrawler
from store import eprc as eprc_store
from tools import utils
from var import crawler_type_var, source_keyword_var

# 尝试导入requests和BeautifulSoup
try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    utils.logger.warning("[EPRCCrawler] requests或BeautifulSoup未安装，将尝试使用Playwright")

# 尝试导入Playwright（可选）
try:
    from playwright.async_api import BrowserContext, BrowserType, Page, async_playwright
    from tools.cdp_browser import CDPBrowserManager
    from .login import EPRCLogin
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    utils.logger.warning("[EPRCCrawler] Playwright未安装，将只能使用requests模式")


class EPRCCrawler(AbstractCrawler):
    """EPRC 香港房地产数据爬虫"""
    
    context_page: Page
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://eprc.com.hk/index.htm"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        self.cdp_manager = None
        self.data_date = None  # 数据日期（当前日期的前一天）

    def get_data_date(self) -> str:
        """
        获取数据记录日期（昨天的日期）

        说明：EPRC 网站显示的是前一天（昨天）的房地产交易数据
        例如：今天是 2025-11-13，网站显示的数据日期是 2025-11-12

        Returns:
            str: YYYY-MM-DD 格式的日期字符串（前一天）

        Examples:
            >>> # 假设今天是 2025-11-13
            >>> crawler = EPRCCrawler()
            >>> crawler.get_data_date()
            '2025-11-12'
        """
        try:
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            return yesterday.strftime("%Y-%m-%d")
        except Exception as e:
            utils.logger.error(f"[EPRCCrawler] 获取数据日期失败: {e}")
            # 如果出错，返回空字符串
            return ""

    async def launch_browser(self, chromium: BrowserType, 
                           playwright_proxy: Optional[Dict], 
                           user_agent: Optional[str], 
                           headless: bool = True) -> BrowserContext:
        """启动浏览器"""
        utils.logger.info("[EPRCCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
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
            return browser_context
        else:
            # 使用非持久化上下文（避免浏览器崩溃问题）
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}, 
                user_agent=user_agent,
                ignore_https_errors=True
            )
            return browser_context

    async def start(self) -> None:
        """
        启动爬虫

        优先级：
        1. 如果配置了 EPRC_USE_BROWSER=True，使用浏览器模式
        2. 否则优先使用 requests 模式（更稳定）
        3. 如果 requests 失败，回退到浏览器模式
        """
        # 检查配置，是否强制使用浏览器模式
        use_browser = getattr(config, 'EPRC_USE_BROWSER', False)

        if use_browser or (not REQUESTS_AVAILABLE):
            # 强制使用浏览器模式
            if not PLAYWRIGHT_AVAILABLE:
                raise Exception("配置要求使用浏览器模式，但Playwright未安装")
            await self.start_with_browser()
            return

        # 尝试requests方式（推荐）
        if REQUESTS_AVAILABLE:
            try:
                await self.start_with_requests()
                return
            except Exception as e:
                utils.logger.warning(f"[EPRCCrawler] requests方式失败: {e}")
                if PLAYWRIGHT_AVAILABLE:
                    utils.logger.info("[EPRCCrawler] 切换到浏览器模式...")
                    await self.start_with_browser()
                else:
                    raise
        else:
            if PLAYWRIGHT_AVAILABLE:
                await self.start_with_browser()
            else:
                raise Exception("既没有requests也没有Playwright，无法运行")

    async def start_with_browser(self):
        """使用浏览器模式启动爬虫"""
        playwright_proxy_format, httpx_proxy_format = None, None
        
        if config.ENABLE_IP_PROXY:
            from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
            ip_proxy_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(
                ip_proxy_info
            )

        try:
            async with async_playwright() as playwright:
                # 尝试使用Firefox（可能更稳定）
                try:
                    utils.logger.info("[EPRCCrawler] 尝试使用Firefox浏览器...")
                    firefox = playwright.firefox
                    browser = await firefox.launch(headless=config.HEADLESS)
                    self.browser_context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent=self.user_agent,
                        ignore_https_errors=True
                    )
                    utils.logger.info("[EPRCCrawler] Firefox启动成功")
                except Exception as firefox_error:
                    utils.logger.warning(f"[EPRCCrawler] Firefox启动失败: {firefox_error}")
                    utils.logger.info("[EPRCCrawler] 尝试使用Chromium...")
                    
                    if config.ENABLE_CDP_MODE:
                        utils.logger.info("[EPRCCrawler] 使用CDP模式启动浏览器")
                        self.browser_context = await self.launch_browser_with_cdp(
                            playwright, playwright_proxy_format, 
                            self.user_agent, headless=config.CDP_HEADLESS
                        )
                    else:
                        utils.logger.info("[EPRCCrawler] 使用标准模式启动浏览器")
                        chromium = playwright.chromium
                        self.browser_context = await self.launch_browser(
                            chromium, None, self.user_agent, headless=config.HEADLESS
                        )
                        await self.browser_context.add_init_script(path="libs/stealth.min.js")

                self.context_page = await self.browser_context.new_page()
                # 等待页面完全加载，包括JavaScript执行
                await self.context_page.goto(self.index_url, wait_until="networkidle", timeout=60000)
                # 额外等待JavaScript执行
                await asyncio.sleep(3)
                
                # 检查是否有frame，如果有则访问frame内容
                frames = self.context_page.frames
                if len(frames) > 1:
                    # 有多个frame，尝试访问包含内容的frame
                    utils.logger.info(f"[EPRCCrawler] 检测到 {len(frames)} 个frame，尝试访问frame内容")
                    for frame in frames:
                        if frame.name == "topFrame" or "main" in frame.url.lower():
                            utils.logger.info(f"[EPRCCrawler] 访问frame: {frame.name}, URL: {frame.url}")
                            # 等待frame加载
                            await frame.wait_for_load_state("networkidle", timeout=30000)
                            await asyncio.sleep(2)
                            # 获取frame的HTML
                            rendered_html = await frame.content()
                            soup = BeautifulSoup(rendered_html, 'html.parser')
                            break
                    else:
                        # 如果没有找到特定frame，使用第一个非主frame
                        for frame in frames[1:]:
                            utils.logger.info(f"[EPRCCrawler] 访问frame: {frame.name}, URL: {frame.url}")
                            await frame.wait_for_load_state("networkidle", timeout=30000)
                            await asyncio.sleep(2)
                            rendered_html = await frame.content()
                            soup = BeautifulSoup(rendered_html, 'html.parser')
                            break
                        else:
                            # 如果都失败了，使用主页面
                            rendered_html = await self.context_page.content()
                            soup = BeautifulSoup(rendered_html, 'html.parser')
                else:
                    # 没有frame，直接使用主页面
                    rendered_html = await self.context_page.content()
                    soup = BeautifulSoup(rendered_html, 'html.parser')
                
                # 如果主页面内容很少，尝试直接访问main.html
                if soup and len(soup.get_text()) < 100:
                    utils.logger.info("[EPRCCrawler] 主页面内容较少，尝试直接访问main.html")
                    try:
                        main_url = "https://eprc.com.hk/main.html"
                        await self.context_page.goto(main_url, wait_until="networkidle", timeout=60000)
                        await asyncio.sleep(3)
                        rendered_html = await self.context_page.content()
                        soup = BeautifulSoup(rendered_html, 'html.parser')
                    except Exception as e:
                        utils.logger.warning(f"[EPRCCrawler] 访问main.html失败: {e}")

                # 获取数据日期（当前日期的前一天）
                self.data_date = self.get_data_date()
                utils.logger.info(f"[EPRCCrawler] 数据日期（前一天）: {self.data_date}")
                
                crawler_type_var.set(config.CRAWLER_TYPE)
                if config.CRAWLER_TYPE == "search":
                    # 使用渲染后的HTML进行提取
                    await self.search_with_soup(soup)
                elif config.CRAWLER_TYPE == "detail":
                    await self.get_specified_data()
                elif config.CRAWLER_TYPE == "trend":
                    await self.get_market_trends_with_soup(soup)

                utils.logger.info("[EPRCCrawler.start_with_browser] EPRC Crawler finished ...")
        except Exception as e:
            utils.logger.error(f"[EPRCCrawler] 浏览器模式失败: {e}")
            raise

    async def start_with_requests(self):
        """使用requests方式启动爬虫（尝试解析JavaScript动态内容）"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        try:
            utils.logger.info(f"[EPRCCrawler] 正在访问: {self.index_url}")
            response = session.get(self.index_url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            html = response.text
            
            # 尝试解析JavaScript动态内容
            soup = await self.parse_javascript_content(html)
            
            if soup is None:
                utils.logger.warning("[EPRCCrawler] 无法解析JavaScript内容，页面可能需要浏览器执行JS")
                # 如果requests无法解析，抛出异常，让上层决定是否使用浏览器
                raise Exception("页面内容通过JavaScript动态加载，需要浏览器支持")
            
            # 获取数据日期（当前日期的前一天）
            self.data_date = self.get_data_date()
            utils.logger.info(f"[EPRCCrawler] 数据日期（前一天）: {self.data_date}")
            
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search_with_soup(soup)
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_data()
            elif config.CRAWLER_TYPE == "trend":
                await self.get_market_trends_with_soup(soup)
            
            utils.logger.info("[EPRCCrawler.start_with_requests] 爬取完成")
        except Exception as e:
            utils.logger.error(f"[EPRCCrawler] requests方式失败: {e}")
            # 不再递归调用，让start()方法处理
            raise

    async def parse_javascript_content(self, html: str) -> Optional[BeautifulSoup]:
        """尝试解析JavaScript动态生成的内容"""
        import urllib.parse
        
        try:
            # 方法1: 查找document.write中的内容
            pattern = r"document\.write\(['\"]([^'\"]+)['\"]\)"
            matches = re.findall(pattern, html)
            
            if matches:
                utils.logger.info(f"[EPRCCrawler] 找到 {len(matches)} 个document.write调用")
                combined_html = ""
                for match in matches:
                    try:
                        decoded = urllib.parse.unquote(match)
                        combined_html += decoded
                    except:
                        combined_html += match
                
                if combined_html and ('<table' in combined_html or '<div' in combined_html):
                    soup = BeautifulSoup(combined_html, 'html.parser')
                    utils.logger.info("[EPRCCrawler] 成功解析JavaScript内容")
                    return soup
            
            # 方法2: 查找unescape中的编码内容
            pattern2 = r"unescape\(['\"]([^'\"]+)['\"]\)"
            matches2 = re.findall(pattern2, html)
            
            if matches2:
                utils.logger.info(f"[EPRCCrawler] 找到 {len(matches2)} 个unescape调用")
                combined_html = ""
                for match in matches2:
                    try:
                        decoded = urllib.parse.unquote(match)
                        combined_html += decoded
                    except:
                        combined_html += match
                
                if combined_html and ('<table' in combined_html or '<div' in combined_html):
                    soup = BeautifulSoup(combined_html, 'html.parser')
                    utils.logger.info("[EPRCCrawler] 成功解析unescape内容")
                    return soup
            
            # 方法3: 查找变量赋值中的编码内容
            pattern3 = r"m=['\"]([^'\"]+)['\"]"
            matches3 = re.findall(pattern3, html)
            
            if matches3:
                utils.logger.info(f"[EPRCCrawler] 找到 {len(matches3)} 个编码变量")
                for match in matches3:
                    try:
                        decoded = urllib.parse.unquote(match)
                        if '<table' in decoded or '<div' in decoded or len(decoded) > 1000:
                            soup = BeautifulSoup(decoded, 'html.parser')
                            # 检查是否包含实际数据
                            text = soup.get_text()
                            if any(keyword in text for keyword in ['屋苑', '成交', '价格', '地区']):
                                utils.logger.info("[EPRCCrawler] 成功解析变量中的内容")
                                return soup
                    except:
                        continue
            
            # 如果都失败了，返回原始HTML的soup（可能没有数据）
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()
            if len(text) > 100:  # 如果有足够的内容
                return soup
            
            return None
            
        except Exception as e:
            utils.logger.error(f"[EPRCCrawler] 解析JavaScript内容失败: {e}")
            return None

    async def check_login(self) -> bool:
        """检查登录状态（EPRC网站通常不需要登录）"""
        # 检查是否有登录相关的cookie或元素
        cookies = await self.browser_context.cookies()
        cookie_dict = {c['name']: c['value'] for c in cookies}
        # 根据实际网站调整检查逻辑
        return True  # 默认返回True，因为EPRC主要是公开数据

    async def search(self) -> None:
        """搜索房地产数据（浏览器模式）"""
        utils.logger.info("[EPRCCrawler.search] 开始抓取EPRC数据（浏览器模式）")
        
        # 1. 抓取指标屋苑数据
        await self.get_indicator_estates()
        
        # 2. 抓取交易分析数据
        await self.get_transaction_analysis()
        
        # 3. 抓取市场趋势数据
        await self.get_market_trends()
        
        # 4. 抓取屋苑价格数据
        await self.get_estate_prices()

    async def search_with_soup(self, soup: BeautifulSoup) -> None:
        """搜索房地产数据（requests模式）"""
        utils.logger.info("[EPRCCrawler.search_with_soup] 开始抓取EPRC数据（requests模式）")
        
        # 1. 抓取指标屋苑数据
        await self.get_indicator_estates_with_soup(soup)
        
        # 2. 抓取交易分析数据
        await self.get_transaction_analysis_with_soup(soup)
        
        # 3. 抓取市场趋势数据
        await self.get_market_trends_with_soup(soup)
        
        # 4. 抓取屋苑价格数据
        await self.get_estate_prices_with_soup(soup)

    async def get_indicator_estates(self) -> None:
        """抓取成交排行榜数据（浏览器模式，支持分页）"""
        utils.logger.info("[EPRCCrawler] 抓取成交排行榜数据（浏览器模式，支持分页）")
        
        try:
            # 等待页面加载
            await self.context_page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            # 查找并点击"成交排行榜"标签（如果存在）
            try:
                # 尝试多种选择器
                ranking_tab = await self.context_page.query_selector("a:has-text('成交排行榜')")
                if not ranking_tab:
                    ranking_tab = await self.context_page.query_selector("text=成交排行榜")
                if not ranking_tab:
                    ranking_tab = await self.context_page.query_selector("[class*='ranking']")
                if ranking_tab:
                    await ranking_tab.click()
                    await asyncio.sleep(2)
                    await self.context_page.wait_for_load_state("networkidle")
            except:
                pass
            
            # 分页抓取成交排行榜数据
            page_num = 1
            max_pages = 50  # 设置最大页数限制
            
            while page_num <= max_pages:
                utils.logger.info(f"[EPRCCrawler] 正在抓取成交排行榜第 {page_num} 页")
                
                # 等待表格加载
                try:
                    await self.context_page.wait_for_selector("table", timeout=10000)
                except:
                    utils.logger.warning(f"[EPRCCrawler] 第 {page_num} 页未找到表格")
                    break
                
                # 提取当前页面的数据
                tables = await self.context_page.query_selector_all("table")
                page_data_count = 0
                
                for table in tables:
                    rows = await table.query_selector_all("tr")
                    if len(rows) < 2:
                        continue
                    
                    # 检查表头并动态映射列
                    header_row = rows[0]
                    header_cells = await header_row.query_selector_all("th, td")
                    header_texts = [await cell.inner_text() for cell in header_cells]
                    header_text = ' '.join(header_texts)
                    
                    if not any(keyword in header_text for keyword in ['排名', '屋苑', '成交', '呎價', '地區']):
                        continue
                    
                    # 动态映射列索引
                    col_map = {}
                    for idx, header in enumerate(header_texts):
                        header_lower = header.lower().strip()
                        if '排名' in header or 'rank' in header_lower:
                            col_map['rank'] = idx
                        elif '屋苑' in header or 'estate' in header_lower or '名稱' in header:
                            col_map['estate_name'] = idx
                        elif '地區' in header or 'region' in header_lower or 'district' in header_lower:
                            col_map['region'] = idx
                        elif '成交' in header and '宗' in header:
                            col_map['transaction_count'] = idx
                        elif '最高' in header and ('呎' in header or 'price' in header_lower):
                            col_map['highest_price'] = idx
                        elif '最低' in header and ('呎' in header or 'price' in header_lower):
                            col_map['lowest_price'] = idx
                        elif '平均' in header and ('呎' in header or 'price' in header_lower):
                            col_map['avg_price'] = idx
                    
                    utils.logger.debug(f"[EPRCCrawler] 成交排行榜列映射: {col_map}")
                    utils.logger.debug(f"[EPRCCrawler] 表头: {header_texts}")
                    
                    # 提取数据行
                    for row in rows[1:]:
                        try:
                            cells = await row.query_selector_all("td")
                            if len(cells) < 5:
                                continue
                            
                            # 使用列映射提取数据
                            rank = await cells[col_map.get('rank', 0)].inner_text() if col_map.get('rank', 0) < len(cells) else ""
                            estate_name = await cells[col_map.get('estate_name', 1)].inner_text() if col_map.get('estate_name', 1) < len(cells) else ""
                            region = await cells[col_map.get('region', 2)].inner_text() if col_map.get('region', 2) < len(cells) else ""
                            transaction_count = await cells[col_map.get('transaction_count', 3)].inner_text() if col_map.get('transaction_count', 3) < len(cells) else ""
                            highest_price = await cells[col_map.get('highest_price', 4)].inner_text() if col_map.get('highest_price', 4) < len(cells) else ""
                            lowest_price = await cells[col_map.get('lowest_price', 5)].inner_text() if col_map.get('lowest_price', 5) < len(cells) else ""
                            avg_price = await cells[col_map.get('avg_price', 6)].inner_text() if col_map.get('avg_price', 6) < len(cells) else ""
                            
                            if not estate_name or estate_name.strip() == '排名' or not estate_name.strip():
                                continue
                            
                            # 解析排名数字
                            rank_num = 0
                            if rank:
                                import re
                                rank_match = re.search(r'\d+', str(rank))
                                if rank_match:
                                    rank_num = int(rank_match.group())
                            
                            estate_data = {
                                "content_id": f"ranking_{hash(str(page_num) + str(rank_num) + estate_name + region)}",
                                "title": f"{rank}. {estate_name} ({region})",
                                "content_text": f"成交宗数: {transaction_count}, 最高呎價: {highest_price}, 最低呎價: {lowest_price}, 平均呎價: {avg_price}",
                                "content_url": self.index_url,
                                "rank": rank_num,
                                "estate_name": estate_name.strip(),
                                "region": region.strip(),
                                "transaction_count": self.parse_number(transaction_count),
                                "highest_price": highest_price.replace(',', '').replace('*', '').strip() if highest_price else "",
                                "lowest_price": lowest_price.replace(',', '').replace('*', '').strip() if lowest_price else "",
                                "avg_price": avg_price.replace(',', '').replace('*', '').strip() if avg_price else "",
                                "price": avg_price.replace(',', '').replace('*', '').strip() if avg_price else "",  # 保留用于兼容
                                "page_num": page_num,
                                "data_date": self.data_date or "",  # 数据日期
                                "source_keyword": "成交排行榜",
                                "created_time": int(time.time()),
                            }
                            
                            await eprc_store.store_content(estate_data)
                            page_data_count += 1
                            
                        except Exception as e:
                            utils.logger.error(f"提取成交排行榜数据失败: {e}")
                            continue
                    
                    if page_data_count > 0:
                        break
                
                if page_data_count == 0:
                    utils.logger.info(f"[EPRCCrawler] 第 {page_num} 页没有数据，停止分页")
                    break
                
                utils.logger.info(f"[EPRCCrawler] 第 {page_num} 页成功提取 {page_data_count} 条数据")
                
                # 查找并点击"下一頁"按钮
                try:
                    # 尝试多种选择器
                    next_button = await self.context_page.query_selector("a:has-text('下一頁')")
                    if not next_button:
                        next_button = await self.context_page.query_selector("text=下一頁")
                    if not next_button:
                        next_button = await self.context_page.query_selector("button:has-text('下一頁')")
                    if not next_button:
                        next_button = await self.context_page.query_selector("[class*='next']")
                    if not next_button:
                        next_button = await self.context_page.query_selector("[class*='下一页']")
                    if next_button:
                        # 检查按钮是否可点击
                        is_disabled = await next_button.evaluate("el => el.disabled || el.classList.contains('disabled')")
                        if not is_disabled:
                            await next_button.click()
                            await asyncio.sleep(3)
                            await self.context_page.wait_for_load_state("networkidle")
                            page_num += 1
                        else:
                            utils.logger.info("[EPRCCrawler] 已到达最后一页")
                            break
                    else:
                        # 尝试点击页码按钮
                        page_links = await self.context_page.query_selector_all(
                            "a:has-text('" + str(page_num + 1) + "'), button:has-text('" + str(page_num + 1) + "')"
                        )
                        if page_links:
                            await page_links[0].click()
                            await asyncio.sleep(3)
                            await self.context_page.wait_for_load_state("networkidle")
                            page_num += 1
                        else:
                            utils.logger.info("[EPRCCrawler] 未找到下一页按钮，停止分页")
                            break
                except Exception as e:
                    utils.logger.warning(f"[EPRCCrawler] 查找下一页按钮失败: {e}")
                    break
                    
        except Exception as e:
            utils.logger.error(f"抓取成交排行榜数据失败: {e}")

    async def get_transaction_analysis(self) -> None:
        """抓取赚蚀分析数据（浏览器模式，支持分页）"""
        utils.logger.info("[EPRCCrawler] 抓取赚蚀分析数据（浏览器模式，支持分页）")
        
        try:
            # 等待页面加载
            await self.context_page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            # 查找并点击"赚蚀分析"标签（如果存在）
            try:
                # 尝试多种选择器
                profit_loss_tab = await self.context_page.query_selector("a:has-text('賺蝕分析')")
                if not profit_loss_tab:
                    profit_loss_tab = await self.context_page.query_selector("a:has-text('赚蚀分析')")
                if not profit_loss_tab:
                    profit_loss_tab = await self.context_page.query_selector("text=賺蝕分析")
                if not profit_loss_tab:
                    profit_loss_tab = await self.context_page.query_selector("text=赚蚀分析")
                if not profit_loss_tab:
                    profit_loss_tab = await self.context_page.query_selector("[class*='profit']")
                if not profit_loss_tab:
                    profit_loss_tab = await self.context_page.query_selector("[class*='loss']")
                if profit_loss_tab:
                    await profit_loss_tab.click()
                    await asyncio.sleep(2)
                    await self.context_page.wait_for_load_state("networkidle")
            except:
                pass
            
            # 分页抓取赚蚀分析数据
            page_num = 1
            max_pages = 50  # 设置最大页数限制（根据网页描述，赚蚀分析有23页）
            
            while page_num <= max_pages:
                utils.logger.info(f"[EPRCCrawler] 正在抓取赚蚀分析第 {page_num} 页")
                
                # 等待表格加载
                try:
                    await self.context_page.wait_for_selector("table", timeout=10000)
                except:
                    utils.logger.warning(f"[EPRCCrawler] 第 {page_num} 页未找到表格")
                    break
                
                # 提取当前页面的数据
                tables = await self.context_page.query_selector_all("table")
                page_data_count = 0
                
                for table in tables:
                    rows = await table.query_selector_all("tr")
                    if len(rows) < 2:
                        continue
                    
                    # 检查表头并动态映射列
                    header_row = rows[0]
                    header_cells = await header_row.query_selector_all("th, td")
                    header_texts = [await cell.inner_text() for cell in header_cells]
                    header_text = ' '.join(header_texts)
                    
                    if not any(keyword in header_text for keyword in ['地区', '赚', '蚀', '宗', '幅度']):
                        continue
                    
                    # 动态映射列索引
                    col_map = {}
                    for idx, header in enumerate(header_texts):
                        header_lower = header.lower().strip()
                        if '地區' in header or 'region' in header_lower or 'district' in header_lower:
                            col_map['region'] = idx
                        elif '代表性' in header or '物業' in header or 'estate' in header_lower or '屋苑' in header:
                            col_map['estate_name'] = idx
                        elif '賺' in header or 'profit' in header_lower:
                            if '宗' in header or 'cases' in header_lower:
                                col_map['profit_cases'] = idx
                            elif '幅度' in header or 'range' in header_lower:
                                col_map['profit_range'] = idx
                        elif '蝕' in header or 'loss' in header_lower:
                            if '宗' in header or 'cases' in header_lower:
                                col_map['loss_cases'] = idx
                            elif '幅度' in header or 'range' in header_lower:
                                col_map['loss_range'] = idx
                    
                    utils.logger.debug(f"[EPRCCrawler] 赚蚀分析列映射: {col_map}")
                    utils.logger.debug(f"[EPRCCrawler] 表头: {header_texts}")
                    
                    # 提取数据行
                    for row in rows[1:]:
                        try:
                            cells = await row.query_selector_all("td")
                            if len(cells) < 5:
                                continue
                            
                            # 使用列映射提取数据
                            region = await cells[col_map.get('region', 0)].inner_text() if col_map.get('region', 0) < len(cells) else ""
                            estate_name = await cells[col_map.get('estate_name', 1)].inner_text() if col_map.get('estate_name', 1) < len(cells) else ""
                            profit_cases = await cells[col_map.get('profit_cases', 2)].inner_text() if col_map.get('profit_cases', 2) < len(cells) else ""
                            profit_range = await cells[col_map.get('profit_range', 3)].inner_text() if col_map.get('profit_range', 3) < len(cells) else ""
                            loss_cases = await cells[col_map.get('loss_cases', 4)].inner_text() if col_map.get('loss_cases', 4) < len(cells) else ""
                            loss_range = await cells[col_map.get('loss_range', 5)].inner_text() if col_map.get('loss_range', 5) < len(cells) else ""
                            
                            if not region or not estate_name or region.strip() == '地区' or not estate_name.strip():
                                continue
                            # 过滤掉无效的数据（地区或屋苑名称太短）
                            if len(region.strip()) < 2 or len(estate_name.strip()) < 2:
                                continue
                            # 过滤掉包含页码或导航文本的数据
                            if '下一頁' in region or '下一頁' in estate_name or '...' in region or '...' in estate_name:
                                continue
                            
                            transaction_data = {
                                "content_id": f"txn_{hash(str(page_num) + region + estate_name)}",
                                "title": f"{region} - {estate_name} 交易分析",
                                "content_text": f"赚: {profit_cases}宗 ({profit_range}), 蚀: {loss_cases}宗 ({loss_range})",
                                "content_url": self.index_url,
                                "region": region.strip(),
                                "estate_name": estate_name.strip(),
                                "profit_cases": self.parse_number(profit_cases),
                                "profit_range": profit_range.strip(),
                                "loss_cases": self.parse_number(loss_cases),
                                "loss_range": loss_range.strip(),
                                "page_num": page_num,
                                "data_date": self.data_date or "",  # 数据日期
                                "source_keyword": "交易分析",
                                "created_time": int(time.time()),
                            }
                            
                            await eprc_store.store_content(transaction_data)
                            page_data_count += 1
                            
                        except Exception as e:
                            utils.logger.error(f"提取交易数据失败: {e}")
                            continue
                    
                    if page_data_count > 0:
                        break
                
                if page_data_count == 0:
                    utils.logger.info(f"[EPRCCrawler] 第 {page_num} 页没有数据，停止分页")
                    break
                
                utils.logger.info(f"[EPRCCrawler] 第 {page_num} 页成功提取 {page_data_count} 条数据")
                
                # 查找并点击"下一頁"按钮
                try:
                    # 尝试多种选择器
                    next_button = await self.context_page.query_selector("a:has-text('下一頁')")
                    if not next_button:
                        next_button = await self.context_page.query_selector("text=下一頁")
                    if not next_button:
                        next_button = await self.context_page.query_selector("button:has-text('下一頁')")
                    if not next_button:
                        next_button = await self.context_page.query_selector("[class*='next']")
                    if not next_button:
                        next_button = await self.context_page.query_selector("[class*='下一页']")
                    if next_button:
                        # 检查按钮是否可点击
                        is_disabled = await next_button.evaluate("el => el.disabled || el.classList.contains('disabled')")
                        if not is_disabled:
                            await next_button.click()
                            await asyncio.sleep(3)
                            await self.context_page.wait_for_load_state("networkidle")
                            page_num += 1
                        else:
                            utils.logger.info("[EPRCCrawler] 已到达最后一页")
                            break
                    else:
                        # 尝试点击页码按钮
                        page_links = await self.context_page.query_selector_all(
                            "a:has-text('" + str(page_num + 1) + "'), button:has-text('" + str(page_num + 1) + "')"
                        )
                        if page_links:
                            await page_links[0].click()
                            await asyncio.sleep(3)
                            await self.context_page.wait_for_load_state("networkidle")
                            page_num += 1
                        else:
                            utils.logger.info("[EPRCCrawler] 未找到下一页按钮，停止分页")
                            break
                except Exception as e:
                    utils.logger.warning(f"[EPRCCrawler] 查找下一页按钮失败: {e}")
                    break
                        
        except Exception as e:
            utils.logger.error(f"抓取赚蚀分析数据失败: {e}")

    async def get_market_trends(self) -> None:
        """抓取市场趋势数据"""
        utils.logger.info("[EPRCCrawler] 抓取市场趋势数据")
        
        try:
            # 查找市场动向新闻
            news_elements = await self.context_page.query_selector_all(
                ".news-item, .market-trend, [class*='news'], [class*='trend']"
            )
            
            for element in news_elements[:20]:  # 限制数量
                try:
                    news_data = await self.extract_news_data(element)
                    if news_data:
                        await eprc_store.store_content(news_data)
                except Exception as e:
                    utils.logger.error(f"提取新闻数据失败: {e}")
                    continue
            
            # 抓取成交宗数走势图数据
            await self.get_transaction_volume_trend()
            
        except Exception as e:
            utils.logger.error(f"抓取市场趋势数据失败: {e}")

    async def get_transaction_volume_trend(self) -> None:
        """抓取成交宗数走势图数据"""
        try:
            # 查找走势图数据表格
            trend_tables = await self.context_page.query_selector_all(
                "table:has-text('成交'), table:has-text('宗数'), table:has-text('登记月')"
            )
            
            for table in trend_tables:
                rows = await table.query_selector_all("tr")
                
                for row in rows[1:]:  # 跳过表头
                    try:
                        cells = await row.query_selector_all("td")
                        if len(cells) < 5:
                            continue
                        
                        date_str = await cells[0].inner_text() if len(cells) > 0 else ""
                        transaction_count = await cells[1].inner_text() if len(cells) > 1 else ""
                        count_change = await cells[2].inner_text() if len(cells) > 2 else ""
                        total_amount = await cells[3].inner_text() if len(cells) > 3 else ""
                        amount_change = await cells[4].inner_text() if len(cells) > 4 else ""
                        
                        trend_data = {
                            "content_id": f"trend_{date_str}",
                            "title": f"{date_str} 成交数据",
                            "content_text": f"成交宗数: {transaction_count} ({count_change}), 总金额: {total_amount} ({amount_change})",
                            "content_url": self.index_url,
                            "date": date_str.strip(),
                            "transaction_count": self.parse_number(transaction_count),
                            "count_change": count_change.strip(),
                            "total_amount": self.parse_number(total_amount),
                            "amount_change": amount_change.strip(),
                            "source_keyword": "成交走势",
                            "created_time": int(asyncio.get_event_loop().time()),
                        }
                        
                        await eprc_store.store_content(trend_data)
                        
                    except Exception as e:
                        utils.logger.error(f"提取走势数据失败: {e}")
                        continue
                        
        except Exception as e:
            utils.logger.error(f"抓取成交走势数据失败: {e}")

    async def get_estate_prices(self) -> None:
        """抓取屋苑价格数据"""
        utils.logger.info("[EPRCCrawler] 抓取屋苑价格数据")
        
        try:
            # 查找价格数据
            price_elements = await self.context_page.query_selector_all(
                ".price-item, .estate-price, [class*='price'], [data-price]"
            )
            
            for element in price_elements[:config.CRAWLER_MAX_NOTES_COUNT]:
                try:
                    price_data = await self.extract_price_data(element)
                    if price_data:
                        await eprc_store.store_content(price_data)
                except Exception as e:
                    utils.logger.error(f"提取价格数据失败: {e}")
                    continue
                    
        except Exception as e:
            utils.logger.error(f"抓取屋苑价格数据失败: {e}")

    async def get_specified_data(self) -> None:
        """获取指定数据（根据关键词）"""
        utils.logger.info("[EPRCCrawler] 获取指定数据")
        
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"搜索关键词: {keyword}")
            
            # 如果网站有搜索功能，可以在这里实现
            # 否则根据关键词过滤已抓取的数据
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

    async def extract_estate_data(self, element) -> Optional[Dict]:
        """从元素提取屋苑数据"""
        try:
            # 使用 evaluate 提取数据
            data = await element.evaluate("""
                el => {
                    const text = el.innerText || el.textContent || '';
                    const priceMatch = text.match(/\\$([\\d,]+)/);
                    const changeMatch = text.match(/[↓↑]([\\d.]+)%/);
                    return {
                        text: text,
                        price: priceMatch ? priceMatch[1] : '',
                        change: changeMatch ? changeMatch[1] : '',
                    };
                }
            """)
            
            if not data.get("text"):
                return None
            
            # 提取屋苑名称（通常在第一个元素或特定位置）
            estate_name = await element.evaluate("""
                el => {
                    const nameEl = el.querySelector('.estate-name, .name, h3, h4, strong') || el;
                    return nameEl.innerText || nameEl.textContent || '';
                }
            """)
            
            return {
                "content_id": f"estate_{hash(estate_name)}",
                "title": estate_name.strip() or "屋苑数据",
                "content_text": data.get("text", ""),
                "content_url": self.index_url,
                "estate_name": estate_name.strip(),
                "price": data.get("price", ""),
                "price_change": data.get("change", ""),
                "source_keyword": "指标屋苑",
                "created_time": int(asyncio.get_event_loop().time()),
            }
        except Exception as e:
            utils.logger.error(f"提取屋苑数据异常: {e}")
            return None

    async def extract_news_data(self, element) -> Optional[Dict]:
        """提取新闻数据"""
        try:
            title = await element.evaluate("""
                el => {
                    const titleEl = el.querySelector('.title, h3, h4, a, strong') || el;
                    return titleEl.innerText || titleEl.textContent || '';
                }
            """)
            
            content = await element.evaluate("""
                el => {
                    const contentEl = el.querySelector('.content, .text, p') || el;
                    return contentEl.innerText || contentEl.textContent || '';
                }
            """)
            
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content or title)
            date_str = date_match.group(1) if date_match else ""
            
            return {
                "content_id": f"news_{hash(title)}",
                "title": title.strip(),
                "content_text": content.strip(),
                "content_url": self.index_url,
                "publish_date": date_str,
                "source_keyword": "市场动向",
                "created_time": int(asyncio.get_event_loop().time()),
            }
        except Exception as e:
            utils.logger.error(f"提取新闻数据异常: {e}")
            return None

    async def extract_price_data(self, element) -> Optional[Dict]:
        """提取价格数据"""
        try:
            data = await element.evaluate("""
                el => {
                    const text = el.innerText || el.textContent || '';
                    return {
                        text: text,
                        price: text.match(/\\$([\\d,]+)/)?.[1] || '',
                        unit: text.match(/(元|呎|尺)/)?.[0] || '',
                    };
                }
            """)
            
            return {
                "content_id": f"price_{hash(data.get('text', ''))}",
                "title": "屋苑价格",
                "content_text": data.get("text", ""),
                "content_url": self.index_url,
                "price": data.get("price", ""),
                "price_unit": data.get("unit", ""),
                "source_keyword": "屋苑价格",
                "created_time": int(asyncio.get_event_loop().time()),
            }
        except Exception as e:
            utils.logger.error(f"提取价格数据异常: {e}")
            return None

    def parse_number(self, text: str) -> int:
        """解析数字字符串"""
        if not text:
            return 0
        # 移除逗号和其他非数字字符（保留负号）
        numbers = re.findall(r'-?\d+', text.replace(',', ''))
        return int(numbers[0]) if numbers else 0

    # ==================== requests模式的方法 ====================
    
    async def get_indicator_estates_with_soup(self, soup: BeautifulSoup):
        """抓取指标屋苑数据（成交排行榜）- requests模式，支持分页"""
        utils.logger.info("[EPRCCrawler] 抓取成交排行榜数据（requests模式，支持分页）")
        
        try:
            # 查找成交排行榜表格
            tables = soup.find_all('table')
            count = 0  # 初始化计数器
            found_ranking_table = False  # 标记是否找到排行榜表格

            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')
                if len(rows) < 2:
                    continue

                # 检查表头并动态映射列 - 尝试第一行和第二行作为表头
                for header_row_idx in [0, 1]:
                    if header_row_idx >= len(rows):
                        continue

                    header_cells = rows[header_row_idx].find_all(['th', 'td'])
                    header_texts = [th.get_text(strip=True) for th in header_cells]
                    header_text = ' '.join(header_texts)

                    # 快速检查是否包含关键词
                    if not any(keyword in header_text for keyword in ['排名', '屋苑', '地區', '成交宗']):
                        continue

                    # 排除明显的错误表格（如赚蚀分析表）
                    if any(keyword in header_text for keyword in ['座數/大廈', '買入日期', '賣出日期', '持貨日']):
                        utils.logger.debug(f"[EPRCCrawler] 跳过表格#{table_idx+1}: 这是賺蚀分析表，不是成交排行榜")
                        continue

                    # 动态映射列索引
                    col_map = {}
                    for idx, header in enumerate(header_texts):
                        header_lower = header.lower().strip()
                        if '排名' in header or 'rank' in header_lower:
                            col_map['rank'] = idx
                        elif '屋苑' in header and '名稱' in header:
                            col_map['estate_name'] = idx
                        elif '地區' in header or 'region' in header_lower or 'district' in header_lower:
                            col_map['region'] = idx
                        elif '成交' in header and '宗' in header:
                            col_map['transaction_count'] = idx
                        elif '最高' in header and '呎價' in header:
                            if 'highest_price' not in col_map:  # 取第一个匹配
                                col_map['highest_price'] = idx
                        elif '最低' in header and '呎價' in header:
                            if 'lowest_price' not in col_map:
                                col_map['lowest_price'] = idx
                        elif '平均' in header and '呎價' in header:
                            if 'avg_price' not in col_map:
                                col_map['avg_price'] = idx

                    # 检查是否成功映射了核心字段
                    required_fields = ['estate_name', 'region']
                    if not all(field in col_map for field in required_fields):
                        utils.logger.debug(f"[EPRCCrawler] 表格#{table_idx+1} 行{header_row_idx}: 缺少必需字段 {required_fields}, 当前映射: {col_map}")
                        continue

                    utils.logger.info(f"[EPRCCrawler] 找到成交排行榜表格 (表格#{table_idx+1}, 表头行{header_row_idx})")
                    utils.logger.debug(f"[EPRCCrawler] 成交排行榜列映射: {col_map}")
                    utils.logger.debug(f"[EPRCCrawler] 表头: {header_texts[:15]}...")  # 只显示前15列

                    # 数据行从表头的下一行开始
                    data_start_row = header_row_idx + 1
                    found_ranking_table = True
                    for row in rows[data_start_row:]:  # 从表头后开始
                        try:
                            cells = row.find_all('td')
                            if len(cells) < 5:
                                continue

                            # 使用列映射提取数据（不使用默认值，没有映射就跳过）
                            if 'estate_name' not in col_map or 'region' not in col_map:
                                continue

                            rank = cells[col_map['rank']].get_text(strip=True) if 'rank' in col_map and col_map['rank'] < len(cells) else ""
                            estate_name = cells[col_map['estate_name']].get_text(strip=True) if col_map['estate_name'] < len(cells) else ""
                            region = cells[col_map['region']].get_text(strip=True) if col_map['region'] < len(cells) else ""
                            transaction_count = cells[col_map['transaction_count']].get_text(strip=True) if 'transaction_count' in col_map and col_map['transaction_count'] < len(cells) else ""
                            highest_price = cells[col_map['highest_price']].get_text(strip=True) if 'highest_price' in col_map and col_map['highest_price'] < len(cells) else ""
                            lowest_price = cells[col_map['lowest_price']].get_text(strip=True) if 'lowest_price' in col_map and col_map['lowest_price'] < len(cells) else ""
                            avg_price = cells[col_map['avg_price']].get_text(strip=True) if 'avg_price' in col_map and col_map['avg_price'] < len(cells) else ""

                            if not estate_name or estate_name == '排名' or len(estate_name) < 2:
                                continue

                            # 解析排名数字
                            rank_num = 0
                            if rank:
                                rank_match = re.search(r'\d+', str(rank))
                                if rank_match:
                                    rank_num = int(rank_match.group())

                            estate_data = {
                                "content_id": f"ranking_{hash(str(rank_num) + estate_name + region)}",
                                "title": f"{rank}. {estate_name} ({region})",
                                "content_text": f"成交宗数: {transaction_count}, 最高呎價: {highest_price}, 最低呎價: {lowest_price}, 平均呎價: {avg_price}",
                                "content_url": self.index_url,
                                "rank": rank_num,
                                "estate_name": estate_name,
                                "region": region,
                                "transaction_count": self.parse_number(transaction_count),
                                "highest_price": highest_price.replace(',', '').replace('*', '').strip() if highest_price else "",
                                "lowest_price": lowest_price.replace(',', '').replace('*', '').strip() if lowest_price else "",
                                "avg_price": avg_price.replace(',', '').replace('*', '').strip() if avg_price else "",
                                "price": avg_price.replace(',', '').replace('*', '').strip() if avg_price else "",  # 保留用于兼容
                                "page_num": 1,  # requests模式只有第一页
                                "data_date": self.data_date or "",  # 数据日期
                                "source_keyword": "成交排行榜",
                                "created_time": int(time.time()),
                            }

                            await eprc_store.store_content(estate_data)
                            count += 1

                        except Exception as e:
                            utils.logger.error(f"提取成交排行榜数据失败: {e}")
                            continue

                    if count > 0:
                        utils.logger.info(f"[EPRCCrawler] 成功提取 {count} 条成交排行榜数据")
                        return  # 找到并处理了正确的表格，退出函数
                    break  # 跳出header_row_idx循环

                if found_ranking_table:
                    break  # 跳出table_idx循环
            
            # 如果没有找到表格，尝试查找其他格式的数据
            if count == 0:
                estate_elements = soup.find_all(['div', 'span', 'td', 'li'], 
                                              class_=re.compile(r'estate|property|屋苑', re.I))
                
                if not estate_elements:
                    price_texts = soup.find_all(text=re.compile(r'\$\d+'))
                    estate_elements = [text.parent for text in price_texts[:config.CRAWLER_MAX_NOTES_COUNT] if text.parent]
                
                for element in estate_elements[:config.CRAWLER_MAX_NOTES_COUNT]:
                    try:
                        estate_data = self.extract_estate_data_from_soup(element)
                        if estate_data:
                            await eprc_store.store_content(estate_data)
                            count += 1
                    except Exception as e:
                        utils.logger.error(f"提取屋苑数据失败: {e}")
                        continue
                
                if count > 0:
                    utils.logger.info(f"[EPRCCrawler] 成功提取 {count} 条屋苑数据")
                    
        except Exception as e:
            utils.logger.error(f"抓取成交排行榜数据失败: {e}")

    async def get_transaction_analysis_with_soup(self, soup: BeautifulSoup):
        """抓取交易分析数据（赚蚀分析）- requests模式，支持分页"""
        utils.logger.info("[EPRCCrawler] 抓取赚蚀分析数据（requests模式，支持分页）")

        try:
            tables = soup.find_all('table')
            count = 0
            found_analysis_table = False

            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')
                if len(rows) < 3:  # 需要至少3行（多行表头 + 数据）
                    continue

                # 检查是否是赚蚀分析汇总表（不是个别交易表）
                # 收集前3行的文本进行检测
                combined_header_text = ""
                for row_idx in range(min(3, len(rows))):
                    cells = rows[row_idx].find_all(['th', 'td'])
                    combined_header_text += ' '.join([cell.get_text(strip=True) for cell in cells]) + " "

                # 必须包含：地區 AND 代表性物業 AND 賺 (宗) AND 蝕 (宗)
                required_keywords = ['地區', '代表性物業', '賺', '蝕', '宗']
                if not all(kw in combined_header_text for kw in required_keywords):
                    continue

                # 排除个别交易明细表（有座數、買入日期等）
                exclude_keywords = ['座數/大廈', '買入日期', '賣出日期', '持貨日']
                if any(kw in combined_header_text for kw in exclude_keywords):
                    utils.logger.debug(f"[EPRCCrawler] 跳过表格#{table_idx+1}: 这是个别交易表，不是区域汇总表")
                    continue

                utils.logger.info(f"[EPRCCrawler] 找到赚蚀分析汇总表 (表格#{table_idx+1})")
                found_analysis_table = True

                # 该表的固定列结构（基于诊断输出的table #12）:
                # 列0: 地區, 列2: 代表性物業, 列3: 賺宗數, 列4: 賺幅度, 列8: 蝕宗數, 列9: 蝕幅度
                # 数据从第3行开始（前几行是表头）

                for row_idx, row in enumerate(rows[3:], start=3):  # 从第4行开始（索引3）
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 10:  # 需要至少10列
                            continue

                        # 提取数据 - 使用固定的列索引
                        region = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                        estate_name = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        profit_cases_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        profit_range = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                        loss_cases_text = cells[8].get_text(strip=True) if len(cells) > 8 else ""
                        loss_range = cells[9].get_text(strip=True) if len(cells) > 9 else ""

                        # 严格验证：必须是区域汇总表数据
                        # 1. region 必须以"區"结尾（如：元朗區、沙田區）
                        if not region or not region.endswith('區'):
                            continue
                        # 2. region 不能包含括号（排除详细地址）
                        if '(' in region or '）' in region or '（' in region:
                            continue
                        # 3. estate_name 必须至少3个字符
                        if not estate_name or len(estate_name) < 3:
                            continue
                        # 4. 跳过表头行
                        if '地區' in region or '代表性物業' in estate_name:
                            continue
                        # 5. profit_cases 必须是纯数字
                        if profit_cases_text and not profit_cases_text.replace(',', '').isdigit():
                            continue
                        # 6. profit_range 不能是日期格式（不能包含-连接的年月日）
                        if '-' in profit_range and len(profit_range.split('-')) == 3:
                            continue

                        transaction_data = {
                            "content_id": f"txn_{hash(region + estate_name)}",
                            "title": f"{region} - {estate_name} 交易分析",
                            "content_text": f"赚: {profit_cases_text}宗 ({profit_range}), 蚀: {loss_cases_text}宗 ({loss_range})",
                            "content_url": self.index_url,
                            "region": region,
                            "estate_name": estate_name,
                            "profit_cases": self.parse_number(profit_cases_text),
                            "profit_range": profit_range,
                            "loss_cases": self.parse_number(loss_cases_text),
                            "loss_range": loss_range,
                            "page_num": 1,  # requests模式只有第一页
                            "data_date": self.data_date or "",  # 数据日期
                            "source_keyword": "交易分析",
                            "created_time": int(time.time()),
                        }

                        await eprc_store.store_content(transaction_data)
                        count += 1

                    except Exception as e:
                        utils.logger.error(f"提取交易数据失败 (行{row_idx}): {e}")
                        continue

                if count > 0:
                    utils.logger.info(f"[EPRCCrawler] 成功提取 {count} 条交易数据")
                    return  # 找到并处理了正确的表格，退出

                if found_analysis_table:
                    break  # 找到了表格但没有数据，跳出循环

        except Exception as e:
            utils.logger.error(f"抓取交易分析数据失败: {e}")

    async def get_market_trends_with_soup(self, soup: BeautifulSoup):
        """抓取市场趋势数据（requests模式）"""
        utils.logger.info("[EPRCCrawler] 抓取市场趋势数据（requests模式）")
        
        try:
            # 查找新闻元素
            news_elements = soup.find_all(['div', 'article', 'li'], 
                                         class_=re.compile(r'news|trend|market|动向', re.I))
            
            count = 0
            for element in news_elements[:20]:
                try:
                    news_data = self.extract_news_data_from_soup(element)
                    if news_data:
                        await eprc_store.store_content(news_data)
                        count += 1
                except Exception as e:
                    utils.logger.error(f"提取新闻数据失败: {e}")
                    continue
            
            utils.logger.info(f"[EPRCCrawler] 成功提取 {count} 条新闻数据")
            
            # 抓取成交走势数据
            await self.get_transaction_volume_trend_with_soup(soup)
            
        except Exception as e:
            utils.logger.error(f"抓取市场趋势数据失败: {e}")

    async def get_transaction_volume_trend_with_soup(self, soup: BeautifulSoup):
        """抓取成交走势数据（requests模式）"""
        try:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) < 2:
                    continue
                
                # 检查是否包含成交相关关键词
                header_text = ' '.join([th.get_text() for th in rows[0].find_all(['th', 'td'])])
                if not any(keyword in header_text for keyword in ['成交', '宗数', '登记月', '金额']):
                    continue
                
                count = 0
                for row in rows[1:]:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 5:
                            continue
                        
                        date_str = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                        transaction_count = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        count_change = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        total_amount = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        amount_change = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                        
                        if not date_str:
                            continue
                        
                        trend_data = {
                            "content_id": f"trend_{hash(date_str)}",
                            "title": f"{date_str} 成交数据",
                            "content_text": f"成交宗数: {transaction_count} ({count_change}), 总金额: {total_amount} ({amount_change})",
                            "content_url": self.index_url,
                            "date": date_str,
                            "transaction_count": self.parse_number(transaction_count),
                            "count_change": count_change,
                            "total_amount": self.parse_number(total_amount),
                            "amount_change": amount_change,
                            "source_keyword": "成交走势",
                            "created_time": int(time.time()),
                        }
                        
                        await eprc_store.store_content(trend_data)
                        count += 1
                        
                        if count >= config.CRAWLER_MAX_NOTES_COUNT:
                            break
                        
                    except Exception as e:
                        utils.logger.error(f"提取走势数据失败: {e}")
                        continue
                
                if count > 0:
                    utils.logger.info(f"[EPRCCrawler] 成功提取 {count} 条走势数据")
                    break
                        
        except Exception as e:
            utils.logger.error(f"抓取成交走势数据失败: {e}")

    async def get_estate_prices_with_soup(self, soup: BeautifulSoup):
        """抓取屋苑价格数据（requests模式）"""
        utils.logger.info("[EPRCCrawler] 抓取屋苑价格数据（requests模式）")
        
        try:
            # 查找包含价格信息的文本
            price_texts = soup.find_all(text=re.compile(r'\$\d+[,\d]*'))
            
            count = 0
            for price_text in price_texts[:config.CRAWLER_MAX_NOTES_COUNT]:
                try:
                    parent = price_text.parent
                    if not parent:
                        continue
                    
                    text = parent.get_text(strip=True)
                    price_match = re.search(r'\$([\d,]+)', str(price_text))
                    
                    price_data = {
                        "content_id": f"price_{hash(text)}",
                        "title": "屋苑价格",
                        "content_text": text[:200],  # 限制长度
                        "content_url": self.index_url,
                        "price": price_match.group(1) if price_match else "",
                        "source_keyword": "屋苑价格",
                        "created_time": int(time.time()),
                    }
                    
                    await eprc_store.store_content(price_data)
                    count += 1
                    
                except Exception as e:
                    utils.logger.error(f"提取价格数据失败: {e}")
                    continue
            
            utils.logger.info(f"[EPRCCrawler] 成功提取 {count} 条价格数据")
                    
        except Exception as e:
            utils.logger.error(f"抓取屋苑价格数据失败: {e}")

    def extract_estate_data_from_soup(self, element) -> Optional[Dict]:
        """从BeautifulSoup元素提取屋苑数据"""
        try:
            text = element.get_text(strip=True)
            if not text or len(text) < 5:
                return None
            
            # 提取价格
            price_match = re.search(r'\$([\d,]+)', text)
            price = price_match.group(1) if price_match else ""
            
            # 提取变化
            change_match = re.search(r'[↓↑]([\d.]+)%', text)
            change = change_match.group(1) if change_match else ""
            
            # 提取屋苑名称
            name_match = re.search(r'([\u4e00-\u9fa5a-zA-Z]+)', text)
            estate_name = name_match.group(1) if name_match else "未知屋苑"
            
            return {
                "content_id": f"estate_{hash(text)}",
                "title": estate_name or "屋苑数据",
                "content_text": text,
                "content_url": self.index_url,
                "estate_name": estate_name,
                "price": price,
                "price_change": change,
                "source_keyword": "指标屋苑",
                "created_time": int(time.time()),
            }
        except Exception as e:
            utils.logger.error(f"提取屋苑数据异常: {e}")
            return None

    def extract_news_data_from_soup(self, element) -> Optional[Dict]:
        """从BeautifulSoup元素提取新闻数据"""
        try:
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'strong', 'a'])
            title = title_elem.get_text(strip=True) if title_elem else element.get_text(strip=True)[:100]
            
            content = element.get_text(strip=True)
            
            date_match = re.search(r'(\d{4}[-/]\d{2}[-/]\d{2})', content or title)
            date_str = date_match.group(1) if date_match else ""
            
            if not title or len(title) < 5:
                return None
            
            return {
                "content_id": f"news_{hash(title)}",
                "title": title,
                "content_text": content[:500],
                "content_url": self.index_url,
                "publish_date": date_str,
                "source_keyword": "市场动向",
                "created_time": int(time.time()),
            }
        except Exception as e:
            utils.logger.error(f"提取新闻数据异常: {e}")
            return None

