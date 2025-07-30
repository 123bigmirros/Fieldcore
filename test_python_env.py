#!/usr/bin/env python3
"""
测试Python环境和依赖
"""

import sys
import subprocess

def test_imports():
    """测试必要的模块导入"""
    print("🔍 测试Python环境...")
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")

    try:
        import flask
        print(f"✅ Flask已安装，版本: {flask.__version__}")
    except ImportError as e:
        print(f"❌ Flask导入失败: {e}")
        return False

    try:
        import flask_cors
        print("✅ Flask-CORS已安装")
    except ImportError as e:
        print(f"❌ Flask-CORS导入失败: {e}")
        return False

    return True

def test_api_server():
    """测试API服务器启动"""
    print("\n🔧 测试API服务器启动...")
    try:
        # 尝试导入API服务器模块
        sys.path.append('app')
        from api_server import app
        print("✅ API服务器模块导入成功")
        return True
    except Exception as e:
        print(f"❌ API服务器模块导入失败: {e}")
        return False

def install_dependencies():
    """安装依赖"""
    print("\n📦 尝试安装依赖...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "flask", "flask-cors"],
                      check=True, capture_output=True, text=True)
        print("✅ 依赖安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Python环境测试")
    print("=" * 50)

    if not test_imports():
        print("\n💡 尝试安装依赖...")
        if install_dependencies():
            if not test_imports():
                print("❌ 依赖安装后仍然无法导入")
                sys.exit(1)
        else:
            print("❌ 无法安装依赖")
            sys.exit(1)

    if not test_api_server():
        print("❌ API服务器测试失败")
        sys.exit(1)

    print("\n🎉 所有测试通过！")
    print("💡 现在可以运行: ./start_frontend.sh")
