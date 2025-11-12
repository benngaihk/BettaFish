#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPRC HTML结构诊断脚本
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def inspect_eprc_html():
    """检查EPRC网站的HTML结构"""
    async with async_playwright() as playwright:
        print("启动Firefox...")
        browser = await playwright.firefox.launch(headless=False)
        page = await browser.new_page()

        print("访问 https://eprc.com.hk/index.htm ...")
        await page.goto("https://eprc.com.hk/index.htm", wait_until="networkidle")
        await asyncio.sleep(3)

        # 获取所有frame
        frames = page.frames
        print(f"\n找到 {len(frames)} 个 frame:")
        for idx, frame in enumerate(frames):
            print(f"  Frame {idx}: {frame.name} - {frame.url}")

        # 找到主frame
        main_frame = None
        for frame in frames:
            if "main.html" in frame.url or frame.name == "topFrame":
                main_frame = frame
                print(f"\n使用主frame: {frame.name} - {frame.url}")
                break

        if not main_frame:
            print("\n未找到主frame,使用默认page")
            main_frame = page

        await asyncio.sleep(2)

        # 获取HTML内容
        html = await main_frame.content()
        soup = BeautifulSoup(html, 'html.parser')

        # 查找所有表格
        tables = soup.find_all('table')
        print(f"\n找到 {len(tables)} 个表格\n")

        for table_idx, table in enumerate(tables):
            print(f"{'='*80}")
            print(f"表格 #{table_idx + 1}")
            print(f"{'='*80}")

            rows = table.find_all('tr')
            print(f"行数: {len(rows)}")

            if len(rows) > 0:
                # 打印表头
                header_row = rows[0]
                header_cells = header_row.find_all(['th', 'td'])
                header_texts = [cell.get_text(strip=True) for cell in header_cells]
                print(f"\n表头 ({len(header_cells)} 列):")
                for idx, text in enumerate(header_texts):
                    print(f"  列 {idx}: '{text}'")

                # 打印前3行数据
                if len(rows) > 1:
                    print(f"\n前3行数据:")
                    for row_idx in range(1, min(4, len(rows))):
                        data_row = rows[row_idx]
                        data_cells = data_row.find_all('td')
                        print(f"\n  行 {row_idx} ({len(data_cells)} 列):")
                        for cell_idx, cell in enumerate(data_cells):
                            cell_text = cell.get_text(strip=True)
                            # 限制显示长度
                            display_text = cell_text[:50] + "..." if len(cell_text) > 50 else cell_text
                            print(f"    列 {cell_idx}: '{display_text}'")

            print()

        print("\n按Enter键关闭浏览器...")
        input()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_eprc_html())
