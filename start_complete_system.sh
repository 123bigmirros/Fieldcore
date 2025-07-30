#!/bin/bash

# 启动完整的OpenManus系统

echo "🚀 启动完整的OpenManus系统..."

# 检查是否在正确的目录
if [ ! -f "app/api_server.py" ]; then
    echo "❌ 错误: 请在OpenManus项目根目录运行此脚本"
    exit 1
fi

# 检测Python环境 - 优先使用Anaconda
echo "🐍 检测Python环境..."
if command -v python &> /dev/null && python --version 2>&1 | grep -q "3.11"; then
    PYTHON_CMD="python"
    echo "✅ 使用Anaconda Python 3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo "⚠️  使用系统Python 3"
else
    echo "❌ 错误: 找不到Python环境"
    exit 1
fi

# 检查Python依赖
echo "📦 检查Python依赖..."
$PYTHON_CMD -c "import flask, flask_cors" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少Python依赖，正在安装..."
    if command -v pip &> /dev/null; then
        pip install flask flask-cors
    elif command -v pip3 &> /dev/null; then
        pip3 install flask flask-cors
    else
        echo "❌ 错误: 找不到pip命令"
        exit 1
    fi
else
    echo "✅ Python依赖已安装"
fi

# 检查Node.js依赖
echo "📦 检查前端依赖..."
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 安装前端依赖..."
    cd frontend
    npm install
    cd ..
fi

# 启动MCP服务器
echo "🔧 启动MCP服务器..."
$PYTHON_CMD run_mcp_server.py &
MCP_PID=$!

# 等待MCP服务器启动
echo "⏳ 等待MCP服务器启动..."
sleep 5

# 启动API服务器
echo "🔧 启动API服务器..."
$PYTHON_CMD app/api_server.py &
API_PID=$!

# 等待API服务器启动
echo "⏳ 等待API服务器启动..."
sleep 3

# 检查API服务器是否成功启动
if ! curl -s http://localhost:8000/api/health > /dev/null; then
    echo "❌ API服务器启动失败"
    echo "🔍 检查错误信息..."
    kill $API_PID $MCP_PID 2>/dev/null
    exit 1
fi

echo "✅ API服务器启动成功"

# 启动前端开发服务器
echo "🎨 启动前端开发服务器..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo "✅ 系统启动完成!"
echo "🌐 前端地址: http://localhost:3000"
echo "🔧 API地址: http://localhost:8000"
echo "🤖 MCP服务器: 运行中 (stdio模式)"
echo ""
echo "💡 现在可以运行测试脚本:"
echo "   python examples/test_human_machine_lineup_simple.py"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "echo '🛑 正在停止服务...'; kill $API_PID $FRONTEND_PID $MCP_PID 2>/dev/null; exit" INT
wait
