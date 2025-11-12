"""
Streamlit Web界面
为 DataSource Agent 提供友好的Web界面
"""

import os
import sys
import streamlit as st
from datetime import datetime
import json
import locale
from loguru import logger
from pathlib import Path

# 设置UTF-8编码环境
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 设置系统编码
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except locale.Error:
        pass

# 添加项目根目录到Python路径
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from DataSourceEngine import DataSourceAgent, scan_data_source_files
from DataSourceEngine.utils.config import Settings
from config import settings


def main():
    """主函数"""
    st.set_page_config(
        page_title="DataSource Agent",
        page_icon="📊",
        layout="wide"
    )

    st.title("📊 DataSource Agent")
    st.markdown("**外部数据源相关性判断与深度分析**")
    st.markdown("自动扫描、评估和分析外部数据源，提供智能化的数据筛选和洞察")

    # 检查URL参数
    try:
        # 尝试使用新版本的query_params
        query_params = st.query_params
        auto_query = query_params.get('query', '')
        auto_search = query_params.get('auto_search', 'false').lower() == 'true'
    except AttributeError:
        # 兼容旧版本
        query_params = st.experimental_get_query_params()
        auto_query = query_params.get('query', [''])[0]
        auto_search = query_params.get('auto_search', ['false'])[0].lower() == 'true'

    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")

        # 数据源目录
        data_source_dir = st.text_input(
            "数据源目录",
            value="DataSourceEngine/data_source",
            help="存放JSON数据源文件的目录"
        )

        # 扫描数据源
        if st.button("🔍 扫描数据源"):
            with st.spinner("正在扫描数据源..."):
                try:
                    # 扫描数据源文件
                    data_source_path = os.path.join(project_root, data_source_dir)
                    if os.path.exists(data_source_path):
                        json_files = [f for f in os.listdir(data_source_path) if f.endswith('.json')]
                        st.session_state.available_sources = json_files
                        st.session_state.data_source_dir = data_source_path
                        st.success(f"✓ 发现 {len(json_files)} 个数据源文件")

                        # 显示数据源列表
                        if json_files:
                            st.write("**可用数据源**:")
                            for i, file in enumerate(json_files, 1):
                                st.write(f"{i}. {file}")
                    else:
                        st.error(f"目录不存在: {data_source_dir}")
                except Exception as e:
                    st.error(f"扫描失败: {str(e)}")

        # 显示当前可用数据源
        if 'available_sources' in st.session_state:
            st.info(f"当前有 {len(st.session_state.available_sources)} 个可用数据源")

        st.divider()

        # 高级配置
        with st.expander("🔧 高级配置"):
            relevance_threshold = st.slider(
                "相关性阈值",
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.05,
                help="只有相关性评分高于此阈值的数据源才会被认为相关"
            )

            max_samples = st.number_input(
                "数据预览样本数",
                min_value=10,
                max_value=200,
                value=50,
                help="用于相关性分析的数据样本数量"
            )

            # 选择要分析的数据源
            if 'available_sources' in st.session_state and st.session_state.available_sources:
                selected_sources = st.multiselect(
                    "选择要分析的数据源",
                    options=st.session_state.available_sources,
                    default=st.session_state.available_sources,
                    help="可以选择一个或多个数据源进行分析"
                )
                st.session_state.selected_sources = selected_sources
            else:
                st.warning("请先扫描数据源")

    # 主界面
    # 查询输入区域
    display_query = auto_query if auto_query else "请输入您的问题或分析需求..."

    query = st.text_area(
        "分析查询",
        value=display_query if auto_query else "",
        height=100,
        placeholder=display_query,
        help="输入您想要分析的问题，系统会自动判断哪些数据源与之相关",
        disabled=bool(auto_query) and not auto_search,
        label_visibility="hidden"
    )

    # 自动搜索逻辑
    start_analysis = False

    if auto_search and auto_query and 'auto_search_executed' not in st.session_state:
        st.session_state.auto_search_executed = True
        start_analysis = True
        query = auto_query
    elif auto_query and not auto_search:
        st.warning("等待分析启动信号...")

    # 手动触发按钮
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🚀 开始分析", type="primary", use_container_width=True):
            start_analysis = True
    with col2:
        if st.button("🔄 重置", use_container_width=True):
            if 'analysis_result' in st.session_state:
                del st.session_state.analysis_result
            if 'auto_search_executed' in st.session_state:
                del st.session_state.auto_search_executed
            st.rerun()

    # 执行分析
    if start_analysis:
        if not query or not query.strip():
            st.error("❌ 请输入分析查询")
            return

        # 检查是否有可用数据源
        if 'available_sources' not in st.session_state or not st.session_state.available_sources:
            st.error("❌ 没有可用的数据源，请先扫描数据源目录")
            return

        # 检查API配置
        if not settings.DATA_SOURCE_ENGINE_API_KEY and not settings.INSIGHT_ENGINE_API_KEY:
            st.error("❌ 请设置 DATA_SOURCE_ENGINE_API_KEY 或 INSIGHT_ENGINE_API_KEY 环境变量")
            return

        execute_analysis(
            query=query.strip(),
            relevance_threshold=relevance_threshold if 'relevance_threshold' in locals() else 0.6,
            max_samples=max_samples if 'max_samples' in locals() else 50
        )

    # 显示分析结果
    if 'analysis_result' in st.session_state:
        display_analysis_results(st.session_state.analysis_result)


