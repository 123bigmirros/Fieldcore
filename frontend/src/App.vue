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
          ></div>

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
      shownAttacks: [], // 已经显示过的攻击，避免重复
    }
  },
  mounted() {
    this.startAutoRefresh()
    // 监听窗口大小变化，确保网格中心正确
    window.addEventListener('resize', this.forceUpdate)
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

          // 检查是否有激光攻击效果需要显示
          this.checkForLaserEffects(machines)
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
    // 检查机器人是否在任何其他机器人的可见范围内
    isMachineVisible(machine) {
      return this.machines.some(observer => {
        if (observer.machine_id === machine.machine_id) return true
        return this.squareDistance(observer.position, machine.position) <= observer.visibility_radius
      })
    },
    // 检查障碍物是否在任何机器人的可见范围内
    isObstacleVisible(obstacle) {
      return this.machines.some(machine => {
        return this.squareDistance(machine.position, obstacle.position) <= machine.visibility_radius
      })
    },

    // 检查是否有激光攻击效果
    checkForLaserEffects(machines) {
      machines.forEach(machine => {
        // 检查机器人的最后动作是否为激光攻击
        if (machine.last_action && machine.last_action.includes('laser_attack')) {
          console.log(`检测到激光攻击: ${machine.machine_id} - ${machine.last_action}`)

          // 从last_action中提取时间戳来判断是否是新的攻击
          const timeMatch = machine.last_action.match(/time:(\d+)/)
          if (timeMatch) {
            const attackTimestamp = timeMatch[1]
            const attackId = `${machine.machine_id}_${attackTimestamp}`

            if (!this.shownAttacks.includes(attackId)) {
              console.log(`显示激光特效: ${machine.machine_id} (时间戳: ${attackTimestamp})`)
              this.showLaserEffect(machine)
              this.shownAttacks.push(attackId)
              // 限制历史记录大小
              if (this.shownAttacks.length > 50) {
                this.shownAttacks = this.shownAttacks.slice(-25)
              }
            } else {
              console.log(`攻击已显示过: ${attackId}`)
            }
          } else {
            // 兼容旧格式（没有时间戳）
            const attackId = `${machine.machine_id}_${machine.last_action}`
            if (!this.shownAttacks.includes(attackId)) {
              console.log(`显示激光特效: ${machine.machine_id} (旧格式)`)
              this.showLaserEffect(machine)
              this.shownAttacks.push(attackId)
            }
          }
        }
      })
    },
    // 显示激光特效
    showLaserEffect(machine) {
      const laserId = Date.now() + Math.random()
      const [x, y] = machine.position
      const [dx, dy] = machine.facing_direction

      console.log(`创建激光特效: 机器人${machine.machine_id} 位置(${x},${y}) 朝向(${dx},${dy})`)

      // 计算激光终点（假设射程为5）
      const range = 5.0
      const endX = x + dx * range
      const endY = y + dy * range

      const laser = {
        id: laserId,
        startPos: [x, y],
        endPos: [endX, endY],
        timestamp: Date.now()
      }

      this.activeLasers.push(laser)
      console.log(`激光特效已添加，当前活跃激光数量: ${this.activeLasers.length}`)

      // 3秒后移除激光特效（增加显示时长）
      setTimeout(() => {
        this.activeLasers = this.activeLasers.filter(l => l.id !== laserId)
        console.log(`激光特效已移除，剩余激光数量: ${this.activeLasers.length}`)
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
    // 获取激光特效样式
    getLaserStyle(laser) {
      const gridSize = 30
      const worldCenter = {
        x: window.innerWidth / 2,
        y: window.innerHeight / 2
      }

      const [startX, startY] = laser.startPos
      const [endX, endY] = laser.endPos

      const pixelStartX = worldCenter.x + startX * gridSize
      const pixelStartY = worldCenter.y - startY * gridSize
      const pixelEndX = worldCenter.x + endX * gridSize
      const pixelEndY = worldCenter.y - endY * gridSize

      const dx = pixelEndX - pixelStartX
      const dy = pixelEndY - pixelStartY
      const length = Math.sqrt(dx * dx + dy * dy)
      const angle = Math.atan2(dy, dx) * 180 / Math.PI

      return {
        left: `${pixelStartX}px`,
        top: `${pixelStartY}px`,
        width: `${length}px`,
        height: '3px',
        transform: `rotate(${angle}deg)`,
        transformOrigin: '0 50%'
      }
    },
    forceUpdate() {
      // 强制重新渲染，确保窗口大小变化时网格中心正确
      this.$forceUpdate()
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
    rgba(255, 0, 0, 0.9) 0%,
    rgba(255, 100, 100, 0.8) 50%,
    rgba(255, 0, 0, 0) 100%);
  box-shadow: 0 0 10px #ff0000, 0 0 20px #ff0000;
  z-index: 5;
  animation: laser-pulse 3s ease-out;
}

@keyframes laser-pulse {
  0% { opacity: 0; transform: scaleX(0); }
  10% { opacity: 1; transform: scaleX(1); }
  90% { opacity: 1; transform: scaleX(1); }
  100% { opacity: 0; transform: scaleX(1); }
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


</style>

