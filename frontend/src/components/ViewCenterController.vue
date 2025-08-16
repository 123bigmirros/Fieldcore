<template>
  <div class="view-center-controller">
    <!-- 当前视野中心状态显示 - 已隐藏 -->
    <!-- <div v-if="isFollowingMachine" class="view-status">
      <span class="status-icon">🎯</span>
      <span class="status-text">跟随: {{ followingMachineDisplayName }}</span>
      <span class="rotation-text">{{ rotationDegrees }}°</span>
      <button @click="resetViewCenter" class="reset-button" title="按0键重置">🏠</button>
    </div> -->

    <!-- 机器人快捷键提示 -->
    <div v-if="showHints" class="view-hints">
      <div class="hints-title">🎮 视野中心控制</div>
      <div class="hints-content">
        <div v-for="(machine, index) in myMachines.slice(0, 9)" :key="machine.machine_id" class="hint-item">
          <kbd>{{ index + 1 }}</kbd>
          <span>机器人{{ getMachineDisplayName(machine.machine_id) }}</span>
          <span class="machine-pos">({{ machine.position[0] }}, {{ machine.position[1] }})</span>
        </div>
        <div class="hint-item">
          <kbd>0</kbd>
          <span>回到世界中心</span>
        </div>
        <div class="hint-separator"></div>
        <div class="hint-item">
          <kbd>Ctrl+H</kbd>
          <span>显示/隐藏提示</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ViewCenterController',
  props: {
    machines: {
      type: Array,
      default: () => []
    },
    humanId: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      // 视野中心偏移量（相对于屏幕中心的偏移）
      viewOffset: { x: 0, y: 0 },
      // 视野旋转角度（弧度）
      viewRotation: 0,
      // 是否正在跟随某个机器人
      isFollowingMachine: false,
      // 正在跟随的机器人ID
      followingMachineId: null,
      // 是否显示快捷键提示
      showHints: false,
      // 网格大小，与主组件保持一致
      gridSize: 30
    }
  },
  computed: {
    // 获取属于当前human的机器人
    myMachines() {
      return this.machines
        .filter(m => m.isMyMachine)
        .sort((a, b) => {
          // 提取机器人ID中的数字部分进行排序
          const getNumber = (machineId) => {
            const match = machineId.match(/(\d+)/)
            return match ? parseInt(match[1], 10) : 0
          }
          return getNumber(a.machine_id) - getNumber(b.machine_id)
        })
    },
    // 当前跟随的机器人显示名称
    followingMachineDisplayName() {
      if (!this.followingMachineId) return ''
      return `机器人${this.getMachineDisplayName(this.followingMachineId)}`
    },
    // 当前旋转角度（度数）
    rotationDegrees() {
      return (this.viewRotation * 180 / Math.PI).toFixed(0)
    }
  },
  mounted() {
    // 监听键盘事件
    window.addEventListener('keydown', this.handleKeyDown)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.handleKeyDown)
  },
  watch: {
    // 监听机器人数据变化，更新跟随的视野中心
    machines: {
      handler() {
        this.updateFollowingViewCenter()
      },
      deep: true
    },
    // 监听viewOffset变化，通知父组件
    viewOffset: {
      handler(newOffset) {
        this.$emit('view-center-changed', {
          offset: newOffset,
          rotation: this.viewRotation
        })
      },
      deep: true
    },
    // 监听viewRotation变化，通知父组件
    viewRotation: {
      handler(newRotation) {
        this.$emit('view-center-changed', {
          offset: this.viewOffset,
          rotation: newRotation
        })
      }
    }
  },
  methods: {
    // 处理键盘按下事件
    handleKeyDown(e) {
      // 只在登录状态下且不在输入框中时响应
      if (!this.humanId || e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return
      }

      // 数字键1-9切换到对应机器人
      if (/^[1-9]$/.test(e.key)) {
        e.preventDefault()
        this.focusOnMachine(parseInt(e.key))
      }

      // 数字键0重置视野中心
      if (e.key === '0') {
        e.preventDefault()
        this.resetViewCenter()
      }

      // Ctrl+H显示/隐藏快捷键提示
      if (e.key === 'h' && e.ctrlKey) {
        e.preventDefault()
        this.toggleHints()
      }
    },

                // 将视野中心移动到指定编号的机器人
    focusOnMachine(machineNumber) {
      if (!this.humanId) return

      // 调试信息：显示所有机器人和筛选结果
      console.log(`🔍 调试按键${machineNumber}:`)
      console.log(`  当前Human ID: ${this.humanId}`)
      console.log(`  所有机器人数量: ${this.machines.length}`)

      // 显示所有机器人的详细信息
      this.machines.forEach((machine, index) => {
        console.log(`    机器人${index + 1}: ${machine.machine_id}, owner: ${machine.owner}, isMyMachine: ${machine.isMyMachine}`)
      })

      console.log(`  我的机器人数量: ${this.myMachines.length}`)
      this.myMachines.forEach((machine, index) => {
        console.log(`    我的机器人${index + 1}: ${machine.machine_id}, owner: ${machine.owner}`)
      })

      // 按键编号对应我的机器人顺序：按键1->我的第1个机器人, 按键2->我的第2个机器人
      if (machineNumber > this.myMachines.length || machineNumber < 1) {
        console.log(`⚠️ 没有第${machineNumber}个属于我的机器人，当前只有${this.myMachines.length}个`)
        this.$emit('show-message', {
          type: 'warning',
          message: `没有第${machineNumber}个属于我的机器人，当前只有${this.myMachines.length}个`
        })
        return
      }

      // 直接按顺序获取我的第N个机器人
      const targetMachine = this.myMachines[machineNumber - 1]
      if (!targetMachine) {
        console.log(`⚠️ 无法获取我的第${machineNumber}个机器人`)
        return
      }

      console.log(`✅ 选中机器人: ${targetMachine.machine_id}, owner: ${targetMachine.owner}`)

                              // 计算机器人朝向角度并设置视野旋转（视角对齐）
      const [dx, dy] = targetMachine.facing_direction || [1.0, 0.0]
      this.viewRotation = this.calculateRotationAngle(dx, dy)

      // 计算视野偏移量，使机器人位置成为屏幕中心
      const [machineX, machineY] = targetMachine.position

      // 先应用旋转变换到机器人位置
      const rotatedPosition = this.applyRotationTransform(machineX * this.gridSize, -machineY * this.gridSize)

      // 计算需要的偏移量（负值是因为我们要移动世界，使旋转后的机器人位置对应屏幕中心）
      this.viewOffset.x = -rotatedPosition.x
      this.viewOffset.y = -rotatedPosition.y

      console.log(`📐 坐标计算详情:`)
      console.log(`  机器人世界坐标: (${machineX}, ${machineY})`)
      console.log(`  网格大小: ${this.gridSize}px`)
      console.log(`  旋转角度: ${(this.viewRotation * 180 / Math.PI).toFixed(1)}°`)
      console.log(`  旋转后位置: (${rotatedPosition.x.toFixed(1)}, ${rotatedPosition.y.toFixed(1)})`)
      console.log(`  计算的视野偏移: (${this.viewOffset.x.toFixed(1)}, ${this.viewOffset.y.toFixed(1)})`)
      console.log(`  屏幕尺寸: ${window.innerWidth}x${window.innerHeight}`)
      console.log(`  屏幕中心: (${window.innerWidth/2}, ${window.innerHeight/2})`)

      // 设置跟随状态
      this.isFollowingMachine = true
      this.followingMachineId = targetMachine.machine_id

      console.log(`🎯 按键${machineNumber} -> 我的第${machineNumber}个机器人 ${targetMachine.machine_id} 居中显示并对齐视角，位置: (${machineX}, ${machineY}), 朝向: (${dx}, ${dy}), 旋转角度: ${(this.viewRotation * 180 / Math.PI).toFixed(1)}°`)

      // 通知父组件
      this.$emit('focus-machine', {
        machineId: targetMachine.machine_id,
        machineNumber: machineNumber,
        position: [machineX, machineY],
        facing: [dx, dy],
        rotation: this.viewRotation
      })
    },

        // 重置视野中心到世界中心
    resetViewCenter() {
      this.viewOffset.x = 0
      this.viewOffset.y = 0
      this.viewRotation = 0  // 重置旋转角度
      this.isFollowingMachine = false
      this.followingMachineId = null
      console.log(`🏠 视野中心重置到世界中心 (0, 0)，旋转角度重置`)

      // 通知父组件
      this.$emit('reset-view-center')
    },

            // 更新跟随机器人的视野中心
    updateFollowingViewCenter() {
      if (!this.isFollowingMachine || !this.followingMachineId) return

      const followingMachine = this.machines.find(m =>
        m.machine_id === this.followingMachineId && m.isMyMachine
      )

      if (!followingMachine) {
        // 跟随的机器人不存在了，重置视野中心
        this.resetViewCenter()
        console.log(`⚠️ 跟随的机器人 ${this.followingMachineId} 不存在，重置视野中心`)
        return
      }

                  // 平滑跟随机器人移动和旋转（实时更新位置和朝向）
      const [machineX, machineY] = followingMachine.position
      const [dx, dy] = followingMachine.facing_direction || [1.0, 0.0]

      // 计算目标旋转角度（实时跟随机器人朝向）
      const targetRotation = this.calculateRotationAngle(dx, dy)

      // 先应用旋转变换到机器人位置
      const rotatedPosition = this.applyRotationTransform(machineX * this.gridSize, -machineY * this.gridSize)

      // 计算目标偏移量
      const targetOffsetX = -rotatedPosition.x
      const targetOffsetY = -rotatedPosition.y

      // 使用线性插值实现平滑移动和旋转
      const lerpFactor = 0.15 // 适中的平滑度，既不会闪烁也不会太慢

      // 计算偏移差值
      const offsetDiffX = targetOffsetX - this.viewOffset.x
      const offsetDiffY = targetOffsetY - this.viewOffset.y
      const rotationDiff = this.normalizeAngleDifference(targetRotation - this.viewRotation)

      // 设置阈值，避免微小抖动
      const positionThreshold = 0.3 // 降低位置阈值，更敏感
      const rotationThreshold = 0.005 // 降低旋转阈值，更敏感（约0.3度）

      // 同时更新位置和旋转角度
      if (Math.abs(offsetDiffX) > positionThreshold) {
        this.viewOffset.x += offsetDiffX * lerpFactor
      }
      if (Math.abs(offsetDiffY) > positionThreshold) {
        this.viewOffset.y += offsetDiffY * lerpFactor
      }
      if (Math.abs(rotationDiff) > rotationThreshold) {
        this.viewRotation += rotationDiff * lerpFactor
      }
    },

    // 提取机器人显示名称
    getMachineDisplayName(machineId) {
      const match = machineId.match(/(\d+)/)
      return match ? match[1] : machineId
    },

    // 切换快捷键提示显示/隐藏
    toggleHints() {
      this.showHints = !this.showHints
      console.log(`💡 快捷键提示: ${this.showHints ? '显示' : '隐藏'}`)
    },

    // 获取当前视野偏移量（供父组件调用）
    getViewOffset() {
      return { ...this.viewOffset }
    },

    // 设置视野偏移量（供父组件调用）
    setViewOffset(offset) {
      this.viewOffset.x = offset.x
      this.viewOffset.y = offset.y
    },

    // 计算机器人朝向角度（从朝向向量计算旋转角度）
    calculateRotationAngle(dx, dy) {
      // 目标：让机器人的前方（朝向）旋转到屏幕正上方
      // 计算机器人当前朝向的角度（相对于正东方向）
      const machineAngle = Math.atan2(-dy, dx) // 注意Y轴反转
      // 目标角度是正上方：π/2 (90度)
      const targetAngle = Math.PI / 2
      // 计算需要旋转的角度：当前角度 - 目标角度（让世界反向旋转）
      let rotationAngle = machineAngle - targetAngle
      // 规范化角度，确保使用最短路径
      rotationAngle = this.normalizeAngleDifference(rotationAngle)
      return rotationAngle
    },

    // 规范化角度差，确保最短路径旋转
    normalizeAngleDifference(angleDiff) {
      // 将角度差限制在[-π, π]范围内
      while (angleDiff > Math.PI) {
        angleDiff -= 2 * Math.PI
      }
      while (angleDiff < -Math.PI) {
        angleDiff += 2 * Math.PI
      }
      return angleDiff
    },

    // 应用旋转变换
    applyRotationTransform(x, y) {
      const cos = Math.cos(this.viewRotation)
      const sin = Math.sin(this.viewRotation)

      return {
        x: x * cos - y * sin,
        y: x * sin + y * cos
      }
    }
  }
}
</script>

