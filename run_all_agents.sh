#!/bin/bash
# 启动所有 Agent 的 Streamlit 应用

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         🚀 启动所有 Agent 应用                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Agent 配置
declare -A AGENTS
AGENTS[InsightAgent]="8501:SingleEngineApp/insight_engine_streamlit_app.py"
AGENTS[MediaAgent]="8502:SingleEngineApp/media_engine_streamlit_app.py"
AGENTS[QueryAgent]="8503:SingleEngineApp/query_engine_streamlit_app.py"
AGENTS[DataSourceAgent]="8504:SingleEngineApp/datasource_engine_streamlit_app.py"

# 检查依赖
if ! command -v streamlit &> /dev/null; then
    echo -e "${RED}❌ 错误: Streamlit 未安装${NC}"
    echo "请运行: pip install streamlit"
    exit 1
fi

echo -e "${YELLOW}📋 Agent 端口分配:${NC}"
echo "  - Insight Agent:     端口 8501"
echo "  - Media Agent:       端口 8502"
echo "  - Query Agent:       端口 8503"
echo "  - DataSource Agent:  端口 8504"
echo ""

# 询问启动模式
echo -e "${YELLOW}选择启动模式:${NC}"
echo "  1) 启动所有 Agent"
echo "  2) 选择性启动"
echo "  3) 仅启动 DataSource Agent"
echo ""
read -p "请输入选项 (1-3): " MODE

case $MODE in
    1)
        SELECTED_AGENTS=("InsightAgent" "MediaAgent" "QueryAgent" "DataSourceAgent")
        ;;
    2)
        echo ""
        echo -e "${YELLOW}请选择要启动的 Agent (用空格分隔):${NC}"
        echo "  1) Insight Agent"
        echo "  2) Media Agent"
        echo "  3) Query Agent"
        echo "  4) DataSource Agent"
        echo ""
        read -p "输入选项 (如: 1 3 4): " CHOICES

        SELECTED_AGENTS=()
        for choice in $CHOICES; do
            case $choice in
                1) SELECTED_AGENTS+=("InsightAgent") ;;
                2) SELECTED_AGENTS+=("MediaAgent") ;;
                3) SELECTED_AGENTS+=("QueryAgent") ;;
                4) SELECTED_AGENTS+=("DataSourceAgent") ;;
            esac
        done
        ;;
    3)
        SELECTED_AGENTS=("DataSourceAgent")
        ;;
    *)
        echo -e "${RED}❌ 无效选项${NC}"
        exit 1
        ;;
esac

# 检查端口占用
echo ""
echo -e "${YELLOW}🔍 检查端口占用...${NC}"
for agent in "${SELECTED_AGENTS[@]}"; do
    IFS=':' read -r port script <<< "${AGENTS[$agent]}"

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  端口 $port ($agent) 已被占用${NC}"
        read -p "是否终止占用进程? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            lsof -ti :$port | xargs kill -9 2>/dev/null
            echo -e "${GREEN}✓ 进程已终止${NC}"
        else
            echo -e "${RED}⏭️  跳过 $agent${NC}"
            continue
        fi
    fi
done

# 启动 Agent
echo ""
echo -e "${GREEN}🚀 开始启动 Agent...${NC}"
echo ""

PIDS=()

for agent in "${SELECTED_AGENTS[@]}"; do
    IFS=':' read -r port script <<< "${AGENTS[$agent]}"

    # 检查脚本是否存在
    if [ ! -f "$script" ]; then
        echo -e "${RED}❌ 脚本不存在: $script${NC}"
        continue
    fi

    echo -e "${BLUE}启动 $agent (端口: $port)...${NC}"

    # 后台启动
    nohup streamlit run "$script" \
        --server.port=$port \
        --server.address=localhost \
        --server.headless=true \
        --browser.gatherUsageStats=false \
        > "logs/${agent,,}_streamlit.log" 2>&1 &

    PID=$!
    PIDS+=($PID)

    echo -e "${GREEN}✓ $agent 已启动 (PID: $PID)${NC}"
    echo -e "  访问地址: ${BLUE}http://localhost:$port${NC}"
    echo ""

    # 等待一下，避免端口冲突
    sleep 2
done

# 保存 PID 到文件
echo "${PIDS[@]}" > .agent_pids

echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ 所有 Agent 已启动！${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}📝 访问地址:${NC}"
for agent in "${SELECTED_AGENTS[@]}"; do
    IFS=':' read -r port script <<< "${AGENTS[$agent]}"
    echo -e "  - $agent: ${BLUE}http://localhost:$port${NC}"
done
echo ""
echo -e "${YELLOW}📋 管理命令:${NC}"
echo "  - 查看日志: tail -f logs/*_streamlit.log"
echo "  - 停止所有: ./stop_all_agents.sh"
echo "  - 查看进程: ps -p \$(cat .agent_pids)"
echo ""
echo -e "${YELLOW}💡 提示: 按 Ctrl+C 不会停止后台进程，请使用 ./stop_all_agents.sh${NC}"
