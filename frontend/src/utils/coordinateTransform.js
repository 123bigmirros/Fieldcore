import { CONFIG } from '../constants/config'

/**
 * 坐标转换工具类
 */
export class CoordinateTransform {
    constructor(viewCenterOffset = { x: 0, y: 0 }, viewRotation = 0) {
        this.viewCenterOffset = viewCenterOffset
        this.viewRotation = viewRotation
    }

    /**
     * 应用旋转变换
     */
    applyRotation(x, y) {
        const cos = Math.cos(this.viewRotation)
        const sin = Math.sin(this.viewRotation)
        return {
            x: x * cos - y * sin,
            y: x * sin + y * cos
        }
    }

    /**
     * 网格坐标转屏幕坐标
     */
    gridToPixel(gridX, gridY) {
        const rotatedCoords = this.applyRotation(
            gridX * CONFIG.GRID_SIZE,
            -gridY * CONFIG.GRID_SIZE
        )

        const worldCenter = {
            x: window.innerWidth / 2 + this.viewCenterOffset.x,
            y: window.innerHeight / 2 + this.viewCenterOffset.y
        }

        return {
            x: worldCenter.x + rotatedCoords.x,
            y: worldCenter.y + rotatedCoords.y
        }
    }

    /**
     * 计算切比雪夫距离（正方形距离）
     */
    static squareDistance(pos1, pos2) {
        const dx = Math.abs(pos1[0] - pos2[0])
        const dy = Math.abs(pos1[1] - pos2[1])
        return Math.max(dx, dy)
    }

    /**
     * 计算机器人朝向方向（4个基本方向）
     */
    getFacingDirection(dx, dy) {
        const rotatedDirection = this.applyRotation(dx, -dy)
        const rotatedDx = rotatedDirection.x
        const rotatedDy = -rotatedDirection.y

        if (Math.abs(rotatedDx) > Math.abs(rotatedDy)) {
            return rotatedDx > 0 ? 'right' : 'left'
        }
        return rotatedDy > 0 ? 'up' : 'down'
    }
}

/**
 * 方向样式配置
 */
export const DIRECTION_STYLES = {
    right: { right: '-2px', top: '25%', width: '8px', height: '50%', borderRadius: '0 4px 4px 0' },
    left: { left: '-2px', top: '25%', width: '8px', height: '50%', borderRadius: '4px 0 0 4px' },
    up: { top: '-2px', left: '25%', width: '50%', height: '8px', borderRadius: '4px 4px 0 0' },
    down: { bottom: '-2px', left: '25%', width: '50%', height: '8px', borderRadius: '0 0 4px 4px' }
}

