#!/bin/bash
# 停止所有运行中的 Agent

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 停止所有 Agent...${NC}"
echo ""

# 从 PID 文件读取并停止
if [ -f .agent_pids ]; then
    PIDS=$(cat .agent_pids)
    for PID in $PIDS; do
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}停止进程 $PID...${NC}"
            kill $PID 2>/dev/null
            echo -e "${GREEN}✓ 进程 $PID 已停止${NC}"
        else
            echo -e "${YELLOW}⏭️  进程 $PID 不存在${NC}"
        fi
    done
    rm .agent_pids
fi

# 停止所有端口上的 Streamlit 进程
echo ""
echo -e "${YELLOW}检查端口占用...${NC}"

for PORT in 8501 8502 8503 8504; do
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}停止端口 $PORT 上的进程...${NC}"
        lsof -ti :$PORT | xargs kill -9 2>/dev/null
        echo -e "${GREEN}✓ 端口 $PORT 已释放${NC}"
    fi
done

echo ""
echo -e "${GREEN}✅ 所有 Agent 已停止${NC}"
