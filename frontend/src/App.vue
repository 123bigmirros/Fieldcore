<template>
  <div id="app">
    <!-- 登录界面 -->
    <div v-if="!humanId" class="login-container">
      <div class="login-box">
        <h2>🤖 OpenManus 智能管理系统</h2>
        <div class="login-form">
          <input
            v-model="inputHumanId"
            type="text"
            placeholder="请输入Human ID"
            @keyup.enter="createHuman"
            class="human-id-input"
          />
          <input
            v-model="machineCount"
            type="number"
            placeholder="机器人数量"
            min="1"
            max="10"
            class="machine-count-input"
          />
          <button @click="createHuman" :disabled="!inputHumanId || isCreating" class="create-button">
            {{ isCreating ? '创建中...' : '创建Human' }}
          </button>
          <div v-if="loginError" class="error-message">{{ loginError }}</div>
        </div>
      </div>
    </div>

    <!-- 主界面 -->
    <div v-else class="main-interface">
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
              <!-- 机器人前端指示器 -->
              <div class="machine-front" :style="getFrontStyle(machine)"></div>
              <div class="machine-id">{{ getMachineDisplayName(machine.machine_id) }}</div>
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
          <span class="status-label">Human ID:</span>
          <span class="status-value">{{ humanId }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">机器人:</span>
          <span class="status-value">{{ machines.length }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">障碍物:</span>
          <span class="status-value">{{ obstacles.length }}</span>
        </div>
        <button @click="exitSystem" class="exit-button">退出系统</button>
      </div>

      <!-- 指令输入框 -->
      <div v-if="showCommandInput" class="command-input-overlay">
        <div class="command-input-box">
          <h3>🎯 发送指令</h3>
          <textarea
            v-model="currentCommand"
            placeholder="请输入指令..."
            @keyup.enter.ctrl="sendCommand"
            class="command-textarea"
            ref="commandTextarea"
          ></textarea>
          <div class="command-buttons">
            <button @click="sendCommand" :disabled="!currentCommand.trim() || isSendingCommand" class="send-button">
              {{ isSendingCommand ? '发送中...' : '发送 (Ctrl+Enter)' }}
            </button>
            <button @click="closeCommandInput" class="cancel-button">取消</button>
          </div>
          <div v-if="commandError" class="error-message">{{ commandError }}</div>
        </div>
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
      // 原始数据
      machines: [],
      obstacles: [],
      refreshInterval: null,
      activeLasers: [], // 活跃的激光特效
      laserVisionAreas: [], // 激光路径的临时视野区域
      shownAttacks: [], // 已经显示过的攻击，避免重复
      showGrid: false, // 是否显示网格辅助线

      // Human管理相关
      humanId: null, // 当前登录的human ID
      inputHumanId: '', // 输入框中的human ID
      machineCount: 3, // 机器人数量
      isCreating: false, // 是否正在创建Human
      loginError: '', // 登录错误信息

      // 指令相关
      showCommandInput: false, // 是否显示指令输入框
      currentCommand: '', // 当前指令
      isSendingCommand: false, // 是否正在发送指令
      commandError: '', // 指令错误信息
      spaceKeyCount: 0, // 空格键计数
      spaceKeyTimer: null // 空格键定时器
    }
  },
  mounted() {
    // 只有登录后才开始刷新数据
    if (this.humanId) {
      this.startAutoRefresh()
    }

    // 监听窗口大小变化，确保网格中心正确
    window.addEventListener('resize', this.forceUpdate)

    // 添加键盘快捷键
    window.addEventListener('keydown', (e) => {
      // 调试快捷键
      if (e.key === 'd' && e.ctrlKey) {
        e.preventDefault()
        this.showDebugInfo()
      }
      if (e.key === 'g' && e.ctrlKey) {
        e.preventDefault()
        this.toggleGridOverlay()
      }

      // 双击空格显示指令输入框
      if (e.key === ' ' && this.humanId && !this.showCommandInput) {
        this.handleSpaceKey()
      }
    })
  },
  beforeUnmount() {
    this.stopAutoRefresh()
    window.removeEventListener('resize', this.forceUpdate)
  },
  methods: {
    // =============  Human管理方法 =============
    async createHuman() {
      if (!this.inputHumanId.trim()) {
        this.loginError = 'Human ID不能为空'
        return
      }

      this.isCreating = true
      this.loginError = ''

      try {
        const response = await axios.post('http://localhost:8004/api/humans', {
          human_id: this.inputHumanId.trim(),
          machine_count: this.machineCount
        })

        if (response.data.status === 'success') {
          this.humanId = this.inputHumanId.trim()
          this.inputHumanId = ''

          // 登录成功后开始刷新数据
          this.startAutoRefresh()

          console.log(`✅ Human ${this.humanId} 创建成功，机器人数量: ${response.data.machine_count}`)
        }
      } catch (error) {
        console.error('创建Human失败:', error)
        this.loginError = error.response?.data?.error || '创建失败，请重试'
      } finally {
        this.isCreating = false
      }
    },

    async exitSystem() {
      if (!this.humanId) return

      try {
        await axios.delete(`http://localhost:8004/api/humans/${this.humanId}`)
        console.log(`✅ Human ${this.humanId} 已删除`)

        // 停止刷新数据
        this.stopAutoRefresh()

        // 重置状态
        this.humanId = null
        this.machines = []
        this.obstacles = []
        this.activeLasers = []
        this.laserVisionAreas = []
        this.shownAttacks = []

      } catch (error) {
        console.error('删除Human失败:', error)
        // 即使删除失败也要退出界面
        this.humanId = null
      }
    },

    // ============= 指令相关方法 =============
    handleSpaceKey() {
      this.spaceKeyCount++

      // 清除之前的定时器
      if (this.spaceKeyTimer) {
        clearTimeout(this.spaceKeyTimer)
      }

      // 500ms内双击空格
      this.spaceKeyTimer = setTimeout(() => {
        if (this.spaceKeyCount >= 2) {
          this.openCommandInput()
        }
        this.spaceKeyCount = 0
      }, 500)
    },

    openCommandInput() {
      this.showCommandInput = true
      this.currentCommand = ''
      this.commandError = ''

      // 下一帧后聚焦到文本框
      this.$nextTick(() => {
        if (this.$refs.commandTextarea) {
          this.$refs.commandTextarea.focus()
        }
      })
    },

    closeCommandInput() {
      this.showCommandInput = false
      this.currentCommand = ''
      this.commandError = ''
    },

    async sendCommand() {
      if (!this.currentCommand.trim() || !this.humanId) {
        return
      }

      this.isSendingCommand = true
      this.commandError = ''

      // 发送命令后立即关闭窗口，不等待响应
      const commandToSend = this.currentCommand.trim()
      this.closeCommandInput()

      try {
        const response = await axios.post(`http://localhost:8004/api/humans/${this.humanId}/command`, {
          command: commandToSend
        })

        if (response.data.status === 'success') {
          console.log(`📡 指令已发送: ${commandToSend}`)
        }
      } catch (error) {
        console.error('发送指令失败:', error)
        // 由于窗口已关闭，这里只能在控制台输出错误信息
        console.error('指令发送失败，请重试')
      } finally {
        this.isSendingCommand = false
      }
    },

    // ============= 原始刷新数据方法 =============
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
        // 获取机器人前端指示器样式
    getFrontStyle(machine) {
      const [dx, dy] = machine.facing_direction || [1, 0]

      // 将方向向量转换为4个基本方向
      let direction = 'right' // 默认向右
      if (Math.abs(dx) > Math.abs(dy)) {
        direction = dx > 0 ? 'right' : 'left'
      } else {
        direction = dy > 0 ? 'up' : 'down'
      }

      // 根据方向设置前端指示器位置和形状
      const styles = {
        'right': {
          right: '-2px', top: '25%',
          width: '8px', height: '50%',
          borderRadius: '0 4px 4px 0'
        },
        'left': {
          left: '-2px', top: '25%',
          width: '8px', height: '50%',
          borderRadius: '4px 0 0 4px'
        },
        'up': {
          top: '-2px', left: '25%',
          width: '50%', height: '8px',
          borderRadius: '4px 4px 0 0'
        },
        'down': {
          bottom: '-2px', left: '25%',
          width: '50%', height: '8px',
          borderRadius: '0 0 4px 4px'
        }
      }

      return styles[direction] || styles['right']
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
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 1rem;
  font-family: 'JetBrains Mono', 'Fira Mono', 'Consolas', monospace;
  font-weight: 800;
  letter-spacing: 1px;
  text-shadow:
    0 1px 3px rgba(0, 0, 0, 0.8),
    0 0 8px rgba(255, 255, 255, 0.6),
    0 0 12px rgba(116, 185, 255, 0.4);
  color: #fff;
  white-space: nowrap;
  z-index: 2;
}



/* 机器人前端指示器 */
.machine-front {
  position: absolute;
  background: linear-gradient(135deg, #ffff00 0%, #ffd700 100%);
  box-shadow:
    0 0 8px rgba(255, 255, 0, 0.8),
    0 0 12px rgba(255, 215, 0, 0.4),
    inset 0 1px 2px rgba(255, 255, 255, 0.3);
  z-index: 4;
  pointer-events: none;
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

/* =============== 登录界面样式 =============== */
.login-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(20px);
  text-align: center;
  min-width: 400px;
}

.login-box h2 {
  margin-bottom: 30px;
  color: #2d3436;
  font-size: 1.8rem;
  font-weight: 700;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.human-id-input, .machine-count-input {
  padding: 12px 16px;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.human-id-input:focus, .machine-count-input:focus {
  outline: none;
  border-color: #74b9ff;
  box-shadow: 0 0 0 3px rgba(116, 185, 255, 0.1);
}

.create-button {
  padding: 12px 24px;
  background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.create-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(116, 185, 255, 0.4);
}

.create-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* =============== 主界面样式 =============== */
.main-interface {
  width: 100vw;
  height: 100vh;
  position: relative;
}

.exit-button {
  margin-top: 10px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #fd79a8 0%, #e84393 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  width: 100%;
}

.exit-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(232, 67, 147, 0.4);
}

/* =============== 指令输入框样式 =============== */
.command-input-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.command-input-box {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  min-width: 500px;
  max-width: 80vw;
}

.command-input-box h3 {
  margin: 0 0 20px 0;
  color: #2d3436;
  font-size: 1.4rem;
  text-align: center;
}

.command-textarea {
  width: 100%;
  min-height: 120px;
  padding: 12px;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 15px;
}

.command-textarea:focus {
  outline: none;
  border-color: #74b9ff;
  box-shadow: 0 0 0 3px rgba(116, 185, 255, 0.1);
}

.command-buttons {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.send-button {
  padding: 10px 20px;
  background: linear-gradient(135deg, #00b894 0%, #00a085 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.send-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0, 184, 148, 0.4);
}

.send-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cancel-button {
  padding: 10px 20px;
  background: #636e72;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.cancel-button:hover {
  background: #2d3436;
  transform: translateY(-1px);
}

/* =============== 错误信息样式 =============== */
.error-message {
  color: #d63031;
  background: rgba(214, 48, 49, 0.1);
  padding: 10px;
  border-radius: 6px;
  border: 1px solid rgba(214, 48, 49, 0.2);
  font-size: 0.9rem;
  margin-top: 10px;
}
</style>

