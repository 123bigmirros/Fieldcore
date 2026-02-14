import { ref, computed } from 'vue'
import { CoordinateTransform } from '../utils/coordinateTransform'

/**
 * Viewport control and visibility checks
 */
export function useViewport() {
    const viewCenterOffset = ref({ x: 0, y: 0 })
    const viewRotation = ref(0)
    const laserVisionAreas = ref([])

    // Coordinate transformer
    const transformer = computed(() =>
        new CoordinateTransform(viewCenterOffset.value, viewRotation.value)
    )

    /**
     * Check if a position is visible.
     * Server already applies fog-of-war filtering, so this always returns true.
     * Function signature kept for debug code compatibility.
     */
    function isPositionVisible() {
        return true
    }

    /**
     * Update view center
     */
    function updateViewCenter(offset, rotation) {
        viewCenterOffset.value = offset
        viewRotation.value = rotation
    }

    /**
     * Reset view
     */
    function resetView() {
        viewCenterOffset.value = { x: 0, y: 0 }
        viewRotation.value = 0
    }

    /**
     * Add laser vision areas
     */
    function addLaserVision(areas) {
        laserVisionAreas.value.push(...areas)
    }

    /**
     * Remove laser vision areas
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
