import { ref, computed } from 'vue'
import { CoordinateTransform } from '../utils/coordinateTransform'

/**
 * 视口控制和可见性判断
 */
export function useViewport() {
    const viewCenterOffset = ref({ x: 0, y: 0 })
    const viewRotation = ref(0)
    const laserVisionAreas = ref([])

    // 坐标转换器
    const transformer = computed(() =>
        new CoordinateTransform(viewCenterOffset.value, viewRotation.value)
    )

    /**
     * 检查位置是否在视野内
     */
    function isPositionVisible(position, myMachines) {
        // 检查机器人视野
        const inNormalVision = myMachines.some(machine => {
            const distance = CoordinateTransform.squareDistance(position, machine.position)
            return distance <= machine.visibility_radius
        })

        // 检查激光视野
        const inLaserVision = laserVisionAreas.value.some(area => {
            const distance = CoordinateTransform.squareDistance(position, area.center)
            return distance <= area.radius
        })

        return inNormalVision || inLaserVision
    }

    /**
     * 更新视野中心
     */
    function updateViewCenter(offset, rotation) {
        viewCenterOffset.value = offset
        viewRotation.value = rotation
    }

    /**
     * 重置视野
     */
    function resetView() {
        viewCenterOffset.value = { x: 0, y: 0 }
        viewRotation.value = 0
    }

    /**
     * 添加激光视野区域
     */
    function addLaserVision(areas) {
        laserVisionAreas.value.push(...areas)
    }

    /**
     * 移除激光视野区域
     */
    function removeLaserVision(predicate) {
        laserVisionAreas.value = laserVisionAreas.value.filter(predicate)
    }

    return {
        viewCenterOffset,
        viewRotation,
        laserVisionAreas,
        transformer,
        isPositionVisible,
        updateViewCenter,
        resetView,
        addLaserVision,
        removeLaserVision
    }
}

