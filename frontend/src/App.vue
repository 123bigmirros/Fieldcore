<template>
  <div id="app">
    <div class="visualization">
      <div class="world-container">
        <div class="world-grid">
          <!-- 障碍物 -->
          <div
            v-for="obstacle in obstacles"
            :key="obstacle.obstacle_id"
            class="obstacle"
            :style="getObstacleStyle(obstacle)"
            :title="obstacle.obstacle_id"
            v-show="isObstacleVisible(obstacle)"
          >
          </div>
          <!-- 机器人 -->
          <div
            v-for="machine in machines"
            :key="machine.machine_id"
            class="machine"
            :style="getMachineStyle(machine)"
            :title="machine.machine_id"
            v-show="isMachineVisible(machine)"
          >
            <div class="machine-id">{{ getMachineDisplayName(machine.machine_id) }}</div>
            <div class="machine-life">{{ machine.life_value }}</div>
            <!-- 机器人朝向指示器 -->
            <div class="machine-direction" :style="getDirectionStyle(machine)"></div>
          </div>
          <!-- 激光特效 -->
          <div
            v-for="laser in activeLasers"
            :key="'laser-' + laser.id"
            class="laser-beam"
            :style="getLaserStyle(laser)"
            :title="`激光 ${laser.id}`"
          ></div>

          <!-- 网格辅助线 -->
          <div v-if="showGrid" class="grid-overlay"></div>

        </div>
      </div>
    </div>
    <!-- 状态信息 -->
    <div class="status-panel">
      <div class="status-item">
        <span class="status-label">机器人:</span>
        <span class="status-value">{{ machines.length }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">障碍物:</span>
        <span class="status-value">{{ obstacles.length }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
export default {
  name: 'App',
  data() {
    return {
      machines: [],
      obstacles: [],
      refreshInterval: null,
      activeLasers: [], // 活跃的激光特效
      laserVisionAreas: [], // 激光路径的临时视野区域
      shownAttacks: [], // 已经显示过的攻击，避免重复
      showGrid: false // 是否显示网格辅助线
    }
  },
  mounted() {
    this.startAutoRefresh()
    // 监听窗口大小变化，确保网格中心正确
    window.addEventListener('resize', this.forceUpdate)

    // 添加键盘调试快捷键
    window.addEventListener('keydown', (e) => {
      if (e.key === 'd' && e.ctrlKey) {
        e.preventDefault()
        this.showDebugInfo()
      }
      if (e.key === 'g' && e.ctrlKey) {
        e.preventDefault()
        this.toggleGridOverlay()
      }
    })
  },
  beforeUnmount() {
    this.stopAutoRefresh()
    window.removeEventListener('resize', this.forceUpdate)
  },
  methods: {
    async refreshData() {
      // 获取机器人数据
      try {
        const response = await axios.get('/mcp/machines')
        let machines = response.data
        if (typeof machines === 'string') {
          try {
            machines = JSON.parse(machines)
          } catch {
            machines = {}
          }
        }
        if (machines && !Array.isArray(machines) && typeof machines === 'object') {
          machines = Object.values(machines)
        }
        if (machines && Array.isArray(machines)) {
          // 为每个机器人添加默认属性（后端现在会自动删除生命值为0的机器人）
          this.machines = machines.map(machine => ({
            ...machine,
            visibility_radius: machine.visibility_radius || 3.0,
            facing_direction: machine.facing_direction || [1.0, 0.0]
          }))

          // 检查是否有激光攻击效果需要显示（使用处理后的数据）
          this.checkForLaserEffects(this.machines)
        }
      } catch (error) {
        // 只在请求失败时清空
        this.machines = []
      }

      // 获取障碍物数据
      try {
        const response = await axios.get('/mcp/obstacles')
        let obstacles = response.data
        if (typeof obstacles === 'string') {
          try {
            obstacles = JSON.parse(obstacles)
          } catch {
            obstacles = {}
          }
        }
        if (obstacles && !Array.isArray(obstacles) && typeof obstacles === 'object') {
          obstacles = Object.values(obstacles)
        }
        if (obstacles && Array.isArray(obstacles)) {
          this.obstacles = obstacles
        }
      } catch (error) {
        // 只在请求失败时清空
        this.obstacles = []
      }
    },
    startAutoRefresh() {
      this.refreshData()
      this.refreshInterval = setInterval(() => {
        this.refreshData()
      }, 300)  // 300ms刷新一次，提供流畅的动画效果
    },
    stopAutoRefresh() {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval)
        this.refreshInterval = null
      }
    },
    getMachineStyle(machine) {
      const [x, y, z] = machine.position

      // 网格系统：每个单位固定大小
      const gridSize = 30  // 每个网格30px
      // 动态计算屏幕中心作为世界原点
      const worldCenter = {
        x: window.innerWidth / 2,
        y: window.innerHeight / 2
      }

      // 机器人大小等于一个网格单位
      const size = (machine.size || 1.0) * gridSize

      // 机器人可以自由定位，不必对齐网格
      const pixelX = worldCenter.x + x * gridSize
      const pixelY = worldCenter.y - y * gridSize  // 反转Y轴：数学坐标系转屏幕坐标系

      return {
        left: `${pixelX}px`,
        top: `${pixelY}px`,
        width: `${size}px`,
        height: `${size}px`,
        transform: `translate(-50%, -50%)`
      }
    },
    getObstacleStyle(obstacle) {
      const [x, y, z] = obstacle.position

      // 网格系统：每个单位固定大小
      const gridSize = 30  // 每个网格30px
      // 动态计算屏幕中心作为世界原点
      const worldCenter = {
        x: window.innerWidth / 2,
        y: window.innerHeight / 2
      }

      // 障碍物严格占据一个网格单位
      const size = gridSize  // 固定网格大小，确保无间隙

      // 障碍物严格对齐到网格中心
      const pixelX = worldCenter.x + x * gridSize
      const pixelY = worldCenter.y - y * gridSize  // 反转Y轴：数学坐标系转屏幕坐标系

      return {
        left: `${pixelX}px`,
        top: `${pixelY}px`,
        width: `${size}px`,
        height: `${size}px`,
        transform: `translate(-50%, -50%)`
      }
    },
    getMachineDisplayName(machineId) {
      // 提取数字部分，去掉前缀如robot_或其他文本
      const match = machineId.match(/(\d+)/);
      return match ? match[1] : machineId;
    },
    // 计算切比雪夫距离（正方形距离）
    squareDistance(pos1, pos2) {
      const dx = Math.abs(pos1[0] - pos2[0])
      const dy = Math.abs(pos1[1] - pos2[1])
      return Math.max(dx, dy)
    },
    // 检查机器人是否在可见范围内
    isMachineVisible(machine) {
      return this.isPositionVisible(machine.position)
    },
    // 检查障碍物是否在可见范围内
    isObstacleVisible(obstacle) {
      return this.isPositionVisible(obstacle.position)
    },
    // 检查位置是否可见（包括正常视野和激光路径视野）
    isPositionVisible(position) {
      // 检查正常机器人视野
      const inNormalVision = this.machines.some(machine => {
        return this.squareDistance(position, machine.position) <= machine.visibility_radius
      })

      // 检查激光路径视野
      const inLaserVision = this.laserVisionAreas.some(area => {
        const distance = this.squareDistance(position, area.center)
        return distance <= area.radius
      })

      return inNormalVision || inLaserVision
    },

    // 检查是否有激光攻击效果
    checkForLaserEffects(machines) {
      console.log(`🔍 检查激光攻击效果，机器人数量: ${machines.length}`)
      machines.forEach(machine => {
        if (machine.last_action) {
          console.log(`📡 机器人${machine.machine_id}的最后动作: ${machine.last_action}`)
        }
        if (machine.last_action && machine.last_action.includes('laser_attack')) {
          console.log(`🎯 发现激光攻击: ${machine.machine_id}`)
          const timeMatch = machine.last_action.match(/time:(\d+)/)
          if (timeMatch) {
            const attackId = `${machine.machine_id}_${timeMatch[1]}`
            if (!this.shownAttacks.includes(attackId)) {
              console.log(`🚀 创建新的激光特效: ${machine.machine_id}`)
              this.createLaserEffect(machine)
              this.shownAttacks.push(attackId)
              // 限制历史记录大小
              if (this.shownAttacks.length > 50) {
                this.shownAttacks = this.shownAttacks.slice(-25)
              }
            } else {
              console.log(`⏭️  激光攻击已显示过: ${attackId}`)
            }
          } else {
            // 兼容旧格式
            const attackId = `${machine.machine_id}_${machine.last_action}`
            if (!this.shownAttacks.includes(attackId)) {
              console.log(`🚀 创建激光特效(旧格式): ${machine.machine_id}`)
              this.createLaserEffect(machine)
              this.shownAttacks.push(attackId)
            } else {
              console.log(`⏭️  激光攻击已显示过(旧格式): ${attackId}`)
            }
          }
        }
      })
    },
    // 从machine的last_action中解析后端计算的激光攻击结果
    parseLaserActionData(machine) {
      const timestamp = machine.last_action.match(/time:(\d+)/)
      const effectId = timestamp ? timestamp[1] : Date.now().toString()

      // 尝试从last_action中提取后端计算的完整结果
      const resultMatch = machine.last_action.match(/result_(.+)$/)
      if (resultMatch) {
        try {
          const backendResult = JSON.parse(resultMatch[1])
          console.log(`✅ 使用后端计算的激光数据:`, backendResult)

          return {
            effectId: effectId,
            attacker_position: backendResult.attacker_position,
            facing_direction: backendResult.facing_direction,
            laser_start_pos: backendResult.laser_start_pos,
            laser_end_pos: backendResult.laser_end_pos,
            laser_path_grids: backendResult.laser_path_grids,
            actual_range: backendResult.actual_range,
            hit_result: backendResult.hit_result
          }
        } catch (e) {
          console.warn(`⚠️ 解析后端激光数据失败:`, e)
        }
      }

      // 降级方案：使用简化数据
      const rangeMatch = machine.last_action.match(/range_([0-9.]+)/)
      const range = rangeMatch ? parseFloat(rangeMatch[1]) : 5.0

      const [x, y] = machine.position
      const [dx, dy] = machine.facing_direction

      console.log(`⚠️ 降级方案：前端显示完整${range}格激光`)

      return {
        effectId: effectId,
        attacker_position: [x, y],
        facing_direction: [dx, dy],
        laser_start_pos: [x, y],
        laser_end_pos: [x + dx * range, y + dy * range],
        laser_path_grids: this.generateSimpleGridPath(x, y, dx, dy, range),
        actual_range: range,
        hit_result: {hit_type: "fallback"} // 表示降级方案
      }
    },

    // 生成简单的网格路径（纯显示用）
    generateSimpleGridPath(x, y, dx, dy, range) {
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
    },



    // 创建激光特效（基于后端数据）
    createLaserEffect(machine) {
      console.log(`⚡ 开始创建激光特效，机器人${machine.machine_id}`)

      // 解析激光攻击数据
      const laserData = this.parseLaserActionData(machine)

      console.log(`🔫 激光数据解析完成: 起点(${laserData.laser_start_pos[0]}, ${laserData.laser_start_pos[1]}) -> 终点(${laserData.laser_end_pos[0]}, ${laserData.laser_end_pos[1]})`)

      // 创建激光束特效（0.5秒）
      const laser = {
        id: laserData.effectId,
        startPos: laserData.laser_start_pos,
        endPos: laserData.laser_end_pos,
        pathGrids: laserData.laser_path_grids,
        timestamp: Date.now()
      }

      this.activeLasers.push(laser)
      console.log(`⚡ 激光特效已添加到数组，当前活跃激光数量: ${this.activeLasers.length}`)

      setTimeout(() => {
        this.activeLasers = this.activeLasers.filter(l => l.id !== laserData.effectId)
        console.log(`🔄 激光特效已移除，剩余激光数量: ${this.activeLasers.length}`)
      }, 500) // 0.5秒后移除激光束

      // 创建激光路径周围的临时视野（3秒）
      this.createLaserVision({pathGrids: laserData.laser_path_grids}, laserData.effectId)
    },

    // 网格坐标转换为屏幕坐标
    gridToPixel(gridX, gridY) {
      const gridSize = 30
      const worldCenter = {
        x: window.innerWidth / 2,
        y: window.innerHeight / 2
      }

      return {
        x: worldCenter.x + gridX * gridSize,
        y: worldCenter.y - gridY * gridSize // 反转Y轴
      }
    },

    // 从后端API获取激光攻击结果（未来实现）
    async fetchLaserAttackResult(machineId, timestamp) {
      // TODO: 实现从后端API获取激光攻击的完整结果
      // 包括精确的路径、碰撞点、伤害等信息
      // 目前使用简化的方法
      return null
    },

    // 创建激光路径的临时视野（基于网格）
    createLaserVision(laserPath, effectId) {
      // 为激光路径上的每个网格创建视野区域
      const visionGrids = laserPath.pathGrids

      visionGrids.forEach((grid, index) => {
        const visionArea = {
          id: `${effectId}_${index}`,
          center: [grid.x, grid.y], // 网格中心坐标
          radius: 2, // 2格视野范围
          timestamp: Date.now()
        }

        this.laserVisionAreas.push(visionArea)
      })

      console.log(`👁️ 创建了${visionGrids.length}个网格激光视野区域，持续3秒`)

      // 3秒后移除激光视野
      setTimeout(() => {
        const beforeCount = this.laserVisionAreas.length
        this.laserVisionAreas = this.laserVisionAreas.filter(area =>
          !area.id.startsWith(`${effectId}_`)
        )
        console.log(`🔄 激光视野已移除 (${beforeCount - this.laserVisionAreas.length}个区域)`)
      }, 3000)
    },
    // 获取机器人朝向指示器样式
    getDirectionStyle(machine) {
      const [dx, dy] = machine.facing_direction
      const angle = Math.atan2(dy, dx) * 180 / Math.PI
      return {
        transform: `rotate(${angle}deg)`
      }
    },
    // 获取激光特效样式（基于网格坐标）
    getLaserStyle(laser) {
      const [startGridX, startGridY] = laser.startPos
      const [endGridX, endGridY] = laser.endPos

      // 转换为屏幕坐标
      const startPixel = this.gridToPixel(startGridX, startGridY)
      const endPixel = this.gridToPixel(endGridX, endGridY)

      const dx = endPixel.x - startPixel.x
      const dy = endPixel.y - startPixel.y
      const length = Math.sqrt(dx * dx + dy * dy)
      const angle = Math.atan2(dy, dx) * 180 / Math.PI

      const style = {
        left: `${startPixel.x}px`,
        top: `${startPixel.y}px`,
        width: `${length}px`,
        height: '8px',
        transform: `rotate(${angle}deg)`,
        transformOrigin: '0 50%'
      }

      console.log(`🎨 网格激光样式:`, {
        id: laser.id,
        startGrid: [startGridX, startGridY],
        endGrid: [endGridX, endGridY],
        length: `${length.toFixed(1)}px`,
        angle: `${angle.toFixed(1)}°`
      })

      return style
    },
    forceUpdate() {
      // 强制重新渲染，确保窗口大小变化时网格中心正确
      this.$forceUpdate()
    },

    // 显示调试信息
    showDebugInfo() {
      console.log('=== 🔍 调试信息 ===')
      console.log(`机器人数量: ${this.machines.length}`)
      console.log(`障碍物数量: ${this.obstacles.length}`)
      console.log(`当前激光视野区域: ${this.laserVisionAreas.length}`)
      console.log('障碍物位置:', this.obstacles.map(o => `${o.obstacle_id}: (${o.position[0]}, ${o.position[1]})`))
      console.log('机器人位置:', this.machines.map(m => `${m.machine_id}: (${m.position[0]}, ${m.position[1]})`))
      if (this.laserVisionAreas.length > 0) {
        console.log('激光视野中心:', this.laserVisionAreas.map(v => `(${v.center[0].toFixed(1)}, ${v.center[1].toFixed(1)})`))
      }

      // 激光系统状态
      console.log('\n=== 🧪 激光系统状态 ===')
      console.log(`活跃激光数量: ${this.activeLasers.length}`)
      console.log(`激光视野区域: ${this.laserVisionAreas.length}`)
      if (this.activeLasers.length > 0) {
        this.activeLasers.forEach(laser => {
          console.log(`激光${laser.id}: 起点(${laser.startPos[0]},${laser.startPos[1]}) -> 终点(${laser.endPos[0]},${laser.endPos[1]})`)
        })
      }
      console.log('===============')
    },

    // 切换网格显示
    toggleGridOverlay() {
      this.showGrid = !this.showGrid
      console.log(`🔲 网格辅助线: ${this.showGrid ? '开启' : '关闭'}`)
    }
  }
}
</script>

