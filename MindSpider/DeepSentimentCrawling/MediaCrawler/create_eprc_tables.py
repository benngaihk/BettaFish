#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPRC 数据库表初始化脚本（优化版 v2.0）
直接创建优化后的表结构 - 自动执行版本
"""

from database.models import Base, EPRCProfitLoss, EPRCRanking, EPRCContent
from sqlalchemy import create_engine, inspect, text
import config
from config.db_config import postgresql_db_config, sqlite_db_config, mysql_db_config

print("=" * 80)
print("EPRC 数据库表初始化脚本 v2.0")
print("=" * 80)
print()

# 获取数据库配置
db_type = config.SAVE_DATA_OPTION

print(f"📋 配置信息：")
print(f"  数据库类型: {db_type}")

# 构建连接字符串
if db_type == 'postgresql':
    connection_string = (
        f"postgresql://{postgresql_db_config['user']}:{postgresql_db_config['password']}"
        f"@{postgresql_db_config['host']}:{postgresql_db_config['port']}/{postgresql_db_config['db_name']}"
    )
    print(f"  连接信息: {postgresql_db_config['user']}@{postgresql_db_config['host']}:{postgresql_db_config['port']}/{postgresql_db_config['db_name']}")
elif db_type == 'sqlite':
    connection_string = f"sqlite:///{sqlite_db_config['db_path']}"
    print(f"  数据库文件: {sqlite_db_config['db_path']}")
elif db_type in ['mysql', 'db']:
    connection_string = (
        f"mysql+pymysql://{mysql_db_config['user']}:{mysql_db_config['password']}"
        f"@{mysql_db_config['host']}:{mysql_db_config['port']}/{mysql_db_config['db_name']}"
        f"?charset=utf8mb4"
    )
    print(f"  连接信息: {mysql_db_config['user']}@{mysql_db_config['host']}:{mysql_db_config['port']}/{mysql_db_config['db_name']}")
else:
    print(f"⚠️ 警告：数据库类型 '{db_type}' 可能不受支持")
    print(f"   支持的类型: postgresql, mysql, sqlite")
    exit(1)

print()

# 创建引擎
engine = create_engine(connection_string, echo=False)

# 测试连接
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        result.close()
    print("✅ 数据库连接成功")
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
    exit(1)

# 创建 EPRC 表
print()
print("🔨 创建 EPRC 表...")
print()

eprc_tables = [
    ('eprc_profit_loss', EPRCProfitLoss.__table__, '赚蚀分析表'),
    ('eprc_ranking', EPRCRanking.__table__, '成交排行榜表'),
    ('eprc_content', EPRCContent.__table__, '通用内容表'),
]

for table_name, table_obj, description in eprc_tables:
    try:
        table_obj.create(engine, checkfirst=True)
        print(f"  ✅ {table_name} ({description})")

        # 显示优化信息
        if table_name == 'eprc_ranking':
            print(f"      ✨ 价格字段: Numeric(12,2) 类型（支持数值计算）")
            print(f"      ✨ 已删除 4 个未使用字段")
        elif table_name == 'eprc_profit_loss':
            print(f"      📊 字段: region, estate_name, profit/loss 数据")
        elif table_name == 'eprc_content':
            print(f"      📝 字段: 通用内容（兜底表）")

    except Exception as e:
        print(f"  ❌ {table_name}: {e}")

print()

# 验证表结构
print("🔍 验证表结构...")
print()

inspector = inspect(engine)

for table_name, _, description in eprc_tables:
    if inspector.has_table(table_name):
        columns = inspector.get_columns(table_name)
        col_names = [col['name'] for col in columns]
        print(f"✅ {table_name} ({len(columns)} 列)")

        # 验证关键字段
        if table_name == 'eprc_ranking':
            # 验证 record_date
            if 'record_date' in col_names:
                print(f"   ✅ record_date (优化后的字段名)")

            # 验证价格字段类型
            for col in columns:
                if col['name'] == 'highest_price':
                    col_type = str(col['type'])
                    if 'NUMERIC' in col_type.upper() or 'DECIMAL' in col_type.upper():
                        print(f"   ✅ highest_price: {col_type} (Numeric类型)")

            # 验证删除的字段
            removed_fields = ['rental_yield', 'avg_rent', 'rental_listings', 'sale_listings']
            removed_count = sum(1 for field in removed_fields if field not in col_names)
            if removed_count == len(removed_fields):
                print(f"   ✅ 已删除 {removed_count} 个未使用字段")

        elif table_name in ['eprc_profit_loss', 'eprc_content']:
            if 'record_date' in col_names:
                print(f"   ✅ record_date (优化后的字段名)")

        print()
    else:
        print(f"❌ {table_name} 不存在")
        print()

print("=" * 80)
print("✨ EPRC 表创建完成！")
print("=" * 80)
print()

print("📊 表结构概览：")
print()
print("1. eprc_profit_loss（赚蚀分析表）")
print("   - 字段：region, estate_name, profit/loss cases/range")
print("   - 索引：content_id (unique), region, estate_name, record_date")
print()
print("2. eprc_ranking（成交排行榜表）")
print("   - 字段：rank, estate_name, region, transaction_count")
print("   - 价格：highest_price, lowest_price, avg_price (Numeric 类型)")
print("   - 索引：content_id (unique), rank, estate_name, region, record_date")
print("   - 优化：支持价格范围查询、排序、统计")
print()
print("3. eprc_content（通用内容表）")
print("   - 字段：title, content_text, content_url, source_keyword")
print("   - 索引：content_id, record_date")
print("   - 用途：存储其他类型数据（如市场动向、成交走势）")
print()
print("🎉 可以开始使用 EPRC 爬虫了！")
print()
print("测试命令：")
print("  python main.py --platforms eprc --crawler-type search")
print()
