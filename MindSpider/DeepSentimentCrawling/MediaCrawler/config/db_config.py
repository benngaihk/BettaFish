# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


import os
from pathlib import Path

# 尝试加载.env文件（支持从项目根目录或当前目录）
try:
    from dotenv import load_dotenv
    # 查找.env文件：优先当前目录，其次项目根目录，最后BettaFish目录
    current_file = Path(__file__).resolve()
    # db_config.py 在 MediaCrawler/config/ 目录下
    # current_file.parent = MediaCrawler/config
    # current_file.parent.parent = MediaCrawler
    # current_file.parent.parent.parent = DeepSentimentCrawling
    # current_file.parent.parent.parent.parent = MindSpider
    mindspider_root = current_file.parent.parent.parent.parent  # MindSpider根目录
    bettafish_root = mindspider_root.parent  # BettaFish根目录（MindSpider的父目录）
    
    env_files = [
        Path.cwd() / ".env",  # 当前工作目录
        bettafish_root / ".env",  # BettaFish根目录（.env文件所在位置）
        mindspider_root / ".env",  # MindSpider根目录
        current_file.parent / ".env",  # config目录
    ]
    loaded = False
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=True)
            loaded = True
            break
    
    # 如果都没找到，尝试使用pydantic_settings的方式（从MindSpider的config.py加载）
    if not loaded:
        try:
            import sys
            sys.path.insert(0, str(mindspider_root))
            from config import settings
            # 将settings中的配置设置到环境变量中（覆盖现有值）
            if hasattr(settings, "DB_HOST") and settings.DB_HOST:
                os.environ["DB_HOST"] = settings.DB_HOST
            if hasattr(settings, "DB_PORT") and settings.DB_PORT:
                os.environ["DB_PORT"] = str(settings.DB_PORT)
            if hasattr(settings, "DB_USER") and settings.DB_USER:
                os.environ["DB_USER"] = settings.DB_USER
            if hasattr(settings, "DB_PASSWORD") and settings.DB_PASSWORD:
                os.environ["DB_PASSWORD"] = settings.DB_PASSWORD
            if hasattr(settings, "DB_NAME") and settings.DB_NAME:
                os.environ["DB_NAME"] = settings.DB_NAME
            if hasattr(settings, "DB_DIALECT") and settings.DB_DIALECT:
                os.environ["DB_DIALECT"] = settings.DB_DIALECT
        except Exception as e:
            # 如果加载失败，使用默认值
            pass
except ImportError:
    # 如果没有安装python-dotenv，尝试使用pydantic_settings的方式
    try:
        import sys
        current_file = Path(__file__).resolve()
        mindspider_root = current_file.parent.parent.parent.parent  # MindSpider根目录
        sys.path.insert(0, str(mindspider_root))
        from config import settings
        # 将settings中的配置设置到环境变量中
        if hasattr(settings, "DB_HOST") and settings.DB_HOST:
            os.environ["DB_HOST"] = settings.DB_HOST
        if hasattr(settings, "DB_PORT") and settings.DB_PORT:
            os.environ["DB_PORT"] = str(settings.DB_PORT)
        if hasattr(settings, "DB_USER") and settings.DB_USER:
            os.environ["DB_USER"] = settings.DB_USER
        if hasattr(settings, "DB_PASSWORD") and settings.DB_PASSWORD:
            os.environ["DB_PASSWORD"] = settings.DB_PASSWORD
        if hasattr(settings, "DB_NAME") and settings.DB_NAME:
            os.environ["DB_NAME"] = settings.DB_NAME
        if hasattr(settings, "DB_DIALECT") and settings.DB_DIALECT:
            os.environ["DB_DIALECT"] = settings.DB_DIALECT
    except:
        pass

