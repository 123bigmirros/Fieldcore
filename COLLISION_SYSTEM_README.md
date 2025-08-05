# 碰撞检测系统升级说明

## 概述

我已经成功升级了 `world_manager.py`，添加了障碍物概念和碰撞检测功能。现在当Human Agent控制Machine Agent移动时，系统会自动进行碰撞检测，如果前进道路有障碍物，就不允许继续移动。

## 主要新功能

### 1. 障碍物系统
- **静态障碍物**: 可以在世界中添加固定的障碍物
- **机器人作为障碍物**: 每个机器人默认占据一个单位空间（可配置大小）
- **动态碰撞检测**: 实时检测移动路径上的碰撞

### 2. 核心特性
- **碰撞检测**: 在机器人移动前检查目标位置是否有障碍物或其他机器人
- **详细错误信息**: 当碰撞发生时，系统会返回详细的碰撞信息
- **边界检测**: 确保机器人不会移动到世界边界之外
- **大小可配置**: 机器人和障碍物的大小都可以自定义

## 新增的数据结构

### Position 类 (升级)
```python
class Position:
    def is_within_bounds(self, min_pos: Position, max_pos: Position) -> bool
    # 检查位置是否在边界内
```

### Obstacle 类 (新增)
```python
@dataclass
class Obstacle:
    obstacle_id: str          # 障碍物ID
    position: Position        # 位置
    size: float = 1.0        # 大小（半径）
    obstacle_type: str = "static"  # 类型
```

### MachineInfo 类 (升级)
```python
@dataclass
class MachineInfo:
    # ... 原有属性 ...
    size: float = 1.0  # 机器人大小（半径）
```

## 新增的核心方法

### WorldManager 类新方法
```python
# 碰撞检测
def check_collision(self, position: Position, size: float = None, exclude_machine_id: str = None) -> bool
def find_collision_details(self, position: Position, size: float = None, exclude_machine_id: str = None) -> List[str]

# 位置更新（带碰撞检测）
def update_machine_position_with_details(self, machine_id: str, new_position: Position) -> Tuple[bool, List[str]]

# 障碍物管理
def add_obstacle(self, obstacle_id: str, position: Position, size: float = 1.0, obstacle_type: str = "static") -> bool
def remove_obstacle(self, obstacle_id: str) -> bool
def get_obstacle(self, obstacle_id: str) -> Optional[Obstacle]
def get_all_obstacles(self) -> Dict[str, Obstacle]
def clear_all_obstacles(self) -> None
```

## 新增的MCP工具

### 障碍物管理工具
- `add_obstacle`: 添加障碍物
- `remove_obstacle`: 移除障碍物
- `get_obstacle_info`: 获取障碍物信息
- `get_all_obstacles`: 获取所有障碍物
- `clear_all_obstacles`: 清除所有障碍物
- `check_collision`: 检查指定位置的碰撞情况

### 升级的工具
- `update_machine_position`: 现在包含碰撞检测和详细错误信息

## HTTP API端点

### 新增端点
```
GET    /mcp/obstacles           # 获取所有障碍物
POST   /mcp/obstacles           # 添加障碍物
DELETE /mcp/obstacles/<id>      # 删除障碍物
POST   /mcp/collision/check     # 检查碰撞
```

## 使用示例

### 1. 添加障碍物
```python
# 通过Human Agent添加障碍物
await human.call_tool(
    "mcp_python_add_obstacle",
    obstacle_id="wall_1",
    position=[5.0, 0.0, 0.0],
    size=1.0,
    obstacle_type="static"
)
```

### 2. 测试碰撞
```python
# 尝试移动到有障碍物的位置
result = await human.run("让robot_01移动到位置(5,0,0)")
# 如果有碰撞，会返回详细的错误信息
```

### 3. 检查碰撞
```python
# 直接检查位置是否会发生碰撞
collision_info = await human.call_tool(
    "mcp_python_check_collision",
    position=[5.0, 0.0, 0.0],
    size=1.0
)
```

### 4. 创建不同大小的机器人
```python
# 创建大型机器人
large_machine = MachineAgent(
    machine_id="large_robot",
    size=2.0  # 大机器人占用更多空间
)

# 创建小型机器人
small_machine = MachineAgent(
    machine_id="small_robot",
    size=0.5  # 小机器人占用较少空间
)
```

## 测试脚本

运行 `test_collision_demo.py` 来测试完整的碰撞检测系统：

```bash
python test_collision_demo.py
```

该脚本会测试：
1. 添加静态障碍物
2. 机器人与障碍物碰撞检测
3. 机器人间碰撞检测
4. 直接碰撞检测API
5. 创建迷宫环境
6. 智能路径规划

## 兼容性

- ✅ 完全向后兼容
- ✅ 不影响现有功能
- ✅ 原有的移动命令会自动包含碰撞检测
- ✅ 可选功能：可以选择性使用障碍物系统

## 配置选项

在 `WorldManager` 初始化时可以配置：
- `world_bounds`: 世界边界（默认 -100 到 100）

在 `MachineAgent` 初始化时可以配置：
- `size`: 机器人大小（碰撞检测半径，默认 1.0）

在 `Obstacle` 创建时可以配置：
- `size`: 障碍物大小（碰撞检测半径，默认 1.0）

## 性能考虑

- 碰撞检测使用欧几里得距离计算，复杂度为 O(n)，其中n是障碍物和机器人总数
- 文件系统持久化确保跨进程状态共享
- 适合中小规模机器人数量（<100个）

## 未来扩展

可以进一步扩展的功能：
1. 路径规划算法（A*）
2. 动态障碍物
3. 复杂形状的障碍物
4. 碰撞预测
5. 物理仿真集成