<style>
#app {
  width: 100vw;
  height: 100vh;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
}
.visualization {
  width: 100vw;
  height: 100vh;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
}
.world-container {
  width: 100vw;
  height: 100vh;
  position: relative;
}
.world-grid {
  width: 100vw;
  height: 100vh;
  position: relative;
  background:
    /* 网格系统：30px网格 */
    linear-gradient(to right, rgba(200, 200, 200, 0.3) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(200, 200, 200, 0.3) 1px, transparent 1px),
    /* 主轴线：更明显的中心线 */
    linear-gradient(to right, rgba(100, 100, 100, 0.8) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(100, 100, 100, 0.8) 1px, transparent 1px);
  background-size: 30px 30px, 30px 30px, 100vw 30px, 30px 100vh;
  background-position: 50% 50%, 50% 50%, 50% 50%, 50% 50%;
}
.machine {
  position: absolute;
  background:
    linear-gradient(135deg, #74b9ff 0%, #0984e3 100%),
    linear-gradient(135deg, #fff6, #fff0 60%);
  border: 2px solid #fff;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 1rem;
  font-weight: 700;
  box-shadow: 0 0 12px 3px #74b9ffaa, 0 2px 6px #0984e344 inset;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  cursor: pointer;
  user-select: none;
  overflow: hidden;
  backdrop-filter: blur(1px);
  z-index: 2;
}
.machine:hover {
  box-shadow: 0 0 20px 6px #74b9ffdd, 0 2px 8px #0984e366 inset;
  transform: scale(1.1) rotate(1deg);
}
.machine-id {
  width: 100%;
  text-align: center;
  font-size: 0.8rem;
  font-family: 'JetBrains Mono', 'Fira Mono', 'Consolas', monospace;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-shadow: 0 1px 4px #0984e355, 0 0 2px #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 2px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 2px;
}

.machine-life {
  position: absolute;
  bottom: -2px;
  right: -2px;
  background: rgba(255, 0, 0, 0.8);
  color: white;
  font-size: 0.7rem;
  font-weight: bold;
  padding: 1px 4px;
  border-radius: 3px;
  min-width: 12px;
  text-align: center;
}

.machine-direction {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-left: 8px solid #fff;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  transform-origin: 0 50%;
  margin-left: 6px;
  margin-top: -2px;
}

.laser-beam {
  position: absolute;
  background: linear-gradient(90deg,
    rgba(255, 50, 50, 0.9) 0%,
    rgba(255, 150, 150, 1) 20%,
    rgba(255, 200, 200, 1) 50%,
    rgba(255, 150, 150, 1) 80%,
    rgba(255, 50, 50, 0.2) 100%);
  box-shadow:
    0 0 15px rgba(255, 0, 0, 0.8),
    0 0 30px rgba(255, 0, 0, 0.6),
    inset 0 0 5px rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  z-index: 5;
  animation: laser-flash 0.5s ease-out;
}

@keyframes laser-flash {
  0% {
    opacity: 0;
    transform: scaleX(0) scaleY(0.3);
    filter: brightness(2) blur(2px);
  }
  15% {
    opacity: 1;
    transform: scaleX(0.3) scaleY(1);
    filter: brightness(3) blur(1px);
  }
  30% {
    opacity: 1;
    transform: scaleX(1) scaleY(1.2);
    filter: brightness(2.5) blur(0px);
  }
  70% {
    opacity: 1;
    transform: scaleX(1) scaleY(1);
    filter: brightness(1.5) blur(0px);
  }
  100% {
    opacity: 0;
    transform: scaleX(1) scaleY(0.8);
    filter: brightness(1) blur(1px);
  }
}

.obstacle {
  position: absolute;
  background:
    linear-gradient(135deg, #636e72 0%, #2d3436 100%);
  border: 1px solid #474747;
  border-radius: 2px;
  box-shadow: 0 0 4px 1px rgba(45, 52, 54, 0.3);
  transition: all 0.3s ease;
  cursor: pointer;
  user-select: none;
  z-index: 1;
}
.obstacle:hover {
  box-shadow: 0 0 8px 2px rgba(116, 185, 255, 0.5);
  border-color: #74b9ff;
}

.status-panel {
  position: fixed;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  z-index: 10;
}
.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.status-item:last-child {
  margin-bottom: 0;
}
.status-label {
  font-weight: 600;
  color: #636e72;
  margin-right: 10px;
}
.status-value {
  font-weight: 700;
  color: #2d3436;
  background: #f8f9fa;
  padding: 2px 8px;
  border-radius: 4px;
  min-width: 30px;
  text-align: center;
}

/* 网格辅助线样式 */
.grid-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
  background-size: 30px 30px;
  background-position:
    calc(50% - 15px) calc(50% - 15px);
  z-index: 0;
}
</style>

