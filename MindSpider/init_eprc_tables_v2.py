#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPRC 数据库表初始化脚本（优化版 v2.0）
直接创建优化后的表结构
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
mediacrawler_path = project_root / "DeepSentimentCrawling" / "MediaCrawler"
sys.path.insert(0, str(mediacrawler_path))

print("=" * 80)
print("EPRC 数据库表初始化脚本 v2.0")
print("=" * 80)
print()


def create_eprc_tables():
    """创建 EPRC 表（优化后的表结构）"""
    try:
        from database.models import Base, EPRCProfitLoss, EPRCRanking, EPRCContent
        from sqlalchemy import create_engine, text
        import config
        from database.db_config import DB_CONFIG

        print("📋 配置信息：")
        print(f"  数据库类型: {config.DB_TYPE}")
        print()

        # 获取数据库配置
        db_type = config.DB_TYPE
        db_config = DB_CONFIG.get(db_type)

        if not db_config:
            print(f"❌ 错误：不支持的数据库类型 '{db_type}'")
            print(f"   支持的类型：{list(DB_CONFIG.keys())}")
            return False

        # 构建连接字符串
        if db_type == 'postgresql':
            connection_string = (
                f"postgresql://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            )
            print(f"📦 数据库连接：{db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
        elif db_type == 'sqlite':
            db_path = db_config.get('path', 'data/media_crawler.db')
            connection_string = f"sqlite:///{db_path}"
            print(f"📦 数据库文件：{db_path}")
        else:
            print(f"⚠️ 警告：数据库类型 '{db_type}' 可能不受支持")
            return False

        print()
        print("🔨 开始创建表...")
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
            return False

        # 创建 EPRC 表
        print()
        print("📝 创建 EPRC 表...")
        print()

        # 只创建 EPRC 相关的表
        eprc_tables = [
            EPRCProfitLoss.__table__,
            EPRCRanking.__table__,
            EPRCContent.__table__
        ]

        for table in eprc_tables:
            try:
                table.create(engine, checkfirst=True)
                print(f"  ✅ {table.name}")

                # 显示表的列信息
                if table.name == 'eprc_ranking':
                    print(f"      - 优化：价格字段为 Numeric(12,2) 类型")
                    print(f"      - 优化：删除了 4 个未使用字段")
                elif table.name == 'eprc_profit_loss':
                    print(f"      - 字段：region, estate_name, profit/loss 数据")
                elif table.name == 'eprc_content':
                    print(f"      - 字段：通用内容表（兜底）")

            except Exception as e:
                print(f"  ❌ {table.name}: {e}")

        print()
        print("=" * 80)
        print("✨ EPRC 表创建完成！")
        print("=" * 80)
        print()

        # 显示表结构信息
        print("📊 表结构概览：")
        print()
        print("1. eprc_profit_loss（赚蚀分析表）")
        print("   - content_id, region, estate_name")
        print("   - profit_cases, profit_range, loss_cases, loss_range")
        print("   - record_date (数据日期，EPRC显示前一天的数据)")
        print()
        print("2. eprc_ranking（成交排行榜表）")
        print("   - content_id, rank, estate_name, region")
        print("   - transaction_count, highest_price, lowest_price, avg_price")
        print("   - 价格字段类型：Numeric(12,2) ✨ 支持数值计算")
        print("   - record_date (数据日期，EPRC显示前一天的数据)")
        print()
        print("3. eprc_content（通用内容表）")
        print("   - content_id, title, content_text, content_url")
        print("   - record_date, source_keyword")
        print()

        return True

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print()
        print("请确保已安装所需依赖：")
        print("  pip install sqlalchemy psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_tables():
    """验证表是否创建成功"""
    try:
        from sqlalchemy import create_engine, inspect, text
        import config
        from database.db_config import DB_CONFIG

        db_type = config.DB_TYPE
        db_config = DB_CONFIG.get(db_type)

        if db_type == 'postgresql':
            connection_string = (
                f"postgresql://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            )
        elif db_type == 'sqlite':
            db_path = db_config.get('path', 'data/media_crawler.db')
            connection_string = f"sqlite:///{db_path}"
        else:
            return

        engine = create_engine(connection_string, echo=False)
        inspector = inspect(engine)

        print("🔍 验证表结构...")
        print()

        eprc_tables = ['eprc_profit_loss', 'eprc_ranking', 'eprc_content']

        for table_name in eprc_tables:
            if inspector.has_table(table_name):
                columns = inspector.get_columns(table_name)
                print(f"✅ {table_name} ({len(columns)} 列)")

                # 验证关键字段
                col_names = [col['name'] for col in columns]

                if table_name == 'eprc_ranking':
                    # 验证优化后的字段
                    if 'record_date' in col_names:
                        print(f"   ✅ record_date 字段存在（优化后）")
                    else:
                        print(f"   ⚠️ record_date 字段不存在")

                    if 'highest_price' in col_names:
                        # 检查类型
                        for col in columns:
                            if col['name'] == 'highest_price':
                                col_type = str(col['type'])
                                if 'NUMERIC' in col_type.upper() or 'DECIMAL' in col_type.upper():
                                    print(f"   ✅ highest_price 为 Numeric 类型（优化后）")
                                else:
                                    print(f"   ⚠️ highest_price 类型为 {col_type}")

                    # 验证删除的字段
                    if 'rental_yield' not in col_names:
                        print(f"   ✅ rental_yield 已删除（优化后）")
                    if 'avg_rent' not in col_names:
                        print(f"   ✅ avg_rent 已删除（优化后）")

                print()
            else:
                print(f"❌ {table_name} 不存在")
                print()

    except Exception as e:
        print(f"⚠️ 验证失败: {e}")


def main():
    print("此脚本将创建优化后的 EPRC 数据库表（v2.0）")
    print()
    print("优化内容：")
    print("  ✅ 价格字段使用 Numeric(12,2) 类型（支持数值计算）")
    print("  ✅ 删除了未使用的字段（rental_yield, avg_rent 等）")
    print("  ✅ 字段重命名：data_date → record_date")
    print()

    confirm = input("是否继续？(yes/no): ").strip().lower()

    if confirm == 'yes':
        print()
        success = create_eprc_tables()

        if success:
            print()
            verify_tables()
            print()
            print("=" * 80)
            print("🎉 初始化完成！可以开始使用 EPRC 爬虫了")
            print("=" * 80)
            print()
            print("测试命令：")
            print("  python main.py --platforms eprc --crawler-type search")
            print()
        else:
            print()
            print("❌ 初始化失败，请检查错误信息")
    else:
        print()
        print("已取消操作")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n❌ 运行错误: {e}")
        import traceback
        traceback.print_exc()
