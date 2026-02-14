/**
 * Data parsing utilities
 * Handles multi-layered JSON data returned from the backend
 */

/**
 * Parse data returned from the API
 * @param {*} data - Raw data
 * @returns {Array|Object} Parsed data
 */
export function parseApiData(data) {
    let parsed = data

    // First layer: parse HTTP response (stringified JSON)
    if (typeof parsed === 'string') {
        try {
            parsed = JSON.parse(parsed)
        } catch {
            return null
        }
    }

    // Second layer: extract actual data from the output field
    if (parsed?.output && typeof parsed.output === 'string') {
        try {
            parsed = JSON.parse(parsed.output)
        } catch {
            return null
        }
    }

    // Convert to array format
    if (parsed && !Array.isArray(parsed) && typeof parsed === 'object') {
        parsed = Object.values(parsed)
    }

    return Array.isArray(parsed) ? parsed : null
}

/**
 * Parse laser attack data from last_action
 * @param {Object} machine - Machine object
 * @returns {Object|null} Laser data
 */
export function parseLaserAction(machine) {
    if (!machine.last_action?.includes('laser_attack')) {
        return null
    }

    const timestamp = machine.last_action.match(/time:(\d+)/)
    const effectId = timestamp ? timestamp[1] : Date.now().toString()

    // Try to extract the full backend-computed result from last_action
    const resultMatch = machine.last_action.match(/result_(.+)$/)
    if (resultMatch) {
        try {
            const backendResult = JSON.parse(resultMatch[1])
            return { effectId, ...backendResult }
        } catch (e) {
            console.warn('Failed to parse backend laser data:', e)
        }
    }

    // Fallback: use simplified data
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
 * Generate a simple grid path
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

