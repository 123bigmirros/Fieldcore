// 游戏配置常量
export const CONFIG = {
    GRID_SIZE: 30,           // 网格大小（像素）
    REFRESH_INTERVAL: 300,   // 刷新间隔（毫秒）
    LASER_DURATION: 500,     // 激光持续时间（毫秒）
    LASER_VISION_DURATION: 3000, // 激光视野持续时间（毫秒）
    LASER_VISION_RADIUS: 2,  // 激光视野半径（格）
    SPACE_KEY_TIMEOUT: 500,  // 双击空格超时（毫秒）
    MESSAGE_DURATION: 3000,  // 消息显示时长（毫秒）
    API_BASE_URL: 'http://localhost:8004',
    MCP_BASE_URL: '/mcp'
}

// 默认值
export const DEFAULTS = {
    MACHINE_COUNT: 3,
    MACHINE_SIZE: 1.0,
    VISIBILITY_RADIUS: 3.0,
    FACING_DIRECTION: [1.0, 0.0],
    LASER_RANGE: 5.0
}

// 颜色主题
export const COLORS = {
    MY_MACHINE: '#74b9ff',
    OTHER_MACHINE: '#95a5a6',
    LASER: '#ff3232',
    OBSTACLE: '#636e72'
}

