#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 EPRC 数据库数据质量"""

import pymysql
from config.db_config import mysql_db_config

# 连接数据库
conn = pymysql.connect(
    host=mysql_db_config['host'],
    port=mysql_db_config['port'],
    user=mysql_db_config['user'],
    password=mysql_db_config['password'],
    database=mysql_db_config['db_name'],
    charset='utf8mb4'
)

cursor = conn.cursor(pymysql.cursors.DictCursor)

print("=" * 80)
print("EPRC 数据质量检查")
print("=" * 80)
print()

# 检查 eprc_profit_loss 表
print("【1】eprc_profit_loss (赚蚀分析表)")
print("-" * 80)

cursor.execute("SELECT COUNT(*) as total FROM eprc_profit_loss")
total = cursor.fetchone()['total']
print(f"总记录数: {total}")
print()

if total > 0:
    print("前5条记录:")
    cursor.execute("""
        SELECT region, estate_name, profit_cases, profit_range,
               loss_cases, loss_range, record_date
        FROM eprc_profit_loss
        ORDER BY id DESC
        LIMIT 5
    """)

    for row in cursor.fetchall():
        print(f"  地区: {row['region']}")
        print(f"  屋苑: {row['estate_name']}")
        print(f"  赚: {row['profit_cases']}宗 ({row['profit_range']})")
        print(f"  蚀: {row['loss_cases']}宗 ({row['loss_range']})")
        print(f"  日期: {row['record_date']}")
        print()

print()

# 检查 eprc_ranking 表
print("【2】eprc_ranking (成交排行榜表)")
print("-" * 80)

cursor.execute("SELECT COUNT(*) as total FROM eprc_ranking")
total = cursor.fetchone()['total']
print(f"总记录数: {total}")
print()

if total > 0:
    print("前5条记录:")
    cursor.execute("""
        SELECT `rank`, estate_name, region, transaction_count,
               highest_price, lowest_price, avg_price, record_date
        FROM eprc_ranking
        ORDER BY id DESC
        LIMIT 5
    """)

    for row in cursor.fetchall():
        print(f"  排名: {row['rank']}")
        print(f"  屋苑: {row['estate_name']}")
        print(f"  地区: {row['region']}")
        print(f"  成交: {row['transaction_count']}宗")
        print(f"  价格: 最高${row['highest_price']}, 最低${row['lowest_price']}, 平均${row['avg_price']}")
        print(f"  日期: {row['record_date']}")
        print()

print()

# 数据质量检查
print("【3】数据质量分析")
print("-" * 80)

# 检查 profit_loss 数据质量
cursor.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN LENGTH(region) < 3 THEN 1 ELSE 0 END) as bad_region,
        SUM(CASE WHEN LENGTH(estate_name) < 3 THEN 1 ELSE 0 END) as bad_estate,
        SUM(CASE WHEN region LIKE '%20%' OR region LIKE '%日期%' THEN 1 ELSE 0 END) as date_in_region
    FROM eprc_profit_loss
""")
quality = cursor.fetchone()
print(f"profit_loss 质量:")
print(f"  - 总记录: {quality['total']}")
print(f"  - 地区名过短 (<3字符): {quality['bad_region']}")
print(f"  - 屋苑名过短 (<3字符): {quality['bad_estate']}")
print(f"  - 地区包含日期: {quality['date_in_region']}")
print()

# 检查 ranking 数据质量
cursor.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN LENGTH(estate_name) < 3 THEN 1 ELSE 0 END) as bad_estate,
        SUM(CASE WHEN estate_name REGEXP '^[0-9,]+$' THEN 1 ELSE 0 END) as number_estate,
        SUM(CASE WHEN region REGEXP '^[0-9,]+$' THEN 1 ELSE 0 END) as number_region
    FROM eprc_ranking
""")
quality = cursor.fetchone()
print(f"ranking 质量:")
print(f"  - 总记录: {quality['total']}")
print(f"  - 屋苑名过短 (<3字符): {quality['bad_estate']}")
print(f"  - 屋苑名是纯数字: {quality['number_estate']}")
print(f"  - 地区是纯数字: {quality['number_region']}")

cursor.close()
conn.close()

print()
print("=" * 80)
print("检查完成")
print("=" * 80)
