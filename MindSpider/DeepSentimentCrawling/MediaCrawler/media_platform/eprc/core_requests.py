# -*- coding: utf-8 -*-
"""
EPRC 爬虫 - 使用requests+BeautifulSoup版本（更稳定，适合静态网站）
"""
import asyncio
import re
import time
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
import config
from store import eprc as eprc_store
from tools import utils
from var import crawler_type_var, source_keyword_var


class EPRCRequestsCrawler:
    """EPRC 使用requests的爬虫版本（更稳定）"""
    
    def __init__(self):
        self.base_url = "https://eprc.com.hk/index.htm"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    async def start(self):
        """启动爬虫"""
        utils.logger.info("[EPRCRequestsCrawler] 开始使用requests方式抓取EPRC数据")
        
        crawler_type_var.set(config.CRAWLER_TYPE)
        if config.CRAWLER_TYPE == "search":
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            await self.get_specified_data()
        elif config.CRAWLER_TYPE == "trend":
            await self.get_market_trends()
        
        utils.logger.info("[EPRCRequestsCrawler] 爬取完成")

    async def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """获取页面内容"""
        try:
            utils.logger.info(f"[EPRCRequestsCrawler] 正在访问: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
        except Exception as e:
            utils.logger.error(f"[EPRCRequestsCrawler] 获取页面失败: {e}")
            return None

    async def search(self):
        """搜索房地产数据"""
        utils.logger.info("[EPRCRequestsCrawler.search] 开始抓取EPRC数据")
        
        soup = await self.fetch_page(self.base_url)
        if not soup:
            utils.logger.error("无法获取页面内容")
            return
        
        # 1. 抓取指标屋苑数据
        await self.get_indicator_estates(soup)
        
        # 2. 抓取交易分析数据
        await self.get_transaction_analysis(soup)
        
        # 3. 抓取市场趋势数据
        await self.get_market_trends_from_soup(soup)
        
        # 4. 抓取屋苑价格数据
        await self.get_estate_prices(soup)

    async def get_indicator_estates(self, soup: BeautifulSoup):
        """抓取指标屋苑数据"""
        utils.logger.info("[EPRCRequestsCrawler] 抓取指标屋苑数据")
        
        try:
            # 查找所有可能包含屋苑信息的元素
            estate_elements = soup.find_all(['div', 'span', 'td', 'li'], 
                                          class_=re.compile(r'estate|property|屋苑', re.I))
            
            # 如果没有找到，尝试查找包含价格信息的元素
            if not estate_elements:
                estate_elements = soup.find_all(text=re.compile(r'\$\d+'))
                estate_elements = [elem.parent for elem in estate_elements[:config.CRAWLER_MAX_NOTES_COUNT]]
            
            count = 0
            for element in estate_elements[:config.CRAWLER_MAX_NOTES_COUNT]:
                try:
                    estate_data = await self.extract_estate_data_from_element(element)
                    if estate_data:
                        await eprc_store.store_content(estate_data)
                        count += 1
                except Exception as e:
                    utils.logger.error(f"提取屋苑数据失败: {e}")
                    continue
            
            utils.logger.info(f"[EPRCRequestsCrawler] 成功提取 {count} 条屋苑数据")
                    
        except Exception as e:
            utils.logger.error(f"抓取指标屋苑数据失败: {e}")

    async def get_transaction_analysis(self, soup: BeautifulSoup):
        """抓取交易分析数据（赚蚀分析）"""
        utils.logger.info("[EPRCRequestsCrawler] 抓取交易分析数据")
        
        try:
            # 查找所有表格
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) < 2:
                    continue
                
                # 检查表头是否包含相关关键词
                header_text = ' '.join([th.get_text() for th in rows[0].find_all(['th', 'td'])])
                if not any(keyword in header_text for keyword in ['地区', '赚', '蚀', '宗', '幅度']):
                    continue
                
                count = 0
                for row in rows[1:]:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 5:
                            continue
                        
                        region = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                        estate_name = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        profit_cases = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        profit_range = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        loss_cases = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                        loss_range = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                        
                        if not region or not estate_name:
                            continue
                        
                        transaction_data = {
                            "content_id": f"txn_{hash(region + estate_name)}",
                            "title": f"{region} - {estate_name} 交易分析",
                            "content_text": f"赚: {profit_cases}宗 ({profit_range}), 蚀: {loss_cases}宗 ({loss_range})",
                            "content_url": self.base_url,
                            "region": region,
                            "estate_name": estate_name,
                            "profit_cases": self.parse_number(profit_cases),
                            "profit_range": profit_range,
                            "loss_cases": self.parse_number(loss_cases),
                            "loss_range": loss_range,
                            "source_keyword": "交易分析",
                            "created_time": int(time.time()),
                        }
                        
                        await eprc_store.store_content(transaction_data)
                        count += 1
                        
                        if count >= config.CRAWLER_MAX_NOTES_COUNT:
                            break
                        
                    except Exception as e:
                        utils.logger.error(f"提取交易数据失败: {e}")
                        continue
                
                if count > 0:
                    utils.logger.info(f"[EPRCRequestsCrawler] 成功提取 {count} 条交易数据")
                    break  # 找到第一个相关表格就退出
                        
        except Exception as e:
            utils.logger.error(f"抓取交易分析数据失败: {e}")

    async def get_market_trends_from_soup(self, soup: BeautifulSoup):
        """从soup中抓取市场趋势数据"""
        try:
            # 查找新闻或趋势相关的元素
            news_elements = soup.find_all(['div', 'article', 'li'], 
                                         class_=re.compile(r'news|trend|market|动向', re.I))
            
            count = 0
            for element in news_elements[:20]:
                try:
                    news_data = await self.extract_news_data_from_element(element)
                    if news_data:
                        await eprc_store.store_content(news_data)
                        count += 1
                except Exception as e:
                    utils.logger.error(f"提取新闻数据失败: {e}")
                    continue
            
            utils.logger.info(f"[EPRCRequestsCrawler] 成功提取 {count} 条新闻数据")
            
        except Exception as e:
            utils.logger.error(f"抓取市场趋势数据失败: {e}")

    async def get_market_trends(self):
        """抓取市场趋势数据（独立方法）"""
        await self.get_market_trends_from_soup(await self.fetch_page(self.base_url))

    async def get_estate_prices(self, soup: BeautifulSoup):
        """抓取屋苑价格数据"""
        utils.logger.info("[EPRCRequestsCrawler] 抓取屋苑价格数据")
        
        try:
            # 查找包含价格信息的元素
            price_elements = soup.find_all(text=re.compile(r'\$\d+[,\d]*'))
            
            count = 0
            for price_text in price_elements[:config.CRAWLER_MAX_NOTES_COUNT]:
                try:
                    parent = price_text.parent
                    if not parent:
                        continue
                    
                    price_data = {
                        "content_id": f"price_{hash(str(price_text))}",
                        "title": "屋苑价格",
                        "content_text": parent.get_text(strip=True),
                        "content_url": self.base_url,
                        "price": re.search(r'\$([\d,]+)', str(price_text)).group(1) if re.search(r'\$([\d,]+)', str(price_text)) else "",
                        "source_keyword": "屋苑价格",
                        "created_time": int(time.time()),
                    }
                    
                    await eprc_store.store_content(price_data)
                    count += 1
                    
                except Exception as e:
                    utils.logger.error(f"提取价格数据失败: {e}")
                    continue
            
            utils.logger.info(f"[EPRCRequestsCrawler] 成功提取 {count} 条价格数据")
                    
        except Exception as e:
            utils.logger.error(f"抓取屋苑价格数据失败: {e}")

    async def get_specified_data(self):
        """获取指定数据"""
        utils.logger.info("[EPRCRequestsCrawler] 获取指定数据")
        # 实现逻辑
        pass

    async def extract_estate_data_from_element(self, element) -> Optional[Dict]:
        """从元素提取屋苑数据"""
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
            
            # 提取屋苑名称（通常是第一个非数字非符号的文本）
            name_match = re.search(r'([\u4e00-\u9fa5a-zA-Z]+)', text)
            estate_name = name_match.group(1) if name_match else "未知屋苑"
            
            return {
                "content_id": f"estate_{hash(text)}",
                "title": estate_name or "屋苑数据",
                "content_text": text,
                "content_url": self.base_url,
                "estate_name": estate_name,
                "price": price,
                "price_change": change,
                "source_keyword": "指标屋苑",
                "created_time": int(time.time()),
            }
        except Exception as e:
            utils.logger.error(f"提取屋苑数据异常: {e}")
            return None

    async def extract_news_data_from_element(self, element) -> Optional[Dict]:
        """提取新闻数据"""
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
                "content_text": content[:500],  # 限制长度
                "content_url": self.base_url,
                "publish_date": date_str,
                "source_keyword": "市场动向",
                "created_time": int(time.time()),
            }
        except Exception as e:
            utils.logger.error(f"提取新闻数据异常: {e}")
            return None

    def parse_number(self, text: str) -> int:
        """解析数字字符串"""
        if not text:
            return 0
        numbers = re.findall(r'-?\d+', text.replace(',', ''))
        return int(numbers[0]) if numbers else 0

