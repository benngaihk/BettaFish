@echo off
REM 启动 DataSource Agent Streamlit 应用

cd /d %~dp0

set PORT=8504

echo 🚀 启动 DataSource Agent (端口: %PORT%)
echo 📊 访问地址: http://localhost:%PORT%
echo.

REM 启动 Streamlit 应用
streamlit run SingleEngineApp/datasource_engine_streamlit_app.py ^
    --server.port=%PORT% ^
    --server.address=localhost ^
    --server.headless=true ^
    --browser.gatherUsageStats=false

pause
