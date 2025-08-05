# 障碍物环境演示

## 概述

新的测试环境展示了完整的障碍物碰撞检测系统，包括：
- 围成封闭正方形的外围墙体
- 内部随机分布的障碍物
- 在安全位置自动创建的机器人
- 支持碰撞检测的实时导航

## 🚀 快速开始

### 1. 启动 MCP 服务器
```bash
python run_mcp_server.py
```

### 2. 启动前端 (可选)
```bash
cd frontend
npm run dev
```

### 3. 运行障碍物环境测试
```bash
python examples/test_human_machine_lineup_simple.py
```

## 🏗️ 环境特性

### 障碍物布局
- **外围墙体**: 30x30 单位的封闭正方形边界
- **内部障碍物**: 20个随机分布的静态障碍物
- **安全区域**: 原点附近保留机器人创建空间

### 机器人配置
- **数量**: 5个机器人（根据安全位置动态调整）
- **命名**: 纯数字编码 (01, 02, 03, ...)
- **初始位置**: 自动检测安全位置并创建
- **大小**: 默认 1.0 单位（可配置）

## 🎮 前端界面

### 显示元素
- **机器人**: 蓝色正方形，显示数字编号
- **障碍物**: 灰色正方形，静态显示
- **状态面板**: 右上角实时显示机器人和障碍物数量

### 视觉特效
- **机器人**: 蓝色渐变，悬停放大效果
- **障碍物**: 灰色渐变，轻微悬停效果
- **网格背景**: 帮助定位的对角线网格

## 🎯 测试命令示例

### 基础移动
```
让01号机器人移动到位置(3,3,0)
让所有机器人聚集到原点附近
```

### 碰撞测试
```
让01号机器人移动到位置(15,15,0)  # 撞墙
让02号机器人移动到01号的位置    # 机器人碰撞
```

### 状态查询
```
检查所有机器人的状态
查看机器人01的位置
```

### 复杂任务
```
让所有机器人排成一条线
让机器人们围成一个圆形
让02号和03号机器人交换位置
```

## 🔧 自定义配置

### 修改环境大小
在 `create_obstacle_environment()` 函数中调整：
```python
wall_size = 15  # 调整边界大小
```

### 修改障碍物数量
```python
for i in range(20):  # 调整内部障碍物数量
```

### 修改机器人数量
```python
safe_positions = await find_safe_positions(human, count=5)  # 调整机器人数量
```

### 修改机器人大小
```python
machine = MachineAgent(
    machine_id=machine_id,
    size=2.0,  # 调整机器人大小
    # ...
)
```

## 🛠️ API 端点

### 查看所有障碍物
```bash
curl http://localhost:8003/mcp/obstacles
```

### 添加新障碍物
```bash
curl -X POST http://localhost:8003/mcp/obstacles \
  -H "Content-Type: application/json" \
  -d '{"obstacle_id": "new_wall", "position": [10, 5, 0], "size": 1.0}'
```

### 检查碰撞
```bash
curl -X POST http://localhost:8003/mcp/collision/check \
  -H "Content-Type: application/json" \
  -d '{"position": [5, 5, 0], "size": 1.0}'
```

### 删除障碍物
```bash
curl -X DELETE http://localhost:8003/mcp/obstacles/wall_1
```

## 🎨 前端定制

### 修改机器人颜色
在 `App.vue` 中修改：
```css
.machine {
  background: linear-gradient(135deg, #your_color 0%, #your_darker_color 100%);
}
```

### 修改障碍物样式
```css
.obstacle {
  background: linear-gradient(135deg, #your_color 0%, #your_darker_color 100%);
}
```

### 调整缩放比例
```javascript
getMachineStyle(machine) {
  const scale = 3;  // 调整缩放比例
  // ...
}
```

## 📊 性能说明

- **碰撞检测**: O(n) 复杂度，适合中小规模环境
- **更新频率**: 前端每2秒刷新一次
- **内存使用**: 基于文件的状态持久化
- **并发支持**: 支持多进程共享状态

## 🔍 故障排除

### 机器人创建失败
- 检查是否有足够的安全位置
- 增大安全区域范围
- 减少障碍物密度

### 前端不显示障碍物
- 确认 MCP 服务器正在运行
- 检查 `/mcp/obstacles` 端点是否响应
- 查看浏览器开发者工具的网络请求

### 移动命令被拒绝
- 检查目标位置是否有障碍物
- 使用碰撞检测 API 预先验证
- 确认机器人大小和障碍物大小设置

## 🎯 扩展功能

该演示为后续扩展奠定了基础：
- 路径规划算法
- 动态障碍物
- 多机器人协作
- 任务调度系统
- 实时可视化增强

## 🌟 提示

- 使用 `quit` 命令退出测试环境
- 障碍物会在测试结束时保留，可用于下次测试
- 前端界面支持悬停查看详细信息
- 可以同时运行多个测试实例（不同端口）
