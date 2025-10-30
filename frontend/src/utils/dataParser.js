/**
 * 数据解析工具
 * 处理后端返回的多层JSON数据
 */

/**
 * 解析API返回的数据
 * @param {*} data - 原始数据
 * @returns {Array|Object} 解析后的数据
 */
export function parseApiData(data) {
    let parsed = data

    // 第一层解析：HTTP响应（字符串化的JSON）
    if (typeof parsed === 'string') {
        try {
            parsed = JSON.parse(parsed)
        } catch {
            return null
        }
    }

    // 第二层解析：提取output中的实际数据
    if (parsed?.output && typeof parsed.output === 'string') {
        try {
            parsed = JSON.parse(parsed.output)
        } catch {
            return null
        }
    }

    // 转换为数组格式
    if (parsed && !Array.isArray(parsed) && typeof parsed === 'object') {
        parsed = Object.values(parsed)
    }

    return Array.isArray(parsed) ? parsed : null
}

/**
 * 从last_action中解析激光攻击数据
 * @param {Object} machine - 机器人对象
 * @returns {Object|null} 激光数据
 */
export function parseLaserAction(machine) {
    if (!machine.last_action?.includes('laser_attack')) {
        return null
    }

    const timestamp = machine.last_action.match(/time:(\d+)/)
    const effectId = timestamp ? timestamp[1] : Date.now().toString()

    // 尝试从last_action中提取后端计算的完整结果
    const resultMatch = machine.last_action.match(/result_(.+)$/)
    if (resultMatch) {
        try {
            const backendResult = JSON.parse(resultMatch[1])
            return { effectId, ...backendResult }
        } catch (e) {
            console.warn('解析后端激光数据失败:', e)
        }
    }

    // 降级方案：使用简化数据
    const rangeMatch = machine.last_action.match(/range_([0-9.]+)/)
    const range = rangeMatch ? parseFloat(rangeMatch[1]) : 5.0
    const [x, y] = machine.position
    const [dx, dy] = machine.facing_direction

    return {
        effectId,
        attacker_position: [x, y],
        facing_direction: [dx, dy],
        laser_start_pos: [x, y],
        laser_end_pos: [x + dx * range, y + dy * range],
        laser_path_grids: generateGridPath(x, y, dx, dy, range),
        actual_range: range,
        hit_result: { hit_type: 'fallback' }
    }
}

/**
 * 生成简单的网格路径
 */
function generateGridPath(x, y, dx, dy, range) {
    const grids = []
    const startX = Math.round(x)
    const startY = Math.round(y)

    for (let i = 0; i <= range; i++) {
        grids.push({
            x: startX + Math.round(dx * i),
            y: startY + Math.round(dy * i)
        })
    }

    return grids
}