<style scoped>
.view-center-controller {
  position: fixed;
  top: 120px;
  right: 20px;
  z-index: 15;
}

.view-status {
  background: rgba(52, 152, 219, 0.95);
  color: white;
  padding: 8px 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(10px);
  margin-bottom: 10px;
  animation: slide-in 0.3s ease-out;
}

.status-icon {
  font-size: 1.1em;
}

.status-text {
  font-weight: 600;
  font-size: 0.9rem;
}

.rotation-text {
  font-weight: 700;
  font-size: 0.8rem;
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}

.reset-button {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.reset-button:hover {
  background: rgba(255, 255, 255, 0.3);
}

.view-hints {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  min-width: 220px;
  animation: slide-in 0.3s ease-out;
}

.hints-title {
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 8px;
  font-size: 0.9rem;
  text-align: center;
}

.hints-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: #636e72;
}

.hint-item kbd {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 3px;
  padding: 2px 6px;
  font-family: 'Courier New', monospace;
  font-size: 0.8rem;
  font-weight: 600;
  color: #495057;
  min-width: 24px;
  text-align: center;
}

.machine-pos {
  color: #3498db;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  margin-left: auto;
}

.hint-separator {
  height: 1px;
  background: #dee2e6;
  margin: 4px 0;
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .view-center-controller {
    top: 80px;
    right: 10px;
  }

  .view-hints {
    min-width: 200px;
  }
}
</style>
