import { ref, watch } from 'vue'
import { parseLaserAction } from '../utils/dataParser'
import { CONFIG } from '../constants/config'

/**
 * 激光特效管理
 */
export function useLaser(machines, addLaserVision, removeLaserVision) {
    const activeLasers = ref([])
    const shownAttacks = ref([])

    /**
     * 检查并创建激光特效
     */
    function checkForLaserEffects() {
        machines.value.forEach(machine => {
            // 只处理属于当前human的机器人的激光攻击
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

                // 限制历史记录大小
                if (shownAttacks.value.length > 50) {
                    shownAttacks.value = shownAttacks.value.slice(-25)
                }
            }
        })
    }

    /**
     * 创建激光特效
     */
    function createLaserEffect(machine) {
        const laserData = parseLaserAction(machine)
        if (!laserData) return

        console.log(`⚡ 创建激光特效: ${machine.machine_id}`)

        // 创建激光束
        const laser = {
            id: laserData.effectId,
            startPos: laserData.laser_start_pos,
            endPos: laserData.laser_end_pos,
            pathGrids: laserData.laser_path_grids,
            timestamp: Date.now()
        }

        activeLasers.value.push(laser)

        // 0.5秒后移除激光束
        setTimeout(() => {
            activeLasers.value = activeLasers.value.filter(l => l.id !== laserData.effectId)
        }, CONFIG.LASER_DURATION)

        // 创建激光路径视野
        createLaserVision(laserData.laser_path_grids, laserData.effectId)
    }

    /**
     * 创建激光路径的临时视野
     */
    function createLaserVision(pathGrids, effectId) {
        const visionAreas = pathGrids.map((grid, index) => ({
            id: `${effectId}_${index}`,
            center: [grid.x, grid.y],
            radius: CONFIG.LASER_VISION_RADIUS,
            timestamp: Date.now()
        }))

        addLaserVision(visionAreas)

        console.log(`👁️ 创建了${visionAreas.length}个激光视野区域`)

        // 3秒后移除激光视野
        setTimeout(() => {
            removeLaserVision(area => !area.id.startsWith(`${effectId}_`))
        }, CONFIG.LASER_VISION_DURATION)
    }

    // 监听机器人数据变化
    watch(machines, checkForLaserEffects, { deep: true })

    return {
        activeLasers,
        shownAttacks
    }
}