def execute_analysis(query: str, relevance_threshold: float = 0.6, max_samples: int = 50):
    """执行数据源分析"""
    try:
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 初始化Agent
        status_text.text("正在初始化 DataSource Agent...")

        config = Settings(
            DATA_SOURCE_ENGINE_API_KEY=settings.DATA_SOURCE_ENGINE_API_KEY or settings.INSIGHT_ENGINE_API_KEY,
            DATA_SOURCE_ENGINE_MODEL_NAME=settings.DATA_SOURCE_ENGINE_MODEL_NAME or settings.INSIGHT_ENGINE_MODEL_NAME,
            DATA_SOURCE_ENGINE_BASE_URL=settings.DATA_SOURCE_ENGINE_BASE_URL or settings.INSIGHT_ENGINE_BASE_URL,
            MAX_RELEVANCE_SCORE_THRESHOLD=relevance_threshold,
            MAX_DATA_SAMPLES_FOR_ANALYSIS=max_samples,
            OUTPUT_DIR="datasource_engine_streamlit_reports"
        )

        agent = DataSourceAgent(config)
        progress_bar.progress(10)

        # 添加数据源
        status_text.text("正在加载数据源...")

        data_source_dir = st.session_state.get('data_source_dir', 'DataSourceEngine/data_source')
        selected_sources = st.session_state.get('selected_sources', st.session_state.get('available_sources', []))

        total_sources = len(selected_sources)
        for i, source_file in enumerate(selected_sources, 1):
            source_path = os.path.join(data_source_dir, source_file)
            source_id = f"source_{i}_{source_file.replace('.json', '')}"

            try:
                agent.add_data_source(
                    source_id=source_id,
                    source_type="json_file",
                    source_path=source_path,
                    metadata={
                        "filename": source_file,
                        "streamlit": True
                    }
                )
                status_text.text(f"已加载数据源 {i}/{total_sources}: {source_file}")
                progress_bar.progress(10 + (30 * i // total_sources))
            except Exception as e:
                st.warning(f"⚠️ 加载数据源 {source_file} 失败: {str(e)}")

        progress_bar.progress(40)

        # 执行相关性分析
        status_text.text("正在分析数据源相关性...")
        result = agent.analyze_relevance(query, save_results=True)
        progress_bar.progress(70)

        # 完成
        status_text.text("分析完成！")
        progress_bar.progress(100)

        # 保存结果到session state
        st.session_state.analysis_result = result

        st.success("✅ 分析完成！")

        # 清空进度显示
        status_text.empty()
        progress_bar.empty()

    except Exception as e:
        st.error(f"❌ 分析失败: {str(e)}")
        logger.exception(f"分析失败: {str(e)}")


def display_analysis_results(result: dict):
    """显示分析结果"""
    st.divider()
    st.header("📊 分析结果")

    # 总体概况
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总数据源数", result['total_sources'])
    with col2:
        st.metric("相关数据源", result['relevant_sources'],
                 delta=f"{result['relevant_sources']/result['total_sources']*100:.0f}%" if result['total_sources'] > 0 else "0%")
    with col3:
        avg_score = sum(a['relevance_score'] for a in result['relevance_analyses']) / len(result['relevance_analyses']) if result['relevance_analyses'] else 0
        st.metric("平均相关性", f"{avg_score:.2f}")
    with col4:
        has_analysis = 'data_analysis' in result and result['data_analysis']
        st.metric("数据分析", "✅ 已完成" if has_analysis else "⏭️ 跳过")

    # Tab视图
    tab1, tab2, tab3, tab4 = st.tabs(["📝 相关性分析", "🎯 使用策略", "🔍 数据分析", "💾 原始数据"])

    with tab1:
        st.subheader("相关性分析详情")

        for i, analysis in enumerate(result['relevance_analyses'], 1):
            with st.expander(
                f"**数据源 {i}: {analysis['source_id']}** - 相关性: {analysis['relevance_score']:.2f} {'✅' if analysis['is_relevant'] else '❌'}",
                expanded=analysis['is_relevant']
            ):
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.write("**基本信息**")
                    st.write(f"- 相关性评分: `{analysis['relevance_score']:.2f}`")
                    st.write(f"- 是否相关: {'✅ 是' if analysis['is_relevant'] else '❌ 否'}")

                    if analysis.get('key_matches'):
                        st.write("**关键匹配点**:")
                        for match in analysis['key_matches']:
                            st.write(f"  - {match}")

                with col2:
                    st.write("**判断理由**")
                    st.info(analysis['reasoning'])

                    st.write("**使用建议**")
                    st.success(analysis['usage_recommendation'])

    with tab2:
        st.subheader("数据使用策略")
        st.markdown(result['usage_strategy'])

        # 相关数据源列表
        if result['relevant_source_ids']:
            st.write("**推荐使用的数据源**:")
            for source_id in result['relevant_source_ids']:
                st.write(f"- `{source_id}`")

    with tab3:
        st.subheader("深度数据分析")

        if 'data_analysis' in result and result['data_analysis']:
            analysis = result['data_analysis']

            # 分析总结
            st.markdown("### 📋 分析总结")
            st.info(analysis.get('analysis_summary', '无'))

            # 关键发现
            if analysis.get('key_findings'):
                st.markdown("### 🔑 关键发现")
                for i, finding in enumerate(analysis['key_findings'], 1):
                    st.write(f"{i}. {finding}")

            # 深度洞察
            if analysis.get('insights'):
                st.markdown("### 💡 深度洞察")
                for i, insight in enumerate(analysis['insights'], 1):
                    if isinstance(insight, dict):
                        with st.expander(f"**{i}. {insight.get('title', '洞察')}**"):
                            st.write(insight.get('description', ''))
                            if insight.get('supporting_data'):
                                st.caption(f"支撑数据: {insight.get('supporting_data')}")
                    else:
                        st.write(f"{i}. {insight}")

            # 行动建议
            if analysis.get('recommendations'):
                st.markdown("### 🎯 行动建议")
                for i, rec in enumerate(analysis['recommendations'], 1):
                    if isinstance(rec, dict):
                        priority = rec.get('priority', 'medium').upper()
                        priority_color = {
                            'HIGH': '🔴',
                            'MEDIUM': '🟡',
                            'LOW': '🟢'
                        }.get(priority, '⚪')

                        st.write(f"{priority_color} **[{priority}]** {rec.get('action', '')}")
                        if rec.get('rationale'):
                            st.caption(f"理由: {rec.get('rationale')}")
                    else:
                        st.write(f"{i}. {rec}")

            # 额外信息
            col1, col2 = st.columns(2)
            with col1:
                if analysis.get('data_quality_notes'):
                    st.markdown("#### 数据质量评估")
                    st.text(analysis['data_quality_notes'])
            with col2:
                if analysis.get('limitations'):
                    st.markdown("#### 分析局限性")
                    st.text(analysis['limitations'])
        else:
            st.info("ℹ️ 没有相关数据源，跳过了数据分析")

    with tab4:
        st.subheader("原始数据")
        st.json(result)

    # 下载按钮
    st.divider()
    col1, col2 = st.columns([1, 5])
    with col1:
        # 生成JSON下载
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="💾 下载JSON结果",
            data=json_str,
            file_name=f"datasource_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )


if __name__ == "__main__":
    main()
