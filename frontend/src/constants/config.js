// Game configuration constants
export const CONFIG = {
    GRID_SIZE: 30,           // Grid size (pixels)
    REFRESH_INTERVAL: 300,   // Refresh interval (ms)
    LASER_DURATION: 500,     // Laser duration (ms)
    LASER_VISION_DURATION: 3000, // Laser vision duration (ms)
    LASER_VISION_RADIUS: 2,  // Laser vision radius (cells)
    SPACE_KEY_TIMEOUT: 500,  // Double-press space timeout (ms)
    MESSAGE_DURATION: 3000,  // Message display duration (ms)
    API_BASE_URL: 'http://localhost:8004'
}

// Defaults
export const DEFAULTS = {
    MACHINE_COUNT: 3,
    MACHINE_SIZE: 1.0,
    VISIBILITY_RADIUS: 3.0,
    FACING_DIRECTION: [1.0, 0.0],
    LASER_RANGE: 5.0
}

// Color theme
export const COLORS = {
    MY_MACHINE: '#74b9ff',
    OTHER_MACHINE: '#95a5a6',
    LASER: '#ff3232',
    OBSTACLE: '#636e72'
}
