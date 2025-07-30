#!/bin/bash

# 启动OpenManus前端系统

echo "🚀 启动OpenManus前端系统..."

# 检查是否在正确的目录
if [ ! -f "run_mcp_server.py" ]; then
    echo "❌ 错误: 请在OpenManus项目根目录运行此脚本"
    exit 1
fi

# 检测Python环境
echo "🐍 检测Python环境..."
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "❌ 错误: 找不到Python环境"
    exit 1
fi

# 检查Node.js环境
echo "📦 检查Node.js环境..."
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 找不到Node.js环境"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ 错误: 找不到npm命令"
    exit 1
fi

# 检查前端依赖
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
sleep 3

# 检查MCP服务器是否成功启动
if ! curl -s http://localhost:8003/mcp/health > /dev/null; then
    echo "❌ MCP服务器启动失败"
    echo "🔍 检查错误信息..."
    kill $MCP_PID 2>/dev/null
    exit 1
fi

echo "✅ MCP服务器启动成功"

# 启动前端开发服务器
echo "🎨 启动前端开发服务器..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo "✅ 系统启动完成!"
echo "🌐 前端地址: http://localhost:3000"
echo "🔧 MCP服务器: http://localhost:8003"
echo ""
echo "💡 现在可以运行测试脚本:"
echo "   python examples/test_human_machine_lineup_simple.py"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "echo '🛑 正在停止服务...'; kill $FRONTEND_PID $MCP_PID 2>/dev/null; exit" INT
wait