# mysql config - 使用MindSpider的数据库配置或环境变量
# 优先使用统一的DB_*配置，其次使用MYSQL_*配置
MYSQL_DB_PWD = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_DB_PWD", "bettafish")
MYSQL_DB_USER = os.getenv("DB_USER") or os.getenv("MYSQL_DB_USER", "bettafish")
MYSQL_DB_HOST = os.getenv("DB_HOST") or os.getenv("MYSQL_DB_HOST", "127.0.0.1")
# 如果DB_DIALECT是mysql，使用DB_PORT；否则使用MYSQL_DB_PORT
db_dialect = os.getenv("DB_DIALECT", "").lower()
if db_dialect == "mysql":
    MYSQL_DB_PORT = int(os.getenv("DB_PORT") or os.getenv("MYSQL_DB_PORT", "3306"))
else:
    MYSQL_DB_PORT = int(os.getenv("DB_PORT") or os.getenv("MYSQL_DB_PORT", "3306"))
MYSQL_DB_NAME = os.getenv("DB_NAME") or os.getenv("MYSQL_DB_NAME", "bettafish")

mysql_db_config = {
    "user": MYSQL_DB_USER,
    "password": MYSQL_DB_PWD,
    "host": MYSQL_DB_HOST,
    "port": MYSQL_DB_PORT,
    "db_name": MYSQL_DB_NAME,
}


# redis config
REDIS_DB_HOST = os.getenv("REDIS_DB_HOST", "127.0.0.1")  # your redis host
REDIS_DB_PWD = os.getenv("REDIS_DB_PWD", "123456")  # your redis password
REDIS_DB_PORT = int(os.getenv("REDIS_DB_PORT", "6379"))  # your redis port
REDIS_DB_NUM = int(os.getenv("REDIS_DB_NUM", "0"))  # your redis db num

# cache type
CACHE_TYPE_REDIS = "redis"
CACHE_TYPE_MEMORY = "memory"

# sqlite config
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "sqlite_tables.db")

sqlite_db_config = {
    "db_path": SQLITE_DB_PATH
}

# postgresql config - 优先使用MindSpider的统一数据库配置（DB_*），其次使用POSTGRESQL_*环境变量
# 如果DB_DIALECT是postgresql，使用DB_*配置；否则使用POSTGRESQL_*配置
if db_dialect == "postgresql":
    POSTGRESQL_DB_PWD = os.getenv("DB_PASSWORD") or os.getenv("POSTGRESQL_DB_PWD", "bettafish")
    POSTGRESQL_DB_USER = os.getenv("DB_USER") or os.getenv("POSTGRESQL_DB_USER", "bettafish")
    POSTGRESQL_DB_HOST = os.getenv("DB_HOST") or os.getenv("POSTGRESQL_DB_HOST", "127.0.0.1")
    POSTGRESQL_DB_PORT = int(os.getenv("DB_PORT") or os.getenv("POSTGRESQL_DB_PORT", "5432"))
    POSTGRESQL_DB_NAME = os.getenv("DB_NAME") or os.getenv("POSTGRESQL_DB_NAME", "bettafish")
else:
    # 如果DB_DIALECT不是postgresql，使用默认的PostgreSQL配置
    POSTGRESQL_DB_PWD = os.getenv("POSTGRESQL_DB_PWD") or os.getenv("DB_PASSWORD", "bettafish")
    POSTGRESQL_DB_USER = os.getenv("POSTGRESQL_DB_USER") or os.getenv("DB_USER", "bettafish")
    POSTGRESQL_DB_HOST = os.getenv("POSTGRESQL_DB_HOST") or os.getenv("DB_HOST", "127.0.0.1")
    POSTGRESQL_DB_PORT = int(os.getenv("POSTGRESQL_DB_PORT") or os.getenv("DB_PORT", "5432"))
    POSTGRESQL_DB_NAME = os.getenv("POSTGRESQL_DB_NAME") or os.getenv("DB_NAME", "bettafish")

postgresql_db_config = {
    "user": POSTGRESQL_DB_USER,
    "password": POSTGRESQL_DB_PWD,
    "host": POSTGRESQL_DB_HOST,
    "port": POSTGRESQL_DB_PORT,
    "db_name": POSTGRESQL_DB_NAME,
}

