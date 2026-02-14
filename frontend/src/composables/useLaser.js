import { ref, watch } from 'vue'
import { parseLaserAction } from '../utils/dataParser'
import { CONFIG } from '../constants/config'

/**
 * Laser effect management
 */
export function useLaser(machines, addLaserVision, removeLaserVision) {
    const activeLasers = ref([])
    const shownAttacks = ref([])

    /**
     * Check for and create laser effects
     */
    function checkForLaserEffects() {
        machines.value.forEach(machine => {
            // Only process laser attacks from machines belonging to the current human
            if (!machine.isMyMachine || !machine.last_action?.includes('laser_attack')) {
                return
            }

            const timeMatch = machine.last_action.match(/time:(\d+)/)
            const attackId = timeMatch
                ? `${machine.machine_id}_${timeMatch[1]}`
                : `${machine.machine_id}_${machine.last_action}`

            if (!shownAttacks.value.includes(attackId)) {
                createLaserEffect(machine)
                shownAttacks.value.push(attackId)

                // Limit history size
                if (shownAttacks.value.length > 50) {
                    shownAttacks.value = shownAttacks.value.slice(-25)
                }
            }
        })
    }

    /**
     * Create a laser effect
     */
    function createLaserEffect(machine) {
        const laserData = parseLaserAction(machine)
        if (!laserData) return

        console.log(`⚡ Creating laser effect: ${machine.machine_id}`)

        // Create laser beam
        const laser = {
            id: laserData.effectId,
            startPos: laserData.laser_start_pos,
            endPos: laserData.laser_end_pos,
            pathGrids: laserData.laser_path_grids,
            timestamp: Date.now()
        }

        activeLasers.value.push(laser)

        // Remove laser beam after 0.5 seconds
        setTimeout(() => {
            activeLasers.value = activeLasers.value.filter(l => l.id !== laserData.effectId)
        }, CONFIG.LASER_DURATION)

        // Create laser path vision
        createLaserVision(laserData.laser_path_grids, laserData.effectId)
    }

    /**
     * Create temporary vision along the laser path
     */
    function createLaserVision(pathGrids, effectId) {
        const visionAreas = pathGrids.map((grid, index) => ({
            id: `${effectId}_${index}`,
            center: [grid.x, grid.y],
            radius: CONFIG.LASER_VISION_RADIUS,
            timestamp: Date.now()
        }))

        addLaserVision(visionAreas)

        console.log(`👁️ Created ${visionAreas.length} laser vision areas`)

        // Remove laser vision after 3 seconds
        setTimeout(() => {
            removeLaserVision(area => !area.id.startsWith(`${effectId}_`))
        }, CONFIG.LASER_VISION_DURATION)
    }

    // Watch for changes in machine data
    watch(machines, checkForLaserEffects, { deep: true })

    return {
        activeLasers,
        shownAttacks
    }
}

