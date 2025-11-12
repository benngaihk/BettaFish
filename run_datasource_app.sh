#!/bin/bash
# 启动 DataSource Agent Streamlit 应用

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 设置端口
PORT=8504

# 检查端口是否被占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  端口 $PORT 已被占用"
    echo "正在查找占用端口的进程..."
    lsof -i :$PORT
    echo ""
    read -p "是否要终止占用端口的进程? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在终止进程..."
        lsof -ti :$PORT | xargs kill -9
        echo "✓ 进程已终止"
    else
        echo "❌ 启动取消"
        exit 1
    fi
fi

echo "🚀 启动 DataSource Agent (端口: $PORT)"
echo "📊 访问地址: http://localhost:$PORT"
echo ""

# 启动 Streamlit 应用
streamlit run SingleEngineApp/datasource_engine_streamlit_app.py \
    --server.port=$PORT \
    --server.address=localhost \
    --server.headless=true \
    --browser.gatherUsageStats=false
